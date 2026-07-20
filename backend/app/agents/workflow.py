from __future__ import annotations

import asyncio
import json
import operator
from collections.abc import Awaitable, Callable, Coroutine
from datetime import date, timedelta
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import Settings, get_settings
from app.models.travel import (
    AgentProgressEvent,
    CriticComment,
    DayPlan,
    GeoPoint,
    ItineraryItem,
    MemoryItem,
    Revision,
    SourceRef,
    TravelPlan,
    TravelPlanRequest,
)
from app.services.amap import AmapPoi, AmapService
from app.services.geo_optimizer import geo_optimizer
from app.services.harness import ToolExecutor, ExecutorConfig, ToolResult, ToolStatus, CircuitBreaker
from app.services.llm import LlmService
from app.services.rag import TravelRagService

ProgressSink = Callable[[AgentProgressEvent], Awaitable[None]]


def merge_context(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {**left, **right}


class TravelState(TypedDict, total=False):
    request: TravelPlanRequest
    context: Annotated[dict[str, Any], merge_context]
    events: Annotated[list[AgentProgressEvent], operator.add]
    plan: TravelPlan
    revision_round: int
    critique: dict[str, Any]


class _WorkflowHarness:
    """为 Workflow Agent 定制的 Harness 执行器封装

    提供 api_call() 方法，统一处理超时、重试、降级。
    内部使用 ToolExecutor，预配置针对外部 API 的执行策略。
    """

    def __init__(self, settings: Settings):
        self._executor = ToolExecutor(ExecutorConfig(
            timeout_seconds=settings.harness_timeout or 10.0,
            max_retries=settings.harness_max_retries if hasattr(settings, "harness_max_retries") else 2,
            base_backoff_seconds=0.5,
            backoff_multiplier=2.0,
            circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_timeout=60.0),
        ))

    async def api_call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        args: tuple[Any, ...] = (),
        fallback: Callable[..., Any] | None = None,
        tool_name: str = "api",
        **kwargs: Any,
    ) -> ToolResult:
        """执行外部 API 调用（带容错）"""
        return await self._executor.execute(
            func,
            *args,
            fallback=fallback,
            fallback_args=None,
            tool_name=tool_name,
            **kwargs,
        )


