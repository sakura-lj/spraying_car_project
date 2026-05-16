#!/usr/bin/env python3
"""Probe STM32 turn command state through /spraying_car/base_state.

This script publishes /cmd_vel only. It never opens serial ports directly and
does not prove physical steering direction.
"""

import json
import sys
import threading

import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import String


CONFIRM_TEXT = "I_UNDERSTAND_THIS_SENDS_REAL_STM32_TURN_COMMANDS"


class TurnExtStatusProbe:
    def __init__(self):
        self.cmd_topic = rospy.get_param("~cmd_topic", "/cmd_vel")
        self.state_topic = rospy.get_param("~state_topic", "/spraying_car/base_state")
        self.require_confirm = bool(rospy.get_param("~require_confirm", True))
        self.linear_x = float(rospy.get_param("~linear_x", 0.05))
        self.angular_z = float(rospy.get_param("~angular_z", 0.2))
        self.duration = max(2.0, float(rospy.get_param("~duration", 2.0)))
        self.stop_duration = max(0.5, float(rospy.get_param("~stop_duration", 0.8)))
        self.rate_hz = max(1.0, float(rospy.get_param("~rate", 10.0)))

        self.condition = threading.Condition()
        self.latest_state = None
        self.latest_state_time = None
        self.last_print_key = None

        self.cmd_pub = rospy.Publisher(self.cmd_topic, Twist, queue_size=1)
        self.state_sub = rospy.Subscriber(self.state_topic, String, self.state_callback, queue_size=20)
        self.rate = rospy.Rate(self.rate_hz)

    def state_callback(self, msg):
        try:
            state = json.loads(msg.data)
        except Exception as exc:
            rospy.logwarn("Failed to parse base_state JSON: %s", exc)
            return
        with self.condition:
            self.latest_state = state
            self.latest_state_time = rospy.Time.now()
            self.condition.notify_all()

    def require_confirmation(self):
        if not self.require_confirm:
            return True
        print("")
        print("TURN EXT STATUS PROBE")
        print("This publishes real /cmd_vel if spraying_car_base is running with dry_run=false.")
        print("It does not open serial ports and does not prove physical steering direction.")
        print("Vehicle should be raised or otherwise safe. Flask must be stopped. Spray must be off.")
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

    def make_twist(self, linear_x=0.0, angular_z=0.0):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        return msg

    def publish_stop(self, duration=None):
        self.publish_and_print("center_stop", self.make_twist(), duration or self.stop_duration)

    def publish_and_print(self, label, msg, duration):
        rospy.logwarn("Probe %s: linear.x=%.3f angular.z=%.3f duration=%.2f", label, msg.linear.x, msg.angular.z, duration)
        end_time = rospy.Time.now() + rospy.Duration(duration)
        while not rospy.is_shutdown() and rospy.Time.now() < end_time:
            self.cmd_pub.publish(msg)
            self.print_latest_state(label)
            self.rate.sleep()

    def print_latest_state(self, label):
        with self.condition:
            if self.latest_state is None or self.latest_state_time is None:
                return
            stamp = self.latest_state_time.to_sec()
            state = dict(self.latest_state)

        raw_ext = state.get("raw_ext_status_payload_hex") or state.get("raw_ext_status_packet_hex")
        key = (
            label,
            state.get("ext_status_seq"),
            state.get("using_ext_status"),
            state.get("turn_cmd_position"),
            state.get("turn_target_encoder"),
            state.get("turn_encoder_position"),
            raw_ext,
        )
        if key == self.last_print_key:
            return
        self.last_print_key = key
        rospy.loginfo(
            "%s state: stamp=%.3f ext_status_seq=%s using_ext_status=%s "
            "turn_cmd_position=%s turn_target_encoder=%s turn_encoder_position=%s raw_ext=%s",
            label,
            stamp,
            state.get("ext_status_seq"),
            state.get("using_ext_status"),
            state.get("turn_cmd_position"),
            state.get("turn_target_encoder"),
            state.get("turn_encoder_position"),
            raw_ext,
        )

    def run(self):
        rospy.sleep(0.5)
        rospy.logwarn("turn_ext_status_probe publishes /cmd_vel only; it never opens serial ports directly.")
        rospy.logwarn("This verifies STM32 software state only and does not prove physical steering direction.")
        if not self.require_confirmation():
            self.publish_stop(0.5)
            return 1

        try:
            self.publish_and_print("left_slow", self.make_twist(abs(self.linear_x), abs(self.angular_z)), self.duration)
            self.publish_stop()
            self.publish_and_print("right_slow", self.make_twist(abs(self.linear_x), -abs(self.angular_z)), self.duration)
            self.publish_stop()
        except KeyboardInterrupt:
            rospy.logwarn("Interrupted, publishing center/stop")
            self.publish_stop(0.8)
            return 130
        finally:
            self.publish_stop(0.8)
        return 0


def main():
    rospy.init_node("turn_ext_status_probe")
    probe = TurnExtStatusProbe()
    sys.exit(probe.run())


if __name__ == "__main__":
    main()
