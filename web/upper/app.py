import threading
import time
import logging
import json
import os
import math
import struct
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SprayCarApp')

try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# 导入串口库，优先使用pyserial
try:
    import serial
    from serial import SerialException
    SERIAL_AVAILABLE = True
    logger.info("成功导入pyserial库")
except ImportError:
    logger.error("未找到pyserial库，串口功能将不可用")
    logger.error("请安装pyserial: pip install pyserial")
    SERIAL_AVAILABLE = False
    # 创建一个虚拟的serial模块以避免错误
    class MockSerial:
        EIGHTBITS = 8
        PARITY_NONE = 'N'
        STOPBITS_ONE = 1
        @staticmethod
        def Serial(*args, **kwargs):
            raise Exception("pyserial库未安装")
    serial = MockSerial()
    SerialException = Exception

# 定义通信协议常量
PACKET_HEAD = 0xAA  # 数据包头部标识
PACKET_TAIL = 0x55  # 数据包尾部标识
BUFFER_SIZE = 256   # 缓冲区大小
READ_MAX_SIZE = 256  # 最大读取大小
RXBUFFER_LEN = 128  # 与 STM32 USART1 DMA 接收缓冲区保持一致
MAX_PACKET_DATA_LEN = 127  # Python 接收侧允许的最大 data 长度

# 定义命令类型
CMD_SPRAY_CONTROL = 0x01    # 喷药控制
CMD_SPEED_CONTROL = 0x02    # 速度控制
CMD_DIRECTION_CONTROL = 0x03  # 方向控制
CMD_TURN_CONTROL = 0x04     # 转向控制
CMD_STATUS_QUERY = 0xFF     # 状态查询
CMD_STATUS_RESPONSE = 0x05  # 状态响应

# 创建Flask应用
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VUE_DIST = os.path.join(BASE_DIR, 'website', 'dist')
app = Flask(__name__)
if CORS_AVAILABLE:
    CORS(app)
else:
    logger.warning("未找到flask-cors库，跨端口开发调试时可能需要安装: pip install flask-cors")

