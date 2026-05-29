@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0\.."

title AI Chief of Staff - 状态

echo.
echo ========================================
echo   📊 AI首席参谋 - 系统状态
echo ========================================
echo.

echo [容器状态]
docker compose ps
echo.

echo [健康检查]
curl -s http://localhost:8000/health 2>nul && echo. || echo ❌ FastAPI 未响应
echo.

echo [资源占用]
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>nul | findstr ai-secretary

echo.
pause
