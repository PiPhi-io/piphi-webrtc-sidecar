FROM ghcr.io/alexxit/go2rtc:1.9.13@sha256:f394f6329f5389a4c9a7fc54b09fdec9621bbb78bf7a672b973440bbdfb02241 AS go2rtc

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS dependencies

ARG PDM_VERSION=2.26.7
WORKDIR /build
RUN pip install --no-cache-dir "pdm==${PDM_VERSION}"
COPY pyproject.toml pdm.lock ./
RUN pdm export --prod --without-hashes --output requirements.txt

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ARG APP_VERSION=0.1.1
LABEL org.opencontainers.image.title="PiPhi WebRTC Sidecar" \
      org.opencontainers.image.description="Private go2rtc adapter for PiPhi camera widgets" \
      org.opencontainers.image.source="https://github.com/PiPhi-io/piphi-webrtc-sidecar" \
      org.opencontainers.image.version="${APP_VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIPHI_ENV=production \
    GO2RTC_BINARY=/usr/local/bin/go2rtc \
    GO2RTC_CONFIG=/etc/piphi/go2rtc.yaml \
    GO2RTC_URL=http://127.0.0.1:1984

WORKDIR /app
COPY --from=go2rtc /usr/local/bin/go2rtc /usr/local/bin/go2rtc
COPY --from=dependencies /build/requirements.txt /tmp/requirements.txt
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir --no-deps . \
    && rm /tmp/requirements.txt \
    && useradd --create-home --uid 10001 piphi \
    && mkdir -p /etc/piphi /app/data \
    && chown -R piphi:piphi /app/data
COPY --chown=piphi:piphi go2rtc.yaml /etc/piphi/go2rtc.yaml

USER piphi
EXPOSE 8090 8555/tcp 8555/udp
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=3)"
CMD ["uvicorn", "piphi_webrtc_sidecar.main:app", "--host", "0.0.0.0", "--port", "8090"]
