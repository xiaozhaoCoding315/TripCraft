from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


AgentName = Literal[
    "orchestrator",
    "weather",
    "transport",
    "accommodation",
    "attraction",
    "itinerary",
    "critic",
]
AgentStatus = Literal["queued", "running", "success", "error", "retrying", "warning"]


class TravelerProfile(BaseModel):
    adults: int = 1
    children: int = 0
    seniors: int = 0
    mobility_notes: str | None = None


class TravelPlanRequest(BaseModel):
    destination: str = Field(..., min_length=1, examples=["杭州"])
    start_date: str = Field(..., examples=["2026-07-01"])
    days: int = Field(..., ge=1, le=14)
    budget: int | None = Field(default=None, ge=0)
    departure_city: str | None = Field(default=None, examples=["上海"])
    travelers: TravelerProfile = Field(default_factory=TravelerProfile)
    interests: list[str] = Field(default_factory=list)
    preferences: str | None = None

    @field_validator("interests", mode="before")
    @classmethod
    def parse_interests(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
        return value


class SourceRef(BaseModel):
    type: Literal["amap", "rag", "llm", "template"]
    label: str
    url: str | None = None


class GeoPoint(BaseModel):
    lng: float | None = None
    lat: float | None = None
    address: str | None = None


class ItineraryItem(BaseModel):
    id: str = Field(default_factory=lambda: f"item_{uuid4().hex[:10]}")
    time: str
    type: Literal["transport", "attraction", "meal", "hotel", "rest", "note"]
    title: str
    description: str
    location: GeoPoint | None = None
    cost: float | None = None
    duration_minutes: int | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class DayPlan(BaseModel):
    day: int
    date: str | None = None
    title: str
    weather_summary: str | None = None
    items: list[ItineraryItem] = Field(default_factory=list)
    estimated_cost: float | None = None
    pace: Literal["relaxed", "balanced", "intensive"] = "balanced"


class CriticComment(BaseModel):
    dimension: Literal["physical", "time", "budget", "weather", "data", "overall"]
    severity: Literal["info", "warning", "critical"] = "info"
    message: str
    suggestion: str | None = None


class Revision(BaseModel):
    version: int
    passed: bool
    comments: list[CriticComment] = Field(default_factory=list)
    summary: str


class TravelPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:12]}")
    destination: str
    version: int = 1
    days: list[DayPlan] = Field(default_factory=list)
    total_estimated_cost: float | None = None
    revisions: list[Revision] = Field(default_factory=list)
    raw_context: dict[str, Any] = Field(default_factory=dict)


class AgentProgressEvent(BaseModel):
    agent: AgentName
    status: AgentStatus
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TravelPlanResponse(BaseModel):
    plan: TravelPlan
    events: list[AgentProgressEvent] = Field(default_factory=list)


class AdjustmentRequest(BaseModel):
    plan: TravelPlan
    instruction: str = Field(..., min_length=1)


class AdjustmentResponse(BaseModel):
    plan: TravelPlan
    summary: str
    events: list[AgentProgressEvent] = Field(default_factory=list)


class PlanSummary(BaseModel):
    plan_id: str
    destination: str
    departure_city: str | None = None
    version: int
    days: int
    total_estimated_cost: float | None = None
    created_at: str
    updated_at: str


class PersistedPlanResponse(BaseModel):
    plan: TravelPlan
    request: TravelPlanRequest | None = None
    events: list[AgentProgressEvent] = Field(default_factory=list)
    adjustments: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class MemoryItem(BaseModel):
    key: str
    value: str
    category: Literal["traveler", "pace", "budget", "hotel", "transport", "interest", "avoid", "general"] = "general"
    source: Literal["request", "adjustment", "system", "llm"] = "system"
    confidence: float = Field(default=1.0, ge=0, le=1)
    updated_at: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str | None = None


class RagDocument(BaseModel):
    id: str | None = None
    title: str | None = None
    text: str = Field(..., min_length=1)
    city: str | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagIngestRequest(BaseModel):
    city: str
    documents: list[RagDocument] = Field(..., min_length=1)


class RagIngestResponse(BaseModel):
    job_id: str
    collection: str
    status: Literal["completed", "failed", "fallback"]
    inserted: int = 0
    message: str


class RagStatusItem(BaseModel):
    job_id: str
    collection: str
    status: str
    inserted: int
    message: str | None = None
    created_at: str
    updated_at: str
