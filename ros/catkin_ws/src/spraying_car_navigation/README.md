这个包放自动导航相关配置。

包括：

move_base
global_costmap
local_costmap
teb_local_planner
map_server
amcl 或其他定位

推荐结构：

spraying_car_navigation/
├── launch/
│   ├── map_server.launch
│   ├── move_base.launch
│   └── navigation.launch
├── config/
│   ├── costmap_common_params.yaml
│   ├── global_costmap_params.yaml
│   ├── local_costmap_params.yaml
│   ├── move_base_params.yaml
│   └── teb_local_planner_params.yaml
├── maps/
│   ├── farm_map.yaml
│   └── farm_map.pgm
└── rviz/
    └── navigation.rviz

其中：

global_costmap_params.yaml       全局地图配置
local_costmap_params.yaml        局部避障地图配置
costmap_common_params.yaml       公共障碍物参数
teb_local_planner_params.yaml    TEB 局部规划器参数

农业车后续主要调这些文件。