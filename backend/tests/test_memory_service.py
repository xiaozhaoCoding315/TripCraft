"""
TripCraft 分层记忆系统测试
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest

from app.models.travel import MemoryItem as MemoryItemSchema
from app.services.memory_service import (
    LongTermMemory,
    ShortTermMemory,
    MemoryAssembler,
    RECENCY_HALF_LIFE_DAYS,
    FREIGHT_DECAY_LAMBDA,
    build_memory_context,
)


# ==========================================================================
# 1. 衰减权重计算
# ==========================================================================

class TestDecayWeight:
    def test_fresh_memory_full_weight(self):
        """刚更新的记忆 recency ≈ 1, weight = 1 * log(2) * 1 ≈ 0.693"""
        weight = LongTermMemory.compute_decay_weight(
            confidence=1.0,
            updated_at=datetime.now(UTC),
        )
        # recency=1.0, frequency=log(1+1)=log(2)≈0.693, confidence=1.0
        assert abs(weight - 0.693) < 0.01

    def test_old_memory_decays(self):
        """30 天前的记忆 recency ≈ 0.5"""
        old_time = datetime.now(UTC) - timedelta(days=30)
        weight = LongTermMemory.compute_decay_weight(
            confidence=1.0,
            updated_at=old_time,
        )
        # recency = e^(-λ×30) = e^(-ln2) = 0.5, freq = log(1) = 0
        # Actually freq = log(1+1) = log(2) ≈ 0.693
        assert 0.3 < weight < 0.7

    def test_very_old_memory_near_zero(self):
        """90 天前的记忆接近 0"""
        old_time = datetime.now(UTC) - timedelta(days=90)
        weight = LongTermMemory.compute_decay_weight(
            confidence=1.0,
            updated_at=old_time,
        )
        assert weight < 0.2

    def test_confidence_scales_weight(self):
        """置信度越低权重越低"""
        now = datetime.now(UTC)
        w_high = LongTermMemory.compute_decay_weight(confidence=1.0, updated_at=now)
        w_low = LongTermMemory.compute_decay_weight(confidence=0.3, updated_at=now)
        assert w_high > w_low

    def test_half_life_constant(self):
        """半衰期常数正确: λ = ln(2) / 30"""
        assert abs(FREIGHT_DECAY_LAMBDA - 0.693 / 30) < 0.001

    def test_recency_formula(self):
        """recency = e^(-λ×days)"""
        days = 10
        expected_recency = math.exp(-FREIGHT_DECAY_LAMBDA * days)
        old_time = datetime.now(UTC) - timedelta(days=days)
        # With confidence=1, access_count=1: weight = recency * log(2) * 1
        weight = LongTermMemory.compute_decay_weight(
            confidence=1.0, access_count=1, updated_at=old_time
        )
        expected = expected_recency * math.log(2)
        assert abs(weight - expected) < 0.01


# ==========================================================================
# 2. 语义去重
# ==========================================================================

class TestSemanticDedup:
    def test_exact_match(self):
        assert LongTermMemory._is_semantic_duplicate("完全相同", "完全相同") is True

    def test_completely_different(self):
        assert LongTermMemory._is_semantic_duplicate("北京烤鸭", "杭州西湖") is False

    def test_similar_text(self):
        """高度相似的文本应判定为重复"""
        a = "偏好慢节奏旅行，每天安排1-2个景点"
        b = "偏好慢节奏旅行每天安排1-2个景点"  # 仅少了标点
        assert LongTermMemory._is_semantic_duplicate(a, b) is True

    def test_empty_string(self):
        assert LongTermMemory._is_semantic_duplicate("", "有内容") is False

    def test_threshold_boundary(self):
        """刚好在阈值边界：Jaccard 高于阈值 → 重复"""
        a = "北京烤鸭便宜坊"
        b = "北京烤鸭四季民福"
        # set_a={北,京,烤,鸭,便,宜,坊} = 7
        # set_b={北,京,烤,鸭,四,季,民,福} = 8
        # intersection={北,京,烤,鸭} = 4
        # union={北,京,烤,鸭,便,宜,坊,四,季,民,福} = 11
        # jaccard = 4/11 ≈ 0.36 → False
        result = LongTermMemory._is_semantic_duplicate(a, b, threshold=0.85)
        assert result is False

    def test_high_similarity(self):
        """高度相似的字符串 → 重复"""
        a = "偏好慢节奏旅行每天安排1到2个景点并增加休息时间"
        b = "偏好慢节奏旅行每天安排1到2个景点并增加休息"  # 只差最后2字
        result = LongTermMemory._is_semantic_duplicate(a, b, threshold=0.85)
        assert result is True


# ==========================================================================
# 3. 短期记忆（Redis 依赖，降级测试）
# ==========================================================================

class TestShortTermMemory:
    def test_key_format(self):
        mem = ShortTermMemory("user_123")
        key = mem._key("session_abc")
        assert key == "tripcraft:short_term:user_123:session_abc"

    def test_default_session(self):
        mem = ShortTermMemory("user_123")
        key = mem._key()
        assert "default" in key

    @pytest.mark.asyncio
    async def test_append_when_redis_unavailable(self):
        """Redis 不可用时不报错"""
        mem = ShortTermMemory("user_123")
        # cache_service.available 默认为 False（无 Redis 连接）
        await mem.append({"type": "test", "data": "hello"})

    @pytest.mark.asyncio
    async def test_get_recent_when_redis_unavailable(self):
        """Redis 不可用返回空列表"""
        mem = ShortTermMemory("user_123")
        result = await mem.get_recent()
        assert result == []


# ==========================================================================
# 4. 上下文组装
# ==========================================================================

class TestMemoryAssembler:
    @pytest.mark.asyncio
    async def test_assemble_returns_structure(self):
        """组装结果包含必要字段"""
        assembler = MemoryAssembler("user_test")
        result = await assembler.assemble_context()
        assert "short_term" in result
        assert "long_term" in result
        assert "context_text" in result
        assert "total_items" in result

    @pytest.mark.asyncio
    async def test_assemble_with_empty_memory(self):
        """无记忆时返回空上下文"""
        assembler = MemoryAssembler("new_user_no_memory")
        result = await assembler.assemble_context()
        assert isinstance(result["context_text"], str)

    @pytest.mark.asyncio
    async def test_assemble_respects_max_items(self):
        """max_items 限制生效"""
        assembler = MemoryAssembler("user_test")
        result = await assembler.assemble_context(max_items=3)
        assert result["total_items"] <= 3


# ==========================================================================
# 5. 便捷函数
# ==========================================================================

class TestBuildMemoryContext:
    @pytest.mark.asyncio
    async def test_returns_string(self):
        result = await build_memory_context("user_test")
        assert isinstance(result, str)
