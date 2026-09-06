# Runtime contract

- Integration ID: `piphi.service.webrtc-sidecar`
- Runtime kind: `sidecar` (published in the registry as a `platform_service`)
- Port: `8090`

Core configures one RTSP or RTSPS source per `config_id` through `POST /config`. The source URL is
treated as a secret and is only forwarded to the loopback-only go2rtc control API.

## Camera media

- `POST /v1/cameras/{config_id}/webrtc` accepts `{ "type": "offer", "sdp": "..." }` and
  returns the SDP answer and an opaque session ID.
- `GET /v1/cameras/{config_id}/snapshot` returns the latest JPEG, PNG, or WebP frame.
- Closing the browser `RTCPeerConnection` releases the upstream go2rtc HTTP consumer. There is no
  separate close endpoint because go2rtc does not expose an HTTP consumer identifier.

## Runtime endpoints

- `GET /health`, `/diagnostics`, `/entities`, `/state`, `/contract`, `/events`, and `/ui-config`
- `POST /config`, `/config/sync`, `/deconfigure`, `/discover`, and `/command`

The only command is `refresh`. Passive discovery intentionally returns no cameras because camera
credentials and stream URLs must be entered explicitly.
