"""
TripCraft Backend Application

FastAPI 异步后端服务，使用 PostgreSQL 持久化。
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.services.cache import cache_service
from app.services.database import db_service
from app.services.logging import RequestTimer, get_logger, set_request_id, setup_logging
from app.services.persistence import PersistenceService
from app.services.rag import TravelRagService
from app.services.seed_data import seed_rag_data

logger = get_logger("tripcraft")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio as _asyncio
    settings = get_settings()

    setup_logging(settings)
    logger.info("Application starting", app_env=settings.app_env)

    # 初始化数据库（persistence 自带完整引擎+建表，不再重复 db_service.initialize）
    await db_service.connect()
    persistence = PersistenceService(settings)
    await persistence.initialize(settings)
    logger.info("Database + persistence initialized")

    # 连接 Redis（非阻塞，失败不影响启动）
    await cache_service.connect()
    logger.info("Cache connected", available=cache_service.available)

    # RAG 初始化改为后台任务，不阻塞启动
    async def _init_rag():
        if settings.dashscope_api_key and settings.qdrant_url:
            try:
                rag_svc = TravelRagService(settings)
                await rag_svc.ensure_collections()
                await seed_rag_data(settings)
                logger.info("RAG service ready (background)")
            except Exception as exc:
                logger.warning("RAG unavailable", error=str(exc))
    _asyncio.ensure_future(_init_rag())

    yield

    await cache_service.close()
    await db_service.close()
    await persistence.close()
    logger.info("Application shutdown")


settings = get_settings()

# 启动前校验 JWT 密钥
if "your-secret-key-change-in-production" in settings.secret_key:
    import sys
    print("❌ FATAL: JWT secret key is still the default placeholder!")
    print("   Please set a strong secret key in your .env file.")
    print("   Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    sys.exit(1)

if len(settings.secret_key) < 32:
    import sys
    print("❌ FATAL: JWT secret key must be at least 32 characters!")
    sys.exit(1)

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.middleware("http")
async def add_request_tracking(request: Request, call_next):
    """添加请求 ID 和计时"""
    request_id = request.headers.get("X-Request-ID")
    set_request_id(request_id)

    with RequestTimer(f"{request.method} {request.url.path}", logger):
        response = await call_next(request)

    response.headers["X-Request-ID"] = set_request_id()
    return response


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "TripCraft", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """增强健康检查（含组件状态）"""
    from datetime import datetime, timezone

    cache_stats = await cache_service.get_stats()
    db_health = await db_service.health_check()

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "components": {
            "api": "up",
            "cache": "up" if cache_stats["available"] else "down",
            "database": db_health["status"],
        },
        "cache_stats": cache_stats,
    }
