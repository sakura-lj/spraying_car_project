#!/usr/bin/env python3
"""Archive a point_lio PCD map into the project maps directory."""

import argparse
import datetime as _dt
import os
from pathlib import Path
import re
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SOURCE_CANDIDATES = (
    PROJECT_ROOT / "third_party/catkin_point_lio_unilidar/PCD/scans.pcd",
    PROJECT_ROOT / "ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/PCD/scans.pcd",
    PROJECT_ROOT / "ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/src/point_lio_unilidar/PCD/scans.pcd",
)
MAP_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def ros_args_to_cli(argv):
    converted = []
    for item in argv:
        if item.startswith("__"):
            continue
        if ":=" in item:
            key, value = item.split(":=", 1)
            key = key.lstrip("_").replace("_", "-")
            if key:
                converted.extend(["--" + key, value])
            continue
        converted.append(item)
    return converted


def resolve_path(value, default_base=PROJECT_ROOT):
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = default_base / path
    return path.resolve()


def validate_map_name(map_name):
    if not map_name or not MAP_NAME_RE.match(map_name):
        raise ValueError("map_name must match [A-Za-z0-9][A-Za-z0-9_.-]*")
    return map_name


def shell_quote_yaml(value):
    text = "" if value is None else str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped + '"'


def write_metadata(path, metadata):
    lines = []
    for key, value in metadata.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {shell_quote_yaml(item)}")
            else:
                lines.append(f"{key}: []")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {shell_quote_yaml(value)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_source_pcd(source_pcd):
    if source_pcd:
        path = resolve_path(source_pcd)
        if path.exists():
            return path
        raise FileNotFoundError(f"source_pcd does not exist: {path}")

    for candidate in DEFAULT_SOURCE_CANDIDATES:
        if candidate.exists():
            return candidate

    tried = "\n".join(f"  - {p}" for p in DEFAULT_SOURCE_CANDIDATES)
    raise FileNotFoundError("No default point_lio PCD found. Tried:\n" + tried)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pcd", default="", help="Source PCD path. If omitted, common point_lio paths are tried.")
    parser.add_argument("--map-name", required=True, help="Map base name without extension.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "maps/pcd"), help="Output directory for archived PCD.")
    parser.add_argument("--metadata-dir", default=str(PROJECT_ROOT / "maps/metadata"), help="Output directory for metadata YAML.")
    parser.add_argument("--location-name", default="unknown")
    parser.add_argument("--environment-type", default="orchard")
    parser.add_argument("--lidar-model", default="Unitree L1RM")
    parser.add_argument("--slam-algorithm", default="point_lio_unilidar")
    parser.add_argument("--grid-map-path", default="")
    parser.add_argument("--resolution", type=float, default=0.0)
    parser.add_argument("--origin", default="")
    parser.add_argument("--height-filter-min", type=float, default=0.0)
    parser.add_argument("--height-filter-max", type=float, default=0.0)
    parser.add_argument("--notes", default="")
    parser.add_argument("--known-issues", default="")
    return parser.parse_args(ros_args_to_cli(argv))


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        map_name = validate_map_name(args.map_name)
        source = find_source_pcd(args.source_pcd)
        output_dir = resolve_path(args.output_dir)
        metadata_dir = resolve_path(args.metadata_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        target_pcd = output_dir / f"{map_name}.pcd"
        metadata_path = metadata_dir / f"{map_name}.meta.yaml"
        shutil.copy2(str(source), str(target_pcd))

        metadata = {
            "map_name": map_name,
            "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "location_name": args.location_name,
            "environment_type": args.environment_type,
            "lidar_model": args.lidar_model,
            "slam_algorithm": args.slam_algorithm,
            "pcd_source_path": str(source),
            "pcd_archived_path": str(target_pcd),
            "grid_map_path": args.grid_map_path,
            "resolution": args.resolution,
            "origin": args.origin,
            "height_filter_min": args.height_filter_min,
            "height_filter_max": args.height_filter_max,
            "notes": args.notes,
            "known_issues": [x.strip() for x in args.known_issues.split(";") if x.strip()],
        }
        write_metadata(metadata_path, metadata)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Archived PCD: {target_pcd}")
    print(f"Wrote metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
