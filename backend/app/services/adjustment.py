"""
TripCraft Adjustment Service

行程调整服务，支持确定性规则 + LLM 辅助，可选流式进度回调。
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

from app.models.travel import (
    AgentProgressEvent,
    GeoPoint,
    ItineraryItem,
    MemoryItem,
    SourceRef,
    TravelPlan,
)
from app.services.llm import LlmService

ProgressSink = Callable[[AgentProgressEvent], Awaitable[None]]


class AdjustmentService:
    """行程调整服务"""

    def __init__(self, llm: LlmService | None = None, progress_sink: ProgressSink | None = None):
        self.llm = llm
        self.progress_sink = progress_sink

    async def _emit(self, agent: str, status: str, message: str) -> None:
        """发送进度事件"""
        if self.progress_sink:
            event = AgentProgressEvent(agent=agent, status=status, message=message)
            result = self.progress_sink(event)
            if isinstance(result, Awaitable):
                await result

    async def adjust(
        self,
        plan: TravelPlan,
        instruction: str,
        memory_context: list[MemoryItem] | None = None,
    ) -> tuple[TravelPlan, str, list[AgentProgressEvent], list[MemoryItem]]:
        """调整行程计划"""
        events: list[AgentProgressEvent] = []
        touched: list[str] = []

        await self._emit("orchestrator", "running", "正在解析对话式调整意图")

        # LLM 建议（如果可用）
        llm_patch = await self._safe_llm_patch(plan, instruction, memory_context or [])
        if llm_patch.get("summary"):
            await self._emit(
                "orchestrator",
                "success",
                f"AI 已生成调整建议，正在合并确定性规则",
            )

        # 确定性规则
        if any(word in instruction for word in ["慢", "轻松", "老人", "休息", "腿脚", "不赶"]):
            await self._emit("orchestrator", "running", "正在放慢节奏...")
            self._relax_plan(plan)
            touched.append("节奏已放慢，并增加休息时间")

        if any(word in instruction for word in ["预算", "便宜", "省钱", "降低费用", "少花"]):
            await self._emit("orchestrator", "running", "正在优化费用...")
            self._reduce_cost(plan)
            touched.append("住宿与总费用已按省钱偏好下调")

        add_match = re.search(r"(?:增加|加入|添加|想去)([^，。,；;\n]{2,24})", instruction)
        if add_match:
            title = add_match.group(1).strip()
            await self._emit("orchestrator", "running", f"正在添加 {title}...")
            self._add_place(plan, title)
            touched.append(f"已加入 {title}")

        avoid_match = re.search(r"(?:不要去|不去|避开)([^，。,；;\n]{2,24})", instruction)
        if avoid_match:
            keyword = avoid_match.group(1).strip()
            await self._emit("orchestrator", "running", f"正在避开 {keyword}...")
            removed = self._remove_matching(plan, keyword)
            touched.append(f"已避开 {keyword}，移除 {removed} 个相关项目")

        # 更新版本和费用
        plan.version += 1
        for day in plan.days:
            day.estimated_cost = sum(item.cost or 0 for item in day.items)
        plan.total_estimated_cost = sum(day.estimated_cost or 0 for day in plan.days)

        summary = "；".join(touched) if touched else "已记录调整诉求；当前版本先保留原行程，可继续指定要替换的景点/酒店。"
        memories = extract_memory_from_instruction(instruction)

        await self._emit("orchestrator", "success", summary)

        events.append(AgentProgressEvent(agent="orchestrator", status="success", message=summary))
        return plan, summary, events, memories

    async def _safe_llm_patch(
        self, plan: TravelPlan, instruction: str, memory_context: list[MemoryItem]
    ) -> dict[str, Any]:
        """安全调用 LLM 获取调整建议"""
        if not self.llm or not self.llm.enabled:
            return {}
        try:
            return await self.llm.adjustment_advice(plan, instruction, memory_context)
        except Exception:
            return {}

    @staticmethod
    def _relax_plan(plan: TravelPlan) -> None:
        """放慢行程节奏"""
        for day in plan.days:
            day.pace = "relaxed"
            if not any(item.id == f"adjust_rest_{day.day}" for item in day.items):
                insert_at = min(2, len(day.items))
                day.items.insert(
                    insert_at,
                    ItineraryItem(
                        id=f"adjust_rest_{day.day}",
                        time="15:30",
                        type="rest",
                        title="新增休息时间",
                        description="根据对话要求降低节奏，增加下午休息，避免连续步行过久。",
                        cost=0,
                        duration_minutes=60,
                        source_refs=[SourceRef(type="template", label="对话调整")],
                    ),
                )

    @staticmethod
    def _reduce_cost(plan: TravelPlan) -> None:
        """降低费用"""
        for day in plan.days:
            for item in day.items:
                if item.type == "hotel" and item.cost:
                    item.cost = round(item.cost * 0.8, 2)
                if item.type == "attraction" and item.cost:
                    item.cost = round(item.cost * 0.9, 2)

    @staticmethod
    def _add_place(plan: TravelPlan, title: str) -> None:
        """添加新景点，根据类型动态估算费用和时长"""
        if not plan.days:
            return
        # 根据关键词动态估算
        is_hotel = any(w in title for w in ["酒店", "宾馆", "民宿", "旅馆", "住宿"])
        is_restaurant = any(w in title for w in ["餐厅", "美食", "小吃", "火锅", "面馆", "饭店", "早餐", "午餐", "晚餐"])
        is_attraction = not is_hotel and not is_restaurant

        if is_hotel:
            cost = 300
            duration = 0
            item_type = "hotel"
        elif is_restaurant:
            cost = 80
            duration = 60
            item_type = "meal"
        else:
            cost = 50
            duration = 120
            item_type = "attraction"

        target = plan.days[0]
        target.items.insert(
            min(3, len(target.items)),
            ItineraryItem(
                id=f"adjust_add_{abs(hash(title)) % 100000}",
                time="16:30",
                type=item_type,
                title=title,
                description=f"根据用户对话新增的{item_type}，建议后续结合地图距离确认具体安排。",
                location=GeoPoint(address=plan.destination),
                cost=cost,
                duration_minutes=duration,
                source_refs=[SourceRef(type="llm", label="对话调整")],
            ),
        )

    @staticmethod
    def _remove_matching(plan: TravelPlan, keyword: str) -> int:
        """移除匹配的项目"""
        removed = 0
        for day in plan.days:
            before = len(day.items)
            day.items = [
                item for item in day.items if keyword not in item.title and keyword not in item.description
            ]
            removed += before - len(day.items)
        return removed


def extract_memory_from_request_text(text: str) -> list[MemoryItem]:
    """从请求文本中提取记忆"""
    return extract_memory_from_instruction(text, source="request")


def extract_memory_from_instruction(
    instruction: str, source: str = "adjustment"
) -> list[MemoryItem]:
    """从调整指令中提取偏好记忆"""
    memories: list[MemoryItem] = []
    if any(word in instruction for word in ["慢", "轻松", "休息", "不赶"]):
        memories.append(
            MemoryItem(key="pace.preference", value="偏好慢节奏、预留休息", category="pace", source=source)
        )
    if any(word in instruction for word in ["老人", "腿脚", "行动不便"]):
        memories.append(
            MemoryItem(
                key="traveler.mobility",
                value="同行人可能需要低强度、少换乘安排",
                category="traveler",
                source=source,
            )
        )
    if any(word in instruction for word in ["预算", "便宜", "省钱", "少花"]):
        memories.append(
            MemoryItem(
                key="budget.preference",
                value="预算敏感，优先控制住宿和门票成本",
                category="budget",
                source=source,
            )
        )
    if "地铁" in instruction and "酒店" in instruction:
        memories.append(
            MemoryItem(
                key="hotel.metro",
                value="酒店优先靠近地铁或公共交通",
                category="hotel",
                source=source,
            )
        )
    avoid_match = re.search(r"(?:不要去|不去|避开)([^，。,；;\n]{2,24})", instruction)
    if avoid_match:
        keyword = avoid_match.group(1).strip()
        memories.append(MemoryItem(key=f"avoid.{keyword}", value=keyword, category="avoid", source=source))
    return memories
