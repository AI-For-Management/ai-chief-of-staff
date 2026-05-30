#!/usr/bin/env bash
# 升级流程：拉新代码 → 备份 → 重建镜像 → 迁移 DB → 重启
# 用法:  ./scripts/upgrade.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "==> [1/5] 拉取最新代码"
if [ -d ".git" ]; then
    git fetch --all
    git pull --ff-only || { echo "ERR: git pull 失败，请先解决冲突"; exit 1; }
else
    echo "    跳过（非 git 工作树）"
fi

echo "==> [2/5] 升级前自动备份数据库"
"$ROOT/scripts/backup_now.sh"

echo "==> [3/5] 重建镜像"
docker compose build

echo "==> [4/5] 应用数据库迁移"
docker compose up -d postgres redis
docker compose run --rm fastapi alembic upgrade head

echo "==> [5/5] 重启全部服务"
docker compose up -d
sleep 5
docker compose ps

echo ""
echo "==> 验证 /version + /health/ready"
curl -fsS http://localhost:8000/version && echo
curl -fsS http://localhost:8000/health/ready && echo
echo ""
echo "==> 升级完成"
