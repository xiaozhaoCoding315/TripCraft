"""
TripCraft RAG 检索层评测指标

纯 Python 实现，零外部依赖。
支持指标：
- Recall@k (k=3, 5, 10)
- MRR (Mean Reciprocal Rank)
- NDCG@k (Normalized Discounted Cumulative Gain)
- HitRate@k (任意相关文档命中)
"""

from __future__ import annotations

import math
from typing import Any


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Recall@k = |relevant ∩ retrieved[:k]| / min(|relevant|, k)

    对于 negative 查询（relevant 为空），定义为 0.0（无目标可召回）。
    """
    if not relevant or k <= 0:
        return 0.0
    retrieved_set = set(retrieved[:k])
    return len(relevant & retrieved_set) / min(len(relevant), k)


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    """MRR = 1 / rank_of_first_relevant

    第一个相关文档的排名倒数。无相关文档命中返回 0.0。
    """
    if not relevant:
        return 0.0
    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def _dcg_at_k(relevances: list[float], k: int) -> float:
    """内部辅助：计算 DCG@k"""
    score = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        score += rel / math.log2(i + 1)
    return score


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """NDCG@k = DCG@k / IDCG@k

    使用二元相关性（相关=1，不相关=0）。
    无相关文档时返回 0.0。
    """
    if not relevant or k <= 0:
        return 0.0

    # 构建相关性列表
    relevances = [1.0 if doc in relevant else 0.0 for doc in retrieved[:k]]

    dcg = _dcg_at_k(relevances, k)

    # 理想排序：所有相关文档排在前面
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = _dcg_at_k(ideal_relevances, k)

    return dcg / idcg if idcg > 0 else 0.0


def hit_rate_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """HitRate@k = 1.0 if any relevant in top-k else 0.0

    衡量 top-k 中是否包含至少一个相关文档。
    """
    if not relevant or k <= 0:
        return 0.0
    return 1.0 if any(doc in relevant for doc in retrieved[:k]) else 0.0


def compute_all_metrics(
    retrieved: list[str],
    relevant: set[str],
    ks: list[int] | None = None,
) -> dict[str, float]:
    """一次性计算所有指标。

    Args:
        retrieved: 检索结果列表（按排名排序），元素为 doc_id
        relevant: 相关文档 ID 集合
        ks: 需要计算 Recall/NDCG/HitRate 的 k 值列表，默认 [3, 5, 10]

    Returns:
        {
            "Recall@3": float, "Recall@5": float, "Recall@10": float,
            "MRR": float,
            "NDCG@3": float, "NDCG@5": float, "NDCG@10": float,
            "HitRate@3": float, "HitRate@5": float, "HitRate@10": float,
        }
    """
    if ks is None:
        ks = [3, 5, 10]

    metrics: dict[str, float] = {}

    for k in ks:
        metrics[f"Recall@{k}"] = recall_at_k(retrieved, relevant, k)
        metrics[f"NDCG@{k}"] = ndcg_at_k(retrieved, relevant, k)
        metrics[f"HitRate@{k}"] = hit_rate_at_k(retrieved, relevant, k)

    metrics["MRR"] = mrr(retrieved, relevant)

    return metrics


# ---------------------------------------------------------------------------
# 多查询聚合
# ---------------------------------------------------------------------------

def aggregate_metrics(
    per_query_metrics: list[dict[str, float]],
) -> dict[str, float]:
    """对多查询的指标结果取平均。

    Args:
        per_query_metrics: 每条查询的指标字典列表

    Returns:
        平均后的指标字典
    """
    if not per_query_metrics:
        return {}

    keys = per_query_metrics[0].keys()
    n = len(per_query_metrics)

    aggregated: dict[str, float] = {}
    for key in keys:
        values = [m[key] for m in per_query_metrics if key in m]
        aggregated[key] = sum(values) / len(values) if values else 0.0

    return aggregated


def format_metrics_table(
    results: dict[str, dict[str, float]],
    metric_keys: list[str] | None = None,
) -> str:
    """格式化多方案指标对比为表格字符串。

    Args:
        results: {方案名: {指标名: 值}}
        metric_keys: 要显示的指标顺序，None 则自动提取

    Returns:
        表格字符串
    """
    if not results:
        return "No results"

    if metric_keys is None:
        metric_keys = []
        for metrics in results.values():
            for k in metrics:
                if k not in metric_keys:
                    metric_keys.append(k)

    # 排序：Recall → MRR → NDCG → HitRate
    def sort_key(k: str) -> tuple[int, int, str]:
        if k.startswith("Recall"):
            prefix_order = 0
        elif k.startswith("MRR"):
            prefix_order = 1
        elif k.startswith("NDCG"):
            prefix_order = 2
        elif k.startswith("HitRate"):
            prefix_order = 3
        else:
            prefix_order = 4
        # Extract number from k (e.g., "Recall@5" → 5)
        num = int(k.split("@")[1]) if "@" in k else 0
        return (prefix_order, num, k)

    metric_keys = sorted(metric_keys, key=sort_key)

    # Header
    col_width = 14
    name_width = 18
    lines = []
    header = f"{'方案':<{name_width}}" + "".join(f"{k:>{col_width}}" for k in metric_keys)
    lines.append(header)
    lines.append("-" * len(header))

    for method_name, metrics in results.items():
        row = f"{method_name:<{name_width}}"
        for k in metric_keys:
            val = metrics.get(k, 0.0)
            row += f"{val:>{col_width}.4f}"
        lines.append(row)

    return "\n".join(lines)
