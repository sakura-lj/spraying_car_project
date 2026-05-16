# spraying_car_navigation

第一版 `move_base` + TEB 导航配置包。当前目标是建立 ROS 标准导航结构，并支持低速、保守、dry-run 的验证流程；不承诺实车自动驾驶闭环。

## 两种模式

### Live SLAM / Odom 模式

入口：

```bash
roslaunch spraying_car_navigation navigation_live_slam.launch base_dry_run:=true use_rviz:=false
```

该模式启动 description、L1RM、point_lio、`point_lio_frame_bridge`、`spraying_car_base` dry-run 和 move_base。`move_base` 的 `global_frame=odom`，不依赖已保存地图。适合低速测试 `/slam_odom`、costmap、TEB 和 `/cmd_vel` 链路。

### Saved Map 模式

入口：

```bash
roslaunch spraying_car_navigation navigation_saved_map.launch map_yaml:=/abs/path/to/map.yaml base_dry_run:=true
```

该模式加载 `map_server` 和 saved grid map，但当前缺少可靠 `map -> odom` 重定位来源。因此它只是配置骨架，不保证能实车闭环。不要用 `fake_map_to_odom:=true` 做实车测试；该参数只允许 RViz/debug 使用。

## Planner

- Global planner：`global_planner/GlobalPlanner`
- Local planner：`teb_local_planner/TebLocalPlannerROS`
- move_base 只发布 `/cmd_vel`
- 底盘只能通过 `/cmd_vel -> spraying_car_base -> STM32`

## 关键参数

- 车体 footprint：`[[-0.75, -0.45], [-0.75, 0.45], [0.75, 0.45], [0.75, -0.45]]`
- 障碍物点云：`/unilidar/cloud`
- 点云 frame：`lidar_link`
- 最大前进速度：`0.3 m/s`
- 最大倒车速度：`0.1 m/s`
- 最大角速度：`0.4 rad/s`
- 最小转弯半径：`1.5 m`
- 轴距：`1.2 m`
- 目标容差：`xy=0.3 m`，`yaw=0.3 rad`

## 安全边界

- 默认 `base_dry_run=true`。
- 不启动 waypoint。
- 不实现 Web 自动驾驶入口。
- 不实现 `CONTROL_BACKEND=ros`。
- 不发布 `map -> odom`。
- 不伪造 wheel odom。
- 实车测试前必须停止 Flask，避免抢 `/dev/ttyS3`。
- 实车测试前必须确认遥控器可以接管。
