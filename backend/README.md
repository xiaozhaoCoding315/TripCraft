# TripCraft Backend

FastAPI + LangGraph backend for collaborative multi-agent travel planning.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health
- WebSocket: `ws://localhost:8000/api/v1/plans/stream`

Secrets such as `DASHSCOPE_API_KEY` and `AMAP_API_KEY` must be configured through `.env` or environment variables.
