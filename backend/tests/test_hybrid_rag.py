"""
TripCraft Hybrid RAG 单元测试 + 集成测试

测试覆盖：
1. clean_markdown — 各种 Markdown 语法剥离
2. extract_entities — POI/时间/价格/城市 正则抽取
3. reciprocal_rank_fusion — 融合算法核心行为
4. sliding_window_chunk — 分块逻辑
5. chunk_id — 与 Qdrant 侧 uuid5 对齐
6. prepare_chunks — 预处理管线输出
"""

from __future__ import annotations

import pytest
from uuid import uuid5, NAMESPACE_URL

from app.services.hybrid_rag import (
    Reco,
    chunk_id,
    clean_markdown,
    extract_entities,
    reciprocal_rank_fusion,
    sliding_window_chunk,
)
from app.services.preprocess import prepare_chunks


# ==========================================================================
# 1. clean_markdown
# ==========================================================================

class TestCleanMarkdown:
    def test_code_block_removed(self):
        md = "```python\nprint('hello')\n```\nSome text"
        result = clean_markdown(md)
        assert "print" not in result
        assert "Some text" in result

    def test_inline_code(self):
        md = "Use the `search_notes` function to query"
        result = clean_markdown(md)
        assert "search_notes" in result
        assert "`" not in result

    def test_image_stripped(self):
        md = "![alt text](http://example.com/img.png) caption"
        result = clean_markdown(md)
        assert "alt text" in result
        assert "http" not in result
        assert "!" not in result

    def test_link_to_text(self):
        md = "Visit [Google](https://google.com) for more"
        result = clean_markdown(md)
        assert "Google" in result
        assert "https" not in result
        assert "(" not in result

    def test_headers(self):
        md = "# Title\n## Subtitle\nContent"
        result = clean_markdown(md)
        assert "Title" in result
        assert "Subtitle" in result
        assert "#" not in result

    def test_bold_italic(self):
        md = "**bold** and *italic* text"
        result = clean_markdown(md)
        assert "bold" in result
        assert "italic" in result
        assert "*" not in result

    def test_strikethrough(self):
        md = "~~deleted~~ active"
        result = clean_markdown(md)
        assert "deleted" in result
        assert "~~" not in result

    def test_html_tags(self):
        md = "<div>content</div> <br/> text"
        result = clean_markdown(md)
        assert "content" in result
        assert "<div>" not in result

    def test_blockquote(self):
        md = "> quoted text\nnormal text"
        result = clean_markdown(md)
        assert "quoted text" in result
        assert "normal text" in result

    def test_horizontal_rule(self):
        md = "above\n---\nbelow"
        result = clean_markdown(md)
        assert "above" in result
        assert "below" in result

    def test_table_stripped(self):
        md = "| col1 | col2 |\n|------|------|\n| a | b |"
        result = clean_markdown(md)
        assert "|" not in result
        assert "col1" in result

    def test_whitespace_compressed(self):
        md = "  too    many   spaces  "
        result = clean_markdown(md)
        assert "  " not in result

    def test_empty_input(self):
        assert clean_markdown("") == ""
        assert clean_markdown(None) == ""

    def test_complex_document(self):
        md = """# 杭州旅行攻略

## Day 1 — 西湖
上午去**西湖**游玩，`建议`乘坐游船。

> 西湖是世界文化遗产，建议清晨或傍晚避开人流

推荐餐厅：[楼外楼](https://example.com) — 西湖醋鱼

![西湖美景](http://img.example.com/xihu.jpg)
"""
        result = clean_markdown(md)
        assert "杭州旅行攻略" in result
        assert "西湖" in result
        assert "楼外楼" in result
        assert "西湖醋鱼" in result
        # 不应有 markdown 符号
        assert "#" not in result
        assert "**" not in result
        assert "`" not in result
        assert "!" not in result
        assert ">" not in result


# ==========================================================================
# 2. extract_entities
# ==========================================================================

