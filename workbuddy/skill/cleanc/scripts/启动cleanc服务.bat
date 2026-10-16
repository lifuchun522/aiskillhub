@echo off
chcp 65001 >nul
title cleanc - Windows C 盘可清理目录管理
cd /d "%~dp0"

echo ================================================================
echo  cleanc 管理页
echo ----------------------------------------------------------------
echo  由你自己的会话启动本服务，清理动作不受代理沙箱的批量删除保护限制。
echo  启动后浏览器访问: http://127.0.0.1:8848/
echo  关闭本窗口即停止服务。
echo ================================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [!] 未找到 python，请先安装 Python 3 并加入 PATH。
  pause
  exit /b 1
)

python server.py serve --port 8848
echo.
echo 服务已退出。
pause
