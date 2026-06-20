"""
TripCraft API Routes

所有 API 端点，使用 PostgreSQL 持久化 + JWT 认证。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.agents.workflow import TravelPlannerWorkflow
from app.api.auth import router as auth_router
from app.core.config import get_settings
from app.models.travel import (
    AdjustmentRequest,
    AdjustmentResponse,
    AgentProgressEvent,
    MemoryItem,
    PersistedPlanResponse,
    PlanSummary,
    RagIngestRequest,
    RagIngestResponse,
    RagStatusItem,
    TravelPlanRequest,
    TravelPlanResponse,
)
from app.services.adjustment import AdjustmentService, extract_memory_from_instruction, extract_memory_from_request_text
from app.services.auth import User, require_user
from app.services.cache import cache_service
from app.services.export import export_service
from app.services.llm import LlmService
from app.services.persistence import PersistenceService, get_persistence
from app.services.rag import TravelRagService

router = APIRouter(prefix="/api/v1", tags=["travel"])

# 包含认证路由
router.include_router(auth_router)


def persistence() -> PersistenceService:
    """获取持久化服务单例"""
    return get_persistence()


# ==================== 健康检查 ====================

@router.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "tripcraft",
        "redis": cache_service.available,
    }


# ==================== 行程计划 CRUD ====================

@router.get("/plans", response_model=list[PlanSummary])
async def list_plans(
    limit: int = 30,
    user: User = Depends(require_user),
) -> list[PlanSummary]:
    """列出当前用户的行程计划"""
    return await persistence().list_plans(limit=limit, owner_id=user.user_id)


@router.get("/plans/{plan_id}", response_model=PersistedPlanResponse)
async def get_plan(plan_id: str, user: User = Depends(require_user)) -> PersistedPlanResponse:
    """获取行程计划详情"""
    data = await persistence().get_plan(plan_id)
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found")
    # 检查所有权
    if data.get("owner_id") and data["owner_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return PersistedPlanResponse(**data)


@router.get("/plans/{plan_id}/events", response_model=list[AgentProgressEvent])
async def get_plan_events(plan_id: str, user: User = Depends(require_user)) -> list[AgentProgressEvent]:
    """获取行程事件列表"""
    store = persistence()
    # 检查所有权
    data = await store.get_plan(plan_id)
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found")
    if data.get("owner_id") and data["owner_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await store.get_events(plan_id)


@router.post("/plans", response_model=TravelPlanResponse)
async def create_plan(
    request: TravelPlanRequest,
    user: User = Depends(require_user),
) -> TravelPlanResponse:
    """创建新的行程计划"""
    store = persistence()
    memory = await store.list_memory(owner_id=user.user_id)
    workflow = TravelPlannerWorkflow()
    plan, events = await workflow.plan(request, memory_context=memory)
    await store.save_plan(plan, request, events, owner_id=user.user_id)
    await store.upsert_memory(_memory_from_request(request), owner_id=user.user_id)
    await cache_service.set_json(
        f"plan:{plan.plan_id}:events",
        [event.model_dump() for event in events],
        ttl_seconds=86400,
    )
    return TravelPlanResponse(plan=plan, events=events)


@router.websocket("/plans/stream")
async def stream_plan(websocket: WebSocket) -> None:
    """WebSocket 流式规划（支持 token 认证）"""
    # 尝试从 query param 获取 token
    token = websocket.query_params.get("token")
    owner_id = None
    if token:
        try:
            from app.services.auth import decode_token
            settings = get_settings()
            payload = decode_token(token, settings)
            owner_id = payload.get("sub")
        except Exception:
            pass

    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        request = TravelPlanRequest.model_validate(payload)
        store = persistence()
        live_events: list[AgentProgressEvent] = []

        async def send_event(event: AgentProgressEvent) -> None:
            live_events.append(event)
            await websocket.send_json({"type": "progress", "event": event.model_dump()})

        workflow = TravelPlannerWorkflow(progress_sink=send_event)
        plan, events = await workflow.plan(request, memory_context=await store.list_memory(owner_id=owner_id))
        # 认证用户设置 owner_id，否则为 NULL（兼容旧版前端）
        await store.save_plan(plan, request, events, owner_id=owner_id)
        await store.upsert_memory(_memory_from_request(request), owner_id=owner_id)
        await cache_service.set_json(
            f"plan:{plan.plan_id}:events",
            [event.model_dump() for event in events],
            ttl_seconds=86400,
        )
        await websocket.send_json(
            {
                "type": "complete",
                "plan": plan.model_dump(),
                "events": [event.model_dump() for event in events],
            }
        )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass


@router.websocket("/plans/adjust/stream")
async def stream_adjust(websocket: WebSocket) -> None:
    """WebSocket 流式调整 — 支持 token 认证，数据按用户隔离"""
    # 从 query param 获取 token 进行认证
    token = websocket.query_params.get("token")
    owner_id: str | None = None
    if token:
        try:
            from app.services.auth import decode_token
            settings = get_settings()
            payload = decode_token(token, settings)
            owner_id = payload.get("sub")
        except Exception:
            pass

    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        request = AdjustmentRequest.model_validate(payload)

        store = persistence()
        # 使用用户自己的偏好记忆（未认证则为空）
        memory = await store.list_memory(owner_id=owner_id) if owner_id else []
        llm = LlmService(get_settings())
        service = AdjustmentService(llm)

        async def send_progress(event: AgentProgressEvent) -> None:
            await websocket.send_json({
                "type": "progress",
                "agent": event.agent,
                "message": event.message,
            })

        # 发送开始事件
        await send_progress(
            AgentProgressEvent(agent="orchestrator", status="running", message="正在解析调整意图...")
        )

        # 获取调整结果
        before = request.plan.model_copy(deep=True)
        plan, summary, events, memories = await service.adjust(
            before, request.instruction.strip(), memory
        )

        # 发送完成事件
        for event in events:
            await send_progress(event)

        # 保存调整记录
        await store.save_adjustment(
            plan.plan_id, request.instruction.strip(), summary, before, plan, events
        )
        # 保存偏好记忆（归当前用户所有）
        if owner_id:
            await store.upsert_memory(
                memories or extract_memory_from_instruction(request.instruction.strip()),
                owner_id=owner_id,
            )

        await websocket.send_json({
            "type": "complete",
            "plan": plan.model_dump(),
            "summary": summary,
        })
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass


@router.post("/plans/adjust", response_model=AdjustmentResponse)
async def adjust_plan(
    request: AdjustmentRequest,
    user: User = Depends(require_user),
) -> AdjustmentResponse:
    """调整行程计划（非流式，保留兼容）"""
    store = persistence()
    memory = await store.list_memory(owner_id=user.user_id)
    service = AdjustmentService(LlmService(get_settings()))
    before = request.plan.model_copy(deep=True)
    plan, summary, events, memories = await service.adjust(before, request.instruction.strip(), memory)

    # 如果计划不存在，先保存原文（归属当前用户）
    existing = await store.get_plan(plan.plan_id)
    if not existing:
        await store.save_plan(before, None, [], owner_id=user.user_id)

    await store.save_adjustment(plan.plan_id, request.instruction.strip(), summary, before, plan, events)
    await store.upsert_memory(memories or extract_memory_from_instruction(request.instruction.strip()), owner_id=user.user_id)
    return AdjustmentResponse(plan=plan, summary=summary, events=events)


# ==================== 对话记录持久化 ====================

@router.get("/plans/{plan_id}/chat")
async def get_chat_messages(plan_id: str, user: User = Depends(require_user)) -> list[dict]:
    """获取某个行程的对话历史（Redis缓存）"""
    store = persistence()
    data = _verify_plan_ownership(await store.get_plan(plan_id), user)
    key = f"chat:{plan_id}"
    messages = await cache_service.get_json(key) or []
    return messages


@router.post("/plans/{plan_id}/chat")
async def save_chat_messages(
    plan_id: str,
    messages: list[dict],
    user: User = Depends(require_user),
) -> dict[str, bool]:
    """保存某个行程的对话历史（Redis缓存，TTL 7天）"""
    store = persistence()
    data = _verify_plan_ownership(await store.get_plan(plan_id), user)
    key = f"chat:{plan_id}"
    await cache_service.set_json(key, messages, ttl_seconds=604800)
    return {"saved": True}


# ==================== 记忆管理 ====================

@router.get("/memory", response_model=list[MemoryItem])
async def list_memory(user: User = Depends(require_user)) -> list[MemoryItem]:
    """列出用户偏好记忆"""
    return await persistence().list_memory(owner_id=user.user_id)


@router.delete("/memory/{key}")
async def delete_memory(key: str, user: User = Depends(require_user)) -> dict[str, bool]:
    """删除一条记忆"""
    result = await persistence().delete_memory(key, owner_id=user.user_id)
    return {"deleted": result}


# ==================== 行程删除 ====================

@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, user: User = Depends(require_user)) -> dict[str, bool]:
    """删除行程计划（仅所有者可删除）"""
    store = persistence()
    data = await store.get_plan(plan_id)
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found")
    # 检查所有权（如果计划有所有者）
    if data.get("owner_id") and data["owner_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await store.delete_plan(plan_id)
    return {"deleted": result}


# ==================== RAG 管理 ====================

@router.post("/rag/notes", response_model=RagIngestResponse)
async def ingest_notes(
    request: RagIngestRequest,
    user: User = Depends(require_user),
) -> RagIngestResponse:
    """导入游记到 RAG 知识库"""
    return await TravelRagService(get_settings()).ingest_notes(request.city, request.documents)


@router.post("/rag/attractions", response_model=RagIngestResponse)
async def ingest_attractions(
    request: RagIngestRequest,
    user: User = Depends(require_user),
) -> RagIngestResponse:
    """导入景点到 RAG 知识库"""
    return await TravelRagService(get_settings()).ingest_attractions(request.city, request.documents)


@router.get("/rag/status", response_model=list[RagStatusItem])
async def rag_status(user: User = Depends(require_user)) -> list[RagStatusItem]:
    """获取 RAG 导入状态"""
    return await persistence().list_rag_status()


# ==================== 导出接口 ====================

def _verify_plan_ownership(data: dict[str, Any] | None, user: User) -> dict[str, Any]:
    """验证行程存在且属于当前用户"""
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found")
    if data.get("owner_id") and data["owner_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return data


@router.get("/plans/{plan_id}/export/json")
async def export_plan_json(plan_id: str, user: User = Depends(require_user)) -> dict[str, Any]:
    """导出行程为 JSON"""
    store = persistence()
    data = _verify_plan_ownership(await store.get_plan(plan_id), user)
    plan = data["plan"]
    return {
        "filename": export_service.get_export_filename(plan, "json"),
        "content": plan.model_dump(),
    }


@router.get("/plans/{plan_id}/export/markdown")
async def export_plan_markdown(plan_id: str, user: User = Depends(require_user)) -> dict[str, str]:
    """导出行程为 Markdown"""
    store = persistence()
    data = _verify_plan_ownership(await store.get_plan(plan_id), user)
    plan = data["plan"]
    return {
        "filename": export_service.get_export_filename(plan, "md"),
        "content": export_service.to_markdown(plan),
    }


@router.get("/plans/{plan_id}/export/text")
async def export_plan_text(plan_id: str, user: User = Depends(require_user)) -> dict[str, str]:
    """导出行程为纯文本"""
    store = persistence()
    data = _verify_plan_ownership(await store.get_plan(plan_id), user)
    plan = data["plan"]
    return {
        "filename": export_service.get_export_filename(plan, "txt"),
        "content": export_service.to_plain_text(plan),
    }


@router.get("/plans/{plan_id}/export/preview")
async def export_plan_preview(plan_id: str, user: User = Depends(require_user)) -> dict[str, str]:
    """AI 预览导出 — 使用 LLM 格式化行程为精美 Markdown"""
    store = persistence()
    data = _verify_plan_ownership(await store.get_plan(plan_id), user)
    plan = data["plan"]

    # 先构建基础 markdown
    base_md = export_service.to_markdown(plan)

    # 用 LLM 润色格式化
    try:
        settings = get_settings()
        llm = LlmService(settings)
        if llm.enabled:
            prompt = f"""你是一位专业旅行编辑。请将以下旅行计划润色为一份精美的 Markdown 格式游记。
要求：
1. 保持所有原始数据不变（日期、时间、费用、地点）
2. 添加吸引人的标题和emoji装饰
3. 每个景点添加1-2句生动的描述
4. 在末尾添加"旅行小贴士"部分（基于行程特点给出3条建议）
5. 保持结构清晰：概述 → 每日行程 → 费用一览 → 旅行小贴士

原始行程：
{base_md}"""
            polished = await llm.chat(prompt, max_tokens=4096)
            content = polished or base_md
        else:
            content = base_md
    except Exception:
        content = base_md

    return {
        "filename": export_service.get_export_filename(plan, "md"),
        "content": content,
    }


# ==================== 辅助函数 ====================

def _memory_from_request(request: TravelPlanRequest) -> list[MemoryItem]:
    """从请求中提取用户偏好记忆"""
    text = " ".join(
        item
        for item in [
            request.preferences or "",
            request.travelers.mobility_notes or "",
            " ".join(request.interests),
        ]
        if item
    )
    memories = extract_memory_from_request_text(text)
    if request.interests:
        memories.append(
            MemoryItem(
                key="interest.preference",
                value="、".join(request.interests),
                category="interest",
                source="request",
            )
        )
    return memories
