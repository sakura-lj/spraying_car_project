# 架空底盘方向验证

阶段 8F 只验证 ROS 通过 `/cmd_vel -> spraying_car_base -> STM32` 真实控制底盘时的方向和安全停车。它不验证自动导航，不启动 `move_base`，不启动 TEB，不启动 point_lio，也不测试地面行驶。

## 测试目的

- 验证 `forward_slow` 时驱动轮方向是否为前进。
- 验证 `backward_slow` 时驱动轮方向是否为后退。
- 验证 `left_slow` 和 `right_slow` 时转向方向是否符合预期。
- 验证停车命令有效。
- 验证 `cmd_timeout` 超时保护有效。
- 验证节点退出安全停车有效。
- 验证 `/dev/ttyACM0` 只能作为 STM32 CDC 只读调试口。

## 测试前条件

人工逐项确认：

- 车辆已架空，驱动轮离地。
- 周围无人、无障碍物、无喷药风险。
- 喷药泵/风机电源最好断开，或确认喷药关闭。
- 遥控器在手，可以随时接管。
- 软件急停可用。
- Flask 上位机已停止，确保 `web/upper/start.py` 没有运行。
- `/dev/ttyS3` 未被其他进程占用。
- `/dev/ttyACM0` 只用于只读监控，不用于控制。
- `max_speed_duty` 保持低值。
- 每次动作只持续 `0.5..1.0 s`。
- 测试结束必须发送停车命令。

检查命令：

```bash
ps aux | grep -E "app.py|start.py|flask" | grep -v grep
lsof /dev/ttyS3
lsof /dev/ttyACM0
```

如果没有安装 `lsof`，可以使用：

```bash
fuser -v /dev/ttyS3
fuser -v /dev/ttyACM0
```

这些命令只用于检查占用情况，不会发送串口数据。

## 启动 STM32 CDC 只读监控

可选开一个终端：

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py _port:=/dev/ttyACM0 _baud:=115200
```

要求：

- 只读。
- 不向 `/dev/ttyACM0` 写入。
- 无输出不视为失败。
- 不要把 `/dev/ttyACM0` 配置给 `spraying_car_base`。

## Dry-run 预演

先确认 launch 和 `/cmd_vel` 工具链路：

```bash
roslaunch spraying_car_base base_real_suspended_test.launch dry_run:=true
```

另开终端：

```bash
rosrun spraying_car_tools cmd_vel_test.py _preset:=forward_slow
```

预期：

- `spraying_car_base_node` 打印 `dry_run=true`。
- 不打开 `/dev/ttyS3`。
- `forward_slow` 被映射为低速前进意图。
- 测试结束后发布 0 速度。

## CDC 状态前置验证

在观察车轮真实方向前，建议先执行阶段 8F-1：

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py _port:=/dev/ttyACM0 _raw_hex:=true _ascii:=true
rosrun spraying_car_tools base_state_verification_test.py
```

只验证转向扩展状态回传时，也可以运行：

```bash
rosrun spraying_car_tools turn_ext_status_probe.py
```

该探针会要求输入：

```text
I_UNDERSTAND_THIS_SENDS_REAL_STM32_TURN_COMMANDS
```

该步骤通过 `/dev/ttyACM0` 和 `/spraying_car/base_state` 验证 STM32 是否接收并设置了 `direction`、`speed_duty`、`turn_cmd_position` 等软件状态。

当前未连接步进电机和转向编码器时：

- `turn_cmd_position` 只表示最近一次串口转向命令位置，`51` 为中位。
- `turn_target_encoder` 是由命令换算出的目标编码器值。
- `turn_encoder_position` 是实际编码器反馈，未接编码器时不可信。
- `ext_status_seq` 每个 `0x07` 扩展状态响应递增一次，用于判断 `/spraying_car/base_state` 是否来自新的扩展状态包。
- CDC 中的 `EXT TURN:<value> SEQ:<seq>` 用于确认 STM32 发送扩展状态包前 `data[5]` 的实际值。

边界：

- `/dev/ttyACM0` 仍然只读，禁止写入。
- `/dev/ttyS3` 才是控制串口。
- CDC 状态验证不能替代架空物理方向观察。
- 即使 8F-1c 软件状态通过，仍不能证明真实转向机械方向，后续仍必须人工观察架空物理方向。

## 真实架空测试

只有在车辆已架空、Flask 已停止、遥控器和急停已准备好时，才允许人工显式启动：

```bash
roslaunch spraying_car_base base_real_suspended_test.launch dry_run:=false port:=/dev/ttyS3
```

另开终端运行：

```bash
rosrun spraying_car_tools suspended_base_direction_test.py
```

脚本会要求输入：

```text
I_UNDERSTAND_WHEELS_ARE_OFF_GROUND
```

未输入完全一致的确认字符串时，不会发布任何非零 `/cmd_vel`。

## 单项测试命令

只测试停车：

```bash
rosrun spraying_car_tools cmd_vel_test.py _preset:=stop
```

只测试前进：

```bash
rosrun spraying_car_tools cmd_vel_test.py _preset:=forward_slow
```

只测试后退：

```bash
rosrun spraying_car_tools cmd_vel_test.py _preset:=backward_slow
```

只测试左转：

```bash
rosrun spraying_car_tools cmd_vel_test.py _preset:=left_slow
```

只测试右转：

```bash
rosrun spraying_car_tools cmd_vel_test.py _preset:=right_slow
```

## 观察项

- `forward_slow` 时驱动轮是否前进。
- `backward_slow` 时驱动轮是否后退。
- `left_slow` 时转向是否向期望方向。
- `right_slow` 时转向是否向期望方向。
- `stop` 是否立即停。
- 停止发布 `/cmd_vel` 后，`cmd_timeout` 是否停车。
- Ctrl-C 或关闭节点时是否发送安全停车。
- 遥控器是否可以随时接管。

## 如果方向反了

- 立即停止测试并记录现象。
- 不要现场乱改 STM32 固件。
- 先判断是 `direction` 前后映射反、`turn_direction_sign` 反，还是机械方向理解反。
- 如果只是转向方向反，优先调整 `spraying_car_base` 参数 `turn_direction_sign`。
- 如果前后方向反，检查 STM32 对 `direction=1/2` 的定义和接线/电机方向。
- 修改参数后重新从 dry-run 预演开始。

## 禁止事项

- 禁止车辆落地测试。
- 禁止启动 `move_base`。
- 禁止启动 `navigation_live_slam.launch`。
- 禁止启动 point_lio。
- 禁止 Flask 同时打开 `/dev/ttyS3`。
- 禁止长时间持续发速度。
- 禁止高速度档位。
- 禁止向 `/dev/ttyACM0` 写入数据。

## 测试结果记录表

| 字段 | 记录 |
| --- | --- |
| 测试时间 |  |
| 操作者 |  |
| 车辆是否架空 |  |
| Flask 是否停止 |  |
| `/dev/ttyS3` 是否空闲 |  |
| `max_speed_duty` |  |
| forward 是否正确 |  |
| backward 是否正确 |  |
| left 是否正确 |  |
| right 是否正确 |  |
| stop 是否正确 |  |
| timeout 是否正确 |  |
| 节点退出停车是否正确 |  |
| 遥控器接管是否有效 |  |
| 需要修改的参数 |  |
| 备注 |  |
