"""STM32 UART protocol helpers for the spraying car.

This module is pure protocol code. Importing it never opens a serial port.
"""

PACKET_HEAD = 0xAA
PACKET_TAIL = 0x55

BUFFER_SIZE = 256
READ_MAX_SIZE = 256
RXBUFFER_LEN = 128
MAX_PACKET_DATA_LEN = 127

CMD_SPRAY_CONTROL = 0x01
CMD_SPEED_CONTROL = 0x02
CMD_DIRECTION_CONTROL = 0x03
CMD_TURN_CONTROL = 0x04
CMD_STATUS_RESPONSE = 0x05
CMD_EXT_STATUS_QUERY = 0x06
CMD_EXT_STATUS_RESPONSE = 0x07
CMD_STATUS_QUERY = 0xFF

EXT_STATUS_PAYLOAD_LEN = 26


class ProtocolError(ValueError):
    """Raised when a packet does not match the STM32 UART protocol."""


def _to_bytes(data_bytes):
    if data_bytes is None:
        return None
    return bytes(bytearray(data_bytes))


def calculate_checksum(data_bytes):
    """Return checksum over data bytes only."""
    data = _to_bytes(data_bytes)
    if data is None:
        raise ProtocolError("data bytes cannot be None")
    return sum(data) % 256


checksum = calculate_checksum


def pack_packet(cmd_type, data_bytes):
    """Pack one protocol frame.

    Frame format:
      [0xAA][type][len][data...][checksum][0x55]
    """
    data = _to_bytes(data_bytes)
    if data is None or len(data) == 0:
        return None

    length = len(data)
    if length > BUFFER_SIZE or length > 0xFF:
        return None

    packet = bytearray(length + 5)
    packet[0] = PACKET_HEAD
    packet[1] = int(cmd_type) & 0xFF
    packet[2] = length
    packet[3:3 + length] = data
    packet[3 + length] = calculate_checksum(data)
    packet[4 + length] = PACKET_TAIL
    return packet


pack_data = pack_packet


def parse_packet(packet):
    """Validate and split one complete protocol frame."""
    packet_bytes = bytes(packet)
    if len(packet_bytes) < 5:
        raise ProtocolError("packet too short")
    if packet_bytes[0] != PACKET_HEAD:
        raise ProtocolError("invalid packet head")

    packet_type = packet_bytes[1]
    length = packet_bytes[2]
    if length > MAX_PACKET_DATA_LEN:
        raise ProtocolError("data length too large")

    expected_len = length + 5
    if len(packet_bytes) != expected_len:
        raise ProtocolError("packet length mismatch")
    if packet_bytes[-1] != PACKET_TAIL:
        raise ProtocolError("invalid packet tail")

    data = packet_bytes[3:3 + length]
    received_checksum = packet_bytes[3 + length]
    calculated_checksum = calculate_checksum(data)
    if received_checksum != calculated_checksum:
        raise ProtocolError("checksum mismatch")

    return {
        "type": packet_type,
        "length": length,
        "data": data,
        "checksum": received_checksum,
        "packet": packet_bytes,
    }


class PacketParser:
    """Incremental parser for a serial byte stream."""

    def __init__(self, max_packet_data_len=MAX_PACKET_DATA_LEN, max_buffer_len=RXBUFFER_LEN):
        self.max_packet_data_len = max_packet_data_len
        self.max_buffer_len = max_buffer_len
        self.buffer = bytearray()
        self.parsing = False

    def reset(self):
        self.buffer = bytearray()
        self.parsing = False

    def feed(self, data):
        packets = []
        for byte in bytes(data):
            packet = self.feed_byte(byte)
            if packet is not None:
                packets.append(packet)
        return packets

    def feed_byte(self, byte):
        byte = int(byte) & 0xFF

        if byte == PACKET_HEAD and not self.parsing:
            self.buffer = bytearray([PACKET_HEAD])
            self.parsing = True
            return None

        if not self.parsing:
            return None

        self.buffer.append(byte)

        if len(self.buffer) > self.max_buffer_len:
            self.reset()
            return None

        if len(self.buffer) < 3:
            return None

        length = self.buffer[2]
        if length > self.max_packet_data_len:
            self.reset()
            return None

        expected_len = length + 5
        if len(self.buffer) < expected_len:
            return None

        packet = bytes(self.buffer)
        self.reset()

        try:
            parse_packet(packet)
        except ProtocolError:
            return None
        return packet


def parse_status_response(packet_or_data):
    """Parse the current 4-byte legacy status response into a dict."""
    data = bytes(packet_or_data)

    if len(data) >= 5 and data[0] == PACKET_HEAD:
        parsed = parse_packet(data)
        if parsed["type"] != CMD_STATUS_RESPONSE:
            return None
        data = parsed["data"]

    if len(data) < 4:
        return None

    return {
        "spray_state": data[0],
        "speed_duty": data[1],
        "direction": data[2],
        "is_open": data[3],
        "relay_state": data[3],
    }


def _read_i32_le(data, offset):
    return int.from_bytes(data[offset:offset + 4], byteorder="little", signed=True)


def _read_u16_le(data, offset):
    return int.from_bytes(data[offset:offset + 2], byteorder="little", signed=False)


def _read_u32_le(data, offset):
    return int.from_bytes(data[offset:offset + 4], byteorder="little", signed=False)


def parse_ext_status_response(packet_or_data):
    """Parse the 26-byte extended status response into a dict."""
    data = bytes(packet_or_data)

    if len(data) >= 5 and data[0] == PACKET_HEAD:
        parsed = parse_packet(data)
        if parsed["type"] != CMD_EXT_STATUS_RESPONSE:
            return None
        data = parsed["data"]

    if len(data) != EXT_STATUS_PAYLOAD_LEN:
        raise ProtocolError(
            "extended status payload length must be %d bytes, got %d"
            % (EXT_STATUS_PAYLOAD_LEN, len(data))
        )

    reserved_u16 = _read_u16_le(data, 20)

    return {
        "protocol_version": data[0],
        "spray_state": data[1],
        "speed_duty": data[2],
        "direction": data[3],
        "is_open": data[4],
        "turn_cmd_position": data[5],
        "turn_target_encoder": _read_i32_le(data, 6),
        "turn_encoder_position": _read_i32_le(data, 10),
        "uart_control_mode": data[14],
        "safety_state": data[15],
        "fault_code": _read_u16_le(data, 16),
        "battery_mv": _read_u16_le(data, 18),
        "reserved_u16": reserved_u16,
        "ext_status_seq": reserved_u16,
        "reserved_u32": _read_u32_le(data, 22),
    }


def build_spray_packet(state):
    return pack_packet(CMD_SPRAY_CONTROL, [1 if state else 0])


def build_speed_packet(speed):
    speed = max(1, min(102, int(speed)))
    return pack_packet(CMD_SPEED_CONTROL, [speed])


def build_direction_packet(direction):
    direction = max(0, min(2, int(direction)))
    return pack_packet(CMD_DIRECTION_CONTROL, [direction])


def build_turn_packet(position):
    position = max(1, min(101, int(position)))
    return pack_packet(CMD_TURN_CONTROL, [position])


def build_status_query_packet(query_byte=0):
    return pack_packet(CMD_STATUS_QUERY, [int(query_byte) & 0xFF])


def build_ext_status_query_packet(query_byte=0):
    return pack_packet(CMD_EXT_STATUS_QUERY, [int(query_byte) & 0xFF])
