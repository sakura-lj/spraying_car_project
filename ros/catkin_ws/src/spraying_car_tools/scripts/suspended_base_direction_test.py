#!/usr/bin/env python3
"""Publish short /cmd_vel steps for wheels-off-ground base direction checks."""

import sys

import rospy
from geometry_msgs.msg import Twist


CONFIRM_TEXT = "I_UNDERSTAND_WHEELS_ARE_OFF_GROUND"


def make_twist(linear_x=0.0, angular_z=0.0):
    msg = Twist()
    msg.linear.x = float(linear_x)
    msg.angular.z = float(angular_z)
    return msg


def publish_for_duration(pub, msg, duration, rate):
    end_time = rospy.Time.now() + rospy.Duration(duration)
    while not rospy.is_shutdown() and rospy.Time.now() < end_time:
        pub.publish(msg)
        rate.sleep()


def publish_stop(pub, rate, cycles=5):
    stop = make_twist()
    for _ in range(cycles):
        if rospy.is_shutdown():
            break
        pub.publish(stop)
        rate.sleep()


def require_confirmation():
    print("")
    print("SUSPENDED BASE DIRECTION TEST")
    print("This script only publishes /cmd_vel. It does not open /dev/ttyS3 directly.")
    print("Run only when the vehicle is raised and drive wheels are off the ground.")
    print("Flask must be stopped, the remote controller must be ready, and spray must be off.")
    print("Type exactly this confirmation string to continue:")
    print(CONFIRM_TEXT)
    try:
        answer = input("> ").strip()
    except EOFError:
        answer = ""
    if answer != CONFIRM_TEXT:
        print("Confirmation did not match. No non-zero /cmd_vel will be published.")
        return False
    return True


def main():
    rospy.init_node("suspended_base_direction_test")

    topic = rospy.get_param("~topic", "/cmd_vel")
    linear_x = float(rospy.get_param("~linear_x", 0.08))
    angular_z = float(rospy.get_param("~angular_z", 0.2))
    duration = float(rospy.get_param("~duration", 0.8))
    rate_hz = float(rospy.get_param("~rate", 10.0))
    require_confirm = bool(rospy.get_param("~require_confirm", True))
    skip_backward = bool(rospy.get_param("~skip_backward", False))
    skip_turning = bool(rospy.get_param("~skip_turning", False))

    duration = max(0.1, min(duration, 1.0))
    rate_hz = max(1.0, rate_hz)
    rate = rospy.Rate(rate_hz)
    pub = rospy.Publisher(topic, Twist, queue_size=1)
    rospy.sleep(0.5)

    rospy.logwarn("This script is for wheels-off-ground suspended testing only.")
    rospy.logwarn("It publishes /cmd_vel only and never opens /dev/ttyS3 directly.")
    rospy.logwarn("Keep spraying_car_base max_speed_duty low and be ready to stop immediately.")

    if require_confirm and not require_confirmation():
        publish_stop(pub, rate)
        return

    steps = [
        ("stop", 0.0, 0.0, 0.5),
        ("forward_slow", abs(linear_x), 0.0, duration),
        ("stop", 0.0, 0.0, 0.8),
    ]

    if not skip_backward:
        steps.extend([
            ("backward_slow", -abs(linear_x), 0.0, duration),
            ("stop", 0.0, 0.0, 0.8),
        ])

    if not skip_turning:
        steps.extend([
            ("left_slow", abs(linear_x), abs(angular_z), duration),
            ("stop", 0.0, 0.0, 0.8),
            ("right_slow", abs(linear_x), -abs(angular_z), duration),
            ("stop", 0.0, 0.0, 0.8),
        ])

    try:
        for name, step_linear_x, step_angular_z, step_duration in steps:
            if rospy.is_shutdown():
                break
            rospy.logwarn(
                "Step %s: linear.x=%.3f angular.z=%.3f duration=%.2f",
                name,
                step_linear_x,
                step_angular_z,
                step_duration,
            )
            publish_for_duration(
                pub,
                make_twist(step_linear_x, step_angular_z),
                step_duration,
                rate,
            )
            publish_stop(pub, rate)
    except KeyboardInterrupt:
        rospy.logwarn("Interrupted, publishing stop")
        publish_stop(pub, rate)
        sys.exit(130)
    finally:
        publish_stop(pub, rate)


if __name__ == "__main__":
    main()
