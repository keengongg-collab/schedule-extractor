@echo off
REM ============================================================
REM schedule-extractor v1.1 Windows 一键启动
REM 双击运行：分别在新窗口启动 Flask 后端与 PySide6 PC 桌面客户端
REM （旧 Streamlit 管理端保留为备用，启动命令见下方注释）
REM ============================================================
chcp 65001 >nul
title schedule-extractor 启动器
cd /d "%~dp0"

echo ============================================================
echo   轻量化AI排班日程提取工具 v1.1（AI 日程管理桌面端）
echo ============================================================
echo.
echo [1/2] 启动 Flask 后端（新窗口，端口 5000）...
start "schedule-extractor-backend" cmd /k py backend\app.py

REM 等待后端就绪
timeout /t 3 /nobreak >nul

echo [2/2] 启动 PySide6 PC 桌面客户端（连接真实后端）...
start "schedule-extractor-pc" cmd /k set USE_MOCK=0&& py pc_client\app.py

echo.
echo ============================================================
echo   后端 API : http://127.0.0.1:5000/api/health
echo   PC 客户端: 桌面窗口（USE_MOCK=0 连接真实后端）
echo.
echo   备用 Streamlit 管理端（如需）:
echo     py -m streamlit run pc_client\app_streamlit.py
echo.
echo 关闭对应窗口即可停止服务。
echo ============================================================
timeout /t 5 /nobreak >nul
