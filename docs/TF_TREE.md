# 喷药车 TF 树设计

本文档定义阶段 5 的车体模型和后续导航/SLAM 需要对齐的标准 TF 结构。当前阶段只实现 `base_footprint` 以下的静态模型，不实现 `map -> odom`、`odom -> base_footprint`，也不发布正式 `/odom`。

## 推荐最终 TF 树

```text
map
└── odom
    └── base_footprint
        └── base_link
            ├── chassis_link
            ├── front_left_wheel_link
            ├── front_right_wheel_link
            ├── rear_left_wheel_link
            ├── rear_right_wheel_link
            ├── lidar_link
            │   └── imu_link
            ├── camera_link
            └── gps_link
```

## 当前阶段已实现

`spraying_car_description` 当前只通过 URDF/XACRO 和 `robot_state_publisher` 发布以下固定 TF：

```text
base_footprint
└── base_link
    ├── chassis_link
    ├── front_left_wheel_link
    ├── front_right_wheel_link
    ├── rear_left_wheel_link
    ├── rear_right_wheel_link
    ├── lidar_link
    │   └── imu_link
    ├── camera_link
    └── gps_link
```

不会伪造 `odom -> base_footprint` 或 `odom -> base_link`。车辆没有轮速编码器，硬件也无法安装，因此后续 `/odom` 不能来自 wheel odom。

## 坐标系职责

- `map`：全局地图坐标系，后续由 SLAM/定位系统提供。
- `odom`：连续局部里程计坐标系。由于无轮速编码器，不能依赖 wheel odom，后续可能由 point_lio、普通 GPS 辅助或融合定位提供。
- `base_footprint`：车辆在地面上的投影坐标系。
- `base_link`：车辆主体坐标系，当前定义在车体几何中心附近。
- `chassis_link`：车体可视化模型。
- `front_left_wheel_link`、`front_right_wheel_link`、`rear_left_wheel_link`、`rear_right_wheel_link`：四个轮子可视化模型，当前均为 fixed joint，不建转向 joint 或 ros_control。
- `lidar_link`：L1RM 雷达坐标系。
- `imu_link`：L1RM 内置 IMU 坐标系，当前与 `lidar_link` 重合。
- `camera_link`：USB 摄像头坐标系。
- `gps_link`：普通 Modbus GPS 坐标系，不是 RTK。

## 已确认参数

- 轴距：1.2 m。
- 轮距：0.8 m。
- 轮子直径：0.4 m。
- 轮子半径：0.2 m。
- 最小转弯半径：大于 1 m；URDF 当前记录保守占位 1.5 m。
- 最大转向角：估计约正负 35 度，待实测。
- 电机：48V 直流电机，方向由 STM32 控制。
- 转向：86 步进电机，细分疑似 3200，待确认。
- 控制串口：Orange Pi 上车辆控制串口基本固定为 `/dev/ttyS3`。

## 占位参数

以下尺寸和外参当前只是初始占位，必须实车测量后修正：

- 车体长宽高：当前 `chassis_length=1.5`、`chassis_width=0.9`、`chassis_height=0.35`。
- 轮宽：当前 `wheel_width=0.10`。
- L1RM：当前 `xyz=[0.45, 0.0, 0.55]`、`rpy=[0, 0, 0]`，位置描述为车辆正前方、高于底盘一点。
- 摄像头：当前 `xyz=[0.45, 0.0, 0.65]`、`rpy=[0, 0, 0]`。
- GPS：当前 `xyz=[0.0, 0.0, 0.70]`、`rpy=[0, 0, 0]`。
- 转向编码器值与真实转向角的关系。
- 速度档位 `1..102` 与实际车速的关系。
- GPS 串口位置。

## 与 point_lio_unilidar 的关系

`point_lio_unilidar` 当前可能使用 `camera_init`、`aft_mapped` 等 frame。后续需要把 point_lio 输出与本标准 TF 树对齐，但本阶段不修改 point_lio 源码。

后续可通过 launch 参数或静态 TF，把 `lidar_link` 与 point_lio 使用的雷达 frame 对齐，再决定 `map -> odom` 或 `map -> base_link` 的来源。由于车辆没有轮速编码器，point_lio 很可能是自动驾驶定位链路中的主要里程计来源。