class VideoCamera:
    """摄像头类，用于捕获和处理视频流"""
    def __init__(self, camera_id=0, width=640, height=480):
        self.video = None
        self.is_running = False
        self.frame = None
        self.lock = threading.Lock()
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = 60
        self.connect_camera()
        
    def connect_camera(self):
        """连接到USB摄像头"""
        try:
            # 尝试多种摄像头设备格式
            camera_sources = [
                self.camera_id,              # 默认摄像头ID (通常为0)
                f'/dev/video{self.camera_id}',  # Linux格式
                f'video={self.camera_id}'       # 另一种格式
            ]
            
            # 尝试不同的摄像头源
            for source in camera_sources:
                try:
                    self.video = cv2.VideoCapture(source)
                    if self.video.isOpened():
                        logger.info(f"成功连接到摄像头: {source}")
                        break
                except Exception as e:
                    logger.warning(f"尝试连接 {source} 失败: {str(e)}")
                    continue
            
            if not self.video or not self.video.isOpened():
                logger.error("无法打开摄像头")
                return False
            
            # 保持高帧率，不降低
            self.fps = 60  # 使用原始设计的60fps
            
            # 设置分辨率 - 从高分辨率开始尝试
            test_resolutions = [
                (1920, 1080),  # 1080p全高清分辨率
                (1280, 720),   # 720p高清分辨率
                (800, 600),    # 替代分辨率
                (640, 480),    # 默认分辨率
                (320, 240)     # 降低的分辨率
            ]
            
            resolution_set = False
            for width, height in test_resolutions:
                # 尝试设置分辨率
                self.video.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                
                # 在设置分辨率后，确保同时设置高帧率
                self.video.set(cv2.CAP_PROP_FPS, self.fps)
                
                # 检查是否成功设置
                actual_width = self.video.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.video.get(cv2.CAP_PROP_FRAME_HEIGHT)
                actual_fps = self.video.get(cv2.CAP_PROP_FPS)
                
                # 使用更宽松的标准检查分辨率是否设置成功
                if abs(actual_width - width) < 100 and abs(actual_height - height) < 100:
                    self.width = int(actual_width)
                    self.height = int(actual_height)
                    resolution_set = True
                    logger.info(f"成功设置分辨率: {self.width}x{self.height} @ {actual_fps}fps")
                    break
            
            if not resolution_set:
                # 如果无法设置任何分辨率，使用摄像头默认值
                self.width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
                logger.warning(f"使用摄像头默认分辨率: {self.width}x{self.height}")
            
            # 尝试设置不同的格式
            formats = [
                (cv2.VideoWriter_fourcc('M','J','P','G')),  # MJPG - 高性能格式，通常支持高分辨率和高帧率
                (cv2.VideoWriter_fourcc('H','2','6','4')),  # H264 - 如果摄像头支持
                (cv2.VideoWriter_fourcc('Y','U','Y','V')),  # YUYV
                0  # 默认格式
            ]
            
            format_set = False
            for fmt in formats:
                self.video.set(cv2.CAP_PROP_FOURCC, fmt)
                # 每次设置格式后也重新设置分辨率和帧率
                self.video.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.video.set(cv2.CAP_PROP_FPS, self.fps)
                
                # 检查是否可以读取帧来验证格式是否设置成功
                success, _ = self.video.read()
                if success:
                    format_set = True
                    logger.info(f"成功设置视频格式: {fmt}")
                    break
                else:
                    # 如果设置格式后无法读取，需要重新打开摄像头
                    self.video.release()
                    self.video = cv2.VideoCapture(source)
            
            if not format_set:
                logger.warning("无法设置视频格式，使用默认值")
            
            # 设置帧率
            self.video.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 获取实际设置的参数
            actual_fps = self.video.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"摄像头实际参数: {self.width}x{self.height} @ {actual_fps}fps")
            
            # 启动获取帧的线程
            self.is_running = True
            self.thread = threading.Thread(target=self.update)
            self.thread.daemon = True
            self.thread.start()
            
            logger.info("摄像头已连接并开始捕获")
            return True
        except Exception as e:
            logger.error(f"摄像头连接失败: {str(e)}")
            return False
    
    def update(self):
        """持续更新摄像头帧的线程"""
        frame_count = 0
        last_log_time = time.time()
        
        while self.is_running:
            if self.video and self.video.isOpened():
                try:
                    success, frame = self.video.read()
                    if success:
                        # 添加时间戳到帧
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cv2.putText(frame, timestamp, (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        
                        # 更新帧
                        with self.lock:
                            self.frame = frame
                            
                        # 计算FPS
                        frame_count += 1
                        if frame_count % 100 == 0:
                            current_time = time.time()
                            elapsed = current_time - last_log_time
                            if elapsed > 0:
                                fps = frame_count / elapsed
                                logger.debug(f"摄像头FPS: {fps:.1f}")
                                frame_count = 0
                                last_log_time = current_time
                    else:
                        logger.warning("无法读取摄像头帧")
                        # 短暂暂停后重试
                        time.sleep(0.5)
                        # 尝试重新连接
                        if not self.video.isOpened():
                            logger.warning("尝试重新连接摄像头...")
                            self.connect_camera()
                except Exception as e:
                    logger.error(f"读取摄像头帧时出错: {str(e)}")
                    time.sleep(1)  # 出错时延长等待时间
            
            # 动态调整线程睡眠时间以匹配目标FPS
            time.sleep(1.0 / (self.fps * 1.5))  # 稍微更频繁地检查以避免丢帧
    
    def get_frame(self):
        """获取当前帧并转换为JPEG"""
        with self.lock:
            if self.frame is None:
                # 如果没有帧，返回一个黑色图像
                black_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                cv2.putText(black_frame, "Camera Disconnected", (int(self.width/4), int(self.height/2)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                _, jpeg = cv2.imencode('.jpg', black_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                return jpeg.tobytes()
            
            # 将BGR格式转换为JPEG，优化JPEG压缩质量参数
            _, jpeg = cv2.imencode('.jpg', self.frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return jpeg.tobytes()
    
    def __del__(self):
        """清理资源"""
        self.is_running = False
        if self.video:
            self.video.release()

class SprayApp:
    """
    喷药车应用主类，协调下位机通信
    """
    PI = 3.14159265358979324
    A = 6378245.0
    EE = 0.00669342162296594323
    GPS_MODBUS_CMD = '01 03 00 00 00 14 45 C5'

    def __init__(self):
        """
        初始化应用程序组件
        """
        # 系统状态
        self.is_running = False
        self.thread = None
        
        # 串口通信相关
        self.ser = None
        self.current_speed = 0.0  # 当前后轮速度
        self.parsing = False
        self.buffer = bytearray()

        # 喷药车控制相关
        self.spray_state = 0  # 喷药状态：0-关闭，1-开启
        self.speed_value = 0  # 速度值：1-102，51为中间值
        self.direction = 0  # 行进方向：0-停止，1-前进，2-后退
        self.turn_position = 51  # 转向位置：1-101，51为中间值
        
        # 车辆状态
        self.relay_state = 0  # 继电器状态：0-关闭，1-开启
        self.battery_voltage = 0
        
        # GPS数据
        self.gps_serial = None
        self.gps_data = {}
        self.gps_history = []
        self.vehicle_port = os.environ.get('VEHICLE_SERIAL_PORT', '/dev/ttyS3')
        self.gps_port = os.environ.get('GPS_SERIAL_PORT', '/dev/ttyUSB0')
        self.gps_running = True
        self.gps_thread = None
        self.gps_last_connect_attempt = 0
        self.frontend_receive_status = False
        
        # 通信锁，防止多线程同时操作串口
        self.serial_lock = threading.Lock()
        self.gps_lock = threading.Lock()
        self.gps_serial_lock = threading.Lock()
        
        # 通信状态
        self.last_status_update = 0
        self.communication_error_count = 0
        
        # 初始化串口
        self.init_serial()
        
        # 启动后台通信线程
        if self.ser:
            self.is_running = True
            self.thread = threading.Thread(target=self.communication_thread)
            self.thread.daemon = True
            self.thread.start()

        # 启动GPS采集线程，串口不可用时不阻塞Flask启动
        self.init_gps()
        self.gps_thread = threading.Thread(target=self.gps_collection_thread)
        self.gps_thread.daemon = True
        self.gps_thread.start()

    def init_gps(self):
        """初始化GPS Modbus RTU串口"""
        if not SERIAL_AVAILABLE:
            logger.error("pyserial库未安装，无法使用GPS串口")
            return False

        if self.gps_serial and self.gps_serial.is_open:
            return True

        try:
            control_port = getattr(self.ser, 'port', None)
            if control_port and control_port == self.gps_port:
                logger.warning(
                    f"GPS串口 {self.gps_port} 与车辆控制串口相同，跳过GPS连接；"
                    "请通过环境变量 GPS_SERIAL_PORT 指定独立GPS串口"
                )
                return False

            self.gps_serial = serial.Serial(
                port=self.gps_port,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                write_timeout=1
            )

            if self.gps_serial.is_open:
                self.gps_serial.flush()
                logger.info(f"GPS串口已连接: {self.gps_port}")
                return True
        except Exception as e:
            self.gps_serial = None
            logger.warning(f"GPS串口初始化失败: {e}")

        return False

    def hex_to_float(self, hex_bytes):
        """将4个十六进制字节转换为浮点数"""
        if len(hex_bytes) != 4:
            raise ValueError("输入必须是包含4个字节的列表")
        return struct.unpack('>f', bytes(hex_bytes))[0]

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

    def read_gps_data(self):
        """读取GPS模块数据并转换为前端轨迹点格式"""
        if not self.gps_serial or not self.gps_serial.is_open:
            return None

        try:
            with self.gps_serial_lock:
                byte_data = bytes.fromhex(self.GPS_MODBUS_CMD.replace(' ', ''))
                self.gps_serial.reset_input_buffer()
                self.gps_serial.write(byte_data)
                time.sleep(0.1)
                response = self.gps_serial.read_all()

            if not response:
                logger.debug("未收到GPS数据响应")
                return None

            data_list = response.hex(' ').split(' ')
            if len(data_list) < 29:
                logger.debug(f"GPS数据长度不足: {len(data_list)}")
                return None

            longtitude_raw = data_list[7:11]
            latitude_raw = data_list[13:17]
            speed_raw = data_list[17:21]
            direction_raw = data_list[21:25]
            altitude_raw = data_list[25:29]

            longtitude = self.hex_to_float(self.string_to_hex(longtitude_raw))
            latitude = self.hex_to_float(self.string_to_hex(latitude_raw))
            speed = self.hex_to_float(self.string_to_hex(speed_raw))
            direction = self.hex_to_float(self.string_to_hex(direction_raw))
            altitude = self.hex_to_float(self.string_to_hex(altitude_raw))

            if not all(math.isfinite(value) for value in [longtitude, latitude, speed, direction, altitude]):
                logger.debug("GPS数据包含无效浮点值")
                return None

            gcj_lon, gcj_lat = self.wgs84_to_gcj02(longtitude, latitude)

            return {
                "location": [gcj_lon, gcj_lat],
                "speed": speed,
                "angle": direction,
                "altitude": altitude,
                "target_info": [
                    {"location": [123, 123]},
                ],
                "pump_status": {"pump1": bool(self.spray_state), "pump2": False},
                "timestamp": time.time()
            }
        except Exception as e:
            logger.warning(f"读取GPS数据失败: {e}")
            try:
                if self.gps_serial:
                    self.gps_serial.close()
            except Exception:
                pass
            self.gps_serial = None
            return None

    def gps_collection_thread(self):
        """后台GPS采集线程，每秒更新当前点和最多500条轨迹"""
        while self.gps_running:
            try:
                if not self.gps_serial or not self.gps_serial.is_open:
                    current_time = time.time()
                    if current_time - self.gps_last_connect_attempt > 10:
                        self.gps_last_connect_attempt = current_time
                        self.init_gps()
                    time.sleep(1)
                    continue

                data = self.read_gps_data()
                if data:
                    with self.gps_lock:
                        self.gps_data = data
                        self.gps_history.append(data)
                        if len(self.gps_history) > 500:
                            self.gps_history = self.gps_history[-500:]

                time.sleep(1)
            except Exception as e:
                logger.warning(f"GPS采集线程错误: {e}")
                time.sleep(1)

    def init_serial(self):
        """
        初始化串口通信
        车辆控制串口固定使用硬件UART，默认 /dev/ttyS3
        """
        if not SERIAL_AVAILABLE:
            logger.error("pyserial库未安装，无法使用串口功能")
            logger.error("请运行: pip install pyserial")
            return False

        try:
            logger.info(f"连接车辆控制串口: {self.vehicle_port}")
            self.ser = serial.Serial(
                port=self.vehicle_port,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
                write_timeout=0.1
            )

            if self.ser.is_open:
                self.ser.flush()
                logger.info(f"成功连接车辆控制串口: {self.vehicle_port}")
                logger.info(f"串口参数: {self.ser.baudrate}bps, 8N1")
                return True

        except SerialException as e:
            logger.error(f"无法打开车辆串口 {self.vehicle_port}: {e}")
            logger.error("请检查:")
            logger.error(f"1. {self.vehicle_port} 设备是否存在 (ls -la {self.vehicle_port})")
            logger.error("2. 当前用户是否有串口权限 (sudo usermod -aG dialout $USER)")
            logger.error("3. 硬件UART是否已在系统中启用 (sudo orangepi-config → System → Hardware)")
            if 'ttyS' in self.vehicle_port:
                logger.error("提示：/dev/ttyS* 是硬件UART，需要在系统中启用：")
                logger.error("  sudo orangepi-config → System → Hardware → 启用对应UART")
                logger.error("  然后重启：sudo reboot")
        except Exception as e:
            logger.error(f"串口初始化失败: {e}")

        # [DEPRECATED] 原自动扫描逻辑，已改为固定端口。
        # 如现场硬件恢复为 USB 转串口，可参考下面代码恢复自动扫描。
        #
        # import glob
        # import os
        #
        # detected_ports = []
        #
        # if os.name == 'posix':
        #     usb_ports = glob.glob('/dev/ttyUSB*')
        #     detected_ports.extend(usb_ports)
        #
        #     acm_ports = glob.glob('/dev/ttyACM*')
        #     detected_ports.extend(acm_ports)
        #
        #     logger.info(f"检测到的USB串口设备: {detected_ports}")
        #
        # elif os.name == 'nt':
        #     for i in range(1, 21):
        #         detected_ports.append(f'COM{i}')
        #
        # priority_ports = []
        #
        # if '/dev/ttyUSB0' in detected_ports:
        #     priority_ports.insert(0, '/dev/ttyUSB0')
        #     detected_ports.remove('/dev/ttyUSB0')
        #
        # priority_ports.extend(detected_ports)
        #
        # fallback_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', 'COM3', 'COM4', 'COM5']
        # for port in fallback_ports:
        #     if port not in priority_ports:
        #         priority_ports.append(port)
        #
        # logger.info(f"端口扫描顺序: {priority_ports}")
        #
        # for port in priority_ports:
        #     try:
        #         logger.info(f"尝试连接串口: {port}")
        #         self.ser = serial.Serial(
        #             port=port,
        #             baudrate=115200,
        #             bytesize=serial.EIGHTBITS,
        #             parity=serial.PARITY_NONE,
        #             stopbits=serial.STOPBITS_ONE,
        #             timeout=0.1,
        #             write_timeout=0.1
        #         )
        #
        #         if self.ser.is_open:
        #             self.ser.flush()
        #             logger.info(f"成功连接到串口: {port}")
        #             logger.info(
        #                 f"串口参数: {self.ser.baudrate}bps, "
        #                 f"{self.ser.bytesize}数据位, {self.ser.parity}校验, {self.ser.stopbits}停止位"
        #             )
        #             return True
        #
        #     except SerialException as e:
        #         logger.debug(f"串口 {port} 连接失败: {e}")
        #         continue
        #     except Exception as e:
        #         logger.debug(f"串口 {port} 其他错误: {e}")
        #         continue
        #
        # logger.warning("无法连接到任何串口设备")
        # logger.warning("请检查:")
        # logger.warning("1. USB转串口设备是否已连接")
        # logger.warning("2. 设备驱动是否正确安装")
        # logger.warning("3. 设备权限是否正确 (Linux下可尝试: sudo chmod 666 /dev/ttyUSB*)")
        return False

    def reconnect_serial(self):
        """尝试重新连接串口"""
        if self.ser:
            try:
                self.ser.close()
                logger.info("已关闭现有串口连接")
            except Exception as e:
                logger.warning(f"关闭串口时出错: {e}")
        
        self.ser = None
        logger.info("尝试重新连接串口...")
        
        # 短暂延时，让设备稳定
        time.sleep(0.5)
        
        success = self.init_serial()
        if success:
            # 重置错误计数
            self.communication_error_count = 0
            logger.info("串口重新连接成功")
        else:
            logger.error("串口重新连接失败")
            
        return success

    def communication_thread(self):
        """后台通信线程，负责接收数据和保持连接"""
        while self.is_running:
            try:
                self.receive_data()
                
                # 定期查询状态
                current_time = time.time()
                if current_time - self.last_status_update > 2:  # 每2秒查询一次
                    self.query_status()
                    self.last_status_update = current_time
                
                # 检查连接状态
                if self.communication_error_count > 5:
                    logger.warning("通信错误过多，尝试重新连接")
                    if self.reconnect_serial():
                        self.communication_error_count = 0
                    else:
                        time.sleep(5)  # 连接失败，等待5秒再试
                
                time.sleep(0.05)  # 降低CPU使用率
            except Exception as e:
                logger.error(f"通信线程错误: {e}")
                self.communication_error_count += 1
                time.sleep(1)  # 出错时等待一秒后重试

    def pack_data(self, cmd_type, data_bytes):
        """
        通用数据打包方法
        
        参数:
            cmd_type: 命令类型
            data_bytes: 要发送的数据字节
        
        返回:
            打包后的完整数据包
        """
        if data_bytes is None or len(data_bytes) == 0:
            return None
            
        length = len(data_bytes)
        
        if length > BUFFER_SIZE:
            return None  # 数据过长，返回None
        
        # 构建完整的数据包
        buffer = bytearray(length + 5)  # 创建缓冲区，只分配需要的空间
        buffer[0] = PACKET_HEAD  # 添加包头
        buffer[1] = cmd_type     # 命令类型
        buffer[2] = length       # 添加长度
        
        # 添加数据
        for i in range(length):
            buffer[3 + i] = data_bytes[i]
        
        # 计算校验和
        checksum = sum(data_bytes) % 256
        buffer[length + 3] = checksum  # 添加校验和
        buffer[length + 4] = PACKET_TAIL  # 添加包尾
        
        return buffer  # 返回完整的数据包

    def send_packet(self, cmd_type, data_bytes, log_message=None):
        """
        通用数据包发送方法
        
        参数:
            cmd_type: 命令类型
            data_bytes: 要发送的数据字节
            log_message: 可选的日志消息
        
        返回:
            发送是否成功
        """
        if not self.ser or not self.ser.is_open:
            logger.warning("无法发送数据：串口未连接")
            return False
            
        packed_data = self.pack_data(cmd_type, data_bytes)
        if packed_data:
            try:
                with self.serial_lock:
                    self.ser.write(packed_data)
                if log_message:
                    logger.info(log_message)
                return True
            except Exception as e:
                logger.error(f"发送数据失败: {e}")
                self.communication_error_count += 1
                return False
        return False

    def query_status(self):
        """查询喷药车状态"""
        return self.send_packet(CMD_STATUS_QUERY, bytearray([0]), "查询车辆状态")

    def receive_data(self):
        """接收并解析串口数据"""
        if not self.ser or not self.ser.is_open:
            return
            
        # 尝试读取串口数据
        try:
            with self.serial_lock:
                while self.ser.in_waiting > 0:
                    data = self.ser.read(min(self.ser.in_waiting, READ_MAX_SIZE))
                    if not data:
                        break
                    for byte in data:
                        self.parse_byte(byte)
        except Exception as e:
            logger.error(f"读取串口数据失败: {e}")
            self.communication_error_count += 1

    def parse_byte(self, byte):
        """解析单个字节，效验数据包是否合规"""
        if byte == PACKET_HEAD:
            self.buffer = bytearray([PACKET_HEAD])
            self.parsing = True
        elif self.parsing:
            self.buffer.append(byte)

            if len(self.buffer) > RXBUFFER_LEN:
                logger.warning(f"接收缓冲区超过上限: {len(self.buffer)}，重置解析器")
                self.buffer = bytearray()
                self.parsing = False
                return
            
            if len(self.buffer) >= 3:
                length = self.buffer[2]
                if length > MAX_PACKET_DATA_LEN:
                    logger.warning(f"数据长度异常: {length}，重置解析器")
                    self.buffer = bytearray()
                    self.parsing = False
                    return

                expected_len = length + 5
                if len(self.buffer) == expected_len:
                    if self.buffer[-1] == PACKET_TAIL:
                        self.process_packet(self.buffer)
                    else:
                        logger.warning(f"包尾错误: 收到 {self.buffer[-1]}")
                    self.buffer = bytearray()
                    self.parsing = False
    
    def process_packet(self, packet):
        """处理完整数据包"""
        if len(packet) < 6:  # 数据包至少6字节
            return
            
        packet_type = packet[1]
        length = packet[2]
        
        # 验证数据包长度
        if length > MAX_PACKET_DATA_LEN:
            logger.warning(f"数据长度异常: {length}")
            return

        if len(packet) != length + 5:
            logger.warning(f"数据包长度错误: 收到 {len(packet)}，期望 {length + 5}")
            return

        if packet[-1] != PACKET_TAIL:
            logger.warning(f"包尾错误: 收到 {packet[-1]}")
            return
            
        data = packet[3:3+length]
        checksum = packet[3+length]
        
        # 验证校验和
        calculated_checksum = sum(data) % 256
        if calculated_checksum != checksum:
            logger.warning(f"校验和错误: 收到 {checksum}，计算得 {calculated_checksum}")
            return
            
        # 处理不同类型的数据包
        if packet_type == CMD_STATUS_RESPONSE:  # 状态数据
            if length >= 4:
                self.spray_state = data[0]
                self.speed_value = data[1]
                self.direction = data[2]
                self.relay_state = data[3]
                self.last_status_update = time.time()
                self.communication_error_count = 0  # 重置错误计数
                logger.debug(f"收到状态更新: 喷药={self.spray_state}, 速度={self.speed_value}, 方向={self.direction}, 继电器={self.relay_state}")

    def send_spray_control(self, spray_state):
        """发送喷药控制命令"""
        # 确保喷药状态为0或1
        spray_state = 1 if spray_state else 0
        
        data = bytearray(1) # 创建1字节数据
        data[0] = spray_state
        
        success = self.send_packet(CMD_SPRAY_CONTROL, data, f"发送喷药控制: {spray_state}")
        if success:
            # 立即更新本地状态
            self.spray_state = spray_state
        return success
    
    def send_speed_control(self, speed):
        """发送速度控制命令"""
        # 限制速度在1-102范围内
        speed = max(1, min(102, int(speed)))
        
        data = bytearray(1)
        data[0] = speed
        
        success = self.send_packet(CMD_SPEED_CONTROL, data, f"发送速度控制: {speed}")
        if success:
            # 立即更新本地状态
            self.speed_value = speed
        return success

    def send_direction_control(self, direction):
        """发送方向控制命令"""
        # 限制方向值为0(停止)、1(前进)或2(后退)
        direction = max(0, min(2, int(direction)))
        
        data = bytearray(1)
        data[0] = direction
        
        success = self.send_packet(CMD_DIRECTION_CONTROL, data, f"发送方向控制: {direction}")
        if success:
            # 立即更新本地状态
            self.direction = direction
        return success

    def send_turn_position(self, position):
        """发送转向角度控制命令"""
        # 限制位置在1-101范围内
        position = max(1, min(101, int(position)))
        
        data = bytearray(1)
        data[0] = position
        
        success = self.send_packet(CMD_TURN_CONTROL, data, f"发送转向位置: {position}")
        if success:
            # 立即更新本地状态
            self.turn_position = position
        return success

    def emergency_stop(self):
        """紧急停止所有动作 - 增强版，带重试机制"""
        logger.warning("🚨 执行紧急停止序列...")
        
        # 定义紧急停止命令序列
        commands = [
            ("方向控制", lambda: self.send_direction_control(0)),
            ("速度控制", lambda: self.send_speed_control(1)),
            ("喷药控制", lambda: self.send_spray_control(0)),
            ("转向控制", lambda: self.send_turn_position(51))
        ]
        
        success_count = 0
        total_commands = len(commands)
        
        # 执行每个命令，失败时重试一次
        for cmd_name, cmd_func in commands:
            success = False
            for attempt in range(2):  # 最多重试1次
                try:
                    if cmd_func():
                        success = True
                        logger.info(f"✅ {cmd_name}已停止")
                        break
                    else:
                        logger.warning(f"⚠️ {cmd_name}停止失败，重试中...")
                        time.sleep(0.1)  # 短暂延迟后重试
                except Exception as e:
                    logger.error(f"❌ {cmd_name}停止异常: {e}")
                    time.sleep(0.1)  # 短暂延迟后重试
            
            if success:
                success_count += 1
            else:
                logger.error(f"🔴 {cmd_name}停止彻底失败")
        
        # 强制更新本地状态确保一致性
        self.direction = 0
        self.speed_value = 1
        self.spray_state = 0
        self.turn_position = 51
        
        # 至少3个命令成功才算整体成功
        overall_success = success_count >= 3
        status_msg = f"紧急停止完成: {success_count}/{total_commands} 个命令成功"
        
        if overall_success:
            logger.warning(f"� {status_msg}")
        else:
            logger.error(f"🔴 {status_msg} - 系统可能未完全停止！")
        
        return overall_success

# 创建应用实例
spray_app = SprayApp()
camera = VideoCamera(camera_id=0, width=640, height=480)  # 可以根据需要调整参数

# Flask路由
@app.route('/')
def index():
    """主页路由，显示控制界面"""
    serial_status = "已连接" if spray_app.ser and spray_app.ser.is_open else "未连接"
    return render_template('index.html', serial_status=serial_status)

@app.route('/app')
@app.route('/app/')
@app.route('/app/<path:path>')
def serve_vue(path='index.html'):
    """托管Vue构建后的主控制面板"""
    requested_path = path or 'index.html'
    file_path = os.path.join(VUE_DIST, requested_path)
    if requested_path != 'index.html' and os.path.isfile(file_path):
        return send_from_directory(VUE_DIST, requested_path)
    return send_from_directory(VUE_DIST, 'index.html')

@app.route('/video_feed')
def video_feed():
    """视频流路由，用于显示摄像头画面"""
    def generate():
        while True:
            frame = camera.get_frame()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/spray_control', methods=['POST'])
def spray_control():
    """控制喷药开关的API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的JSON数据"})
            
        state = bool(data.get('state', False))
        
        success = spray_app.send_spray_control(state)
        
        return jsonify({
            "success": success,
            "state": state,
            "message": "喷药控制命令已发送" if success else "发送失败，请检查连接"
        })
    except Exception as e:
        logger.error(f"喷药控制失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/speed_control', methods=['POST'])
def speed_control():
    """控制车速的API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的JSON数据"})
            
        speed = int(data.get('speed', 51))
        
        success = spray_app.send_speed_control(speed)
        
        return jsonify({
            "success": success,
            "speed": speed,
            "message": "速度控制命令已发送" if success else "发送失败，请检查连接"
        })
    except Exception as e:
        logger.error(f"速度控制失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/direction_control', methods=['POST'])
def direction_control():
    """控制行进方向的API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的JSON数据"})
            
        direction = int(data.get('direction', 0))
        
        success = spray_app.send_direction_control(direction)
        
        return jsonify({
            "success": success,
            "direction": direction,
            "message": "方向控制命令已发送" if success else "发送失败，请检查连接"
        })
    except Exception as e:
        logger.error(f"方向控制失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/turn_control', methods=['POST'])
def turn_control():
    """控制转向角度的API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的JSON数据"})
            
        position = int(data.get('position', 51))
        
        success = spray_app.send_turn_position(position)
        
        return jsonify({
            "success": success,
            "position": position,
            "message": "转向控制命令已发送" if success else "发送失败，请检查连接"
        })
    except Exception as e:
        logger.error(f"转向控制失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    """紧急停止API"""
    try:
        logger.warning("🚨 收到紧急停止请求")
        success = spray_app.emergency_stop()
        
        status_msg = "紧急停止命令执行完成" if success else "紧急停止执行不完整，请检查设备连接"
        
        response = {
            "success": success,
            "message": status_msg,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "vehicle_state": {
                "direction": spray_app.direction,
                "speed": spray_app.speed_value,
                "spray": spray_app.spray_state,
                "turn": spray_app.turn_position
            }
        }
        
        if success:
            logger.warning(f"✅ 紧急停止成功: {status_msg}")
        else:
            logger.error(f"⚠️ 紧急停止部分失败: {status_msg}")
        
        return jsonify(response)
    except Exception as e:
        error_msg = f"紧急停止系统异常: {str(e)}"
        logger.error(f"🔴 {error_msg}")
        return jsonify({
            "success": False, 
            "message": error_msg,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

@app.route('/vehicle_status', methods=['GET'])
def vehicle_status():
    """获取车辆状态的API"""
    # 如果上次状态更新时间过长，先尝试查询一次
    if time.time() - spray_app.last_status_update > 3:
        spray_app.query_status()
        time.sleep(0.1)  # 等待一下，让状态可能更新

    with spray_app.gps_lock:
        gps_data = dict(spray_app.gps_data)
        gps_history = list(spray_app.gps_history)
    
    # 添加GPS数据到返回结果
    status = {
        "spray_state": spray_app.spray_state,
        "speed": spray_app.speed_value,
        "direction": spray_app.direction,
        "turn_position": spray_app.turn_position,
        "relay_state": spray_app.relay_state,
        "connected": spray_app.ser is not None and spray_app.ser.is_open,
        "gps": gps_data,
        "gps_history": gps_history,
        "gps_connected": spray_app.gps_serial is not None and spray_app.gps_serial.is_open,
        "battery_voltage": spray_app.battery_voltage
    }

    return jsonify(status)

@app.route('/updateData', methods=['GET'])
def update_data():
    """兼容Vue前端的GPS轨迹数据接口"""
    with spray_app.gps_lock:
        gps_history = [item for item in spray_app.gps_history if item.get("location")]
    return jsonify(gps_history)

@app.route('/status', methods=['POST'])
def status():
    """兼容旧Vue-MQTT中转的接收开关接口"""
    data = request.get_json(silent=True) or {}
    spray_app.frontend_receive_status = bool(data.get('receive_status', False))
    return jsonify({
        "success": True,
        "receive_status": spray_app.frontend_receive_status,
        "message": "状态已更新"
    })

@app.route('/reconnect', methods=['POST'])
def reconnect():
    """重新连接串口API"""
    success = spray_app.reconnect_serial()
    
    return jsonify({
        "success": success,
        "message": "串口重新连接成功" if success else "串口重新连接失败，请检查硬件"
    })

# 主程序入口
if __name__ == "__main__":
    print("喷药车控制系统已启动，访问 http://[设备IP]:5000 进行控制")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
