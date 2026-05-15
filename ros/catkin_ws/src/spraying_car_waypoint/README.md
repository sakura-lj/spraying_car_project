这个包负责“规定路线行驶”。

你可以把固定路线保存成：

spraying_car_waypoint/config/waypoints.yaml

示例：

waypoints:
  - name: start
    x: 0.0
    y: 0.0
    yaw: 0.0
    speed: 0.4

  - name: row_1_start
    x: 5.0
    y: 0.0
    yaw: 0.0
    speed: 0.4

  - name: row_1_end
    x: 20.0
    y: 0.0
    yaw: 0.0
    speed: 0.4

  - name: turn_1
    x: 22.0
    y: 2.0
    yaw: 1.57
    speed: 0.25

节点负责依次发送目标点给 move_base。