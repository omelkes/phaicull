"""Configuration for Phaicull.

Loads from TOML (via stdlib tomllib). Handles: thresholds (blur, brightness),
burst window, and enable/disable heavy features.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ThresholdsConfig(BaseModel):
    """Thresholds for blur and brightness metrics (0–1 normalized)."""

    blur_min: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Below this = blurry; images with blur score < blur_min are flagged.",
    )
    brightness_min: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Below this = too dark.",
    )
    brightness_max: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Above this = too bright / blown out.",
    )

    @model_validator(mode="after")
    def brightness_min_lt_max(self) -> "ThresholdsConfig":
        if self.brightness_min >= self.brightness_max:
            raise ValueError(
                "brightness_min must be less than brightness_max "
                f"(got brightness_min={self.brightness_min}, brightness_max={self.brightness_max})"
            )
        return self


class Config(BaseModel):
    """Phaicull configuration."""

    model_config = ConfigDict(extra="ignore")

    thresholds: ThresholdsConfig = Field(
        default_factory=ThresholdsConfig,
        description="Blur and brightness thresholds (0–1 normalized).",
    )
    burst_window_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=300.0,
        description="Group photos within this many seconds as bursts.",
    )
    heavy_features_enabled: bool = Field(
        default=False,
        description="Enable heavy analyzers (e.g. CLIP, face mesh).",
    )


def load_config(path: Path | None = None) -> Config:
    """Load config from a TOML file, or return defaults if not found.

    Args:
        path: Path to phaicull.toml. If None, returns default Config.

    Returns:
        Config instance. Merges file values over defaults; validates via Pydantic.
    """
    if path is None:
        return Config()
    path = Path(path).resolve()
    if not path.exists():
        return Config()
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return Config.model_validate(raw)
