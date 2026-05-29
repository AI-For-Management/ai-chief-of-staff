@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0\.."

title AI Chief of Staff - 重启

echo.
echo ========================================
echo   🔄 AI首席参谋 - 重启服务
echo ========================================
echo.

docker compose restart

echo.
echo ⏳ 等待服务就绪...
timeout /t 5 /nobreak >nul

curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 服务已重启完成
) else (
    echo ⚠️  服务可能仍在启动中，请稍候
)

echo.
echo 管理后台: http://localhost:8501
echo.
pause
