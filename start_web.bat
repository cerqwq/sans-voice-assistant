@echo off
echo ========================================
echo   Sans 语音助手 - Web界面
echo ========================================
echo.

cd /d "%~dp0"

echo 正在启动Web服务器...
echo 浏览器访问: http://localhost:8080
echo.

python web_server.py --port 8080

pause
