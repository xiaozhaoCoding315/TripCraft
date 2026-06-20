---
name: superpowers
description: Use a rigorous, high-leverage planning process for TripCraft architecture, project breakdown, implementation sequencing, and risk control.
---

# Superpowers

Use this skill when designing or planning meaningful TripCraft work before implementation.

## Operating mode

- Think as a senior full-stack architect and tech lead.
- Optimize for a shippable MVP first, then extensibility.
- Keep plans in the conversation unless the user explicitly asks for a file.
- Ask for authorization before making non-trivial code changes.
- Prefer concrete implementation steps over abstract strategy.

## Planning checklist

When invoked, produce a concise but actionable plan covering:

1. **Goal** — what outcome this iteration should deliver.
2. **Scope** — what is included and excluded.
3. **Architecture fit** — how the change fits TripCraft's FastAPI + React + LangGraph + Qdrant + Amap architecture.
4. **Data contracts** — request/response JSON, WebSocket events, or state shape affected.
5. **Implementation steps** — ordered backend/frontend/integration tasks.
6. **Validation** — tests, smoke checks, and manual verification steps.
7. **Risks** — API keys, external services, degraded modes, and assumptions.

## TripCraft defaults

- Backend: Python FastAPI.
- Frontend: React.
- Agent orchestration: LangGraph/LangChain.
- LLM: Qwen/DashScope via environment variables.
- Vector DB: Qdrant.
- Maps/POI/weather: Amap via environment variables.
- Planning flow: parallel information agents → itinerary agent → critic loop → final structured JSON.
- Use stable IDs and source labels in itinerary data so conversational edits can patch existing plans precisely.

## Output format

Return:

```markdown
## Plan
...

## Files likely to change
...

## Validation
...

## Approval needed
请确认是否按这个方案开始实现。
```
