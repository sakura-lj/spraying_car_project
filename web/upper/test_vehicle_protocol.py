#!/usr/bin/env python3

import unittest

from vehicle_protocol import (
    CMD_EXT_STATUS_RESPONSE,
    CMD_STATUS_RESPONSE,
    PacketParser,
    ProtocolError,
    build_ext_status_query_packet,
    build_direction_packet,
    build_speed_packet,
    build_spray_packet,
    build_status_query_packet,
    build_turn_packet,
    calculate_checksum,
    pack_packet,
    parse_status_response,
    parse_ext_status_response,
)


class VehicleProtocolTest(unittest.TestCase):
    def test_build_spray_packet(self):
        self.assertEqual(bytes(build_spray_packet(True)), b"\xAA\x01\x01\x01\x01\x55")
        self.assertEqual(bytes(build_spray_packet(False)), b"\xAA\x01\x01\x00\x00\x55")

    def test_build_speed_packet(self):
        self.assertEqual(bytes(build_speed_packet(51)), b"\xAA\x02\x01\x33\x33\x55")

    def test_build_direction_packet(self):
        self.assertEqual(bytes(build_direction_packet(2)), b"\xAA\x03\x01\x02\x02\x55")

    def test_build_turn_packet(self):
        self.assertEqual(bytes(build_turn_packet(51)), b"\xAA\x04\x01\x33\x33\x55")

    def test_build_status_query_packet(self):
        self.assertEqual(bytes(build_status_query_packet()), b"\xAA\xFF\x01\x00\x00\x55")

    def test_build_ext_status_query_packet(self):
        self.assertEqual(bytes(build_ext_status_query_packet()), b"\xAA\x06\x01\x00\x00\x55")

    def test_checksum_only_uses_data_bytes(self):
        packet = bytes(pack_packet(0x02, [0x01]))
        self.assertEqual(packet, b"\xAA\x02\x01\x01\x01\x55")
        self.assertEqual(calculate_checksum([0x01, 0x02, 0x03]), 0x06)

    def test_parser_reads_complete_packet(self):
        packet = bytes(build_spray_packet(True))
        parser = PacketParser()
        self.assertEqual(parser.feed(packet), [packet])

    def test_parser_handles_sticky_packets(self):
        first = bytes(build_speed_packet(12))
        second = bytes(build_direction_packet(1))
        parser = PacketParser()
        self.assertEqual(parser.feed(first + second), [first, second])

    def test_parser_handles_partial_packet(self):
        packet = bytes(build_turn_packet(60))
        parser = PacketParser()
        self.assertEqual(parser.feed(packet[:3]), [])
        self.assertEqual(parser.feed(packet[3:]), [packet])

    def test_parser_discards_bad_head_and_bad_checksum(self):
        valid = bytes(build_spray_packet(True))
        bad_checksum = b"\xAA\x01\x01\x01\x00\x55"

        parser = PacketParser()
        self.assertEqual(parser.feed(b"\x00\x99" + valid), [valid])

        parser = PacketParser()
        self.assertEqual(parser.feed(bad_checksum + valid), [valid])

    def test_parse_status_response(self):
        packet = bytes(pack_packet(CMD_STATUS_RESPONSE, [1, 51, 2, 1]))
        status = parse_status_response(packet)
        self.assertEqual(status["spray_state"], 1)
        self.assertEqual(status["speed_duty"], 51)
        self.assertEqual(status["direction"], 2)
        self.assertEqual(status["is_open"], 1)
        self.assertEqual(status["relay_state"], 1)

    def test_parse_ext_status_response(self):
        payload = self._build_ext_payload(
            turn_target_encoder=123456,
            turn_encoder_position=-123456,
            fault_code=0x1234,
            battery_mv=12000,
            reserved_u16=0xABCD,
            reserved_u32=0x12345678,
        )
        packet = bytes(pack_packet(CMD_EXT_STATUS_RESPONSE, payload))
        status = parse_ext_status_response(packet)

        self.assertEqual(status["protocol_version"], 1)
        self.assertEqual(status["spray_state"], 1)
        self.assertEqual(status["speed_duty"], 40)
        self.assertEqual(status["direction"], 2)
        self.assertEqual(status["is_open"], 1)
        self.assertEqual(status["turn_cmd_position"], 76)
        self.assertEqual(status["turn_target_encoder"], 123456)
        self.assertEqual(status["turn_encoder_position"], -123456)
        self.assertEqual(status["uart_control_mode"], 1)
        self.assertEqual(status["safety_state"], 0)
        self.assertEqual(status["fault_code"], 0x1234)
        self.assertEqual(status["battery_mv"], 12000)
        self.assertEqual(status["reserved_u16"], 0xABCD)
        self.assertEqual(status["ext_status_seq"], 0xABCD)
        self.assertEqual(status["reserved_u32"], 0x12345678)

    def test_parse_ext_status_seq_alias(self):
        payload = self._build_ext_payload(reserved_u16=37)
        status = parse_ext_status_response(payload)
        self.assertEqual(status["reserved_u16"], 37)
        self.assertEqual(status["ext_status_seq"], 37)

    def test_ext_status_little_endian_signed_i32(self):
        payload = self._build_ext_payload(turn_target_encoder=-1, turn_encoder_position=-2147483648)
        status = parse_ext_status_response(payload)
        self.assertEqual(status["turn_target_encoder"], -1)
        self.assertEqual(status["turn_encoder_position"], -2147483648)

    def test_ext_status_little_endian_uint16(self):
        payload = self._build_ext_payload(fault_code=0xBEEF, battery_mv=0x1234)
        status = parse_ext_status_response(payload)
        self.assertEqual(status["fault_code"], 0xBEEF)
        self.assertEqual(status["battery_mv"], 0x1234)

    def test_parser_reads_ext_status_response_packet(self):
        payload = self._build_ext_payload()
        packet = bytes(pack_packet(CMD_EXT_STATUS_RESPONSE, payload))
        parser = PacketParser()
        self.assertEqual(parser.feed(packet), [packet])

    def test_parse_ext_status_rejects_wrong_length(self):
        with self.assertRaises(ProtocolError):
            parse_ext_status_response(b"\x01\x02")

    def _build_ext_payload(
        self,
        turn_target_encoder=0,
        turn_encoder_position=0,
        fault_code=0,
        battery_mv=0,
        reserved_u16=0,
        reserved_u32=0,
    ):
        payload = bytearray(26)
        payload[0] = 1
        payload[1] = 1
        payload[2] = 40
        payload[3] = 2
        payload[4] = 1
        payload[5] = 76
        payload[6:10] = int(turn_target_encoder).to_bytes(4, "little", signed=True)
        payload[10:14] = int(turn_encoder_position).to_bytes(4, "little", signed=True)
        payload[14] = 1
        payload[15] = 0
        payload[16:18] = int(fault_code).to_bytes(2, "little", signed=False)
        payload[18:20] = int(battery_mv).to_bytes(2, "little", signed=False)
        payload[20:22] = int(reserved_u16).to_bytes(2, "little", signed=False)
        payload[22:26] = int(reserved_u32).to_bytes(4, "little", signed=False)
        return payload


if __name__ == "__main__":
    unittest.main()
