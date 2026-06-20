from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.models.travel import RagDocument
from app.services.rag import TravelRagService


def load_documents(path: Path) -> list[RagDocument]:
    raw = path.read_text(encoding="utf-8")
    rows: list[dict[str, Any]]
    if path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        data = json.loads(raw)
        rows = data if isinstance(data, list) else data.get("documents", [])
    return [RagDocument.model_validate(row) for row in rows]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest TripCraft RAG documents into Qdrant")
    parser.add_argument("path", type=Path, help="JSON or JSONL file with documents")
    parser.add_argument("--city", required=True, help="City attached to documents")
    parser.add_argument("--collection", choices=["notes", "attractions"], default="notes")
    args = parser.parse_args()

    docs = load_documents(args.path)
    service = TravelRagService(get_settings())
    if args.collection == "notes":
        result = await service.ingest_notes(args.city, docs)
    else:
        result = await service.ingest_attractions(args.city, docs)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
