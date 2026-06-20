from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4, uuid5, NAMESPACE_URL

import dashscope
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import Settings
from app.models.travel import RagDocument, RagIngestResponse
from app.services.persistence import PersistenceService


class TravelRagService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    @property
    def enabled(self) -> bool:
        return bool(self.settings.dashscope_api_key and self.settings.qdrant_url)

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

    async def search_notes(self, city: str, query: str, limit: int = 6) -> list[dict[str, Any]]:
        if not self.enabled:
            return self.fallback_notes(city, query)
        try:
            vector = await self.embed(f"{city} {query}")
            result = await self.client.search(
                collection_name=self.settings.qdrant_travel_notes_collection,
                query_vector=vector,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "score": item.score,
                    "text": (item.payload or {}).get("text") or (item.payload or {}).get("content"),
                    "city": (item.payload or {}).get("city", city),
                    "source": (item.payload or {}).get("source", "qdrant:travel_notes"),
                    "tags": (item.payload or {}).get("tags", []),
                }
                for item in result
            ]
        except Exception:
            return self.fallback_notes(city, query)

    async def ingest_notes(self, city: str, documents: list[RagDocument]) -> RagIngestResponse:
        return await self._ingest(self.settings.qdrant_travel_notes_collection, city, documents)

    async def ingest_attractions(self, city: str, documents: list[RagDocument]) -> RagIngestResponse:
        return await self._ingest(self.settings.qdrant_attractions_collection, city, documents)

    async def _ingest(self, collection: str, city: str, documents: list[RagDocument]) -> RagIngestResponse:
        job_id = f"rag_{uuid4().hex[:12]}"
        persistence = PersistenceService(self.settings)
        if not self.enabled:
            message = "DashScope/Qdrant 未配置，RAG 导入未执行"
            persistence.save_rag_status(job_id, collection, "fallback", 0, message)
            return RagIngestResponse(job_id=job_id, collection=collection, status="fallback", inserted=0, message=message)
        try:
            await self.ensure_collections()
            points: list[PointStruct] = []
            for doc in documents:
                for index, chunk in enumerate(self._chunk_text(doc.text)):
                    vector = await self.embed(chunk)
                    source_key = doc.id or doc.source or doc.title or hashlib.sha1(doc.text.encode("utf-8")).hexdigest()
                    point_id = str(uuid5(NAMESPACE_URL, f"{collection}:{city}:{source_key}:{index}"))
                    payload = {
                        "text": chunk,
                        "title": doc.title,
                        "city": doc.city or city,
                        "source": doc.source or "manual_ingest",
                        "tags": doc.tags,
                        "chunk_index": index,
                        **doc.metadata,
                    }
                    points.append(PointStruct(id=point_id, vector=vector, payload=payload))
            if points:
                await self.client.upsert(collection_name=collection, points=points)
            message = f"成功导入 {len(points)} 个分块"
            persistence.save_rag_status(job_id, collection, "completed", len(points), message)
            return RagIngestResponse(job_id=job_id, collection=collection, status="completed", inserted=len(points), message=message)
        except Exception as exc:
            message = f"RAG 导入失败：{exc}"
            persistence.save_rag_status(job_id, collection, "failed", 0, message)
            return RagIngestResponse(job_id=job_id, collection=collection, status="failed", inserted=0, message=message)

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 700, overlap: int = 80) -> list[str]:
        clean = " ".join(text.split())
        if len(clean) <= max_chars:
            return [clean]
        chunks: list[str] = []
        start = 0
        while start < len(clean):
            end = min(start + max_chars, len(clean))
            chunks.append(clean[start:end])
            if end == len(clean):
                break
            start = max(0, end - overlap)
        return chunks

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
