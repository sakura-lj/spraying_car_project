#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist


def main():
    rospy.init_node("cmd_vel_zero")
    topic = rospy.get_param("~topic", "/cmd_vel")
    pub = rospy.Publisher(topic, Twist, queue_size=1, latch=True)
    rospy.sleep(0.5)
    pub.publish(Twist())
    rospy.loginfo("Published one zero Twist to %s", topic)


if __name__ == "__main__":
    main()
