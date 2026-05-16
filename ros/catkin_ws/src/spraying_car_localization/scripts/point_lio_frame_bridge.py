#!/usr/bin/env python3
"""Standardize point_lio odometry frames for the spraying car."""

import copy
import math

import rospy
from nav_msgs.msg import Odometry
import tf
from tf.transformations import (
    concatenate_matrices,
    quaternion_from_matrix,
    quaternion_matrix,
    translation_from_matrix,
)


def pose_to_matrix(pose):
    quat = [
        pose.orientation.x,
        pose.orientation.y,
        pose.orientation.z,
        pose.orientation.w,
    ]
    matrix = quaternion_matrix(quat)
    matrix[0, 3] = pose.position.x
    matrix[1, 3] = pose.position.y
    matrix[2, 3] = pose.position.z
    return matrix


def transform_to_matrix(translation, rotation):
    matrix = quaternion_matrix(rotation)
    matrix[0, 3] = translation[0]
    matrix[1, 3] = translation[1]
    matrix[2, 3] = translation[2]
    return matrix


def normalize_quaternion(q):
    norm = math.sqrt(sum(v * v for v in q))
    if norm <= 1e-12:
        return [0.0, 0.0, 0.0, 1.0]
    return [v / norm for v in q]


class PointLioFrameBridge:
    def __init__(self):
        self.point_lio_odom_topic = rospy.get_param("~point_lio_odom_topic", "/pointlio/odom")
        self.output_odom_topic = rospy.get_param("~output_odom_topic", "/slam_odom")
        self.point_lio_world_frame = rospy.get_param("~point_lio_world_frame", "camera_init")
        self.point_lio_body_frame = rospy.get_param("~point_lio_body_frame", "aft_mapped")
        self.standard_odom_frame = rospy.get_param("~standard_odom_frame", "odom")
        self.standard_base_frame = rospy.get_param("~standard_base_frame", "base_link")
        self.tf_child_frame = rospy.get_param("~tf_child_frame", "base_footprint")
        self.lidar_frame = rospy.get_param("~lidar_frame", "lidar_link")
        self.publish_tf = rospy.get_param("~publish_tf", False)
        self.republish_odom = rospy.get_param("~republish_odom", True)
        self.use_lidar_to_base_tf = rospy.get_param("~use_lidar_to_base_tf", True)
        self.tf_lookup_timeout = float(rospy.get_param("~tf_lookup_timeout", 0.2))
        self.warn_if_frame_mismatch = rospy.get_param("~warn_if_frame_mismatch", True)
        self.print_frame_debug = rospy.get_param("~print_frame_debug", True)

        self.tf_listener = tf.TransformListener()
        self.tf_broadcaster = tf.TransformBroadcaster()
        self.odom_pub = rospy.Publisher(self.output_odom_topic, Odometry, queue_size=10)
        self.debug_printed = False

        self.odom_sub = rospy.Subscriber(
            self.point_lio_odom_topic,
            Odometry,
            self.odom_callback,
            queue_size=20,
        )

        rospy.loginfo(
            "point_lio_frame_bridge: %s -> %s, output %s -> %s on %s, publish_tf=%s",
            self.point_lio_world_frame,
            self.point_lio_body_frame,
            self.standard_odom_frame,
            self.standard_base_frame,
            self.output_odom_topic,
            self.publish_tf,
        )
        rospy.loginfo(
            "point_lio_frame_bridge: TF child frame is %s",
            self.tf_child_frame,
        )
        if not self.publish_tf:
            rospy.loginfo("point_lio_frame_bridge: TF publishing is disabled by default")

    def lookup_transform_matrix(self, target_frame, source_frame, timeout_msg):
        lookup_time = rospy.Time(0)
        timeout = rospy.Duration(self.tf_lookup_timeout)
        try:
            self.tf_listener.waitForTransform(
                target_frame,
                source_frame,
                lookup_time,
                timeout,
            )
            trans, rot = self.tf_listener.lookupTransform(
                target_frame,
                source_frame,
                lookup_time,
            )
            return transform_to_matrix(trans, rot)
        except (tf.Exception, tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as exc:
            rospy.logwarn_throttle(
                2.0,
                timeout_msg,
                target_frame,
                source_frame,
                exc,
            )
            return None

    def lookup_lidar_to_base(self, stamp):
        if not self.use_lidar_to_base_tf:
            return None
        return self.lookup_transform_matrix(
            self.lidar_frame,
            self.standard_base_frame,
            "point_lio_frame_bridge: cannot lookup %s -> %s TF: %s. Start description.launch first.",
        )

    def output_tf_pose(self, odom_to_base):
        if self.tf_child_frame == self.standard_base_frame:
            return odom_to_base

        base_to_tf_child = self.lookup_transform_matrix(
            self.standard_base_frame,
            self.tf_child_frame,
            "point_lio_frame_bridge: cannot lookup %s -> %s TF for publish_tf: %s.",
        )
        if base_to_tf_child is None:
            return None
        return concatenate_matrices(odom_to_base, base_to_tf_child)

    def odom_callback(self, msg):
        src_world = msg.header.frame_id
        src_body = msg.child_frame_id

        if self.print_frame_debug and not self.debug_printed:
            rospy.loginfo(
                "point_lio_frame_bridge: first input odom frame=%s child=%s",
                src_world,
                src_body,
            )
            self.debug_printed = True

        if self.warn_if_frame_mismatch:
            if src_world and src_world != self.point_lio_world_frame:
                rospy.logwarn_throttle(
                    5.0,
                    "point_lio_frame_bridge: input header.frame_id is %s, expected %s",
                    src_world,
                    self.point_lio_world_frame,
                )
            if src_body and src_body != self.point_lio_body_frame:
                rospy.logwarn_throttle(
                    5.0,
                    "point_lio_frame_bridge: input child_frame_id is %s, expected %s",
                    src_body,
                    self.point_lio_body_frame,
                )

        odom_to_lidar = pose_to_matrix(msg.pose.pose)
        if self.use_lidar_to_base_tf:
            lidar_to_base = self.lookup_lidar_to_base(msg.header.stamp)
            if lidar_to_base is None:
                return
            odom_to_base = concatenate_matrices(odom_to_lidar, lidar_to_base)
        else:
            odom_to_base = odom_to_lidar

        translation = translation_from_matrix(odom_to_base)
        rotation = normalize_quaternion(quaternion_from_matrix(odom_to_base))

        out = Odometry()
        out.header = copy.deepcopy(msg.header)
        out.header.frame_id = self.standard_odom_frame
        out.child_frame_id = self.standard_base_frame
        out.pose = copy.deepcopy(msg.pose)
        out.pose.pose.position.x = float(translation[0])
        out.pose.pose.position.y = float(translation[1])
        out.pose.pose.position.z = float(translation[2])
        out.pose.pose.orientation.x = float(rotation[0])
        out.pose.pose.orientation.y = float(rotation[1])
        out.pose.pose.orientation.z = float(rotation[2])
        out.pose.pose.orientation.w = float(rotation[3])
        out.twist = copy.deepcopy(msg.twist)

        if self.republish_odom:
            self.odom_pub.publish(out)

        if self.publish_tf:
            odom_to_tf_child = self.output_tf_pose(odom_to_base)
            if odom_to_tf_child is None:
                return
            tf_translation = translation_from_matrix(odom_to_tf_child)
            tf_rotation = normalize_quaternion(quaternion_from_matrix(odom_to_tf_child))
            self.tf_broadcaster.sendTransform(
                (tf_translation[0], tf_translation[1], tf_translation[2]),
                (tf_rotation[0], tf_rotation[1], tf_rotation[2], tf_rotation[3]),
                out.header.stamp if out.header.stamp != rospy.Time(0) else rospy.Time.now(),
                self.tf_child_frame,
                self.standard_odom_frame,
            )


def main():
    rospy.init_node("point_lio_frame_bridge")
    PointLioFrameBridge()
    rospy.spin()


if __name__ == "__main__":
    main()
