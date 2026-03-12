"""Tests for CLI scaffold."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from core.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    """--help shows usage and commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "phaicull" in result.output
    assert "scan" in result.output
    assert "photo" in result.output


def test_cli_version() -> None:
    """--version prints version and exits 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_scan_help() -> None:
    """scan --help shows folder argument and options."""
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "folder" in result.output.lower()
    assert "config" in result.output.lower() or "--config" in result.output


def test_scan_requires_folder() -> None:
    """scan without folder fails."""
    result = runner.invoke(app, ["scan"])
    assert result.exit_code != 0


def test_scan_with_valid_folder(tmp_path: Path) -> None:
    """scan with existing folder runs (scaffold output)."""
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert str(tmp_path) in result.output or tmp_path.name in result.output
    assert "Burst window" in result.output
    assert "Sprint 1" in result.output


def test_scan_with_config(tmp_path: Path) -> None:
    """scan with --config loads config."""
    config = tmp_path / "phaicull.toml"
    config.write_text(
        "burst_window_seconds = 10.0\nheavy_features_enabled = true\n",
        encoding="utf-8",
    )
    folder = tmp_path / "photos"
    folder.mkdir()
    result = runner.invoke(
        app,
        ["scan", str(folder), "--config", str(config)],
    )
    assert result.exit_code == 0
    assert "10.0" in result.output
    assert "enabled" in result.output
