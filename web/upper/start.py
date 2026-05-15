import subprocess
import sys
import os

print("启动喷药车控制系统...")

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 启动app.py (控制模块)
app_process = subprocess.Popen([sys.executable, os.path.join(current_dir, 'app.py')])
print("已启动车辆控制模块 (app.py，GPS采集线程已内置)")

print("系统已完全启动，按Ctrl+C结束程序")

try:
    # 等待主进程结束
    app_process.wait()
except KeyboardInterrupt:
    print("正在关闭系统...")
    # 终止进程
    app_process.terminate()
    print("系统已关闭")