## point_lio frame 对齐

阶段 6 的启动封装默认让 Unitree L1RM 原始点云使用 `lidar_link`，内置 IMU 使用 `imu_link`：

- `/unilidar/cloud`：期望 `frame_id=lidar_link`。
- `/unilidar/imu`：期望 `frame_id=imu_link`。

该设置通过 `spraying_car_slam/launch/unilidar.launch` 覆盖 Unitree 驱动参数完成，不修改 `third_party/unilidar_sdk` 源码。

point_lio_unilidar 当前源码中输出 frame 仍是第三方默认命名：

- `/pointlio/odom`：`header.frame_id=camera_init`，`child_frame_id=aft_mapped`。
- `/pointlio/cloud_registered`：`frame_id=camera_init`。
- `/pointlio/laser_map`：`frame_id=camera_init`。
- `/pointlio/path`：`frame_id=camera_init`。
- TF：发布 `camera_init -> aft_mapped`。

本阶段不把 `camera_init` 强行命名为 `map`，也不把 `aft_mapped` 强行命名为 `base_link` 或 `odom`。这样可以避免在定位来源未验证前污染标准导航 TF 树。

实机检查步骤：

```bash
rostopic echo -n 1 /unilidar/cloud | grep frame_id
rostopic echo -n 1 /unilidar/imu | grep frame_id
rostopic echo -n 1 /pointlio/odom
rosrun tf view_frames
```

如果实测发现 L1RM 驱动仍发布 `unilidar_lidar` 或 `unilidar_imu`，优先检查 `unilidar.launch` 的 `lidar_frame`、`imu_frame` 参数是否生效。不要直接修改第三方源码；必要时用 launch 参数、配置文件或静态 TF 处理。后续标准化导航阶段再决定 `camera_init/aft_mapped` 到 `map/odom/base_link` 的转换关系。

## 阶段 8A 定位标准化

阶段 8A 新增 `spraying_car_localization`，不修改 point_lio 源码，只订阅 `/pointlio/odom` 并发布标准化后的 `/slam_odom`。

默认输入仍按 point_lio 第三方输出理解：

```text
camera_init
└── aft_mapped
```

桥接节点默认假设 point_lio pose 表示 `lidar_link` 或 L1RM 内置 IMU 主体在 point_lio world frame 下的位姿。节点使用 URDF/TF 中的 `base_link -> lidar_link` 静态外参，把 lidar 位姿转换为 `base_link` 位姿，然后输出：

```text
/slam_odom
header.frame_id: odom
child_frame_id: base_link
```

`point_lio_frame_bridge` 的 `publish_tf` 默认是 `false`。也就是说，当前不会自动发布 `odom -> base_link`，更不会发布 `map -> odom` 或 `map -> base_link`。只有在实机确认 L1RM 外参、point_lio 输出含义和 `/slam_odom` 方向都正确后，才允许通过 `bridge_publish_tf:=true` 显式打开 `odom -> base_link`。

当前仍然没有 wheel odom。`/slam_odom` 是 live SLAM odom 标准化输出，不代表已经具备基于旧地图的重定位能力。

## move_base/TEB 阶段 TF 要求

Live SLAM 导航 dry-run 使用：

```text
odom
└── base_link
    └── lidar_link
        └── imu_link
```

其中 `odom -> base_link` 由 `point_lio_frame_bridge` 在 `bridge_publish_tf:=true` 时发布。该 TF 不是 wheel odom，而是 point_lio live odom 的标准化结果。

Saved map 模式最终需要：

```text
map
└── odom
    └── base_link
```

当前项目尚无可靠 `map -> odom` 重定位来源。本阶段不发布 `map -> odom`，也不允许把静态 `map -> odom` 当作正式实车方案。

## 导航约束

- 目标导航模式是普通点到点导航，不做果园行间路径跟踪。
- 目标运行环境是果园。
- 自动驾驶时允许遥控器随时接管。
- 当前无物理急停开关，只有软件急停；导航测试必须低速、空旷、有人看护。
- 喷药泵和风机共用同一个继电器。
- 后续不需要 MQTT 云端接入。
- 后续不需要多车协同管理。
- 当前无电池电压采集，不能实现低电量返航。
- 普通 GPS 不是 RTK，不能依赖其做高精度导航。
