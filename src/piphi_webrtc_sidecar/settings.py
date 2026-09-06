from __future__ import annotations

import os

INTEGRATION_ID = "piphi.service.webrtc-sidecar"
INTEGRATION_NAME = "PiPhi WebRTC Sidecar"
INTEGRATION_VERSION = "0.1.2"
PROJECT_KIND = "sidecar"
PROJECT_PRESET = "platform-service"
PROJECT_DOMAIN = "sidecar-service"
DEFAULT_PORT = 8090


def runtime_port() -> int:
    raw_port = os.getenv("PORT", str(DEFAULT_PORT))
    try:
        return int(raw_port)
    except ValueError:
        return DEFAULT_PORT
