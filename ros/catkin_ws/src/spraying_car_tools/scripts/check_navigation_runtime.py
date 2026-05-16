#!/usr/bin/env python3
"""Read-only runtime checks for navigation topics, frames, and TF."""

import sys

import rosgraph
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import Imu, PointCloud2
import tf


TOPIC_TYPES = {
    "/unilidar/cloud": PointCloud2,
    "/unilidar/imu": Imu,
    "/pointlio/odom": Odometry,
    "/slam_odom": Odometry,
    "/cmd_vel": Twist,
    "/move_base/global_costmap/costmap": OccupancyGrid,
    "/move_base/local_costmap/costmap": OccupancyGrid,
}


def line(level, text):
    print(f"[{level}] {text}")


def topic_sets():
    master = rosgraph.Master("/check_navigation_runtime")
    pubs, subs, _ = master.getSystemState()
    pub_map = {topic: nodes for topic, nodes in pubs}
    sub_map = {topic: nodes for topic, nodes in subs}
    return pub_map, sub_map


def topic_exists(topic, pub_map, sub_map):
    return topic in pub_map or topic in sub_map


def wait_for_message(topic, msg_type, timeout):
    try:
        return rospy.wait_for_message(topic, msg_type, timeout=timeout), None
    except Exception as exc:
        return None, str(exc)


def check_topic_presence(topic, pub_map, sub_map, required=True):
    exists = topic_exists(topic, pub_map, sub_map)
    if exists:
        line("OK", f"{topic} exists publishers={len(pub_map.get(topic, []))} subscribers={len(sub_map.get(topic, []))}")
        return True
    level = "FAIL" if required else "WARN"
    line(level, f"{topic} missing")
    return not required


def check_frame_message(topic, msg_type, expected_frame, timeout):
    msg, err = wait_for_message(topic, msg_type, timeout)
    if msg is None:
        line("WARN", f"{topic} no sample received for frame check: {err}")
        return False
    frame = msg.header.frame_id
    if frame == expected_frame:
        line("OK", f"{topic} frame_id={frame}")
        return True
    line("WARN", f"{topic} frame_id={frame}, expected {expected_frame}")
    return False


def check_slam_odom(timeout):
    msg, err = wait_for_message("/slam_odom", Odometry, timeout)
    if msg is None:
        line("WARN", f"/slam_odom no sample received: {err}")
        return False
    ok = True
    if msg.header.frame_id == "odom":
        line("OK", "/slam_odom header.frame_id=odom")
    else:
        line("WARN", f"/slam_odom header.frame_id={msg.header.frame_id}, expected odom")
        ok = False
    if msg.child_frame_id == "base_link":
        line("OK", "/slam_odom child_frame_id=base_link")
    else:
        line("WARN", f"/slam_odom child_frame_id={msg.child_frame_id}, expected base_link")
        ok = False
    return ok


def check_tf(listener, parent, child, required=True):
    try:
        listener.waitForTransform(parent, child, rospy.Time(0), rospy.Duration(0.5))
        line("OK", f"TF {parent} -> {child} available")
        return True
    except Exception as exc:
        level = "FAIL" if required else "WARN"
        line(level, f"TF {parent} -> {child} unavailable: {exc}")
        return not required


def main():
    rospy.init_node("check_navigation_runtime", anonymous=True)
    timeout = float(rospy.get_param("~message_timeout", 2.0))
    expect_odom_tf = bool(rospy.get_param("~expect_odom_to_base_tf", False))

    try:
        pub_map, sub_map = topic_sets()
    except Exception as exc:
        line("FAIL", f"Cannot query ROS master: {exc}")
        return 1

    ok = True
    required_topics = [
        "/unilidar/cloud",
        "/unilidar/imu",
        "/pointlio/odom",
        "/slam_odom",
        "/cmd_vel",
        "/spraying_car/base_state",
        "/move_base/status",
        "/move_base/global_costmap/costmap",
        "/move_base/local_costmap/costmap",
    ]
    for topic in required_topics:
        ok = check_topic_presence(topic, pub_map, sub_map, required=True) and ok

    if "/cmd_vel" in pub_map:
        line("OK", f"/cmd_vel publishers: {', '.join(pub_map['/cmd_vel'])}")
    else:
        line("FAIL", "/cmd_vel has no publisher")
        ok = False
    if "/cmd_vel" in sub_map:
        line("OK", f"/cmd_vel subscribers: {', '.join(sub_map['/cmd_vel'])}")
    else:
        line("FAIL", "/cmd_vel has no subscriber; spraying_car_base may not be running")
        ok = False

    check_frame_message("/unilidar/cloud", PointCloud2, "lidar_link", timeout)
    check_frame_message("/unilidar/imu", Imu, "imu_link", timeout)
    check_slam_odom(timeout)

    listener = tf.TransformListener()
    rospy.sleep(0.5)
    ok = check_tf(listener, "base_footprint", "base_link", required=True) and ok
    ok = check_tf(listener, "base_link", "lidar_link", required=True) and ok
    ok = check_tf(listener, "lidar_link", "imu_link", required=True) and ok
    ok = check_tf(listener, "odom", "base_link", required=expect_odom_tf) and ok
    if not expect_odom_tf:
        line("WARN", "odom -> base_link is only required when bridge_publish_tf=true")

    if ok:
        print("\nRuntime navigation checks passed.")
        return 0

    print("\nRuntime navigation checks found missing items.")
    print("Next steps: verify description.launch, point_lio bridge, move_base, and spraying_car_base dry-run are running.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
