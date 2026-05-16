# move_base / TEB 第一版导航配置

阶段 8B 已建立第一版 `move_base` + TEB 配置。当前能力只适合 dry-run、RViz 和低速受控实验，不代表可以直接实车自动驾驶。

## 当前导航能力

- 已创建 `move_base`/TEB 配置。
- Live SLAM 模式可用于低速 dry-run 或受控测试。
- Saved map 模式只是配置骨架，当前缺少重定位，不保证闭环。
- `move_base` 只发布 `/cmd_vel`。
- 底盘控制链路只能是 `/cmd_vel -> spraying_car_base -> STM32`。

## 为什么不能直接实车

- 当前无物理急停开关，只有软件急停。
- 无轮速编码器，硬件无法安装，不能使用 wheel odom。
- 普通 GPS 不是 RTK，不能提供高精度定位。
- point_lio frame 与 `/slam_odom` 方向仍需实机确认。
- 速度档位 `1..102` 未实车标定。
- L1RM 雷达外参仍未实测。
- 果园地面、草、枝叶会影响点云障碍物层。

## 依赖

可能需要安装：

```bash
sudo apt install ros-noetic-navigation
sudo apt install ros-noetic-teb-local-planner
sudo apt install ros-noetic-map-server
sudo apt install ros-noetic-global-planner
```

本项目不会自动安装 apt 包。

## Live SLAM Dry-run 测试

启动：

```bash
roslaunch spraying_car_navigation navigation_live_slam.launch base_dry_run:=true use_rviz:=true
```

检查：

```bash
rostopic list | grep -E "slam_odom|cmd_vel|move_base|costmap|unilidar"
rostopic echo -n 1 /slam_odom
rostopic echo /cmd_vel
```

在 RViz 中发送 `2D Nav Goal`，观察：

- move_base 是否收到 goal。
- global/local costmap 是否发布。
- TEB 是否发布 local plan。
- move_base 是否输出 `/cmd_vel`。
- `spraying_car_base` 是否以 dry-run 打印命令。

## 实车低速测试前检查

- Flask 已停止，避免抢 `/dev/ttyS3`。
- 遥控器可随时接管。
- 测试场地空旷、低速、有人看护。
- `base_dry_run` 必须显式设为 `false`。
- `max_speed_duty` 保持低值。
- 软件急停可用。
- `bridge_publish_tf:=true` 前已经确认 `/slam_odom` 和 TF 方向正确。

实车启动示例：

```bash
roslaunch spraying_car_navigation navigation_live_slam.launch base_dry_run:=false bridge_publish_tf:=true use_rviz:=true
```

## Saved Map 模式

启动骨架：

```bash
roslaunch spraying_car_navigation navigation_saved_map.launch \
  map_yaml:=/home/orangepi/spraying_car_project/maps/grid/orchard_test_area_20260516_v01.yaml \
  base_dry_run:=true
```

当前限制：

- 没有 AMCL 2D 激光重定位。
- 没有 RTK。
- 没有基于 PCD 地图的重定位。
- 没有可靠 `map -> odom` 来源。
- 如果没有 `map -> odom`，move_base 可能无法正常工作，这是预期限制。

`fake_map_to_odom:=true` 只允许 RViz/debug，禁止实车使用。

## 常见问题

No transform from base_link to odom：
确认 `point_lio_frame_bridge` 已启动，并且在实测确认后开启了 `bridge_publish_tf:=true`。

No map received：
saved map 模式下确认 `map_yaml` 路径正确，且安装了 `map_server`。

Costmap obstacle layer 没有数据：
确认 `/unilidar/cloud` 正常发布，`frame_id` 是 `lidar_link`，并且 TF 中存在 `base_link -> lidar_link`。

TEB 输出原地转圈但车辆不能原地旋转：
检查 TEB 参数，当前已设置 Ackermann 近似约束和 `min_turning_radius=1.5`，但参数仍需实车调试。

move_base 不输出 `/cmd_vel`：
检查 goal、TF、costmap、planner 状态，以及 `/slam_odom` 是否存在。

`/cmd_vel` 输出但 `spraying_car_base` 没反应：
确认 `spraying_car_base` 已启动，默认 dry-run 只打印命令；实车测试需显式 `base_dry_run:=false`，且 Flask 必须停止。

