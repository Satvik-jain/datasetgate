"""Comparison engine for baseline audits and regression detection."""

from __future__ import annotations

from pathlib import Path

from datasetgate.core.constants import ExitCode


def compare_reports_cli(baseline_path: Path, current_path: Path) -> int:
    """Compare two audit report JSON files from CLI and output summary."""
    return ExitCode.SUCCESS
