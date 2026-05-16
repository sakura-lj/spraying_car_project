# spraying_car_bringup

总启动包，用来聚合自研 ROS 包的 launch 文件。这里不放复杂业务逻辑，只提供常用组合入口。

## 当前入口

- `launch/bringup.launch`：阶段早期入口，默认不启动底盘控制。
- `launch/bringup_lidar.launch`：启动车体描述模型和 L1RM 驱动，用于先验证雷达。
- `launch/bringup_slam.launch`：启动车体描述模型、L1RM 驱动和 point_lio 建图。
- `launch/bringup_localization.launch`：启动车体描述、可选 L1RM、可选 point_lio，以及 point_lio frame 标准化桥接。

推荐顺序：

1. 先运行 `bringup_lidar.launch`，确认 `/unilidar/cloud` 和 `/unilidar/imu` 正常。
2. 再运行 `bringup_slam.launch`，确认 point_lio 输出 `/pointlio/odom`、`/pointlio/cloud_registered`、`/pointlio/path`。

## 示例

```bash
roslaunch spraying_car_bringup bringup_lidar.launch lidar_port:=/dev/ttyUSB0
```

```bash
roslaunch spraying_car_bringup bringup_slam.launch lidar_port:=/dev/ttyUSB0 use_rviz:=false
```

```bash
roslaunch spraying_car_bringup bringup_localization.launch bridge_publish_tf:=false
```

如果 GPS 也被识别为 `/dev/ttyUSB0`，需要先确认实际 L1RM 设备名，后续建议使用 udev 固定设备名。

## 安全边界

- 不启动 Flask。
- 不启动 `spraying_car_base`。
- 不启动 move_base、TEB、waypoint。
- 不发布 `/cmd_vel`。
- 不操作 STM32 串口。
- `bringup_localization.launch` 默认不发布 `odom -> base_link`，需要实测确认后显式设置 `bridge_publish_tf:=true`。
