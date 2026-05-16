#!/usr/bin/env python3
"""Check ROS navigation dependencies without installing or modifying anything."""

import os
from pathlib import Path
import subprocess
import sys


REQUIRED_PACKAGES = [
    "spraying_car_base",
    "spraying_car_description",
    "spraying_car_slam",
    "spraying_car_localization",
    "spraying_car_navigation",
    "move_base",
    "teb_local_planner",
    "map_server",
    "global_planner",
    "costmap_2d",
    "nav_core",
]

INSTALL_HINT = (
    "sudo apt update\n"
    "sudo apt install ros-noetic-navigation ros-noetic-teb-local-planner "
    "ros-noetic-map-server ros-noetic-global-planner"
)


def status_line(ok, name, detail=""):
    label = "OK" if ok else "MISSING"
    suffix = f" - {detail}" if detail else ""
    print(f"[{label}] {name}{suffix}")


def rospack_find(package):
    try:
        result = subprocess.run(
            ["rospack", "find", package],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0,
        )
    except Exception as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, result.stdout.strip()
    detail = result.stderr.strip() or result.stdout.strip()
    return False, detail


def check_roscore():
    try:
        import rosgraph

        master = rosgraph.Master("/check_navigation_dependencies")
        master.getPid()
        return True, "ROS master reachable"
    except Exception as exc:
        return False, str(exc)


def main():
    missing = []
    missing_ros_packages = []

    ok, detail = check_roscore()
    status_line(ok, "roscore connection", detail)
    if not ok:
        missing.append("roscore connection")

    ros_package_path = os.environ.get("ROS_PACKAGE_PATH", "")
    catkin_ws = Path(__file__).resolve().parents[3]
    catkin_src = catkin_ws / "src"
    has_workspace = str(catkin_src) in ros_package_path or str(catkin_ws) in ros_package_path
    status_line(
        has_workspace,
        "ROS_PACKAGE_PATH contains current catkin_ws",
        str(catkin_src),
    )
    if not has_workspace:
        missing.append("ROS_PACKAGE_PATH current workspace")

    opt_setup = Path("/opt/ros/noetic/setup.bash")
    devel_setup = catkin_ws / "devel/setup.bash"
    status_line(opt_setup.exists(), "/opt/ros/noetic/setup.bash", str(opt_setup))
    status_line(devel_setup.exists(), "ros/catkin_ws/devel/setup.bash", str(devel_setup))
    if not opt_setup.exists():
        missing.append(str(opt_setup))
    if not devel_setup.exists():
        missing.append(str(devel_setup))

    for package in REQUIRED_PACKAGES:
        ok, detail = rospack_find(package)
        status_line(ok, f"rospack find {package}", detail)
        if not ok:
            missing.append(package)
            missing_ros_packages.append(package)

    if missing:
        print("\nMissing items:")
        for item in missing:
            print(f"  - {item}")
        if missing_ros_packages:
            print("\nInstall suggestion for ROS navigation packages:")
            print(INSTALL_HINT)
        else:
            print("\nROS packages are present. Start roscore or roslaunch before runtime checks.")
        return 1

    print("\nAll navigation dependency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
