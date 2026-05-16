# CDC 与 Base State 联合验证

阶段 8F-1 的目的，是在真正观察车轮物理方向前，通过 STM32 USB CDC 调试输出和 `/spraying_car/base_state` 验证 STM32 软件状态是否按 ROS 命令变化。

该测试不能替代架空物理方向测试。它只验证 STM32 是否接收、解析并设置状态，不验证车轮真实方向、转向机械方向、继电器接线或电机控制器实际响应。

当前 STM32 未连接步进电机和转向编码器时，`turn_encoder_position` 可能无效，PID 到位判断也不可信。本阶段只要求 `turn_cmd_position` 能反映最近一次通过串口收到的转向命令位置。

## 测试前条件

- Flask 已停止，避免和 ROS 同时占用 `/dev/ttyS3`。
- `/dev/ttyS3` 空闲，它仍是 STM32 车辆控制串口。
- `/dev/ttyACM0` 只读，它是 STM32 USB CDC 调试口。
- 车辆最好仍然架空，或至少确保驱动电机不会造成危险。
- 喷药关闭，喷药泵/风机最好断电。
- 遥控器在手，可以随时接管。
- 软件急停可用。
- 每个非零速度动作只持续 `0.3..0.5 s`。
- 测试结束必须发送 stop。

检查命令：

```bash
ps aux | grep -E "app.py|start.py|flask" | grep -v grep
lsof /dev/ttyS3
lsof /dev/ttyACM0
```

如果 `lsof` 不可用，可使用：

```bash
fuser -v /dev/ttyS3
fuser -v /dev/ttyACM0
```

## 启动步骤

终端 1：启动 ROS 底盘节点。注意这会真实打开 `/dev/ttyS3`，必须人工确认安全后再执行。

```bash
roslaunch spraying_car_base base_real_suspended_test.launch dry_run:=false port:=/dev/ttyS3
```

终端 2：只读监控 STM32 CDC 调试口。

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py \
  _port:=/dev/ttyACM0 \
  _raw_hex:=true \
  _ascii:=true
```

终端 3：执行状态验证。

```bash
rosrun spraying_car_tools base_state_verification_test.py
```

脚本会要求输入确认字符串：

```text
I_UNDERSTAND_THIS_SENDS_REAL_STM32_COMMANDS
```

未输入完全一致的确认字符串时，不会发布非零 `/cmd_vel`。

转向步骤会默认保持至少 2 秒，并在保持期间连续记录 `turn_cmd_position`、`turn_target_encoder` 和 `turn_encoder_position` 时间序列。需要延长采样时可使用：

```bash
rosrun spraying_car_tools base_state_verification_test.py _turn_duration:=3.0
```

## 预期现象

CDC 侧可能看到：

- `CMD Received`
- `SPEED`
- `DIR`
- `TURN`
- `SPRAY`
- `STATUS`
- `EXT STATUS`
- `FORWARD`
- `BACK`
- `STOP`
- 或原始二进制包的 hex 输出

如果日志太多，可以启用关键词过滤：

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py \
  _port:=/dev/ttyACM0 \
  _raw_hex:=true \
  _ascii:=true \
  _keyword_filter:=default
```

`/spraying_car/base_state` 中应能看到：

- `forward_slow` 后 `direction=1`，`speed_duty > 1`
- `backward_slow` 后 `direction=2`，`speed_duty > 1`
- `stop` 后 `direction=0`，`speed_duty` 接近 `min_speed_duty`
- `left_slow` 和 `right_slow` 后 `turn_cmd_position` 偏离 51，且方向相反
- `using_ext_status=true`
- `uart_control_mode=1`，表示串口控制模式

字段语义：

- `turn_cmd_position`：最近一次串口转向命令位置，范围 `1..101`，`51` 为中位。
- `turn_target_encoder`：根据转向命令计算出的目标编码器位置。
- `turn_encoder_position`：实际转向编码器反馈。当前未连接步进电机/编码器时该字段不可信，只作为日志参考，不作为本测试的核心 PASS/FAIL 依据。

## 不能证明的内容

- 不能证明车轮真实前进/后退方向。
- 不能证明转向机械方向。
- 不能证明继电器接线方向。
- 不能证明电机控制器实际响应。
- 不能证明自动导航能力。

下一步仍需要执行架空物理方向测试，人工观察 `forward/backward/left/right/stop`。

## 失败判断

CDC 有命令但 `/spraying_car/base_state` 不变：

- STM32 可能收到串口字节但状态包未更新。
- 检查扩展状态包 `0x07` 是否被发送。
- 检查 `spraying_car_base` 是否解析到 `using_ext_status=true`。

`/spraying_car/base_state` 变化但 CDC 无文本：

- CDC 调试输出可能未启用或没有文本日志。
- 如果 raw hex 有数据，仍可作为辅助证据。
- 无 CDC 文本不代表控制链路失败。

`direction` 反了：

- 不要立即改 STM32。
- 先记录 ROS 命令、CDC 文本、base_state。
- 检查 STM32 对 `direction=1/2` 的定义。

`turn_cmd_position` 不变化：

- 检查 `/cmd_vel angular.z` 是否非零。
- 检查 `turn_direction_sign` 是否为预期。
- 检查扩展状态包是否真实返回 `turn_cmd_position`。
- 如果 CDC 中能看到 `aa 04 01 47 47 55`、`aa 04 01 1f 1f 55` 或 `TURN` 文本，但 `turn_cmd_position` 仍为 51，优先检查 STM32 扩展状态中的 `get_turn_cmd_position()` 是否返回了最近一次串口转向命令，而不是实际编码器值或默认中位。

`using_ext_status=false`：

- 旧状态包仍兼容，但本阶段无法确认扩展转向字段。
- 检查 STM32 是否支持 `CMD_EXT_STATUS_QUERY=0x06` 和 `CMD_EXT_STATUS_RESPONSE=0x07`。
- 检查 `/dev/ttyS3` 是否被 Flask 或其他进程占用。
