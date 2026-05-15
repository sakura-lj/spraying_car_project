@echo off
echo 🚀 启动植保车云端监控系统...

REM 检查Node.js是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 需要安装Node.js
    echo 请访问 https://nodejs.org 下载并安装Node.js
    pause
    exit /b 1
)

REM 检查是否在正确的目录
if not exist package.json (
    echo ❌ 错误: 请在website目录下运行此脚本
    pause
    exit /b 1
)

REM 安装依赖
echo 📦 安装项目依赖...
call npm install

if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

echo ✅ 依赖安装完成

REM 启动开发服务器
echo 🌟 启动开发服务器...
echo 📱 访问地址: http://localhost:5173
echo 🔧 控制系统: http://localhost:5000
echo ⚡ 按 Ctrl+C 停止服务器

call npm run dev
pause
