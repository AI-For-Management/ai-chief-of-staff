#!/usr/bin/env bash
# AI Chief of Staff - 启动
set -e
cd "$(dirname "$0")/.."

echo ""
echo "========================================"
echo "  🏢 AI首席参谋 - 启动"
echo "========================================"
echo ""

# 检查Docker
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 检查.env
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env，从 .env.example 创建..."
    cp .env.example .env
    echo "✅ 已创建 .env，请编辑该文件填入 SILICONFLOW_API_KEY"
    ${EDITOR:-nano} .env
fi

echo "🚀 启动所有服务..."
docker compose up -d

echo ""
echo "⏳ 等待服务就绪..."
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/health 2>/dev/null | grep -q '"ok"'; then
        break
    fi
    sleep 2
done

echo ""
echo "========================================"
echo "  📍 访问地址"
echo "========================================"
echo "  管理后台: http://localhost:8501"
echo "  API文档:  http://localhost:8000/docs"
echo "========================================"

# 自动打开浏览器
if command -v xdg-open >/dev/null; then
    xdg-open http://localhost:8501 >/dev/null 2>&1 &
elif command -v open >/dev/null; then
    open http://localhost:8501
fi
