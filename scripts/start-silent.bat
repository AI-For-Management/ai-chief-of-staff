@echo off
REM 静默版启动脚本 — 用于开机自启，不弹窗、不打开浏览器
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0\.."

REM 等待Docker Desktop就绪（最多5分钟）
set /a count=0
:wait_docker
docker info >nul 2>&1
if %errorlevel% equ 0 goto docker_ready
timeout /t 10 /nobreak >nul
set /a count+=1
if %count% lss 30 goto wait_docker

REM Docker一直没起来，写日志退出
echo [%date% %time%] Docker not ready after 5min >> "%~dp0\autostart.log"
exit /b 1

:docker_ready
echo [%date% %time%] Starting services... >> "%~dp0\autostart.log"
docker compose up -d >> "%~dp0\autostart.log" 2>&1
echo [%date% %time%] Started >> "%~dp0\autostart.log"
