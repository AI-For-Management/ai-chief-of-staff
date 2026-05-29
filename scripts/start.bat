@echo off
chcp 65001 >nul 2>&1
setlocal

REM 切换到项目根目录
cd /d "%~dp0\.."

title AI Chief of Staff - 启动中

echo.
echo ========================================
echo   🏢 AI首席参谋 - 启动
echo ========================================
echo.

REM 检查Docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker未运行，正在尝试启动Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe" >nul 2>&1
    echo    请等待Docker Desktop启动完成（约30-60秒），然后重新运行本脚本
    echo.
    pause
    exit /b 1
)

REM 检查.env
if not exist .env (
    echo ⚠️  未找到 .env 文件，从 .env.example 创建...
    copy .env.example .env >nul
    echo ✅ 已创建 .env，请编辑该文件填入 SILICONFLOW_API_KEY
    echo.
    notepad .env
    pause
)

echo 🚀 正在启动所有服务...
docker compose up -d

if %errorlevel% neq 0 (
    echo.
    echo ❌ 启动失败！查看错误信息后按任意键退出
    pause
    exit /b 1
)

echo.
echo ⏳ 等待服务就绪（最多30秒）...
set /a count=0
:waitloop
timeout /t 2 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://localhost:8000/health 2>nul | findstr /C:"200" >nul
if %errorlevel% equ 0 goto ready
set /a count+=1
if %count% lss 15 goto waitloop

echo ⚠️  服务启动较慢，但已在后台运行
goto open_browser

:ready
echo ✅ 所有服务已就绪！

:open_browser
echo.
echo ========================================
echo   📍 访问地址
echo ========================================
echo   管理后台: http://localhost:8501
echo   API文档:  http://localhost:8000/docs
echo ========================================
echo.

REM 自动打开浏览器
start "" http://localhost:8501

echo 浏览器已自动打开。按任意键关闭此窗口。
pause >nul
