"""版本信息端点 — 用于客户现场快速核对部署版本和构建身份"""
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

_BOOT_TS = datetime.now(timezone.utc).isoformat()


def _read_version() -> str:
    try:
        path = Path(__file__).resolve().parents[2] / "VERSION"
        return path.read_text(encoding="utf-8").strip() or "unknown"
    except Exception:
        return "unknown"


def _read_git_sha() -> str:
    """优先读 GIT_SHA 环境变量（构建时注入），其次本地 .git，否则 unknown"""
    env_sha = os.getenv("GIT_SHA", "").strip()
    if env_sha:
        return env_sha[:12]
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=2,
        )
        return out.decode().strip() or "unknown"
    except Exception:
        return "unknown"


_VERSION = _read_version()
_GIT_SHA = _read_git_sha()


@router.get("/version")
async def version():
    return {
        "version": _VERSION,
        "git_sha": _GIT_SHA,
        "started_at": _BOOT_TS,
        "env": os.getenv("APP_ENV", "development"),
    }
