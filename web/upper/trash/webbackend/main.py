from flask import Flask, jsonify, request
from flask_mqtt import Mqtt
from flask_cors import CORS
import json
import os

app = Flask(__name__)

# 临时存储
tempData = []
receiveStatus = False  # 初始化为否

# MQTT 配置
app.config['MQTT_BROKER_URL'] = os.environ.get('MQTT_BROKER_URL', 'localhost')  # 旧MQTT代理
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] = 5  # 心跳间隔（秒）
app.config['MQTT_TLS_ENABLED'] = False  # 禁用 TLS
app.config['MQTT_CLEAN_SESSION'] = True  # 清除旧会话

mqtt = Mqtt(app)
CORS(app)


# def data_process():


# MQTT 连接回调
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] 成功连接代理")
        mqtt.subscribe('main/message')  # 默认订阅主题
    else:
        print(f"[MQTT] 连接失败，错误码：{rc}")


# MQTT 消息接收回调
@mqtt.on_message()
def handle_message(client, userdata, message):
    # print(message.payload.decode())
    # print(type(message.payload.decode()))
    try:
        data = json.loads(message.payload.decode())

        global tempData
        # 只是读貌似不需要声明全局
        if receiveStatus:
            print(f"收到消息: {data}")
            tempData.append(data)

    except Exception as e:  # 如果解析失败，则直接返回原始数据
        print(f'数据疑似损坏：{message.payload.decode()}')


@app.route("/status", methods=['POST'], endpoint='status')
def updateStatus():
    global receiveStatus
    global tempData
    # 打印
    print(request.json)
    if request.json['receive_status']:
        receiveStatus = True
        print('开启接受')
    else:
        receiveStatus = False
        tempData = []
        print('关闭接受, 并清除临时数据')
    return jsonify(message="Success receive")


# 主页路由
@app.route('/updateData', methods=['GET'], endpoint='updateData')
def updateData():
    print('返回所有数据')
    mqtt.publish('main/getData', '114514')
    print('成功发送消息')
    return jsonify(tempData)


if __name__ == '__main__':
    # 注意：禁用 reloader 避免多实例问题
    app.run(host='0.0.0.0', port=5000, use_reloader=True)

# 发布消息的 API 接口
# @app.route('/publish/<message>')
# def publish(message):
#     mqtt.publish('test/topic', message)
#     return jsonify({"status": "消息已发布", "content": message})

# @app.route('/receiveStatus')
# def index():
#     return "Flask-MQTT 集成示例 | 访问 /publish/<消息内容> 发布消息"
