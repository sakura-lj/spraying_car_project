cmake_minimum_required(VERSION 3.0.2)
project(spraying_car_tools)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  rospy
)

catkin_package(
  CATKIN_DEPENDS geometry_msgs rospy
)

catkin_install_python(
  PROGRAMS
  scripts/cmd_vel_test.py
  scripts/cmd_vel_zero.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(
  DIRECTORY config launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