class TestExtractEntities:
    def test_quoted_poi(self):
        text = "推荐《西湖》和《灵隐寺》，都是杭州著名景点"
        result = extract_entities(text, city_hints=["杭州"])
        assert "西湖" in result["pois"]
        assert "灵隐寺" in result["pois"]

    def test_bracket_poi(self):
        text = "去【故宫】参观，然后逛【南锣鼓巷】"
        result = extract_entities(text)
        assert "故宫" in result["pois"]
        assert "南锣鼓巷" in result["pois"]

    def test_time_patterns(self):
        text = "上午9:30出发，下午2点到达，耗时约3小时"
        result = extract_entities(text)
        assert "9:30" in result["times"]
        assert any("2点" in t for t in result["times"])
        assert "3小时" in result["hours"]

    def test_price_patterns(self):
        text = "门票120元，午餐花了80元，打车50块"
        result = extract_entities(text)
        assert "120元" in result["prices"]
        assert "80元" in result["prices"]
        assert "50元" in result["prices"]

    def test_city_matching(self):
        text = "从北京出发，先去西安，再到成都"
        result = extract_entities(text)
        assert "北京" in result["cities"]
        assert "西安" in result["cities"]
        assert "成都" in result["cities"]

    def test_city_hints(self):
        text = "三亚的海滩很美"
        result = extract_entities(text, city_hints=["三亚"])
        assert "三亚" in result["cities"]

    def test_empty_input(self):
        result = extract_entities("")
        assert result == {"pois": [], "times": [], "prices": [], "cities": [], "hours": []}

    def test_no_entities(self):
        result = extract_entities("这是一段没有任何实体信息的普通文本")
        assert result["pois"] == []
        assert result["times"] == []
        assert result["prices"] == []

    def test_comprehensive_travel_text(self):
        text = (
            "《故宫博物院》建议游玩半天，门票60元，8:30开门。"
            "从北京站打车约30分钟到达，建议游玩4小时。"
        )
        result = extract_entities(text, city_hints=["北京"])
        assert "故宫博物院" in result["pois"]
        assert "60元" in result["prices"]
        assert "4小时" in result["hours"]
        assert "8:30" in result["times"]
        assert "北京" in result["cities"]


# ==========================================================================
# 3. reciprocal_rank_fusion
# ==========================================================================

