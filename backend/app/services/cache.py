"""
TripCraft Redis Cache Service

Redis 缓存服务，支持优雅降级。
Redis 不可用时记录警告（修复 P1#16）。
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis 缓存服务"""

    # TTL 常量（秒）
    TTL_SHORT = 300      # 5 分钟
    TTL_MEDIUM = 3600    # 1 小时
    TTL_LONG = 86400     # 24 小时
    TTL_WEEK = 604800    # 1 周

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: Any | None = None
        self.available = False

    async def connect(self) -> None:
        """连接 Redis"""
        if not self.settings.redis_enabled:
            logger.info("Redis caching disabled")
            return
        try:
            from redis.asyncio import Redis

            self._client = Redis.from_url(self.settings.redis_url, decode_responses=True)
            await self._client.ping()
            self.available = True
            logger.info("Redis cache connected successfully")
        except Exception as exc:
            self._client = None
            self.available = False
            # P1#16: Redis 不可用时记录警告（而非静默降级）
            logger.warning(
                "Redis cache unavailable, performance may degrade",
                extra={"error": str(exc), "redis_url": self.settings.redis_url.split("@")[-1]},
            )

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            await self._client.aclose()

    def _make_key(self, namespace: str, *args: str) -> str:
        """生成缓存键"""
        key_parts = ":".join(args)
        return f"tripcraft:{namespace}:{key_parts}"

    def _hash_key(self, key: str) -> str:
        """哈希长键"""
        if len(key) < 100:
            return key
        return hashlib.md5(key.encode()).hexdigest()

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """存储 JSON 值"""
        if not self.available or not self._client:
            return
        try:
            await self._client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds)
        except Exception as exc:
            logger.debug(f"Cache set failed: {exc}")
            self.available = False

    async def get_json(self, key: str) -> Any | None:
        """获取 JSON 值"""
        if not self.available or not self._client:
            return None
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.debug(f"Cache get failed: {exc}")
            self.available = False
            return None

    async def delete(self, key: str) -> None:
        """删除缓存键"""
        if not self.available or not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception as exc:
            logger.debug(f"Cache delete failed: {exc}")

    async def delete_pattern(self, pattern: str) -> None:
        """删除匹配模式的所有键"""
        if not self.available or not self._client:
            return
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._client.delete(*keys)
                logger.info(f"Deleted {len(keys)} cache keys matching {pattern}")
        except Exception as exc:
            logger.debug(f"Cache pattern delete failed: {exc}")

    # 便捷方法

    async def cache_amap_response(self, query: str, response: Any, ttl: int = TTL_MEDIUM) -> None:
        """缓存 Amap API 响应"""
        key = self._make_key("amap", self._hash_key(query))
        await self.set_json(key, response, ttl)

    async def get_cached_amap_response(self, query: str) -> Any | None:
        """获取缓存的 Amap API 响应"""
        key = self._make_key("amap", self._hash_key(query))
        return await self.get_json(key)

    async def cache_rag_results(self, query: str, results: Any, ttl: int = TTL_LONG) -> None:
        """缓存 RAG 搜索结果"""
        key = self._make_key("rag", self._hash_key(query))
        await self.set_json(key, results, ttl)

    async def get_cached_rag_results(self, query: str) -> Any | None:
        """获取缓存的 RAG 搜索结果"""
        key = self._make_key("rag", self._hash_key(query))
        return await self.get_json(key)

    async def invalidate_plan_cache(self, plan_id: str) -> None:
        """使计划相关缓存失效"""
        await self.delete_pattern(f"tripcraft:plan:{plan_id}:*")

    async def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        if not self.available or not self._client:
            return {"available": False}
        try:
            info = await self._client.info("memory")
            return {
                "available": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception:
            return {"available": False}


cache_service = CacheService()
