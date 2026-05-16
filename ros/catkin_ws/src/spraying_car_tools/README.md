# spraying_car_tools

ROS 调试工具包，后续放串口测试、`/cmd_vel` 测试、里程计检查、急停测试和航点记录脚本。

当前状态：

- 已补齐 catkin 包结构。
- 已预留 `scripts/`、`launch/`、`config/`。
- 已提供 `scripts/cmd_vel_zero.py`，只发布一次零速度 Twist，用于调试停车链路。
- 已提供 `scripts/cmd_vel_test.py`，用于向 `/cmd_vel` 发布一次测试速度。

示例：

```bash
rosrun spraying_car_tools cmd_vel_test.py _linear_x:=0.2 _angular_z:=0.5
```

开发边界：

- 调试脚本不得绕过 `spraying_car_base` 直接操作 STM32 串口。
- 可能驱动车辆的脚本必须默认停车，并要求显式参数开启。
