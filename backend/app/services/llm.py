from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.models.travel import MemoryItem, TravelPlan, TravelPlanRequest


class LlmService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.dashscope_api_key)

    @lru_cache(maxsize=1)
    def chat_model(self) -> ChatOpenAI:
        if not self.settings.dashscope_api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")
        return ChatOpenAI(
            model=self.settings.qwen_model,
            api_key=self.settings.dashscope_api_key,
            base_url=self.settings.qwen_base_url,
            temperature=0.5,
        )

    async def chat(self, user: str, system: str = "你是专业旅行助手。", max_tokens: int = 2048) -> str | None:
        """普通文本对话，返回字符串"""
        if not self.enabled:
            return None
        try:
            model = self.chat_model()
            model.max_tokens = max_tokens
            response = await model.ainvoke([
                ("system", system),
                ("user", user),
            ])
            return str(response.content).strip()
        except Exception:
            return None

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.enabled:
            return {}
        response = await self.chat_model().ainvoke(
            [
                ("system", f"{system}\n只输出合法 JSON，不要 Markdown。"),
                ("user", user),
            ]
        )
        content = str(response.content).strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content.removeprefix("json").strip()
        return json.loads(content)

    async def adjustment_advice(
        self,
        plan: TravelPlan,
        instruction: str,
        memory_context: list[MemoryItem],
    ) -> dict[str, Any]:
        system = "你是旅行行程 JSON 修改助手，只提出安全、局部、可验证的修改建议。"
        user = json.dumps(
            {
                "plan": plan.model_dump(),
                "instruction": instruction,
                "memory_context": [item.model_dump() for item in memory_context],
                "output_schema": {
                    "summary": "string",
                    "changed_item_ids": ["string"],
                    "actions": ["add|remove|replace|reorder|relax|budget"],
                    "memory_candidates": [{"key": "string", "value": "string", "category": "string"}],
                },
            },
            ensure_ascii=False,
        )
        try:
            data = await self.generate_json(system, user)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    async def scenic_advice(self, request: TravelPlanRequest, rag_context: list[dict[str, Any]]) -> dict[str, Any]:
        system = "你是专业旅行规划师，擅长结合真实景点数据和游记片段生成可执行建议。"
        user = json.dumps(
            {
                "request": request.model_dump(),
                "rag_context": rag_context[:8],
                "output_schema": {
                    "themes": ["string"],
                    "pace_notes": "string",
                    "risk_notes": ["string"],
                    "must_see": ["string"],
                },
            },
            ensure_ascii=False,
        )
        try:
            return await self.generate_json(system, user)
        except Exception:
            return {}


def get_llm_service() -> LlmService:
    return LlmService(get_settings())
