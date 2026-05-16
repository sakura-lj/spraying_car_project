cmake_minimum_required(VERSION 3.0.2)
project(spraying_car_localization)

find_package(catkin REQUIRED)

catkin_package()

catkin_install_python(
  PROGRAMS
    scripts/point_lio_frame_bridge.py
    scripts/check_point_lio_frames.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(
  DIRECTORY config launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
