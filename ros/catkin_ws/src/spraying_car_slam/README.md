这个包放建图相关内容。

你用的是：

宇树 L1RM
point_lio_unilidar

建议不要直接在 point_lio_unilidar 包里乱改配置，而是在 agrocar_slam 中写自己的 launch 和 config。

例如：

spraying_car_slam/
├── launch/
│   ├── point_lio_mapping.launch
│   └── save_map.launch
├── config/
│   ├── point_lio.yaml
│   └── lidar_filter.yaml
├── maps/
│   ├── pcd/
│   │   └── scans.pcd
│   └── grid/
│       ├── farm_map.yaml
│       └── farm_map.pgm

这样第三方包更新时，不会把你的配置覆盖掉。