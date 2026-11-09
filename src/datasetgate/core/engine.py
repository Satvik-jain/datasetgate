"""Core execution engine for audit, validation, and snapshot pipelines."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datasetgate.core.config import DatasetFormat, DatasetGateConfig
from datasetgate.core.constants import ExitCode
from datasetgate.core.models import (
    AuditSnapshot,
    ComparisonResult,
    DatasetManifest,
    DatasetStatistics,
    Finding,
)
from datasetgate.parsers.coco import CocoParser
from datasetgate.parsers.yolo import YoloParser
from datasetgate.policies.engine import PolicyEngine
from datasetgate.reporting.html import generate_html_report
from datasetgate.reporting.json import generate_json_report
from datasetgate.validators.annotations import AnnotationValidator
from datasetgate.validators.distribution import compute_dataset_statistics
from datasetgate.validators.duplicates import DuplicateValidator
from datasetgate.validators.image_integrity import ImageIntegrityValidator

console = Console()
err_console = Console(stderr=True)


def calculate_dataset_fingerprint(manifest: DatasetManifest, stats: DatasetStatistics) -> str:
    """Compute deterministic SHA-256 fingerprint for a dataset version."""
    h = hashlib.sha256()

    # Sort images deterministically by relative path
    for img in sorted(manifest.images, key=lambda x: x.relative_path):
        h.update(
            f"{img.relative_path}:{img.split}:{img.sha256 or ''}:{img.file_size_bytes}".encode()
        )

    # Include classes
    for cid, name in sorted(manifest.classes.items()):
        h.update(f"{cid}:{name}".encode())

    # Include aggregate stats
    h.update(
        f"{stats.total_images}:{stats.total_annotations}:{stats.class_imbalance_ratio}".encode()
    )
    return h.hexdigest()[:16]


def parse_dataset(dataset_path: Path, config: DatasetGateConfig) -> DatasetManifest:
    """Select and run appropriate parser for the dataset."""
    fmt = config.dataset.format

    if fmt == DatasetFormat.YOLO:
        return YoloParser().parse(dataset_path, config)
    elif fmt == DatasetFormat.COCO:
        return CocoParser().parse(dataset_path, config)
    elif fmt == DatasetFormat.AUTO:
        # Heuristic auto detection
        yolo_parser = YoloParser()
        coco_parser = CocoParser()

        if yolo_parser.can_parse(dataset_path):
            return yolo_parser.parse(dataset_path, config)
        elif coco_parser.can_parse(dataset_path):
            return coco_parser.parse(dataset_path, config)
        else:
            # Default to YOLO parser with clear warnings
            manifest = yolo_parser.parse(dataset_path, config)
            if not manifest.images:
                # Try COCO
                coco_manifest = coco_parser.parse(dataset_path, config)
                if coco_manifest.images:
                    return coco_manifest
            return manifest
    else:
        raise ValueError(f"Unsupported dataset format: {fmt}")


def run_audit(
    dataset_path: Path,
    config: DatasetGateConfig,
    output_dir: Path | None = None,
    baseline_path: Path | None = None,
    quiet: bool = False,
) -> int:
    """Run full audit workflow and return exit code."""
    dataset_root = dataset_path.resolve()

    if not quiet:
        console.print(
            f"[bold cyan]DatasetGate Audit[/bold cyan]: Scanning [yellow]{dataset_root}[/yellow]..."
        )

    # 1. Parse dataset
    manifest = parse_dataset(dataset_root, config)

    # 2. Run validators
    findings: list[Finding] = list(manifest.discovery_warnings)
    findings.extend(ImageIntegrityValidator().validate(manifest, config))
    findings.extend(AnnotationValidator().validate(manifest, config))
    findings.extend(DuplicateValidator().validate(manifest, config))

    # De-duplicate findings by fingerprint
    unique_findings: list[Finding] = []
    seen_fingerprints: set[str] = set()
    for f in findings:
        fp = f.fingerprint()
        if fp not in seen_fingerprints:
            seen_fingerprints.add(fp)
            unique_findings.append(f)

    # 3. Compute statistics
    stats = compute_dataset_statistics(manifest, discovery_findings=unique_findings)

    # 4. Evaluate policies
    policy_engine = PolicyEngine()
    final_findings, policy_result = policy_engine.evaluate(manifest, stats, unique_findings, config)

    # 5. Compute fingerprint & build snapshot
    fingerprint = calculate_dataset_fingerprint(manifest, stats)
    dataset_name = dataset_root.name

    snapshot = AuditSnapshot(
        dataset_fingerprint=fingerprint,
        format=manifest.format,
        dataset_name=dataset_name,
        statistics=stats,
        findings=final_findings,
        policy_result=policy_result,
    )

    # 6. Baseline comparison (if requested)
    comparison: ComparisonResult | None = None
    if baseline_path is not None:
        from datasetgate.comparison.engine import compare_snapshots

        baseline_file = Path(baseline_path)
        if baseline_file.is_file():
            try:
                with open(baseline_file, encoding="utf-8") as f:
                    baseline_data = json.load(f)
                baseline_snapshot = AuditSnapshot.model_validate(baseline_data)
                comparison = compare_snapshots(baseline_snapshot, snapshot)
            except Exception as e:
                if not quiet:
                    err_console.print(
                        f"[bold yellow]Warning:[/bold yellow] Could not compare against baseline {baseline_path}: {e}"
                    )

    # 7. Write reports
    out_dir = output_dir or Path(config.reporting.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "report.json"
    html_path = out_dir / "report.html"

    if config.reporting.generate_json:
        generate_json_report(snapshot, json_path)
    if config.reporting.generate_html:
        generate_html_report(snapshot, html_path, comparison=comparison)

    # 8. Console output
    if not quiet:
        _render_console_summary(snapshot, json_path, html_path, comparison)

    return ExitCode.SUCCESS if policy_result.passed else ExitCode.GATE_FAILED


def run_snapshot(
    dataset_path: Path,
    config: DatasetGateConfig,
    output_path: Path,
) -> int:
    """Generate a standalone baseline snapshot JSON file."""
    dataset_root = dataset_path.resolve()
    manifest = parse_dataset(dataset_root, config)

    findings: list[Finding] = list(manifest.discovery_warnings)
    findings.extend(ImageIntegrityValidator().validate(manifest, config))
    findings.extend(AnnotationValidator().validate(manifest, config))
    findings.extend(DuplicateValidator().validate(manifest, config))

    # De-duplicate findings
    unique_findings: list[Finding] = []
    seen: set[str] = set()
    for f in findings:
        fp = f.fingerprint()
        if fp not in seen:
            seen.add(fp)
            unique_findings.append(f)

    stats = compute_dataset_statistics(manifest, discovery_findings=unique_findings)
    policy_engine = PolicyEngine()
    final_findings, policy_result = policy_engine.evaluate(manifest, stats, unique_findings, config)
    fingerprint = calculate_dataset_fingerprint(manifest, stats)

    snapshot = AuditSnapshot(
        dataset_fingerprint=fingerprint,
        format=manifest.format,
        dataset_name=dataset_root.name,
        statistics=stats,
        findings=final_findings,
        policy_result=policy_result,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_json_report(snapshot, output_path)
    console.print(f"[bold green]Baseline snapshot saved:[/bold green] [cyan]{output_path}[/cyan]")
    return ExitCode.SUCCESS


def _render_console_summary(
    snapshot: AuditSnapshot,
    json_path: Path,
    html_path: Path,
    comparison: ComparisonResult | None = None,
) -> None:
    """Render structured terminal report using Rich."""
    stats = snapshot.statistics
    policy = snapshot.policy_result

    # Overview Table
    table = Table(
        title=f"DatasetGate Audit: {snapshot.dataset_name} ({snapshot.format.upper()})",
        show_header=True,
    )
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="bold white")

    table.add_row("Total Images", str(stats.total_images))
    table.add_row("Total Annotations", str(stats.total_annotations))
    table.add_row(
        "Dataset Splits", ", ".join(f"{s} ({cnt})" for s, cnt in stats.images_per_split.items())
    )
    table.add_row("Classes Count", str(len(stats.instances_per_class)))
    table.add_row("Empty Label Rate", f"{stats.empty_label_rate * 100:.1f}%")
    table.add_row("Class Imbalance Ratio", f"{stats.class_imbalance_ratio:.1f}:1")
    table.add_row("Duplicate Image Groups", str(stats.duplicate_groups_count))
    table.add_row("Cross-Split Leakages", str(stats.leakage_groups_count))
    table.add_row("Fingerprint", snapshot.dataset_fingerprint)

    console.print(table)

    # Comparison summary if applicable
    if comparison:
        comp_style = "bold red" if comparison.has_regressions else "bold green"
        console.print(
            Panel(
                f"[bold]Image Diff:[/bold] {comparison.image_count_diff:+d} | "
                f"[bold]Annotation Diff:[/bold] {comparison.annotation_count_diff:+d} | "
                f"[bold]New Findings:[/bold] {len(comparison.findings_diff.new_findings)} | "
                f"[bold]Resolved Findings:[/bold] {len(comparison.findings_diff.resolved_findings)}\n"
                f"{comparison.summary}",
                title="Baseline Comparison",
                border_style=comp_style,
            )
        )

    # Findings Highlights
    if policy.errors:
        console.print(f"\n[bold red]Errors ({len(policy.errors)}):[/bold red]")
        for err in policy.errors[:5]:
            console.print(f"  [red]&bull;[/red] {err}")
        if len(policy.errors) > 5:
            console.print(f"  [dim]... and {len(policy.errors) - 5} more (see reports)[/dim]")

    if policy.warnings:
        console.print(f"\n[bold yellow]Warnings ({len(policy.warnings)}):[/bold yellow]")
        for warn in policy.warnings[:5]:
            console.print(f"  [yellow]&bull;[/yellow] {warn}")
        if len(policy.warnings) > 5:
            console.print(f"  [dim]... and {len(policy.warnings) - 5} more (see reports)[/dim]")

    # Status Panel
    if policy.passed:
        console.print(
            Panel(
                f"[bold green]QUALITY GATE PASSED[/bold green]\n"
                f"Reports generated: [cyan]{json_path}[/cyan] and [cyan]{html_path}[/cyan]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]QUALITY GATE FAILED[/bold red]\n"
                f"Violations detected against configured policy.\n"
                f"Inspect reports: [cyan]{json_path}[/cyan] and [cyan]{html_path}[/cyan]",
                border_style="red",
            )
        )
