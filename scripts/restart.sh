#!/usr/bin/env bash
cd "$(dirname "$0")/.."
echo "🔄 重启服务..."
docker compose restart
sleep 5
if curl -s http://localhost:8000/health 2>/dev/null | grep -q '"ok"'; then
    echo "✅ 服务已就绪"
else
    echo "⚠️  服务可能仍在启动中"
fi
