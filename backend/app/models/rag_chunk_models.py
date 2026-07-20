"""
TripCraft RagChunk ORM Model

Defines the rag_chunks table used for BM25 sparse retrieval and structured filtering,
complementing the Qdrant dense vector index. Both indexes share the same chunk_id
derivation (uuid5) so RRF fusion can deduplicate across dense and sparse paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Local base for rag_chunk models (separate from persistence Base to avoid
    circular imports — both are bound to the same engine at runtime)."""

    pass


class RagChunk(Base):
    """RAG chunk record with PostgreSQL full-text search support.

    The search_vector column is a GENERATED column maintained by PostgreSQL.
    It is declared here as a read-only ORM attribute for SELECT queries —
    values are never written from Python.
    """

    __tablename__ = "rag_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    collection: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="'[]'")
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="'{}'"
    )
    chunk_index: Mapped[int] = mapped_column(default=0, nullable=False)
    doc_key: Mapped[str] = mapped_column(String(512), nullable=False)
    entities: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="'{}'"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default="now()", nullable=False
    )

    # Read-only generated column — never written from Python.
    # Declared via Column (not mapped_column) to avoid dataclass init conflicts.
    search_vector = Column(TSVECTOR)

    __table_args__ = (
        Index("rag_chunks_collection_city_idx", "collection", "city"),
    )

    def __repr__(self) -> str:
        return f"<RagChunk(id={self.id[:12]}..., city={self.city}, coll={self.collection})>"
