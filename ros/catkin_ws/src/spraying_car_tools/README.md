# spraying_car_tools

ROS 调试工具包，放串口测试、`/cmd_vel` 测试、里程计检查、导航依赖检查、急停测试和航点记录脚本。

当前状态：

- 已补齐 catkin 包结构。
- 已预留 `scripts/`、`launch/`、`config/`。
- 已提供 `scripts/cmd_vel_zero.py`，只发布一次零速度 Twist，用于调试停车链路。
- 已提供 `scripts/cmd_vel_test.py`，用于向 `/cmd_vel` 发布测试速度，默认低速并在结束后发布 0 速度。
- 已提供 `scripts/suspended_base_direction_test.py`，用于轮子离地的短时方向验证，默认要求人工确认字符串。
- 已提供 `scripts/check_navigation_dependencies.py`，只读检查 ROS 导航依赖。
- 已提供 `scripts/check_navigation_runtime.py`，只读检查导航运行时话题、TF 和 frame。
- 已提供 `scripts/mock_slam_odom.py` 和 `scripts/mock_lidar_cloud.py`，只用于开发机 mock 测试，禁止实车使用。mock odom 会发布测试用 `/slam_odom` 和 `/pointlio/odom`，mock lidar 会发布测试用 `/unilidar/cloud` 和 `/unilidar/imu`。
- 已提供 `scripts/stm32_cdc_monitor.py`，只读监控 STM32 USB CDC 调试口，默认 `/dev/ttyACM0`，禁止用于车辆控制。
- 已提供 `scripts/base_state_verification_test.py`，通过短时 `/cmd_vel` 和 `/spraying_car/base_state` 验证 STM32 软件状态，不证明物理方向。
- 已提供 `scripts/check_serial_devices.py`，只读列出 `/dev/ttyS*`、`/dev/ttyUSB*`、`/dev/ttyACM*` 设备。

示例：

```bash
rosrun spraying_car_tools cmd_vel_test.py _linear_x:=0.2 _angular_z:=0.5
```

预设测试：

```bash
rosrun spraying_car_tools cmd_vel_test.py _preset:=stop
rosrun spraying_car_tools cmd_vel_test.py _preset:=forward_slow
rosrun spraying_car_tools cmd_vel_test.py _preset:=backward_slow
rosrun spraying_car_tools cmd_vel_test.py _preset:=left_slow
rosrun spraying_car_tools cmd_vel_test.py _preset:=right_slow
```

架空方向验证：

```bash
rosrun spraying_car_tools suspended_base_direction_test.py
```

该脚本只发布 `/cmd_vel`，不直接操作 STM32 串口。默认要求输入 `I_UNDERSTAND_WHEELS_ARE_OFF_GROUND` 后才会发布非零速度。

CDC + base_state 状态验证：

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py _port:=/dev/ttyACM0 _raw_hex:=true _ascii:=true
rosrun spraying_car_tools base_state_verification_test.py
```

`stm32_cdc_monitor.py` 使用只读方式打开 `/dev/ttyACM0`，可同时显示 ASCII 和 HEX，可通过 `_output_file:=...` 保存日志。`base_state_verification_test.py` 只发布 `/cmd_vel` 并订阅 `/spraying_car/base_state`，默认要求输入 `I_UNDERSTAND_THIS_SENDS_REAL_STM32_COMMANDS`。

```bash
rosrun spraying_car_tools check_navigation_dependencies.py
rosrun spraying_car_tools check_navigation_runtime.py
```

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py _port:=/dev/ttyACM0 _baud:=115200 _max_lines:=20
python3 ros/catkin_ws/src/spraying_car_tools/scripts/stm32_cdc_monitor.py --port /dev/ttyACM0 --baud 115200
rosrun spraying_car_tools check_serial_devices.py
```

开发边界：

- 调试脚本不得绕过 `spraying_car_base` 直接操作 STM32 串口。
- 可能驱动车辆的脚本必须默认停车，并要求显式参数开启。
- mock 节点只允许开发机验证配置，禁止实车导航使用。
- `/dev/ttyACM0` 只用于 STM32 USB CDC 调试输出监控，不发送控制命令。
- 车辆控制串口仍然是 `/dev/ttyS3`。
