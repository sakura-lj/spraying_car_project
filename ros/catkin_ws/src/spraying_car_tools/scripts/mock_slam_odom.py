#!/usr/bin/env python3
"""MOCK ONLY: publish static odometry for development tests.

Do not use on a real vehicle.
"""

import rospy
from geometry_msgs.msg import Quaternion
from nav_msgs.msg import Odometry
import tf


def build_odom_msg(topic_frame, child_frame, now):
    msg = Odometry()
    msg.header.stamp = now
    msg.header.frame_id = topic_frame
    msg.child_frame_id = child_frame
    msg.pose.pose.orientation = Quaternion(0.0, 0.0, 0.0, 1.0)
    msg.pose.covariance[0] = 0.05
    msg.pose.covariance[7] = 0.05
    msg.pose.covariance[35] = 0.10
    msg.twist.covariance[0] = 0.10
    msg.twist.covariance[35] = 0.20
    return msg


def main():
    rospy.init_node("mock_slam_odom")
    topic = rospy.get_param("~topic", "/slam_odom")
    point_lio_topic = rospy.get_param("~point_lio_topic", "/pointlio/odom")
    odom_frame = rospy.get_param("~odom_frame", "odom")
    base_frame = rospy.get_param("~base_frame", "base_link")
    tf_child_frame = rospy.get_param("~tf_child_frame", "base_footprint")
    point_lio_world_frame = rospy.get_param("~point_lio_world_frame", "camera_init")
    point_lio_body_frame = rospy.get_param("~point_lio_body_frame", "aft_mapped")
    publish_tf = bool(rospy.get_param("~publish_tf", True))
    publish_point_lio_odom = bool(rospy.get_param("~publish_point_lio_odom", True))
    rate_hz = float(rospy.get_param("~rate", 20.0))

    rospy.logwarn("mock_slam_odom is for development only. It is forbidden for real vehicle navigation.")

    pub = rospy.Publisher(topic, Odometry, queue_size=10)
    point_lio_pub = rospy.Publisher(point_lio_topic, Odometry, queue_size=10)
    broadcaster = tf.TransformBroadcaster()
    rate = rospy.Rate(max(1.0, rate_hz))
    quat = (0.0, 0.0, 0.0, 1.0)

    while not rospy.is_shutdown():
        now = rospy.Time.now()
        pub.publish(build_odom_msg(odom_frame, base_frame, now))
        if publish_point_lio_odom:
            point_lio_pub.publish(build_odom_msg(point_lio_world_frame, point_lio_body_frame, now))

        if publish_tf:
            # URDF already publishes base_footprint -> base_link. Publishing
            # odom -> base_footprint avoids giving base_link two TF parents.
            broadcaster.sendTransform((0.0, 0.0, 0.0), quat, now, tf_child_frame, odom_frame)

        rate.sleep()


if __name__ == "__main__":
    main()
