cmake_minimum_required(VERSION 3.0.2)
project(spraying_car_waypoint)

find_package(catkin REQUIRED COMPONENTS
  rospy
)

catkin_package(
  CATKIN_DEPENDS rospy
)

catkin_install_python(
  PROGRAMS
  scripts/waypoint_follower.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(
  DIRECTORY config launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
