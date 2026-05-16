cmake_minimum_required(VERSION 3.0.2)
project(spraying_car_tools)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  nav_msgs
  rospy
  sensor_msgs
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS geometry_msgs nav_msgs rospy sensor_msgs std_msgs
)

catkin_install_python(
  PROGRAMS
  scripts/check_navigation_dependencies.py
  scripts/check_navigation_runtime.py
  scripts/cmd_vel_test.py
  scripts/cmd_vel_zero.py
  scripts/mock_slam_odom.py
  scripts/mock_lidar_cloud.py
  scripts/stm32_cdc_monitor.py
  scripts/check_serial_devices.py
  scripts/suspended_base_direction_test.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(
  DIRECTORY config launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
