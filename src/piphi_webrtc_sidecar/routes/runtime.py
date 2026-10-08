from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..contract import ENDPOINTS, REQUIRED_ENDPOINTS
from ..settings import (
    INTEGRATION_ID,
    INTEGRATION_NAME,
    INTEGRATION_VERSION,
    PROJECT_DOMAIN,
    PROJECT_KIND,
    PROJECT_PRESET,
)
from ..state import registry, starter

router = APIRouter(tags=["runtime"])


@router.get("/state")
async def state(
    refresh: bool = Query(default=False),
    refresh_request_id: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        state_payload = await starter.state.response(
            refresh=refresh,
            refresh_request_id=refresh_request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    public_entries = [
        {
            "config_id": entry["config_id"],
            "device_id": entry["device_id"],
            "alias": entry.get("alias"),
            "stream_name": entry.get("stream_name"),
            "source_scheme": entry.get("source_scheme"),
        }
        for entry in registry.entries.values()
    ]
    return {
        **state_payload,
        "summary": {
            "active_config_count": len(registry.ids()),
            "recent_event_count": len(registry.recent_events),
        },
        "entries": public_entries,
        "state_snapshots": registry.state_snapshots,
    }


@router.get("/contract")
async def contract() -> dict[str, Any]:
    return {
        "integration_id": INTEGRATION_ID,
        "name": INTEGRATION_NAME,
        "version": INTEGRATION_VERSION,
        "kind": PROJECT_KIND,
        "preset": PROJECT_PRESET,
        "domain": PROJECT_DOMAIN,
        "endpoints": ENDPOINTS,
        "required": REQUIRED_ENDPOINTS,
    }
