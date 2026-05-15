建议把第三方包单独放到：

catkin_ws/src/third_party/

例如：

third_party/
├── point_lio_unilidar/
├── unilidar_sdk/
├── teb_local_planner/
├── robot_localization/
└── serial/

好处是：

你自己的代码和别人的代码分开
方便升级第三方包
方便 git 管理
不容易误改源码

原则：

不要直接修改第三方包源码
如果要改参数，在自己的 spraying_car_xxx/config 里写
如果要改启动方式，在自己的 spraying_car_bringup/launch 里 include 它