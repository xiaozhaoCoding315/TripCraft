"""
TripCraft Hybrid RAG — Pure Function Library

无 I/O 的纯函数模块，提供：
- Markdown 清洗
- 实体抽取（POI、时间、价格、城市）
- RRF (Reciprocal Rank Fusion) 融合算法
- chunk_id 生成器（与 Qdrant 侧完全一致）
- 滑动窗口分块

被 rag.py、preprocess.py、test_hybrid_rag.py 共同依赖。
"""

from __future__ import annotations

import re
from uuid import uuid5, NAMESPACE_URL

from app.services.logging import get_logger

logger = get_logger(__name__)

# 类型别名
Reco = tuple[str, float, dict]  # (chunk_id, score, payload)


# ---------------------------------------------------------------------------
# Chunk ID — 与 rag.py._ingest 的 Qdrant point_id 推导函数完全一致
# ---------------------------------------------------------------------------

def chunk_id(collection: str, city: str, source_key: str, index: int) -> str:
    """生成全局唯一的 chunk ID（与 Qdrant 侧 point_id 相同算法）。

    双索引使用此函数保证 dense/sparse 去重对齐。
    """
    return str(uuid5(NAMESPACE_URL, f"{collection}:{city}:{source_key}:{index}"))


# ---------------------------------------------------------------------------
# RRF 融合
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    ranked_lists: list[list[Reco]],
    k: int = 60,
    limit: int = 6,
) -> list[dict]:
    """多路排序结果 RRF 融合。

    RRF 公式: score(d) = Σ_i 1/(k + rank_i(d))
    同一 doc 出现在多路中会获得累加权重（自动去重 + boost）。

    Args:
        ranked_lists: 多个已排序的结果列表，每个元素为 (chunk_id, score, payload)
        k: RRF 阻尼系数，标准默认 60
        limit: 最终返回条数上限

    Returns:
        融合后的结果列表，每个元素包含 score, text, city, source, tags, entities, _rrf_id
    """
    fused: dict[str, tuple[float, dict]] = {}

    for ranked in ranked_lists:
        if not ranked:
            continue
        for rank, (cid, _orig_score, payload) in enumerate(ranked, start=1):
            entry = fused.setdefault(cid, (0.0, payload))
            fused[cid] = (entry[0] + 1.0 / (k + rank), payload)

    # 按 RRF 分数降序
    ordered = sorted(fused.items(), key=lambda kv: kv[1][0], reverse=True)

    results: list[dict] = []
    for cid, (rrf_score, payload) in ordered[:limit]:
        results.append({
            "score": round(rrf_score, 6),
            "text": payload.get("text", ""),
            "city": payload.get("city", ""),
            "source": payload.get("source", ""),
            "tags": payload.get("tags", []),
            "entities": payload.get("entities", {}),
            "title": payload.get("title"),
            "_rrf_id": cid,
        })

    return results


# ---------------------------------------------------------------------------
# Markdown 清洗
# ---------------------------------------------------------------------------

# 编译一次复用
_RE_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_RE_INLINE_CODE = re.compile(r"`([^`]*)`")
_RE_IMAGE = re.compile(r"!\[([^\]]*)\]\([^\)]+\)")
_RE_LINK = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_HEADERS = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_RE_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_RE_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_RE_STRIKETHROUGH = re.compile(r"~~([^~]+)~~")
_RE_BLOCKQUOTE = re.compile(r"^\s*>\s*", re.MULTILINE)
_RE_HR = re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE)
_RE_TABLE = re.compile(r"\|")
_RE_EXTRA_WHITESPACE = re.compile(r"[ \t]+")
_RE_MULTI_NEWLINES = re.compile(r"\n{3,}")


def clean_markdown(text: str) -> str:
    """清洗 Markdown 语法，返回纯文本。

    处理：代码块、行内代码、图片、链接、HTML 标签、标题、
    加粗、斜体、删除线、引用、表格、水平线、多余空白。
    """
    if not text:
        return ""

    # 顺序很重要：先移除块级结构
    cleaned = _RE_CODE_BLOCK.sub("", text)
    cleaned = _RE_INLINE_CODE.sub(r"\1", cleaned)
    cleaned = _RE_IMAGE.sub(r"\1", cleaned)
    cleaned = _RE_LINK.sub(r"\1", cleaned)
    cleaned = _RE_HTML_TAG.sub("", cleaned)
    cleaned = _RE_HEADERS.sub(r"\1", cleaned)
    cleaned = _RE_BLOCKQUOTE.sub("", cleaned)
    cleaned = _RE_HR.sub("", cleaned)
    cleaned = _RE_TABLE.sub("", cleaned)
    cleaned = _RE_STRIKETHROUGH.sub(r"\1", cleaned)
    cleaned = _RE_BOLD.sub(r"\1", cleaned)
    cleaned = _RE_ITALIC.sub(r"\1", cleaned)

    # 压缩空白
    cleaned = _RE_EXTRA_WHITESPACE.sub(" ", cleaned)
    cleaned = _RE_MULTI_NEWLINES.sub("\n\n", cleaned)

    return cleaned.strip()


