# 建图保存与地图管理工作流

本文档记录阶段 7 的 point_lio 建图、PCD 归档、PCD 到 2D 栅格地图转换和验证流程。本阶段不做 move_base、TEB、waypoint、Flask/Vue 自动驾驶入口、不控制 STM32、不发布正式 `/odom`。

## 地图目录

```text
maps/
├── README.md
├── pcd/
├── grid/
├── routes/
└── metadata/
```

- `maps/pcd/`：保存 point_lio 输出的原始或处理后的 PCD 地图。
- `maps/grid/`：保存后续 `map_server` 可加载的 `.pgm/.yaml`。
- `maps/routes/`：后续保存 waypoint 路线，本阶段只建目录。
- `maps/metadata/`：保存地图元数据。

## 命名规范

推荐格式：

```text
果园名_区域名_日期_版本
```

示例：

```text
orchard_test_area_20260516_v01.pcd
orchard_test_area_20260516_v01.yaml
orchard_test_area_20260516_v01.pgm
orchard_test_area_20260516_v01.meta.yaml
```

元数据建议包含：

- `map_name`
- `created_at`
- `location_name`
- `environment_type`
- `lidar_model`
- `slam_algorithm`
- `pcd_source_path`
- `grid_map_path`
- `resolution`
- `origin`
- `height_filter_min`
- `height_filter_max`
- `notes`
- `known_issues`

## 建图前准备

- 确认 ROS Noetic 可用。
- 确认 L1RM 接口正确。
- 确认 GPS 与 L1RM 不抢 `/dev/ttyUSB0`。
- 确认车辆处于安全手动模式。
- 建图时建议人工遥控低速行驶。
- 建图测试时不启动自动驾驶。
- L1RM 初始化时车辆保持静止。
- 普通 GPS 不是 RTK，不能依赖 GPS 做高精度地图定位。

## 启动顺序

1. 启动 ROS master：

```bash
roscore
```

2. 启动 L1RM：

```bash
roslaunch spraying_car_bringup bringup_lidar.launch lidar_port:=/dev/ttyUSB0
```

3. 检查 L1RM 输出：

```bash
rostopic echo -n 1 /unilidar/cloud
rostopic echo -n 1 /unilidar/imu
rostopic hz /unilidar/cloud
rostopic hz /unilidar/imu
```

4. 启动建图：

```bash
roslaunch spraying_car_bringup bringup_slam.launch lidar_port:=/dev/ttyUSB0 use_rviz:=false
```

5. 检查 point_lio 输出：

```bash
rostopic list | grep -E "pointlio|odom|cloud|map"
rostopic echo -n 1 /pointlio/odom
```

6. 人工遥控低速绕场，覆盖整个作业区域。

## 保存 PCD

point_lio 默认可能保存到：

```text
ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/src/point_lio_unilidar/PCD/scans.pcd
```

归档到项目 `maps/pcd/`：

```bash
rosrun spraying_car_slam save_point_lio_pcd.py \
  _source_pcd:=ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/src/point_lio_unilidar/PCD/scans.pcd \
  _map_name:=orchard_test_area_20260516_v01 \
  _location_name:=test_area \
  _notes:="manual low speed mapping"
```

输出：

- `maps/pcd/orchard_test_area_20260516_v01.pcd`
- `maps/metadata/orchard_test_area_20260516_v01.meta.yaml`

## 转换 2D 地图

运行：

```bash
rosrun spraying_car_slam pcd_to_occupancy_grid.py \
  _input_pcd:=maps/pcd/orchard_test_area_20260516_v01.pcd \
  _output_name:=orchard_test_area_20260516_v01 \
  _resolution:=0.10 \
  _height_min:=0.15 \
  _height_max:=1.50 \
  _inflation_radius:=0.30
```

输出：

- `maps/grid/orchard_test_area_20260516_v01.pgm`
- `maps/grid/orchard_test_area_20260516_v01.yaml`
- `maps/metadata/orchard_test_area_20260516_v01_grid.meta.yaml`

参数建议：

- `resolution`：果园初测可用 `0.10` m/pixel；需要更细地图时试 `0.05`。
- `height_min`：提高可过滤地面点；如果低矮障碍漏掉，适当降低。
- `height_max`：降低可过滤高处枝叶；如果树冠噪声太多，适当降低。
- `inflation_radius`：初始可用 `0.30` m，后续应结合车体宽度和导航膨胀层重新调整。

第一版工具只支持 ASCII PCD。binary PCD 需要先用 PCL/Open3D 等工具转成 ASCII，或后续扩展脚本。

## YAML 示例

```yaml
image: orchard_test_area_20260516_v01.pgm
resolution: 0.100000
origin: [-2.300000, -1.700000, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
```

## 验证 2D 地图

```bash
roslaunch spraying_car_slam view_grid_map.launch \
  map_yaml:=/home/orangepi/spraying_car_project/maps/grid/orchard_test_area_20260516_v01.yaml \
  use_rviz:=true
```

如果没有图形界面，可先只启动 map_server：

```bash
roslaunch spraying_car_slam view_grid_map.launch \
  map_yaml:=/home/orangepi/spraying_car_project/maps/grid/orchard_test_area_20260516_v01.yaml \
  use_rviz:=false
```

再检查：

```bash
rostopic echo -n 1 /map
```

## 常见问题

PCD 文件不存在：
确认 point_lio 是否开启 PCD 保存，或者手动指定 `_source_pcd`。

PCD 是二进制：
当前转换脚本只支持 ASCII PCD，会明确报错。后续可接入 PCL、python-pcl 或 open3d。

地图上下颠倒或原点不对：
检查 YAML `origin`，并在 RViz 中核对点云、grid 和 TF。

障碍物太多或太少：
调整 `height_min`、`height_max` 和 `inflation_radius`。

地面点没有滤掉：
提高 `height_min`，并检查 point_lio 输出坐标系的 z 轴方向。

果园噪声：
树干、枝叶、草地会导致障碍物噪声，需要多次试验高度过滤和点云预处理。

没有 RTK 时地图复用定位风险：
普通 GPS 不能提供高精度定位，后续定位主要依赖 point_lio 或融合方案。

point_lio frame 仍是 `camera_init/aft_mapped`：
本阶段只记录和观察，不强行改成 `map/odom/base_link`。

## 本阶段不做

- 不实现 move_base。
- 不实现 TEB。
- 不实现 waypoint。
- 不实现 Flask/Vue 自动驾驶入口。
- 不控制 STM32。
- 不发布正式 `/odom`。
