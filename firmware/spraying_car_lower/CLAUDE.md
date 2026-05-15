# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`spraying_car_lower` is the **STM32F407 firmware for the lower controller of a two-board spraying-car system**. A separate "upper computer" sends commands over UART; an RC receiver provides a parallel manual-control path. The firmware drives a DC traction motor (via DAC), a stepper for steering (with encoder feedback + PID), a spray-pump relay, and an OLED used as a debug overlay.

Generated from STM32CubeMX (`spraying_car.ioc`, `.mxproject`); user code lives in `Core/Src` + `Core/Inc`. Source comments are in Chinese.

## Build / flash / debug

There are **two parallel build setups for the same source tree** — both use the ARM Compiler 5 (AC5) toolchain and produce a J-Link-flashable image. Pick whichever matches the host's installed tooling; do not migrate one to the other casually.

- **EIDE (VS Code)** — primary. Config: `.eide/eide.yml`. Output: `build/spraying_car/`. Run via the VS Code tasks in `.vscode/tasks.json`:
  - `build`, `rebuild`, `clean`, `flash`, `build and flash` — these are command-palette wrappers over EIDE (`${command:eide.project.build}` etc.); they only work inside VS Code with the `cl.eide` extension installed. There is no headless CLI build.
- **Keil MDK-ARM uVision** — `MDK-ARM/spraying_car.uvprojx`. Output: `MDK-ARM/spraying_car/spraying_car.{axf,hex}`.

Both targets define `USE_HAL_DRIVER` and `STM32F407xx`, include `Core/Inc` + `Drivers/STM32F4xx_HAL_Driver/Inc` + `Drivers/CMSIS/...`, and flash via J-Link at 8000 kHz. Optimization is `-O3` with `--diag_suppress=1,1295` (suppresses noisy AC5 warnings — keep the suppression when adding files).

If you change peripherals or pin config, regenerate from `spraying_car.ioc` in CubeMX. The CubeMX-generated files (`gpio.c/h`, `dma.c/h`, `tim.c/h`, `usart.c/h`, `dac.c/h`, `stm32f4xx_it.c/h`, `stm32f4xx_hal_msp.c`, `main.c` outside `USER CODE` blocks) get overwritten — keep edits inside the `/* USER CODE BEGIN ... */` ... `/* USER CODE END ... */` markers.

## Code style

Formatting is governed by `.clang-format` (Microsoft base, 4-space indent, no column limit, Linux braces, `SortIncludes: false`). Run clang-format before committing significant changes — the existing files are not all conformant, so reformat only what you touch.

## Architecture: the two control paths

The single most important thing to understand is that **two independent input sources can drive the car, and `car_drive.c` arbitrates between them**:

1. **Remote control (RC)** — an RC receiver outputs PWM on 5 channels (CH3–CH7). Each channel feeds a TIMx input-capture in slave reset mode (`Remote_control.c`): TIM9=CH3, TIM12=CH4, TIM2=CH5, TIM3=CH6, TIM4=CH7. `GetDuty()` returns `(CCR2 - 1000) / 10`, mapping a 1000–2020 µs pulse to `0..102`.
2. **UART (upper computer)** — USART1 @ 115200, DMA + idle-line RX. `upper.c` runs a byte-wise state machine parsing framed packets `[0xAA][type][len][data...][checksum=Σdata][0x55]`. Command types are `CMD_SPRAY_CONTROL=0x01`, `CMD_SPEED_CONTROL=0x02`, `CMD_DIRECTION_CONTROL=0x03`, `CMD_TURN_CONTROL=0x04`, `CMD_STATUS_QUERY=0xFF` (responds with `CMD_STATUS_RESPONSE=0x05`). `packData()` / `sendData()` build replies; `send_status_data()` is the canonical reply shape.

Arbitration is a **single global `uart_control_mode` flag** in `car_drive.c`:
- UART setters (`carSpeed_set` / `spray_set` / `direction_set`) → `uart_control_mode = 1`.
- The RC polling functions (`speed_control` / `direction_control` / `spray_control`, called every iteration of `main` while `is_open == 1`) detect a *change* in their channel vs. its `prev_CHx` and, on change, force `uart_control_mode = 0` and re-apply RC state via `update_rc_control()`. Without a change, RC stays passive in UART mode.
- All three layers share volatile globals: `is_open`, `direction_state`, `spray_state`, `vehicle_speed`, `uart_control_mode`. Anything that writes hardware should also update these so the other path stays consistent.

`car_drive.c` enforces a **hardware/control layer split** that any new actuator code should follow:
- `hw_set_*` (static) — touch hardware only, no state mutation.
- Public `*_set` (called from `upper.c`) — update state, set `uart_control_mode=1`, then call `hw_set_*`.
- `update_rc_control` — update state + hardware without touching `uart_control_mode` (the RC path).