class TestReciprocalRankFusion:
    def test_basic_fusion(self):
        list1: list[Reco] = [
            ("a", 0.9, {"text": "A"}),
            ("b", 0.8, {"text": "B"}),
            ("c", 0.7, {"text": "C"}),
        ]
        list2: list[Reco] = [
            ("b", 0.85, {"text": "B"}),
            ("a", 0.75, {"text": "A"}),
            ("d", 0.6, {"text": "D"}),
        ]
        result = reciprocal_rank_fusion([list1, list2], k=60, limit=4)
        # a, b appear in both → should rank higher than c, d
        assert len(result) == 4
        ids = [r["_rrf_id"] for r in result]
        # b is rank2 in list1 (1/62) + rank1 in list2 (1/61) ≈ 0.0325
        # a is rank1 in list1 (1/61) + rank2 in list2 (1/62) ≈ 0.0325
        # b slightly higher due to list2 rank1
        assert ids[0] in ("a", "b")
        assert ids[1] in ("a", "b")
        # c only in list1
        assert ids[2] in ("c", "d")
        assert ids[3] in ("c", "d")

    def test_overlap_gets_higher_score(self):
        shared: list[Reco] = [("shared", 0.5, {"text": "S"})]
        only_a: list[Reco] = [("only_a", 0.9, {"text": "OA"})]
        only_b: list[Reco] = [("only_b", 0.9, {"text": "OB"})]
        # shared appears in two lists, only_a/only_b in one
        result = reciprocal_rank_fusion([shared + only_a, shared + only_b], k=60, limit=3)
        assert result[0]["_rrf_id"] == "shared"  # must be top

    def test_single_list_preserves_order(self):
        lst: list[Reco] = [
            ("x", 0.9, {"text": "X"}),
            ("y", 0.8, {"text": "Y"}),
            ("z", 0.7, {"text": "Z"}),
        ]
        result = reciprocal_rank_fusion([lst], k=60, limit=3)
        assert [r["_rrf_id"] for r in result] == ["x", "y", "z"]

    def test_empty_list_skipped(self):
        lst: list[Reco] = [("a", 0.9, {"text": "A"})]
        result = reciprocal_rank_fusion([lst, []], k=60, limit=1)
        assert len(result) == 1
        assert result[0]["_rrf_id"] == "a"

    def test_all_empty(self):
        result = reciprocal_rank_fusion([[], []], k=60, limit=6)
        assert result == []

    def test_limit_applied(self):
        list1: list[Reco] = [(f"item_{i}", 1.0 - i * 0.01, {"text": str(i)}) for i in range(10)]
        result = reciprocal_rank_fusion([list1], k=60, limit=3)
        assert len(result) == 3

    def test_k_value_dampening(self):
        # With larger k, rank differences are dampened more
        lst: list[Reco] = [("a", 0.9, {}), ("b", 0.1, {})]
        result_small_k = reciprocal_rank_fusion([lst], k=1, limit=2)
        result_large_k = reciprocal_rank_fusion([lst], k=1000, limit=2)
        # With k=1: a=1/2=0.5, b=1/3≈0.33 → gap=0.17
        # With k=1000: a=1/1001≈0.001, b=1/1002≈0.001 → gap≈0
        score_a_small = result_small_k[0]["score"]
        score_b_small = result_small_k[1]["score"]
        score_a_large = result_large_k[0]["score"]
        score_b_large = result_large_k[1]["score"]
        gap_small = score_a_small - score_b_small
        gap_large = score_a_large - score_b_large
        assert gap_small > gap_large  # small k = bigger gap between ranks

    def test_payload_preserved(self):
        payload = {"text": "Hello", "city": "杭州", "source": "test", "tags": ["t1"], "entities": {"pois": ["西湖"]}}
        lst: list[Reco] = [("id1", 0.9, payload)]
        result = reciprocal_rank_fusion([lst], k=60, limit=1)
        assert result[0]["text"] == "Hello"
        assert result[0]["city"] == "杭州"
        assert result[0]["source"] == "test"
        assert result[0]["tags"] == ["t1"]
        assert result[0]["entities"] == {"pois": ["西湖"]}
        assert "_rrf_id" in result[0]

    def test_score_is_float(self):
        lst: list[Reco] = [("a", 0.9, {"text": "A"})]
        result = reciprocal_rank_fusion([lst], k=60, limit=1)
        assert isinstance(result[0]["score"], float)


# ==========================================================================
# 4. sliding_window_chunk
# ==========================================================================

class TestSlidingWindowChunk:
    def test_short_text_single_chunk(self):
        text = "short text"
        chunks = sliding_window_chunk(text, max_chars=700, overlap=80)
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_exact_boundary(self):
        text = "a" * 700
        chunks = sliding_window_chunk(text, max_chars=700, overlap=80)
        assert len(chunks) == 1

    def test_long_text_multiple_chunks(self):
        # 2000 chars should produce multiple chunks
        text = "x" * 2000
        chunks = sliding_window_chunk(text, max_chars=700, overlap=80)
        assert len(chunks) >= 3

    def test_overlap_correctness(self):
        text = "a" * 800
        chunks = sliding_window_chunk(text, max_chars=500, overlap=100)
        # chunk1: [0:500], chunk2 starts at 400 (500-100 overlap)
        assert len(chunks[0]) == 500
        assert chunks[1][:100] == chunks[0][-100:]  # overlap matches

    def test_whitespace_compressed(self):
        text = "word1    word2    word3"
        chunks = sliding_window_chunk(text, max_chars=700, overlap=80)
        assert "    " not in chunks[0]

    def test_empty_input(self):
        assert sliding_window_chunk("") == []
        assert sliding_window_chunk(None) == []

    def test_preserves_content(self):
        # All original words should appear in chunks
        texts = ["杭州", "西湖", "灵隐寺", "雷峰塔", "西溪湿地", "宋城"]
        text = "。".join(texts) + "。" * 1000  # pad to make it long
        chunks = sliding_window_chunk(text, max_chars=50, overlap=10)
        combined = "".join(chunks)
        for t in texts:
            assert t in combined