local costmap 把地面当障碍：
调整 `min_obstacle_height`、`max_obstacle_height`，并实测 L1RM 外参。

## 阶段 8C 验证流程

阶段 8C 不新增自动驾驶能力，目标是检查依赖、话题、TF 和 dry-run 控制链路。

### 依赖安装检查

运行：

```bash
source /opt/ros/noetic/setup.bash
source ros/catkin_ws/devel/setup.bash
rosrun spraying_car_tools check_navigation_dependencies.py
```

该脚本检查：

- ROS master 是否可连接。
- `ROS_PACKAGE_PATH` 是否包含当前 catkin workspace。
- `spraying_car_base`、`spraying_car_description`、`spraying_car_slam`、`spraying_car_localization`、`spraying_car_navigation`。
- `move_base`、`teb_local_planner`、`map_server`、`global_planner`、`costmap_2d`、`nav_core`。
- `/opt/ros/noetic/setup.bash` 和 `ros/catkin_ws/devel/setup.bash`。

缺少依赖时按需安装：

```bash
sudo apt update
sudo apt install ros-noetic-navigation ros-noetic-teb-local-planner ros-noetic-map-server ros-noetic-global-planner
```

脚本只检查，不自动安装。

### 半实机 dry-run 验证

1. 确认 `base_dry_run=true`。

2. 启动 L1RM：

```bash
roslaunch spraying_car_bringup bringup_lidar.launch
```

3. 检查雷达和 IMU：

```bash
rostopic echo -n 1 /unilidar/cloud | grep frame_id
rostopic echo -n 1 /unilidar/imu | grep frame_id
```

4. 启动 localization：

```bash
roslaunch spraying_car_bringup bringup_localization.launch bridge_publish_tf:=false
```

5. 检查 point_lio 和 bridge：

```bash
rostopic echo -n 1 /pointlio/odom
rostopic echo -n 1 /slam_odom
rosrun tf view_frames
```

6. 确认是否发布 `odom -> base_link`。只有确认 point_lio frame、`/slam_odom` 方向和 L1RM 外参后，才允许测试：

```bash
roslaunch spraying_car_bringup bringup_localization.launch bridge_publish_tf:=true
```

7. 启动导航 dry-run：

```bash
roslaunch spraying_car_navigation navigation_dryrun_check.launch base_dry_run:=true use_rviz:=true
```

8. RViz 中发 `2D Nav Goal`。

9. 检查 `/cmd_vel`：

```bash
rostopic echo /cmd_vel
```

10. 检查 `spraying_car_base` dry-run 输出，确认只打印 STM32 控制意图，不真实动车。

11. 运行运行时检查：

```bash
rosrun spraying_car_tools check_navigation_runtime.py _expect_odom_to_base_tf:=true
```

### 无雷达开发机 mock 测试

仅用于开发机验证 launch、move_base 参数和 `/cmd_vel` 链路，禁止实车使用：

```bash
roslaunch spraying_car_navigation navigation_mock_test.launch base_dry_run:=true use_rviz:=true
```

mock 节点：

- `mock_slam_odom.py` 发布测试用 `/slam_odom`、`/pointlio/odom`，并发布 `odom -> base_footprint`，再通过 URDF 的 `base_footprint -> base_link` 形成 `odom -> base_link`。
- `mock_lidar_cloud.py` 发布测试用 `/unilidar/cloud` 和 `/unilidar/imu`。

这些节点不代表真实定位或真实障碍物，不能用于实车导航。

### /cmd_vel dry-run 验证

只推荐在 `spraying_car_base dry_run=true` 时使用：

```bash
rosrun spraying_car_tools cmd_vel_test.py _linear_x:=0.1 _angular_z:=0.0 _stop_after_test:=true
```

脚本只发布 `/cmd_vel`，不直接操作 STM32 串口。

### Rosbag 录制建议

```bash
rosbag record -O bags/navigation_dryrun_YYYYMMDD_HHMMSS.bag \
/tf /tf_static \
/unilidar/cloud /unilidar/imu \
/pointlio/odom /slam_odom \
/cmd_vel /spraying_car/base_state \
/move_base/status \
/move_base/global_costmap/costmap \
/move_base/local_costmap/costmap
```

本项目不自动启动 rosbag。

### 实车低速测试前置条件

