# Development Baseline

记录日期：2026-05-16

本文档用于保护当前农业喷药无人车项目的已验证闭环能力。进入 ROS 化开发前，任何改动都必须先确认不会破坏这些能力。

## 当前可运行功能

### 1. 遥控器驾驶闭环

当前遥控器驾驶已经形成闭环：

```text
遥控器接收器 -> STM32 PWM 捕获 -> 底盘执行机构
```

已形成闭环的执行能力包括：

- 牵引电机速度控制。
- 转向步进电机闭环控制。
- 行驶方向控制。
- 喷药继电器控制。
- 遥控器接管逻辑。

保护要求：

- 不要破坏遥控器对车辆的直接控制能力。
- 不要降低遥控器接管优先级。
- 不要让 ROS 自动驾驶绕过现有底层安全仲裁。

### 2. Web 远程控制闭环

当前 Web 远程控制已经形成闭环：

```text
浏览器/Vue -> Flask API -> STM32 串口 -> 底盘执行机构
```

启动方式：

```bash
cd web/upper
export GPS_SERIAL_PORT=/dev/ttyUSB1
python3 start.py
```

默认 Flask 监听：

```text
0.0.0.0:5000
```

常用访问入口：

```text
http://<OrangePi_IP>:5000/
http://<OrangePi_IP>:5000/app
http://<OrangePi_IP>:5000/app/monitor
http://<OrangePi_IP>:5000/app/control
```

常用验证命令：

```bash
curl http://127.0.0.1:5000/vehicle_status
curl http://127.0.0.1:5000/updateData
```

保护要求：

- 不要破坏 Flask API 到 STM32 的现有串口控制链路。
- 不要破坏 Vue 页面已有的监控页、控制页和急停入口。
- 不要在公开文档中记录 frp 服务器地址、公网地址、认证信息或其他隧道私有参数。
- 如需公网访问，只引用本地私有配置文件路径，不展开配置内容。

### 3. GPS 与摄像头显示闭环

当前 GPS 和摄像头显示已经形成闭环：

```text
GPS 模块 -> Flask GPS 线程 -> Vue 地图/轨迹显示
USB 摄像头 -> Flask MJPEG -> Web 页面显示
```

关键约束：

- STM32 控制串口默认由 `VEHICLE_SERIAL_PORT` 指定，当前基线为 `/dev/ttyS3`。
- GPS 串口默认由 `GPS_SERIAL_PORT` 指定，当前文档建议显式设置为实际 GPS 设备，例如 `/dev/ttyUSB1`。
- GPS、LiDAR、STM32 控制串口必须是不同设备，不能混用。

保护要求：

- 不要让 GPS 采集占用 STM32 控制串口。
- 不要破坏 `/vehicle_status`、`/updateData`、`/video_feed` 等现有页面依赖接口。
- 不要把电池电压、RTK、图像识别等未形成闭环的字段当作已验证能力。

### 4. L1RM LiDAR 驱动

当前 L1RM 驱动已经可以独立编译运行。运行时建议显式修正 ROS/Python 路径：

```bash
export PATH="/usr/bin:/opt/ros/noetic/bin:$PATH"
roscore
```

新终端启动 LiDAR 驱动：

```bash
export PATH="/usr/bin:/opt/ros/noetic/bin:$PATH"
cd ros/catkin_ws/src/third_party/unilidar_sdk/unitree_lidar_ros
source devel/setup.bash
roslaunch unitree_lidar_ros run_without_rviz.launch
```

验证话题：

```bash
rostopic echo /unilidar/cloud
rostopic echo /unilidar/imu
```

保护要求：

- 不要直接修改 `third_party/unilidar_sdk` 源码。
- 不要让 LiDAR 默认串口与 GPS 串口冲突。
- LiDAR 当前只作为独立感知链路，不代表已接入底盘自动驾驶。

### 5. point_lio_unilidar 建图

当前 `point_lio_unilidar` 已经可以独立编译运行。必须先启动同一个 `roscore`，再启动 LiDAR 驱动和 SLAM。

启动 Point-LIO：

```bash
export PATH="/usr/bin:/opt/ros/noetic/bin:$PATH"
cd ros/catkin_ws/src/third_party/catkin_point_lio_unilidar
source devel/setup.bash
roslaunch point_lio_unilidar mapping_unilidar_l1.launch rviz:=false
```

常用验证话题：

```bash
rostopic echo /pointlio/odom
rostopic echo /pointlio/cloud_registered
rostopic echo /pointlio/laser_map
```

保护要求：

- 不要直接修改 `third_party/catkin_point_lio_unilidar` 源码。
- 不要跳过 `roscore`，避免驱动和 SLAM 分别连接到不同 ROS Master。
- 当前建图链路未与底盘控制闭环连接，不能把它当作导航闭环。

## 当前尚未实现的 ROS 功能

以下内容目前仍是未实现或骨架状态，不能在开发、演示或文档中表述为已完成：

- ROS 底盘节点 `spraying_car_base`。
- `/cmd_vel -> spraying_car_base -> STM32` 控制链路。
- URDF/XACRO 机器人模型。
- 标准 TF 树，例如 `map -> odom -> base_link`。
- `/odom` 或轮速里程计。
- move_base / TEB 导航。
- waypoint 航点跟随。
- Web 页面到 ROS 控制后端的切换机制。
- RTK 定位闭环。
- 电池电压、液位、故障检测闭环。
- 图像识别自动喷药闭环。

## 不能破坏的功能

后续任何 ROS 化开发必须保护：

- 遥控器驾驶闭环。
- Web 远程控制闭环。
- GPS 地图与轨迹显示。
- 摄像头视频显示。
- STM32 串口协议的既有控制能力。
- 现有急停入口和急停语义。
- L1RM 驱动独立运行能力。
- point_lio_unilidar 独立建图能力。
- frp 私有配置文件的保密性。

## 基线保护结论

当前基线是“遥控/Web/GPS/摄像头已闭环，LiDAR/SLAM 可独立运行，ROS 底盘与导航尚未实现”。后续 ROS 化开发应先新增独立 ROS 包和配置，不应通过破坏已有闭环来换取自动驾驶功能。
