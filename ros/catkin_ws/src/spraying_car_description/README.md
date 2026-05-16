# spraying_car_description

喷药车 URDF/XACRO、传感器安装位和基础 TF 描述包。当前阶段只建立静态车体模型，服务于后续 L1RM、point_lio、导航和避障的坐标系对齐。

## 内容

- `urdf/spraying_car.urdf.xacro`：参数化车体模型。
- `config/sensor_mount.yaml`：雷达、IMU、摄像头、GPS 外参占位记录。
- `launch/description.launch`：加载 xacro 并启动 `robot_state_publisher`。
- `rviz/description.rviz`：RobotModel、TF、Grid 显示配置。

## 启动

```bash
cd ros/catkin_ws
catkin_make
source devel/setup.bash
roslaunch spraying_car_description description.launch use_rviz:=false
```

有图形界面时可以启动 RViz：

```bash
roslaunch spraying_car_description description.launch use_rviz:=true
```

查看 TF：

```bash
rosrun tf view_frames
```

或使用：

```bash
rosrun rqt_tf_tree rqt_tf_tree
```

## 已确认车辆参数

- 轴距：1.2 m。
- 轮距：0.8 m。
- 轮径：0.4 m。
- 轮子半径：0.2 m。
- 最小转弯半径：大于 1 m，URDF 当前按 1.5 m 作为保守占位。
- 最大转向角：估计约正负 35 度，待实测。
- 速度档位 `1..102` 尚未做实际车速标定。
- 车辆控制串口 `/dev/ttyS3` 在 Orange Pi 上基本固定。

## 仍需实测或确认

- 车体长宽高。
- 轮宽。
- L1RM 雷达相对 `base_link` 的 xyz/rpy。
- 摄像头相对 `base_link` 的 xyz/rpy。
- GPS 相对 `base_link` 的 xyz/rpy。
- 转向编码器值与实际转向角关系。
- 速度档位 `1..102` 与实际车速关系。
- 86 步进电机驱动器细分是否确认为 3200。
- GPS 串口。

## 当前限制

- 本阶段不会发布 `/odom`。
- 当前没有轮速编码器，硬件也无法安装，因此后续 `/odom` 不能来自 wheel odom。
- 四个轮子当前均为 fixed joint，只用于 RViz 可视化和基础 TF。
- 不包含 `move_base`、TEB、waypoint 或 ros_control。
- IMU 使用 L1RM 内置 IMU，不单独安装外置 IMU。
- GPS 是普通 Modbus GPS，不是 RTK，不能依赖其做高精度导航。

## 后续接入 L1RM 和 point_lio

后续阶段应先让 L1RM 驱动和 point_lio 输出 frame 与本包的 `lidar_link` 对齐。`point_lio_unilidar` 可能使用 `camera_init`、`aft_mapped` 等 frame，本阶段不硬改源码，后续通过 launch 参数或静态 TF 做对齐。

由于没有 wheel odom，point_lio 很可能成为定位链路中的主要里程计来源。是否发布 `map -> odom` 或 `map -> base_link` 应在 SLAM/定位阶段确定。
