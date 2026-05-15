这个包放调试脚本。

例如：

serial_test.py             测试 ROS 到 STM32 串口
cmd_vel_test.py            自动发布 /cmd_vel
odom_test.py               检查 /wheel_odom 是否正常
emergency_stop_test.py     测试急停
record_waypoint.py         记录当前位置为航点

调试工具不要塞进正式控制包里，否则后面会很乱。