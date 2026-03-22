"""CLI entry point for Phaicull.

Per ADR-001: standalone CLI, Typer app, rich for terminal output.
"""

from __future__ import annotations

import asyncio
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
    """Scan a folder for photos and compute metrics (blur, brightness, duplicates)."""
    from core.scanner.pipeline import run_scan

    cfg = load_config(config_path)
    console.print(f"[bold]Scanning:[/bold] {folder}")
    console.print(
        f"Loader limits: {cfg.loader.max_file_size_mb} MB, "
        f"{cfg.loader.max_image_dimension}px max dimension"
    )

    summary = asyncio.run(run_scan(folder, cfg))

    console.print("\n[bold green]Scan complete[/bold green]")
    console.print(f"  Discovered: {summary.total_discovered}")
    console.print(f"  Processed:  {summary.processed}")
    if summary.load_failed:
        console.print(f"  [yellow]Load failures:[/yellow] {summary.load_failed}")
    if summary.analyzer_errors:
        console.print(f"  [yellow]Analyzer errors:[/yellow] {summary.analyzer_errors}")


def run() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    run()
