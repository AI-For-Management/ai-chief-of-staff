@echo off
chcp 65001 >nul 2>&1

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 需要管理员权限
    pause
    exit /b 1
)

schtasks /Delete /TN "AI-Chief-of-Staff-AutoStart" /F

if %errorlevel% equ 0 (
    echo ✅ 已取消开机自启
) else (
    echo ⚠️  任务不存在或删除失败
)

pause
