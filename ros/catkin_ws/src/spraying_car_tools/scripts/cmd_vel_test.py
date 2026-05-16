#!/usr/bin/env python3

import time

import rospy
from geometry_msgs.msg import Twist


PRESETS = {
    "stop": (0.0, 0.0, 0.5),
    "forward_slow": (0.08, 0.0, 0.8),
    "backward_slow": (-0.08, 0.0, 0.8),
    "left_slow": (0.05, 0.2, 0.8),
    "right_slow": (0.05, -0.2, 0.8),
}


def publish_for_duration(pub, msg, duration, rate):
    if duration <= 0.0:
        pub.publish(msg)
        return

    end_time = rospy.Time.now() + rospy.Duration(duration)
    while not rospy.is_shutdown() and rospy.Time.now() < end_time:
        pub.publish(msg)
        rate.sleep()


def publish_stop(pub, rate):
    stop = Twist()
    for _ in range(3):
        if rospy.is_shutdown():
            break
        pub.publish(stop)
        rate.sleep()


def main():
    rospy.init_node("cmd_vel_test")

    preset = rospy.get_param("~preset", "stop")
    if preset not in PRESETS:
        rospy.logfatal(
            "Unknown preset '%s'. Valid presets: %s",
            preset,
            ", ".join(sorted(PRESETS.keys())),
        )
        return

    default_linear_x, default_angular_z, default_duration = PRESETS[preset]
    linear_x = float(rospy.get_param("~linear_x", default_linear_x))
    angular_z = float(rospy.get_param("~angular_z", default_angular_z))
    duration = float(rospy.get_param("~duration", default_duration))
    rate_hz = float(rospy.get_param("~rate", 10.0))
    repeat = int(rospy.get_param("~repeat", 1))
    stop_after_test = bool(rospy.get_param("~stop_after_test", True))
    topic = rospy.get_param("~topic", "/cmd_vel")

    rate_hz = max(0.1, rate_hz)
    repeat = max(1, repeat)
    pub = rospy.Publisher(topic, Twist, queue_size=1)
    rate = rospy.Rate(rate_hz)
    rospy.sleep(0.5)

    msg = Twist()
    msg.linear.x = linear_x
    msg.angular.z = angular_z

    rospy.logwarn("cmd_vel_test publishes only to %s and never opens a serial port.", topic)
    rospy.logwarn(
        "Use with spraying_car_base dry_run=true unless explicitly performing wheels-off-ground testing."
    )
    rospy.loginfo(
        "cmd_vel_test preset=%s linear.x=%.3f angular.z=%.3f duration=%.3f rate=%.3f repeat=%d stop_after_test=%s",
        preset,
        linear_x,
        angular_z,
        duration,
        rate_hz,
        repeat,
        stop_after_test,
    )
    if duration > 2.0:
        rospy.logerr(
            "Requested duration %.3f s is longer than 2 seconds. This is unsafe for suspended direction tests.",
            duration,
        )

    for index in range(repeat):
        if rospy.is_shutdown():
            break
        rospy.loginfo(
            "Publishing cmd_vel test %d/%d: linear.x=%.3f angular.z=%.3f duration=%.3f",
            index + 1,
            repeat,
            linear_x,
            angular_z,
            duration,
        )
        publish_for_duration(pub, msg, duration, rate)
        if repeat > 1 and index + 1 < repeat:
            time.sleep(0.1)

    if stop_after_test:
        rospy.loginfo("Publishing zero cmd_vel after test")
        publish_stop(pub, rate)


if __name__ == "__main__":
    main()
