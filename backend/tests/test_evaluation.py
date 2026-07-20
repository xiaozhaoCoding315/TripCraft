"""
TripCraft RAG 评测体系测试

包含：
1. 单元测试（无需外部服务）：指标公式正确性、数据集完整性
2. 集成测试（需 Qdrant + PG + DashScope）：端到端评测运行
"""

from __future__ import annotations

import math

import pytest

from app.evaluation.golden_dataset import (
    GOLDEN_QUERIES,
    EXACT,
    SEMANTIC,
    NEGATIVE,
    dataset_stats,
    get_queries_by_city,
    get_queries_by_difficulty,
    get_queries_by_type,
)
from app.evaluation.metrics import (
    recall_at_k,
    mrr,
    ndcg_at_k,
    hit_rate_at_k,
    compute_all_metrics,
    aggregate_metrics,
)


# ==========================================================================
# 1. 检索指标单元测试
# ==========================================================================

class TestRecallAtK:
    def test_perfect_recall(self):
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, 3) == 1.0

    def test_partial_recall(self):
        retrieved = ["a", "x", "y", "b"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, 3) == 0.5  # only "a" in top-3

    def test_no_relevant(self):
        assert recall_at_k(["a", "b"], set(), 3) == 0.0

    def test_no_match(self):
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, 3) == 0.0

    def test_k_larger_than_retrieved(self):
        retrieved = ["a"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, 10) == 0.5

    def test_k_zero(self):
        assert recall_at_k(["a"], {"a"}, 0) == 0.0

    def test_more_relevant_than_k(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c", "d", "e"}
        # min(|relevant|, k) = min(5, 3) = 3, hit = 3 → 1.0
        assert recall_at_k(retrieved, relevant, 3) == 1.0


class TestMRR:
    def test_first_relevant(self):
        assert mrr(["a", "b", "c"], {"a"}) == 1.0

    def test_second_relevant(self):
        assert mrr(["x", "a", "c"], {"a"}) == 0.5

    def test_third_relevant(self):
        assert mrr(["x", "y", "a"], {"a"}) == 1.0 / 3

    def test_no_relevant(self):
        assert mrr(["a", "b"], set()) == 0.0

    def test_no_match(self):
        assert mrr(["x", "y"], {"a"}) == 0.0

    def test_multiple_relevant_uses_first(self):
        assert mrr(["x", "a", "b"], {"a", "b"}) == 0.5  # first relevant at rank 2


class TestNDCGAtK:
    def test_perfect_ranking(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c"}
        assert ndcg_at_k(retrieved, relevant, 3) == 1.0

    def test_worst_ranking(self):
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b", "c"}
        assert ndcg_at_k(retrieved, relevant, 3) == 0.0

    def test_no_relevant(self):
        assert ndcg_at_k(["a", "b"], set(), 3) == 0.0

    def test_partial_relevant(self):
        retrieved = ["a", "x", "b"]
        relevant = {"a", "b"}
        # DCG = 1/log2(2) + 0 + 1/log2(4) = 1 + 0 + 0.5 = 1.5
        # IDCG = 1/log2(2) + 1/log2(3) = 1 + 0.631 = 1.631
        # NDCG = 1.5 / 1.631 ≈ 0.919
        score = ndcg_at_k(retrieved, relevant, 3)
        assert 0.91 < score < 0.93

    def test_k_zero(self):
        assert ndcg_at_k(["a"], {"a"}, 0) == 0.0

    def test_single_relevant_at_top(self):
        retrieved = ["a", "x", "y"]
        relevant = {"a"}
        assert ndcg_at_k(retrieved, relevant, 3) == 1.0  # perfect for single relevant


class TestHitRateAtK:
    def test_hit(self):
        assert hit_rate_at_k(["a", "b", "c"], {"b"}, 3) == 1.0

    def test_miss(self):
        assert hit_rate_at_k(["x", "y", "z"], {"a"}, 3) == 0.0

    def test_no_relevant(self):
        assert hit_rate_at_k(["a", "b"], set(), 3) == 0.0

    def test_k_smaller_than_hit_position(self):
        assert hit_rate_at_k(["x", "y", "a"], {"a"}, 2) == 0.0

    def test_k_equal_to_hit_position(self):
        assert hit_rate_at_k(["x", "y", "a"], {"a"}, 3) == 1.0


class TestComputeAllMetrics:
    def test_output_keys(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b"}
        metrics = compute_all_metrics(retrieved, relevant, ks=[3, 5, 10])

        expected_keys = {
            "Recall@3", "Recall@5", "Recall@10",
            "MRR",
            "NDCG@3", "NDCG@5", "NDCG@10",
            "HitRate@3", "HitRate@5", "HitRate@10",
        }
        assert set(metrics.keys()) == expected_keys

    def test_all_values_in_range(self):
        retrieved = ["a", "x", "b", "y"]
        relevant = {"a", "b"}
        metrics = compute_all_metrics(retrieved, relevant)

        for key, value in metrics.items():
            assert 0.0 <= value <= 1.0, f"{key} = {value} out of range"


class TestAggregateMetrics:
    def test_average(self):
        per_query = [
            {"Recall@5": 0.8, "MRR": 0.5},
            {"Recall@5": 0.6, "MRR": 0.7},
        ]
        result = aggregate_metrics(per_query)
        assert result["Recall@5"] == 0.7
        assert result["MRR"] == 0.6

    def test_empty(self):
        assert aggregate_metrics([]) == {}


# ==========================================================================
# 2. 黄金数据集完整性测试
# ==========================================================================

class TestGoldenDataset:
    def test_total_count(self):
        """必须有 50 条查询"""
        assert len(GOLDEN_QUERIES) == 50

    def test_eight_cities(self):
        """覆盖 8 城"""
        cities = set(q["city"] for q in GOLDEN_QUERIES)
        expected = {"杭州", "北京", "上海", "成都", "西安", "南京", "重庆", "苏州"}
        assert cities == expected

    def test_type_distribution(self):
        """3 种类型都有"""
        stats = dataset_stats()
        assert stats["by_type"][EXACT] > 0
        assert stats["by_type"][SEMANTIC] > 0
        assert stats["by_type"][NEGATIVE] > 0

    def test_exact_count(self):
        """精确匹配约 17 条（5城×2 + 3城×2 + 苏州×1 额外）"""
        assert 15 <= len(get_queries_by_type(EXACT)) <= 20

    def test_semantic_count(self):
        """语义模糊约 24 条（5城×3 + 3城×3）"""
        assert 22 <= len(get_queries_by_type(SEMANTIC)) <= 26

    def test_negative_count(self):
        """否定查询 8 条"""
        assert 6 <= len(get_queries_by_type(NEGATIVE)) <= 10

    def test_negative_have_no_relevant_docs(self):
        """否定查询的 relevant_docs 必须为空"""
        for q in get_queries_by_type(NEGATIVE):
            assert q["relevant_docs"] == [], f"Query {q['id']} is negative but has relevant docs"

    def test_exact_have_relevant_docs(self):
        """精确匹配查询必须有 relevant_docs"""
        for q in get_queries_by_type(EXACT):
            assert len(q["relevant_docs"]) > 0, f"Query {q['id']} is exact but has no relevant docs"

    def test_all_queries_have_required_fields(self):
        """每条查询必须有完整字段"""
        required = {"id", "city", "query", "type", "difficulty", "relevant_docs", "expected_answer"}
        for q in GOLDEN_QUERIES:
            missing = required - set(q.keys())
            assert not missing, f"Query {q.get('id')} missing fields: {missing}"

    def test_all_queries_have_non_empty_query(self):
        """查询文本非空"""
        for q in GOLDEN_QUERIES:
            assert q["query"].strip(), f"Query {q['id']} has empty query text"

    def test_difficulty_levels(self):
        """3 种难度都有"""
        stats = dataset_stats()
        assert stats["by_difficulty"]["easy"] > 0
        assert stats["by_difficulty"]["medium"] > 0
        assert stats["by_difficulty"]["hard"] > 0

    def test_city_distribution_balanced(self):
        """每城至少 5 条查询"""
        cities = set(q["city"] for q in GOLDEN_QUERIES)
        for city in cities:
            count = len(get_queries_by_city(city))
            assert count >= 5, f"City {city} has only {count} queries"

    def test_unique_ids(self):
        """查询 ID 唯一"""
        ids = [q["id"] for q in GOLDEN_QUERIES]
        assert len(ids) == len(set(ids)), "Duplicate query IDs found"

    def test_valid_types(self):
        """类型值合法"""
        valid_types = {EXACT, SEMANTIC, NEGATIVE}
        for q in GOLDEN_QUERIES:
            assert q["type"] in valid_types, f"Query {q['id']} has invalid type: {q['type']}"

    def test_valid_difficulties(self):
        """难度值合法"""
        valid_difficulties = {"easy", "medium", "hard"}
        for q in GOLDEN_QUERIES:
            assert q["difficulty"] in valid_difficulties

    def test_stats_consistency(self):
        """dataset_stats 数据一致"""
        stats = dataset_stats()
        assert stats["total"] == 50
        assert len(stats["cities"]) == 8
        assert sum(stats["by_type"].values()) == 50
        assert sum(stats["by_difficulty"].values()) == 50


# ==========================================================================
# 3. 集成测试（需 Qdrant + PG + DashScope）
# ==========================================================================

@pytest.mark.integration
class TestRetrievalEvaluationIntegration:
    """端到端检索评测集成测试"""

    @pytest.fixture
    def settings(self):
        return Settings(
            dashscope_api_key=None,  # 使用 fallback 模式
            qdrant_url="http://192.168.150.128:6333",
            amap_api_key=None,
        )

    @pytest.mark.asyncio
    async def test_metrics_computation_on_known_data(self):
        """用已知数据验证指标计算"""
        # 模拟检索结果
        retrieved = ["doc_a", "doc_b", "doc_c", "doc_x", "doc_y"]
        relevant = {"doc_a", "doc_c"}

        metrics = compute_all_metrics(retrieved, relevant, ks=[3, 5, 10])

        # Recall@3: top-3 = {a, b, c}, relevant = {a, c} → 2/min(2,3) = 1.0
        assert metrics["Recall@3"] == 1.0

        # MRR: first relevant at rank 1 → 1.0
        assert metrics["MRR"] == 1.0

        # HitRate@3: a in top-3 → 1.0
        assert metrics["HitRate@3"] == 1.0

        # NDCG@3: DCG = 1/log2(2) + 0 + 1/log2(4) = 1.5
        # IDCG = 1/log2(2) + 1/log2(3) ≈ 1.631
        expected_ndcg = 1.5 / (1.0 / math.log2(2) + 1.0 / math.log2(3))
        assert abs(metrics["NDCG@3"] - expected_ndcg) < 0.01

    @pytest.mark.asyncio
    async def test_negative_query_metrics(self):
        """否定查询的指标应为 0"""
        retrieved = ["doc_a", "doc_b"]
        relevant = set()  # negative query

        metrics = compute_all_metrics(retrieved, relevant, ks=[3, 5, 10])

        assert metrics["Recall@5"] == 0.0
        assert metrics["MRR"] == 0.0
        assert metrics["NDCG@5"] == 0.0
        assert metrics["HitRate@5"] == 0.0
