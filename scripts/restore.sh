#!/usr/bin/env bash
# 从 ./backups/ 中的 SQL.gz 文件恢复数据库
# 用法:  ./scripts/restore.sh backups/backup_chief_of_staff_2026-05-30_031700.sql.gz
#
# 警告：这是破坏性操作，会覆盖现有数据库内容。
# 建议先 docker compose down，然后再跑这个脚本。
set -euo pipefail

cd "$(dirname "$0")/.."

FILE="${1:-}"
if [ -z "$FILE" ]; then
    echo "用法: $0 <backup-file.sql.gz>"
    echo ""
    echo "可用备份:"
    ls -1 backups/*.sql.gz 2>/dev/null || echo "  （无备份文件）"
    exit 1
fi
if [ ! -f "$FILE" ]; then
    echo "ERR: 文件不存在: $FILE"
    exit 1
fi

DB_USER="${POSTGRES_USER:-chief}"
DB_NAME="${POSTGRES_DB:-chief_of_staff}"

echo "==> 即将恢复 $FILE 到数据库 $DB_NAME"
echo "==> 这将覆盖现有数据。继续？(y/N)"
read -r ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "已取消"; exit 0; }

# 确保 postgres 起着
docker compose up -d postgres
echo "==> 等待 postgres 就绪..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U "$DB_USER" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "==> 恢复中..."
gunzip -c "$FILE" | docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME"

echo "==> 完成。建议重启 fastapi/celery 让 ORM 重新连接:"
echo "    docker compose restart fastapi celery-worker celery-beat"
