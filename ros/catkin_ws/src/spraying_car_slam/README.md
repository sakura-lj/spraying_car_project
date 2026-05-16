# spraying_car_slam

自研 SLAM 封装包，用于统一启动 Unitree L1RM 驱动、`point_lio_unilidar` 建图流程，并管理建图后的 PCD 与 2D 栅格地图。当前包不修改 third_party 源码，不启动底盘控制，不发布 `/cmd_vel`，不发布正式 `/odom`。

## 当前支持

- 启动 L1RM：`launch/unilidar.launch`。
- 启动 point_lio：`launch/point_lio_mapping.launch`。
- 一键启动建图链路：`launch/slam.launch`。
- 归档 point_lio PCD：`scripts/save_point_lio_pcd.py`。
- ASCII PCD 转 2D 栅格地图：`scripts/pcd_to_occupancy_grid.py`。
- 查看 grid map：`launch/view_grid_map.launch`。

## 建图命令示例

先验证雷达：

```bash
roslaunch spraying_car_bringup bringup_lidar.launch lidar_port:=/dev/ttyUSB0
```

再启动建图：

```bash
roslaunch spraying_car_bringup bringup_slam.launch lidar_port:=/dev/ttyUSB0 use_rviz:=false
```

检查输出：

```bash
rostopic list | grep -E "unilidar|pointlio|cloud|imu|odom"
rostopic echo -n 1 /unilidar/cloud | grep frame_id
rostopic echo -n 1 /unilidar/imu | grep frame_id
rostopic echo -n 1 /pointlio/odom
```

## 地图保存目录

- `maps/pcd/`：归档后的 `.pcd`。
- `maps/grid/`：转换得到的 `.pgm` 和 `.yaml`。
- `maps/metadata/`：地图元数据。
- `maps/routes/`：后续 waypoint 路线预留目录。

推荐命名：

```text
orchard_test_area_20260516_v01
```

## 归档 PCD

```bash
rosrun spraying_car_slam save_point_lio_pcd.py \
  _source_pcd:=ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/src/point_lio_unilidar/PCD/scans.pcd \
  _map_name:=orchard_test_area_20260516_v01
```

如果不传 `_source_pcd`，脚本会尝试常见的 point_lio `PCD/scans.pcd` 路径。源文件不存在时会清晰报错。

## PCD 转 2D 栅格

```bash
rosrun spraying_car_slam pcd_to_occupancy_grid.py \
  _input_pcd:=maps/pcd/orchard_test_area_20260516_v01.pcd \
  _output_name:=orchard_test_area_20260516_v01 \
  _resolution:=0.10 \
  _height_min:=0.15 \
  _height_max:=1.50 \
  _inflation_radius:=0.30
```

第一版转换工具只支持 ASCII PCD。遇到 binary PCD 会明确报错；可先用 PCL 工具或其他点云工具转换成 ASCII PCD。

## 查看 grid map

```bash
roslaunch spraying_car_slam view_grid_map.launch \
  map_yaml:=/home/orangepi/spraying_car_project/maps/grid/orchard_test_area_20260516_v01.yaml \
  use_rviz:=true
```

如果系统没有 `map_server`：

```bash
sudo apt install ros-noetic-map-server
```

## Frame 现状

- 标准车体 frame：`base_link -> lidar_link -> imu_link`。
- L1RM wrapper 默认把原始点云 frame 设置为 `lidar_link`，IMU frame 设置为 `imu_link`。
- point_lio 当前源码输出 `/pointlio/odom`，父 frame 为 `camera_init`，子 frame 为 `aft_mapped`。
- 当前不把 `camera_init -> aft_mapped` 强行接入 `map/odom/base_link`。
- 阶段 8A 新增 `spraying_car_localization`，可把 `/pointlio/odom` 标准化发布为 `/slam_odom`。该桥接默认不发布 TF；实测确认后可选择发布 `odom -> base_link`。

## 当前限制

- 不实现 move_base、TEB、waypoint。
- 不将 SLAM 输出直接控制底盘。
- 不做 Flask/Vue 自动驾驶入口。
- 不控制 STM32。
- 不发布正式 `/odom`。
- PCD 转 grid 是第一版投影工具，输出地图只适合后续导航初步测试，不能替代实测验证。
