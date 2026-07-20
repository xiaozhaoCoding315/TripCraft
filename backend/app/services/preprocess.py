"""
TripCraft RAG 预处理管线

编排 Markdown 清洗 → 滑动窗口分块 → 实体抽取 → enriched chunk 输出。
被 TravelRagService._ingest 调用，输出写入双索引 (Qdrant + rag_chunks 表)。
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.services.hybrid_rag import (
    chunk_id,
    clean_markdown,
    extract_entities,
    sliding_window_chunk,
)
from app.services.logging import get_logger

logger = get_logger(__name__)


def prepare_chunks(
    raw_text: str,
    base_meta: dict[str, Any],
    max_chars: int = 700,
    overlap: int = 80,
) -> list[dict[str, Any]]:
    """预处理管线：清洗 → 分块 → 实体抽取 → enriched chunk 列表。

    每条输出 chunk 包含写入双索引所需的全部字段：
    - id: uuid5 全局唯一 ID (与 Qdrant point_id 对齐)
    - collection, city, source, tags, metadata: 来自 base_meta
    - text: 分块后的纯文本
    - title: 来自 base_meta
    - chunk_index: 在文档内的分块序号
    - doc_key: 文档级稳定标识
    - entities: 抽取的结构化实体

    Args:
        raw_text: 原始文本（可能含 Markdown）
        base_meta: 基础元数据，需包含 collection, city；可选 title, source, tags, metadata
        max_chars: 滑动窗口大小
        overlap: 滑动窗口重叠字符数

    Returns:
        enriched chunk 字典列表，可直接写入 rag_chunks 表
    """
    collection = base_meta.get("collection", "travel_notes")
    city = base_meta.get("city", "")
    title = base_meta.get("title")
    source = base_meta.get("source", "manual_ingest")
    tags: list[str] = list(base_meta.get("tags", []))
    metadata: dict[str, Any] = dict(base_meta.get("metadata", {}))

    # 生成 doc_key（文档级稳定 ID）
    source_key = base_meta.get("doc_key") or base_meta.get("id") or (
        hashlib.sha1(raw_text.encode("utf-8")).hexdigest()
    )

    # Step 1: Markdown 清洗
    cleaned = clean_markdown(raw_text)

    # Step 2: 滑动窗口分块
    text_chunks = sliding_window_chunk(cleaned, max_chars=max_chars, overlap=overlap)

    if not text_chunks:
        logger.warning(f"prepare_chunks: empty result after chunking (city={city}, source={source})")
        return []

    # Step 3: 对首块做实体抽取（作为文档级实体标签）
    city_hints = [city] if city else []
    doc_entities = extract_entities(cleaned[:2000], city_hints=city_hints)

    # 从实体标签中提取 POI 追加到 tags
    extracted_pois = doc_entities.get("pois", [])
    enriched_tags = list(set(tags + extracted_pois)) if extracted_pois else tags

    # Step 4: 输出 enriched chunks
    rows: list[dict[str, Any]] = []
    for idx, text_chunk in enumerate(text_chunks):
        cid = chunk_id(collection=collection, city=city, source_key=source_key, index=idx)
        rows.append({
            "id": cid,
            "collection": collection,
            "city": city,
            "title": title,
            "text": text_chunk,
            "tags": enriched_tags,
            "source": source,
            "metadata": {**metadata, "chunk_index": idx},
            "chunk_index": idx,
            "doc_key": source_key,
            "entities": doc_entities,
        })

    return rows
