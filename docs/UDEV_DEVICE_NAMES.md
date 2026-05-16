# ROS 设备名固定建议

喷药车上多个 USB/串口设备可能同时存在。如果依赖 `/dev/ttyUSB0` 这类动态编号，重启或插拔后设备名可能变化，导致 LiDAR 和 GPS 配置互相抢占。

## 当前事实

- 车辆控制串口 `/dev/ttyS3` 在 Orange Pi 上基本固定。
- GPS 串口尚未固定。
- L1RM 可能默认使用 `/dev/ttyUSB0`。
- GPS 和 LiDAR 都可能被系统分配为 `/dev/ttyUSB0`。

## 建议目标

后续建议固定为：

- `/dev/spraying_car_lidar`
- `/dev/spraying_car_gps`

本阶段不写入系统 udev 规则，只记录建议和示例。

## 查看设备 ID

```bash
ls -l /dev/serial/by-id/
udevadm info -a -n /dev/ttyUSB0
```

## 示例规则

以下只是示例，不能直接复制使用。实际 `idVendor`、`idProduct`、`serial` 必须以本机 `udevadm` 输出为准。

```text
SUBSYSTEM=="tty", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="yyyy", ATTRS{serial}=="LIDAR_SERIAL", SYMLINK+="spraying_car_lidar"
SUBSYSTEM=="tty", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="yyyy", ATTRS{serial}=="GPS_SERIAL", SYMLINK+="spraying_car_gps"
```

规则写入系统后通常需要：

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

实际部署前先用 `ls -l /dev/spraying_car_lidar /dev/spraying_car_gps` 确认软链接指向正确设备。
