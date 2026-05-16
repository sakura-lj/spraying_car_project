#!/usr/bin/env python3

import json
import os
import sys
import threading

import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import String


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


class VehicleBaseNode:
    def __init__(self):
        self._load_params()
        self.protocol = self._load_protocol_module()

        self.serial = None
        self.serial_lock = threading.Lock()
        self.parser = self.protocol.PacketParser()

        self.connected = False
        self.error_count = 0
        self.last_cmd_time = None
        self.timeout_active = False
        self.last_status_query_time = rospy.Time(0)
        self.last_ext_status_time = None
        self.raw_status = None
        self.using_ext_status = False

        self.spray_state = 0
        self.speed_duty = self.min_speed_duty
        self.direction = 0
        self.is_open = 0
        self.turn_cmd_position = self.center_turn_position
        self.turn_target_encoder = 0
        self.turn_encoder_position = 0
        self.uart_control_mode = 0
        self.safety_state = 0
        self.fault_code = 0
        self.battery_mv = 0

        self.state_pub = rospy.Publisher(self.state_topic, String, queue_size=10)
        self.cmd_sub = rospy.Subscriber(self.cmd_topic, Twist, self.cmd_vel_callback, queue_size=10)

        if self.dry_run:
            rospy.logwarn("spraying_car_base_node dry_run=true: no real serial port will be opened.")
        else:
            rospy.logwarn(
                "spraying_car_base_node dry_run=false: stop web/upper/start.py before testing, "
                "otherwise Flask may already occupy %s.",
                self.port,
            )
            self._open_serial_or_fail()

        rospy.on_shutdown(self.on_shutdown)
        self.start_time = rospy.Time.now()

    def _load_params(self):
        self.port = rospy.get_param("~port", "/dev/ttyS3")
        self.baud = int(rospy.get_param("~baud", 115200))
        self.dry_run = bool(rospy.get_param("~dry_run", True))
        self.protocol_module_path = rospy.get_param("~protocol_module_path", "../../../web/upper")

        self.cmd_topic = rospy.get_param("~cmd_topic", "/cmd_vel")
        self.state_topic = rospy.get_param("~state_topic", "/spraying_car/base_state")

        self.control_rate = float(rospy.get_param("~control_rate", 20.0))
        self.status_query_rate = float(rospy.get_param("~status_query_rate", 2.0))
        self.ext_status_fallback_timeout = float(rospy.get_param("~ext_status_fallback_timeout", 3.0))
        self.cmd_timeout = float(rospy.get_param("~cmd_timeout", 0.5))

        self.stop_linear_threshold = float(rospy.get_param("~stop_linear_threshold", 0.03))
        self.max_linear_speed = float(rospy.get_param("~max_linear_speed", 0.6))
        self.max_angular_z = float(rospy.get_param("~max_angular_z", 1.0))

        self.min_speed_duty = int(rospy.get_param("~min_speed_duty", 1))
        self.max_speed_duty = int(rospy.get_param("~max_speed_duty", 40))

        self.center_turn_position = int(rospy.get_param("~center_turn_position", 51))
        self.min_turn_position = int(rospy.get_param("~min_turn_position", 1))
        self.max_turn_position = int(rospy.get_param("~max_turn_position", 101))
        self.turn_direction_sign = int(rospy.get_param("~turn_direction_sign", 1))

        self.send_spray_off_on_timeout = bool(rospy.get_param("~send_spray_off_on_timeout", True))
        self.send_turn_center_on_timeout = bool(rospy.get_param("~send_turn_center_on_timeout", True))

        self.min_speed_duty = int(clamp(self.min_speed_duty, 1, 102))
        self.max_speed_duty = int(clamp(self.max_speed_duty, self.min_speed_duty, 102))
        self.center_turn_position = int(clamp(self.center_turn_position, 1, 101))
        self.min_turn_position = int(clamp(self.min_turn_position, 1, self.center_turn_position))
        self.max_turn_position = int(clamp(self.max_turn_position, self.center_turn_position, 101))
        if self.turn_direction_sign not in (-1, 1):
            rospy.logwarn("turn_direction_sign=%s is invalid; using 1", self.turn_direction_sign)
            self.turn_direction_sign = 1

    def _load_protocol_module(self):
        candidates = self._protocol_path_candidates()
        for candidate in candidates:
            if candidate and os.path.isdir(candidate):
                if candidate not in sys.path:
                    sys.path.insert(0, candidate)
                try:
                    import vehicle_protocol

                    rospy.loginfo("Loaded vehicle_protocol.py from %s", candidate)
                    return vehicle_protocol
                except ImportError as exc:
                    rospy.logdebug("vehicle_protocol import failed from %s: %s", candidate, exc)

        raise ImportError(
            "Unable to import vehicle_protocol.py. Set ROS param ~protocol_module_path "
            "to the web/upper directory. Tried: %s" % candidates
        )

    def _protocol_path_candidates(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        package_dir = os.path.abspath(os.path.join(script_dir, ".."))
        catkin_ws_dir = os.path.abspath(os.path.join(package_dir, "..", ".."))
        project_root = os.path.abspath(os.path.join(package_dir, "..", "..", "..", ".."))

        configured = self.protocol_module_path
        candidates = []
        if os.path.isabs(configured):
            candidates.append(configured)
        else:
            candidates.extend([
                os.path.abspath(os.path.join(os.getcwd(), configured)),
                os.path.abspath(os.path.join(package_dir, configured)),
                os.path.abspath(os.path.join(catkin_ws_dir, configured)),
                os.path.abspath(os.path.join(project_root, configured)),
            ])

        candidates.append(os.path.join(project_root, "web", "upper"))

        unique = []
        for path in candidates:
            if path not in unique:
                unique.append(path)
        return unique

    def _open_serial_or_fail(self):
        try:
            import serial

            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.0,
                write_timeout=0.1,
            )
            self.serial.flush()
            self.connected = bool(self.serial.is_open)
            rospy.loginfo("Connected STM32 serial port %s at %s baud", self.port, self.baud)
        except Exception as exc:
            self.connected = False
            self.error_count += 1
            raise RuntimeError(
                "Failed to open STM32 serial port %s. Stop web/upper/start.py first and "
                "check serial permissions. Original error: %s" % (self.port, exc)
            )

    def cmd_vel_callback(self, msg):
        self.last_cmd_time = rospy.Time.now()
        self.timeout_active = False

        direction, speed_duty, turn_position = self.map_cmd_vel(msg)
        rospy.loginfo(
            "cmd_vel mapped: linear.x=%.3f angular.z=%.3f -> direction=%d speed_duty=%d turn_position=%d",
            msg.linear.x,
            msg.angular.z,
            direction,
            speed_duty,
            turn_position,
        )

        self.send_drive_command(direction, speed_duty, turn_position, reason="cmd_vel")

    def map_cmd_vel(self, msg):
        linear_x = float(msg.linear.x)
        angular_z = float(msg.angular.z)

        if abs(linear_x) < self.stop_linear_threshold:
            direction = 0
            speed_duty = self.min_speed_duty
        else:
            direction = 1 if linear_x > 0.0 else 2
            max_linear = max(self.max_linear_speed, self.stop_linear_threshold)
            ratio = clamp(abs(linear_x) / max_linear, 0.0, 1.0)
            speed_duty = int(round(
                self.min_speed_duty + ratio * (self.max_speed_duty - self.min_speed_duty)
            ))

        if abs(angular_z) < 1e-6 or self.max_angular_z <= 0.0:
            turn_position = self.center_turn_position
        else:
            normalized = clamp((angular_z * self.turn_direction_sign) / self.max_angular_z, -1.0, 1.0)
            if normalized >= 0.0:
                turn_position = self.center_turn_position + normalized * (
                    self.max_turn_position - self.center_turn_position
                )
            else:
                turn_position = self.center_turn_position + normalized * (
                    self.center_turn_position - self.min_turn_position
                )
            turn_position = int(round(turn_position))

        speed_duty = int(clamp(speed_duty, 1, 102))
        direction = int(clamp(direction, 0, 2))
        turn_position = int(clamp(turn_position, 1, 101))
        return direction, speed_duty, turn_position

    def send_drive_command(self, direction, speed_duty, turn_position, reason):
        self._send_packet(
            "direction=%d (%s)" % (direction, reason),
            self.protocol.build_direction_packet(direction),
        )
        self._send_packet(
            "speed_duty=%d (%s)" % (speed_duty, reason),
            self.protocol.build_speed_packet(speed_duty),
        )
        self._send_packet(
            "turn_position=%d (%s)" % (turn_position, reason),
            self.protocol.build_turn_packet(turn_position),
        )

        self.direction = direction
        self.speed_duty = speed_duty

    def send_safe_stop(self, reason, include_spray=False, include_turn_center=True):
        rospy.logwarn("Sending safe stop: %s", reason)
        self._send_packet(
            "direction=0 (%s)" % reason,
            self.protocol.build_direction_packet(0),
        )
        self._send_packet(
            "speed_duty=%d (%s)" % (self.min_speed_duty, reason),
            self.protocol.build_speed_packet(self.min_speed_duty),
        )
        if include_spray:
            self._send_packet(
                "spray_state=0 (%s)" % reason,
                self.protocol.build_spray_packet(0),
            )
            self.spray_state = 0
        if include_turn_center:
            self._send_packet(
                "turn_position=%d (%s)" % (self.center_turn_position, reason),
                self.protocol.build_turn_packet(self.center_turn_position),
            )

        self.direction = 0
        self.speed_duty = self.min_speed_duty

    def _send_packet(self, label, packet):
        packet_hex = self._packet_hex(packet)
        if self.dry_run:
            rospy.loginfo("[dry_run] would send %s packet=%s", label, packet_hex)
            return True

        if not self.serial or not self.serial.is_open:
            self.connected = False
            self.error_count += 1
            rospy.logerr("Serial not connected; cannot send %s packet=%s", label, packet_hex)
            return False

        try:
            with self.serial_lock:
                self.serial.write(packet)
            self.connected = True
            rospy.logdebug("Sent %s packet=%s", label, packet_hex)
            return True
        except Exception as exc:
            self.connected = False
            self.error_count += 1
            rospy.logerr("Serial write failed for %s packet=%s: %s", label, packet_hex, exc)
            return False

    def _packet_hex(self, packet):
        return bytes(packet).hex(" ")

    def read_serial_once(self):
        if self.dry_run or not self.serial or not self.serial.is_open:
            return

        try:
            waiting = self.serial.in_waiting
            if waiting <= 0:
                return
            with self.serial_lock:
                data = self.serial.read(waiting)
            for packet in self.parser.feed(data):
                self.handle_packet(packet)
        except Exception as exc:
            self.connected = False
            self.error_count += 1
            rospy.logerr("Serial read failed: %s", exc)

    def handle_packet(self, packet):
        try:
            ext_status = self.protocol.parse_ext_status_response(packet)
        except Exception as exc:
            self.error_count += 1
            rospy.logwarn("Failed to parse extended status packet: %s", exc)
            return

        if ext_status:
            self.spray_state = int(ext_status["spray_state"])
            self.speed_duty = int(ext_status["speed_duty"])
            self.direction = int(ext_status["direction"])
            self.is_open = int(ext_status["is_open"])
            self.turn_cmd_position = int(ext_status["turn_cmd_position"])
            self.turn_target_encoder = int(ext_status["turn_target_encoder"])
            self.turn_encoder_position = int(ext_status["turn_encoder_position"])
            self.uart_control_mode = int(ext_status["uart_control_mode"])
            self.safety_state = int(ext_status["safety_state"])
            self.fault_code = int(ext_status["fault_code"])
            self.battery_mv = int(ext_status["battery_mv"])
            self.raw_status = {
                "type": "extended",
                "packet_hex": self._packet_hex(packet),
                "data": ext_status,
            }
            self.using_ext_status = True
            self.last_ext_status_time = rospy.Time.now()
            self.connected = True
            return

        try:
            status = self.protocol.parse_status_response(packet)
        except Exception as exc:
            self.error_count += 1
            rospy.logwarn("Failed to parse legacy status packet: %s", exc)
            return

        if not status:
            return

        self.spray_state = int(status["spray_state"])
        self.speed_duty = int(status["speed_duty"])
        self.direction = int(status["direction"])
        self.is_open = int(status["is_open"])
        self.raw_status = {
            "type": "legacy",
            "packet_hex": self._packet_hex(packet),
            "data": [self.spray_state, self.speed_duty, self.direction, self.is_open],
        }
        self.using_ext_status = False
        self.connected = True

    def maybe_query_status(self):
        if self.status_query_rate <= 0:
            return

        now = rospy.Time.now()
        interval = rospy.Duration(1.0 / self.status_query_rate)
        if now - self.last_status_query_time >= interval:
            self._send_packet("ext_status_query", self.protocol.build_ext_status_query_packet())
            if self.should_query_legacy_status(now):
                self._send_packet("status_query_fallback", self.protocol.build_status_query_packet())
            self.last_status_query_time = now

    def should_query_legacy_status(self, now):
        if self.last_ext_status_time is None:
            elapsed = (now - self.start_time).to_sec()
        else:
            elapsed = (now - self.last_ext_status_time).to_sec()
        return elapsed >= self.ext_status_fallback_timeout

    def check_cmd_timeout(self):
        now = rospy.Time.now()
        if self.last_cmd_time is None:
            elapsed = (now - self.start_time).to_sec()
        else:
            elapsed = (now - self.last_cmd_time).to_sec()

        if elapsed <= self.cmd_timeout:
            return

        if not self.timeout_active:
            self.send_safe_stop(
                "cmd_timeout",
                include_spray=self.send_spray_off_on_timeout,
                include_turn_center=self.send_turn_center_on_timeout,
            )
            self.timeout_active = True

    def publish_state(self):
        state = {
            "spray_state": self.spray_state,
            "speed_duty": self.speed_duty,
            "direction": self.direction,
            "is_open": self.is_open,
            "turn_cmd_position": self.turn_cmd_position,
            "turn_target_encoder": self.turn_target_encoder,
            "turn_encoder_position": self.turn_encoder_position,
            "uart_control_mode": self.uart_control_mode,
            "safety_state": self.safety_state,
            "fault_code": self.fault_code,
            "battery_mv": self.battery_mv,
            "connected": self.connected,
            "using_ext_status": self.using_ext_status,
            "last_cmd_time": self.last_cmd_time.to_sec() if self.last_cmd_time else None,
            "mode": "dry_run" if self.dry_run else "serial",
            "error_count": self.error_count,
            "raw_status": self.raw_status,
        }
        self.state_pub.publish(String(data=json.dumps(state, ensure_ascii=False)))

    def spin(self):
        rate = rospy.Rate(self.control_rate)
        while not rospy.is_shutdown():
            self.read_serial_once()
            self.maybe_query_status()
            self.check_cmd_timeout()
            self.publish_state()
            rate.sleep()

    def on_shutdown(self):
        try:
            self.send_safe_stop(
                "node_shutdown",
                include_spray=True,
                include_turn_center=True,
            )
        except Exception as exc:
            rospy.logwarn("Safe stop on shutdown failed: %s", exc)

        if self.serial:
            try:
                self.serial.close()
            except Exception as exc:
                rospy.logwarn("Failed to close serial port: %s", exc)


def main():
    rospy.init_node("spraying_car_base_node")
    try:
        VehicleBaseNode().spin()
    except Exception as exc:
        rospy.logfatal("spraying_car_base_node failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
