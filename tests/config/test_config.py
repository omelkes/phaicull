"""Tests for config loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config import Config, ThresholdsConfig, load_config


# --- Default config ---


def test_load_config_none_returns_defaults() -> None:
    """load_config(None) returns default Config."""
    cfg = load_config(None)
    assert isinstance(cfg, Config)
    assert cfg.thresholds.blur_min == 0.1
    assert cfg.thresholds.brightness_min == 0.2
    assert cfg.thresholds.brightness_max == 0.9
    assert cfg.burst_window_seconds == 5.0
    assert cfg.heavy_features_enabled is False


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    """load_config(non-existent path) returns default Config."""
    missing = tmp_path / "no_such_file.toml"
    assert not missing.exists()
    cfg = load_config(missing)
    assert cfg.burst_window_seconds == 5.0


# --- Valid TOML ---


def test_load_config_full_toml(tmp_path: Path) -> None:
    """Load full config from TOML."""
    toml = tmp_path / "phaicull.toml"
    toml.write_text(
        """burst_window_seconds = 10.0
heavy_features_enabled = true

[thresholds]
blur_min = 0.2
brightness_min = 0.15
brightness_max = 0.95
""",
        encoding="utf-8",
    )
    cfg = load_config(toml)
    assert cfg.thresholds.blur_min == 0.2
    assert cfg.thresholds.brightness_min == 0.15
    assert cfg.thresholds.brightness_max == 0.95
    assert cfg.burst_window_seconds == 10.0
    assert cfg.heavy_features_enabled is True


def test_load_config_partial_toml(tmp_path: Path) -> None:
    """Partial TOML merges with defaults."""
    toml = tmp_path / "phaicull.toml"
    toml.write_text(
        """
burst_window_seconds = 3.5
""",
        encoding="utf-8",
    )
    cfg = load_config(toml)
    assert cfg.burst_window_seconds == 3.5
    assert cfg.thresholds.blur_min == 0.1  # default
    assert cfg.heavy_features_enabled is False  # default


def test_load_config_thresholds_only(tmp_path: Path) -> None:
    """Only [thresholds] section overrides those values."""
    toml = tmp_path / "phaicull.toml"
    toml.write_text(
        """
[thresholds]
blur_min = 0.05
""",
        encoding="utf-8",
    )
    cfg = load_config(toml)
    assert cfg.thresholds.blur_min == 0.05
    assert cfg.thresholds.brightness_min == 0.2
    assert cfg.burst_window_seconds == 5.0


# --- Validation ---


def test_thresholds_blur_min_out_of_range() -> None:
    """blur_min must be 0–1."""
    with pytest.raises(ValidationError):
        ThresholdsConfig(blur_min=1.5)
    with pytest.raises(ValidationError):
        ThresholdsConfig(blur_min=-0.1)


def test_thresholds_brightness_min_lt_max() -> None:
    """brightness_min must be less than brightness_max."""
    with pytest.raises(ValidationError, match="brightness_min must be less than brightness_max"):
        ThresholdsConfig(brightness_min=0.9, brightness_max=0.2)
    with pytest.raises(ValidationError, match="brightness_min must be less than brightness_max"):
        ThresholdsConfig(brightness_min=0.5, brightness_max=0.5)
    # Valid: min < max
    cfg = ThresholdsConfig(brightness_min=0.2, brightness_max=0.9)
    assert cfg.brightness_min == 0.2
    assert cfg.brightness_max == 0.9


def test_burst_window_out_of_range() -> None:
    """burst_window_seconds must be 0.1–300."""
    with pytest.raises(ValidationError):
        Config(burst_window_seconds=0.05)
    with pytest.raises(ValidationError):
        Config(burst_window_seconds=400.0)


def test_invalid_toml_raises(tmp_path: Path) -> None:
    """Invalid TOML syntax raises."""
    import tomllib

    toml = tmp_path / "bad.toml"
    toml.write_text("not valid toml [ section = broken", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_config(toml)


def test_invalid_types_in_toml_raises_validation(tmp_path: Path) -> None:
    """Wrong types in TOML raise ValidationError."""
    toml = tmp_path / "phaicull.toml"
    toml.write_text(
        """
burst_window_seconds = "five"
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_config(toml)


def test_load_config_inverted_brightness_raises(tmp_path: Path) -> None:
    """TOML with brightness_min >= brightness_max raises ValidationError."""
    toml = tmp_path / "phaicull.toml"
    toml.write_text(
        """
[thresholds]
brightness_min = 0.9
brightness_max = 0.2
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="brightness_min must be less than brightness_max"):
        load_config(toml)
