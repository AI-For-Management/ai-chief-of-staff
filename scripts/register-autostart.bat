@echo off
chcp 65001 >nul 2>&1
setlocal

REM 必须以管理员身份运行
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 需要管理员权限！
    echo    请右键此脚本，选择"以管理员身份运行"
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0\.."
set "SCRIPT_PATH=%cd%\scripts\start-silent.bat"

title AI Chief of Staff - 注册开机自启

echo.
echo ========================================
echo   ⚙️  注册开机自启
echo ========================================
echo.
echo 脚本路径: %SCRIPT_PATH%
echo.

REM 删除已有任务（如果存在）
schtasks /Delete /TN "AI-Chief-of-Staff-AutoStart" /F >nul 2>&1

REM 创建新任务：登录时自动运行（延迟2分钟等Docker Desktop启动完）
schtasks /Create /TN "AI-Chief-of-Staff-AutoStart" /TR "\"%SCRIPT_PATH%\"" /SC ONLOGON /DELAY 0002:00 /RL HIGHEST /F

if %errorlevel% equ 0 (
    echo.
    echo ✅ 已注册开机自启！
    echo    任务名: AI-Chief-of-Staff-AutoStart
    echo    触发: 用户登录后2分钟
    echo.
    echo 如需取消，运行 unregister-autostart.bat
) else (
    echo.
    echo ❌ 注册失败
)

echo.
pause
