# spraying_car_base

ROS1 Noetic 底盘桥接包，负责把 `/cmd_vel` 转换为 STM32 当前旧串口协议。

控制链路：

```text
/cmd_vel -> spraying_car_base_node -> vehicle_protocol.py -> STM32 -> 底盘执行机构
```

当前节点：

- `scripts/vehicle_base_node.py`
- 节点名：`spraying_car_base_node`
- 订阅：`/cmd_vel` (`geometry_msgs/Twist`)
- 发布：`/spraying_car/base_state` (`std_msgs/String` JSON)
- 默认 `dry_run: true`，不会打开真实串口。
- 优先查询扩展状态 `CMD_EXT_STATUS_QUERY=0x06`。
- 若长期没有扩展状态 `CMD_EXT_STATUS_RESPONSE=0x07`，回退查询旧状态 `CMD_STATUS_QUERY=0xFF`。

启动：

```bash
roslaunch spraying_car_base base.launch
```

实车串口测试前必须先停止 Flask：

```bash
# 先停止 web/upper/start.py
roslaunch spraying_car_base base.launch dry_run:=false port:=/dev/ttyS3
```

原因：Flask 和 ROS 不能同时占用 `/dev/ttyS3`。

当前限制：

- 不发布正式 `/odom`。
- 旧状态包 `0x05` 和扩展状态包 `0x07` 并存，旧 4 字节格式保持兼容。
- 扩展状态已回传转向命令、转向目标编码器、转向编码器读数和控制模式。
- `turn_encoder_position` 来自现有 TIM5 转向编码器读取，但底层仍是 `int16_t` 读数，后续需改造。
- `battery_mv`、`fault_code`、`safety_state` 当前是占位 0。
- 当前仍没有真实轮速。
- 速度档位只是线性映射，尚未做实车速度标定。
- 后续需要轮速编码器或可靠速度反馈后再实现里程计。