class TravelPlannerWorkflow:
    def __init__(self, settings: Settings | None = None, progress_sink: ProgressSink | None = None):
        self.settings = settings or get_settings()
        self.progress_sink = progress_sink
        self.amap = AmapService(self.settings)
        self.rag = TravelRagService(self.settings)
        self.llm = LlmService(self.settings)
        # Harness 容错执行引擎（API 调用统一入口：超时+重试+熔断+降级）
        self._harness = _WorkflowHarness(settings=self.settings)
        self.graph = self._build_graph()

    async def plan(
        self,
        request: TravelPlanRequest,
        memory_context: list[MemoryItem] | None = None,
    ) -> tuple[TravelPlan, list[AgentProgressEvent]]:
        initial: TravelState = {
            "request": request,
            "context": {"memory": [item.model_dump() for item in (memory_context or [])]},
            "events": [],
            "revision_round": 0,
            "critique": {},
        }
        result = await self.graph.ainvoke(initial)
        return result["plan"], result.get("events", [])

    def _build_graph(self):
        graph = StateGraph(TravelState)
        graph.add_node("weather", self._weather_agent)
        graph.add_node("transport", self._transport_agent)
        graph.add_node("accommodation", self._accommodation_agent)
        graph.add_node("attraction", self._attraction_agent)
        graph.add_node("itinerary", self._itinerary_agent)
        graph.add_node("critic", self._critic_agent)

        graph.add_edge(START, "weather")
        graph.add_edge(START, "transport")
        graph.add_edge(START, "accommodation")
        graph.add_edge(START, "attraction")
        graph.add_edge("weather", "itinerary")
        graph.add_edge("transport", "itinerary")
        graph.add_edge("accommodation", "itinerary")
        graph.add_edge("attraction", "itinerary")
        graph.add_edge("itinerary", "critic")
        graph.add_conditional_edges("critic", self._after_critic, {"retry": "itinerary", "done": END})
        return graph.compile()

    async def _emit(self, agent: str, status: str, message: str, payload: dict[str, Any] | None = None) -> AgentProgressEvent:
        event = AgentProgressEvent(agent=agent, status=status, message=message, payload=payload or {})
        if self.progress_sink:
            result = self.progress_sink(event)
            if asyncio.iscoroutine(result):
                await result
        return event

    async def _weather_agent(self, state: TravelState) -> TravelState:
        request = state["request"]
        events = [await self._emit("weather", "running", f"查询 {request.destination} 天气")]

        # 使用 Harness 容错执行引擎：超时 + 重试 + 降级
        weather_result = await self._harness.api_call(
            func=self.amap.weather,
            args=(request.destination,),
            fallback=lambda: {
                "city": request.destination,
                "casts": [],
                "fallback": True,
            },
            tool_name="weather",
        )

        if weather_result.success:
            weather = weather_result.data
            summary = self._summarize_weather(weather)
            events.append(await self._emit("weather", "success", summary, {"weather": weather}))
        else:
            weather = {"city": request.destination, "casts": [], "fallback": True}
            summary = "天气服务暂不可用，行程将保留室内/机动备选。"
            events.append(await self._emit("weather", "error", summary, {"error": weather_result.error}))

        return {"context": {"weather": weather, "weather_summary": summary}, "events": events}

    async def _transport_agent(self, state: TravelState) -> TravelState:
        request = state["request"]
        events = [await self._emit("transport", "running", "生成城际与市内交通建议")]
        departure = request.departure_city or "出发地"
        transport = {
            "arrival": f"建议从{departure}乘坐高铁/飞机抵达{request.destination}，优先选择上午到达班次。",
            "local": "市内以地铁/网约车为主；老人或腿脚不便时减少换乘，单日跨区不超过 2 次。",
            "source": "transport_template",
        }
        events.append(await self._emit("transport", "success", "交通模板已生成", transport))
        return {"context": {"transport": transport}, "events": events}

    async def _accommodation_agent(self, state: TravelState) -> TravelState:
        request = state["request"]
        events = [await self._emit("accommodation", "running", "检索酒店 POI")]

        # 使用 Harness 容错执行引擎：重试 + 降级
        async def _fetch_hotels():
            hotels = await self.amap.search_pois(request.destination, "酒店", "100000", offset=8)
            return hotels or self.amap.fallback_pois(request.destination, "hotel")

        hotels_result = await self._harness.api_call(
            func=_fetch_hotels,
            fallback=lambda: self.amap.fallback_pois(request.destination, "hotel"),
            tool_name="accommodation",
        )

        hotels = hotels_result.data if hotels_result.success else self.amap.fallback_pois(request.destination, "hotel")
        status = "success" if hotels_result.source == "primary" else "warning"
        events.append(await self._emit("accommodation", status, f"找到 {len(hotels)} 个住宿候选"))

        return {"context": {"hotels": [hotel.__dict__ for hotel in hotels]}, "events": events}

    async def _attraction_agent(self, state: TravelState) -> TravelState:
        request = state["request"]
        events = [await self._emit("attraction", "running", "检索景点 POI 与游记 RAG（竞速模式）")]
        memory_terms = " ".join(item.get("value", "") for item in state.get("context", {}).get("memory", []))
        query = " ".join(request.interests + ([memory_terms] if memory_terms else [])) or "经典景点"

        # 竞速策略：高德 POI API 与 Qdrant RAG 并发检索，取最快返回结果
        pois_task = asyncio.create_task(self._safe_search_attractions(request.destination, query))
        notes_task = asyncio.create_task(self.rag.search_notes(request.destination, query))

        pois: list[AmapPoi] = []
        notes: list[dict[str, Any]] = []
        done, pending = await asyncio.wait(
            {pois_task, notes_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        # 处理已完成的任务
        for task in done:
            try:
                result = task.result()
                if task is pois_task:
                    pois = result
                else:
                    notes = result
            except Exception as exc:
                events.append(await self._emit("attraction", "warning", f"竞速路径异常: {str(exc)[:50]}"))

        # 等待剩余任务（给予额外超时）
        if pending:
            try:
                extra_done, still_pending = await asyncio.wait(pending, timeout=10.0)
                for task in extra_done:
                    try:
                        result = task.result()
                        if task is pois_task:
                            pois = result
                        else:
                            notes = result
                    except Exception as exc:
                        events.append(await self._emit("attraction", "warning", f"补全路径异常: {str(exc)[:50]}"))
                if still_pending:
                    events.append(await self._emit("attraction", "warning", "慢路径超时，使用已竞速结果"))
            except asyncio.TimeoutError:
                events.append(await self._emit("attraction", "warning", "慢路径超时，使用已竞速结果"))

        # 确保兜底数据可用（任一路径失败或超时都降级到本地兜底）
        if not pois:
            pois = self.amap.fallback_pois(request.destination, "attraction")
        if not notes:
            notes = self.rag.fallback_notes(request.destination, query)

        advice = await self.llm.scenic_advice(request, notes)
        events.append(
            await self._emit(
                "attraction",
                "success",
                f"整理 {len(pois)} 个景点候选和 {len(notes)} 条游记片段",
                {"advice": advice},
            )
        )
        return {
            "context": {
                "attractions": [poi.__dict__ for poi in pois],
                "rag_notes": notes,
                "scenic_advice": advice,
            },
            "events": events,
        }

    async def _safe_search_attractions(self, city: str, query: str) -> list[AmapPoi]:
        try:
            pois = await self.amap.search_pois(city, query, "110000", offset=12)
            return pois or self.amap.fallback_pois(city, "attraction")
        except Exception:
            return self.amap.fallback_pois(city, "attraction")

    async def _itinerary_agent(self, state: TravelState) -> TravelState:
        request = state["request"]
        round_no = state.get("revision_round", 0) + 1
        events = [await self._emit("itinerary", "running", f"AI 正在智能编排第 {round_no} 版行程...")]

        # Try LLM-powered generation first
        try:
            if self.llm.enabled:
                plan = await self._compose_plan_with_llm(request, state.get("context", {}), round_no, state.get("critique", {}))
                events.append(await self._emit("itinerary", "success", f"✅ AI 已生成第 {round_no} 版智能行程", {"plan_id": plan.plan_id}))
            else:
                # Fallback to template-based generation
                plan = self._compose_plan(request, state.get("context", {}), round_no, state.get("critique", {}))
                events.append(await self._emit("itinerary", "success", f"第 {round_no} 版行程已生成（模板模式）", {"plan_id": plan.plan_id}))
        except Exception as exc:
            # Fallback to template on LLM failure
            plan = self._compose_plan(request, state.get("context", {}), round_no, state.get("critique", {}))
            events.append(await self._emit("itinerary", "warning", f"LLM 生成失败，使用模板降级: {str(exc)[:50]}", {"plan_id": plan.plan_id}))

        # Post-process: geocode itinerary locations that lack coordinates
        events.append(await self._emit("itinerary", "running", "正在为行程地点获取地图坐标..."))
        resolved, total = await self._geocode_itinerary_locations(plan)
        events.append(await self._emit("itinerary", "success", f"已获取 {resolved}/{total} 个地点坐标"))

        return {"plan": plan, "revision_round": round_no, "events": events}

    async def _critic_agent(self, state: TravelState) -> TravelState:
        plan = state["plan"]
        request = state["request"]
        round_no = state.get("revision_round", 1)
        events = [await self._emit("critic", "running", "从体力、时间、预算、天气维度审查行程")]
        comments = self._review_plan(plan, request)
        passed = not any(comment.severity == "critical" for comment in comments) or round_no >= self.settings.max_critic_rounds
        revision = Revision(
            version=round_no,
            passed=passed,
            comments=comments,
            summary="审查通过" if passed else "发现需要调整的问题，返回 Itinerary Agent 重新编排",
        )
        plan.revisions.append(revision)
        plan.version = round_no
        status = "success" if passed else "retrying"
        message = "Critic 审查通过" if passed else "Critic 要求重新编排"
        events.append(await self._emit("critic", status, message, {"comments": [item.model_dump() for item in comments]}))
        return {"plan": plan, "critique": {"comments": [item.model_dump() for item in comments]}, "events": events}

    def _after_critic(self, state: TravelState) -> str:
        plan = state["plan"]
        if plan.revisions and plan.revisions[-1].passed:
            return "done"
        if state.get("revision_round", 1) >= self.settings.max_critic_rounds:
            return "done"
        return "retry"

    async def _compose_plan_with_llm(
        self,
        request: TravelPlanRequest,
        context: dict[str, Any],
        version: int,
        critique: dict[str, Any],
    ) -> TravelPlan:
        """使用 LLM 智能生成行程"""
        attractions = context.get("attractions") or [poi.__dict__ for poi in self.amap.fallback_pois(request.destination, "attraction")]
        hotels = context.get("hotels") or [poi.__dict__ for poi in self.amap.fallback_pois(request.destination, "hotel")]
        weather = context.get("weather", {})
        rag_notes = context.get("rag_notes", [])
        memory = context.get("memory", [])
        scenic_advice = context.get("scenic_advice", {})

        # Build intelligent prompt
        system = """你是专业的旅行规划师，擅长根据用户需求、天气、景点数据和用户偏好生成个性化行程。

你的职责：
1. 智能分配每日景点，考虑地理位置聚类（相近景点安排在同一天）
2. 根据用户特征调整节奏（老人/行动不便者减少景点、增加休息）
3. 结合天气预报调整室内外活动，不同日期如果天气差异大应安排不同类型的活动
4. 参考游记RAG数据添加实用建议
5. 控制总预算在用户范围内
6. 优化路线减少折返

【重要规则】
- 去重：不同天不能推荐完全相同的景点，每个景点最多出现一次
- 每日天气应对：如果某些天有雨，优先安排室内景点；晴天才安排户外
- 如果提供了previous_critique（审查意见），你必须针对每个批评点做出修改。例如：
  * "体力消耗过大" → 减少该天景点数、增加休息
  * "预算超支" → 替换为更便宜的酒店/餐厅
  * "天气不适合户外" → 把户外景点换到天气好的那天
  * "地点之间距离太远" → 重新按地理位置聚类
  不要忽略任何审查意见！

输出格式必须是合法JSON，包含完整的行程规划。

输出格式示例：
{
  "itinerary": [
    {
      "day": 1,
      "title": "第一天标题",
      "activities": [
        {
          "time": "09:00-12:00",
          "activity": "活动名称",
          "details": "详细描述",
          "location": "地点",
          "cost": 100
        }
      ]
    }
  ],
  "total_estimated_cost": 2000
}

注意：每个activity必须包含cost字段（数值，单位：元）。"""

        user_context = {
            "request": {
                "destination": request.destination,
                "departure_city": request.departure_city,
                "start_date": request.start_date,
                "days": request.days,
                "budget": request.budget,
                "travelers": request.travelers.model_dump(),
                "interests": request.interests,
                "preferences": request.preferences,
            },
            "weather_summary": context.get("weather_summary", ""),
            "weather_data": weather,
            "available_attractions": [
                {
                    "name": a.get("name", ""),
                    "address": a.get("address", ""),
                    "type": a.get("type", ""),
                    "location": a.get("location", [None, None]),
                }
                for a in attractions[:15]  # Limit to prevent prompt too long
            ],
            "available_hotels": [
                {"name": h.get("name", ""), "address": h.get("address", "")}
                for h in hotels[:5]
            ],
            "rag_notes": [{"text": n.get("text", "")[:200]} for n in rag_notes[:5]],
            "user_memory": [item.get("value", "") for item in memory],
            "scenic_advice": scenic_advice,
            "previous_critique": critique.get("comments", []) if critique else [],
            "version": version,
        }

        user = json.dumps(user_context, ensure_ascii=False)

        # Call LLM
        response = await self.llm.chat_model().ainvoke(
            [
                ("system", system + "\n只输出合法JSON，不要Markdown代码块。"),
                ("user", user),
            ]
        )

        content = str(response.content).strip()
        if content.startswith("```"):
            content = content.strip("`").removeprefix("json").strip()

        plan_data = json.loads(content)

        # Convert LLM response to TravelPlan
        return self._parse_llm_plan(plan_data, request, context, version)

    def _parse_llm_plan(
        self,
        plan_data: dict[str, Any],
        request: TravelPlanRequest,
        context: dict[str, Any],
        version: int,
    ) -> TravelPlan:
        """解析LLM返回的JSON为TravelPlan对象"""
        days = []
        start = self._safe_date(request.start_date)
        weather_data = context.get("weather", {})
        optimize_routes = context.get("optimize_routes", True)

        # Handle different LLM response formats
        # Format 1: {"days": [{"day": 1, "items": [...]}]}
        # Format 2: {"itinerary": [{"day": 1, "activities": [...]}]}
        raw_days = plan_data.get("days") or plan_data.get("itinerary") or []

        for day_data in raw_days:
            day_num = day_data.get("day", len(days) + 1)
            items = []

            # Handle both "items" and "activities" formats
            raw_items = day_data.get("items") or day_data.get("activities") or []

            for idx, item_data in enumerate(raw_items):
                # Skip if item_data is not a dict
                if not isinstance(item_data, dict):
                    continue

                # Determine item type based on content or position
                item_type = self._infer_item_type(item_data, idx, len(raw_items))

                # Handle different field names from LLM
                title = (
                    item_data.get("title")
                    or item_data.get("name")
                    or item_data.get("activity", f"Activity {idx + 1}")
                )

                # Get description from various possible fields
                description = (
                    item_data.get("description")
                    or item_data.get("details", "")
                )

                # Parse time - handle "09:00-12:00" format
                time_str = item_data.get("time", self._get_default_time(idx))
                if "-" in time_str:
                    time_str = time_str.split("-")[0]

                # Parse cost - check budget_estimate as well
                cost = item_data.get("cost") or item_data.get("budget_estimate", 0)

                # Parse location - can be string or dict
                loc = item_data.get("location")
                address = None
                lng = None
                lat = None
                if isinstance(loc, str):
                    address = loc
                elif isinstance(loc, dict):
                    address = loc.get("address")
                    lng = loc.get("lng")
                    lat = loc.get("lat")

                item = ItineraryItem(
                    time=time_str,
                    type=item_type,
                    title=title,
                    description=description,
                    duration_minutes=item_data.get("duration_minutes", 120),
                    cost=cost,
                    location=GeoPoint(lng=lng, lat=lat, address=address),
                    source_refs=[
                        SourceRef(type="llm", label="AI智能规划"),
                        SourceRef(type="amap", label="高德POI"),
                    ],
                )
                items.append(item)

            # Optimize route if enabled and items have coordinates
            if optimize_routes:
                items = geo_optimizer.optimize_day_route(items)

            day = DayPlan(
                day=day_num,
                date=(start + timedelta(days=day_num - 1)).isoformat() if start else None,
                title=day_data.get("title", f"第 {day_num} 天 · {request.destination}探索"),
                weather_summary=day_data.get("weather_summary"),
                items=items,
                estimated_cost=sum(item.cost or 0 for item in items),
                pace=day_data.get("pace", "balanced"),
            )
            days.append(day)

        total = sum(day.estimated_cost or 0 for day in days)

        return TravelPlan(
            destination=request.destination,
            version=version,
            days=days,
            total_estimated_cost=total,
            raw_context={
                "weather": weather_data,
                "weather_summary": context.get("weather_summary", ""),
                "scenic_advice": context.get("scenic_advice"),
                "llm_plan": plan_data,
                "rag_notes_count": len(context.get("rag_notes", [])),
            },
        )

    async def _geocode_itinerary_locations(self, plan: TravelPlan) -> tuple[int, int]:
        """Post-process: geocode itinerary items that have addresses but no coordinates.

        Returns (resolved_count, total_count) for progress reporting.
        """
        # Collect items that need geocoding
        items_to_geocode: list[tuple[int, int, ItineraryItem]] = []  # (day_idx, item_idx, item)
        for day in plan.days:
            for item in day.items:
                has_address = bool(item.location and item.location.address)
                has_coords = bool(item.location and item.location.lng and item.location.lat)
                if has_address and not has_coords:
                    items_to_geocode.append((day.day - 1, day.items.index(item), item))

        total = len(items_to_geocode)
        if total == 0:
            return 0, 0

        resolved = 0

        async def geocode_one(day_idx: int, item_idx: int, item: ItineraryItem) -> bool:
            address = item.location.address if item.location else None
            if not address:
                return False
            try:
                # 使用城市+地址组合提高命中率
                lng, lat = await self.amap.geocode_address(address, plan.destination)
                if lng is not None and lat is not None:
                    plan.days[day_idx].items[item_idx].location.lng = lng
                    plan.days[day_idx].items[item_idx].location.lat = lat
                    return True
            except Exception:
                pass
            return False

        # Concurrent geocoding with limited concurrency
        semaphore = asyncio.Semaphore(5)

        async def geocode_with_limit(day_idx: int, item_idx: int, item: ItineraryItem) -> bool:
            async with semaphore:
                return await geocode_one(day_idx, item_idx, item)

        results = await asyncio.gather(
            *[geocode_with_limit(d, i, item) for d, i, item in items_to_geocode],
            return_exceptions=True,
        )
        resolved = sum(1 for r in results if r is True)
        return resolved, total

    @staticmethod
    def _infer_item_type(item_data: dict, index: int, total: int) -> str:
        """根据内容推断活动类型"""
        title = str(item_data.get("title", "")).lower()
        desc = str(item_data.get("description", "")).lower()

        # Check for hotel keywords
        if any(kw in title for kw in ["酒店", "住宿", "hotel"]):
            return "hotel"

        # Check for transport keywords
        if any(kw in title for kw in ["交通", "出发", "抵达", "transport"]):
            return "transport"

        # Check for meal keywords
        if any(kw in title for kw in ["餐", "美食", "吃", "meal", "lunch", "dinner"]):
            return "meal"

        # Check for rest keywords
        if any(kw in title for kw in ["休息", "自由", "rest"]):
            return "rest"

        # Last item is often hotel
        if index == total - 1:
            return "hotel"

        # Default to attraction
        return "attraction"

    @staticmethod
    def _get_default_time(index: int) -> str:
        """根据索引返回默认时间"""
        times = ["09:00", "10:30", "12:00", "14:00", "16:00", "18:00", "20:00"]
        if index < len(times):
            return times[index]
        return f"{(9 + index) % 24:02d}:00"

    def _compose_plan(
        self,
        request: TravelPlanRequest,
        context: dict[str, Any],
        version: int,
        critique: dict[str, Any],
    ) -> TravelPlan:
        attractions = context.get("attractions") or [poi.__dict__ for poi in self.amap.fallback_pois(request.destination, "attraction")]
        hotels = context.get("hotels") or [poi.__dict__ for poi in self.amap.fallback_pois(request.destination, "hotel")]
        weather_summary = context.get("weather_summary")
        memory = context.get("memory", [])
        memory_text = " ".join(item.get("value", "") for item in memory)
        relaxed = (
            request.travelers.seniors > 0
            or bool(request.travelers.mobility_notes)
            or any(word in memory_text for word in ["慢节奏", "休息", "低强度", "少换乘"])
        )
        budget_sensitive = any(word in memory_text for word in ["预算敏感", "省钱", "控制"])
        max_spots = 2 if relaxed or version > 1 else 3
        days: list[DayPlan] = []
        start = self._safe_date(request.start_date)
        for day in range(1, request.days + 1):
            day_attractions = [attractions[(day + idx - 1) % len(attractions)] for idx in range(min(max_spots, len(attractions)))]
            items: list[ItineraryItem] = [
                ItineraryItem(
                    time="09:00",
                    type="transport",
                    title="从酒店出发",
                    description=context.get("transport", {}).get("local", "根据距离选择地铁/网约车出行。"),
                    duration_minutes=40,
                    source_refs=[SourceRef(type="template", label="交通常识模板")],
                )
            ]
            cursor_hour = 10
            for poi in day_attractions:
                lng, lat = poi.get("location", (None, None))
                items.append(
                    ItineraryItem(
                        time=f"{cursor_hour:02d}:00",
                        type="attraction",
                        title=poi.get("name", "推荐景点"),
                        description=self._poi_description(poi, context),
                        location=GeoPoint(lng=lng, lat=lat, address=poi.get("address")),
                        cost=40 if budget_sensitive else 60,
                        duration_minutes=120 if relaxed else 100,
                        source_refs=[SourceRef(type="amap", label="高德 POI"), SourceRef(type="rag", label="游记 RAG")],
                    )
                )
                cursor_hour += 3
                items.append(
                    ItineraryItem(
                        time=f"{cursor_hour:02d}:00",
                        type="rest" if relaxed else "meal",
                        title="休息与用餐",
                        description="预留补给和休息时间，避免连续步行过久。" if relaxed else "选择附近本地餐饮，控制用餐和转场时间。",
                        cost=80,
                        duration_minutes=80,
                        source_refs=[SourceRef(type="template", label="节奏控制模板")],
                    )
                )
                cursor_hour += 2
            hotel = hotels[(day - 1) % len(hotels)]
            lng, lat = hotel.get("location", (None, None))
            items.append(
                ItineraryItem(
                    time="20:00",
                    type="hotel",
                    title=hotel.get("name", "推荐酒店"),
                    description="优先选择交通便利、评分稳定、靠近次日活动区域的住宿。",
                    location=GeoPoint(lng=lng, lat=lat, address=hotel.get("address")),
                    cost=300 if budget_sensitive else 380,
                    source_refs=[SourceRef(type="amap", label="高德酒店 POI")],
                )
            )
            days.append(
                DayPlan(
                    day=day,
                    date=(start + timedelta(days=day - 1)).isoformat() if start else None,
                    title=f"第 {day} 天 · {request.destination}探索",
                    weather_summary=weather_summary,
                    items=items,
                    estimated_cost=sum(item.cost or 0 for item in items),
                    pace="relaxed" if relaxed else "balanced",
                )
            )
        total = sum(day.estimated_cost or 0 for day in days)
        return TravelPlan(
            destination=request.destination,
            version=version,
            days=days,
            total_estimated_cost=total,
            raw_context={
                "weather": context.get("weather"),
                "scenic_advice": context.get("scenic_advice"),
                "critique": critique,
                "memory": memory,
            },
        )

    def _review_plan(self, plan: TravelPlan, request: TravelPlanRequest) -> list[CriticComment]:
        comments: list[CriticComment] = []

        # Get weather data from raw_context
        raw_context = plan.raw_context or {}
        weather_data = raw_context.get("weather", {})
        weather_summary = raw_context.get("weather_summary", "")

        # Analyze weather conditions
        weather_analysis = self._analyze_weather_for_plan(weather_data, plan)

        for day in plan.days:
            attractions = [item for item in day.items if item.type == "attraction"]

            # Physical strain check
            if request.travelers.seniors > 0 and len(attractions) > 2:
                comments.append(
                    CriticComment(
                        dimension="physical",
                        severity="critical",
                        message=f"第 {day.day} 天景点数量偏多，不适合老人或行动不便人群。",
                        suggestion="减少到 1-2 个核心景点并增加休息。",
                    )
                )

            # Time check
            if sum(item.duration_minutes or 0 for item in day.items) > 720:
                comments.append(
                    CriticComment(
                        dimension="time",
                        severity="warning",
                        message=f"第 {day.day} 天活动时长较长。",
                        suggestion="压缩转场或加入机动时间。",
                    )
                )

            # Weather suitability check
            day_weather = weather_analysis.get(day.day, {})
            if day_weather.get("has_rain"):
                outdoor_attractions = [a for a in attractions if self._is_outdoor_attraction(a)]
                if outdoor_attractions:
                    comments.append(
                        CriticComment(
                            dimension="weather",
                            severity="warning",
                            message=f"第 {day.day} 天预报有雨（{day_weather.get('weather', '雨天')}），"
                                    f"但包含 {len(outdoor_attractions)} 个户外景点"
                                    f"（{', '.join(a.title for a in outdoor_attractions[:2])}）。",
                            suggestion="建议：1) 携带雨具；2) 准备室内备选方案（博物馆、商场）；"
                                      "3) 调整户外景点到室内景点。",
                        )
                    )

            # Check for extreme weather
            if day_weather.get("is_extreme"):
                comments.append(
                    CriticComment(
                        dimension="weather",
                        severity="critical",
                        message=f"第 {day.day} 天天气预报有极端天气（{day_weather.get('weather', '')}，"
                                f"{day_weather.get('temperature', '')}），不适合户外活动。",
                        suggestion="强烈建议调整此日行程，改为室内活动或休息日。",
                    )
                )

        # Budget check
        if request.budget and plan.total_estimated_cost and plan.total_estimated_cost > request.budget:
            comments.append(
                CriticComment(
                    dimension="budget",
                    severity="critical",
                    message="预计费用超过预算。",
                    suggestion="降低住宿标准或减少付费景点。",
                )
            )

        # Overall weather summary
        if weather_analysis.get("overall_rain_days", 0) > len(plan.days) / 2:
            comments.append(
                CriticComment(
                    dimension="weather",
                    severity="info",
                    message=f"行程期间有 {weather_analysis['overall_rain_days']} 天预报有雨，"
                            f"建议整体增加室内活动比例。",
                    suggestion="考虑增加博物馆、商场、室内娱乐等备选方案。",
                )
            )

        if not comments:
            comments.append(CriticComment(dimension="overall", message="行程节奏、预算和天气适配性基本合理。"))
        return comments

    def _analyze_weather_for_plan(self, weather_data: dict, plan: TravelPlan) -> dict[int, dict]:
        """Analyze weather data for each day of the plan"""
        result = {}
        casts = weather_data.get("casts", [])

        for day in plan.days:
            day_index = day.day - 1
            if day_index < len(casts):
                cast = casts[day_index]
                weather = cast.get("dayweather", "")
                night_temp = cast.get("nighttemp", "")
                day_temp = cast.get("daytemp", "")

                # Determine if rainy
                rain_keywords = ["雨", "雪", "雷暴", "暴雨", "大雪"]
                has_rain = any(keyword in weather for keyword in rain_keywords)

                # Determine if extreme weather
                extreme_keywords = ["暴雪", "台风", "暴雨", "高温", "寒潮"]
                is_extreme = any(keyword in weather for keyword in extreme_keywords)

                # Temperature check
                try:
                    temp = int(day_temp) if day_temp else 20
                    if temp > 35 or temp < -5:
                        is_extreme = True
                except ValueError:
                    pass

                result[day.day] = {
                    "weather": weather,
                    "temperature": f"{night_temp}~{day_temp}℃" if night_temp and day_temp else "未知",
                    "has_rain": has_rain,
                    "is_extreme": is_extreme,
                }

        # Count rain days
        rain_days = sum(1 for d in result.values() if d.get("has_rain"))
        result["overall_rain_days"] = rain_days

        return result

    @staticmethod
    def _is_outdoor_attraction(item: ItineraryItem) -> bool:
        """Determine if an attraction is primarily outdoor"""
        outdoor_keywords = ["公园", "山", "湖", "海", "古镇", "寺庙", "塔", "遗址", "湿地", "森林"]
        indoor_keywords = ["博物馆", "商场", "室内", "剧院", "美术馆"]

        title_lower = item.title.lower()
        desc_lower = item.description.lower()

        # Check if explicitly indoor
        for keyword in indoor_keywords:
            if keyword in title_lower or keyword in desc_lower:
                return False

        # Check if outdoor
        for keyword in outdoor_keywords:
            if keyword in title_lower or keyword in desc_lower:
                return True

        # Default to outdoor for unknown types
        return item.type == "attraction"

    @staticmethod
    def _summarize_weather(weather: dict[str, Any]) -> str:
        casts = weather.get("casts") or []
        if not casts:
            return "未获取到天气预报，建议出发前再次确认。"
        first = casts[0]
        return f"{weather.get('city', '')}近期天气：{first.get('dayweather', '未知')}，{first.get('nighttemp', '')}-{first.get('daytemp', '')}℃。"

    @staticmethod
    def _poi_description(poi: dict[str, Any], context: dict[str, Any]) -> str:
        advice = context.get("scenic_advice") or {}
        notes = context.get("rag_notes") or []
        note = notes[0].get("text") if notes else "结合真实 POI 数据安排游玩。"
        pace = advice.get("pace_notes") if isinstance(advice, dict) else None
        return f"{note} {pace or '建议提前确认开放时间并错峰出行。'}"

    @staticmethod
    def _safe_date(value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
