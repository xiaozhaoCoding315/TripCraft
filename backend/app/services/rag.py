"""
TripCraft Hybrid RAG Service

提供三路召回融合检索：
- Path A: Qdrant 稠密向量检索（cosine similarity）
- Path B: PostgreSQL BM25 稀疏关键词检索（ts_rank_cd）
- Path C: 结构化过滤（城市谓词嵌入 Path B SQL）
- RRF(k=60) 融合三路结果

写入时双索引同步（Qdrant + rag_chunks 表）。
搜索降级链: hybrid → dense-only → sparse-only → fallback_notes。
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any
from uuid import uuid4

import dashscope
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import Settings
from app.models.travel import RagDocument, RagIngestResponse
from app.services.hybrid_rag import (
    Reco,
    chunk_id,
    reciprocal_rank_fusion,
)
from app.services.logging import get_logger
from app.services.persistence import PersistenceService
from app.services.preprocess import prepare_chunks

logger = get_logger(__name__)


class TravelRagService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        self.rrf_k = settings.rrf_k
        self.sparse_limit_multiplier = settings.sparse_limit_multiplier

    @property
    def enabled(self) -> bool:
        return bool(self.settings.dashscope_api_key and self.settings.qdrant_url)

    # ------------------------------------------------------------------
    # 集合管理
    # ------------------------------------------------------------------

    async def ensure_collections(self) -> None:
        for collection in [
            self.settings.qdrant_travel_notes_collection,
            self.settings.qdrant_attractions_collection,
        ]:
            exists = await self.client.collection_exists(collection)
            if not exists:
                await self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=self.settings.qwen_embedding_dimension, distance=Distance.COSINE),
                )

    async def embed(self, text: str) -> list[float]:
        if not self.settings.dashscope_api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")
        dashscope.api_key = self.settings.dashscope_api_key
        response = dashscope.TextEmbedding.call(
            model=self.settings.qwen_embedding_model,
            input=text,
            dimension=self.settings.qwen_embedding_dimension,
        )
        embeddings = response.output.get("embeddings") or []
        if not embeddings:
            raise RuntimeError("DashScope embedding response is empty")
        return embeddings[0]["embedding"]

    # ------------------------------------------------------------------
    # 三路检索入口
    # ------------------------------------------------------------------

    async def search_notes(self, city: str, query: str, limit: int = 6) -> list[dict[str, Any]]:
        """混合检索入口 — 三路召回 + RRF 融合。

        返回格式与原始单路检索完全兼容（score/text/city/source/tags），
        新增 entities 和 _rrf_id 字段（非破坏性扩展）。
        """
        if not self.enabled:
            return self.fallback_notes(city, query)

        try:
            if not self.settings.hybrid_rag_enabled:
                # Feature flag 关闭时退化为纯 dense（与变更前行为一致）
                dense_results = await self._dense_search(city, query, limit)
                return reciprocal_rank_fusion([dense_results], k=self.rrf_k, limit=limit)

            # 并行执行 dense + sparse 两路检索
            collection = self.settings.qdrant_travel_notes_collection
            upstream_limit = limit * self.sparse_limit_multiplier

            dense_task = self._dense_search(city, query, upstream_limit, collection=collection)
            sparse_task = self._sparse_search(city, query, upstream_limit, collection=collection)

            dense_results, sparse_results = await asyncio.gather(
                dense_task, sparse_task, return_exceptions=True
            )

            # 处理异常：任何一路失败则降级为该路空列表
            if isinstance(dense_results, Exception):
                logger.warning(f"Dense search failed, degrading to sparse-only: {dense_results}")
                dense_results = []
            if isinstance(sparse_results, Exception):
                logger.warning(f"Sparse search failed, degrading to dense-only: {sparse_results}")
                sparse_results = []

            ranked_lists: list[list[Reco]] = []
            if dense_results:
                ranked_lists.append(dense_results)
            if sparse_results:
                ranked_lists.append(sparse_results)

            if not ranked_lists:
                return self.fallback_notes(city, query)

            return reciprocal_rank_fusion(ranked_lists, k=self.rrf_k, limit=limit)

        except Exception as exc:
            logger.warning(f"Hybrid search failed, falling back: {exc}")
            return self.fallback_notes(city, query)

    async def _dense_search(
        self,
        city: str,
        query: str,
        limit: int,
        collection: str | None = None,
    ) -> list[Reco]:
        """Path A: 稠密向量检索。

        返回 [(chunk_id, cosine_score, payload), ...] 按分数降序。
        """
        collection = collection or self.settings.qdrant_travel_notes_collection
        vector = await self.embed(f"{city} {query}")

        # 结构化过滤：加入城市 payload filter（与 sparse 路径对齐）
        query_filter = None
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            query_filter = Filter(
                must=[
                    FieldCondition(key="city", match=MatchValue(value=city)),
                ]
            )
        except Exception:
            pass  # filter 可选，失败不影响检索

        search_kwargs: dict[str, Any] = {
            "collection_name": collection,
            "query_vector": vector,
            "limit": limit,
            "with_payload": True,
        }
        if query_filter is not None:
            search_kwargs["query_filter"] = query_filter

        result = await self.client.search(**search_kwargs)

        recos: list[Reco] = []
        for item in result:
            payload = item.payload or {}
            cid = str(item.id) if item.id else payload.get("doc_key", "")
            recos.append((cid, float(item.score), {
                "text": payload.get("text", ""),
                "city": payload.get("city", city),
                "source": payload.get("source", f"qdrant:{collection}"),
                "tags": payload.get("tags", []),
                "title": payload.get("title"),
                "entities": payload.get("entities", {}),
            }))
        return recos

    async def _sparse_search(
        self,
        city: str,
        query: str,
        limit: int,
        collection: str | None = None,
    ) -> list[Reco]:
        """Path B + C: BM25 稀疏关键词检索 + 结构化城市过滤。

        返回 [(chunk_id, bm25_score, payload), ...] 按分数降序。
        """
        collection = collection or self.settings.qdrant_travel_notes_collection
        persistence = PersistenceService(self.settings)
        rows = await persistence.sparse_search_chunks(
            collection=collection,
            city=city,
            query=query,
            limit=limit,
        )

        recos: list[Reco] = []
        for cid, bm25_score, row_dict in rows:
            recos.append((cid, bm25_score, {
                "text": row_dict.get("text", ""),
                "city": row_dict.get("city", city),
                "source": row_dict.get("source", "bm25"),
                "tags": row_dict.get("tags", []),
                "title": row_dict.get("title"),
                "entities": row_dict.get("entities", {}),
            }))
        return recos

    # ------------------------------------------------------------------
    # 双写导入
    # ------------------------------------------------------------------

    async def ingest_notes(self, city: str, documents: list[RagDocument]) -> RagIngestResponse:
        return await self._ingest(self.settings.qdrant_travel_notes_collection, city, documents)

    async def ingest_attractions(self, city: str, documents: list[RagDocument]) -> RagIngestResponse:
        return await self._ingest(self.settings.qdrant_attractions_collection, city, documents)

    async def _ingest(self, collection: str, city: str, documents: list[RagDocument]) -> RagIngestResponse:
        """双写导入：Qdrant (dense) + rag_chunks 表 (sparse)。

        任一路写入失败不影响另一路（try/except 隔离）。
        """
        job_id = f"rag_{uuid4().hex[:12]}"
        persistence = PersistenceService(self.settings)

        if not self.enabled:
            message = "DashScope/Qdrant 未配置，RAG 导入未执行"
            persistence.save_rag_status(job_id, collection, "fallback", 0, message)
            return RagIngestResponse(job_id=job_id, collection=collection, status="fallback", inserted=0, message=message)

        try:
            await self.ensure_collections()
        except Exception as exc:
            message = f"RAG 集合创建失败：{exc}"
            persistence.save_rag_status(job_id, collection, "failed", 0, message)
            return RagIngestResponse(job_id=job_id, collection=collection, status="failed", inserted=0, message=message)

        # 预处理：清洗 + 分块 + 实体抽取
        all_enriched_chunks: list[dict[str, Any]] = []
        for doc in documents:
            base_meta = {
                "collection": collection,
                "city": doc.city or city,
                "title": doc.title,
                "source": doc.source or "manual_ingest",
                "tags": doc.tags,
                "metadata": doc.metadata,
                "id": doc.id,
            }
            enriched = prepare_chunks(doc.text, base_meta=base_meta)
            all_enriched_chunks.extend(enriched)

        if not all_enriched_chunks:
            message = "预处理后无有效 chunk"
            persistence.save_rag_status(job_id, collection, "fallback", 0, message)
            return RagIngestResponse(job_id=job_id, collection=collection, status="fallback", inserted=0, message=message)

        # Path A: 写入 Qdrant (dense index)
        qdrant_count = 0
        try:
            points: list[PointStruct] = []
            for chunk in all_enriched_chunks:
                vector = await self.embed(chunk["text"])
                payload = {
                    "text": chunk["text"],
                    "title": chunk.get("title"),
                    "city": chunk.get("city", city),
                    "source": chunk.get("source", "manual_ingest"),
                    "tags": chunk.get("tags", []),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "doc_key": chunk.get("doc_key", ""),
                    "entities": chunk.get("entities", {}),
                }
                points.append(PointStruct(id=chunk["id"], vector=vector, payload=payload))
            if points:
                await self.client.upsert(collection_name=collection, points=points)
                qdrant_count = len(points)
        except Exception as exc:
            logger.warning(f"Qdrant write failed (continuing with PG write): {exc}")

        # Path B: 写入 rag_chunks 表 (sparse index)
        pg_count = 0
        try:
            pg_count = await persistence.upsert_rag_chunks(all_enriched_chunks)
        except Exception as exc:
            logger.warning(f"rag_chunks write failed (continuing): {exc}")

        total = max(qdrant_count, pg_count)
        message = f"双写完成: Qdrant {qdrant_count} points + rag_chunks {pg_count} rows"
        status = "completed" if (qdrant_count > 0 or pg_count > 0) else "failed"
        persistence.save_rag_status(job_id, collection, status, total, message)
        return RagIngestResponse(job_id=job_id, collection=collection, status=status, inserted=total, message=message)

    # ------------------------------------------------------------------
    # 降级回退
    # ------------------------------------------------------------------

    # 热门城市的基础知识库（用作RAG不可用时的回退）
    _CITY_KNOWLEDGE: dict[str, list[str]] = {
        "杭州": ["西湖必游，建议清晨或傍晚避开人流", "灵隐寺素面值得一试", "龙井村可体验采茶", "推荐京杭大运河水上巴士"],
        "北京": ["故宫需提前预约，周一闭馆", "长城建议去慕田峪段，人少景美", "南锣鼓巷商业化较重，可去五道营胡同", "烤鸭推荐便宜坊或四季民福"],
        "上海": ["外滩夜景比白天更美", "田子坊周末人极多，建议工作日去", "迪士尼避开周一和节假日", "推荐乘坐轮渡看黄浦江两岸"],
        "成都": ["大熊猫基地建议早上8点前到", "宽窄巷子商业化较重，人民公园更地道", "火锅推荐社区小店而非连锁品牌", "都江堰+青城山可安排一日游"],
        "西安": ["兵马俑建议请讲解，否则体验打折扣", "回民街主街人多价高，周边小巷更实惠", "城墙骑行建议傍晚，不晒且景色好", "陕西历史博物馆需提前3天预约"],
        "南京": ["中山陵周一闭馆", "秦淮河夜游比白天更有韵味", "南京博物院免费但需预约", "推荐老门东的小吃而非夫子庙"],
        "重庆": ["洪崖洞晚上亮灯后更壮观", "长江索道避开早晚高峰", "磁器口商业化重，可去山城步道", "火锅微辣对很多人已足够辣"],
        "苏州": ["拙政园和留园风格不同，都值得去", "平江路早上人少，适合拍照", "推荐坐船游古城河", "虎丘塔是苏州地标"],
    }

    @classmethod
    def fallback_notes(cls, city: str, query: str) -> list[dict[str, Any]]:
        tips = cls._CITY_KNOWLEDGE.get(city, [
            f"{city}建议上午安排主要景点，下午留弹性时间",
            "出行前查看天气预报，灵活调整室内外活动",
            "使用地图App规划路线，减少不必要的折返",
        ])
        results = []
        for i, tip in enumerate(tips):
            if query and any(w in tip for w in query):
                results.append({"score": 0.6, "city": city, "source": "local_knowledge", "tags": ["城市常识"], "text": tip})
        # 无匹配时返回所有
        if not results:
            results = [{"score": 0.3, "city": city, "source": "local_knowledge", "tags": ["城市常识"], "text": tip} for tip in tips]
        return results[:6]
