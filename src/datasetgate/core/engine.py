"""Execution engine stubs for audit and snapshot workflows."""

from __future__ import annotations

from pathlib import Path

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.constants import ExitCode


def run_audit(
    dataset_path: Path,
    config: DatasetGateConfig,
    output_dir: Path | None = None,
    baseline_path: Path | None = None,
    quiet: bool = False,
) -> int:
    """Run full dataset validation audit and return exit code."""
    # To be fully implemented in subsequent milestones
    return ExitCode.SUCCESS


def run_snapshot(
    dataset_path: Path,
    config: DatasetGateConfig,
    output_path: Path,
) -> int:
    """Generate a baseline snapshot JSON file and return exit code."""
    return ExitCode.SUCCESS
