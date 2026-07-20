"""
TripCraft Async PostgreSQL Persistence Service

基于 SQLAlchemy 2.0 async 的持久化服务。
使用单例模式管理数据库连接池和 session 工厂。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, AsyncIterator

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.models.persistence_models import (
    AgentEvent,
    Base,
    ChatAdjustment,
    MemoryItem,
    Plan,
    PlanVersion,
    RagIngestionStatus,
    User,
)
from app.models.travel import (
    AgentProgressEvent,
    MemoryItem as MemoryItemSchema,
    PlanSummary,
    RagStatusItem,
    TravelPlan,
    TravelPlanRequest,
)

logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class PersistenceService:
    """
    异步持久化服务（单例）

    使用 PostgreSQL + SQLAlchemy async 实现。
    """

    _instance: PersistenceService | None = None
    _settings: Settings | None = None
    _engine: Any | None = None
    _async_session: async_sessionmaker[AsyncSession] | None = None

    def __new__(cls, settings: Settings | None = None) -> PersistenceService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self, settings: Settings | None = None) -> None:
        """初始化数据库连接和 session 工厂（幂等）"""
        # 始终创建新的引擎，确保与当前 event loop 兼容
        await self._close_engine()

        if settings is not None:
            self._settings = settings
        if self._settings is None:
            self._settings = get_settings()

        # 构建 async PostgreSQL URL
        db_url = (
            f"postgresql+asyncpg://{self._settings.postgres_user}:{self._settings.postgres_password}"
            f"@{self._settings.postgres_host}:{self._settings.postgres_port}/{self._settings.postgres_db}"
        )

        self._engine = create_async_engine(
            db_url,
            echo=self._settings.app_env == "development",
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
        )

        self._async_session = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # 创建表（如果不存在）
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self._ensure_rag_chunks_ddl(conn)

        logger.info("PostgreSQL persistence service initialized")

    @staticmethod
    async def _ensure_rag_chunks_ddl(conn: Any) -> None:
        """创建 rag_chunks 表及全文搜索索引（幂等，可重复执行）。

        包含 RagChunk ORM 模型对应的表结构 + tsvector generated column + GIN 索引。
        使用原始 DDL 而非 Alembic（项目无迁移基础设施）。
        """
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id            TEXT PRIMARY KEY,
                collection    VARCHAR(128) NOT NULL,
                city          TEXT NOT NULL,
                title         VARCHAR(512),
                text          TEXT NOT NULL,
                tags          JSONB NOT NULL DEFAULT '[]',
                source        VARCHAR(512),
                metadata      JSONB NOT NULL DEFAULT '{}',
                chunk_index   INTEGER NOT NULL DEFAULT 0,
                doc_key       TEXT NOT NULL,
                entities      JSONB NOT NULL DEFAULT '{}',
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            # 城市 + 集合索引
            "CREATE INDEX IF NOT EXISTS rag_chunks_city_idx ON rag_chunks (city)",
            "CREATE INDEX IF NOT EXISTS rag_chunks_collection_city_idx ON rag_chunks (collection, city)",
            # tsvector generated column (BM25 全文索引) — 仅当列不存在时添加
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'rag_chunks' AND column_name = 'search_vector'
                ) THEN
                    ALTER TABLE rag_chunks
                      ADD COLUMN search_vector tsvector
                      GENERATED ALWAYS AS (to_tsvector('simple', coalesce(text, ''))) STORED;
                END IF;
            END$$;
            """,
            # GIN 索引用于全文搜索
            "CREATE INDEX IF NOT EXISTS rag_chunks_search_vector_idx ON rag_chunks USING GIN (search_vector)",
            # trigram 扩展 + 索引（CJK 子串匹配加速）
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            "CREATE INDEX IF NOT EXISTS rag_chunks_text_trgm_idx ON rag_chunks USING GIN (text gin_trgm_ops)",
        ]
        for stmt in ddl_statements:
            try:
                await conn.execute(text(stmt))
            except Exception as exc:
                logger.warning(f"RAG chunk DDL step skipped: {exc}")

    async def _close_engine(self) -> None:
        """关闭旧的引擎"""
        if self._engine is not None:
            try:
                await self._engine.dispose()
            except Exception as exc:
                logger.debug(f"Engine disposal error: {exc}")
            self._engine = None
            self._async_session = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """获取数据库 session 的异步上下文管理器"""
        if self._async_session is None:
            await self.initialize()

        session = self._async_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        """关闭数据库连接"""
        await self._close_engine()
        logger.info("PostgreSQL persistence service closed")

    # ==================== 行程计划 CRUD ====================

    async def save_plan(
        self,
        plan: TravelPlan,
        request: TravelPlanRequest | None,
        events: Iterable[AgentProgressEvent] = (),
        owner_id: str | None = None,
    ) -> None:
        """保存或更新行程计划"""
        now = utc_now()
        plan_json = plan.model_dump_json()
        request_json = request.model_dump_json() if request else None
        revision_json = plan.revisions[-1].model_dump_json() if plan.revisions else None

        async with self.session() as session:
            existing = await session.execute(
                select(Plan).where(Plan.plan_id == plan.plan_id)
            )
            existing_plan = existing.scalar_one_or_none()

            if existing_plan:
                existing_plan.destination = plan.destination
                existing_plan.version = plan.version
                existing_plan.plan_json = plan_json
                existing_plan.request_json = request_json or existing_plan.request_json
                existing_plan.updated_at = datetime.now(UTC)
                if owner_id:
                    existing_plan.owner_id = owner_id
            else:
                db_plan = Plan(
                    plan_id=plan.plan_id,
                    destination=plan.destination,
                    version=plan.version,
                    plan_json=plan_json,
                    request_json=request_json,
                    owner_id=owner_id,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(db_plan)

            await session.flush()

            version = PlanVersion(
                plan_id=plan.plan_id,
                version=plan.version,
                plan_json=plan_json,
                revision_json=revision_json,
                created_at=datetime.now(UTC),
            )
            session.add(version)

            for event in events:
                db_event = AgentEvent(
                    plan_id=plan.plan_id,
                    agent=event.agent,
                    status=event.status,
                    message=event.message,
                    payload_json=json.dumps(event.payload, ensure_ascii=False),
                    created_at=datetime.now(UTC),
                )
                session.add(db_event)

    async def append_events(self, plan_id: str, events: Iterable[AgentProgressEvent]) -> None:
        """追加事件到已有计划"""
        now = datetime.now(UTC)
        async with self.session() as session:
            for event in events:
                db_event = AgentEvent(
                    plan_id=plan_id,
                    agent=event.agent,
                    status=event.status,
                    message=event.message,
                    payload_json=json.dumps(event.payload, ensure_ascii=False),
                    created_at=now,
                )
                session.add(db_event)

    async def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        """获取行程计划详情"""
        async with self.session() as session:
            result = await session.execute(select(Plan).where(Plan.plan_id == plan_id))
            plan_row = result.scalar_one_or_none()

            if not plan_row:
                return None

            events_result = await session.execute(
                select(AgentEvent)
                .where(AgentEvent.plan_id == plan_id)
                .order_by(AgentEvent.id)
            )
            events = events_result.scalars().all()

            adjustments_result = await session.execute(
                select(ChatAdjustment)
                .where(ChatAdjustment.plan_id == plan_id)
                .order_by(ChatAdjustment.id)
            )
            adjustments = adjustments_result.scalars().all()

            plan = TravelPlan.model_validate_json(plan_row.plan_json)
            request = (
                TravelPlanRequest.model_validate_json(plan_row.request_json)
                if plan_row.request_json
                else None
            )

            return {
                "plan": plan,
                "request": request,
                "events": [
                    AgentProgressEvent(
                        agent=e.agent,
                        status=e.status,
                        message=e.message,
                        payload=json.loads(e.payload_json),
                    )
                    for e in events
                ],
                "adjustments": [
                    {
                        "instruction": a.instruction,
                        "summary": a.summary,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in adjustments
                ],
                "created_at": plan_row.created_at.isoformat(),
                "updated_at": plan_row.updated_at.isoformat(),
            }

    async def list_plans(self, limit: int = 30, owner_id: str | None = None) -> list[PlanSummary]:
        """列出行程计划摘要（仅返回属于该用户的行程）"""
        async with self.session() as session:
            query = select(Plan).order_by(Plan.updated_at.desc()).limit(limit)
            if owner_id:
                query = query.where(Plan.owner_id == owner_id)
            else:
                # 没有 owner_id 时返回空，避免泄露其他用户数据
                return []

            result = await session.execute(query)
            rows = result.scalars().all()

            summaries: list[PlanSummary] = []
            for row in rows:
                plan = TravelPlan.model_validate_json(row.plan_json)
                departure = None
                if row.request_json:
                    try:
                        import json as _json
                        req = _json.loads(row.request_json)
                        departure = req.get("departure_city") or None
                    except Exception:
                        pass
                summaries.append(
                    PlanSummary(
                        plan_id=row.plan_id,
                        destination=row.destination,
                        departure_city=departure,
                        version=row.version,
                        days=len(plan.days),
                        total_estimated_cost=plan.total_estimated_cost,
                        created_at=row.created_at.isoformat(),
                        updated_at=row.updated_at.isoformat(),
                    )
                )
            return summaries

    async def get_events(self, plan_id: str) -> list[AgentProgressEvent]:
        """获取行程事件列表"""
        async with self.session() as session:
            result = await session.execute(
                select(AgentEvent)
                .where(AgentEvent.plan_id == plan_id)
                .order_by(AgentEvent.id)
            )
            rows = result.scalars().all()
            return [
                AgentProgressEvent(
                    agent=e.agent,
                    status=e.status,
                    message=e.message,
                    payload=json.loads(e.payload_json),
                )
                for e in rows
            ]

    async def delete_plan(self, plan_id: str) -> bool:
        """删除行程计划"""
        async with self.session() as session:
            result = await session.execute(delete(Plan).where(Plan.plan_id == plan_id))
            return result.rowcount > 0

    # ==================== 调整记录 ====================

    async def save_adjustment(
        self,
        plan_id: str,
        instruction: str,
        summary: str,
        before_plan: TravelPlan,
        after_plan: TravelPlan,
        events: Iterable[AgentProgressEvent] = (),
    ) -> None:
        """保存调整记录并更新计划"""
        now = utc_now()

        async with self.session() as session:
            adjustment = ChatAdjustment(
                plan_id=plan_id,
                instruction=instruction,
                summary=summary,
                before_plan_json=before_plan.model_dump_json(),
                after_plan_json=after_plan.model_dump_json(),
                created_at=datetime.now(UTC),
            )
            session.add(adjustment)

            result = await session.execute(select(Plan).where(Plan.plan_id == plan_id))
            plan_row = result.scalar_one_or_none()
            if plan_row:
                plan_row.version = after_plan.version
                plan_row.plan_json = after_plan.model_dump_json()
                plan_row.updated_at = datetime.now(UTC)

            version = PlanVersion(
                plan_id=plan_id,
                version=after_plan.version,
                plan_json=after_plan.model_dump_json(),
                revision_json=None,
                created_at=datetime.now(UTC),
            )
            session.add(version)

            for event in events:
                db_event = AgentEvent(
                    plan_id=plan_id,
                    agent=event.agent,
                    status=event.status,
                    message=event.message,
                    payload_json=json.dumps(event.payload, ensure_ascii=False),
                    created_at=datetime.now(UTC),
                )
                session.add(db_event)

    # ==================== 用户偏好记忆 ====================

    async def upsert_memory(self, items: Iterable[MemoryItemSchema], owner_id: str) -> None:
        """保存或更新用户偏好记忆"""
        now = datetime.now(UTC)
        async with self.session() as session:
            for item in items:
                existing = await session.execute(
                    select(MemoryItem).where(
                        MemoryItem.key == item.key,
                        MemoryItem.owner_id == owner_id
                    )
                )
                existing_item = existing.scalar_one_or_none()

                if existing_item:
                    existing_item.value = item.value
                    existing_item.category = item.category
                    existing_item.source = item.source
                    existing_item.confidence = item.confidence
                    existing_item.updated_at = now
                else:
                    new_item = MemoryItem(
                        key=item.key,
                        owner_id=owner_id,
                        value=item.value,
                        category=item.category,
                        source=item.source,
                        confidence=item.confidence,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(new_item)

    async def list_memory(self, owner_id: str) -> list[MemoryItemSchema]:
        """列出指定用户的偏好记忆"""
        async with self.session() as session:
            result = await session.execute(
                select(MemoryItem)
                .where(MemoryItem.owner_id == owner_id)
                .order_by(MemoryItem.updated_at.desc())
            )
            rows = result.scalars().all()
            return [
                MemoryItemSchema(
                    key=m.key,
                    value=m.value,
                    category=m.category,
                    source=m.source,
                    confidence=m.confidence,
                    updated_at=m.updated_at.isoformat(),
                )
                for m in rows
            ]

    async def delete_memory(self, key: str, owner_id: str) -> bool:
        """删除一条记忆"""
        async with self.session() as session:
            result = await session.execute(
                delete(MemoryItem).where(
                    MemoryItem.key == key,
                    MemoryItem.owner_id == owner_id
                )
            )
            return result.rowcount > 0

    # ==================== RAG 状态 ====================

    async def save_rag_status(
        self,
        job_id: str,
        collection: str,
        status: str,
        inserted: int,
        message: str | None,
    ) -> None:
        """保存 RAG 导入状态"""
        now = datetime.now(UTC)
        async with self.session() as session:
            existing = await session.execute(
                select(RagIngestionStatus).where(RagIngestionStatus.job_id == job_id)
            )
            existing_item = existing.scalar_one_or_none()

            if existing_item:
                existing_item.status = status
                existing_item.inserted = inserted
                existing_item.message = message
                existing_item.updated_at = now
            else:
                new_item = RagIngestionStatus(
                    job_id=job_id,
                    collection=collection,
                    status=status,
                    inserted=inserted,
                    message=message,
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_item)

    async def list_rag_status(self) -> list[RagStatusItem]:
        """列出 RAG 导入状态"""
        async with self.session() as session:
            result = await session.execute(
                select(RagIngestionStatus)
                .order_by(RagIngestionStatus.updated_at.desc())
                .limit(50)
            )
            rows = result.scalars().all()
            return [
                RagStatusItem(
                    job_id=r.job_id,
                    collection=r.collection,
                    status=r.status,
                    inserted=r.inserted,
                    message=r.message,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                )
                for r in rows
            ]

    # ==================== 用户管理 ====================

    async def create_user(
        self, user_id: str, username: str, email: str | None, password_hash: str, role: str = "traveler"
    ) -> User:
        """创建用户"""
        async with self.session() as session:
            user = User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)
            await session.flush()
            return user

    async def get_user_by_username(self, username: str) -> User | None:
        """根据用户名获取用户"""
        async with self.session() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        """根据 ID 获取用户"""
        async with self.session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    # ==================== RAG Chunks 双写 / BM25 检索 ====================

    async def upsert_rag_chunks(self, rows: Iterable[dict[str, Any]]) -> int:
        """批量 upsert rag_chunks 记录（双写 dense + sparse 索引的 PG 侧）。

        使用 INSERT ... ON CONFLICT DO UPDATE 保证幂等性。
        部分行失败不影响整体（逐行 savepoint）。
        """
        from app.models.rag_chunk_models import RagChunk

        count = 0
        async with self.session() as session:
            for row in rows:
                now = datetime.now(UTC)
                stmt = text(
                    """
                    INSERT INTO rag_chunks
                        (id, collection, city, title, text, tags, source, metadata,
                         chunk_index, doc_key, entities, created_at)
                    VALUES
                        (:id, :collection, :city, :title, :text, :tags::jsonb, :source,
                         :metadata::jsonb, :chunk_index, :doc_key, :entities::jsonb, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        title = EXCLUDED.title,
                        tags = EXCLUDED.tags,
                        source = EXCLUDED.source,
                        metadata = EXCLUDED.metadata,
                        chunk_index = EXCLUDED.chunk_index,
                        doc_key = EXCLUDED.doc_key,
                        entities = EXCLUDED.entities
                    """
                )
                await session.execute(
                    stmt,
                    {
                        "id": row["id"],
                        "collection": row.get("collection", "travel_notes"),
                        "city": row.get("city", ""),
                        "title": row.get("title"),
                        "text": row.get("text", ""),
                        "tags": json.dumps(row.get("tags", []), ensure_ascii=False),
                        "source": row.get("source"),
                        "metadata": json.dumps(row.get("metadata", {}), ensure_ascii=False),
                        "chunk_index": row.get("chunk_index", 0),
                        "doc_key": row.get("doc_key", ""),
                        "entities": json.dumps(row.get("entities", {}), ensure_ascii=False),
                        "created_at": now,
                    },
                )
                count += 1
            await session.commit()
        return count

    async def sparse_search_chunks(
        self,
        collection: str,
        city: str,
        query: str,
        limit: int = 18,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """BM25 稀疏关键词检索（PostgreSQL ts_rank_cd）。

        返回 [(chunk_id, bm25_score, payload_dict), ...] 按分数降序。
        查询失败时返回空列表（调用方应继续降级处理）。

        Args:
            collection: 集合名 (travel_notes / attractions)
            city: 城市过滤
            query: 原始查询文本
            limit: 返回条数上限（融合前通常 3x 最终 limit）
        """
        if not query or not query.strip():
            return []

        stmt = text(
            """
            SELECT id, city, text, title, source, tags, metadata, chunk_index, entities,
                   ts_rank_cd(search_vector, websearch_to_tsquery('simple', :query)) AS bm25
            FROM rag_chunks
            WHERE collection = :collection
              AND city = :city
              AND search_vector @@ websearch_to_tsquery('simple', :query)
            ORDER BY bm25 DESC
            LIMIT :limit
            """
        )

        try:
            async with self.session() as session:
                result = await session.execute(
                    stmt,
                    {"collection": collection, "city": city, "query": query.strip(), "limit": limit},
                )
                rows = result.fetchall()
        except Exception as exc:
            logger.debug(f"Sparse search failed (degrading to dense-only): {exc}")
            return []

        results: list[tuple[str, float, dict[str, Any]]] = []
        for row in rows:
            row_dict = {
                "id": row[0],
                "city": row[1],
                "text": row[2],
                "title": row[3],
                "source": row[4],
                "tags": row[5] or [],
                "metadata": row[6] or {},
                "chunk_index": row[7],
                "entities": row[8] or {},
            }
            results.append((row[0], float(row[9] or 0.0), row_dict))
        return results


def get_persistence(settings: Settings | None = None) -> PersistenceService:
    """获取持久化服务单例"""
    return PersistenceService(settings)
