"""DatasetGate Command Line Interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from datasetgate import __version__
from datasetgate.core.config import ConfigError, generate_default_config_yaml, load_config
from datasetgate.core.constants import ExitCode

app = typer.Typer(
    name="datasetgate",
    help="DatasetGate: Local-first computer-vision dataset validation and release-gating tool.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


@app.command()
def version() -> None:
    """Print the DatasetGate version."""
    console.print(f"[bold cyan]DatasetGate[/bold cyan] version [green]{__version__}[/green]")


@app.command()
def init(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Path where datasetgate.yaml should be written",
        ),
    ] = Path("datasetgate.yaml"),
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing configuration file",
        ),
    ] = False,
) -> None:
    """Initialize a new datasetgate.yaml configuration file with recommended defaults."""
    if path.exists() and not force:
        err_console.print(
            f"[bold yellow]Warning:[/bold yellow] Configuration file already exists at [cyan]{path}[/cyan]. "
            "Use [bold]--force[/bold] to overwrite."
        )
        raise typer.Exit(code=ExitCode.INVALID_USAGE)

    try:
        content = generate_default_config_yaml()
        path.write_text(content, encoding="utf-8")
        console.print(
            Panel(
                f"[bold green]Created configuration file:[/bold green] [cyan]{path.resolve()}[/cyan]\n"
                "Customize policies, split coverage requirements, and output directories as needed.",
                title="DatasetGate Initialized",
                border_style="green",
            )
        )
    except Exception as e:
        err_console.print(f"[bold red]Error writing configuration file:[/bold red] {e}")
        raise typer.Exit(code=ExitCode.RUNTIME_ERROR) from e


@app.command()
def audit(
    dataset_path: Annotated[
        Path,
        typer.Argument(
            help="Path to dataset directory or annotation file to audit",
            exists=True,
            file_okay=True,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to custom datasetgate.yaml configuration file",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Directory where report.json and report.html should be saved",
        ),
    ] = None,
    baseline: Annotated[
        Path | None,
        typer.Option(
            "--baseline",
            "-b",
            help="Path to previous audit report.json to compare against for regressions",
        ),
    ] = None,
    format: Annotated[
        str | None,
        typer.Option(
            "--format",
            help="Explicit format: 'auto', 'yolo', or 'coco'",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress standard console output except for final status",
        ),
    ] = False,
) -> None:
    """Audit a dataset for integrity, annotation, and distribution defects against quality policies."""
    try:
        cfg = load_config(config)
        if format:
            cfg.dataset.format = format  # type: ignore[assignment]
    except ConfigError as e:
        err_console.print(f"[bold red]Configuration error:[/bold red] {e}")
        raise typer.Exit(code=ExitCode.INVALID_USAGE) from e
    except Exception as e:
        err_console.print(f"[bold red]Unexpected error loading configuration:[/bold red] {e}")
        raise typer.Exit(code=ExitCode.INVALID_USAGE) from e

    from datasetgate.core.engine import run_audit

    try:
        exit_code = run_audit(
            dataset_path=dataset_path,
            config=cfg,
            output_dir=output,
            baseline_path=baseline,
            quiet=quiet,
        )
        raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise
    except Exception as e:
        err_console.print(f"[bold red]Audit failed with runtime error:[/bold red] {e}")
        raise typer.Exit(code=ExitCode.RUNTIME_ERROR) from e


@app.command()
def snapshot(
    dataset_path: Annotated[
        Path,
        typer.Argument(
            help="Path to dataset to snapshot",
            exists=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path to save baseline snapshot JSON",
        ),
    ] = Path("reports/baseline.json"),
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file",
        ),
    ] = None,
) -> None:
    """Generate a baseline snapshot JSON file for future regression comparison."""
    try:
        cfg = load_config(config)
    except ConfigError as e:
        err_console.print(f"[bold red]Configuration error:[/bold red] {e}")
        raise typer.Exit(code=ExitCode.INVALID_USAGE) from e

    from datasetgate.core.engine import run_snapshot

    try:
        exit_code = run_snapshot(dataset_path=dataset_path, config=cfg, output_path=output)
        raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise
    except Exception as e:
        err_console.print(f"[bold red]Snapshot generation failed:[/bold red] {e}")
        raise typer.Exit(code=ExitCode.RUNTIME_ERROR) from e


@app.command()
def compare(
    baseline: Annotated[
        Path,
        typer.Argument(
            help="Path to baseline report.json",
            exists=True,
            file_okay=True,
            resolve_path=True,
        ),
    ],
    current: Annotated[
        Path,
        typer.Argument(
            help="Path to current report.json",
            exists=True,
            file_okay=True,
            resolve_path=True,
        ),
    ],
) -> None:
    """Compare two audit report JSON files to detect regressions and distribution shifts."""
    from datasetgate.comparison.engine import compare_reports_cli

    try:
        exit_code = compare_reports_cli(baseline_path=baseline, current_path=current)
        raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise
    except Exception as e:
        err_console.print(f"[bold red]Comparison failed:[/bold red] {e}")
        raise typer.Exit(code=ExitCode.RUNTIME_ERROR) from e


@app.command()
def demo(
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory where synthetic demo dataset will be created",
        ),
    ] = Path("demo_dataset"),
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Demo dataset format: 'yolo' or 'coco'",
        ),
    ] = "yolo",
    audit: Annotated[
        bool,
        typer.Option(
            "--audit/--no-audit",
            help="Automatically run audit on the generated demo dataset",
        ),
    ] = True,
) -> None:
    """Generate a self-contained demo dataset with valid samples and deliberate defects."""
    from datasetgate.synthetic.generator import (
        generate_synthetic_coco_dataset,
        generate_synthetic_yolo_dataset,
    )

    fmt = format.lower()
    if fmt == "yolo":
        ds_dir = generate_synthetic_yolo_dataset(output_dir)
        console.print(
            f"[bold green]Created synthetic YOLO demo dataset at:[/bold green] [cyan]{ds_dir.resolve()}[/cyan]"
        )
    elif fmt == "coco":
        ds_dir = generate_synthetic_coco_dataset(output_dir)
        console.print(
            f"[bold green]Created synthetic COCO demo dataset at:[/bold green] [cyan]{ds_dir.resolve()}[/cyan]"
        )
    else:
        err_console.print(
            f"[bold red]Unsupported format:[/bold red] '{format}'. Must be 'yolo' or 'coco'."
        )
        raise typer.Exit(code=ExitCode.INVALID_USAGE)

    if audit:
        console.print("\n[bold cyan]Running demonstration audit...[/bold cyan]\n")
        from datasetgate.core.config import DatasetGateConfig
        from datasetgate.core.engine import run_audit

        cfg = DatasetGateConfig()
        out_reports = output_dir / "reports"
        exit_code = run_audit(
            dataset_path=ds_dir,
            config=cfg,
            output_dir=out_reports,
            quiet=False,
        )
        raise typer.Exit(code=exit_code)


def main() -> None:
    """Entry point for script console."""
    app()


if __name__ == "__main__":
    main()
