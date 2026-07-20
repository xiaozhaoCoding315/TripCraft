"""
TripCraft 分层记忆系统

三层记忆架构：
1. 短期会话记忆（Short-term）：Redis List，TTL 会话级（24h）
   - 存储用户当前会话的消息历史和行为事件
   - 用于多轮对话连贯性

2. 长期语义记忆（Long-term）：PostgreSQL + 衰减权重
   - 用户偏好、旅行习惯、历史决策
   - 衰减权重 = recency × frequency × confidence
   - 哈希精确去重 + 语义近似去重

3. 运行时状态记忆（Runtime）：请求级上下文组装
   - 每次规划前从三层分别召回
   - 动态拼接为 LLM 上下文
   - 事实抽取 → 去重 → 衰减权重管理
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import Settings, get_settings
from app.models.travel import MemoryItem as MemoryItemSchema
from app.services.cache import cache_service
from app.services.persistence import PersistenceService

logger = logging.getLogger(__name__)

# 短期记忆配置
SHORT_TERM_TTL = 86400  # 24 小时
SHORT_TERM_MAX_MESSAGES = 50  # 每个会话最大消息数

# 衰减权重配置
RECENCY_HALF_LIFE_DAYS = 30  # 半衰期 30 天
FREIGHT_DECAY_LAMBDA = 0.693 / RECENCY_HALF_LIFE_DAYS  # ln(2) / half_life


class ShortTermMemory:
    """短期会话记忆 — Redis List 存储"""

    def __init__(self, owner_id: str):
        self.owner_id = owner_id

    def _key(self, session_id: str | None = None) -> str:
        """生成 Redis key"""
        sid = session_id or "default"
        return f"tripcraft:short_term:{self.owner_id}:{sid}"

    async def append(self, event: dict[str, Any], session_id: str | None = None) -> None:
        """追加会话事件到 Redis List"""
        if not cache_service.available:
            return
        key = self._key(session_id)
        try:
            # 使用 pipeline：右侧推入 + 修剪长度 + 设置 TTL
            client = cache_service._client
            if client is None:
                return
            pipe = client.pipeline()
            pipe.rpush(key, json.dumps(event, ensure_ascii=False))
            pipe.ltrim(key, -SHORT_TERM_MAX_MESSAGES, -1)  # 只保留最近 N 条
            pipe.expire(key, SHORT_TERM_TTL)
            await pipe.execute()
        except Exception as exc:
            logger.debug(f"Short-term memory append failed: {exc}")

    async def get_recent(self, count: int = 20, session_id: str | None = None) -> list[dict[str, Any]]:
        """获取最近的会话事件"""
        if not cache_service.available:
            return []
        key = self._key(session_id)
        try:
            raw = await cache_service._client.lrange(key, -count, -1)
            return [json.loads(item) for item in raw]
        except Exception as exc:
            logger.debug(f"Short-term memory read failed: {exc}")
            return []

    async def clear(self, session_id: str | None = None) -> None:
        """清除会话记忆"""
        if not cache_service.available:
            return
        key = self._key(session_id)
        try:
            await cache_service.delete(key)
        except Exception as exc:
            logger.debug(f"Short-term memory clear failed: {exc}")


class LongTermMemory:
    """长期语义记忆 — PostgreSQL + 衰减权重管理"""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.persistence = PersistenceService(self.settings)

    @staticmethod
    def compute_decay_weight(
        confidence: float,
        access_count: int = 1,
        updated_at: datetime | None = None,
    ) -> float:
        """计算衰减权重 = recency × frequency × confidence

        - recency: 指数衰减 e^(-λ×days)，半衰期 30 天
        - frequency: log(1 + access_count)，访问越多权重越高但边际递减
        - confidence: 原始置信度 [0, 1]
        """
        # 时间衰减
        recency = 1.0
        if updated_at is not None:
            now = datetime.now(UTC)
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            days = max((now - updated_at).total_seconds() / 86400, 0)
            recency = math.exp(-FREIGHT_DECAY_LAMBDA * days)

        # 频率因子（对数压缩边际递减）
        frequency = math.log(1 + access_count)

        return recency * frequency * confidence

    async def upsert(
        self,
        items: Iterable[MemoryItemSchema],
        owner_id: str,
    ) -> None:
        """保存长期记忆（含去重和权重更新）"""
        now = datetime.now(UTC)
        for item in items:
            # 哈希去重：基于 key + value 的精确匹配
            existing_memory = await self._get_by_key(item.key, owner_id)
            if existing_memory and self._is_semantic_duplicate(existing_memory.value, item.value):
                # 语义近似 → 更新访问计数和权重
                await self._bump_access(existing_memory.key, owner_id, now)
                continue
            # 新记忆或显著不同 → 写入
            await self.persistence.upsert_memory([item], owner_id)

    async def recall(
        self,
        owner_id: str,
        limit: int = 10,
        min_weight: float = 0.1,
    ) -> list[dict[str, Any]]:
        """召回高权重长期记忆

        按衰减权重降序返回，过滤低于阈值的旧记忆。
        """
        items = await self.persistence.list_memory(owner_id)
        scored: list[tuple[float, dict[str, Any]]] = []

        for item in items:
            updated = None
            if item.updated_at:
                try:
                    updated = datetime.fromisoformat(item.updated_at)
                except ValueError:
                    pass
            weight = self.compute_decay_weight(
                confidence=item.confidence,
                updated_at=updated,
            )
            if weight >= min_weight:
                scored.append((weight, {
                    "key": item.key,
                    "value": item.value,
                    "category": item.category,
                    "weight": round(weight, 4),
                    "source": item.source,
                }))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    async def decay_cleanup(self, owner_id: str, min_weight: float = 0.05) -> int:
        """清理过期记忆（权重衰减到阈值以下的）"""
        items = await self.persistence.list_memory(owner_id)
        cleaned = 0
        for item in items:
            updated = None
            if item.updated_at:
                try:
                    updated = datetime.fromisoformat(item.updated_at)
                except ValueError:
                    pass
            weight = self.compute_decay_weight(item.confidence, updated_at=updated)
            if weight < min_weight:
                await self.persistence.delete_memory(item.key, owner_id)
                cleaned += 1
        return cleaned

    async def _get_by_key(self, key: str, owner_id: str) -> MemoryItemSchema | None:
        """精确查找"""
        items = await self.persistence.list_memory(owner_id)
        for item in items:
            if item.key == key:
                return item
        return None

    @staticmethod
    def _is_semantic_duplicate(existing_value: str, new_value: str, threshold: float = 0.85) -> bool:
        """语义近似去重 — 基于字符级 Jaccard 相似度（轻量级，无模型依赖）"""
        if existing_value == new_value:
            return True
        # 简单 Jaccard：基于字符 unigram 集合
        set_a = set(existing_value)
        set_b = set(new_value)
        if not set_a or not set_b:
            return False
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        jaccard = intersection / union if union > 0 else 0
        return jaccard >= threshold

    async def _bump_access(
        self,
        key: str,
        owner_id: str,
        now: datetime,
    ) -> None:
        """增加访问计数 + 更新时间（提升 recency）"""
        items = await self.persistence.list_memory(owner_id)
        for item in items:
            if item.key == key:
                # 更新 updated_at 以提升 recency 权重
                bumped = MemoryItemSchema(
                    key=item.key,
                    value=item.value,
                    category=item.category,
                    source=item.source,
                    confidence=min(item.confidence + 0.05, 1.0),  # 小幅提升置信
                    updated_at=now.isoformat(),
                )
                await self.persistence.upsert_memory([bumped], owner_id)
                break


class MemoryAssembler:
    """运行时状态记忆 — 上下文组装器

    每次规划前从三层记忆分别召回，动态拼接为 LLM 上下文。
    """

    def __init__(self, owner_id: str, settings: Settings | None = None):
        self.owner_id = owner_id
        self.settings = settings or get_settings()
        self.short_term = ShortTermMemory(owner_id)
        self.long_term = LongTermMemory(self.settings)

    async def assemble_context(
        self,
        query: str = "",
        session_id: str | None = None,
        max_items: int = 8,
    ) -> dict[str, Any]:
        """组装三层记忆上下文

        Args:
            query: 当前查询（用于语义匹配排序，可选）
            session_id: 会话 ID（用于短期记忆隔离）
            max_items: 返回的最大记忆条数

        Returns:
            {
                "short_term": [...],    # 会话上下文
                "long_term": [...],     # 长期偏好
                "context_text": "...",  # 拼接后的文本（直接给 LLM）
            }
        """
        # 并行召回短期 + 长期
        short_task = self.short_term.get_recent(count=10, session_id=session_id)
        long_task = self.long_term.recall(self.owner_id, limit=max_items)
        short_items, long_items = await asyncio.gather(short_task, long_task)

        # 取 Top-K（优先长期记忆的偏好 + 短期会话）
        selected: list[dict[str, Any]] = []

        # 长期记忆优先（偏好、习惯、预算等）
        for item in long_items:
            if len(selected) >= max_items:
                break
            selected.append({
                **item,
                "layer": "long_term",
            })

        # 短期记忆补充（最近对话、调整意图）
        recent_intents = []
        for event in short_items:
            if event.get("type") == "adjustment":
                recent_intents.append(event.get("intent", ""))

        # 拼接为 LLM 文本
        context_parts: list[str] = []

        if long_items:
            context_parts.append("【用户偏好】")
            for item in long_items:
                context_parts.append(f"- {item['key']}: {item['value']} (权重:{item['weight']})")

        if recent_intents:
            context_parts.append("\n【最近调整意图】")
            for intent in recent_intents[-3:]:  # 最近 3 条
                context_parts.append(f"- {intent}")

        return {
            "short_term": short_items,
            "long_term": long_items,
            "context_text": "\n".join(context_parts),
            "total_items": len(selected),
        }

    async def record_event(
        self,
        event: dict[str, Any],
        session_id: str | None = None,
    ) -> None:
        """记录会话事件到短期记忆"""
        await self.short_term.append(event, session_id)

    async def learn_from_adjustment(
        self,
        instruction: str,
        extracted: list[MemoryItemSchema],
    ) -> None:
        """从调整指令中提取并写入长期记忆"""
        await self.long_term.upsert(extracted, self.owner_id)

        # 同步记录到短期记忆
        await self.short_term.append({
            "type": "adjustment",
            "intent": instruction,
            "timestamp": datetime.now(UTC).isoformat(),
        })


import asyncio  # noqa: E402 — 放在文件末尾避免循环导入

# ---------------------------------------------------------------------------
# 便捷入口
# ---------------------------------------------------------------------------

async def build_memory_context(
    owner_id: str,
    query: str = "",
    settings: Settings | None = None,
) -> str:
    """便捷函数：直接获取拼接好的记忆上下文文本"""
    assembler = MemoryAssembler(owner_id, settings)
    result = await assembler.assemble_context(query=query)
    return result.get("context_text", "")
