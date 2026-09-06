from __future__ import annotations

from piphi_runtime_kit_python import RuntimeConfig
from pydantic import Field, SecretStr, field_validator

from .go2rtc import validate_source_url


class DeviceConfig(RuntimeConfig):
    source_url: SecretStr
    alias: str | None = Field(default=None, max_length=120)

    @field_validator("source_url")
    @classmethod
    def validate_camera_source(cls, value: SecretStr) -> SecretStr:
        validate_source_url(value.get_secret_value())
        return value
