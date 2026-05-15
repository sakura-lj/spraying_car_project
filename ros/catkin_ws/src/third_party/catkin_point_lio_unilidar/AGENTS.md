# AGENTS.md — point_lio_unilidar

## Overview
ROS1 (noetic) catkin workspace for Unitree's Point-LIO LiDAR inertial odometry adapted for Unitree L1/L2 LiDARs.

## Build
```bash
# From workspace root (this directory):
catkin_make
# Then source:
source devel/setup.bash
```
- `catkin_make` from workspace root builds the `point_lio_unilidar` package only.
- `unilidar_sdk/` is a **separate vendored git repo** with its own build:
  ```bash
  cd unilidar_sdk/unitree_lidar_ros && catkin_make
  ```

## Source layout
- `src/point_lio_unilidar/` — the only ROS package in this workspace
  - `src/laserMapping.cpp` — `main()`, ROS node `"laserMapping"`, executable `pointlio_mapping`
  - `include/ikd-Tree/` and `include/IKFoM/` — vendored third-party libs (in-tree, no external fetch needed)
  - `config/` — YAML per LiDAR type (unilidar_l1.yaml, unilidar_l2.yaml, avia.yaml, horizon.yaml, ouster64.yaml, velody16.yaml)
  - `launch/` — `.launch` files per LiDAR type
- `unilidar_sdk/` — independent vendor repo (`git@github.com:unitreerobotics/unilidar_sdk.git`), NOT a git submodule

## Run (correct 3-terminal order)
```bash
# Terminal 1: roscore MUST start first
roscore

# Terminal 2: LiDAR driver
cd unilidar_sdk/unitree_lidar_ros && source devel/setup.bash
roslaunch unitree_lidar_ros run_without_rviz.launch

# Terminal 3: SLAM (after driver publishes data)
cd <workspace_root> && source devel/setup.bash
roslaunch point_lio_unilidar mapping_unilidar_l1.launch rviz:=false
```
- **Never skip roscore.** If driver and SLAM each auto-start their own master, data won't flow between them.
- `rviz:=false` avoids GPU crash on Orange Pi (Rockchip GPU lacks proper OpenGL drivers).
- Runtime output: `src/point_lio_unilidar/PCD/scans.pcd` (map) and `src/point_lio_unilidar/Log/` (debug logs).

## Remote rviz (Ubuntu 20.04 notebook)
```bash
export ROS_MASTER_URI=http://<orangepi_ip>:11311
rviz
```
- Fixed Frame: `camera_init`
- SLAM only publishes `camera_init` → `aft_mapped` TF frames. No `base_link`.
- If DNS fails, add `<orangepi_ip> orangepi5b` to `/etc/hosts`.

## Compiler / flags
- C++14, `-O3`, OpenMP enabled on x86 (≥4 cores).
- Eigen3, PCL ≥1.8 required.
- `ROOT_DIR` is defined as the package source directory.

## Testing / CI
- No tests, no CI, no linting/formatting config.
- `package.xml` declares `rostest`/`rosbag` test depends but has no test targets.

## Environment quirks (Orange Pi 5B / ARM64)
- **Conda Python clash**: System has miniconda3 with Python 3.13. ROS noetic requires system Python 3.8. Before any ROS command in any terminal: `export PATH="/usr/bin:/opt/ros/noetic/bin:$PATH"`
- **OHCI USB controller instability**: Orange Pi 5B's OHCI USB 1.1 ports (Bus 04/06) can silently drop serial reads. SDK example `example_lidar` may show `SerialException: device reports readiness to read but returned no data`. Fix: use USB 2.0/3.0 (xhci) ports. See `troubleshooting_lidar_no_data.md` for full history.
- **SDK debug output buffering**: `printf` output from C++ SDK examples goes through full buffering when piped. Use `stdbuf -oL -eL ./bin/example_lidar` to see real-time output.

## Gotchas
- `unilidar_sdk/` ships `libunitree_lidar_sdk.a` as **pre-compiled static libs** for x86_64 and aarch64 (no source for the core SDK).
- Several launch files had a stray `launch-prefix="gdb -ex run --args"` **outside any `<node>` tag** — already fixed.
- The Livox driver (`livox_ros_driver`) is fully commented out in CMakeLists.txt, package.xml, and source — the project uses standard `sensor_msgs::PointCloud2` instead.
- `catkin_make` requires `src/CMakeLists.txt` (created automatically by first `catkin_make` or `catkin_init_workspace`). If it's missing, run `catkin_init_workspace src` first.
