# Maps Directory

This directory stores mapping outputs and navigation map artifacts for the spraying car project.

## Structure

- `pcd/`: archived point_lio PCD maps, usually copied from the upstream `point_lio_unilidar/PCD/scans.pcd` output.
- `grid/`: 2D occupancy grid maps for later `map_server` and navigation tests, normally `.pgm` plus `.yaml`.
- `routes/`: reserved for future waypoint route files. Stage 7 only keeps the directory.
- `metadata/`: metadata for each map, including collection context, conversion parameters, known issues, and source paths.

## Naming

Use stable ASCII names:

```text
orchard_name_area_name_YYYYMMDD_vNN
```

Examples:

```text
orchard_test_area_20260516_v01.pcd
orchard_test_area_20260516_v01.yaml
orchard_test_area_20260516_v01.pgm
orchard_test_area_20260516_v01.meta.yaml
```

The same base name should be used across `pcd/`, `grid/`, and `metadata/` so the source PCD, generated grid map, and metadata remain traceable.

## Metadata Fields

Map metadata should include at least:

- `map_name`
- `created_at`
- `location_name`
- `environment_type`
- `lidar_model`
- `slam_algorithm`
- `pcd_source_path`
- `grid_map_path`
- `resolution`
- `origin`
- `height_filter_min`
- `height_filter_max`
- `notes`
- `known_issues`

Stage 7 only establishes the storage and conversion workflow. It does not implement navigation, move_base, TEB, waypoint, or formal odometry.
