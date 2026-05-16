#!/usr/bin/env python3
"""Verify STM32 base_state updates from short /cmd_vel commands.

This script publishes /cmd_vel only. It never opens /dev/ttyS3 or /dev/ttyACM0.
It checks software state reported on /spraying_car/base_state and does not prove
physical wheel or steering direction.
"""

import json
import sys
import threading

import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import String


CONFIRM_TEXT = "I_UNDERSTAND_THIS_SENDS_REAL_STM32_COMMANDS"


class ResultTracker:
    def __init__(self):
        self.pass_count = 0
        self.warn_count = 0
        self.fail_count = 0

    def pass_(self, message):
        self.pass_count += 1
        rospy.loginfo("[PASS] %s", message)

    def warn(self, message):
        self.warn_count += 1
        rospy.logwarn("[WARN] %s", message)

    def fail(self, message):
        self.fail_count += 1
        rospy.logerr("[FAIL] %s", message)

    def exit_code(self):
        return 1 if self.fail_count else 0


class BaseStateVerifier:
    def __init__(self):
        self.cmd_topic = rospy.get_param("~cmd_topic", "/cmd_vel")
        self.state_topic = rospy.get_param("~state_topic", "/spraying_car/base_state")
        self.require_confirm = bool(rospy.get_param("~require_confirm", True))
        self.duration = float(rospy.get_param("~duration", 0.5))
        self.turn_duration = float(rospy.get_param("~turn_duration", 2.0))
        self.linear_x = float(rospy.get_param("~linear_x", 0.05))
        self.angular_z = float(rospy.get_param("~angular_z", 0.2))
        self.skip_backward = bool(rospy.get_param("~skip_backward", False))
        self.skip_turning = bool(rospy.get_param("~skip_turning", False))
        self.state_timeout = float(rospy.get_param("~state_timeout", 1.0))
        self.rate_hz = float(rospy.get_param("~rate", 10.0))
        self.min_speed_duty = int(rospy.get_param("~min_speed_duty", 1))
        self.center_turn_position = int(rospy.get_param("~center_turn_position", 51))
        self.expected_uart_control_mode = int(rospy.get_param("~expected_uart_control_mode", 1))

        self.duration = max(0.1, min(self.duration, 1.0))
        self.turn_duration = max(2.0, self.turn_duration)
        self.rate_hz = max(1.0, self.rate_hz)

        self.condition = threading.Condition()
        self.latest_state = None
        self.latest_state_time = None
        self.state_history = []

        self.results = ResultTracker()
        self.cmd_pub = rospy.Publisher(self.cmd_topic, Twist, queue_size=1)
        self.state_sub = rospy.Subscriber(self.state_topic, String, self.state_callback, queue_size=20)
        self.rate = rospy.Rate(self.rate_hz)

        self.left_turn_position = None
        self.right_turn_position = None

    def state_callback(self, msg):
        try:
            state = json.loads(msg.data)
        except Exception as exc:
            self.results.warn("Failed to parse base_state JSON: %s" % exc)
            return
        with self.condition:
            self.latest_state = state
            self.latest_state_time = rospy.Time.now()
            self.state_history.append((self.latest_state_time, state))
            if len(self.state_history) > 500:
                self.state_history = self.state_history[-500:]
            self.condition.notify_all()

    def require_confirmation(self):
        if not self.require_confirm:
            return True
        print("")
        print("BASE STATE VERIFICATION TEST")
        print("This sends real /cmd_vel commands if spraying_car_base is running with dry_run=false.")
        print("It does not open serial ports directly and does not prove physical direction.")
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

    def publish_for_duration(self, msg, duration):
        end_time = rospy.Time.now() + rospy.Duration(duration)
        while not rospy.is_shutdown() and rospy.Time.now() < end_time:
            self.cmd_pub.publish(msg)
            self.rate.sleep()

    def publish_stop(self, cycles=5):
        stop = self.make_twist()
        for _ in range(cycles):
            if rospy.is_shutdown():
                break
            self.cmd_pub.publish(stop)
            self.rate.sleep()

    def wait_for_state_after(self, since):
        deadline = rospy.Time.now() + rospy.Duration(self.state_timeout)
        with self.condition:
            while not rospy.is_shutdown():
                if self.latest_state is not None and self.latest_state_time is not None:
                    if self.latest_state_time >= since:
                        return dict(self.latest_state)
                remaining = (deadline - rospy.Time.now()).to_sec()
                if remaining <= 0.0:
                    return None
                self.condition.wait(min(0.05, remaining))
        return None

    def get_latest_state_after(self, since):
        with self.condition:
            for stamp, state in reversed(self.state_history):
                if stamp >= since:
                    return dict(state)
        return None

    def get_states_after(self, since):
        with self.condition:
            return [(stamp, dict(state)) for stamp, state in self.state_history if stamp >= since]

    def get_int_field(self, state, field):
        value = state.get(field)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def log_state_summary(self, name, state):
        fields = [
            "speed_duty",
            "direction",
            "is_open",
            "turn_cmd_position",
            "turn_target_encoder",
            "turn_encoder_position",
            "uart_control_mode",
            "using_ext_status",
        ]
        summary = ", ".join("%s=%s" % (field, state.get(field)) for field in fields)
        rospy.loginfo("State after %s: %s", name, summary)

    def log_turn_series(self, name, samples):
        if not samples:
            rospy.logwarn("%s: no turn state samples collected", name)
            return
        positions = []
        targets = []
        encoders = []
        for _, state in samples:
            positions.append(self.get_int_field(state, "turn_cmd_position"))
            targets.append(self.get_int_field(state, "turn_target_encoder"))
            encoders.append(self.get_int_field(state, "turn_encoder_position"))
        rospy.loginfo("%s: turn_cmd_position series=%s", name, positions)
        rospy.loginfo("%s: turn_target_encoder series=%s", name, targets)
        rospy.loginfo(
            "%s: turn_encoder_position series=%s (informational only; encoder is currently not connected)",
            name,
            encoders,
        )

    def check_common_status(self, name, state):
        using_ext_status = bool(state.get("using_ext_status", False))
        if using_ext_status:
            self.results.pass_("%s: using_ext_status=true" % name)
        else:
            self.results.warn("%s: using_ext_status=false; extended STM32 status was not confirmed" % name)

        if "uart_control_mode" in state:
            mode = int(state.get("uart_control_mode", -1))
            if mode == self.expected_uart_control_mode:
                self.results.pass_("%s: uart_control_mode=%d" % (name, mode))
            else:
                message = "%s: uart_control_mode=%d, expected %d for serial control" % (
                    name,
                    mode,
                    self.expected_uart_control_mode,
                )
                if using_ext_status:
                    self.results.fail(message)
                else:
                    self.results.warn(message)

    def check_step(self, name, state):
        self.log_state_summary(name, state)
        self.check_common_status(name, state)

        direction = int(state.get("direction", -1))
        speed_duty = int(state.get("speed_duty", -1))
        turn_position = state.get("turn_cmd_position", None)
        if turn_position is not None:
            turn_position = int(turn_position)

        if name == "stop":
            if direction == 0:
                self.results.pass_("stop: direction=0")
            else:
                self.results.fail("stop: direction=%d, expected 0" % direction)
            if speed_duty <= self.min_speed_duty + 1:
                self.results.pass_("stop: speed_duty=%d near min_speed_duty=%d" % (speed_duty, self.min_speed_duty))
            else:
                self.results.fail("stop: speed_duty=%d, expected near %d" % (speed_duty, self.min_speed_duty))
        elif name == "forward_slow":
            if direction == 1:
                self.results.pass_("forward_slow: direction=1")
            else:
                self.results.fail("forward_slow: direction=%d, expected 1" % direction)
            if speed_duty > self.min_speed_duty:
                self.results.pass_("forward_slow: speed_duty=%d > %d" % (speed_duty, self.min_speed_duty))
            else:
                self.results.fail("forward_slow: speed_duty=%d, expected > %d" % (speed_duty, self.min_speed_duty))
        elif name == "backward_slow":
            if direction == 2:
                self.results.pass_("backward_slow: direction=2")
            else:
                self.results.fail("backward_slow: direction=%d, expected 2" % direction)
            if speed_duty > self.min_speed_duty:
                self.results.pass_("backward_slow: speed_duty=%d > %d" % (speed_duty, self.min_speed_duty))
            else:
                self.results.fail("backward_slow: speed_duty=%d, expected > %d" % (speed_duty, self.min_speed_duty))
        elif name == "left_slow":
            self.left_turn_position = turn_position
        elif name == "right_slow":
            self.right_turn_position = turn_position

    def check_turn_position(self, name, turn_position):
        if turn_position is None:
            self.results.fail("%s: turn_cmd_position missing" % name)
            return
        if turn_position == self.center_turn_position:
            self.results.fail(
                "%s: turn_cmd_position=%d, expected offset from %d"
                % (name, turn_position, self.center_turn_position)
            )
        else:
            self.results.pass_(
                "%s: turn_cmd_position=%d offset from center=%d"
                % (name, turn_position, self.center_turn_position)
            )

    def check_turn_step(self, name, state, samples):
        self.log_state_summary(name, state)
        self.check_common_status(name, state)
        self.log_turn_series(name, samples)

        valid_positions = [
            self.get_int_field(sample, "turn_cmd_position")
            for _, sample in samples
            if self.get_int_field(sample, "turn_cmd_position") is not None
        ]
        offset_positions = [
            position for position in valid_positions
            if position != self.center_turn_position
        ]
        observed_position = offset_positions[-1] if offset_positions else (
            valid_positions[-1] if valid_positions else None
        )

        self.check_turn_position(name, observed_position)
        if name == "left_slow":
            self.left_turn_position = observed_position
        elif name == "right_slow":
            self.right_turn_position = observed_position

    def check_turn_pair(self):
        if self.skip_turning:
            return
        if self.left_turn_position is None or self.right_turn_position is None:
            self.results.warn("left/right turn pair not fully observed")
            return
        left_delta = self.left_turn_position - self.center_turn_position
        right_delta = self.right_turn_position - self.center_turn_position
        if left_delta * right_delta < 0:
            self.results.pass_(
                "left/right turn_cmd_position are opposite: left=%d right=%d center=%d"
                % (self.left_turn_position, self.right_turn_position, self.center_turn_position)
            )
        else:
            self.results.fail(
                "left/right turn_cmd_position are not opposite: left=%d right=%d center=%d"
                % (self.left_turn_position, self.right_turn_position, self.center_turn_position)
            )

    def run_step(self, name, linear_x, angular_z, duration):
        rospy.logwarn("Step %s: linear.x=%.3f angular.z=%.3f duration=%.2f", name, linear_x, angular_z, duration)
        start_time = rospy.Time.now()
        self.publish_for_duration(self.make_twist(linear_x, angular_z), duration)
        state = self.get_latest_state_after(start_time)
        if state is None:
            state = self.wait_for_state_after(start_time)
        if state is None:
            self.results.fail("%s: no /spraying_car/base_state received within %.2f s" % (name, self.state_timeout))
            return None
        if name in ("left_slow", "right_slow"):
            self.check_turn_step(name, state, self.get_states_after(start_time))
        else:
            self.check_step(name, state)
        return state

    def build_steps(self):
        steps = [
            ("stop", 0.0, 0.0, 0.5),
            ("forward_slow", abs(self.linear_x), 0.0, self.duration),
            ("stop", 0.0, 0.0, 0.5),
        ]
        if not self.skip_backward:
            steps.extend([
                ("backward_slow", -abs(self.linear_x), 0.0, self.duration),
                ("stop", 0.0, 0.0, 0.5),
            ])
        if not self.skip_turning:
            steps.extend([
                ("left_slow", abs(self.linear_x), abs(self.angular_z), self.turn_duration),
                ("stop", 0.0, 0.0, 0.5),
                ("right_slow", abs(self.linear_x), -abs(self.angular_z), self.turn_duration),
                ("stop", 0.0, 0.0, 0.5),
            ])
        return steps

    def run(self):
        rospy.sleep(0.5)
        rospy.logwarn("base_state_verification_test publishes /cmd_vel only; it never opens serial ports directly.")
        rospy.logwarn("This verifies STM32 software state only and does not prove physical wheel direction.")
        if not self.require_confirmation():
            self.publish_stop()
            return 1

        try:
            for name, linear_x, angular_z, duration in self.build_steps():
                if rospy.is_shutdown():
                    break
                self.run_step(name, linear_x, angular_z, duration)
                if name != "stop":
                    self.publish_stop()
            self.check_turn_pair()
        except KeyboardInterrupt:
            rospy.logwarn("Interrupted, publishing stop")
            self.publish_stop()
            return 130
        finally:
            self.publish_stop()

        rospy.loginfo(
            "Result summary: PASS=%d WARN=%d FAIL=%d",
            self.results.pass_count,
            self.results.warn_count,
            self.results.fail_count,
        )
        return self.results.exit_code()


def main():
    rospy.init_node("base_state_verification_test")
    verifier = BaseStateVerifier()
    sys.exit(verifier.run())


if __name__ == "__main__":
    main()
