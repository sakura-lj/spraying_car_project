这个包只放自定义消息。

例如你的 STM32 会反馈：

车速
转向角
电池电压
控制模式
急停状态
故障码

可以定义：

spraying_car_msgs/msg/VehicleState.msg

内容示例：

std_msgs/Header header

float32 speed_mps
float32 steering_angle_rad
float32 battery_voltage

uint8 mode
bool estop
uint16 fault_code

再定义一个控制指令：

spraying_car_msgs/msg/VehicleCmd.msg

内容：

std_msgs/Header header

float32 target_speed_mps
float32 target_steering_angle_rad
bool enable

不过第一版可以先不用自定义消息，只用标准消息：

/cmd_vel              geometry_msgs/Twist
/wheel_odom           nav_msgs/Odometry

等系统稳定后再加 spraying_car_msgs。