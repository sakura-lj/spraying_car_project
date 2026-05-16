# 定位与 Frame 标准化方案

阶段 8A 的目标是在进入 move_base/TEB 之前，先把 point_lio 的输出整理成项目标准定位输出。当前不做导航、不做重定位、不发布正式 `/odom`，也不控制 STM32。

## 为什么不能直接进入 move_base

- 车辆没有轮速编码器，硬件也无法安装，不能假设存在 wheel odom。
- point_lio 当前输出 frame 是第三方默认的 `camera_init -> aft_mapped`，不是标准 `map/odom/base_link`。
- 阶段 7 的 2D 地图只是保存和转换结果，当前还没有基于旧地图的重定位链路。
- 普通 Modbus GPS 不是 RTK，不能提供高精度全局定位。

## 当前定位方案

第一版使用 `point_lio_unilidar` 作为主要里程计来源：

```text
/pointlio/odom  ->  point_lio_frame_bridge  ->  /slam_odom
```

`point_lio_frame_bridge` 默认：

- 订阅 `/pointlio/odom`。
- 读取原始 `header.frame_id` 和 `child_frame_id`。
- 默认按 `camera_init -> aft_mapped` 理解 point_lio 输出。
- 默认认为 point_lio pose 表示 `lidar_link` 或 L1RM 内置 IMU 主体在 point_lio world frame 下的位姿。
- 使用 URDF/TF 中的 `base_link -> lidar_link` 静态外参，将 lidar 位姿转换为 `base_link` 位姿。
- 发布 `/slam_odom`，`header.frame_id=odom`，`child_frame_id=base_link`。
- `publish_tf=false`，默认不发布动态 TF。
- `publish_tf=true` 时，默认发布 `odom -> base_footprint`，再通过 URDF 的 `base_footprint -> base_link` 形成 `odom -> base_link`。这样避免直接发布 `odom -> base_link` 导致 `base_link` 同时拥有两个父节点。

如果实测确认 frame 和外参正确，可以显式打开：

```bash
roslaunch spraying_car_bringup bringup_localization.launch bridge_publish_tf:=true
```

## 当前不实现

- 不做 AMCL。
- 不做 RTK。
- 不做 robot_localization 融合。
- 不做基于旧 PCD 或 2D 地图的重定位。
- 不发布 `map -> odom`。
- 不发布 `map -> base_link`。
- 不伪造 wheel odom。
- 不让 SLAM 输出控制底盘。

## 两种后续导航实验模式

### A. Live SLAM 模式

L1RM、point_lio 实时运行，`point_lio_frame_bridge` 输出 `/slam_odom`。在实测确认后，可以开启动态 TF，默认发布 `odom -> base_footprint`，用于低速局部导航实验。

这不是基于旧地图的重定位，车辆每次启动仍依赖实时 SLAM 建图/里程计。

### B. Saved Map 模式

使用阶段 7 保存的 2D 地图进行导航前，还需要额外重定位方案。当前项目尚未具备完整能力，不能假装可以直接在旧地图中可靠定位。

## TF 说明

URDF 已提供：

```text
base_footprint
└── base_link
    └── lidar_link
        └── imu_link
```

point_lio 原始输出可能是：

```text
camera_init
└── aft_mapped
```

bridge 的目标输出是：

```text
odom
└── base_footprint
    └── base_link
```

阶段 8A 不发布 `map -> odom`。动态 `odom -> base_footprint` 也默认关闭。

## 验证命令

```bash
rostopic echo -n 1 /unilidar/cloud | grep frame_id
rostopic echo -n 1 /unilidar/imu | grep frame_id
rostopic echo -n 1 /pointlio/odom
rosrun spraying_car_localization check_point_lio_frames.py
rostopic echo -n 1 /slam_odom
rosrun tf view_frames
```

只启动桥接节点：

```bash
roslaunch spraying_car_localization point_lio_bridge.launch publish_tf:=false
```

聚合启动：

```bash
roslaunch spraying_car_bringup bringup_localization.launch bridge_publish_tf:=false
```

进入 move_base/TEB dry-run 前，live SLAM 模式需要 `odom -> base_link` 可达。只有在实测确认 `/slam_odom` 方向和 `base_link -> lidar_link` 外参正确后，才应使用：

```bash
roslaunch spraying_car_navigation navigation_live_slam.launch bridge_publish_tf:=true base_dry_run:=true
```

saved map 模式还缺少 `map -> odom` 重定位来源，不能把 `/slam_odom` 直接等同于旧地图定位。

## 风险

- L1RM 外参仍未实测。
- point_lio 输出是否严格代表 `lidar_link` 需要实机确认。
- 果园环境重复结构可能导致 LiDAR odom 漂移。
- 普通 GPS 不能提供高精度定位。
- 无 wheel odom，低速坑洼、打滑、地面不平无法被轮端观测。
- 当前只有软件急停，导航实验必须低速、空旷、有人看护。

## 阶段 8E 真实 frame 复测结果

验证日期：2026-05-16。

真实 L1RM 输入：

- L1RM 当前设备名：`/dev/ttyUSB0`。
- L1RM by-id：`/dev/serial/by-id/usb-Silicon_Labs_CP2104_USB_to_UART_Bridge_Controller_02C901C5-if00-port0`。
- `/unilidar/cloud`：OK，有真实消息，`frame_id=lidar_link`，频率约 `7.6 Hz`。
- `/unilidar/imu`：OK，有真实消息，`frame_id=imu_link`，频率约 `200 Hz`。
- `/pointlio/odom`：OK，有数据，频率约 `7.6 Hz`。
- `/pointlio/odom header.frame_id`：`camera_init`。
- `/pointlio/odom child_frame_id`：`aft_mapped`。
- point_lio TF：`camera_init -> aft_mapped` 可查询。
- `point_lio_frame_bridge publish_tf=false`：`/slam_odom` 正常，`header.frame_id=odom`，`child_frame_id=base_link`。
- `point_lio_frame_bridge publish_tf=true`：发布 `odom -> base_footprint`，`odom -> base_link` 经 URDF 链路可达。
- `map -> odom`：未发布。
- wheel odom：未伪造。

当前结论：

- L1RM 输入侧 frame 已与 `lidar_link`、`imu_link` 对齐。
- point_lio 仍使用第三方默认 `camera_init -> aft_mapped`，通过 bridge 标准化为 `/slam_odom`。
- bridge 已修正为发布 `odom -> base_footprint`，避免 `base_link` 双父节点。
- 当前可信程度足够支撑 live SLAM dry-run 和 costmap/TEB 调试。
- 还不能认为已经具备实车导航能力：L1RM 外参未实测，真实点云下 TEB 近距离 goal 出现轨迹不可行，且没有基于旧地图的重定位能力。
