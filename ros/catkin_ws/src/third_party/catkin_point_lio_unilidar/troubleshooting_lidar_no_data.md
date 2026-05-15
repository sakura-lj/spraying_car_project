# 雷达数据接收异常问题排查与解决说明

## 1. 问题背景

- **项目场景**：在 OrangePi 5B（ARM64/aarch64，Ubuntu 20.04）上运行 Unitree L1 LiDAR 的 ROS2 驱动节点，通过 USB 串口连接雷达。
- **雷达型号**：Unitree L1 LiDAR，固件版本 1.2.3，SDK 版本 1.0.16。
- **连接方式**：USB-to-UART 桥接芯片（Silicon Labs CP2104），串口设备 `/dev/ttyUSB0`，波特率 2000000。
- **异常表现**：雷达 ROS2 节点启动后无数据发布，topic echo 无输出。

## 2. 异常现象

| 现象 | 详情 |
|------|------|
| ROS2 节点启动正常 | `ros2 launch unitree_lidar_ros2 launch.py` 显示进程已启动 |
| 话题已创建 | `ros2 topic list` 显示 `/unilidar/cloud` 和 `/unilidar/imu` |
| 话题无数据 | `ros2 topic echo /unilidar/cloud` 无任何输出 |
| 串口超时警告 | 终止节点时终端打印大量 `Serial port timeout!` |
| C++ SDK 示例异常 | 直接运行 `bin/example_lidar` 抛出 `SerialException: device reports readiness to read but returned no data (device disconnected?)` |

## 3. 排查思路

按实际执行顺序记录：

### 3.1 串口设备层

- 确认 `/dev/ttyUSB0` 是否存在 → **存在**
- 确认用户是否在 `dialout` 组 → **是**
- 确认端口是否被其他进程占用 → **未被占用**（`fuser`、`lsof` 均无结果）

### 3.2 USB 硬件层

- 确认 USB 设备是否被内核识别 → **已识别**（CP2104，idVendor=10c4，idProduct=ea60）
- 检查 USB 控制器类型 → 设备连接在 **OHCI (USB 1.1) 总线**上（12Mbps）
- 检查 dmesg 中的 USB 事件 → 发现 **多次 disconnect/reconnect 事件**，表明 OHCI 控制器连接不稳定

### 3.3 雷达协议层

- 对比 SDK 示例代码 (`example_lidar.cpp`) 与 ROS2 节点代码 → 发现 ROS2 节点 **缺少 `setLidarWorkingMode(NORMAL)` 调用**
- 该命令是启动雷达数据流的必要条件（示例代码中先发送 STANDBY，再发送 NORMAL）

### 3.4 诊断工具问题

- C++ SDK 示例运行后无任何输出 → 排查发现是 `printf` 输出缓冲问题，管道模式下不自动刷新
- 使用 `stdbuf -oL -eL` 后，示例正常输出初始化信息和版本号

## 4. 使用过的检查命令

以下命令按实际执行顺序列出：

```bash
# 1. 确认串口设备存在
ls /dev/ttyUSB*
# 结果: /dev/ttyUSB0 — 设备存在

# 2. 确认用户有串口权限
groups orangepi | grep -o dialout
# 结果: dialout — 用户已在 dialout 组

# 3. 确认端口未被占用
fuser -v /dev/ttyUSB0
lsof /dev/ttyUSB0
# 结果: 无进程占用

# 4. 列出所有 USB 设备及其总线拓扑
lsusb -t
# 结果: CP2104 连接在 Bus 06 (ohci-platform, 12Mbps)

# 5. 查看内核 USB 事件日志
dmesg | grep -i "cp210\|ttyUSB"
# 结果: 发现多次 disconnect/reconnect 事件，表明 USB 连接不稳定

# 6. 直接运行 C++ SDK 示例测试硬件
stdbuf -oL -eL timeout 10 ./unitree_lidar_sdk/bin/example_lidar
# 结果: 首次直接运行时抛出 SerialException
#       切换 USB 端口后用 stdbuf 运行成功，输出固件版本 1.2.3

# 7. 查看 ROS2 话题列表
source /opt/ros/foxy/setup.bash && ros2 topic list
# 结果: /unilidar/cloud, /unilidar/imu, /rosout, /parameter_events

# 8. 查看话题数据
ros2 topic echo /unilidar/cloud
# 问题修复前: 无输出
# 问题修复后: 输出 point_step=32, width=2100+ 的点云数据
```

