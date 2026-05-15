#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPS数据上传程序 - WiFi版本
功能：通过读取GPS模块数据，并通过WiFi网络上传
"""
import paho.mqtt.client as mqtt
import serial
import struct
import math
import json
import os
import time
import requests  # 新增HTTP请求库


class GPSUploader:
    """GPS数据上传器"""
    
    # 常量定义
    PI = 3.14159265358979324
    A = 6378245.0
    EE = 0.00669342162296594323
    
    def __init__(self, gps_config=None, server_config=None, mqtt_config=None):
        """初始化GPS上传器"""
        # GPS串口默认配置
        self.gps_config = {
            'port': '/dev/ttyUSB0',
            'baudrate': 115200,
            'bytesize': serial.EIGHTBITS,
            'parity': serial.PARITY_NONE,
            'stopbits': serial.STOPBITS_ONE,
            'timeout': 1
        }
        
        # 服务器配置
        self.server_config = {
            'interval': 1  # 数据发送间隔(秒)
        }
        
        # MQTT配置
        self.mqtt_config = {
            'enabled': True,                # 是否启用MQTT
            'broker': os.environ.get('MQTT_BROKER', 'localhost'),  # 旧MQTT模式的代理地址
            'port': 1883,                   # MQTT端口
            'topic': 'main/message',        # MQTT主题
            'client_id': 'gps_uploader',    # 客户端ID
            'username': '',                 # 用户名（如有）
            'password': ''                  # 密码（如有）
        }
        
        # 更新配置
        if gps_config:
            self.gps_config.update(gps_config)
        if server_config:
            self.server_config.update(server_config)
        if mqtt_config:
            self.mqtt_config.update(mqtt_config)
            
        # 串口对象
        self.gps_serial = None
        # MQTT客户端
        self.mqtt_client = None
        
        # Modbus请求命令
        self.modbus_cmd = '01 03 00 00 00 14 45 C5'  # 读取保持寄存器命令
        
        # 记录上次发送时间
        self.last_send_time = 0
    
    def setup(self):
        """初始化串口连接和MQTT连接"""
        try:
            # 初始化GPS串口
            self.gps_serial = serial.Serial(**self.gps_config)
            print(f"GPS串口已连接: {self.gps_config['port']}")
            
            # 初始化MQTT客户端
            if self.mqtt_config['enabled']:
                self.setup_mqtt()
                print(f"MQTT已启用，代理: {self.mqtt_config['broker']}:{self.mqtt_config['port']}")
            
            return True
        except Exception as e:
            print(f"初始化失败: {e}")
            return False
    
    def setup_mqtt(self):
        """设置MQTT客户端"""
        try:
            # 创建MQTT客户端实例
            self.mqtt_client = mqtt.Client(client_id=self.mqtt_config['client_id'])
            
            # 设置认证（如果需要）
            if self.mqtt_config['username']:
                self.mqtt_client.username_pw_set(
                    self.mqtt_config['username'], 
                    self.mqtt_config['password']
                )
                
            # 设置连接回调
            self.mqtt_client.on_connect = self.on_mqtt_connect
            
            # 连接到MQTT代理服务器
            self.mqtt_client.connect(
                self.mqtt_config['broker'], 
                self.mqtt_config['port'], 
                60
            )
            
            # 启动MQTT循环（在后台线程中）
            self.mqtt_client.loop_start()
            
            return True
        except Exception as e:
            print(f"MQTT设置失败: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            print("成功连接到MQTT代理")
        else:
            print(f"MQTT连接失败，返回码: {rc}")
    
    def cleanup(self):
        """清理资源"""
        if self.gps_serial and self.gps_serial.is_open:
            self.gps_serial.close()
            print("GPS串口已关闭")
            
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("MQTT连接已关闭")
    
    def hex_to_float(self, hex_bytes):
        """将4个十六进制字节转换为浮点数"""
        if len(hex_bytes) != 4:
            raise ValueError("输入必须是包含4个字节的列表")
            
        byte_data = bytes(hex_bytes)
        return struct.unpack('>f', byte_data)[0]
    
    def string_to_hex(self, hex_strings):
        """将十六进制字符串列表转换为整数列表"""
        return [int(x, 16) for x in hex_strings]
    
    def transform_lat(self, x, y):
        """转换纬度"""
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * self.PI) + 20.0 * math.sin(2.0 * x * self.PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * self.PI) + 40.0 * math.sin(y / 3.0 * self.PI)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * self.PI) + 320 * math.sin(y * self.PI / 30.0)) * 2.0 / 3.0
        return ret
    
    def transform_lon(self, x, y):
        """转换经度"""
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * self.PI) + 20.0 * math.sin(2.0 * x * self.PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * self.PI) + 40.0 * math.sin(x / 3.0 * self.PI)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * self.PI) + 300.0 * math.sin(x / 30.0 * self.PI)) * 2.0 / 3.0
        return ret
    
    def wgs84_to_gcj02(self, lon, lat):
        """WGS84坐标系转GCJ02坐标系"""
        dlat = self.transform_lat(lon - 105.0, lat - 35.0)
        dlon = self.transform_lon(lon - 105.0, lat - 35.0)
        radlat = lat / 180.0 * self.PI
        magic = math.sin(radlat)
        magic = 1 - self.EE * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((self.A * (1 - self.EE)) / (magic * sqrtmagic) * self.PI)
        dlon = (dlon * 180.0) / (self.A / sqrtmagic * math.cos(radlat) * self.PI)
        mglat = lat + dlat
        mglon = lon + dlon
        return mglon, mglat
    
    def send_data_mqtt(self, data):
        """通过MQTT发送数据"""
        if not self.mqtt_client:
            print("MQTT客户端未初始化")
            return False
            
        try:
            # 将数据转换为JSON
            json_data = json.dumps(data)
            
            # 通过MQTT发布数据
            result = self.mqtt_client.publish(
                self.mqtt_config['topic'],
                json_data
            )
            
            # 检查发布结果
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"MQTT数据已发布: {json_data}")
                return True
            else:
                print(f"MQTT发布失败，错误码: {result.rc}")
                return False
        except Exception as e:
            print(f"MQTT发送数据失败: {e}")
            return False
    
    def read_sensor_data(self):
        """读取传感器数据"""
        if not self.gps_serial or not self.gps_serial.is_open:
            print("GPS串口未打开")
            return None
            
        try:
            # 发送Modbus命令
            byte_data = bytes.fromhex(self.modbus_cmd.replace(' ', ''))
            self.gps_serial.write(byte_data)
            
            # 等待响应
            time.sleep(0.1)
            response = self.gps_serial.read_all()
            
            if not response:
                print("未收到GPS数据响应")
                return None
                
            # 处理响应数据
            data_list = response.hex(' ').split(' ')
            
            # 提取原始数据
            if len(data_list) < 29:
                print(f"数据长度不足: {len(data_list)}")
                return None
                
            longtitude_raw = data_list[7:11]
            latitude_raw = data_list[13:17]
            speed_raw = data_list[17:21]
            direction_raw = data_list[21:25]
            altitude_raw = data_list[25:29]
            
            # 转换数据
            longtitude = self.hex_to_float(self.string_to_hex(longtitude_raw))
            latitude = self.hex_to_float(self.string_to_hex(latitude_raw))
            speed = self.hex_to_float(self.string_to_hex(speed_raw))
            direction = self.hex_to_float(self.string_to_hex(direction_raw))
            altitude = self.hex_to_float(self.string_to_hex(altitude_raw))
            
            # 坐标转换
            gcj_lon, gcj_lat = self.wgs84_to_gcj02(longtitude, latitude)
            
            # 打包数据
            return {
                "location": [gcj_lon, gcj_lat],
                "speed": speed,
                "angle": direction,
                "altitude": altitude,
                "target_info": [
                    {"location": [123, 123]},  # 示例目标点
                ],
                "pump_status": {"pump1": False, "pump2": False},
                "timestamp": time.time()  # 添加时间戳
            }
        except Exception as e:
            print(f"读取传感器数据失败: {e}")
            return None
    
    def run(self):
        """主运行循环"""
        print("GPS数据上传程序启动（WiFi-MQTT模式）...")
        
        if not self.setup():
            print("初始化失败，程序退出")
            return
        
        try:
            while True:
                current_time = time.time()
                
                # 按照设定的时间间隔发送数据
                if current_time - self.last_send_time >= self.server_config['interval']:
                    # 读取并发送数据
                    data = self.read_sensor_data()
                    if data:
                        if self.send_data_mqtt(data):
                            self.last_send_time = current_time
                    else:
                        print("获取传感器数据失败")
                
                # 避免CPU占用过高
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("程序被用户中断")
        finally:
            self.cleanup()


if __name__ == "__main__":
    # 可选：自定义配置
    # gps_config = {'port': '/dev/ttyUSB1'}
    # mqtt_config = {'broker': '192.168.1.200', 'topic': 'gps/data'}
    
    # 创建并运行上传器
    uploader = GPSUploader()
    uploader.run()
