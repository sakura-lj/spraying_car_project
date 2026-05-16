# spraying_car_localization

喷药车定位与 frame 标准化包。当前包不实现 SLAM 算法，不修改 point_lio，只把 point_lio 输出整理成项目后续导航更容易使用的标准话题。

## 当前节点

- `point_lio_frame_bridge.py`
  - 输入：`/pointlio/odom` (`nav_msgs/Odometry`)
  - 输出：`/slam_odom` (`nav_msgs/Odometry`)
  - 可选 TF：`odom -> base_link`
  - 默认 `publish_tf=false`
- `check_point_lio_frames.py`
  - 检查 `/unilidar/cloud`、`/unilidar/imu`、`/pointlio/odom` 和基础 TF。

## 启动

只启动桥接节点：

```bash
roslaunch spraying_car_localization point_lio_bridge.launch
```

确认 frame 后可显式打开 TF：

```bash
roslaunch spraying_car_localization point_lio_bridge.launch publish_tf:=true
```

聚合启动：

```bash
roslaunch spraying_car_bringup bringup_localization.launch bridge_publish_tf:=false
```

## 处理方式

默认假设 point_lio 的位姿表示 `lidar_link` 或雷达内置 IMU 主体在 point_lio world frame 下的位姿。节点通过 TF 查询 `lidar_link -> base_link`，将输入 pose 转为 `base_link` pose，然后发布为：

```text
/slam_odom
header.frame_id: odom
child_frame_id: base_link
```

如果找不到 `base_link -> lidar_link` 静态 TF，节点会报警并跳过该帧，不会崩溃。需要先启动 `spraying_car_description/description.launch`。

## 当前不做

- 不发布 `map -> odom`。
- 不发布 `map -> base_link`。
- 不伪造 wheel odom。
- 不做 AMCL、RTK、robot_localization 融合。
- 不做基于旧 PCD/2D 地图的重定位。
- 不让 SLAM 输出控制底盘。
