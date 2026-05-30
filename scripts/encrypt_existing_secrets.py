#!/usr/bin/env python3
"""
把 lark_configs 表中的明文 app_secret / encrypt_key / verification_token
加密为 enc:v1:<token> 格式，便于现有部署一键升级到加密存储。

使用方法（在容器内执行）：
    docker compose exec fastapi python /app/scripts/encrypt_existing_secrets.py

要求：
- 已设置 .env 中的 APP_ENCRYPTION_KEY
- 多次执行无副作用（已加密的字段会跳过）
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from sqlalchemy import select
from app.database import async_session
from app.models import LarkConfig
from app.security.crypto import encrypt_field, ENC_PREFIX, is_encryption_enabled


async def main():
    if not is_encryption_enabled():
        print("❌ APP_ENCRYPTION_KEY 未配置，先设置后再执行")
        print("   生成命令: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        return

    fields = ("app_secret", "encrypt_key", "verification_token")
    stats = {"checked": 0, "encrypted": 0, "skipped_already_encrypted": 0, "skipped_empty": 0}

    async with async_session() as session:
        rows = (await session.execute(select(LarkConfig))).scalars().all()
        for cfg in rows:
            stats["checked"] += 1
            changed = False
            for field in fields:
                val = getattr(cfg, field, "") or ""
                if not val:
                    stats["skipped_empty"] += 1
                    continue
                if val.startswith(ENC_PREFIX):
                    stats["skipped_already_encrypted"] += 1
                    continue
                encrypted = encrypt_field(val)
                setattr(cfg, field, encrypted)
                changed = True
                stats["encrypted"] += 1
            if changed:
                print(f"  ✓ 已加密配置: {cfg.name} (id={cfg.id})")

        await session.commit()

    print()
    print("迁移完成:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
