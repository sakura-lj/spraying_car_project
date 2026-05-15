这是最重要的底盘包。

负责：

/cmd_vel → STM32 串口/CAN
STM32 状态 → /wheel_odom
STM32 状态 → /vehicle_state
发布 odom → base_link

推荐结构：

base/
├── scripts/
│   └── vehicle_base_node.py
├── config/
│   └── base.yaml
├── launch/
│   └── vehicle_base.launch

base.yaml 示例：

port: /dev/ttyUSB0
baud: 115200

wheelbase: 0.82
track_width: 0.55

max_speed: 0.6
max_reverse_speed: 0.2
max_steer_angle: 0.45
max_steer_rate: 0.8

cmd_timeout: 0.5
publish_tf: true
odom_frame: odom
base_frame: base_link

vehicle_base.launch 示例：

<launch>
    <node pkg="agrocar_base"
          type="vehicle_base_node.py"
          name="vehicle_base_node"
          output="screen">
        <rosparam file="$(find agrocar_base)/config/base.yaml" command="load"/>
    </node>
</launch>

这个包后期可以先用 Python 写，跑通后如果需要更高实时性，再改成 C++。