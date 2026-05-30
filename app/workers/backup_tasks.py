"""数据库自动备份 Celery 任务

用 pg_dump 把 PostgreSQL 导出为 gzip 压缩的 SQL 文件，存到 /backups，
按文件名时间戳保留最近 RETENTION 份，更早的自动清理。
"""
import os
import re
import gzip
import glob
import logging
import subprocess
from datetime import datetime

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")
RETENTION = int(os.getenv("BACKUP_RETENTION", "14"))


def _parse_dsn(dsn: str) -> dict:
    """从 SQLAlchemy 同步 DSN 解析出 pg_dump 需要的连接参数。

    形如 postgresql://user:pass@host:port/dbname
    """
    m = re.match(
        r"postgresql(?:\+\w+)?://(?P<user>[^:]+):(?P<pwd>[^@]+)@"
        r"(?P<host>[^:/]+):(?P<port>\d+)/(?P<db>[^?]+)",
        dsn,
    )
    if not m:
        raise ValueError(f"无法解析 DATABASE_URL_SYNC: {dsn[:40]}...")
    return m.groupdict()


@celery_app.task(name="app.workers.backup_tasks.backup_database")
def backup_database() -> dict:
    """执行一次数据库备份并清理过期文件"""
    from app.config import get_settings

    settings = get_settings()
    try:
        conn = _parse_dsn(settings.DATABASE_URL_SYNC)
    except Exception as e:
        logger.error(f"备份失败：DSN 解析错误 {e}")
        return {"status": "error", "error": str(e)}

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = os.path.join(BACKUP_DIR, f"backup_{conn['db']}_{ts}.sql.gz")

    env = os.environ.copy()
    env["PGPASSWORD"] = conn["pwd"]
    cmd = [
        "pg_dump",
        "-h", conn["host"],
        "-p", conn["port"],
        "-U", conn["user"],
        "-d", conn["db"],
        "--no-owner",
        "--no-privileges",
    ]

    try:
        # pg_dump 输出经管道 gzip 写入文件
        with gzip.open(out_path, "wb") as gz:
            proc = subprocess.run(
                cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=True,
            )
            gz.write(proc.stdout)
        size = os.path.getsize(out_path)
        logger.info(f"数据库备份成功: {out_path} ({size} 字节)")
    except subprocess.CalledProcessError as e:
        # 失败时清掉半成品文件
        if os.path.exists(out_path):
            os.remove(out_path)
        err = (e.stderr or b"").decode(errors="ignore")[:200]
        logger.error(f"pg_dump 失败: {err}")
        return {"status": "error", "error": err}
    except Exception as e:
        if os.path.exists(out_path):
            os.remove(out_path)
        logger.error(f"备份异常: {e}")
        return {"status": "error", "error": str(e)}

    removed = _cleanup_old_backups(conn["db"])
    return {"status": "ok", "file": out_path, "size": size, "removed": removed}


def _cleanup_old_backups(db_name: str) -> int:
    """保留最近 RETENTION 份，删除更早的备份。返回删除数量。"""
    pattern = os.path.join(BACKUP_DIR, f"backup_{db_name}_*.sql.gz")
    files = sorted(glob.glob(pattern))  # 文件名时间戳保证字典序==时间序
    if len(files) <= RETENTION:
        return 0
    to_remove = files[: len(files) - RETENTION]
    for f in to_remove:
        try:
            os.remove(f)
            logger.info(f"清理过期备份: {f}")
        except Exception as e:
            logger.warning(f"清理备份失败 {f}: {e}")
    return len(to_remove)