## 5. 根本原因分析

最终确定两个独立原因叠加导致问题：

### 原因一：OrangePi 5B 的 OHCI USB 控制器不稳定

- CP2104 芯片被自动分配到了 OHCI（USB 1.1）总线控制器
- OrangePi 5B（Rockchip RK3588 SoC）上的 OHCI 控制器在处理连续中断传输（USB 串口数据流）时存在可靠性问题
- dmesg 中多次 disconnect/reconnect 事件证实了这一点
- **效果**：USB 驱动报告"端口可读"但 `read()` 返回 0 字节

### 原因二：ROS2 节点未发送雷达工作模式命令

- 雷达上电后进入默认模式，不主动推流
- 必须通过 SDK API 发送 `setLidarWorkingMode(NORMAL)` 命令才能启动数据流
- C++ SDK 示例 `example_lidar.cpp` 中明确包含了此命令（先 STANDBY 再 NORMAL）
- 原始 ROS2 节点代码（`unitree_lidar_ros2.h`）中只调用了 `initialize()` 后直接调用 `runParse()`，缺少模式设置

## 6. 解决步骤

### 步骤一：切换 USB 物理端口

将 USB 线缆从当前端口拔出，换到 **USB 3.0（蓝色）端口**：

```bash
# 插入后验证设备在新总线上
lsusb -t | grep cp210
# 确认连接到 xhci-hcd 总线（Bus 01/07/08）而非 ohci-platform
```

> **注意**：根据对话实际记录，切换后 `lsusb -t` 仍显示 ohci-platform（Bus 04），但连接稳定性已改善。最佳实践是尝试多个物理端口直到稳定。

### 步骤二：修改 ROS2 节点代码

文件：`unitree_lidar_ros2/src/unitree_lidar_ros2/include/unitree_lidar_ros2.h`

在 `initialize()` 调用之后，添加 `setLidarWorkingMode(NORMAL)`：

```cpp
// 原始代码（修改前）
lsdk_ = createUnitreeLidarReader();
lsdk_->initialize(cloud_scan_num_, port_, 2000000, rotate_yaw_bias_,
      range_scale_, range_bias_, range_max_, range_min_);

// ROS2
pub_cloud_ = this->create_publisher<sensor_msgs::msg::PointCloud2>(...);

// 修改后（新增一行）
lsdk_ = createUnitreeLidarReader();
lsdk_->initialize(cloud_scan_num_, port_, 2000000, rotate_yaw_bias_,
      range_scale_, range_bias_, range_max_, range_min_);

lsdk_->setLidarWorkingMode(NORMAL);  // <-- 新增此行

// ROS2
pub_cloud_ = this->create_publisher<sensor_msgs::msg::PointCloud2>(...);
```

`NORMAL` 枚举值来自 `unitree_lidar_sdk.h` 中的 `LidarWorkingMode` 枚举，通过 `unitree_lidar_sdk_pcl.h` 的 `using namespace unitree_lidar_sdk;` 可直接使用。

### 步骤三：重新编译 ROS2 节点

```bash
cd unitree_lidar_ros2
source /opt/ros/foxy/setup.bash
colcon build
```

### 步骤四：启动并验证

```bash
cd unitree_lidar_ros2
source install/setup.bash
ros2 launch unitree_lidar_ros2 launch.py
```

另开终端验证：

```bash
source /opt/ros/foxy/setup.bash
ros2 topic echo /unilidar/cloud
```

## 7. 修改文件说明

| 文件路径 | 修改内容 | 修改原因 | 修改后效果 |
|----------|----------|----------|-----------|
| `unitree_lidar_ros2/src/unitree_lidar_ros2/include/unitree_lidar_ros2.h` | 在 `initialize()` 后新增 `lsdk_->setLidarWorkingMode(NORMAL);` | 雷达上电后不会自动推送数据，需要发送 NORMAL 模式指令 | 节点启动后雷达开始推送点云和 IMU 数据 |
| `AGENTS.md` | 新增 "Runtime pitfalls" 章节，记录 RViz2 在 OrangePi 5B 上崩溃、USB 端口选择注意事项 | 防止后续开发踩坑 | 提供平台特定注意事项 |
| `~/.bashrc` | (ROS2 卸载时) 删除 `source /opt/ros/foxy/setup.bash` | 清理 ROS2 环境配置 | 新终端不再加载 ROS2 环境 |

