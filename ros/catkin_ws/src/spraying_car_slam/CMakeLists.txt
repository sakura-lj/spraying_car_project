cmake_minimum_required(VERSION 3.0.2)
project(spraying_car_slam)

find_package(catkin REQUIRED)

catkin_package()

catkin_install_python(
  PROGRAMS
    scripts/save_point_lio_pcd.py
    scripts/pcd_to_occupancy_grid.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(
  DIRECTORY config launch rviz
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
