@echo off
REM ============================================================
REM schedule-extractor v1.0 Windows 一键启动
REM 双击运行：分别在新窗口启动 Flask 后端与 Streamlit PC 管理端
REM ============================================================
chcp 65001 >nul
title schedule-extractor 启动器
cd /d "%~dp0"

echo ============================================================
echo   轻量化AI排班日程提取工具 v1.0
echo ============================================================
echo.
echo [1/2] 启动 Flask 后端（新窗口，端口 5000）...
start "schedule-extractor-backend" cmd /k py backend\app.py

REM 等待后端就绪
timeout /t 3 /nobreak >nul

echo [2/2] 启动 Streamlit PC 管理端（新窗口，端口 8501）...
start "schedule-extractor-streamlit" cmd /k py -m streamlit run pc_client\app_streamlit.py

echo.
echo ============================================================
echo   后端 API : http://127.0.0.1:5000/api/health
echo   PC 管理端: http://localhost:8501
echo.
echo 关闭对应窗口即可停止服务。
echo ============================================================
timeout /t 5 /nobreak >nul
