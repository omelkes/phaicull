"""CLI entry point for Phaicull.

Per ADR-001: standalone CLI, Typer app, rich for terminal output.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from core.config import load_config

app = typer.Typer(
    name="phaicull",
    help="AI-powered photo culling tool. Scan folders, find blurry/dark/duplicate photos.",
    no_args_is_help=True,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        from importlib.metadata import version

        console.print(f"phaicull {version('phaicull')}")
        raise typer.Exit(0)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Phaicull — your AI second-set-of-eyes for family photos."""
    pass


@app.command()
def scan(
    folder: Path = typer.Argument(
        ...,
        path_type=Path,
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Photo folder to scan.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        path_type=Path,
        exists=True,
        help="Path to phaicull.toml. Default: project root or folder.",
    ),
) -> None:
    """Scan a folder for photos and compute metrics (blur, brightness, duplicates).

    Sprint 1 will implement full scan logic. This scaffold confirms the command structure.
    """
    cfg = load_config(config_path)
    console.print(f"Folder: {folder}")
    console.print(f"Burst window: {cfg.burst_window_seconds}s")
    console.print(
        "Heavy features: "
        + ("enabled" if cfg.heavy_features_enabled else "disabled")
    )
    console.print("Full scan implementation in Sprint 1.")


def run() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    run()
