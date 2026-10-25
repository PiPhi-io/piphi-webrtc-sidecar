from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .go2rtc import Go2RtcClient, Go2RtcError, go2rtc, validate_source_url


@dataclass(frozen=True)
class ActiveMediaSession:
    session_id: str
    stream_name: str
    expires_at: datetime


class CameraMediaSessionBroker:
    """Owns only short-lived transport sessions; camera configuration stays elsewhere."""

    def __init__(
        self,
        client: Go2RtcClient | None = None,
        *,
        capacity: int | None = None,
    ) -> None:
        self.client = client or go2rtc
        self.capacity = capacity or max(1, int(os.getenv("PIPHI_CAMERA_SESSION_CAPACITY", "16")))
        self._sessions: dict[str, ActiveMediaSession] = {}
        self._expiry_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    async def open(
        self,
        *,
        source_url: str,
        offer_sdp: str,
        idle_timeout_seconds: int,
    ) -> tuple[ActiveMediaSession, str]:
        source = validate_source_url(source_url)
        async with self._lock:
            await self._expire_locked()
            if len(self._sessions) >= self.capacity:
                raise CameraMediaCapacityError("camera media service is at session capacity")
            session_id = uuid4().hex
            stream_name = f"piphi_session_{session_id}"
            await self.client.upsert_stream(stream_name, source)
            try:
                answer_sdp = await self.client.exchange_offer(stream_name, offer_sdp)
            except Go2RtcError as exc:
                if not exc.is_native_source_eof:
                    await self._remove_stream_safely(stream_name)
                    raise
                await self._remove_stream_safely(stream_name)
                await self.client.upsert_ffmpeg_stream(stream_name, source)
                try:
                    answer_sdp = await self.client.exchange_offer(stream_name, offer_sdp)
                except Go2RtcError as relay_exc:
                    if not relay_exc.is_native_source_eof:
                        await self._remove_stream_safely(stream_name)
                        raise
                    await self._remove_stream_safely(stream_name)
                    await self.client.upsert_browser_compatible_ffmpeg_stream(stream_name, source)
                    try:
                        answer_sdp = await self.client.exchange_offer(stream_name, offer_sdp)
                    except Exception:
                        await self._remove_stream_safely(stream_name)
                        raise
                except Exception:
                    await self._remove_stream_safely(stream_name)
                    raise
            except Exception:
                await self._remove_stream_safely(stream_name)
                raise
            active = ActiveMediaSession(
                session_id=session_id,
                stream_name=stream_name,
                expires_at=datetime.now(UTC) + timedelta(seconds=idle_timeout_seconds),
            )
            self._sessions[session_id] = active
            self._expiry_tasks[session_id] = asyncio.create_task(
                self._expire_after(session_id, idle_timeout_seconds),
                name=f"camera-media-expiry:{session_id}",
            )
            return active, answer_sdp

    async def close(self, session_id: str) -> bool:
        async with self._lock:
            active = self._sessions.pop(session_id, None)
            expiry_task = self._expiry_tasks.pop(session_id, None)
            if expiry_task is not None and expiry_task is not asyncio.current_task():
                expiry_task.cancel()
            if active is None:
                return False
            await self._remove_stream_safely(active.stream_name)
            return True

    async def close_all(self) -> None:
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
            expiry_tasks = list(self._expiry_tasks.values())
            self._expiry_tasks.clear()
            for task in expiry_tasks:
                task.cancel()
            for active in sessions:
                await self._remove_stream_safely(active.stream_name)

    async def _expire_after(self, session_id: str, timeout_seconds: int) -> None:
        try:
            await asyncio.sleep(timeout_seconds)
            await self.close(session_id)
        except asyncio.CancelledError:
            return

    async def _expire_locked(self) -> None:
        now = datetime.now(UTC)
        expired = [item for item in self._sessions.values() if item.expires_at <= now]
        for active in expired:
            self._sessions.pop(active.session_id, None)
            expiry_task = self._expiry_tasks.pop(active.session_id, None)
            if expiry_task is not None and expiry_task is not asyncio.current_task():
                expiry_task.cancel()
            await self._remove_stream_safely(active.stream_name)

    async def _remove_stream_safely(self, stream_name: str) -> None:
        try:
            await self.client.remove_stream(stream_name)
        except Go2RtcError:
            pass


class CameraMediaCapacityError(RuntimeError):
    pass


media_session_broker = CameraMediaSessionBroker()
