"""Baseline comparison engine and regression detection."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datasetgate.core.constants import ExitCode
from datasetgate.core.models import (
    AuditSnapshot,
    ComparisonResult,
    Finding,
    FindingDiff,
    Severity,
)

console = Console()
err_console = Console(stderr=True)


PERCEPTUAL_RULE_IDS = {
    "PERCEPTUAL_DUPLICATE",
    "PERCEPTUAL_SPLIT_LEAKAGE",
    "PERCEPTUAL_ANALYSIS_TRUNCATED",
    "PERCEPTUAL_HASH_UNAVAILABLE",
}


def _get_phash_coverage(snapshot: AuditSnapshot) -> dict:
    """Safely extract perceptual hash coverage metadata if present."""
    if not isinstance(snapshot.metadata, dict):
        return {}
    cov = snapshot.metadata.get("analysis_coverage")
    if isinstance(cov, dict):
        p_cov = cov.get("perceptual_hash")
        if isinstance(p_cov, dict):
            return p_cov
    return {}


def compare_snapshots(baseline: AuditSnapshot, current: AuditSnapshot) -> ComparisonResult:
    """Deterministically compare a baseline AuditSnapshot with a current AuditSnapshot.

    Handles coverage differences gracefully:
    - If baseline did not execute perceptual hashing, new perceptual findings are not
      falsely classified as dataset regressions.
    - If current audit did not execute perceptual hashing, baseline perceptual findings
      are not falsely classified as resolved.
    - If algorithm, threshold, or completeness differs, perceptual finding coverage is
      marked as not directly comparable.
    """
    is_identical = baseline.dataset_fingerprint == current.dataset_fingerprint

    # Analysis coverage analysis
    base_cov = _get_phash_coverage(baseline)
    curr_cov = _get_phash_coverage(current)

    base_phash_executed = bool(base_cov.get("enabled") and base_cov.get("executed"))
    curr_phash_executed = bool(curr_cov.get("enabled") and curr_cov.get("executed"))

    coverage_notes: list[str] = []
    phash_directly_comparable = True

    if base_phash_executed and curr_phash_executed:
        base_algo = base_cov.get("algorithm")
        curr_algo = curr_cov.get("algorithm")
        base_dist = base_cov.get("max_hamming_distance")
        curr_dist = curr_cov.get("max_hamming_distance")
        base_complete = base_cov.get("complete", True)
        curr_complete = curr_cov.get("complete", True)

        if base_algo != curr_algo:
            phash_directly_comparable = False
            coverage_notes.append(
                f"Perceptual algorithm differs (baseline: {base_algo}, current: {curr_algo}); "
                "perceptual findings are not directly comparable."
            )
        elif base_dist != curr_dist:
            phash_directly_comparable = False
            coverage_notes.append(
                f"Perceptual Hamming distance threshold differs (baseline: {base_dist}, current: {curr_dist}); "
                "perceptual findings are not directly comparable."
            )
        elif not base_complete or not curr_complete:
            phash_directly_comparable = False
            coverage_notes.append(
                "Perceptual duplicate analysis was truncated in baseline or current snapshot; "
                "coverage is not directly comparable."
            )
    elif curr_phash_executed and not base_phash_executed:
        phash_directly_comparable = False
        coverage_notes.append(
            "Perceptual duplicate detection was executed in current audit but was not present in baseline; "
            "perceptual findings are excluded from regression tracking."
        )
    elif base_phash_executed and not curr_phash_executed:
        phash_directly_comparable = False
        coverage_notes.append(
            "Perceptual duplicate detection was not executed in current audit; "
            "baseline perceptual findings are not considered resolved."
        )

    # Count diffs
    img_diff = current.statistics.total_images - baseline.statistics.total_images
    ann_diff = current.statistics.total_annotations - baseline.statistics.total_annotations

    # Class distribution diffs
    class_diff: dict[str, int] = {}
    all_classes = set(baseline.statistics.instances_per_class.keys()) | set(
        current.statistics.instances_per_class.keys()
    )
    for c_name in sorted(all_classes):
        base_cnt = baseline.statistics.instances_per_class.get(c_name, 0)
        curr_cnt = current.statistics.instances_per_class.get(c_name, 0)
        class_diff[c_name] = curr_cnt - base_cnt

    # Findings diff by fingerprint
    base_findings_by_fp = {f.fingerprint(): f for f in baseline.findings}
    curr_findings_by_fp = {f.fingerprint(): f for f in current.findings}

    new_findings: list[Finding] = []
    resolved_findings: list[Finding] = []
    persisting_count = 0

    for fp, f in curr_findings_by_fp.items():
        if fp not in base_findings_by_fp:
            new_findings.append(f)
        else:
            persisting_count += 1

    for fp, f in base_findings_by_fp.items():
        if fp not in curr_findings_by_fp:
            # If current audit did not run perceptual check, baseline perceptual findings are un-evaluated, not resolved
            if f.rule_id in PERCEPTUAL_RULE_IDS and not curr_phash_executed:
                continue
            resolved_findings.append(f)

    # Detect regressions
    regressions: list[str] = []

    # 1. Newly introduced ERROR findings (excluding non-comparable perceptual findings)
    new_errors = [
        f
        for f in new_findings
        if f.severity == Severity.ERROR
        and not (
            f.rule_id in PERCEPTUAL_RULE_IDS
            and not (base_phash_executed and phash_directly_comparable)
        )
    ]
    if new_errors:
        err_by_rule: dict[str, int] = {}
        for e in new_errors:
            err_by_rule[e.rule_id] = err_by_rule.get(e.rule_id, 0) + 1
        summary_rules = ", ".join(f"{cnt}x {rule}" for rule, cnt in err_by_rule.items())
        regressions.append(f"Introduced {len(new_errors)} new error(s): {summary_rules}")

    # 2. Split leakage increase (exact duplicates)
    curr_leaks = current.statistics.leakage_groups_count
    base_leaks = baseline.statistics.leakage_groups_count
    if curr_leaks > base_leaks:
        regressions.append(
            f"Cross-split leakage increased: was {base_leaks}, now {curr_leaks} groups"
        )

    # 3. Overall policy status regression
    status_changed = baseline.policy_result.passed != current.policy_result.passed
    if baseline.policy_result.passed and not current.policy_result.passed:
        # Check if the failure is solely due to non-comparable perceptual findings
        failing_rules = {f.rule_id for f in current.findings if f.severity == Severity.ERROR}
        solely_perceptual_new = not (
            base_phash_executed and phash_directly_comparable
        ) and failing_rules.issubset(PERCEPTUAL_RULE_IDS)
        if solely_perceptual_new:
            coverage_notes.append(
                "Overall policy status changed from PASSED to FAILED due to newly enabled or non-comparable perceptual checks."
            )
        else:
            regressions.append("Policy status regressed: baseline PASSED, current FAILED")

    # 4. Worsening class imbalance (if ratio increased significantly, e.g. > 50% increase)
    base_imb = baseline.statistics.class_imbalance_ratio
    curr_imb = current.statistics.class_imbalance_ratio
    if base_imb > 0 and curr_imb > base_imb * 1.5 and curr_imb > 15.0:
        regressions.append(f"Class imbalance worsened from {base_imb:.1f}:1 to {curr_imb:.1f}:1")

    # 5. Newly missing classes in train split
    base_missing = set(baseline.statistics.missing_classes_per_split.get("train", []))
    curr_missing = set(current.statistics.missing_classes_per_split.get("train", []))
    new_missing = curr_missing - base_missing
    if new_missing:
        regressions.append(
            f"Classes no longer represented in train split: {', '.join(sorted(new_missing))}"
        )

    has_regressions = len(regressions) > 0

    # Summary text
    summary = (
        f"Compared to baseline: {img_diff:+d} images, {ann_diff:+d} annotations. "
        f"{len(new_findings)} new findings ({len(new_errors)} errors), {len(resolved_findings)} resolved findings."
    )
    if coverage_notes:
        summary += f" Coverage notes: {'; '.join(coverage_notes)}"

    return ComparisonResult(
        baseline_fingerprint=baseline.dataset_fingerprint,
        current_fingerprint=current.dataset_fingerprint,
        is_identical=is_identical,
        image_count_diff=img_diff,
        annotation_count_diff=ann_diff,
        class_distribution_diff=class_diff,
        findings_diff=FindingDiff(
            new_findings=new_findings,
            resolved_findings=resolved_findings,
            persisting_findings_count=persisting_count,
        ),
        regressions=regressions,
        has_regressions=has_regressions,
        policy_status_changed=status_changed,
        coverage_notes=coverage_notes,
        summary=summary,
    )


def compare_reports_cli(baseline_path: Path, current_path: Path) -> int:
    """CLI handler to compare two audit report JSON files."""
    try:
        with open(baseline_path, encoding="utf-8") as f:
            base_data = json.load(f)
        base_snapshot = AuditSnapshot.model_validate(base_data)
    except Exception as e:
        err_console.print(f"[bold red]Failed to load baseline JSON {baseline_path}:[/bold red] {e}")
        return ExitCode.INVALID_USAGE

    try:
        with open(current_path, encoding="utf-8") as f:
            curr_data = json.load(f)
        curr_snapshot = AuditSnapshot.model_validate(curr_data)
    except Exception as e:
        err_console.print(f"[bold red]Failed to load current JSON {current_path}:[/bold red] {e}")
        return ExitCode.INVALID_USAGE

    diff = compare_snapshots(base_snapshot, curr_snapshot)

    # Render terminal output
    table = Table(title="DatasetGate Baseline Comparison", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Baseline", style="white")
    table.add_column("Current", style="white")
    table.add_column("Difference", style="bold")

    table.add_row(
        "Fingerprint",
        base_snapshot.dataset_fingerprint,
        curr_snapshot.dataset_fingerprint,
        "Identical" if diff.is_identical else "Modified",
    )
    table.add_row(
        "Total Images",
        str(base_snapshot.statistics.total_images),
        str(curr_snapshot.statistics.total_images),
        f"{diff.image_count_diff:+d}",
    )
    table.add_row(
        "Total Annotations",
        str(base_snapshot.statistics.total_annotations),
        str(curr_snapshot.statistics.total_annotations),
        f"{diff.annotation_count_diff:+d}",
    )
    table.add_row(
        "Policy Status",
        base_snapshot.policy_result.status,
        curr_snapshot.policy_result.status,
        "Regressed"
        if diff.policy_status_changed and not curr_snapshot.policy_result.passed
        else "Unchanged",
    )
    table.add_row(
        "Total Findings",
        str(len(base_snapshot.findings)),
        str(len(curr_snapshot.findings)),
        f"{len(diff.findings_diff.new_findings) - len(diff.findings_diff.resolved_findings):+d}",
    )

    console.print(table)

    if diff.coverage_notes:
        console.print("\n[bold yellow]Coverage Notes:[/bold yellow]")
        for note in diff.coverage_notes:
            console.print(f"  [yellow]ℹ[/yellow] {note}")

    # Regressions or Pass Panel
    if diff.has_regressions:
        console.print("\n[bold red]Detected Quality Regressions:[/bold red]")
        for reg in diff.regressions:
            console.print(f"  [red]&times;[/red] {reg}")
        console.print(
            Panel(
                f"[bold red]REGRESSION DETECTED[/bold red]\n{diff.summary}",
                border_style="red",
            )
        )
        return ExitCode.GATE_FAILED
    else:
        console.print(
            Panel(
                f"[bold green]NO REGRESSIONS DETECTED[/bold green]\n{diff.summary}",
                border_style="green",
            )
        )
        return ExitCode.SUCCESS