# ==========================================================================
# 5. chunk_id alignment
# ==========================================================================

class TestChunkId:
    def test_deterministic(self):
        id1 = chunk_id("travel_notes", "杭州", "doc_001", 0)
        id2 = chunk_id("travel_notes", "杭州", "doc_001", 0)
        assert id1 == id2

    def test_matches_uuid5_formula(self):
        expected = str(uuid5(NAMESPACE_URL, "travel_notes:杭州:doc_001:0"))
        actual = chunk_id("travel_notes", "杭州", "doc_001", 0)
        assert actual == expected

    def test_different_inputs_differ(self):
        id1 = chunk_id("travel_notes", "杭州", "doc_001", 0)
        id2 = chunk_id("travel_notes", "杭州", "doc_001", 1)
        id3 = chunk_id("attractions", "杭州", "doc_001", 0)
        id4 = chunk_id("travel_notes", "北京", "doc_001", 0)
        assert len({id1, id2, id3, id4}) == 4

    def test_uuid_format(self):
        cid = chunk_id("travel_notes", "杭州", "key", 0)
        # Standard UUID format: 8-4-4-4-12
        parts = cid.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8


# ==========================================================================
# 6. prepare_chunks
# ==========================================================================

class TestPrepareChunks:
    def test_output_structure(self):
        text = "杭州西湖景区是世界文化遗产，建议游玩3小时。门票免费。"
        meta = {
            "collection": "travel_notes",
            "city": "杭州",
            "title": "西湖攻略",
            "source": "test",
            "tags": ["景点"],
            "metadata": {"author": "test"},
            "id": "doc_001",
        }
        chunks = prepare_chunks(text, base_meta=meta)
        assert len(chunks) >= 1
        chunk = chunks[0]
        assert "id" in chunk
        assert "collection" in chunk
        assert "city" in chunk
        assert "text" in chunk
        assert "tags" in chunk
        assert "entities" in chunk
        assert "doc_key" in chunk

    def test_id_matches_chunk_id_function(self):
        text = "杭州西湖景区是世界文化遗产。建议游玩3小时。"
        meta = {
            "collection": "travel_notes",
            "city": "杭州",
            "title": "西湖",
            "source": "test",
            "tags": [],
            "metadata": {},
            "id": "my_doc_123",
        }
        chunks = prepare_chunks(text, base_meta=meta)
        expected_id = chunk_id("travel_notes", "杭州", "my_doc_123", 0)
        assert chunks[0]["id"] == expected_id

    def test_markdown_cleaned_in_output(self):
        text = "# 杭州攻略\n\n**西湖**很美，`推荐`游玩。"
        meta = {"collection": "travel_notes", "city": "杭州"}
        chunks = prepare_chunks(text, base_meta=meta)
        assert len(chunks) >= 1
        # Markdown symbols should be stripped
        assert "#" not in chunks[0]["text"]
        assert "**" not in chunks[0]["text"]
        assert "`" not in chunks[0]["text"]
        # But content preserved
        assert "杭州攻略" in chunks[0]["text"]
        assert "西湖" in chunks[0]["text"]

    def test_entities_extracted(self):
        text = "推荐《西湖》和《灵隐寺》，门票60元，建议游玩3小时。"
        meta = {"collection": "travel_notes", "city": "杭州"}
        chunks = prepare_chunks(text, base_meta=meta)
        entities = chunks[0]["entities"]
        assert "西湖" in entities["pois"]
        assert "灵隐寺" in entities["pois"]
        assert "60元" in entities["prices"]
        assert "3小时" in entities["hours"]

    def test_pois_added_to_tags(self):
        text = "《西湖》是杭州的著名景点"
        meta = {"collection": "travel_notes", "city": "杭州", "tags": ["原有标签"]}
        chunks = prepare_chunks(text, base_meta=meta)
        tags = chunks[0]["tags"]
        assert "原有标签" in tags
        assert "西湖" in tags

    def test_empty_text(self):
        meta = {"collection": "travel_notes", "city": "杭州"}
        chunks = prepare_chunks("", base_meta=meta)
        assert chunks == []

    def test_long_text_multiple_chunks(self):
        # Generate text longer than 700 chars after whitespace normalization
        base_para = "第{i}段：杭州西湖景区是世界文化遗产，建议游玩3小时，门票免费。湖上有三潭印月、雷峰塔、断桥残雪等十景，每处都值得细品慢游。"
        paragraphs = [base_para.format(i=i) for i in range(25)]
        text = "\n\n".join(paragraphs)
        assert len(" ".join(text.split())) > 700  # verify input is long enough
        meta = {"collection": "travel_notes", "city": "杭州", "id": "long_doc"}
        chunks = prepare_chunks(text, base_meta=meta)
        assert len(chunks) >= 2
        # IDs should be sequential
        for i, chunk in enumerate(chunks):
            expected_id = chunk_id("travel_notes", "杭州", "long_doc", i)
            assert chunk["id"] == expected_id
            assert chunk["chunk_index"] == i

    def test_doc_key_from_id(self):
        text = "杭州旅行攻略"
        meta = {"collection": "travel_notes", "city": "杭州", "id": "my_doc_key"}
        chunks = prepare_chunks(text, base_meta=meta)
        assert chunks[0]["doc_key"] == "my_doc_key"

    def test_doc_key_fallback_to_hash(self):
        text = "杭州旅行攻略 without explicit id"
        meta = {"collection": "travel_notes", "city": "杭州"}
        chunks = prepare_chunks(text, base_meta=meta)
        # Should generate a hash-based doc_key
        assert len(chunks[0]["doc_key"]) == 40  # SHA-1 hex length


