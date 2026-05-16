# STM32 UART Protocol

本文档记录当前 Orange Pi 上位机与 STM32 下位机之间的旧版串口协议。本阶段只抽离协议代码，不修改 STM32 固件，不改变协议格式。

## 帧格式

```text
[0xAA][type][len][data...][checksum][0x55]
```

字段说明：

- `0xAA`：固定帧头。
- `type`：1 字节命令类型。
- `len`：1 字节数据长度。
- `data`：命令或状态数据。
- `checksum`：1 字节校验和。
- `0x55`：固定帧尾。

## Checksum

当前校验规则：

```text
checksum = sum(data) % 256
```

注意：

- 只计算 `data` 字节。
- 不包含帧头、`type`、`len`、`checksum`、帧尾。
- 当前协议不是 CRC，只能发现部分传输错误。

## 命令

| 命令 | type | data | 作用 |
|------|------|------|------|
| `CMD_SPRAY_CONTROL` | `0x01` | 1 字节，`0` 关喷药，`1` 开喷药 | 控制喷药继电器 |
| `CMD_SPEED_CONTROL` | `0x02` | 1 字节，`1..102` | 控制牵引电机速度档位 |
| `CMD_DIRECTION_CONTROL` | `0x03` | 1 字节，`0` 停止，`1` 前进，`2` 后退 | 控制行驶方向 |
| `CMD_TURN_CONTROL` | `0x04` | 1 字节，`1..101`，`51` 为中位 | 控制转向位置 |
| `CMD_STATUS_QUERY` | `0xFF` | 当前旧逻辑发送 1 字节 `0x00` | 查询 STM32 状态 |
| `CMD_STATUS_RESPONSE` | `0x05` | 4 字节旧状态包 | STM32 状态响应 |
| `CMD_EXT_STATUS_QUERY` | `0x06` | 当前发送 1 字节 `0x00` | 查询扩展状态 |
| `CMD_EXT_STATUS_RESPONSE` | `0x07` | 26 字节扩展状态包 | STM32 扩展状态响应 |

## 旧状态响应

`CMD_STATUS_RESPONSE = 0x05`

当前旧状态响应 `data` 长度为 4 字节：

| 字节 | 字段 | 含义 |
|------|------|------|
| `data[0]` | `spray_state` | 喷药状态 |
| `data[1]` | `speed_duty` | 速度档位 |
| `data[2]` | `direction` | 行驶方向 |
| `data[3]` | `is_open` | 继电器/开启状态 |

旧状态包必须保留，不能直接替换为扩展状态包。原因：

- 旧 Flask/Web 链路已经依赖 0x05 的 4 字节格式。
- 上位机升级和 STM32 固件升级可能不同步。
- 保留 0x05 可让旧客户端继续工作，新增客户端优先使用 0x07。

## 扩展状态响应

`CMD_EXT_STATUS_QUERY = 0x06`

`CMD_EXT_STATUS_RESPONSE = 0x07`

扩展状态 `data` 长度固定为 26 字节，采用 little-endian：

| 字节 | 字段 | 类型 | 当前来源 |
|------|------|------|----------|
| `byte[0]` | `protocol_version` | `uint8` | 固定为 `1` |
| `byte[1]` | `spray_state` | `uint8` | 真实喷药状态 |
| `byte[2]` | `speed_duty` | `uint8` | 当前速度档位 |
| `byte[3]` | `direction` | `uint8` | 当前方向状态 |
| `byte[4]` | `is_open` | `uint8` | 当前电源/继电器状态 |
| `byte[5]` | `turn_cmd_position` | `uint8` | 最近一次转向命令位置 |
| `byte[6:10]` | `turn_target_encoder` | `int32` | 当前转向目标编码器位置 |
| `byte[10:14]` | `turn_encoder_position` | `int32` | TIM5 转向编码器读数，底层仍来自 `int16_t` 读取 |
| `byte[14]` | `uart_control_mode` | `uint8` | 真实控制模式，0 遥控器，1 串口 |
| `byte[15]` | `safety_state` | `uint8` | 占位，当前无独立硬件急停输入，填 0 |
| `byte[16:18]` | `fault_code` | `uint16` | 占位，当前无故障码系统，填 0 |
| `byte[18:20]` | `battery_mv` | `uint16` | 占位，当前无电池 ADC 采集，填 0 |
| `byte[20:22]` | `reserved_u16` | `uint16` | 保留，填 0 |
| `byte[22:26]` | `reserved_u32` | `uint32` | 保留，填 0 |

## 当前协议不足

当前协议已能支撑遥控器驾驶和 Web 远程控制闭环，但还不足以支撑完整 ROS 自动驾驶：

- 无真实轮速。
- 无真实转向角。
- 转向编码器字段已经回传，但底层读取仍是 `int16_t`，后续需要改造为完整 `int32_t` 计数。
- 电池电压字段存在但当前填 0。
- 无液位。
- 故障码字段存在但当前填 0。
- 无 CRC。

后续阶段需要继续扩展真实轮速、可靠转向角、安全状态和 CRC，满足条件后再用于正式 `/odom`。
