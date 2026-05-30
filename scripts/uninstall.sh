#!/usr/bin/env bash
# 卸载脚本：停服务 + 可选删除数据卷 + 可选删除镜像
# 用法:  ./scripts/uninstall.sh [--purge]
#   --purge   也删除 pgdata / redisdata 数据卷（不可恢复！）
set -euo pipefail

cd "$(dirname "$0")/.."

PURGE=0
if [ "${1:-}" = "--purge" ]; then
    PURGE=1
fi

echo "==> 停止全部服务"
docker compose down

if [ "$PURGE" = "1" ]; then
    echo ""
    echo "!! --purge 将删除 pgdata 和 redisdata 数据卷（不可恢复）"
    echo "!! 备份文件 ./backups/ 仍会保留，可手动删除"
    echo "确认？输入 'YES' 继续:"
    read -r ans
    if [ "$ans" = "YES" ]; then
        docker compose down -v
        echo "==> 数据卷已删除"
    else
        echo "==> 已取消 purge，数据卷保留"
    fi
fi

echo ""
echo "==> 是否删除已构建的镜像（fastapi / celery / streamlit）？(y/N)"
read -r ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    docker images | grep -E "ai-secretary-" | awk '{print $3}' | xargs -r docker rmi -f
    echo "==> 镜像已删除"
fi

echo ""
echo "==> 卸载完成"
echo "    保留的内容:"
echo "      - .env 配置"
echo "      - ./backups/ 备份"
[ "$PURGE" = "1" ] || echo "      - 数据卷 pgdata / redisdata"
