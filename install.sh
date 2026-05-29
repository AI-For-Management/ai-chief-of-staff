#!/bin/bash
#============================================================
# AI Chief of Staff — 一键部署脚本 (Linux/Mac)
#============================================================
set -e

echo "========================================"
echo "  🏢 AI首席参谋 — 一键部署"
echo "========================================"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未检测到Docker，请先安装Docker"
    echo "   Ubuntu: curl -fsSL https://get.docker.com | sh"
    echo "   Mac: 安装Docker Desktop"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ 未检测到Docker Compose"
    exit 1
fi

echo "✅ Docker 已就绪"

# 创建.env
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "📝 请配置以下信息（编辑 .env 文件）："
    echo ""

    read -p "SiliconFlow API Key (sk-xxx): " api_key
    sed -i "s|SILICONFLOW_API_KEY=sk-your-key-here|SILICONFLOW_API_KEY=$api_key|" .env

    read -p "管理员用户名 [admin]: " admin_user
    admin_user=${admin_user:-admin}
    read -s -p "管理员密码: " admin_pass
    echo ""
    read -p "CEO用户名 [ceo]: " ceo_user
    ceo_user=${ceo_user:-ceo}
    read -s -p "CEO密码: " ceo_pass
    echo ""

    sed -i "s|AUTH_USERS=admin:changeme,ceo:changeme|AUTH_USERS=$admin_user:$admin_pass,$ceo_user:$ceo_pass|" .env

    echo ""
    echo "✅ 配置已保存"
else
    echo "✅ .env 已存在，跳过配置"
fi

# 启动服务
echo ""
echo "🚀 正在启动服务（首次启动需下载镜像，约5-10分钟）..."
docker compose up -d --build

# 等待健康检查
echo ""
echo "⏳ 等待服务就绪..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/health | grep -q '"ok"'; then
        break
    fi
    sleep 2
done

# 运行数据库迁移
echo "📦 初始化数据库..."
docker compose exec -T fastapi alembic upgrade head

echo ""
echo "========================================"
echo "  ✅ 部署完成！"
echo "========================================"
echo ""
echo "  管理后台: http://$(hostname -I | awk '{print $1}'):8501"
echo "  API文档:  http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "  默认账号见 .env 中的 AUTH_USERS"
echo ""
echo "  常用命令:"
echo "    查看状态: docker compose ps"
echo "    查看日志: docker compose logs -f"
echo "    停止服务: docker compose down"
echo "    重启服务: docker compose restart"
echo ""
