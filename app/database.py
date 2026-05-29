"""异步SQLAlchemy引擎和会话管理"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

# 用 NullPool 避免在 Celery + asyncio.run() 多次调用时
# SQLAlchemy/asyncpg 连接绑定到已关闭的事件循环
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI依赖注入用的数据库会话"""
    async with async_session() as session:
        yield session
