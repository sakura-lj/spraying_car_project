# ROS Base Bridge

本文档记录阶段 3 的 `spraying_car_base` 底盘桥接节点。该阶段只实现 ROS 到 STM32 当前旧串口协议的桥接，不实现 `move_base`、TEB、waypoint，也不修改 STM32 固件、Flask、Vue 或 third_party。

## 节点功能

节点：`spraying_car_base_node`

包路径：

```text
ros/catkin_ws/src/spraying_car_base/
```

订阅：

```text
/cmd_vel    geometry_msgs/Twist
```

发布：

```text
/spraying_car/base_state    std_msgs/String
```

`/spraying_car/base_state` 是 JSON 字符串，包含：

- `spray_state`
- `speed_duty`
- `direction`
- `is_open`
- `connected`
- `last_cmd_time`
- `mode`
- `error_count`
- `raw_status`

后续阶段再替换为 `spraying_car_msgs/VehicleState.msg`。

## 为什么需要 spraying_car_base

`spraying_car_base` 是 ROS 侧唯一允许操作 STM32 底盘串口的正式节点。这样可以把限速、超时停车、急停、串口异常处理和协议转换集中在一个地方。

禁止让 `move_base`、TEB、waypoint 或 Web 页面直接操作 STM32 串口。它们只能发布目标或 `/cmd_vel`，由 `spraying_car_base` 统一转换为 STM32 协议。

## 协议复用

节点复用：

```text
web/upper/vehicle_protocol.py
```

使用的协议函数包括：

- `build_spray_packet()`
- `build_speed_packet()`
- `build_direction_packet()`
- `build_turn_packet()`
- `build_status_query_packet()`
- `build_ext_status_query_packet()`
- `PacketParser`
- `parse_status_response()`
- `parse_ext_status_response()`

节点不会复制第二套协议实现。默认通过 `protocol_module_path` 参数和仓库相对路径自动寻找 `web/upper`。

## dry_run 测试

默认配置为：

```yaml
dry_run: true
```

启动：

```bash
cd ros/catkin_ws
source devel/setup.bash
roslaunch spraying_car_base base.launch
```

dry-run 模式下：

- 不打开真实串口。
- 不发送真实数据。
- 会打印将要发送的命令含义和十六进制数据包，包括扩展状态查询 `0x06`。
- 可以测试 `/cmd_vel` 映射、超时停车和状态发布。

发布测试命令：

```bash
rostopic pub -1 /cmd_vel geometry_msgs/Twist "linear:
  x: 0.2
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.0"
```

转向测试：

```bash
rostopic pub -1 /cmd_vel geometry_msgs/Twist "linear:
  x: 0.2
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.5"
```

也可以使用调试脚本：

```bash
rosrun spraying_car_tools cmd_vel_test.py _linear_x:=0.2 _angular_z:=0.5
```

停止发布 `/cmd_vel` 后，超过 `cmd_timeout` 会打印安全停车命令。

## 实车测试

实车测试前必须停止 Flask：

```bash
# 先停止 web/upper/start.py
roslaunch spraying_car_base base.launch dry_run:=false port:=/dev/ttyS3
```

原因：当前 Flask 上位机会打开 STM32 控制串口 `/dev/ttyS3`。同一个串口不能被 Flask 和 ROS 同时占用，否则会出现打开失败、写入失败或控制冲突。

实车测试建议：

1. 架空车轮或确保车辆处于安全区域。
2. 确认急停可用。
3. 停止 `web/upper/start.py`。
4. 以 `dry_run:=false` 启动节点。
5. 先发布低速 `/cmd_vel`。
6. 确认 `cmd_timeout` 停车有效。

## /cmd_vel 映射规则

输入：

- `linear.x`：前后速度意图。
- `angular.z`：转向意图。

速度和方向：

- `abs(linear.x) < stop_linear_threshold`：`direction=0`，`speed_duty=min_speed_duty`。
- `linear.x > 0`：`direction=1`，按 `abs(linear.x)` 线性映射到 `min_speed_duty..max_speed_duty`。
- `linear.x < 0`：`direction=2`，按 `abs(linear.x)` 线性映射到 `min_speed_duty..max_speed_duty`。

转向：

- `angular.z = 0`：`turn_position=center_turn_position`，默认 51。
- `angular.z > 0` 或 `< 0`：按 `max_angular_z` 归一化后映射到 `min_turn_position..max_turn_position`。
- `turn_direction_sign` 可设置为 `1` 或 `-1`，用于实车转向方向反了时整体反转。

所有输出都会限幅：

- `speed_duty: 1..102`
- `direction: 0/1/2`
- `turn_position: 1..101`

当前 `max_speed_duty` 默认保守设为 40。速度档位还没有真实车速标定，后续实车标定后再提高。

## 当前局限

- 旧状态包 `0x05` 和扩展状态包 `0x07` 并存，不能直接替换旧 `0x05`。
- 扩展状态包能返回转向命令、转向目标编码器、转向编码器读数和控制模式。
- `turn_encoder_position` 当前来自 TIM5 转向编码器，但底层读取仍是 `int16_t`，后续需要改造为完整 `int32_t` 计数。
- `battery_mv = 0`：当前无电池 ADC 采集。
- `fault_code = 0`：当前无故障码系统。
- `safety_state = 0`：当前无独立硬件急停输入。
- 仍无真实轮速。
- 仍不发布正式 `/odom`。
- 速度档位未标定。

## 下一阶段

下一阶段若要发布正式 `/odom`，至少还需要：

- 真实轮速或轮速编码器。
- 可靠速度反馈。
- 将转向编码器底层读数扩展为可靠 `int32_t` 计数。
- 电池电压。
- 液位。
- 故障码。
- 更可靠的 CRC 校验。

扩展后再在 `spraying_car_base` 中发布正式 `/odom` 和 `spraying_car_msgs/VehicleState.msg`。
