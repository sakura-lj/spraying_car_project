# 农业喷药无人车 — 项目交接文档

> **生成时间**: 2026-05-16  
> **文档目的**: 供下一个 AI 助手/开发者准确了解项目现状，规划后续 ROS 化与自动驾驶开发  
> **约束**: 本文档不修改任何源码，仅基于只读分析生成

---

## 目录

1. [项目总体结论](#1-项目总体结论)
2. [当前仓库目录结构](#2-当前仓库目录结构)
3. [当前硬件系统说明](#3-当前硬件系统说明)
4. [STM32 下位机工程说明](#4-stm32-下位机工程说明)
5. [STM32 与上位机串口协议](#5-stm32-与上位机串口协议)
6. [Orange Pi / Flask 上位机说明](#6-orange-pi--flask-上位机说明)
7. [Vue 前端说明](#7-vue-前端说明)
8. [图像识别 / YOLO / RKNN 说明](#8-图像识别--yolo--rknn-说明)
9. [ROS / 雷达 / SLAM 当前状态](#9-ros--雷达--slam-当前状态)
10. [当前实际数据流与控制流](#10-当前实际数据流与控制流)
11. [当前构建、部署与运行方式](#11-当前构建部署与运行方式)
12. [当前文档状态](#12-当前文档状态)
13. [当前已实现功能与未实现功能清单](#13-当前已实现功能与未实现功能清单)
14. [面向 ROS 化的差距分析](#14-面向-ros-化的差距分析)
15. [后续推荐开发顺序](#15-后续推荐开发顺序)
16. [需要人工确认的问题](#16-需要人工确认的问题)
17. [给下一个 AI 助手的关键提醒](#17-给下一个-ai-助手的关键提醒)

---

## 1. 项目总体结论

1. **遥控器远程驾驶已形成闭环**：RC 接收器 → STM32 PWM 捕获 → DAC（牵引电机）/ 步进电机（转向）/ 继电器（喷药）全部可运行。来源：`firmware/spraying_car_lower/Core/Src/`
2. **Web 远程控制已形成闭环**：Vue 前端 → Flask API → STM32 串口 → 车辆动作，全部可运行。来源：`web/upper/app.py`、`web/upper/website/`
3. **GPS 轨迹显示已实现**：GPS Modbus RTU → Flask GPS 线程 → WGS84→GCJ02 转换 → Vue 高德地图实时轨迹。来源：`web/upper/app.py:415-465`
4. **USB 摄像头视频流已实现**：OpenCV → Flask MJPEG → `/video_feed` 端点可直接显示。来源：`web/upper/app.py:75-266`
5. **串口协议已实现但状态回传字段严重不足**：当前 STM32 仅回传 4 字节（喷药状态、速度档位、方向、继电器状态），缺少真实轮速、真实转向角度、电池电压、编码器位置等自动驾驶必需数据。来源：`firmware/spraying_car_lower/Core/Src/upper.c:477-481`
6. **ROS 底盘节点（`/cmd_vel` 到 STM32 控制转换）完全未实现**：`spraying_car_base` 目录只有 README.md 设计文档，无任何源码。来源：`ros/catkin_ws/src/spraying_car_base/`
7. **宇树 L1RM LiDAR 驱动已编译可运行**：`unitree_lidar_ros` 包有完整 C++ 源码并编译通过，可发布 `/unilidar/cloud` 和 `/unilidar/imu`。来源：`ros/catkin_ws/src/third_party/unilidar_sdk/unitree_lidar_ros/`
8. **point_lio_unilidar 建图已编译可运行**：有完整 C++ 源码和 launch 文件，可输出 PCD 地图。来源：`ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/`
9. **move_base/TEB/waypoint 导航完全未实现**：`spraying_car_navigation`、`spraying_car_waypoint` 均只有 README 骨架。来源：`ros/catkin_ws/src/spraying_car_navigation/README.md`
10. **点云建图与底盘控制之间没有任何桥接**：LiDAR 和 SLAM 可以独立运行，但与车辆底层控制（速度/方向/转向）完全无数据链路。
11. **没有 URDF 模型**：`spraying_car_description` 只有 README 文件，无实际 URDF/XACRO。来源：`ros/catkin_ws/src/spraying_car_description/`
12. **没有 TF 树**：当前 SLAM 只发布 `camera_init` → `aft_mapped`，没有 `base_link`、`odom`、`map` 等标准 ROS TF 帧。来源：`ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/AGENTS.md:50`
13. **Apple_leaf_detection.rknn 模型文件存在但未接入系统**：模型文件 4.1MB 位于 `web/upper/`，无任何代码引用。来源：`web/upper/Apple_leaf_detection.rknn` + 全仓库 grep 零引用
14. **没有 YOLO 数据集、训练代码或推理脚本**：仓库中无 .pt、.onnx 文件，无 `orangepi图像识别/` 目录。结论：图像识别闭环未形成。
15. **电池电压采集、液位采集、故障检测均未实现**：`battery_voltage` 在 Flask 中初始化但始终为 0，STM32 无 ADC 电压采集代码。
16. **RTK 定位未实现**：GPS 模块使用 Modbus RTU 读取，精度为普通 GNSS 单点定位。
17. **MQTT 云端已废弃**：旧 MQTT 代码在 `trash/webbackend/` 中，当前 Flask 不再使用 MQTT。
18. **frp 公网访问已配置**：`deploy/frpc.ini` 存在（含服务器地址，视为敏感配置），可将 Flask 5000 端口映射到公网。
19. **机器人没有 odom（里程计）**：既无轮速编码器采集代码，也无 `/odom` 话题发布。
20. **最大技术风险点**：(a) STM32 状态包缺少自动驾驶核心数据；(b) 串口协议无 CRC 校验（仅简单 checksum），高速控制时可能出错；(c) ORANGE Pi 5B 的 OHCI USB 控制器不稳定，可能影响 LiDAR 数据传输；(d) 转向编码器 int16_t 可能溢出（最大 ±32767 计数）。

---

## 2. 当前仓库目录结构

```
/home/orangepi/spraying_car_project/
│
├── README.md                          [空文件]
├── docs/                              [空目录 - 交付后本文档将在此]
├── maps/                              [空目录 - 预留给地图文件]
├── bags/                              [空目录 - 预留给 rosbag]
├── scripts/                           [空目录 - 预留给脚本]
│
├── firmware/spraying_car_lower/       ★ 下位机 STM32F407 固件工程
│   ├── spraying_car.ioc               CubeMX 项目文件
│   ├── CLAUDE.md                      项目内开发指南 (可信)
│   ├── README.md                      固件说明
│   ├── Core/Inc/  头文件
│   ├── Core/Src/  源文件 (main.c, upper.c, car_drive.c, turn.c 等)
│   ├── Drivers/   HAL 库 & CMSIS
│   ├── MDK-ARM/   Keil uVision 工程
│   ├── Middlewares/ USB Device 中间件
│   └── USB_DEVICE/ CDC 虚拟串口
│
├── ros/catkin_ws/src/                 ★ ROS1 Noetic 工作区
│   ├── spraying_car_base/             [骨架] 底盘桥接 (仅 README)
│   ├── spraying_car_bringup/          [骨架] 启动聚合 (仅 README)
│   ├── spraying_car_description/      [骨架] URDF 模型 (仅 README)
│   ├── spraying_car_msgs/             [骨架] 自定义消息 (仅 README)
│   ├── spraying_car_navigation/       [骨架] 导航配置 (仅 README)
│   ├── spraying_car_slam/             [骨架] SLAM 封装 (仅 README)
│   ├── spraying_car_tools/            [骨架] 调试工具 (仅 README)
│   ├── spraying_car_waypoint/         [骨架] 航线跟随 (仅 README)
│   └── third_party/
│       ├── catkin_point_lio_unilidar/  ✓ 完整编译(Point-LIO 建图)
│       │   └── src/point_lio_unilidar/  ROS 包(含源码+launch+config)
│       └── unilidar_sdk/              ✓ 完整编译(宇树 SDK + ROS 驱动)
│           ├── unitree_lidar_sdk/     纯 C++ SDK (闭源 .a 库)
│           ├── unitree_lidar_ros/     ROS1 Noetic 驱动
│           └── unitree_lidar_ros2/    ROS2 驱动 (未使用)
│
└── web/upper/                         ★ 上位机 Orange Pi 5B
    ├── app.py                         主 Flask 应用 (1147行)
    ├── start.py                       启动器
    ├── Apple_leaf_detection.rknn      未使用的 RKNN 模型 (4.1MB)
    ├── deploy/frpc.ini                frp 公网配置 (含敏感信息)
    ├── docs/使用文档.md               用户使用文档 (可信)
    ├── templates/index.html           备用控制面板 (1795行)
    ├── trash/                         [旧版本/已废弃]
    │   ├── GPSup.py                   旧 GPS 上传脚本
    │   ├── webbackend/                旧 MQTT 中转
    │   ├── website-MainPage.vue       旧 Vue 主页
    │   └── website-NavBar.vue         旧 Vue 导航栏
    └── website/                       主前端 Vue 3 + Vite
        ├── package.json               依赖声明
        ├── vite.config.js             Vite 构建配置
        ├── dist/                      npm run build 产物
        └── src/
            ├── main.js                入口
            ├── App.vue                根组件
            ├── router/index.js        路由 (/, /monitor, /control)
            ├── stores/
            │   ├── axios.js           API 调用 + 状态缓存 (Pinia)
            │   ├── dataPacket.js      GPS 数据处理
            │   └── WindowResize.js    窗口大小 (未使用)
            ├── components/
            │   ├── NavBarNew.vue      导航栏 (含急停按钮)
            │   ├── MapContainer.vue   高德地图封装
            │   ├── CyberInfoCard.vue  信息卡片
            │   └── InfoCard.vue       旧卡片 (未使用)
            └── views/
                ├── MonitorPage.vue    监控页
                └── ControlPage.vue    控制页
```

**目录状态标注**:
- ✓ : 源码完整、可编译/运行
- [骨架] : 仅有 README 设计文档，无源码
- [空目录] : 预留但无内容
- [旧版本/已废弃] : 不再使用，保留供参考

---

## 3. 当前硬件系统说明

### 硬件组成表

| 硬件模块 | 接口 | 当前代码状态 | 是否已验证 | 备注 |
|----------|------|-------------|-----------|------|
| **主控 MCU** | STM32F407VET6 (Cortex-M4, LQFP100, 72MHz) | 完整固件 | 已运行 | 源码: `firmware/spraying_car_lower/` |
| **上位机** | Orange Pi 5B (ARM64, Rockchip RK3588S) | Python Flask | 已运行 | `web/upper/app.py` |
| **牵引电机** | 直流有刷电机 | DAC1 (PA4) 0-3.1V 模拟控制 | 未确认实车速度标定 | 档位 1(0V)~102(3.1V)，非线性的DAC曲线 |
| **牵引电机驱动** | 外置电机控制器 (电压模式) | STM32 DAC 输出 | 未确认型号 | 来源: `car_drive.c` DAC 电压映射逻辑 |
| **转向机构** | 步进电机 + 编码器闭环 | TIM8 PWM（STEP）+ PC5（DIR）+ TIM5 编码器反馈 | 已验证 PID 闭环 | `turn.c` 闭环 PID，4000 细分 |
| **喷药继电器** | PE2（eleRelay2） | GPIO 开关 | 未确认实车 | `car_drive.c:40-46` |
| **主电源继电器** | PE1（eleRelay1） | GPIO 开关 + 遥控器长按手势 | 已运行 | `main.c:96-112`，长按 CH3=1+CH4=1 约 2 秒 |
| **遥控器 RC** | 5 通道 PWM 输入 | TIM9 CH3(速度)、TIM12 CH4(转向)、TIM2 CH5(方向)、TIM3 CH6(喷药)、TIM4 CH7(备用) | 已验证 | `Remote_control.c` |
| **GPS 模块** | Modbus RTU 串口 (115200) | Python 读取，WGS84→GCJ02 | 已验证读取 | 来源: `app.py:415-474`，需独立串口 |
| **USB 摄像头** | USB (OpenCV) | Flask MJPEG 流 | 已验证 | `/video_feed` 端点 |
| **OLED 显示屏** | PE3(SCL)/PE4(SDA) 软件 I²C | DEBUG_MODE=1 时启用 | 已验证调试用途 | `OLED.c`，128x64 |
| **宇树 L1RM LiDAR** | USB 串口 (2M baud) | ROS 驱动已编译 | 已联调通过 | `unitree_lidar_ros`，需接 USB 2.0/3.0 口 |
| **RTK** | 无 | 未实现 | — | GPS 为普通 GNSS 单点 |
| **电池电压采集** | 无 ADC 通道 | 未实现 | — | Flask `battery_voltage` 始终为 0 |
| **液位传感器** | 无 | 未实现 | — | |
| **故障检测** | 无 | 未实现 | — | |
| **蜂鸣器** | PD0（低电平有效） | 已实现 | 已验证 | 开关机提示音 |
| **调试接口** | SWD (PA13/PA14) + USB CDC | 已实现 | 已验证 | CDC 可镜像 USART1 收发数据 |

### 串口资源分配（Orange Pi 侧）

| 串口 | 用途 | 默认设备 | 备注 |
|------|------|---------|------|
| USART1 (硬件UART) | STM32 车辆控制 | `/dev/ttyS3` | 环境变量 `VEHICLE_SERIAL_PORT` |
| USB 转串口 | GPS Modbus | `/dev/ttyUSB0` | 环境变量 `GPS_SERIAL_PORT` |
| USB 转串口 | L1RM LiDAR | `/dev/ttyUSB0` | 与 GPS 冲突，实车需分开 |

> **重要冲突**: LiDAR 驱动配置默认使用 `/dev/ttyUSB0`，与 GPS 默认串口相同。实车部署时需通过 `GPS_SERIAL_PORT` 环境变量区分，或修改 LiDAR 驱动配置。

---

## 4. STM32 下位机工程说明

### 基本信息

| 项目 | 内容 |
|------|------|
| **主工程路径** | `firmware/spraying_car_lower/` |
| **CubeMX ioc** | `firmware/spraying_car_lower/spraying_car.ioc` |
| **Keil 工程** | `firmware/spraying_car_lower/MDK-ARM/spraying_car.uvprojx` |
| **VS Code 工作区** | `firmware/spraying_car_lower/spraying_car.code-workspace` (EIDE 插件) |
| **MCU 型号** | STM32F407VET6 (Cortex-M4F) |
| **主频** | HSE 8MHz → PLL 72MHz SYSCLK |
| **编译工具链** | ARM Compiler V5.06 (AC5)，-O3 优化 |
| **烧录方式** | J-Link (SWD, 8000kHz) |

### 主要源码文件及职责

| 文件 | 职责 | 行数(约) |
|------|------|---------|
| `Core/Src/main.c` | 主入口，外设初始化，主循环调用各控制函数，电源开关手势检测 | 324 |
| `Core/Src/car_drive.c` | **核心仲裁层**。遥控 vs 串口模式切换，三层架构（hw层/控制层/RC层），紧急停止 | 259 |
| `Core/Src/upper.c` | 串口协议引擎。帧解析状态机，命令分发，状态回传，DMA 收发，CDC 调试镜像 | 511 |
| `Core/Src/turn.c` | 步进电机 PID 闭环控制。TIM8 中断驱动，加减速斜坡，方向防抖切换 | 303 |
| `Core/Src/Remote_control.c` | 5 通道遥控器 PWM 捕获读取 | 65 |
| `Core/Src/Encoder.c` | TIM5 编码器读取（int16_t 返回） | 16 |
| `Core/Src/OLED.c` | 软件 I²C OLED 驱动 | — |
| `USB_DEVICE/App/usbd_cdc_if.c` | USB CDC 虚拟串口，调试数据镜像 | — |

### 遥控器通道映射

| 通道 | TIM | 用途 | 值域 |
|------|-----|------|------|
| CH3 | TIM9 CH1 | 油门/速度 | 0-102（1000-2020µs 映射） |
| CH4 | TIM12 CH1 | 转向目标 | 1-101 |
| CH5 | TIM2 CH1 | 方向开关 | 51=停止, 86=前进, 19=后退 |
| CH6 | TIM3 CH1 | 喷药开关 | ≥10=开启 |
| CH7 | TIM4 CH1 | 辅助（未使用） | — |

### 速度控制逻辑 (`car_drive.c`)

- DAC CH1 输出电压: duty=1→0V, duty 2-101→1.00-2.98V(线性+2mV/档), duty=102→3.10V
- 档位范围: 1-102（非映射到真实速度）
- **注意**: 实际车速由外部电机控制器的电压-转速特性决定，未在 STM32 中标定

### 转向闭环控制逻辑 (`turn.c`)

- 目标位置映射: `target = (CH4 - 51) * 500`（编码器计数）
- PID 参数: KP=0.5, KI=0.0, KD=0.1
- 加/减速率: 50Hz/100Hz 每中断周期
- 速度范围: 5kHz ~ 80kHz (STEP 频率)
- 到位判断: 编码器差值 ≤2 且速度低于阈值
- **重要**: 编码器为 4000 细分，与步进电机 4000 细分一致（1 个脉冲 = 1 编码器单位）

### 遥控器与串口双控仲裁逻辑

```
uart_control_mode 标志位 (全局):
- 串口发送任何命令 → uart_control_mode = 1
- 遥控器任一通道值变化 → uart_control_mode = 0，RC 接管
- uart_control_mode=0 时，RC 变化才驱动硬件
- uart_control_mode=1 时，RC 变化立即抢夺控制权
```

来源: `car_drive.c:10, 117-231`

### 急停逻辑

- `emergency_stop()` (`car_drive.c:237-257`): 直接操作 GPIO/DAC，不依赖状态变量
- 关闭所有方向继电器，DAC 输出置 0，关闭喷药，切换为串口控制模式
- **不处理转向电机**（注释：需通过步进电机函数处理）
- 下位机无独立的硬件急停输入引脚（缺乏物理急停开关）

### STM32 当前控制能力表

| 功能 | 是否实现 | 控制来源 | 反馈来源 | 文件位置 | 备注 |
|------|---------|---------|---------|---------|------|
| 牵引电机速度 | ✓ | RC CH3 / UART 0x02 | 无（开环） | `car_drive.c:21-33,70-74` | 无实际轮速反馈 |
| 转向角度 | ✓ | RC CH4 / UART 0x04 | TIM5 编码器 | `turn.c:75-78,201-215` | PID 闭环 |
| 方向控制 | ✓ | RC CH5 / UART 0x03 | 无 | `car_drive.c:53-64,92-96` | 双继电器控制 |
| 喷药控制 | ✓ | RC CH6 / UART 0x01 | 无 | `car_drive.c:40-46,81-85` | 单继电器 |
| 主电源控制 | ✓ | RC 长按手势 / UART 自动开 | 无 | `main.c:96-112` | 无电压检测 |
| 状态回传 | ✓ (4字节) | UART 0xFF 查询/自动回复 | - | `upper.c:477-481` | 数据严重不足 |
| 轮速测量 | ✗ | — | — | — | 需编码器硬件 |
| 电池电压 | ✗ | — | — | — | 需 ADC 通道 |
| 液位检测 | ✗ | — | — | — | 需传感器 + ADC |
| 故障码上报 | ✗ | — | — | — | 无异常处理机制 |
| 硬件急停 | ✗ | — | — | — | 软件急停 |

### 下位机当前已实现但未被上位机使用的能力

1. **USB CDC 调试输出**: STM32 将所有 USART1 收发数据镜像到 USB CDC 虚拟串口，可用于三方监听/日志
2. **转向编码器实时读数**: `Get_Encoder_Value()` 始终在运行，但状态回传中没有包含编码器值
3. **控制模式标志**: `get_control_mode()` 可查询当前是 RC 控制还是串口控制，但上位机不读取
4. **USART2**: 已初始化硬件（PA2/PA3），`Uart_Rxopen(&huart2)` 在 main.c 中被注释掉，可作为扩展通讯口

### 下位机当前潜在问题

1. 编码器 `int16_t` 返回，最大 ±32767 计数，接近目标范围 (CH4=1 时 target=-25000, CH4=101 时 target=25000)，可能发生溢出
2. 无轮速编码器，牵引电机完全开环
3. 转向 PID 仅 P 项有效（KI=0），可能无法精确到位
4. 急停不控制步进电机，紧急情况下转向不回中
5. USART2 未启用（可供未来扩展）

---

## 5. STM32 与上位机串口协议

### 帧格式

```
┌──────┬──────┬──────┬─────────────────┬──────────┬──────┐
│ HEAD │ TYPE │ LEN  │     DATA        │ CHECKSUM │ TAIL │
│ 0xAA │ 1B   │ 1B   │ 0~127 字节      │ 1B       │ 0x55 │
└──────┴──────┴──────┴─────────────────┴──────────┴──────┘
```

- **HEAD**: 固定 0xAA
- **TYPE**: 命令类型（1 字节）
- **LEN**: data 字段长度（1 字节），最大 127
- **DATA**: 有效载荷（0~127 字节）
- **CHECKSUM**: 仅 data 字节的无符号 8 位累加和（`sum(data) % 256`），不含 type/len/head/tail
- **TAIL**: 固定 0x55

**完整包长度 = LEN + 5**

**STM32 端**：`firmware/spraying_car_lower/Core/Src/upper.c:70-80, 131-166`  
**Python 端**：`web/upper/app.py:50-64, 665-699`

### 命令列表

| 命令名 | type 值 | 方向 | data 格式 | 作用 | STM32 代码位置 | Python 代码位置 |
|--------|---------|------|-----------|------|----------------|-----------------|
| CMD_SPRAY_CONTROL | 0x01 | PC→STM32 | 1B: 0=关, 1=开 | 控制喷药继电器 | `upper.c:287-297` | `app.py:825-837` |
| CMD_SPEED_CONTROL | 0x02 | PC→STM32 | 1B: 1-102 档位 | 控制牵引电机速度 | `upper.c:299-313` | `app.py:839-851` |
| CMD_DIRECTION_CONTROL | 0x03 | PC→STM32 | 1B: 0=停, 1=前, 2=后 | 控制方向继电器 | `upper.c:315-334` | `app.py:853-865` |
| CMD_TURN_CONTROL | 0x04 | PC→STM32 | 1B: 1-101(51=中) | 设转向目标位置 | `upper.c:336-349` | `app.py:867-879` |
| CMD_STATUS_QUERY | 0xFF | PC→STM32 | 任意1B(忽略) | 查询当前状态 | `upper.c:351-355` | `app.py:731-733` |
| CMD_STATUS_RESPONSE | 0x05 | STM32→PC | 4B: [喷药 速度 方向 电源] | 返回车辆状态 | `upper.c:477-481` | `app.py:815-823` |

### 状态响应包详情

| 字节偏移 | 字段 | 类型 | 说明 |
|---------|------|------|------|
| data[0] | spray_state | uint8 | 0=关闭, 1=开启 |
| data[1] | vehicle_speed | uint8 | 1-102 档位（非真实速度） |
| data[2] | direction_state | uint8 | 0=停止, 1=前进, 2=后退 |
| data[3] | is_open | uint8 | 0=电源关, 1=电源开 |

### 协议当前不足之处

| 缺失项 | 影响 | 优先级 |
|--------|------|--------|
| **无真实轮速** | 无法计算里程计、速度闭环 | 极高 |
| **无真实转向角** | 无法发布 `/joint_states` | 极高 |
| **无编码器值** | 无法做里程计融合定位 | 极高 |
| **无电池电压** | 无法做低电量保护/返航 | 高 |
| **无故障码** | 无法诊断电机/传感器故障 | 中 |
| **无控制模式位** | 上位机不知道当前是 RC 还是串口在控制 | 中 |
| **仅简单 checksum** | 无 CRC，高速连续控制可能漏错误 | 中 |
| **无时间戳** | 无法做时间同步 | 低 |
| **无数据包序号** | 无法检测丢包 | 低 |

### 超时与重连

- **上位机侧**: `communication_thread` 每 50ms 轮询串口，每 2 秒发送一次状态查询
- **错误处理**: 连续 5 次通信错误触发 `reconnect_serial()`（关闭→等待 0.5s→重新打开）
- **下位机侧**: DMA 空闲中断接收，无超时保护。如 USART1 物理断开，HAL 会自动禁用 DMA 通道
- **无心跳包机制**: 双方都没有独立的心跳检测

---

## 6. Orange Pi / Flask 上位机说明

### 基本信息

| 项目 | 内容 |
|------|------|
| **主程序入口** | `web/upper/start.py` → 子进程启动 `app.py` |
| **文件行数** | `app.py` 1147 行 |
| **Flask 监听** | `0.0.0.0:5000` |
| **串口（车辆控制）** | `/dev/ttyS3` (波特率 115200, 8N1)，环境变量 `VEHICLE_SERIAL_PORT` |
| **串口（GPS）** | `/dev/ttyUSB0` (波特率 115200)，环境变量 `GPS_SERIAL_PORT` |
| **Python 依赖** | flask, flask-cors, pyserial, opencv-python, numpy |

### 线程结构

```
main
  ├── communication_thread (50ms 轮询串口, 2s 状态查询)
  ├── gps_collection_thread (1s GPS 采集, 10s 重连)
  └── VideoCamera.update() (OpenCV 帧捕获, MJPEG 流)
```

### 状态缓存机制

- **乐观更新**: 每个 `send_*()` 方法立即更新本地状态变量
- **STM32 真值覆盖**: 收到 `CMD_STATUS_RESPONSE` 后覆盖本地状态
- **GPS 锁保护**: `gps_lock` 保证 GPS 数据读写线程安全
- **串口锁**: `serial_lock` 防止多线程同时操作串口

### Flask API 路由表

| 路由 | 方法 | 参数 | 返回字段 | 是否真实控制硬件 | 代码位置 | 备注 |
|------|------|------|---------|----------------|---------|------|
| `/` | GET | — | HTML 页面 | 否 | `app.py:939-943` | 备用控制面板 |
| `/app` `/app/` `/app/<path>` | GET | — | Vue SPA 静态文件 | 否 | `app.py:945-954` | 主面板入口 |
| `/video_feed` | GET | — | MJPEG 流 | 否 | `app.py:956-966` | USB 摄像头 |
| `/spray_control` | POST | `{state: bool}` | `{success, state, message}` | **是** | `app.py:968-987` | 喷药开关 |
| `/speed_control` | POST | `{speed: 1-102}` | `{success, speed, message}` | **是** | `app.py:989-1008` | 速度控制 |
| `/direction_control` | POST | `{direction: 0/1/2}` | `{success, direction, message}` | **是** | `app.py:1010-1029` | 方向控制 |
| `/turn_control` | POST | `{position: 1-101}` | `{success, position, message}` | **是** | `app.py:1031-1050` | 转向控制 |
| `/emergency_stop` | POST | `{}` | `{success, message, timestamp, vehicle_state}` | **是** | `app.py:1052-1086` | 急停（4 条命令，2 次重试） |
| `/vehicle_status` | GET | — | 完整车辆状态 + GPS | 否（仅读取） | `app.py:1088-1114` | 主状态接口 |
| `/updateData` | GET | — | GPS 历史数组 | 否（仅读取） | `app.py:1116-1121` | 兼容 Vue |
| `/status` | POST | `{receive_status: bool}` | `{success, receive_status, message}` | **否** | `app.py:1123-1132` | 旧 MQTT 兼容 |
| `/reconnect` | POST | — | `{success, message}` | **否** | `app.py:1134-1142` | 手动重连串口 |

### 后续接入 ROS 时的串口冲突风险

- `app.py` 通过 `serial_lock` 独占操作 USART1 (`/dev/ttyS3`)
- 如果 ROS 底盘节点 (`spraying_car_base`) 也需要打开同一串口，会导致 `Device or resource busy` 错误
- **解决方案**: 实现 `CONTROL_BACKEND` 环境变量，当 `CONTROL_BACKEND=ros` 时 Flask 不打开串口，改为通过 ROS topic/action 通信

### MQTT 状态

当前 **不使用 MQTT**。旧代码在 `trash/webbackend/`，`/status` 端点是旧协议的残余兼容接口，不产生实际控制效果。

### 多进程状态

当前为单进程多线程架构。`start.py` 仅启动 app.py 子进程（无多进程并行）。

### frp 公网部署

- 配置文件: `web/upper/deploy/frpc.ini`（含远程服务器地址和端口，视为敏感配置）
- 映射: `127.0.0.1:5000` → 远程服务器 `5000` 端口
- 公网可访问监控和控制页面

---

## 7. Vue 前端说明

### 技术栈

| 项目 | 内容 |
|------|------|
| 框架 | Vue 3.4.21（Composition API + `<script setup>`） |
| 构建 | Vite 5.1.6 |
| 路由 | vue-router 4.3.0（懒加载） |
| 状态管理 | Pinia 2.1.7 |
| HTTP | Axios 1.6.7 |
| UI 库 | Element Plus 2.6.2 + Vuetify 3.5.9 |
| CSS | Tailwind CSS 3.4.1 |
| 地图 | @amap/amap-jsapi-loader 1.0.1（高德 JSAPI v2.0） |

### 页面路由

| 路径 | 组件 | 作用 |
|------|------|------|
| `/` | — | 重定向到 `/monitor` |
| `/monitor` | MonitorPage.vue | 实时监控（GPS 地图、状态卡片、AI 问答） |
| `/control` | ControlPage.vue | 设备控制（喷药、速度、方向、转向、急停） |

### 前端 API 调用表

| 前端页面/组件 | 调用 API | 用途 | 是否影响车辆动作 |
|-------------|---------|------|----------------|
| MonitorPage | `GET /updateData`（每2s） | 获取 GPS 轨迹 | 否 |
| MonitorPage | `GET /vehicle_status`（每2s） | 获取车辆状态 | 否 |
| ControlPage | `GET /vehicle_status`（每2s） | 获取车辆状态 | 否 |
| ControlPage | `POST /status` | 接收开关（旧兼容） | 否 |
| ControlPage | `POST /spray_control` | 启动/停止喷药 | **是** |
| ControlPage | `POST /speed_control` | 设置速度 | **是** |
| ControlPage | `POST /direction_control` | 设置方向（前/停/后） | **是** |
| ControlPage | `POST /turn_control` | 设置转向位置 | **是** |
| ControlPage | `POST /emergency_stop` | 紧急停止 | **是** |
| NavBarNew | `GET /vehicle_status`（每5s） | 在线状态检测 | 否 |
| NavBarNew | `POST /emergency_stop` | 紧急停止 | **是** |

### 前端关键特性

- **高德地图**: 3D 模式，zoom 18，默认中心为新疆坐标(~81.3°E, 40.55°N)。车辆标记用自定义 SVG 图标，根据 GPS 航向角旋转。轨迹用绿色折线绘制。
- **视频流**: 当前前端未显示视频流（无 `<video>` 元素或 MJPEG 引用），备用页面 `templates/index.html` 有视频显示功能。
- **急停按钮**: 导航栏和 ControlPage 各有一个，均为红色脉动按钮，调用 `POST /emergency_stop`。
- **智能问答 iframe**: MonitorPage 嵌入 `http://127.0.0.1:8080/ui/chat/a668fc74f5f490f1`（可能是 Dify/DeepSeek 本地服务），公网访问时可能不可用，不影响系统功能。
- **键盘快捷键**: 无（Vue 前台无键盘事件监听）。
- **自动驾驶入口**: 无。前端没有任何自动驾驶/路线/导航/SLAM/雷达状态的 UI 元素。

### 构建输出

- 生产构建: `npm run build` → `dist/`
- Base path: `/app/`（生产模式）
- Flask 通过 `/app/<path>` 路由托管

---

## 8. 图像识别 / YOLO / RKNN 说明

### 检查结果

| 项目 | 状态 | 位置 |
|------|------|------|
| 数据集 | 不存在 | — |
| YOLO 模型文件 (.pt) | 不存在 | — |
| ONNX 模型文件 (.onnx) | 不存在 | — |
| RKNN 模型文件 | 存在 1 个（未使用） | `web/upper/Apple_leaf_detection.rknn` (4.1MB) |
| 推理代码 | 不存在 | — |
| `orangepi图像识别/` 目录 | 不存在 | — |

### 结论

- `Apple_leaf_detection.rknn` 是一个苹果叶病害检测的 RKNN 模型，但**完全未被系统引用**
- 无 YOLO 训练/导出脚本
- 无推理代码（没有任何 Python 文件导入 rknn-toolkit 或 rknnlite）
- 图像识别与喷药控制之间**没有任何闭环**
- 视频流仅用于显示和人眼观测，不用于机器视觉决策

### 后续集成需要补充

1. 安装 RKNN toolkit（RKNN-Toolkit-Lite2 for Orange Pi 5B）
2. 编写推理 Python 脚本，从摄像头帧中检测叶片病害
3. 根据检测结果自动触发喷药（需在 `app.py` 或单独线程中实现）
4. 前端增加检测框叠加显示（修改 MJPEG 流或在 Vue 端叠加）

---

## 9. ROS / 雷达 / SLAM 当前状态

### 各方检查

| 项目 | 是否存在 | 状态 |
|------|---------|------|
| ROS1 Noetic 工作区 | 存在 | `ros/catkin_ws/`，仅有 src 目录 |
| roscore 主节点 | 按需启动 | 需手动 `roscore` |
| 自定义 ROS 包 | 存在 8 个 | 全部为**骨架**（仅有 README.md） |
| point_lio_unilidar | 存在 | **已编译可运行** |
| unitree_lidar_ros | 存在 | **已编译可运行** |
| unitree_lidar_sdk | 存在 | **已编译**（闭源 .a 库） |
| launch 文件 | 存在 | point_lio_unilidar: 6 个, unitree_lidar_ros: 2 个 |
| URDF/XACRO | 不存在 | spraying_car_description 仅有 README |
| TF 配置 | 部分存在 | SLAM 输出 `camera_init` → `aft_mapped`，无标准 TF 树 |
| move_base 配置 | 不存在 | spraying_car_navigation 仅有 README |
| teb_local_planner 配置 | 不存在 | — |
| waypoint 路线文件 | 不存在 | spraying_car_waypoint 仅有 README |
| PCD 地图文件 | 按需生成 | SLAM 输出到 `PCD/scans.pcd` |
| rosbag 数据 | 不存在 | bags/ 目录为空 |
| 地图 (.pgm/.yaml) | 不存在 | maps/ 目录为空 |

### 8 个骨架 ROS 包现状

这些目录只包含 README.md 文件，没有 CMakeLists.txt、package.xml 或任何源码：

| 包名 | 计划功能 | README 内容摘要 |
|------|---------|----------------|
| spraying_car_base | 底盘桥接 | `/cmd_vel` ↔ STM32 串口，发布 odom + vehicle_state。建议 Python 实现 |
| spraying_car_bringup | 启动聚合 | 主 launch 文件聚合所有子系统（README 为空） |
| spraying_car_description | URDF 模型 | 机器人模型描述（README 内容与 bringup 相同，疑似复制粘贴错误） |
| spraying_car_msgs | 自定义消息 | VehicleState.msg, VehicleCmd.msg |
| spraying_car_navigation | 导航堆栈 | move_base + costmap + teb_local_planner + map_server + AMCL 配置 |
| spraying_car_slam | SLAM 封装 | launch/config 封装 point_lio_unilidar，保持上游不改 |
| spraying_car_tools | 调试工具 | serial_test.py, cmd_vel_test.py, odom_test.py, emergency_stop_test.py, record_waypoint.py |
| spraying_car_waypoint | 航线跟随 | 固定路线 waypoint 执行，顺序发送目标位姿给 move_base |

### LiDAR 启动流程（已验证可运行）

```bash
# 终端 1: 启动 ROS Master
roscore

# 终端 2: 启动 LiDAR 驱动（发布 /unilidar/cloud + /unilidar/imu）
cd ros/catkin_ws/src/third_party/unilidar_sdk/unitree_lidar_ros
source devel/setup.bash
roslaunch unitree_lidar_ros run_without_rviz.launch

# 终端 3: 启动 Point-LIO SLAM
cd ros/catkin_ws/src/third_party/catkin_point_lio_unilidar
source devel/setup.bash
roslaunch point_lio_unilidar mapping_unilidar_l1.launch rviz:=false
```

来源: `ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/AGENTS.md`

### ROS 自动驾驶闭环现状

**当前不存在 ROS 自动驾驶闭环**。LiDAR + SLAM 可以独立建图，但以下关键链路均未实现：
- 建图结果 → 导航规划 → 速度/转向指令 → STM32 车辆执行
- 里程计（odom）发布
- 地图格式转换（PCD → 2D costmap）
- 全局/局部路径规划
- 遥控器安全接管机制

---

## 10. 当前实际数据流与控制流

### 已实现链路

```
1. 遥控器 → STM32 → 电机/转向/喷药 (已实现)
   RC Receiver → TIMx IC → Remote_control.c → car_drive.c → DAC/GPIO/PWM
   来源: firmware/spraying_car_lower/Core/Src/

2. Vue → Flask API → STM32 串口 → 车辆动作 (已实现)
   ControlPage.vue → POST /xxx_control → app.py send_xxx() → serial write → STM32 upper.c
   来源: web/upper/website/src/views/ControlPage.vue, web/upper/app.py

3. STM32 状态 → Flask → Vue (已实现，数据不完整)
   STM32 send_status_data() → USART1 → Flask receive_data() → /vehicle_status → Vue
   来源: firmware/.../upper.c:477, app.py:735-823, website/src/views/

4. GPS → Flask → Vue 地图 (已实现)
   GPS Module → Modbus RTU → gps_collection_thread → WGS84→GCJ02 → /updateData → MapContainer
   来源: app.py:415-499, website/src/components/MapContainer.vue

5. USB 摄像头 → Flask MJPEG → 页面视频 (已实现)
   VideoCamera.update() → JPEG encode → /video_feed → 浏览器 MJPEG 流
   来源: app.py:75-266, 仅备用模板页 templates/index.html 显示
```

### 半成品链路

```
6. LiDAR → ROS Driver → /unilidar/cloud (半成品)
   L1RM → USB → unitree_lidar_ros → /unilidar/cloud + /unilidar/imu
   可以运行，但数据不参与任何控制回路

7. /unilidar/cloud → point_lio_unilidar → PCD 地图 (半成品)
   SLAM 可以建图，但地图不能被导航系统使用
```

### 文档提到但源码未实现的链路

```
8. /cmd_vel → STM32 控制转换 (未实现)        ↑ 期望链路
9. 地图 → move_base → TEB → /cmd_vel (未实现)
10. waypoint 路线 → move_base (未实现)
11. 视觉识别 → 喷药自动决策 (未实现)
12. 电池电压 → 低电量返航 (未实现)
13. MQTT → 云端控制 (已废弃)
```

### ASCII 数据流图（当前）

```
                    ┌──────────────┐
                    │  RC Receiver │
                    │  (遥控器)     │
                    └──┬──┬──┬──┬──┘
                    CH3│CH4│CH5│CH6
                       │   │   │   │
                    ┌──▼───▼───▼───▼──┐
                    │    STM32F407    │
                    │  (下位机)       │
                    │  car_drive.c    │
                    │  turn.c         │
                    │                 │
                    │ DAC → 牵引电机  │
                    │ PWM → 步进电机  │
                    │ GPIO → 喷药继电 │
                    │ GPIO → 方向继电 │
                    │                 │
                    │ USART1 ←─┐      │
                    └──────────┼──────┘
                               │ 115200 8N1
                               │ /dev/ttyS3
                    ┌──────────┴──────┐
                    │   Orange Pi 5B  │
                    │   Flask app.py  │   ┌─────────┐
                    │                 │   │ USB Cam │
                    │ communication   │◄──┤ OpenCV  │
                    │ _thread         │   └─────────┘
                    │                 │
                    │ gps_collection  │   ┌─────────┐
                    │ _thread         │◄──┤ GPS     │
                    │                 │   │ Modbus  │
                    │ REST API /5000  │   └─────────┘
                    │ MJPEG /vid_feed │
                    │ Vue SPA /app    │
                    └──┬──────────────┘
                       │ HTTP
                    ┌──▼──────┐
                    │ Browser │
                    │ Vue 3   │
                    │ 高德地图 │
                    │ Element │
                    │ Plus    │
                    └─────────┘

                    ┌──────────────┐
                    │  L1RM LiDAR  │ (ROS 独立运行，未连接控制回路)
                    │  unitree_ros │
                    └──┬───────────┘
                       │ /unilidar/cloud
                    ┌──▼────────────────┐
                    │ point_lio_unilidar│
                    │ PCD 地图          │
                    └───────────────────┘
```

---

## 11. 当前构建、部署与运行方式

### 运行方式汇总表

| 模块 | 启动/构建命令 | 运行位置 | 依赖 | 验证方式 |
|------|-------------|---------|------|---------|
| **STM32 编译** | Keil MDK: 打开 `MDK-ARM/spraying_car.uvprojx` → Build | Windows/MDK | ARM Compiler 5, CubeMX FW_F4 V1.28.1 | 生成 `.hex/.axf` |
| **STM32 烧录** | Keil: Flash → Download (J-Link SWD 8000kHz) | — | J-Link 调试器 | 上电后 OLED 显示 "UART COMM INIT" |
| **上位机 Python 依赖** | `pip3 install flask flask-cors pyserial opencv-python numpy` | Orange Pi 5B | Python 3.8+ | `python3 -c "import flask, serial, cv2"` |
| **上位机启动** | `cd web/upper && python3 start.py` | Orange Pi 5B | 串口 `/dev/ttyS3`, GPS `/dev/ttyUSB0` | `curl http://127.0.0.1:5000/vehicle_status` |
| **前端构建** | `cd web/upper/website && npm install && npm run build` | 开发机或 Orange Pi | Node.js 18+ | 检查 `dist/index.html` 存在 |
| **前端访问** | 浏览器 `http://[IP]:5000/app` | 任意浏览器 | — | 看到监控页和控制页 |
| **frp 启动** | `frpc -c web/upper/deploy/frpc.ini` | Orange Pi 5B | frp 客户端 | 公网访问 `http://[公网IP]:5000/app` |
| **ROS roscore** | `source /opt/ros/noetic/setup.bash && roscore` | Orange Pi 5B | ROS Noetic | `rostopic list` 显示 `/rosout` |
| **LiDAR 驱动** | `roslaunch unitree_lidar_ros run_without_rviz.launch` | Orange Pi 5B | LiDAR 接 USB | `rostopic echo /unilidar/cloud` |
| **SLAM 建图** | `roslaunch point_lio_unilidar mapping_unilidar_l1.launch` | Orange Pi 5B | LiDAR 驱动先启动 | `rostopic echo /pointlio/odom` |

### 环境变量

| 变量 | 默认值 | 用途 | 代码位置 |
|------|--------|------|---------|
| VEHICLE_SERIAL_PORT | `/dev/ttyS3` | STM32 控制串口 | `app.py:305` |
| GPS_SERIAL_PORT | `/dev/ttyUSB0` | GPS Modbus 串口 | `app.py:306` |

### 常见故障与排查

| 故障 | 排查命令 | 原因 |
|------|---------|------|
| 串口无法连接 | `ls -la /dev/ttyS3`, `sudo usermod -aG dialout $USER` | 权限或 UART 未启用 |
| GPS 无数据 | `ls /dev/ttyUSB*`, 检查 `gps_connected` | 串口设备不对或模块未上电 |
| Vue 白屏 | 检查 `website/dist/index.html` 是否存在 | 未构建前端 |
| 公网 /app 404 | 确认 `npm run build` 已执行 | dist 为空或 base path 不对 |
| LiDAR 无数据 | 检查是否使用 USB 2.0/3.0 口（非 OHCI） | Orange Pi 5B OHCI 不稳定 |

---

## 12. 当前文档状态

| 文档路径 | 可信度 | 主要内容 | 是否过期 | 备注 |
|----------|--------|---------|---------|------|
| `README.md`（根目录） | — | 空文件 | — | 未填写 |
| `firmware/spraying_car_lower/CLAUDE.md` | ★★★★★ | STM32 开发指南，架构说明，控制路径，引脚表 | 最新 | 最权威的下位机文档 |
| `firmware/spraying_car_lower/README.md` | ★★★ | 固件基本说明 | 基本有效 | 信息较简略 |
| `web/upper/docs/使用文档.md` | ★★★★★ | 上位机部署、启动、API 测试、FAQ | 最新 | 最权威的上位机使用文档 |
| `ros/catkin_ws/src/third_party/catkin_point_lio_unilidar/AGENTS.md` | ★★★★★ | point_lio 编译、启动、调试、环境问题 | 最新 | 重要：记录了 conda PATH、OHCI USB 等坑 |
| `ros/catkin_ws/src/spraying_car_base/README.md` | ★★★ | 底盘包设计规划（仅设计，无实现） | 有效 | 作为设计文档参考 |
| `ros/catkin_ws/src/spraying_car_navigation/README.md` | ★★★ | 导航包设计规划（仅设计，无实现） | 有效 | 作为设计文档参考 |
| `web/upper/trash/` 下各文件 | ★ | 旧 MQTT、旧 GPS 代码 | **已过期** | 仅供参考 |
| `Gap_Analysis_and_Roadmap.md` | — | **不存在** | — | 未找到 |
| `果园车设计.md` | — | **不存在** | — | 未找到 |

### 只在文档中提到但源码未实现的功能

- `spraying_car_base/README.md` 描述的 `/cmd_vel` 桥接、odom 发布
- `spraying_car_navigation/README.md` 描述的 move_base/TEB/AMCL 配置
- `spraying_car_slam/README.md` 描述的 SLAM 封装 launch 文件
- `spraying_car_tools/README.md` 描述的调试脚本（serial_test.py 等）
- `spraying_car_waypoint/README.md` 描述的 waypoint 自动路线

---

## 13. 当前已实现功能与未实现功能清单

### 13.1 已实现且源码中可运行

| 序号 | 功能 | 关键文件 | 备注 |
|------|------|---------|------|
| 1 | 遥控器手动驾驶（速度/方向/转向/喷药） | `firmware/.../car_drive.c`, `Remote_control.c`, `turn.c` | RC 5 通道闭环 |
| 2 | Web 远程控制（速度/方向/转向/喷药） | `web/upper/app.py`, `website/src/views/ControlPage.vue` | 串口命令控制 |
| 3 | Web 急停 | `app.py:881-932`, `NavBarNew.vue`, `ControlPage.vue` | 4 命令 2 重试 |
| 4 | 遥控器与串口双控仲裁 | `car_drive.c:117-231` | RC 变化自动接管 |
| 5 | 转向步进电机 PID 闭环 | `turn.c:75-303` | 编码器反馈 |
| 6 | 主电源遥控器长按开关 | `main.c:96-112` | 约 2 秒长按 |
| 7 | GPS 实时轨迹显示 | `app.py:415-499`, `MapContainer.vue` | 高德地图 |
| 8 | USB 摄像头视频流 | `app.py:75-266`, `/video_feed` | MJPEG |
| 9 | OLED 调试显示 | `OLED.c`, `upper.c` DEBUG_MODE | 可通过宏关闭 |
| 10 | USB CDC 数据镜像 | `upper.c:181, 459` | 调试用 |
| 11 | frp 公网访问 | `deploy/frpc.ini` | 已配置 |
| 12 | STM32 状态回传 (4 字节) | `upper.c:477-481` | 数据不完整 |

### 13.2 部分实现/半成品

| 序号 | 功能 | 已有文件 | 缺失 | 状态 |
|------|------|---------|------|------|
| 1 | point_lio_unilidar 建图 | 完整源码已编译 | 与底盘控制无桥接 | LiDAR+SLAM 可独立运行 |
| 2 | unitree_lidar_ros 驱动 | 完整源码已编译 | 数据仅发布到 ROS topic | 可独立发布点云和 IMU |
| 3 | Apple_leaf_detection.rknn 模型 | 模型文件 4.1MB | 无推理代码，未接入系统 | 孤立文件 |
| 4 | 电机速度控制 | DAC 电压输出 | 无实际车速反馈/标定 | 开环控制 |
| 5 | Flask 备用控制面板 | templates/index.html (1795行) | 不再维护 | 功能可用但不推荐 |

### 13.3 文档提到但源码未形成闭环

| 序号 | 功能 | 出现在 | 实际状态 |
|------|------|--------|---------|
| 1 | 自动导航/路径规划 | navigation README | 无代码 |
| 2 | RTK 高精度定位 | 设计文档 | 无硬件/代码 |
| 3 | LiDAR + DWA/TEB 避障 | navigation README | 无代码 |
| 4 | ROS 底盘桥接 (`/cmd_vel`) | base README | 无代码 |
| 5 | move_base / TEB 导航 | navigation README | 无代码 |
| 6 | waypoint 自动路线 | waypoint README | 无代码 |
| 7 | URDF 机器人模型 | description README | 无 URDF 文件 |
| 8 | 电池电压监测/低电量返航 | 多处文档提及 | 无硬件/代码 |
| 9 | 液位检测/药量不足返航 | 设计文档 | 无硬件/代码 |
| 10 | 增程器闭环控制 | 设计文档 | 无代码 |
| 11 | YOLO/RKNN 实时识别+自动喷药 | 模型文件存在 | 无推理/决策代码 |
| 12 | GLM/MaxKB 专家系统 | MonitorPage iframe | 仅嵌入 iframe，非系统内实现 |
| 13 | 小程序端 | 设计文档 | 无代码 |
| 14 | 云端 MQTT | trash/webbackend | 已废弃 |
| 15 | 多车管理 | 设计文档 | 无代码 |

---

## 14. 面向 ROS 化的差距分析

| 目标能力 | 当前状态 | 缺失内容 | 涉及目录/文件 | 建议优先级 | 风险 |
|----------|---------|---------|-------------|-----------|------|
| 1. ROS 底盘节点 | 无 | Python/C++ 节点，发布/订阅 | `spraying_car_base/` | **P0** | 需处理串口互斥 |
| 2. /cmd_vel → STM32 控制转换 | 无 | 速度分解为差速/阿克曼，转向角映射 | `spraying_car_base/scripts/` | **P0** | 需实车标定速度映射 |
| 3. STM32 扩展状态回传 | 仅 4 字节 | 轮速、转向角、编码器值、电池电压 | `upper.c`, `app.py` | **P0** | 需修改上下位机协议 |
| 4. /odom 或轮速里程计 | 无 | 基于轮速或编码器的里程计 | `spraying_car_base/` | **P0** | 当前无轮速编码器硬件 |
| 5. TF / URDF | 无 | URDF 文件，TF 广播 (base_link/odom/map) | `spraying_car_description/` | **P1** | 需测量车辆几何参数 |
| 6. L1RM 驱动 | ✓ 已编译 | 只需正确连接 | `third_party/unilidar_sdk/` | **P1** | OHCI USB 不稳定 |
| 7. point_lio 建图 | ✓ 已编译 | 需与 TF 树对齐 | `third_party/point_lio_unilidar/` | **P1** | 需修正 TF 帧 |
| 8. 地图保存 | ✓ PCD 输出 | 需转换为 2D 导航地图格式 | `spraying_car_slam/` | **P1** | PCD→PGM+YAML 转换 |
| 9. 2D/3D 地图转换 | 无 | 3D 点云 → 2D costmap | `spraying_car_slam/` | **P1** | 需要 pcl_ros 或 octomap |
| 10. move_base/TEB 导航 | 无 | launch 文件，yaml 参数配置 | `spraying_car_navigation/` | **P2** | 依赖前项完成 |
| 11. 局部避障 costmap | 无 | costmap 配置 | `spraying_car_navigation/config/` | **P2** | 依赖地图和 odom |
| 12. waypoint 路线执行 | 无 | waypoint 文件，执行引擎 | `spraying_car_waypoint/` | **P2** | 需考虑田间边界 |
| 13. Web 与 ROS 后端融合 | 无 | CONTROL_BACKEND 切换机制 | `app.py` | **P2** | 架构决策：Flask 内嵌 vs 独立 rosbridge |
| 14. 控制后端切换 serial/ros | 无 | 环境变量 + 代码分支 | `app.py` | **P2** | 避免串口冲突 |
| 15. 安全策略和急停 | 部分 | ROS 侧急停话题，硬件急停 | `spraying_car_base/`, STM32 | **P2** | 硬件急停独立于软件 |

---

## 15. 后续推荐开发顺序

### 阶段 1：固化文档和目录结构

- **目标**: 建立清晰可交接的代码基线
- **要修改的目录**: `docs/`（新增本文档及后续文档）、`README.md`（填写内容）
- **不应该动的目录**: `firmware/`, `web/`, `ros/`（不动源码）
- **输入**: 当前仓库状态
- **输出**: 完整的项目说明文档体系
- **验收**: 新开发者可根据文档理解系统
- **风险**: 低

### 阶段 2：抽离串口协议

- **目标**: 将串口协议独立为 Python 模块，Flask 和 ROS 节点共用
- **要修改的目录**: `web/upper/`（抽离协议代码为独立 .py 文件）、`ros/catkin_ws/src/spraying_car_base/`（新建节点）
- **不应该动的目录**: `firmware/`（不动 STM32）
- **输入**: `app.py` 中的协议实现
- **输出**: `serial_protocol.py` 独立模块，支持 Flask 和 ROS 双调用
- **验收**: 两个进程可共享协议模块而不冲突
- **风险**: 低（代码重构，不改变功能）

### 阶段 3：新增 ROS 工作区

- **目标**: 建立可编译的 ROS 工作区骨架（package.xml + CMakeLists.txt 补齐）
- **要修改的目录**: `ros/catkin_ws/src/spraying_car_*/`（为骨架包创建实际文件）
- **不应该动的目录**: `third_party/`（不修改第三方包）、`firmware/`、`web/`
- **输入**: 各包 README 中的设计规范
- **输出**: 8 个包均可被 catkin_make 编译通过
- **验收**: `catkin_make` 成功，`rospack list` 可见
- **风险**: 低

### 阶段 4：实现 ROS 底盘桥接

- **目标**: 实现 `/cmd_vel` → STM32 控制转换机器人
- **要修改的目录**: `spraying_car_base/`（新建 Python 节点）
- **不应该动的目录**: `firmware/`（不动 STM32 协议格式）
- **输入**: 抽离的串口协议模块、车辆运动学模型
- **输出**: `vehicle_base_node.py` 订阅 `/cmd_vel`，转换为串口命令
- **验收**: `rostopic pub /cmd_vel` 能驱动车辆运动
- **风险**: **中**（需要实车标定速度/转向映射关系）

### 阶段 5：扩展 STM32 状态包

- **目标**: 增加轮速编码器值、转向角、电池电压到状态回传
- **要修改的目录**: `firmware/spraying_car_lower/Core/Src/upper.c`（扩展 send_status_data）
- **不应该动的目录**: `turn.c`, `car_drive.c`（控制逻辑不动）
- **输入**: 新增传感器采集代码
- **输出**: 状态包从 4 字节扩展至 20+ 字节，含编码器、电压等
- **验收**: 上位机能正确解析扩展状态包
- **风险**: **高**（需要硬件支持轮速编码器、ADC 电压采集，需修改上下位机协议）

### 阶段 6：建立 TF/URDF

- **目标**: 创建机器人 URDF 模型，广播标准 TF 树
- **要修改的目录**: `spraying_car_description/`
- **输入**: 车辆几何测量（轴距、轮距、雷达安装位置）
- **输出**: URDF 文件，TF 广播节点
- **验收**: `rosrun tf view_frames` 显示正确的 TF 树
- **风险**: 低

### 阶段 7：接入 L1RM 和 point_lio

- **目标**: 将建图流程整合进 bringup launch，配置正确的 TF 帧
- **要修改的目录**: `spraying_car_bringup/`, `spraying_car_slam/`
- **不应该动的目录**: `third_party/catkin_point_lio_unilidar/`（上游不改）
- **输入**: 已有的 unitree_lidar_ros + point_lio_unilidar
- **输出**: 一键启动 launch 文件，TF 帧对齐到标准树
- **验收**: 启动一次建图 → 保存 PCD 地图
- **风险**: **中**（Orange Pi GPU 不支持 rviz，需远程显示；OHCI USB 不稳定）

### 阶段 8：保存地图

- **目标**: 保存 PCD 地图并转换为 2D 导航地图
- **要修改的目录**: `spraying_car_slam/`, `maps/`
- **输入**: point_lio 输出的 PCD
- **输出**: `maps/farm_map.pgm` + `maps/farm_map.yaml`
- **验收**: map_server 可加载地图，rviz 可显示
- **风险**: 低（纯软件转换）

### 阶段 9：接入 move_base/TEB

- **目标**: 实现全局 + 局部路径规划
- **要修改的目录**: `spraying_car_navigation/`
- **输入**: 地图、底盘里程计、TF 树
- **输出**: move_base 可接收目标点并生成 /cmd_vel
- **验收**: rviz 中设定导航目标，车辆跟踪路径
- **风险**: **高**（需要在真实环境中调参，农业场景的 costmap 配置不同）

### 阶段 10：实现 waypoint 路线

- **目标**: 实现预先录制的路线自动执行
- **要修改的目录**: `spraying_car_waypoint/`
- **输入**: waypoint 列表、move_base
- **输出**: 可录制、回放路线的工具
- **验收**: 加载路线后自动走完全程
- **风险**: **中**（需要行间导航策略，不仅仅是到点）

### 阶段 11：Flask 增加 CONTROL_BACKEND

- **目标**: Flask 支持 serial 或 ros 两种控制后端
- **要修改的目录**: `web/upper/app.py`
- **不应该动的目录**: `website/`（前端不变）
- **输入**: 阶段 4 的 ROS 底盘节点
- **输出**: `CONTROL_BACKEND=ros` 时 Flask 通过 ROS topic 通信
- **验收**: 切换环境变量后，Vue 控制命令到达正确的后端
- **风险**: **中**（需设计 ROS ↔ Flask 之间的通信机制）

### 阶段 12：Vue 增加自动驾驶入口

- **目标**: 前端增加导航目标点设定、路线选择、SLAM 状态显示
- **要修改的目录**: `website/src/`
- **输入**: ROS 后端 API / rosbridge
- **输出**: 新的 Vue 页面或组件
- **验收**: 可在前端设定导航目标、查看全局/局部 costmap
- **风险**: 低

### 阶段 13：完善安全测试清单

- **目标**: 编写安全测试文档和测试流程
- **要修改的目录**: `docs/`
- **输入**: 上述各阶段的实现
- **输出**: 安全测试 checklist
- **验收**: 按清单执行测试并记录
- **风险**: 低

---

## 16. 需要人工确认的问题

| 序号 | 问题 | 重要性 |
|------|------|--------|
| 1 | 车辆轴距、轮距、最小转弯半径（用于 URDF 和运动学模型） | 极高 |
| 2 | 转向机构最大角度（对应 CH4=1 和 CH4=101 时的实际角度） | 极高 |
| 3 | 速度档位 1..102 对应的实际车速（需要场地标定） | 极高 |
| 4 | STM32 是否已有或计划安装轮速编码器（目前无轮速反馈） | 极高 |
| 5 | 转向编码器值 (0, ±500, ±25000) 与实际转向角的标定关系 | 极高 |
| 6 | 雷达安装位置和姿态（相对车辆中心的前后/左右/高度/俯仰角） | 高 |
| 7 | IMU 安装位置和姿态（目前使用 LiDAR 内置 IMU） | 高 |
| 8 | GPS 是普通 GNSS 还是 RTK（代码中为普通 Modbus GPS） | 高 |
| 9 | 串口设备名在 Orange Pi 上是否固定（`/dev/ttyS3`, `/dev/ttyUSB0`） | 高 |
| 10 | 自动驾驶时是否允许遥控器随时接管（目前仲裁逻辑优先 RC） | 高 |
| 11 | 急停硬件是否独立可靠（目前仅软件急停，无物理急停开关） | 极高 |
| 12 | 喷药泵和风机是同一继电器还是分别控制（代码中仅一个继电器） | 中 |
| 13 | 目标导航模式：行间路径跟踪（rows）还是普通点到点导航 | 高 |
| 14 | 目标运行环境：果园、温室、农田、校园道路还是室内测试场地 | 高 |
| 15 | 直流电机控制器的型号和控制模式（电压? 占空比? 方向由哪侧控制?） | 高 |
| 16 | 步进电机驱动器的型号和细分设置（影响编码器对应关系） | 中 |
| 17 | 当前是否已有电池电压采集硬件（ADC 分压电路） | 中 |
| 18 | Orange Pi 5B 上 ROS Noetic 是否已安装并可用 | 中 |
| 19 | 后续是否需要 MQTT 云端接入 | 低 |
| 20 | 是否需要多车协同管理 | 低 |

---

## 17. 给下一个 AI 助手的关键提醒

1. **不要删除 `trash/` 目录**：其中旧 GPS 和 MQTT 代码可能在理解历史架构时有用。
2. **不要修改 `third_party/` 中的第三方包**：它们有自己的 git 历史，应通过 launch/config 封装而非修改源码。
3. **STM32 `car_drive.c` 的三层架构是必须遵守的模式**：`hw_set_*`(纯硬件) → `*_set`(串口入口) → `update_rc_control`(RC 入口)。新增执行器必须遵循此模式。
4. **串口协议的 checksum 仅计算 data 字段**，不包含 type/len/head/tail。错误理解会导致协议失败。
5. **Orange Pi 5B 的 OHCI USB 控制器不稳**：LiDAR 必须接 USB 2.0/3.0 (xhci) 口，不要用 USB 1.1 (ohci) 口。
6. **Orange Pi 上有 conda Python 路径冲突**：ROS 命令前必须 `export PATH="/usr/bin:/opt/ros/noetic/bin:$PATH"`。
7. **转向编码器是 int16_t**：在边界工况下可能溢出，修改协议时考虑用 int32_t。
8. **Flask 和 ROS 节点不能同时打开同一串口**：实现 CONTROL_BACKEND 时必须注意互斥。
9. **Vue 构建 base 路径是 `/app/`**：这与 Flask 的 `/app` 路由匹配。修改 vite.config.js 的 base 时需同步修改 Flask 路由。
10. **Apple_leaf_detection.rknn 存在但完全未接入系统**：如果要启动图像识别功能，需从头编写推理脚本。
11. **`battery_voltage` 始终为 0**：在添加真实 ADC 采集之前，不要依赖电池状态逻辑。
12. **高德地图 API key 硬编码在前端**：`MapContainer.vue` 中的 key `5453af1e113023d3770919da5ce11f23` 是应用密钥，部署时注意安全。
13. **frpc.ini 包含远程服务器地址**：在公开文档中不要原文贴出。
14. **当前遥控器 ARBITRATION（仲裁）逻辑让 RC 优先**：自动驾驶开发时需要评估是否需要在 UART 模式时禁用 RC 接管（可通过新增命令实现）。
15. **ROS 包全部是骨架**：不要期望能直接 `roslaunch spraying_car_bringup`，需要从 `spraying_car_base` 开始逐个实现。
16. **point_lio 只发布 `camera_init → aft_mapped` TF**：需要增加 `base_link`、`odom`、`map` 等标准 TF 帧才能接入导航。
17. **STM32 USART2 已初始化但未启用**：可作为备用扩展通讯口，避免和 USART1 抢占。
18. **文档散落在多个位置**：最权威的参考是各目录下的 CLAUDE.md / AGENTS.md / 使用文档.md。

---

> **文档结束**  
> **创建者**: 项目审计与交接文档工程师（AI）  
> **阅读的关键文件**: 仓库中所有非 node_modules 的源码、头文件、配置、文档和 README  
> **未修改任何源码**: 确认  
> **生成的文档**: `docs/PROJECT_HANDOFF_FOR_CHATGPT.md`
