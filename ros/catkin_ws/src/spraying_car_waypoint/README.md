# spraying_car_waypoint

航点路线包，后续用于保存田间路线并按顺序发送目标点给导航栈。

当前状态：

- 已补齐 catkin 包结构。
- 已预留 `config/waypoints.yaml`。
- 已预留 `scripts/waypoint_follower.py`。
- 已预留 `launch/waypoint_follower.launch`。
- 暂不向 `move_base` 发送目标。

开发边界：

- waypoint 节点不能直接操作 STM32 串口。
- waypoint 节点只能通过导航栈或 `/cmd_vel` 链路间接控制车辆。
- 急停状态下不得继续推进航点任务。