## 8. 验证方法

### 8.1 硬件层验证

```bash
# 运行 C++ SDK 示例，确认雷达硬件正常
cd unitree_lidar_sdk && stdbuf -oL ./bin/example_lidar
# 预期输出: Unilidar initialization succeed! 以及固件版本号
```

### 8.2 ROS2 话题层验证

```bash
# 确认话题存在
ros2 topic list
# 预期: /unilidar/cloud, /unilidar/imu

# 确认话题有数据
ros2 topic echo /unilidar/cloud
# 预期: 持续输出 point_step=32, width=2100+ 的点云数据
```

### 8.3 数据质量验证

```bash
# 查看话题发布频率
ros2 topic hz /unilidar/cloud
# 预期: ~10-15 Hz（取决于雷达扫描频率）

# 查看点云详情（单帧数据）
ros2 topic echo /unilidar/cloud --once 2>&1 | head -30
```

## 9. 经验总结

### 排查优先级

| 优先级 | 检查项 | 关键命令/方法 |
|--------|--------|--------------|
| 1 | 硬件连接与供电 | `ls /dev/ttyUSB*`, 观察雷达 LED 指示灯 |
| 2 | 串口权限 | `groups $USER \| grep dialout` |
| 3 | USB 总线稳定性 | `lsusb -t`, `dmesg \| grep -i cp210` |
| 4 | USB 端口物理位置 | 优先使用 USB 3.0（蓝色）端口 |
| 5 | 雷达工作模式 | SDK 示例代码 vs 驱动代码对比 |
| 6 | 串口数据验证 | 先运行 SDK 示例排除 ROS 层干扰 |
| 7 | ROS 话题发布 | `ros2 topic list && ros2 topic echo` |

### 关键经验

1. **先排除硬件层，再排查协议层最后查 ROS 层** — 本次直接测试 C++ SDK 示例快速排除了 ROS 框架问题
2. **ARM 单板计算机的 USB 控制器差异** — OrangePi/树莓派等 ARM 板的 OHCI 控制器可能有可靠性问题，优先使用 XHCI 控制的 USB 3.0 端口
3. **驱动代码与示例代码对比** — 对比 SDK 官方示例和 ROS 驱动代码发现缺失的模式命令是关键转折点
4. **注意输出缓冲** — C++ 程序通过管道运行时 `printf` 默认全缓冲，需要用 `stdbuf -oL` 或 `setbuf(stdout, NULL)` 才能看到实时输出

## 10. 附录：常用排查命令

```bash
# ===== 串口诊断 =====
ls /dev/ttyUSB* /dev/ttyACM*          # 列出串口设备
stty -F /dev/ttyUSB0                  # 查看串口配置（波特率等）
fuser -v /dev/ttyUSB0                 # 查看占用端口的进程
cat /dev/ttyUSB0 | xxd | head         # 直接读取原始串口数据

# ===== USB 诊断 =====
lsusb -t                              # USB 设备树（查看总线类型和速度）
cat /sys/bus/usb/devices/*/speed      # 查看各设备速度
dmesg | grep -i "usb\|cp210\|tty"     # 内核 USB 事件日志
dmesg -w                              # 实时内核日志

# ===== ROS2 诊断 =====
ros2 topic list                       # 列出所有活跃话题
ros2 topic echo /unilidar/cloud       # 订阅话题并打印数据
ros2 topic hz /unilidar/cloud         # 查看话题发布频率
ros2 node list                        # 列出活跃节点
ps aux | grep unitree                 # 查看雷达节点进程状态

# ===== 雷达诊断（C++ SDK 示例）=====
cd unitree_lidar_sdk
mkdir -p build && cd build && cmake .. && make -j2
stdbuf -oL -eL ../bin/example_lidar   # 运行示例，查看雷达初始化输出
```

---

> **文档说明**：本文档基于 OrangePi 5B + Unitree L1 LiDAR + ROS2 Foxy 环境的实际排查过程编写。涉及路径为 `/home/orangepi/Desktop/unilidar_sdk/`，如项目路径不同请替换。
