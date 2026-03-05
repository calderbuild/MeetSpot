"""数据库引擎与会话管理。

优先使用 DATABASE_URL 环境变量（Supabase PostgreSQL 等），
未配置时回退到本地 SQLite。
"""

import os
from pathlib import Path
from typing import Any, AsyncGenerator
from uuid import uuid4

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool


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


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_pgbouncer_transaction_mode(url: str) -> bool:
    """检测当前连接串是否走 pgbouncer transaction mode。"""
    if not url.startswith("postgresql+asyncpg://"):
        return False

    # 显式开关优先：可在 Render / 本地强制启用或关闭。
    env_flag = os.getenv("PGBOUNCER_TRANSACTION_MODE")
    if env_flag is not None:
        return _is_truthy(env_flag)

    parsed = make_url(url)
    host = (parsed.host or "").lower()
    query = {k.lower(): str(v).lower() for k, v in parsed.query.items()}
    return (
        "pooler.supabase.com" in host
        or query.get("pgbouncer") in {"1", "true", "yes", "on"}
        or query.get("pool_mode") == "transaction"
    )


def _force_asyncpg_prepared_cache_disabled(url: str) -> str:
    """把 SQLAlchemy asyncpg 的 prepared_statement_cache_size 强制设为 0。"""
    parsed = make_url(url)
    return parsed.update_query_dict({"prepared_statement_cache_size": "0"}).render_as_string(
        hide_password=False
    )


def _next_prepared_statement_name() -> str:
    return f"__asyncpg_{uuid4().hex}__"


DATABASE_URL = _resolve_database_url()
USING_PGBOUNCER = _is_pgbouncer_transaction_mode(DATABASE_URL)
if USING_PGBOUNCER:
    # URL 参数是 SQLAlchemy asyncpg 官方支持写法，防止参数未被透传。
    DATABASE_URL = _force_asyncpg_prepared_cache_disabled(DATABASE_URL)

# 创建异步引擎与会话工厂
_engine_kwargs: dict[str, Any] = {"echo": False, "future": True}
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs["pool_pre_ping"] = True
    if USING_PGBOUNCER:
        # pgbouncer(transaction mode) 下 prepared statement 名字会冲突，
        # 需要三件事：禁用缓存、动态名称、禁用应用内连接池（交给 pgbouncer）。
        _engine_kwargs["poolclass"] = NullPool
        _engine_kwargs["connect_args"] = {
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
            "prepared_statement_name_func": _next_prepared_statement_name,
        }
    else:
        _engine_kwargs["pool_size"] = 5
        _engine_kwargs["max_overflow"] = 10
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