# ==========================================================================
# 7. 向后兼容 — search_notes 返回格式验证
# ==========================================================================

class TestBackwardCompatibility:
    """验证 RRF 融合结果格式与原始 search_notes 返回格式兼容。"""

    def test_required_keys_present(self):
        """原始调用方依赖的 key 必须存在。"""
        payload = {
            "text": "杭州西湖攻略",
            "city": "杭州",
            "source": "qdrant:travel_notes",
            "tags": ["景点"],
            "entities": {"pois": ["西湖"]},
        }
        lst: list[Reco] = [("id1", 0.9, payload)]
        result = reciprocal_rank_fusion([lst], k=60, limit=1)

        # 原始 key
        assert "score" in result[0]
        assert "text" in result[0]
        assert "city" in result[0]
        assert "source" in result[0]
        assert "tags" in result[0]
        # 新增 key（非破坏性）
        assert "entities" in result[0]
        assert "_rrf_id" in result[0]

    def test_score_is_truthy(self):
        """调用方可能用 score 做真值判断。"""
        payload = {"text": "test", "city": "杭州", "source": "test", "tags": [], "entities": {}}
        lst: list[Reco] = [("id1", 0.9, payload)]
        result = reciprocal_rank_fusion([lst], k=60, limit=1)
        assert result[0]["score"] > 0

    def test_text_accessible_via_get(self):
        """workflow.py 使用 notes[i].get("text", "") 访问。"""
        payload = {"text": "杭州西湖", "city": "杭州", "source": "test", "tags": [], "entities": {}}
        lst: list[Reco] = [("id1", 0.9, payload)]
        result = reciprocal_rank_fusion([lst], k=60, limit=1)
        assert result[0].get("text", "") == "杭州西湖"
