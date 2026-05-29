#!/usr/bin/env bash
cd "$(dirname "$0")/.."
echo "🛑 停止所有服务..."
docker compose down
echo "✅ 已停止"
