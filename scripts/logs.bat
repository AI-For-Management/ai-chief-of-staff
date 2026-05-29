@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0\.."

title AI Chief of Staff - 实时日志

echo.
echo ========================================
echo   📋 实时日志 (按 Ctrl+C 退出)
echo ========================================
echo.

docker compose logs -f --tail=100
