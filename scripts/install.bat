@echo off
chcp 65001 >nul
title AI首席参谋 — 一键部署

echo ========================================
echo   AI首席参谋 — 一键部署 (Windows)
echo ========================================
echo.

REM 检查Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Docker，请先安装Docker Desktop
    echo    下载地址: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo ✅ Docker 已就绪

REM 创建.env
if not exist .env (
    copy .env.example .env >nul
    echo.
    echo 📝 请配置以下信息：
    echo.
    set /p api_key="SiliconFlow API Key (sk-xxx): "

    powershell -Command "(Get-Content .env) -replace 'SILICONFLOW_API_KEY=sk-your-key-here', 'SILICONFLOW_API_KEY=%api_key%' | Set-Content .env"

    echo.
    echo ✅ API Key 已保存。其他配置请手动编辑 .env 文件
) else (
    echo ✅ .env 已存在，跳过配置
)

echo.
echo 🚀 正在启动服务（首次约5-10分钟）...
docker compose up -d --build

echo.
echo ⏳ 等待服务就绪...
timeout /t 15 /nobreak >nul

REM 数据库迁移
echo 📦 初始化数据库...
docker compose exec fastapi alembic upgrade head

echo.
echo ========================================
echo   ✅ 部署完成！
echo ========================================
echo.
echo   管理后台: http://localhost:8501
echo   API文档:  http://localhost:8000/docs
echo.
echo   默认账号: admin / admin123
echo   CEO账号:  ceo / ceo888
echo.
echo   （请在 .env 中修改密码）
echo.
pause
