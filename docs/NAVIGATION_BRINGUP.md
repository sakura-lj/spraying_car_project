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

## 本阶段不做

- 不实现 waypoint 路线。
- 不实现 Web 自动驾驶入口。
- 不实现 `CONTROL_BACKEND=ros`。
- 不实现 saved map 重定位。
- 不做真实速度标定。
- 不发布 `map -> odom`。
- 不伪造 wheel odom。