# ---------------------------------------------------------------------------
# 实体抽取
# ---------------------------------------------------------------------------

# 已知中文城市名（用于实体识别扩展）
_KNOWN_CITIES: set[str] = {
    "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "西安",
    "南京", "苏州", "天津", "长沙", "郑州", "青岛", "大连", "厦门", "昆明",
    "三亚", "丽江", "桂林", "大理", "张家界", "黄山", "泰山", "拉萨", "哈尔滨",
}

_RE_QUOTED_NAME = re.compile(r"《([^》]{2,20})》")
_RE_BRACKET_NAME = re.compile(r"(?:【|\[)([^】\]]{2,20})(?:】|\])")
_RE_TIME_1 = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")             # 09:00, 14:30
_RE_TIME_2 = re.compile(r"([上中下午早晚里间]*\s*\d{1,2}\s*点(?:\d{1,2}分)?)")  # 下午3点
_RE_PRICE = re.compile(r"(\d+)\s*(?:元|块|RMB|rmb|人民币)")            # 100元
_RE_HOURS = re.compile(r"(\d+)\s*(?:小时|h|H)")                       # 2小时


def extract_entities(text: str, city_hints: list[str] | None = None) -> dict[str, list[str]]:
    """轻量级正则实体抽取。

    无 NER 模型依赖，基于模式匹配提取：
    - pois: 引号/括号中的名称（POI、地标候选）
    - times: 时间表达（09:00、下午3点）
    - prices: 价格表达（100元）
    - cities: 已知城市名匹配
    - hours: 时长表达（2小时）

    Args:
        text: 已清洗的纯文本
        city_hints: 额外的城市提示词（用于提升召回）

    Returns:
        {"pois": [...], "times": [], "prices": [], "cities": [], "hours": []}
    """
    if not text:
        return {"pois": [], "times": [], "prices": [], "cities": [], "hours": []}

    # POI 提取
    pois: set[str] = set()
    for m in _RE_QUOTED_NAME.finditer(text):
        name = m.group(1).strip()
        if 2 <= len(name) <= 20:
            pois.add(name)
    for m in _RE_BRACKET_NAME.finditer(text):
        name = m.group(1).strip()
        if 2 <= len(name) <= 20:
            pois.add(name)

    # 时间提取
    times: list[str] = []
    for m in _RE_TIME_1.finditer(text):
        times.append(f"{m.group(1)}:{m.group(2)}")
    for m in _RE_TIME_2.finditer(text):
        times.append(m.group(1).strip())

    # 价格提取
    prices: list[str] = []
    for m in _RE_PRICE.finditer(text):
        prices.append(f"{m.group(1)}元")

    # 时长提取
    hours: list[str] = []
    for m in _RE_HOURS.finditer(text):
        hours.append(f"{m.group(1)}小时")

    # 城市匹配
    cities: set[str] = set()
    known = _KNOWN_CITIES | set(city_hints or [])
    for city in known:
        if city in text:
            cities.add(city)

    return {
        "pois": sorted(pois),
        "times": times,
        "prices": prices,
        "cities": sorted(cities),
        "hours": hours,
    }


# ---------------------------------------------------------------------------
# 滑动窗口分块
# ---------------------------------------------------------------------------

def sliding_window_chunk(
    text: str,
    max_chars: int = 700,
    overlap: int = 80,
) -> list[str]:
    """滑动窗口分块。

    - 先压缩连续空白
    - 按 max_chars 切割，相邻块间保留 overlap 字符重叠
    - 文本长度 ≤ max_chars 时返回单元素列表

    Args:
        text: 已清洗的纯文本
        max_chars: 每块最大字符数
        overlap: 相邻块间重叠字符数

    Returns:
        chunk 列表
    """
    if not text:
        return []

    # 压缩空白但保留段落分隔
    clean = " ".join(text.split())

    if len(clean) <= max_chars:
        return [clean]

    chunks: list[str] = []
    start = 0
    text_len = len(clean)

    while start < text_len:
        end = min(start + max_chars, text_len)
        chunks.append(clean[start:end])
        if end == text_len:
            break
        # 下一段起始 = 当前结束 - overlap（避免重复过多）
        start = max(0, end - overlap)

    return chunks


# ---------------------------------------------------------------------------
# 调试辅助
# ---------------------------------------------------------------------------

def describe_fusion_input(lists: list[list[Reco]]) -> dict:
    """生成融合输入的摘要（用于日志/调试）。"""
    return {
        "num_lists": len(lists),
        "list_sizes": [len(lst) for lst in lists],
        "total_candidates": sum(len(lst) for lst in lists),
    }
