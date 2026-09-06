from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from ..go2rtc import Go2RtcError, go2rtc
from ..state import get_entry_or_404

MAX_SDP_BYTES = 256 * 1024
router = APIRouter(prefix="/v1/cameras", tags=["camera"])


class WebRtcOffer(BaseModel):
    type: str = "offer"
    sdp: str = Field(min_length=1, max_length=MAX_SDP_BYTES)
    include_audio: bool = False


@router.post("/{config_id}/webrtc", status_code=201)
async def open_webrtc_session(config_id: str, offer: WebRtcOffer) -> dict[str, str]:
    if offer.type != "offer":
        raise HTTPException(status_code=422, detail="type must be offer")
    entry = get_entry_or_404(config_id)
    try:
        answer = await go2rtc.exchange_offer(str(entry["stream_name"]), offer.sdp)
    except (Go2RtcError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail="camera WebRTC signaling failed") from exc
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    return {
        "sdp": answer,
        "session_id": uuid4().hex,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
    }


@router.get("/{config_id}/snapshot")
async def snapshot(config_id: str) -> Response:
    entry = get_entry_or_404(config_id)
    try:
        content_type, content = await go2rtc.snapshot(str(entry["stream_name"]))
    except (Go2RtcError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail="camera snapshot is unavailable") from exc
    if content_type.split(";", 1)[0].strip().lower() not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        raise HTTPException(status_code=502, detail="camera returned an unsupported snapshot")
    return Response(
        content=content,
        media_type=content_type,
        headers={"cache-control": "private, no-store", "x-content-type-options": "nosniff"},
    )