- Flask 必须停止，避免抢 `/dev/ttyS3`。
- 遥控器必须可接管。
- 空旷场地。
- 有人看护。
- 软件急停已验证。
- `base_dry_run=false` 必须由人工显式设置。
- `max_speed_duty` 必须保持低值。
- `/cmd_vel` 前进/后退方向已经架空验证。
- 转向方向已经架空验证。
- costmap 没有把地面大面积标为障碍。

### 禁止事项

- 禁止在未验证 TF 时实车导航。
- 禁止在未确认 `/cmd_vel` 方向时实车导航。
- 禁止使用 `fake_map_to_odom` 做实车导航。
- 禁止使用 mock 节点做实车导航。
- 禁止让导航直接操作 STM32 串口。
- 禁止绕过 `/cmd_vel -> spraying_car_base -> STM32` 链路。

### 阶段 8C 常见错误

缺少 `move_base`：
安装 `ros-noetic-navigation`。

缺少 `teb_local_planner`：
安装 `ros-noetic-teb-local-planner`。

No transform from `base_link` to `odom`：
确认 `point_lio_frame_bridge` 已启动，且需要导航测试时 `bridge_publish_tf:=true`。

`/slam_odom` 没数据：
确认 `/pointlio/odom` 有数据，并检查 bridge 日志是否提示找不到 `lidar_link -> base_link` TF。

`/cmd_vel` 没输出：
检查 move_base 是否收到 goal、TF 是否完整、costmap 是否正常、TEB 是否规划失败。

costmap 没有 obstacle layer：
确认 `/unilidar/cloud` 存在，frame 是 `lidar_link`，且 `base_link -> lidar_link` TF 可用。

`/unilidar/cloud frame_id` 不是 `lidar_link`：
检查 `spraying_car_slam/launch/unilidar.launch` 的 `lidar_frame` 参数。

TEB 规划失败：
检查 `min_turning_radius`、障碍物膨胀、目标是否在障碍物内，以及 TF 是否跳变。

`spraying_car_base` 没有订阅 `/cmd_vel`：
确认 `roslaunch spraying_car_base base.launch dry_run:=true` 或导航 launch 中 `use_base:=true`。

Flask 占用 `/dev/ttyS3`：
实车测试前停止 `web/upper/start.py`。

## 本阶段不做

- 不实现 waypoint 路线。
- 不实现 Web 自动驾驶入口。
- 不实现 `CONTROL_BACKEND=ros`。
- 不实现 saved map 重定位。
- 不做真实速度标定。
- 不发布 `map -> odom`。
- 不伪造 wheel odom。

## 阶段 8D mock/dry-run 验证结果

验证日期：2026-05-16。

### 导航依赖安装状态

当前环境未完成导航依赖安装。执行 `sudo apt update` 时，系统要求交互式 sudo 密码：

```text
sudo: a terminal is required to read the password
```

因此本阶段没有强行安装依赖。需要人工在 Orange Pi 终端执行：

```bash
sudo apt update
sudo apt install ros-noetic-navigation ros-noetic-teb-local-planner ros-noetic-map-server ros-noetic-global-planner
```

### 依赖检查摘要

`check_navigation_dependencies.py` 最终检查结果：

- `spraying_car_base`：OK
- `spraying_car_description`：OK
- `spraying_car_slam`：OK
- `spraying_car_localization`：OK
- `spraying_car_navigation`：OK
- `move_base`：MISSING
- `teb_local_planner`：MISSING
- `map_server`：MISSING
- `global_planner`：MISSING
- `costmap_2d`：MISSING
- `nav_core`：MISSING
- `roscore connection`：MISSING，当前没有运行 roscore

### mock launch 启动结果

`navigation_mock_test.launch use_rviz:=false` 可以完成 launch 文件展开，并能启动：

- `robot_state_publisher`
- `mock_slam_odom`
- `mock_lidar_cloud`
- `spraying_car_base_node`

但由于 `move_base` 包缺失，启动时报错：

```text
ERROR: cannot launch node of type [move_base/move_base]: move_base
```

因此当前还不能验证 TEB 插件加载、global/local costmap 发布，也不能由 move_base 产生 `/cmd_vel`。

### runtime 检查摘要

在 mock launch 短时运行期间，`check_navigation_runtime.py` 检查结果摘要：

