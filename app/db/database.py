"""数据库引擎与会话管理。

优先使用 DATABASE_URL 环境变量（Supabase PostgreSQL 等），
未配置时回退到本地 SQLite。
"""

import os
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base


def _resolve_database_url() -> str:
    """解析数据库连接串，自动处理 PostgreSQL 协议前缀。"""
    url = os.getenv("DATABASE_URL", "")
    if url:
        # Supabase / Heroku 给的是 postgres://，SQLAlchemy 需要 postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    # 回退到本地 SQLite
    project_root = Path(__file__).resolve().parent.parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    return f"sqlite+aiosqlite:///{(data_dir / 'meetspot.db').as_posix()}"


DATABASE_URL = _resolve_database_url()

# 创建异步引擎与会话工厂
_engine_kwargs = {"echo": False, "future": True}
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10
    # pgbouncer (transaction mode) 不支持 prepared statements，
    # 必须禁用 asyncpg 的 statement cache 否则启动即报错
    _engine_kwargs["connect_args"] = {"statement_cache_size": 0}
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# 统一的ORM基类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供数据库会话并确保正确关闭。"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """在启动时创建数据库表。"""
    # 延迟导入以避免循环依赖
    from app import models  # noqa: F401  确保所有模型已注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

