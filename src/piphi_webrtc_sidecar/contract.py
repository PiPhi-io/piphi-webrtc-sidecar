from __future__ import annotations

from typing import Any

ENDPOINTS = {
    "health": "/health",
    "diagnostics": "/diagnostics",
    "discover": "/discover",
    "entities": "/entities",
    "state": "/state",
    "config": "/config",
    "config_sync": "/config/sync",
    "deconfigure": "/deconfigure",
    "ui_config": "/ui-config",
    "events": "/events",
    "command": "/command",
    "webrtc": "/v1/cameras/{config_id}/webrtc",
    "snapshot": "/v1/cameras/{config_id}/snapshot",
}

REQUIRED_ENDPOINTS = ["health", "entities", "command", "config", "ui_config"]

CAPABILITIES: dict[str, dict[str, Any]] = {
    "camera_stream": {
        "kind": "camera",
        "camera": {
            "snapshot_endpoint": "/v1/cameras/{config_id}/snapshot",
            "webrtc_endpoint": "/v1/cameras/{config_id}/webrtc",
            "refresh_seconds": 15,
        },
    },
    "refresh": {"kind": "action"},
    "service_available": {"kind": "sensor", "unit": "bool"},
}

COMMANDS: dict[str, dict[str, Any]] = {
    "refresh": {"description": "Refresh the device state.", "timeout_ms": 5000}
}

CONFIG_SCHEMA: dict[str, Any] = {
    "schema": {
        "title": "Piphi Webrtc Sidecar Setup",
        "type": "object",
        "required": ["source_url"],
        "properties": {
            "source_url": {"type": "string", "title": "RTSP camera URL", "format": "password"},
            "alias": {"type": "string", "title": "Alias"},
        },
    },
    "uiSchema": {
        "source_url": {
            "ui:widget": "password",
            "placeholder": "rtsp://user:password@camera.local/stream",
        },
        "alias": {"placeholder": "Front door camera"},
    },
}

FALLBACK_ENTITY: dict[str, Any] = {
    "id": "camera",
    "name": "Camera",
    "device_id": "camera",
    "entity_type": "camera",
    "capabilities": ["camera_stream", "service_available", "refresh"],
    "available_commands": [{"id": "refresh", "label": "Refresh", "kind": "action"}],
    "dashboard": {
        "allowed_widgets": ["tile", "stat", "button", "io.piphi.webrtc.camera"],
        "default_widget": "io.piphi.webrtc.camera",
    },
}