- `/unilidar/cloud`：OK，frame_id=`lidar_link`
- `/unilidar/imu`：OK，frame_id=`imu_link`
- `/pointlio/odom`：OK，mock only
- `/slam_odom`：OK，`header.frame_id=odom`，`child_frame_id=base_link`
- `/spraying_car/base_state`：OK
- `/cmd_vel`：存在订阅者 `/spraying_car_base_node`
- `base_footprint -> base_link`：OK
- `base_link -> lidar_link`：OK
- `lidar_link -> imu_link`：OK
- `odom -> base_link`：OK，经 `odom -> base_footprint -> base_link` 可达
- `/move_base/status`：FAIL，原因是 `move_base` 未安装
- `/move_base/global_costmap/costmap`：FAIL，原因是 `move_base` 未安装
- `/move_base/local_costmap/costmap`：FAIL，原因是 `move_base` 未安装
- `/cmd_vel` publisher：FAIL，原因是 `move_base` 未安装，当前没有导航节点发布速度

### /cmd_vel dry-run 链路

在只启动 `spraying_car_base dry_run=true` 的情况下，执行：

```bash
rosrun spraying_car_tools cmd_vel_test.py _linear_x:=0.1 _angular_z:=0.0 _duration:=1.0 _rate:=5.0 _stop_after_test:=true
```

验证结果：

- `spraying_car_base_node` 明确打印 `dry_run=true: no real serial port will be opened`
- `/cmd_vel linear.x=0.1 angular.z=0.0` 被映射为 `direction=1`、`speed_duty=8`、`turn_position=51`
- 测试结束后发布 0 速度，被映射为 `direction=0`、`speed_duty=1`、`turn_position=51`
- 节点超时和关闭时会发送 dry-run 安全停车意图
- 未打开 `/dev/ttyS3`

### 仍未解决的问题

- 需要人工安装 `move_base`、`teb_local_planner`、`map_server`、`global_planner` 及其依赖。
- 安装前无法确认 TEB 插件是否成功加载。
- 安装前无法确认 global/local costmap 是否发布。
- 安装前无法确认 move_base 是否能产生 `/cmd_vel`。

### 进入半实机验证前待办

1. 安装导航依赖。
2. 重新运行 `check_navigation_dependencies.py`，除 roscore 外依赖项应全部 OK。
3. 启动 `navigation_mock_test.launch use_rviz:=false`，确认 move_base 无 fatal error。
4. 运行 `check_navigation_runtime.py`，确认 `/move_base/status` 和两个 costmap 均 OK。
5. 确认 move_base 能产生 `/cmd_vel`，且 `spraying_car_base dry_run=true` 能接收。
6. 再进入 L1RM/point_lio 半实机 dry-run 验证。

## 阶段 8D 复测结果

验证日期：2026-05-16。

### 导航依赖最终检查

人工安装导航依赖后，`check_navigation_dependencies.py` 复测结果：

- `spraying_car_base`：OK
- `spraying_car_description`：OK
- `spraying_car_slam`：OK
- `spraying_car_localization`：OK
- `spraying_car_navigation`：OK
- `move_base`：OK
- `teb_local_planner`：OK
- `map_server`：OK
- `global_planner`：OK
- `costmap_2d`：OK
- `nav_core`：OK
- `roscore connection`：MISSING，原因是检查时未单独启动 roscore；`roslaunch` 会自动启动 roscore

### mock 导航启动结果

`navigation_mock_test.launch use_rviz:=false` 已能完整启动：

- `robot_state_publisher`：OK
- `mock_slam_odom`：OK，仅 mock 测试
- `mock_lidar_cloud`：OK，仅 mock 测试
- `spraying_car_base_node`：OK，`dry_run=true`
- `move_base`：OK
- `global_planner/GlobalPlanner`：OK
- `teb_local_planner/TebLocalPlannerROS`：OK
- global costmap：OK
- local costmap：OK

启动日志确认：

- `global_costmap: Using plugin "obstacle_layer"`
- `global_costmap: Using plugin "inflation_layer"`
- `local_costmap: Using plugin "obstacle_layer"`
- `local_costmap: Using plugin "inflation_layer"`
- `Created local_planner teb_local_planner/TebLocalPlannerROS`
- `Footprint model 'polygon' loaded for trajectory optimization`
- `odom received!`

存在两个可接受 WARN：

