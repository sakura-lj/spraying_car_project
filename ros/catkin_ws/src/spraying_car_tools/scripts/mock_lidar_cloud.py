#!/usr/bin/env python3
"""MOCK ONLY: publish tiny LiDAR/IMU topics for development tests.

Do not use on a real vehicle.
"""

import rospy
from sensor_msgs import point_cloud2
from sensor_msgs.msg import Imu, PointCloud2
from std_msgs.msg import Header


def main():
    rospy.init_node("mock_lidar_cloud")
    topic = rospy.get_param("~topic", "/unilidar/cloud")
    imu_topic = rospy.get_param("~imu_topic", "/unilidar/imu")
    frame_id = rospy.get_param("~frame_id", "lidar_link")
    imu_frame_id = rospy.get_param("~imu_frame_id", "imu_link")
    rate_hz = float(rospy.get_param("~rate", 5.0))
    publish_obstacle = bool(rospy.get_param("~publish_obstacle", True))
    publish_imu = bool(rospy.get_param("~publish_imu", True))

    rospy.logwarn("mock_lidar_cloud is for development only. It is forbidden for real vehicle navigation.")

    pub = rospy.Publisher(topic, PointCloud2, queue_size=5)
    imu_pub = rospy.Publisher(imu_topic, Imu, queue_size=5)
    rate = rospy.Rate(max(1.0, rate_hz))
    points = []
    if publish_obstacle:
        points = [
            (2.0, -0.3, 0.4),
            (2.0, 0.0, 0.4),
            (2.0, 0.3, 0.4),
            (2.2, 0.0, 0.8),
        ]

    while not rospy.is_shutdown():
        header = Header()
        header.stamp = rospy.Time.now()
        header.frame_id = frame_id
        pub.publish(point_cloud2.create_cloud_xyz32(header, points))
        if publish_imu:
            imu = Imu()
            imu.header.stamp = header.stamp
            imu.header.frame_id = imu_frame_id
            imu.orientation.w = 1.0
            imu_pub.publish(imu)
        rate.sleep()


if __name__ == "__main__":
    main()
