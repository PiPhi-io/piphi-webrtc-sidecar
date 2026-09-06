from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from piphi_runtime_kit_python.fastapi import dispatch_automation_action_from_fastapi

from ..go2rtc import Go2RtcError, go2rtc
from ..state import automations, commands, get_entry_or_404, registry

router = APIRouter(tags=["commands"])


@router.post("/command")
async def command(payload: dict[str, Any], request: Request):
    command_name = str(payload.get("command") or payload.get("capability_id") or "").strip()
    if not command_name:
        raise HTTPException(status_code=400, detail="Missing command")
    if command_name not in commands:
        raise HTTPException(status_code=400, detail=f"Unsupported command: {command_name}")

    target = payload.get("target") if isinstance(payload.get("target"), dict) else {}
    device_id = str(payload.get("device_id") or target.get("device_id") or "camera")
    config_id = str(payload.get("config_id") or target.get("config_id") or device_id)
    requirements = payload.get("capability_requirements")
    requested_capabilities = [
        str(item).strip()
        for item in (
            [payload.get("capability")] + (requirements if isinstance(requirements, list) else [])
        )
        if str(item or "").strip()
    ]
    unsupported_capability = next(
        (
            capability
            for capability in requested_capabilities
            if capability not in {"device.refresh", f"action.{command_name}"}
        ),
        None,
    )
    if unsupported_capability:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": "unsupported_capability",
                "message": f"This runtime does not support capability {unsupported_capability}",
            },
        )
    entry = get_entry_or_404(config_id)
    try:
        await go2rtc.health()
    except (Go2RtcError, httpx.HTTPError) as exc:
        registry.update_state(
            config_id,
            {"connected": False, "service_available": False},
            device_id=str(entry["device_id"]),
        )
        raise HTTPException(status_code=502, detail="camera service is unavailable") from exc
    registry.update_state(
        config_id,
        {"connected": True, "service_available": True},
        device_id=str(entry["device_id"]),
    )
    result = await dispatch_automation_action_from_fastapi(
        automations,
        request,
        {
            **payload,
            "command": command_name,
            "args": payload.get("params") or payload.get("args") or {},
            "device_id": device_id,
            "config_id": config_id,
            "target": target,
        },
    )
    response = result.model_dump(mode="json")
    if result.ok:
        response.update(result.result)
    return response
