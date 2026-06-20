"""
TripCraft PostgreSQL Database Service

提供异步 PostgreSQL 数据库连接管理。
与 PersistenceService 配合使用。
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """PostgreSQL 数据库服务"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self.async_session = None

    async def connect(self) -> None:
        """连接 PostgreSQL 数据库"""
        try:
            db_url = (
                f"postgresql+asyncpg://{self.settings.postgres_user}:{self.settings.postgres_password}"
                f"@{self.settings.postgres_host}:{self.settings.postgres_port}/{self.settings.postgres_db}"
            )

            self.engine = create_async_engine(
                db_url,
                echo=self.settings.app_env == "development",
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
            )

            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # 测试连接
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            logger.info(
                "PostgreSQL database connected",
                extra={
                    "host": self.settings.postgres_host,
                    "port": self.settings.postgres_port,
                    "database": self.settings.postgres_db,
                },
            )

        except Exception as exc:
            logger.error(f"Failed to connect to PostgreSQL: {exc}")
            raise

    async def close(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            logger.info("PostgreSQL database connection closed")

    async def initialize(self) -> None:
        """创建表（如果不存在）"""
        from app.models.persistence_models import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables initialized")

    async def health_check(self) -> dict[str, Any]:
        """检查数据库健康状态"""
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            return {"status": "healthy", "database": "postgresql"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}


# 全局单例
db_service = DatabaseService(Settings())
