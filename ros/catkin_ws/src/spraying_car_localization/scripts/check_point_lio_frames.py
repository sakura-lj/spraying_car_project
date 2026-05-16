#!/usr/bin/env python3
"""Check L1RM, point_lio, and vehicle TF frames before navigation."""

import sys

import rospy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, PointCloud2
import tf


def wait_for_header(topic, msg_type, timeout):
    try:
        msg = rospy.wait_for_message(topic, msg_type, timeout=timeout)
        return msg.header.frame_id, None
    except Exception as exc:
        return None, str(exc)


def wait_for_odom(topic, timeout):
    try:
        msg = rospy.wait_for_message(topic, Odometry, timeout=timeout)
        return (msg.header.frame_id, msg.child_frame_id), None
    except Exception as exc:
        return None, str(exc)


def print_status(ok, text):
    print(("[OK] " if ok else "[WARN] ") + text)


def main():
    rospy.init_node("check_point_lio_frames", anonymous=True)

    cloud_topic = rospy.get_param("~cloud_topic", "/unilidar/cloud")
    imu_topic = rospy.get_param("~imu_topic", "/unilidar/imu")
    odom_topic = rospy.get_param("~point_lio_odom_topic", "/pointlio/odom")
    expected_cloud_frame = rospy.get_param("~expected_cloud_frame", "lidar_link")
    expected_imu_frame = rospy.get_param("~expected_imu_frame", "imu_link")
    expected_odom_frame = rospy.get_param("~expected_odom_frame", "camera_init")
    expected_odom_child_frame = rospy.get_param("~expected_odom_child_frame", "aft_mapped")
    timeout = float(rospy.get_param("~timeout", 3.0))

    exit_code = 0

    cloud_frame, err = wait_for_header(cloud_topic, PointCloud2, timeout)
    if cloud_frame is None:
        print_status(False, f"{cloud_topic}: no message received ({err})")
        exit_code = 1
    else:
        print_status(True, f"{cloud_topic}: frame_id={cloud_frame}")
        if cloud_frame != expected_cloud_frame:
            print_status(False, f"{cloud_topic}: expected {expected_cloud_frame}; align unilidar.launch lidar_frame")
            exit_code = 1

    imu_frame, err = wait_for_header(imu_topic, Imu, timeout)
    if imu_frame is None:
        print_status(False, f"{imu_topic}: no message received ({err})")
        exit_code = 1
    else:
        print_status(True, f"{imu_topic}: frame_id={imu_frame}")
        if imu_frame != expected_imu_frame:
            print_status(False, f"{imu_topic}: expected {expected_imu_frame}; align unilidar.launch imu_frame")
            exit_code = 1

    odom_frames, err = wait_for_odom(odom_topic, timeout)
    if odom_frames is None:
        print_status(False, f"{odom_topic}: no message received ({err})")
        exit_code = 1
    else:
        frame_id, child_frame_id = odom_frames
        print_status(True, f"{odom_topic}: header.frame_id={frame_id}, child_frame_id={child_frame_id}")
        if frame_id == expected_odom_frame and child_frame_id == expected_odom_child_frame:
            print_status(False, "point_lio still uses camera_init -> aft_mapped; use point_lio_frame_bridge for /slam_odom")
        elif frame_id != expected_odom_frame or child_frame_id != expected_odom_child_frame:
            print_status(False, "point_lio frames differ from defaults; update point_lio_bridge.yaml after confirming them")

    listener = tf.TransformListener()
    rospy.sleep(0.5)
    frames = set(listener.getFrameStrings())
    for frame in ("base_link", "lidar_link", "imu_link"):
        exists = frame in frames or listener.frameExists(frame)
        print_status(exists, f"TF frame {frame} {'exists' if exists else 'missing'}")
        if not exists:
            print_status(False, "Start spraying_car_description/description.launch before localization checks")
            exit_code = 1

    try:
        listener.waitForTransform("base_link", "lidar_link", rospy.Time(0), rospy.Duration(0.5))
        print_status(True, "TF base_link -> lidar_link is available")
    except Exception as exc:
        print_status(False, f"TF base_link -> lidar_link unavailable: {exc}")
        exit_code = 1

    if exit_code == 0:
        print("Frame check completed. /slam_odom can be tested with point_lio_frame_bridge.")
    else:
        print("Frame check completed with warnings; fix frame alignment before navigation.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
