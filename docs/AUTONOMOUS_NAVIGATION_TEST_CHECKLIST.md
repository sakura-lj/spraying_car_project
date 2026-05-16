# 自动导航测试安全检查表

此检查表用于任何实车自动导航或 `/cmd_vel` 实车验证前后。阶段 8C 默认仍以 dry-run 为主；未完成以下检查前不要关闭 `base_dry_run`。

## mock 验证通过条件

- 依赖检查全部 OK；如果 roscore 未启动，只允许 `roscore connection` 在启动前为 MISSING。
- `navigation_mock_test.launch` 能启动。
- `move_base` 无 fatal error。
- TEB 插件加载成功。
- global costmap 正常发布。
- local costmap 正常发布。
- `odom -> base_link` 可达。
- `base_footprint -> base_link` 可用。
- `base_link -> lidar_link` 可用。
- `/cmd_vel` 能被发布。
- `spraying_car_base dry-run` 能接收 `/cmd_vel`。
- `base_dry_run=true`。
- mock 节点只出现在 `navigation_mock_test.launch`，禁止用于实车。

## STM32 CDC 调试口使用说明

- `/dev/ttyACM0` 是 STM32 USB CDC 虚拟串口。
- 当前识别为 `STM32 Virtual ComPort`。
- SerialNumber 为 `358437793233`。
- `/dev/ttyACM0` 只用于观察 STM32 调试输出。
- `/dev/ttyACM0` 不用于车辆控制。
- 不要向 `/dev/ttyACM0` 发送控制命令或 STM32 控制帧。
- 车辆控制仍使用 `/dev/ttyS3`。
- 实车测试时可以单独开一个终端监控 `/dev/ttyACM0` 日志。
- 如果 `/dev/ttyACM0` 权限不足，检查设备权限或 `dialout` 用户组。

只读监控示例：

```bash
rosrun spraying_car_tools stm32_cdc_monitor.py _port:=/dev/ttyACM0 _baud:=115200
```

## 测试前

- 车辆架空或轮子离地，先进行首次 `/cmd_vel` 实车方向验证。
- Flask 已停止，避免占用 `/dev/ttyS3`。
- `spraying_car_base dry_run=true` 已测试通过。
- 串口 `/dev/ttyS3` 可打开。
- 遥控器接管有效。
- 软件急停有效。
- 周围无人。
- 最大速度档位限制为低值。
- L1RM 固定牢靠。
- 雷达点云正常。
- `/slam_odom` 正常。
- `odom -> base_link` 正常。
- local costmap 正常。
- `/cmd_vel` 前进方向已确认。
- `/cmd_vel` 转向方向已确认。

## 阶段 8F 架空方向验证条件

- 只验证 `/cmd_vel -> spraying_car_base -> STM32`，不启动 `move_base`、TEB、point_lio 或导航 launch。
- 车辆必须架空，驱动轮不能接触地面。
- Flask 必须停止，确认 `web/upper/start.py`、`app.py`、`flask` 没有运行。
- 检查 `/dev/ttyS3` 未被占用；可以用 `lsof /dev/ttyS3` 或 `fuser -v /dev/ttyS3`。
- `/dev/ttyACM0` 只允许用 `stm32_cdc_monitor.py` 只读观察，不得写入。
- 使用 `base_real_suspended_test.launch`，默认 `dry_run=true`。
- 只有人工显式设置 `dry_run:=false port:=/dev/ttyS3` 才允许真实打开控制串口。
- `max_speed_duty` 保持低值，当前架空测试 launch 默认 `8`。
- 每个非零动作不超过 `1.0 s`。
- `suspended_base_direction_test.py` 默认要求输入确认字符串 `I_UNDERSTAND_WHEELS_ARE_OFF_GROUND`。
- 测试结束、Ctrl-C、cmd timeout 和节点退出都应停车。

## 阶段 8F-1 CDC 状态验证条件

- CDC 状态验证可以作为架空物理方向测试前的前置步骤。
- CDC 状态验证只证明 STM32 软件状态变化，不能证明车轮真实方向。
- `/dev/ttyACM0` 是 STM32 USB CDC 调试口，只读监控，禁止写入。
- `/dev/ttyS3` 是 STM32 控制串口，`dry_run=false` 会真实发送控制命令。
- 运行 `base_state_verification_test.py` 前必须确认 Flask 已停止、`/dev/ttyS3` 空闲、喷药关闭。
- `base_state_verification_test.py` 只发布 `/cmd_vel`，不直接操作串口。
- 默认确认字符串为 `I_UNDERSTAND_THIS_SENDS_REAL_STM32_COMMANDS`。
- 预期 `/spraying_car/base_state` 中 `using_ext_status=true`，`uart_control_mode=1`。
- 如果 `using_ext_status=false`，需要先修复扩展状态链路，再依赖 `turn_cmd_position` 判断转向命令状态。

## 进入实车运动前必须满足

- 真实 L1RM `/unilidar/cloud` 数据正常。
- 真实 L1RM `/unilidar/imu` 数据正常。
- `/unilidar/cloud` frame_id 已确认。
- `/unilidar/imu` frame_id 已确认。
- `point_lio` 输出 `/pointlio/odom` 正常。
- `/pointlio/odom` 的 `header.frame_id` 和 `child_frame_id` 已记录。
- `point_lio_frame_bridge` 输出 `/slam_odom` 正常。
- `odom -> base_link` 正常、连续、方向可信；当前推荐由 `point_lio_frame_bridge` 发布 `odom -> base_footprint`，再经 URDF 到 `base_link`。
- local costmap 正常，不把地面大面积标成障碍。
- move_base 能输出 `/cmd_vel`。
- `spraying_car_base dry-run` 能接收 `/cmd_vel` 并打印控制意图；非零前进/转向方向需要架空验证。
- 已架空验证 `/dev/ttyS3` 实车控制方向。
- 遥控器可随时接管。
- 软件急停可用。
- 旁边有人看护。
- `base_dry_run=false` 必须由人工显式设置。

阶段 8E 复测状态：

- 真实 L1RM `/unilidar/cloud`、`/unilidar/imu` 已有消息。
- `/pointlio/odom` 和 `/slam_odom` 已正常。
- `odom -> base_link` 已可达。
- move_base、TEB、global/local costmap 已能启动。
- `/cmd_vel` 链路已连通到 `spraying_car_base dry-run`。
- 真实点云下近距离 goal 出现 TEB 轨迹不可行，`/cmd_vel` 采样为 0 速度。

因此仍不能进入地面实车运动；进入阶段 8F 前应先继续做架空 `/cmd_vel` 方向验证，并在真实点云下继续调 costmap/TEB 参数。

## 测试中

- 只发短距离目标点。
- 低速。
- 人员站在安全距离外。
- 保持遥控器在手。
- 发现方向反了立即停止。
- 发现转向反了立即停止。
- 发现 costmap 全是障碍立即停止。
- 发现 point_lio 漂移立即停止。
- 发现 TF 跳变立即停止。
- 发现 `/cmd_vel` 持续输出异常立即停止。

## 测试后

- 保存 rosbag。
- 保存 ROS 日志。
- 记录速度档位和实际速度感受。
- 记录转向方向是否正确。
- 记录 TF 问题。
- 记录 costmap 问题。
- 记录 point_lio 漂移情况。
- 更新参数。
- 更新测试结论和下一次测试边界。
