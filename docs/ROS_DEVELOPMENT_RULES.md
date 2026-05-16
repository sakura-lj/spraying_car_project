# ROS Development Rules

本文档规定农业喷药无人车后续 ROS 化开发规则。目标是逐步接入自动驾驶，同时保护当前遥控器、Web 控制、GPS、摄像头、LiDAR 和建图基线。

## 1. 仓库边界

- 不要直接修改 `ros/catkin_ws/src/third_party/` 下的第三方源码，除非确认没有其他可行方案。
- 需要改参数时，优先在自有包的 `config/` 中覆盖。
- 需要改启动流程时，优先在自有包的 `launch/` 中 include 第三方 launch。
- 必须修改第三方源码时，应单独记录原因、修改文件、上游版本和回退方式。
- 不要把临时调试脚本塞进正式控制包；调试工具放入 `spraying_car_tools`。

## 2. 串口占用规则

STM32 控制串口在当前基线中为 `/dev/ttyS3`。同一时间只能有一个进程打开该串口。

禁止行为：

- Flask 和 ROS 节点同时占用 `/dev/ttyS3`。
- 导航节点直接打开 STM32 串口。
- waypoint 节点直接打开 STM32 串口。
- Web 页面或前端脚本直接操作 STM32 串口。
- 任意测试脚本在未确认串口空闲时直接向 STM32 发送运动命令。

允许的串口拥有者：

- Web 串口模式：`web/upper/app.py` 独占 STM32 串口。
- ROS 自动驾驶模式：`spraying_car_base` 独占 STM32 串口。

切换控制后端时，必须先停止旧拥有者，再启动新拥有者。不得依赖两个进程竞争串口锁。

## 3. 自动驾驶控制链路

ROS 自动驾驶最终只能通过以下链路控制底盘：

```text
/cmd_vel -> spraying_car_base -> STM32 -> 底盘执行机构
```

规则：

- `spraying_car_base` 是 ROS 侧唯一允许操作 STM32 控制串口的正式底盘节点。
- `move_base`、TEB、waypoint、Web 页面都只能发布目标、状态或 `/cmd_vel`，不能直接写 STM32 串口。
- 导航栈输出必须先进入 `/cmd_vel`，再由 `spraying_car_base` 做限速、超时、急停和协议转换。
- Web 控制接入 ROS 后，也必须通过 ROS 控制接口或 `/cmd_vel`，不能新增第二条串口控制通道。
- `/cmd_vel` 超时后，`spraying_car_base` 必须主动输出停车命令。

## 4. 急停优先级

急停优先级最高，高于遥控器、Web、导航、waypoint、建图和任何自动任务。

急停规则：

- 任意急停触发后，底盘目标速度必须立即归零。
- 急停状态未解除前，`spraying_car_base` 不得执行新的 `/cmd_vel`。
- Web 急停、ROS 急停、遥控器接管和硬件安全机制不得互相屏蔽。
- 导航和 waypoint 节点不得在急停状态下反复重发运动命令来抵消停车。
- 急停恢复必须是显式动作，不能靠定时器或新目标自动恢复。

## 5. TF、URDF 与导航规则

- `spraying_car_description` 负责 URDF/XACRO 和车辆几何模型。
- 标准 TF 目标应逐步收敛到 `map -> odom -> base_link -> sensor frames`。
- LiDAR/SLAM 的坐标系不能直接替代 `base_link`。
- 导航配置必须依赖清晰的 TF 树和里程计，不得用临时 frame 名称硬接 move_base。
- 车辆尺寸、轴距、转向角、速度上限必须来自明确配置，不要散落硬编码在多个节点里。

## 6. 安全默认值

- 默认启动状态应为停车。
- 串口断开、协议解析失败、ROS Master 异常、`/cmd_vel` 超时、急停触发时都应停车。
- 未完成速度标定前，不得把速度档位解释为真实 m/s。
- 未完成状态回传扩展前，不得把 Flask 或 STM32 当前状态包当作真实里程计来源。
- 未实现电池电压、液位、RTK 或图像识别闭环前，不得让这些字段参与自动驾驶决策。

## 7. 开发顺序建议

推荐顺序：

1. 先实现 `spraying_car_base`，打通 `/cmd_vel -> STM32`，并加入串口互斥、超时停车和急停保护。
2. 再实现 URDF/TF，明确 `base_link`、传感器安装位和里程计来源。
3. 再封装 LiDAR 和 point_lio 的自有 launch/config，不直接改 third_party。
4. 再接 move_base/TEB。
5. 最后接 waypoint 和 Web 到 ROS 控制后端。

任何阶段都不能以破坏遥控器驾驶闭环或 Web 远程控制闭环作为代价。
