# PiPhi WebRTC Sidecar

Private, local camera signaling for the PiPhi WebRTC dashboard widget. The runtime embeds
[go2rtc](https://github.com/AlexxIT/go2rtc), keeps its administrative API on loopback, and exposes
only PiPhi's bounded camera contract to Core.

## Security boundary

- Core and dashboards never receive the configured RTSP URL or camera credentials.
- Camera sources are administrator-configured and restricted to `rtsp://` or `rtsps://`.
- The go2rtc control API listens only on `127.0.0.1:1984` inside the container.
- WebRTC media uses TCP/UDP `8555`; the PiPhi runtime API uses TCP `8090`.
- Snapshots are bounded to 8 MiB and returned with `private, no-store`.

## Runtime contract

- `POST /config` installs or updates a camera source.
- `GET /entities` exposes a `camera_stream` camera capability.
- `POST /v1/cameras/{config_id}/webrtc` exchanges a browser SDP offer for an answer.
- `GET /v1/cameras/{config_id}/snapshot` returns a bounded still image.

go2rtc ties an HTTP WebRTC consumer to the browser peer connection and removes it when that
connection closes. Consequently the manifest intentionally omits `webrtc_close_endpoint`; Core
reports the local close as successful without claiming an upstream session deletion.

## Development

```bash
pdm install -G dev
GO2RTC_MANAGED=false pdm run uvicorn piphi_webrtc_sidecar.main:app --reload --port 8090
pdm run pytest
pdm run python scripts/validate.py
```

## Container

```bash
docker build -t ghcr.io/piphi-io/piphi-webrtc-sidecar:0.1.1 .
docker run --rm \
  -p 8090:8090 \
  -p 8555:8555/tcp \
  -p 8555:8555/udp \
  ghcr.io/piphi-io/piphi-webrtc-sidecar:0.1.1
```

The pinned upstream is go2rtc `1.9.13`. No host networking or privileged container mode is
required by default. Deployments with complex NAT may provide explicit ICE candidates or TURN
configuration through a reviewed replacement for `go2rtc.yaml`.
