from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Protocol


class Business(Protocol):
    name: str
    phone_number: str | None
    source_url: str | None


class BusinessDiscoveryProvider(Protocol):
    """Plan §4.4: the brief requires showing where a real call list would
    come from, not that the demo's numbers be auto-discovered. Implement
    this once; swap providers without touching callers."""

    def search(self, vertical: str, location: str, limit: int) -> list[dict[str, Any]]: ...


class TavilyDiscoveryProvider:
    """P1 concrete implementation (plan §16). Requires TAVILY_API_KEY (not
    yet set as of this build). Returns a sample list with source URLs and
    retrieval timestamps -- never merged with private demo-persona phone
    numbers (those stay `source_type="demo_persona"` in app.db.Business)."""

    def search(self, vertical: str, location: str, limit: int = 10) -> list[dict[str, Any]]:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not set; cannot run business discovery")

        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        query = f"moving companies near {location}"
        result = client.search(query=query, max_results=limit)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        return [
            {
                "name": item.get("title"),
                "phone_number": None,
                "source_url": item.get("url"),
                "source_type": "discovered",
                "retrieved_at": retrieved_at,
            }
            for item in result.get("results", [])[:limit]
        ]
