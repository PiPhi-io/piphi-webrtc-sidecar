from __future__ import annotations

import httpx
from fastapi import APIRouter

from ..contract import ENDPOINTS, REQUIRED_ENDPOINTS
from ..go2rtc import Go2RtcError, go2rtc
from ..settings import PROJECT_KIND
from ..state import registry, starter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    upstream_available = True
    upstream_version = None
    try:
        upstream = await go2rtc.health()
        upstream_version = upstream.get("version")
    except (Go2RtcError, httpx.HTTPError, ValueError):
        upstream_available = False
    return starter.health_response(
        metadata={
            "active_configs": len(registry.ids()),
            "status": "healthy" if upstream_available else "degraded",
            "go2rtc_available": upstream_available,
            "go2rtc_version": upstream_version,
        },
    )


@router.get("/diagnostics")
async def diagnostics():
    return starter.diagnostics_response(
        diagnostics={
            "active_config_ids": registry.ids(),
            "recent_event_count": len(registry.recent_events),
            "kind": PROJECT_KIND,
            "go2rtc_control_plane": "loopback-only",
            "contract": {
                "endpoints": ENDPOINTS,
                "required": REQUIRED_ENDPOINTS,
            },
        }
    )
