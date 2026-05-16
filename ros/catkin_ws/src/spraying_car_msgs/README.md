# spraying_car_msgs

自研消息包，集中放后续 ROS 化需要共享的数据结构。

当前预留消息：

- `VehicleState.msg`：底盘状态、急停状态、故障码等。
- `VehicleCmd.msg`：底盘目标速度、目标转向角和使能状态。

第一阶段开发仍应优先使用标准消息：

- `/cmd_vel`：`geometry_msgs/Twist`
- `/wheel_odom`：`nav_msgs/Odometry`

只有当标准消息无法表达车辆状态时，再逐步使用本包中的自定义消息。
