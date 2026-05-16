cmake_minimum_required(VERSION 3.0.2)
project(spraying_car_base)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  nav_msgs
  rospy
  spraying_car_msgs
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS
  geometry_msgs
  nav_msgs
  rospy
  spraying_car_msgs
  std_msgs
)

catkin_install_python(
  PROGRAMS
  scripts/vehicle_base_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(
  DIRECTORY config launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