- `global_costmap: Pre-Hydro parameter "static_map" unused since "plugins" is provided`
- `local_costmap: Pre-Hydro parameter "static_map" unused since "plugins" is provided`

原因：当前 costmap 使用 plugin 配置，`static_map` 是兼容参数，不影响 mock dry-run 验证。后续如需要可拆分 live/saved-map costmap 参数进一步减少警告。

### runtime 检查复测摘要

`check_navigation_runtime.py` 复测通过：

- `/unilidar/cloud`：OK，publisher=1，subscriber=1，frame_id=`lidar_link`
- `/unilidar/imu`：OK，frame_id=`imu_link`
- `/pointlio/odom`：OK，mock only
- `/slam_odom`：OK，`header.frame_id=odom`，`child_frame_id=base_link`
- `/cmd_vel`：OK，publisher=`/move_base`，subscriber=`/spraying_car_base_node`
- `/spraying_car/base_state`：OK
- `/move_base/status`：OK
- `/move_base/global_costmap/costmap`：OK
- `/move_base/local_costmap/costmap`：OK
- `base_footprint -> base_link`：OK
- `base_link -> lidar_link`：OK
- `lidar_link -> imu_link`：OK
- `odom -> base_link`：OK，经 mock 的 `odom -> base_footprint` 与 URDF 的 `base_footprint -> base_link` 可达

WARN：

- `odom -> base_link is only required when bridge_publish_tf=true`

说明：这是检查脚本的提示，不是错误。mock launch 中允许测试用 `odom -> base_footprint`，正式 live launch 仍需由 localization bridge 在确认 frame 后提供。

### /cmd_vel dry-run 复测

在 `navigation_mock_test.launch` 运行期间执行：

```bash
rosrun spraying_car_tools cmd_vel_test.py _linear_x:=0.1 _angular_z:=0.0 _duration:=1.0 _rate:=5.0 _stop_after_test:=true
```

验证结果：

- `/cmd_vel` 可发布。
- `spraying_car_base_node` 订阅 `/cmd_vel`。
- `spraying_car_base_node` 日志确认 `dry_run=true: no real serial port will be opened`。
- `/cmd_vel linear.x=0.1 angular.z=0.0` 映射为 `direction=1`、`speed_duty=8`、`turn_position=51`。
- 测试结束后 0 速度映射为 `direction=0`、`speed_duty=1`、`turn_position=51`。
- 未打开 `/dev/ttyS3`。
- 未向 `/dev/ttyACM0` 写入任何数据。

### STM32 USB CDC 调试口

