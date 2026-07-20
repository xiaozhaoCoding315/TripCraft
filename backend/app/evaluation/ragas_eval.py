"""
TripCraft RAG 生成层评测（基于 RAGAS 框架）

评测维度：
- Faithfulness: 生成答案是否忠实于检索上下文
- Answer Relevance: 生成答案与问题的相关度
- Context Precision: 检索上下文中有多少是真正相关的
- Context Recall: 检索上下文覆盖了多少ground truth信息

依赖：ragas>=0.2.0（运行时动态导入，未安装时优雅降级）
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.logging import get_logger

logger = get_logger(__name__)


def _check_ragas_available() -> bool:
    """检查 ragas 是否已安装"""
    try:
        import ragas  # noqa: F401
        return True
    except ImportError:
        logger.warning(
            "ragas not installed. Generation evaluation skipped. "
            "Install with: pip install ragas>=0.2.0"
        )
        return False


async def evaluate_generation(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
    llm_service: Any = None,
) -> dict[str, float]:
    """RAGAS 生成层评测。

    Args:
        questions: 查询列表
        answers: LLM 生成的答案列表
        contexts: 检索到的上下文文本列表（每条查询对应一组）
        ground_truths: 标准答案列表
        llm_service: LlmService 实例，用于提供 LLM 给 RAGAS

    Returns:
        {"faithfulness": float, "answer_relevancy": float,
         "context_precision": float, "context_recall": float}
        若 ragas 未安装则返回空字典
    """
    if not _check_ragas_available():
        return {}

    if not questions or not answers:
        logger.warning("Empty input for generation evaluation")
        return {}

    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset
    except ImportError as exc:
        logger.warning(f"RAGAS import failed: {exc}")
        return {}

    # 准备 LLM
    try:
        from ragas.llms import LangchainLLMWrapper
        if llm_service and hasattr(llm_service, "chat_model"):
            llm = LangchainLLMWrapper(llm_service.chat_model())
        else:
            logger.warning("No LLM service provided for RAGAS, skipping generation eval")
            return {}
    except ImportError:
        logger.warning("LangchainLLMWrapper not available in ragas")
        return {}

    # 构建数据集
    data_dict: dict[str, list[str]] = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
    }
    if ground_truths:
        data_dict["ground_truth"] = ground_truths

    dataset = Dataset.from_dict(data_dict)

    # 执行评测
    metrics_to_evaluate = [faithfulness, answer_relevancy, context_precision, context_recall]

    try:
        result = evaluate(
            dataset,
            metrics=metrics_to_evaluate,
            llm=llm,
        )
        df = result.to_pandas()
        mean_scores = df.mean(numeric_only=True).to_dict()

        # 标准化 key 名称
        normalized: dict[str, float] = {}
        for k, v in mean_scores.items():
            key = k.lower().replace(" ", "_")
            try:
                normalized[key] = float(v)
            except (ValueError, TypeError):
                continue

        return normalized

    except Exception as exc:
        logger.warning(f"RAGAS evaluation failed: {exc}")
        return {}


def format_generation_report(scores: dict[str, float]) -> str:
    """格式化生成评测结果"""
    if not scores:
        return "生成评测未执行（ragas 未安装或执行失败）"

    lines = ["生成层评测结果:"]
    for metric, score in scores.items():
        lines.append(f"  {metric}: {score:.4f}")
    return "\n".join(lines)
