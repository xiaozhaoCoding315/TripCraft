"""
TripCraft SQLAlchemy ORM Models

PostgreSQL 异步 ORM 模型定义。
生产环境使用 SQLAlchemy 2.0 async 语法。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """基础 ORM 模型"""

    pass


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="traveler", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    plans: Mapped[list["Plan"]] = relationship("Plan", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class Plan(Base):
    """行程计划表"""

    __tablename__ = "plans"

    plan_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    destination: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    owner_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    owner: Mapped["User | None"] = relationship("User", back_populates="plans")
    versions: Mapped[list["PlanVersion"]] = relationship(
        "PlanVersion", back_populates="plan", cascade="all, delete-orphan", order_by="PlanVersion.id"
    )
    events: Mapped[list["AgentEvent"]] = relationship(
        "AgentEvent", back_populates="plan", cascade="all, delete-orphan", order_by="AgentEvent.id"
    )
    adjustments: Mapped[list["ChatAdjustment"]] = relationship(
        "ChatAdjustment", back_populates="plan", cascade="all, delete-orphan", order_by="ChatAdjustment.id"
    )

    def __repr__(self) -> str:
        return f"<Plan(id={self.plan_id}, dest={self.destination}, v={self.version})>"


class PlanVersion(Base):
    """行程版本历史表"""

    __tablename__ = "plan_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("plans.plan_id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关系
    plan: Mapped["Plan"] = relationship("Plan", back_populates="versions")

    def __repr__(self) -> str:
        return f"<PlanVersion(plan={self.plan_id}, v={self.version})>"


class AgentEvent(Base):
    """Agent 执行事件表"""

    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("plans.plan_id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关系
    plan: Mapped["Plan"] = relationship("Plan", back_populates="events")

    def __repr__(self) -> str:
        return f"<AgentEvent(plan={self.plan_id}, agent={self.agent}, status={self.status})>"


class ChatAdjustment(Base):
    """对话调整记录表"""

    __tablename__ = "chat_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("plans.plan_id", ondelete="CASCADE"), nullable=False, index=True
    )
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    before_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    after_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关系
    plan: Mapped["Plan"] = relationship("Plan", back_populates="adjustments")

    def __repr__(self) -> str:
        return f"<ChatAdjustment(plan={self.plan_id}, instruction={self.instruction[:30]}...)>"


class MemoryItem(Base):
    """用户偏好记忆表"""

    __tablename__ = "memory_items"

    # 复合主键：key + owner_id，确保每个用户的记忆独立
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="general")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<MemoryItem(key={self.key}, owner={self.owner_id}, category={self.category})>"


class RagIngestionStatus(Base):
    """RAG 知识库导入状态表"""

    __tablename__ = "rag_ingestion_status"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    collection: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RagIngestionStatus(job={self.job_id}, status={self.status})>"
