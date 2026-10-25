# PiPhi Camera Media Service

One shared, locally managed camera media service for PiPhi. It embeds
[go2rtc](https://github.com/AlexxIT/go2rtc), keeps the upstream administration API on loopback,
and exposes only the authenticated `camera.media.v1` contract to Core.

The stable package ID remains `piphi.service.webrtc-sidecar` so existing installations upgrade in
place. `sidecar` now describes the container deployment mode only; the product and onboarding
model are a zero-setup home service.

## Ownership boundary

- Camera integrations own discovery, camera credentials, source URLs, and saved camera devices.
- This service owns short-lived media sessions and transport adaptation.
- Core installs one shared service per home and binds compatible camera integrations to it.
- The service does not discover devices, create entities, accept device configuration, or appear
  as a camera itself.
- Camera source URLs are accepted only in authenticated, Core-to-service session requests and are
  never returned by health, diagnostics, contract, or session responses.
- The go2rtc control API listens only on `127.0.0.1:1984` inside the container.
- Sources use go2rtc's native RTSP client first. If that client reaches the camera but terminates
  the WebRTC exchange with `EOF`, the service retries once through an FFmpeg stream-copy relay.
- The fallback does not transcode video or audio. Its internal RTSP listener is loopback-only, and
  go2rtc may execute only the packaged `/usr/bin/ffmpeg` binary.

## Runtime contract

- `GET /health` reports service and embedded go2rtc health.
- `GET /diagnostics` reports bounded, non-secret service diagnostics.
- `GET /contract` exposes the runtime endpoint contract.
- `GET /v1/camera-media/status` reports session capacity.
- `POST /v1/camera-media/sessions` exchanges a short-lived source and browser SDP offer for an
  answer.
- `DELETE /v1/camera-media/sessions/{session_id}` closes a media session.

## Development

```bash
pdm install -G dev
GO2RTC_MANAGED=false pdm run uvicorn piphi_webrtc_sidecar.main:app --reload --port 8090
pdm run pytest
pdm run python scripts/validate.py
```

## Container

```bash
docker build -t ghcr.io/piphi-io/piphi-webrtc-sidecar:0.3.1 .
docker run --rm \
  -p 8090:8090 \
  -p 8555:8555/tcp \
  -p 8555:8555/udp \
  ghcr.io/piphi-io/piphi-webrtc-sidecar:0.3.1
```

The pinned upstream is go2rtc `1.9.15`. No host networking or privileged container mode is
required by default. Deployments with complex NAT may provide explicit ICE candidates or TURN
configuration through a reviewed replacement for `go2rtc.yaml`.
