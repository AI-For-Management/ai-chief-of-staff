#!/usr/bin/env bash
# 立即触发一次数据库备份（同步等待结果）
# 备份产物落在 ./backups/backup_<db>_<时间戳>.sql.gz
set -euo pipefail

cd "$(dirname "$0")/.."

if ! docker compose ps celery-worker --status running --quiet | grep -q .; then
    echo "ERR: celery-worker 未运行，先 docker compose up -d"
    exit 1
fi

echo "==> 触发备份任务（celery-worker 内同步执行）"
docker compose exec -T celery-worker python -c "
from app.workers.backup_tasks import backup_database
import json
result = backup_database()
print(json.dumps(result, ensure_ascii=False, indent=2))
if result.get('status') != 'ok':
    raise SystemExit(1)
"

echo "==> 当前备份目录:"
ls -lh ./backups/ | tail -10