新增只读监控工具：

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py _port:=/dev/ttyACM0 _baud:=115200 _max_lines:=20
```

或：

```bash
python3 ros/catkin_ws/src/spraying_car_tools/scripts/stm32_cdc_monitor.py --port /dev/ttyACM0 --baud 115200
```

边界：

- `/dev/ttyACM0` 是 STM32 USB CDC 调试口，只用于观察日志。
- 车辆控制串口仍然是 `/dev/ttyS3`。
- 监控工具不发送任何控制帧。
- 如果权限不足，检查设备权限或 `dialout` 用户组。

本次只读设备检查结果：

- `/dev/ttyACM0`：存在，role=`STM32 USB CDC debug monitor candidate`
- `/dev/ttyS3`：存在，role=`vehicle control UART candidate`
- `/dev/ttyACM0` by-id：`/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_358437793233-if00`
- `/dev/ttyACM0` 权限：`root:dialout`

本次监控测试结果：

- `stm32_cdc_monitor.py` 可以打开 `/dev/ttyACM0`。
- 8 秒测试窗口内未读到 STM32 文本输出。
- 测试过程没有向 `/dev/ttyACM0` 写入任何数据。

### 仍未解决的问题

- mock 验证通过，但还未接入真实 L1RM、真实 point_lio。
- `odom -> base_link` 在 mock 中由测试节点提供；半实机阶段必须由 `point_lio_frame_bridge` 在 frame 确认后提供。
- 还未做 RViz 人工发送导航目标测试。
- 还未进入实车控制；`base_dry_run` 仍必须保持 `true`。

## 阶段 8E 真实 L1RM + point_lio dry-run 复测结果

验证日期：2026-05-16。

### 设备检查

只读串口和 USB 检查结果：

- `/dev/ttyACM0`：STM32 USB CDC 调试口，Product=`STM32 Virtual ComPort`，SerialNumber=`358437793233`
- `/dev/ttyS3`：STM32 车辆控制串口候选，本阶段未打开
- `/dev/ttyS9`：Orange Pi 平台串口，`DEVPATH=/devices/platform/febc0000.serial/tty/ttyS9`
- `/dev/ttyUSB0`：L1RM 当前连接设备，USB 芯片识别为 Silicon Labs CP2104
- `/dev/serial/by-id/usb-Silicon_Labs_CP2104_USB_to_UART_Bridge_Controller_02C901C5-if00-port0`：指向 `/dev/ttyUSB0`
- `/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_358437793233-if00`：指向 `/dev/ttyACM0`
- `lsusb` 可见 `10c4:ea60 Silicon Labs CP210x UART Bridge`

结论：本次 L1RM 实际设备名为 `/dev/ttyUSB0`。`/dev/ttyACM0` 仍是 STM32 CDC 调试口，不是 L1RM。

### bringup_lidar 测试

执行：

```bash
roslaunch spraying_car_bringup bringup_lidar.launch lidar_port:=/dev/ttyUSB0 use_rviz:=false
```

结果：

- `unitree_lidar_ros_node` 能启动。
- 参数中 `port=/dev/ttyUSB0`、`cloud_frame=lidar_link`、`imu_frame=imu_link`。
- `/unilidar/cloud` 有真实消息，`frame_id=lidar_link`，频率约 `7.6 Hz`。
- `/unilidar/imu` 有真实消息，`frame_id=imu_link`，频率约 `200 Hz`。
- 输入侧 frame 已经与 URDF 中的 `lidar_link`、`imu_link` 对齐。

记录字段：

- L1RM 设备名：`/dev/ttyUSB0`
- `/unilidar/cloud` 是否存在：OK
- `/unilidar/cloud frame_id`：`lidar_link`
- `/unilidar/cloud 频率`：约 `7.6 Hz`
- `/unilidar/imu` 是否存在：OK
- `/unilidar/imu frame_id`：`imu_link`
- `/unilidar/imu 频率`：约 `200 Hz`

### point_lio 与 localization bridge

启动 `bringup_slam.launch` 后，point_lio 能输出真实 odom：

- `/pointlio/odom`：OK，有数据。
- `/pointlio/odom` 频率：约 `7.6 Hz`。
- `/pointlio/odom header.frame_id`：`camera_init`。
- `/pointlio/odom child_frame_id`：`aft_mapped`。
- point_lio 发布 TF：OK，`camera_init -> aft_mapped` 可查询。
- point_lio 初始化日志显示 IMU 初始化完成。

启动 `point_lio_frame_bridge`：

- `publish_tf=false` 时，`/slam_odom` 正常输出，`header.frame_id=odom`，`child_frame_id=base_link`，频率约 `7.6 Hz`。
- `publish_tf=true` 时，bridge 默认发布 `odom -> base_footprint`，再通过 URDF 的 `base_footprint -> base_link` 形成 `odom -> base_link`。
- 这样避免直接发布 `odom -> base_link` 与 URDF 中 `base_footprint -> base_link` 形成双父节点冲突。
- 未发布 `map -> odom`。
- 未伪造 wheel odom。

### navigation live SLAM dry-run

执行：

```bash
roslaunch spraying_car_navigation navigation_live_slam.launch \
  lidar_port:=/dev/ttyUSB0 \
  base_dry_run:=true \
  use_rviz:=false \
  bridge_publish_tf:=true
