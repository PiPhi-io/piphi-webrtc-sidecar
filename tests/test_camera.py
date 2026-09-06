from __future__ import annotations

import httpx
import pytest

from piphi_webrtc_sidecar.go2rtc import (
    Go2RtcClient,
    Go2RtcError,
    stream_name_for,
    validate_source_url,
)
from piphi_webrtc_sidecar.main import app
from piphi_webrtc_sidecar.schemas import DeviceConfig
from piphi_webrtc_sidecar.state import apply_config, registry


def test_source_url_is_limited_to_rtsp_and_stream_names_are_safe() -> None:
    assert validate_source_url("rtsps://user:secret@camera.local/live").startswith("rtsps://")
    assert stream_name_for("Front Door/1") == "piphi_front_door_1"
    with pytest.raises(ValueError, match="rtsp"):
        validate_source_url("http://169.254.169.254/latest/meta-data")


@pytest.mark.anyio
async def test_go2rtc_client_uses_private_api_contract() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/streams":
            return httpx.Response(204)
        if request.url.path == "/api/webrtc":
            return httpx.Response(200, json={"type": "answer", "sdp": "v=0\r\na=answer\r\n"})
        if request.url.path == "/api/frame.jpeg":
            return httpx.Response(200, content=b"jpeg", headers={"content-type": "image/jpeg"})
        return httpx.Response(404)

    client = Go2RtcClient("http://127.0.0.1:1984", httpx.MockTransport(handler))
    await client.upsert_stream("piphi_camera_1", "rtsp://user:secret@camera.local/live")
    answer = await client.exchange_offer("piphi_camera_1", "v=0\r\n")
    content_type, image = await client.snapshot("piphi_camera_1")

    assert answer == "v=0\r\na=answer\r\n"
    assert (content_type, image) == ("image/jpeg", b"jpeg")
    assert requests[0].url.params["name"] == "piphi_camera_1"
    assert requests[0].url.params["src"] == "rtsp://user:secret@camera.local/live"
    assert requests[1].url.params["src"] == "piphi_camera_1"


@pytest.mark.anyio
async def test_go2rtc_client_rejects_malformed_answer() -> None:
    client = Go2RtcClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, content=b"not-json"))
    )
    with pytest.raises(Go2RtcError, match="invalid WebRTC answer"):
        await client.exchange_offer("piphi_camera_1", "v=0\r\n")


@pytest.mark.anyio
async def test_camera_contract_exchanges_sdp_without_exposing_credentials(monkeypatch) -> None:
    async def _upsert_stream(_name: str, _source_url: str) -> None:
        return None

    async def _exchange_offer(name: str, sdp: str) -> str:
        assert name == "piphi_camera_1"
        assert sdp == "v=0\r\n"
        return "v=0\r\na=answer\r\n"

    monkeypatch.setattr("piphi_webrtc_sidecar.state.go2rtc.upsert_stream", _upsert_stream)
    monkeypatch.setattr("piphi_webrtc_sidecar.routes.camera.go2rtc.exchange_offer", _exchange_offer)
    registry.entries.clear()
    registry.state_snapshots.clear()
    await apply_config(
        DeviceConfig(
            id="camera-1",
            config_id="camera-1",
            source_url="rtsp://user:top-secret@camera.local/live",
            alias="Front door",
        )
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/cameras/camera-1/webrtc",
            json={"type": "offer", "sdp": "v=0\r\n", "include_audio": True},
        )
        state = await client.get("/state")

    assert response.status_code == 201
    assert response.json()["sdp"] == "v=0\r\na=answer\r\n"
    assert response.json()["session_id"]
    assert "top-secret" not in state.text
    assert "camera.local" not in state.text
