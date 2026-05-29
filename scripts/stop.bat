@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0\.."

title AI Chief of Staff - 停止

echo.
echo ========================================
echo   🛑 AI首席参谋 - 停止服务
echo ========================================
echo.

docker compose down

if %errorlevel% equ 0 (
    echo.
    echo ✅ 已停止所有服务
) else (
    echo.
    echo ⚠️  停止过程出现问题
)

echo.
pause