```

结果：

- `spraying_car_base_node`：OK，日志确认 `dry_run=true: no real serial port will be opened`。
- `move_base`：OK，成功启动。
- `global_planner/GlobalPlanner`：OK。
- `teb_local_planner/TebLocalPlannerROS`：OK。
- global costmap：OK，发布 `/move_base/global_costmap/costmap`。
- local costmap：OK，发布 `/move_base/local_costmap/costmap`。
- costmap obstacle layer 使用 `/unilidar/cloud`。
- `/cmd_vel`：OK，publisher=`/move_base`，subscriber=`/spraying_car_base_node`。
- `/spraying_car/base_state`：OK，`mode=dry_run`，`connected=false` 属于 dry-run 预期。

`check_navigation_runtime.py` 结果摘要：

- `/unilidar/cloud`：OK，frame_id=`lidar_link`。
- `/unilidar/imu`：OK，frame_id=`imu_link`。
- `/pointlio/odom`：OK。
- `/slam_odom`：OK，`header.frame_id=odom`，`child_frame_id=base_link`。
- `base_footprint -> base_link`：OK。
- `base_link -> lidar_link`：OK。
- `lidar_link -> imu_link`：OK。
- `odom -> base_link`：OK，经 `odom -> base_footprint -> base_link` 可达。
- `/move_base/status`：OK。
- global/local costmap：OK。
- `/cmd_vel` publisher/subscriber：OK。

WARN：

- `odom -> base_link is only required when bridge_publish_tf=true`：检查脚本提示，当前本来就是 `bridge_publish_tf=true`。
- `TebLocalPlannerROS: trajectory is not feasible. Resetting planner...`：真实点云下近距离 goal 测试出现，说明 costmap/TEB 参数还需要实地调试。
- `Map update loop missed its desired rate`：点云/costmap 负载下出现，进入实车运动前需要继续关注 CPU 负载和 costmap 参数。

### move_base goal dry-run

发送 `odom` 坐标系下近距离目标：

```bash
rostopic pub -1 /move_base_simple/goal geometry_msgs/PoseStamped "header:
  frame_id: 'odom'
  stamp: {secs: 0, nsecs: 0}
pose:
  position:
    x: 0.8
    y: 0.0
    z: 0.0
  orientation:
    x: 0.0
    y: 0.0
    z: 0.0
    w: 1.0"
```

复测结果：

- `/cmd_vel` 由 `/move_base` 发布。
- `spraying_car_base_node` 能接收 `/cmd_vel`。
- 本次真实点云下 TEB 判断轨迹不可行，`/cmd_vel` 实际采样为 0 速度。
- `spraying_car_base_node` dry-run 打印 0 速度映射：`direction=0`、`speed_duty=1`、`turn_position=51`。
- 节点超时和关闭时继续打印 dry-run 安全停车意图。
- 该结果证明 ROS 话题链路已连通，但还不能说明导航运动方向已经可用。

### STM32 CDC 只读监控

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py _port:=/dev/ttyACM0 _baud:=115200 _max_lines:=50
```

结果：

- `/dev/ttyACM0` 可只读打开。
- 8 秒窗口内未读到 STM32 文本输出。
- 未向 `/dev/ttyACM0` 写入任何数据。
- 未把 `/dev/ttyACM0` 当作控制串口。

### rosbag

已录制短 bag：

```text
bags/l1rm_pointlio_navigation_dryrun_20260516_110249.bag
```

`rosbag info` 摘要：

- duration：约 `7.0 s`
- size：约 `4.6 MB`
- `/unilidar/cloud`：53 条
- `/unilidar/imu`：1420 条
- `/pointlio/odom`：53 条
- `/slam_odom`：53 条
- `/spraying_car/base_state`：139 条
- `/move_base/global_costmap/costmap`：6 条
- `/move_base/local_costmap/costmap`：13 条
- `/tf`、`/tf_static`：已记录

该 bag 用于半实机 dry-run 复查，不提交到 git。由于录制窗口内没有发送导航目标，bag 中没有有效 `/cmd_vel` 消息。

### 安全状态

- 未打开 `/dev/ttyS3` 做真实底盘控制。
- 未向 `/dev/ttyACM0` 写入任何数据。
- 未使用 mock 节点进行 8E 真实链路验证。
- 未使用 `fake_map_to_odom`。
- 未伪造 wheel odom。
- 未修改 STM32、Flask、Vue、third_party。
- `base_dry_run=true` 仍是后续导航 dry-run 的要求。

### 未解决问题

1. TEB 在真实点云近距离 goal 下出现 `trajectory is not feasible`，需要继续调 costmap 高度过滤、膨胀半径、目标位置和 TEB 参数。
2. costmap 更新偶发 missed rate，需要继续观察 Orange Pi 负载和点云处理频率。
3. 真实 `/cmd_vel` 方向还没有通过非零导航输出验证。
4. L1RM 外参仍未实测，当前 `lidar_link` 位置仍是阶段 5 占位值。
5. 进入任何实车运动前，仍必须先做架空 `/cmd_vel` 方向验证，并保持低速、有人看护、遥控器可接管。
