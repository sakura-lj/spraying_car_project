#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist


def main():
    rospy.init_node("cmd_vel_test")

    linear_x = float(rospy.get_param("~linear_x", 0.2))
    angular_z = float(rospy.get_param("~angular_z", 0.0))
    topic = rospy.get_param("~topic", "/cmd_vel")
    repeat = int(rospy.get_param("~repeat", 1))
    rate_hz = float(rospy.get_param("~rate", 1.0))

    pub = rospy.Publisher(topic, Twist, queue_size=1)
    rate = rospy.Rate(rate_hz)
    rospy.sleep(0.5)

    msg = Twist()
    msg.linear.x = linear_x
    msg.angular.z = angular_z

    for _ in range(max(1, repeat)):
        if rospy.is_shutdown():
            break
        rospy.loginfo("Publishing cmd_vel test: linear.x=%s angular.z=%s", linear_x, angular_z)
        pub.publish(msg)
        rate.sleep()


if __name__ == "__main__":
    main()
