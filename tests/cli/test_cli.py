"""Tests for CLI scaffold."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from core.cli import app
from core.scanner import pipeline

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
    """scan with existing folder runs and shows summary."""
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert str(tmp_path) in result.output or tmp_path.name in result.output
    assert "Scan complete" in result.output
    assert "Discovered" in result.output
    assert "Near-duplicate groups: 0" in result.output


def test_scan_with_config(tmp_path: Path) -> None:
    """scan with --config loads config and uses loader limits."""
    config = tmp_path / "phaicull.toml"
    config.write_text(
        '[loader]\nmax_file_size_mb = 50.0\nmax_image_dimension = 10000\n',
        encoding="utf-8",
    )
    folder = tmp_path / "photos"
    folder.mkdir()
    result = runner.invoke(
        app,
        ["scan", str(folder), "--config", str(config)],
    )
    assert result.exit_code == 0
    assert "50.0 MB" in result.output
    assert "10000" in result.output


def test_scan_reports_load_failure_reasons(tmp_path: Path) -> None:
    """Load failures are listed with their reason codes."""
    folder = tmp_path / "photos"
    folder.mkdir()
    (folder / "broken.jpg").write_bytes(b"\xff\xd8\xff\xe0JUNK")

    result = runner.invoke(app, ["scan", str(folder)])

    assert result.exit_code == 0
    assert "Load failures: 1 (cannot_open: 1)" in result.output


def test_scan_interrupted_exits_130(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl+C: message on stderr, no summary, exit code 130."""

    async def interrupted(*_args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(pipeline, "run_scan", interrupted)

    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert result.exit_code == 130
    assert "Scan interrupted" in result.stderr
    assert "Scan complete" not in result.output
