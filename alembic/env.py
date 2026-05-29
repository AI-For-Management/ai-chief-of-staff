"""Alembic迁移环境配置"""
import os
import sys
from logging.config import fileConfig

# 确保项目根目录在sys.path中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 优先使用环境变量中的数据库URL
db_url = os.getenv("DATABASE_URL_SYNC")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# 导入所有模型让Alembic能检测到
from app.database import Base
from app.models import LarkConfig, LarkAsset, DocumentVersion, AgentSession  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
