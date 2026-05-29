#!/usr/bin/env bash
cd "$(dirname "$0")/.."
echo ""
echo "========================================"
echo "  📊 系统状态"
echo "========================================"
echo ""
echo "[容器状态]"
docker compose ps
echo ""
echo "[健康检查]"
curl -s http://localhost:8000/health 2>/dev/null && echo "" || echo "❌ FastAPI未响应"
echo ""
echo "[资源占用]"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep ai-secretary
