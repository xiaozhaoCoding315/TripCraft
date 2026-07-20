"""
TripCraft RAG 评测编排器

完整评测流程：
1. 加载 8 城种子数据 → 双写 (Qdrant + rag_chunks)
2. 加载 50 条黄金查询
3. 对每条查询运行 3 种检索方案（dense / sparse / hybrid+RRF）
4. 计算检索指标（Recall/MRR/NDCG/HitRate）
5. (可选) RAGAS 生成评测
6. 输出对比报告
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from app.core.config import Settings, get_settings
from app.evaluation.golden_dataset import (
    GOLDEN_QUERIES,
    EXACT,
    SEMANTIC,
    NEGATIVE,
    get_queries_by_type,
)
from app.evaluation.metrics import (
    compute_all_metrics,
    aggregate_metrics,
    format_metrics_table,
)
from app.evaluation.ragas_eval import evaluate_generation, format_generation_report
from app.services.persistence import PersistenceService
from app.services.rag import TravelRagService
from app.services.seed_data import SeedDataService

logger = logging.getLogger(__name__)


class RagEvaluator:
    """RAG 评测编排器"""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.rag = TravelRagService(self.settings)
        self.persistence = PersistenceService(self.settings)
        self.results: dict[str, list[dict[str, float]]] = {}

    async def setup(self) -> None:
        """初始化：建表 + 种子数据"""
        await self.persistence.initialize(self.settings)
        seed = SeedDataService(self.settings)
        await seed.seed_if_empty()
        logger.info("Evaluation environment ready")

    async def teardown(self) -> None:
        """清理资源"""
        await self.persistence.close()

    # ------------------------------------------------------------------
    # 检索方案
    # ------------------------------------------------------------------

    async def _retrieve_dense(self, city: str, query: str, limit: int = 10) -> list[str]:
        """纯稠密向量检索"""
        try:
            recos = await self.rag._dense_search(city, query, limit)
            return [cid for cid, _, _ in recos]
        except Exception as exc:
            logger.debug(f"Dense search failed for '{query}': {exc}")
            return []

    async def _retrieve_sparse(self, city: str, query: str, limit: int = 10) -> list[str]:
        """纯 BM25 稀疏检索"""
        try:
            recos = await self.rag._sparse_search(city, query, limit)
            return [cid for cid, _, _ in recos]
        except Exception as exc:
            logger.debug(f"Sparse search failed for '{query}': {exc}")
            return []

    async def _retrieve_hybrid(self, city: str, query: str, limit: int = 10) -> list[str]:
        """混合检索 + RRF 融合"""
        try:
            results = await self.rag.search_notes(city, query, limit)
            return [r.get("_rrf_id", "") for r in results if r.get("_rrf_id")]
        except Exception as exc:
            logger.debug(f"Hybrid search failed for '{query}': {exc}")
            return []

    # ------------------------------------------------------------------
    # 单查询评测
    # ------------------------------------------------------------------

    async def evaluate_query(
        self,
        query_info: dict[str, Any],
        limit: int = 10,
    ) -> dict[str, dict[str, float]]:
        """对单条查询运行 3 种方案并计算指标"""
        city = query_info["city"]
        query = query_info["query"]
        relevant = set(query_info.get("relevant_docs", []))

        # 运行 3 种检索方案
        dense_docs = await self._retrieve_dense(city, query, limit)
        sparse_docs = await self._retrieve_sparse(city, query, limit)
        hybrid_docs = await self._retrieve_hybrid(city, query, limit)

        # 计算指标
        return {
            "Dense-only": compute_all_metrics(dense_docs, relevant, ks=[3, 5, 10]),
            "BM25-only": compute_all_metrics(sparse_docs, relevant, ks=[3, 5, 10]),
            "Hybrid+RRF": compute_all_metrics(hybrid_docs, relevant, ks=[3, 5, 10]),
        }

    # ------------------------------------------------------------------
    # 全量评测
    # ------------------------------------------------------------------

    async def run_retrieval_evaluation(
        self,
        queries: list[dict[str, Any]] | None = None,
        limit: int = 10,
    ) -> dict[str, dict[str, float]]:
        """运行全量检索评测"""
        if queries is None:
            queries = GOLDEN_QUERIES

        logger.info(f"Running retrieval evaluation on {len(queries)} queries...")

        # 收集每种方案的所有查询指标
        all_metrics: dict[str, list[dict[str, float]]] = {
            "Dense-only": [],
            "BM25-only": [],
            "Hybrid+RRF": [],
        }

        for i, q in enumerate(queries, start=1):
            try:
                result = await self.evaluate_query(q, limit=limit)
                for method, metrics in result.items():
                    all_metrics[method].append(metrics)
            except Exception as exc:
                logger.warning(f"Query {q.get('id', i)} failed: {exc}")

        # 聚合
        aggregated: dict[str, dict[str, float]] = {}
        for method, metrics_list in all_metrics.items():
            aggregated[method] = aggregate_metrics(metrics_list)

        self.results = aggregated
        return aggregated

    # ------------------------------------------------------------------
    # 报告生成
    # ------------------------------------------------------------------

    def generate_report(
        self,
        results: dict[str, dict[str, float]] | None = None,
    ) -> str:
        """生成评测报告"""
        if results is None:
            results = self.results

        if not results:
            return "No evaluation results available"

        lines = []
        lines.append("=" * 72)
        lines.append("  TripCraft RAG 全链路评测报告")
        lines.append("=" * 72)
        lines.append("")

        # 数据集信息
        lines.append(f"  黄金查询数: {len(GOLDEN_QUERIES)}")
        lines.append(f"  城市覆盖: 8 城")
        lines.append(f"  查询类型: 精确({len(get_queries_by_type(EXACT))}) + "
                     f"语义({len(get_queries_by_type(SEMANTIC))}) + "
                     f"否定({len(get_queries_by_type(NEGATIVE))})")
        lines.append("")

        # 检索指标对比表
        lines.append("  ── 检索层指标对比 ──")
        lines.append("")
        table = format_metrics_table(results)
        for row in table.split("\n"):
            lines.append(f"  {row}")
        lines.append("")

        # 结论
        if "Hybrid+RRF" in results and "Dense-only" in results:
            hybrid_ndcg = results["Hybrid+RRF"].get("NDCG@10", 0)
            dense_ndcg = results["Dense-only"].get("NDCG@10", 0)
            if dense_ndcg > 0:
                improvement = (hybrid_ndcg - dense_ndcg) / dense_ndcg * 100
                lines.append(f"  结论: Hybrid+RRF NDCG@10 = {hybrid_ndcg:.4f}")
                lines.append(f"        较纯向量(Dense)提升 {improvement:+.1f}%")
            else:
                lines.append(f"  结论: Hybrid+RRF NDCG@10 = {hybrid_ndcg:.4f}")

            if hybrid_ndcg >= 0.80:
                lines.append("        ✅ 达到 0.80 基准线")
            else:
                lines.append("        ⚠️ 未达到 0.80 基准线")

        lines.append("")
        lines.append("=" * 72)

        return "\n".join(lines)


async def main() -> None:
    """命令行入口"""
    settings = get_settings()
    evaluator = RagEvaluator(settings)

    try:
        await evaluator.setup()
        results = await evaluator.run_retrieval_evaluation()
        report = evaluator.generate_report(results)
        print(report)
    finally:
        await evaluator.teardown()


if __name__ == "__main__":
    asyncio.run(main())
