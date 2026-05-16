# L1RM 与 point_lio 建图启动说明

本文档记录阶段 6 的 L1RM、unilidar_sdk、point_lio_unilidar 启动流程。当前只做雷达驱动和建图封装，不做自动驾驶、move_base、waypoint、PCD 转 2D 地图，也不做 Flask 与 ROS 融合。

## 启动顺序

1. 启动 ROS master：

```bash
roscore
```

2. 启动车体模型和 L1RM：

```bash
roslaunch spraying_car_bringup bringup_lidar.launch lidar_port:=/dev/ttyUSB0
```

3. 检查原始雷达与 IMU：

```bash
rostopic list | grep -E "unilidar|cloud|imu"
rostopic echo -n 1 /unilidar/cloud | grep frame_id
rostopic echo -n 1 /unilidar/imu | grep frame_id
rostopic hz /unilidar/cloud
rostopic hz /unilidar/imu
```

4. 启动建图：

```bash
roslaunch spraying_car_bringup bringup_slam.launch lidar_port:=/dev/ttyUSB0
```

5. 检查 point_lio 输出：

```bash
rostopic list | grep -E "unilidar|pointlio|cloud|imu|odom"
rostopic echo -n 1 /pointlio/odom
rosrun tf view_frames
```

## L1RM 初始化注意

- 启动时车辆保持静止，给 IMU 初始化留出稳定状态。
- 雷达不要接不稳定 USB 口。
- Orange Pi 5B 上避免使用不稳定 OHCI USB 口，优先使用实测稳定的 USB 口。
- 普通 GPS 不是 RTK，不能作为高精度建图定位来源。

## 串口与设备名冲突

- L1RM 默认可能是 `/dev/ttyUSB0`。
- GPS 默认也可能是 `/dev/ttyUSB0`。
- GPS 串口当前尚未固定。
- 启动前必须确认哪个设备是 L1RM，哪个设备是 GPS。
- 后续建议通过 udev 固定：
  - `/dev/spraying_car_lidar`
  - `/dev/spraying_car_gps`

## Frame 现状

Unitree 驱动原始配置默认是：

- 点云 frame：`unilidar_lidar`
- IMU frame：`unilidar_imu`

本项目 wrapper 默认覆盖为：

- `/unilidar/cloud`：期望 `frame_id=lidar_link`
- `/unilidar/imu`：期望 `frame_id=imu_link`

point_lio 输入：

- 点云：`/unilidar/cloud`
- IMU：`/unilidar/imu`

point_lio 当前源码输出：

- `/pointlio/odom`：父 frame `camera_init`，子 frame `aft_mapped`
- `/pointlio/cloud_registered`：`camera_init`
- `/pointlio/laser_map`：`camera_init`
- `/pointlio/path`：`camera_init`
- TF：`camera_init -> aft_mapped`

当前 L1RM 输入 frame 已按 launch 参数对齐到 `lidar_link/imu_link`。point_lio 输出仍是 `camera_init/aft_mapped`，尚未整理进标准 `map/odom/base_link` 树。本阶段不伪造 `map -> odom` 或 `odom -> base_link`，也不把 `/pointlio/odom` 强行接成正式 `/odom`。

RViz 配置 `spraying_car_slam/rviz/slam.rviz` 的 Fixed Frame 先设为 `camera_init`，便于观察 point_lio 的地图、轨迹和里程计。如果只验证原始 L1RM 和 RobotModel，可以临时把 Fixed Frame 改为 `base_link` 或 `base_footprint`。

## 常见检查命令

```bash
rostopic list | grep -E "unilidar|pointlio|cloud|imu|odom"
rostopic echo -n 1 /unilidar/cloud
rostopic echo -n 1 /unilidar/imu
rostopic hz /unilidar/cloud
rostopic hz /unilidar/imu
rostopic echo -n 1 /pointlio/odom
rosrun tf view_frames
```

## 常见问题

没有 `/unilidar/cloud`：
检查 L1RM 供电、USB 连接、`lidar_port` 是否正确，以及 GPS 是否抢占了 `/dev/ttyUSB0`。

没有 `/unilidar/imu`：
先确认驱动节点是否启动，再确认 L1RM 型号/配置是否启用了 IMU 输出。

`frame_id` 不一致：
检查 `spraying_car_slam/launch/unilidar.launch` 中的 `lidar_frame`、`imu_frame` 参数。不要直接改第三方源码。

point_lio 不动或发散：
启动时保持车辆静止，检查 `/unilidar/cloud` 和 `/unilidar/imu` 频率，确认 IMU 数据时间戳稳定，确认雷达安装外参还只是占位值。

RViz 显示 Fixed Frame 错误：
观察 point_lio 输出时使用 `camera_init`；只看车体和原始雷达时可用 `base_link` 或 `base_footprint`。标准导航阶段后续再整理为 `map/odom/base_link`。

USB 串口设备名变化：
使用 `ls -l /dev/serial/by-id/` 查找稳定设备 ID，后续写 udev 规则。

## 本阶段不做

- 不做自动驾驶。
- 不启动 move_base、TEB、waypoint。
- 不发布 `/cmd_vel`。
- 不让 SLAM 直接控制底盘。
- 不做 PCD 转 2D 地图。
- 不做 Flask 与 ROS 融合。
- 不修改 STM32、Vue、Flask 或 third_party 源码。
