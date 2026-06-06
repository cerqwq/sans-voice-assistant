@echo off
echo ========================================
echo   Sans 语音助手 - 现代化桌面界面
echo ========================================
echo.

cd /d "%~dp0"

echo 正在启动现代化界面...
echo 按 Ctrl+C 退出
echo.

python test_overlay.py

pause
