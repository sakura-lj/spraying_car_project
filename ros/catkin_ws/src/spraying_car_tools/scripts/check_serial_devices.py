#!/usr/bin/env python3
"""List serial devices without opening or writing to them."""

import glob
import grp
import os
from pathlib import Path
import pwd
import stat


PATTERNS = ["/dev/ttyS*", "/dev/ttyUSB*", "/dev/ttyACM*"]


def device_role(path):
    if path == "/dev/ttyS3":
        return "vehicle control UART candidate; spraying_car_base uses this for STM32 control"
    if path == "/dev/ttyACM0":
        return "STM32 USB CDC debug monitor candidate; read-only logs only"
    if path == "/dev/ttyUSB0":
        return "GPS or L1RM candidate; device name may conflict after replug"
    return "unclassified serial device"


def mode_string(mode):
    return stat.filemode(mode)


def owner_group(st):
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    return owner, group


def serial_links():
    links = {}
    for directory in ("/dev/serial/by-id", "/dev/serial/by-path"):
        base = Path(directory)
        if not base.exists():
            continue
        for link in base.iterdir():
            if not link.is_symlink():
                continue
            try:
                target = str(link.resolve())
            except OSError:
                continue
            links.setdefault(target, []).append(str(link))
    return links


def main():
    devices = sorted({path for pattern in PATTERNS for path in glob.glob(pattern)})
    links = serial_links()

    if not devices:
        print("No /dev/ttyS*, /dev/ttyUSB*, or /dev/ttyACM* devices found.")
        return 0

    print("Serial devices found. This script is read-only and does not open any port.\n")
    for path in devices:
        try:
            st = os.stat(path)
        except OSError as exc:
            print(f"{path}: cannot stat device: {exc}")
            continue
        owner, group = owner_group(st)
        print(path)
        print(f"  role: {device_role(path)}")
        print(f"  permissions: {mode_string(st.st_mode)} owner={owner} group={group}")
        if path in links:
            print("  symlinks:")
            for link in sorted(links[path]):
                print(f"    {link}")
        else:
            print("  symlinks: none")
    print("\nRecommended future udev names:")
    print("  /dev/spraying_car_lidar")
    print("  /dev/spraying_car_gps")
    print("  /dev/spraying_car_stm32_debug")
    print("Keep /dev/ttyS3 reserved for vehicle control.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
