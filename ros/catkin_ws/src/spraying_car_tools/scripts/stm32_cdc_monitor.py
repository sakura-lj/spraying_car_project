#!/usr/bin/env python3
"""Read-only STM32 USB CDC debug monitor.

This tool is for observing debug output from /dev/ttyACM0. It never sends
control frames and must not be used as the vehicle control port.
"""

import argparse
from datetime import datetime
import select
import os
import sys
import termios
import time


DEFAULT_KEYWORDS = [
    "CMD Received",
    "SPEED",
    "DIR",
    "TURN",
    "SPRAY",
    "STATUS",
    "EXT STATUS",
    "FORWARD",
    "BACK",
    "STOP",
    "L",
    "R",
    "C",
]


def ros_args_to_cli(argv):
    converted = []
    for arg in argv:
        if arg.startswith("__"):
            continue
        if arg.startswith("_") and ":=" in arg:
            key, value = arg[1:].split(":=", 1)
            converted.extend([f"--{key.replace('_', '-')}", value])
        else:
            converted.append(arg)
    return converted


def str_to_bool(value):
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Read STM32 USB CDC debug output without writing any data.",
    )
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=0.1)
    parser.add_argument("--output-file", default="")
    parser.add_argument("--max-lines", type=int, default=0, help="0 means unlimited")
    parser.add_argument("--max-seconds", type=float, default=0.0, help="0 means unlimited")
    parser.add_argument("--timestamp", type=str_to_bool, default=True)
    parser.add_argument("--raw-hex", type=str_to_bool, default=True)
    parser.add_argument("--ascii", type=str_to_bool, default=True)
    parser.add_argument(
        "--keyword-filter",
        default="",
        help="Comma separated keywords to show, or 'default' for common STM32 debug keywords.",
    )
    return parser.parse_args(ros_args_to_cli(argv))


def parse_keyword_filter(value):
    if not value:
        return []
    if str(value).strip().lower() == "default":
        return DEFAULT_KEYWORDS
    return [item.strip() for item in str(value).split(",") if item.strip()]


def timestamp_prefix(enabled=True):
    if not enabled:
        return ""
    return datetime.now().isoformat(timespec="milliseconds") + " "


def format_record(data, args, keywords):
    ascii_text = data.decode("utf-8", errors="replace").rstrip("\r\n")
    if keywords and not any(keyword in ascii_text for keyword in keywords):
        return ""

    parts = []
    if args.ascii:
        parts.append("ASCII: " + ascii_text)
    if args.raw_hex:
        parts.append("HEX: " + " ".join(f"{byte:02x}" for byte in data))
    if not parts:
        return ""
    return timestamp_prefix(args.timestamp) + " | ".join(parts)


def format_line(data, timestamp=True, raw_hex=False):
    if raw_hex:
        body = " ".join(f"{byte:02x}" for byte in data)
    else:
        body = data.decode("utf-8", errors="replace").rstrip("\r\n")
    if timestamp:
        return f"{datetime.now().isoformat(timespec='milliseconds')} {body}"
    return body


def open_output_file(path):
    if not path:
        return None
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    return open(path, "a", encoding="utf-8")


class PosixReadOnlySerialReader:
    def __init__(self, port, baud, timeout):
        baud_attr = f"B{baud}"
        baud_const = getattr(termios, baud_attr, None)
        if baud_const is None:
            raise ValueError(f"Unsupported baud rate for termios fallback: {baud}")
        self._fd = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
        self._timeout = timeout
        self._old_attrs = termios.tcgetattr(self._fd)

        attrs = termios.tcgetattr(self._fd)
        attrs[0] = termios.IGNPAR
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = baud_const
        attrs[5] = baud_const
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = max(0, int(timeout * 10))
        termios.tcsetattr(self._fd, termios.TCSANOW, attrs)

    def read(self, size):
        readable, _, _ = select.select([self._fd], [], [], self._timeout)
        if not readable:
            return b""
        try:
            return os.read(self._fd, size)
        except BlockingIOError:
            return b""

    def close(self):
        if self._fd is None:
            return
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, self._old_attrs)
        finally:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def open_reader(args):
    if os.name != "posix":
        raise RuntimeError("Pure read-only serial monitoring is currently implemented for POSIX systems only.")
    return PosixReadOnlySerialReader(args.port, args.baud, args.timeout)


def emit_line(data, args, out):
    line = format_line(data, timestamp=args.timestamp, raw_hex=args.raw_hex)
    print(line, flush=True)
    if out:
        out.write(line + "\n")
        out.flush()


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    keywords = parse_keyword_filter(args.keyword_filter)

    out = None
    line_count = 0
    start_time = time.monotonic()
    try:
        out = open_output_file(args.output_file)
        print(
            f"Opening STM32 USB CDC debug port {args.port} at {args.baud} baud "
            "(pure read-only monitor; no data will be written).",
            flush=True,
        )
        print(
            "Do not use /dev/ttyACM0 as the vehicle control port; /dev/ttyS3 "
            "remains the STM32 control serial port.",
            flush=True,
        )
        print(
            "This tool opens the CDC device with O_RDONLY and never sends STM32 control frames.",
            flush=True,
        )
        if keywords:
            print("Keyword filter enabled: " + ", ".join(keywords), flush=True)

        try:
            reader = open_reader(args)
        except FileNotFoundError as exc:
            print(f"Device does not exist: {args.port}: {exc}", file=sys.stderr)
            return 1
        except PermissionError as exc:
            print(f"Permission denied opening {args.port}: {exc}", file=sys.stderr)
            print("Check device permissions or add the user to the dialout group.", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"Failed to open {args.port}: {exc}", file=sys.stderr)
            print("Check whether the device exists and whether the user is in the dialout group.", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Failed to configure {args.port}: {exc}", file=sys.stderr)
            return 1

        with reader:
            while True:
                if args.max_seconds > 0.0 and time.monotonic() - start_time >= args.max_seconds:
                    return 0
                data = reader.read(256)
                if not data:
                    continue

                line = format_record(data, args, keywords)
                if not line:
                    continue

                print(line, flush=True)
                if out:
                    out.write(line + "\n")
                    out.flush()
                line_count += 1
                if args.max_lines > 0 and line_count >= args.max_lines:
                    return 0
    except KeyboardInterrupt:
        print("\nSTM32 CDC monitor stopped.", file=sys.stderr)
        return 0
    finally:
        if out:
            out.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