Don't call `HAL_GPIO_WritePin` / `HAL_DAC_SetValue` directly from new code; route through these helpers so the two modes stay coherent. `emergency_stop()` is the one intentional exception.

## Steering: stepper + encoder PID (`turn.c`)

Steering uses a closed-loop position controller, not raw open-loop steps:
- TIM8 CH1 PWM (`PSC=72-1`, dynamic `ARR`) clocks STEP at 5–80 kHz; PD5 is DIR.
- TIM5 in encoder mode reads the absolute position (`Get_Encoder_Value` in `Encoder.c`).
- `Calculate_Target_Position(CH4)` maps CH4 ∈ [1,101] → target encoder counts `(CH4 - 51) * 500`.
- `HAL_TIM_PWM_PulseFinishedCallback` (per-pulse ISR) runs the PID + accel/decel ramp, decides direction, and stops within ≤2 counts of target. Direction changes only after speed has dropped below `MIN_SPEED * 1.5` to avoid mechanical shock.
- `Step_Motor_Control()` is the polling entry from `main`; it is a no-op when CH4 hasn't changed (the ISR handles steady-state convergence).
- `set_target_position()` is the entry called from the UART `CMD_TURN_CONTROL` path — it bypasses the CH4-changed gate.

When you tune `PID_KP/KI/KD`, `MIN_SPEED/MAX_SPEED`, `ACCEL_RATE/DECEL_RATE`, or `DECEL_START_DIFF` in `turn.c`, the dynamics change for *both* RC and UART steering inputs.

## Power-on gesture and `is_open`

`main.c::check_and_toggle_relay` implements a long-press gesture: holding CH3==1 with CH4==1 (or CH4==102, depending on current state) for ~50 polling iterations toggles `eleRelay1` (main power) and `is_open`. While `is_open == 0`, the RC handlers force everything to zero; UART commands force `is_open = 1` on receipt, so a UART command bypasses the gesture. The buzzer beeps for ~500 ms on each toggle.

## OLED as debug overlay (`upper.c::DEBUG_MODE`)

`upper.c` defines `DEBUG_MODE` (default `1`). The `DEBUG_OLED_*` macros expand to real `OLED_*` calls when `DEBUG_MODE=1` and to `((void)0)` when `0`. Set `DEBUG_MODE=0` for production builds — it removes a lot of OLED I/O and OLED becomes pure overhead-free. Don't sprinkle raw `OLED_*` calls into new debug code; use the `DEBUG_OLED_*` wrappers so production strips them out. The OLED is driven by software I²C on PE3 (SCL) / PE4 (SDA), not a HAL peripheral.

## Pin map (from `main.h` defines, don't hardcode the same pins again)

| Signal       | Pin  | Notes                                  |
|--------------|------|----------------------------------------|
| eleRelay1    | PE1  | Main power relay (gesture-toggled)     |
| eleRelay2    | PE2  | Spray pump relay (`hw_set_spray`)      |
| forward      | PC0  | Direction relay forward                |
| backward     | PC1  | Direction relay backward               |
| step_dir     | PC5  | Stepper direction                      |
| buzzer       | PD0  | Active-low                             |
| oledscl/sda  | PE3/PE4 | Software I²C, open-drain            |
| USART1 TX/RX | PA9/PA10 | Upper-computer link, DMA both ways |
| USART2 TX/RX | PA2/PA3  | Initialized but `Uart_Rxopen` for it is commented out in main |

Stepper PWM is on TIM8_CH1 (see CubeMX), DAC1 channel 1 drives the traction-motor speed input.

## Things to know before changing things

- **Globals are `volatile` for a reason** — they are touched by the UART RX callback, the TIM8 PWM ISR, and the main loop. Don't make them non-volatile or move them into structs without auditing all writers.
- **`carSpeed_set` curve is non-linear**: duty=1 → 0 V, duty 2..101 → linear 1.00..2.98 V (DAC), duty=102 → 3.10 V. Don't "simplify" this without checking what the motor controller expects.
- **The packet checksum is the unsigned sum of the data bytes only** (not including type/length/head/tail). `processData` only fires when checksum and tail both match; mismatches reset to `WAIT_HEAD`.
- **`HAL_UARTEx_ReceiveToIdle_DMA` is re-armed inside `HAL_UARTEx_RxEventCallback`**. If you change the RX path, keep the re-arm or RX will silently die after the first packet.
- The RX buffer (`rxBuffer[128]`) is defined in `upper.c` and `extern`-referenced by `usart.c::Uart_Rxopen` — moving it requires updating both.
- `Encoder.c` reads TIM5 as an `int16_t` cast of a 32-bit counter; the counter is reset to 0 once at startup in `main` (`__HAL_TIM_SET_COUNTER(&htim5, 0)`). Position drift across half-rotations of the 16-bit window is not handled — keep ranges within ±32 767 counts.
