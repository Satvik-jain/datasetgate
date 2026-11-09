"""Unit tests for baseline comparison and regression detection."""

from pathlib import Path

from typer.testing import CliRunner

from datasetgate.cli.main import app
from datasetgate.comparison.engine import compare_snapshots
from datasetgate.core.constants import ExitCode
from datasetgate.core.models import (
    AuditSnapshot,
    DatasetStatistics,
    Finding,
    FindingCategory,
    PolicyResult,
    Severity,
)

runner = CliRunner()


def make_snapshot(
    fingerprint: str = "base123",
    images: int = 100,
    annotations: int = 500,
    classes: dict[str, int] | None = None,
    findings: list[Finding] | None = None,
    passed: bool = True,
    leakage_count: int = 0,
    missing_train: list[str] | None = None,
) -> AuditSnapshot:
    """Helper to create test snapshots."""
    return AuditSnapshot(
        dataset_fingerprint=fingerprint,
        format="yolo",
        dataset_name="demo",
        statistics=DatasetStatistics(
            total_images=images,
            total_annotations=annotations,
            instances_per_class=classes or {"car": 300, "truck": 200},
            leakage_groups_count=leakage_count,
            missing_classes_per_split={"train": missing_train or []},
            class_imbalance_ratio=1.5,
        ),
        findings=findings or [],
        policy_result=PolicyResult(
            passed=passed,
            status="PASSED" if passed else "FAILED",
        ),
    )


def test_compare_identical_snapshots():
    base = make_snapshot()
    curr = make_snapshot()

    diff = compare_snapshots(base, curr)
    assert diff.is_identical is True
    assert diff.image_count_diff == 0
    assert diff.annotation_count_diff == 0
    assert diff.has_regressions is False
    assert len(diff.findings_diff.new_findings) == 0


def test_compare_new_error_regression():
    base = make_snapshot(fingerprint="base_fp")
    curr = make_snapshot(
        fingerprint="curr_fp",
        images=105,
        annotations=520,
        findings=[
            Finding(
                rule_id="CORRUPTED_IMAGE",
                severity=Severity.ERROR,
                category=FindingCategory.IMAGE_INTEGRITY,
                message="Broken image header",
                file_path="train/corrupted.jpg",
            )
        ],
        passed=False,
    )

    diff = compare_snapshots(base, curr)
    assert diff.is_identical is False
    assert diff.image_count_diff == 5
    assert diff.annotation_count_diff == 20
    assert len(diff.findings_diff.new_findings) == 1
    assert diff.has_regressions is True
    assert any("Introduced 1 new error" in r for r in diff.regressions)
    assert any("Policy status regressed" in r for r in diff.regressions)


def test_compare_resolved_finding():
    initial_finding = Finding(
        rule_id="BBOX_OUT_OF_BOUNDS",
        severity=Severity.WARNING,
        category=FindingCategory.ANNOTATION_INTEGRITY,
        message="Minor edge overlap",
        file_path="train/box.jpg",
    )
    base = make_snapshot(fingerprint="base", findings=[initial_finding])
    curr = make_snapshot(fingerprint="curr", findings=[])  # Issue resolved

    diff = compare_snapshots(base, curr)
    assert len(diff.findings_diff.resolved_findings) == 1
    assert diff.findings_diff.resolved_findings[0].rule_id == "BBOX_OUT_OF_BOUNDS"
    assert diff.has_regressions is False


def test_compare_cli_command(tmp_path: Path):
    base_snap = make_snapshot(fingerprint="base111")
    curr_snap = make_snapshot(fingerprint="curr222", images=110)

    base_file = tmp_path / "base.json"
    curr_file = tmp_path / "curr.json"

    base_file.write_text(base_snap.model_dump_json(), encoding="utf-8")
    curr_file.write_text(curr_snap.model_dump_json(), encoding="utf-8")

    result = runner.invoke(app, ["compare", str(base_file), str(curr_file)])
    assert result.exit_code == ExitCode.SUCCESS
    assert "DatasetGate Baseline Comparison" in result.stdout
    assert "+10" in result.stdout


def test_audit_with_missing_baseline_fails(tmp_path: Path):
    """Audit should fail with INVALID_USAGE (exit code 2) when --baseline does not exist."""
    # Create minimal dataset
    ds = tmp_path / "dataset"
    (ds / "images" / "train").mkdir(parents=True)
    (ds / "labels" / "train").mkdir(parents=True)

    non_existent_baseline = tmp_path / "does_not_exist_report.json"

    result = runner.invoke(
        app,
        ["audit", str(ds), "--baseline", str(non_existent_baseline)],
    )
    assert result.exit_code == ExitCode.INVALID_USAGE
    assert "Baseline snapshot file does not exist" in result.stderr


def test_audit_with_malformed_json_baseline_fails(tmp_path: Path):
    """Audit should fail with INVALID_USAGE (exit code 2) when --baseline has malformed JSON."""
    ds = tmp_path / "dataset"
    (ds / "images" / "train").mkdir(parents=True)
    (ds / "labels" / "train").mkdir(parents=True)

    corrupt_baseline = tmp_path / "corrupt_baseline.json"
    corrupt_baseline.write_text("{ not valid json !!! }", encoding="utf-8")

    result = runner.invoke(
        app,
        ["audit", str(ds), "--baseline", str(corrupt_baseline)],
    )
    assert result.exit_code == ExitCode.INVALID_USAGE
    assert "Baseline snapshot file is malformed or unreadable" in result.stderr


def test_audit_with_invalid_schema_baseline_fails(tmp_path: Path):
    """Audit should fail with INVALID_USAGE (exit code 2) when --baseline has invalid snapshot schema."""
    ds = tmp_path / "dataset"
    (ds / "images" / "train").mkdir(parents=True)
    (ds / "labels" / "train").mkdir(parents=True)

    invalid_schema = tmp_path / "invalid_schema.json"
    invalid_schema.write_text('{"foo": "bar", "unknown": 123}', encoding="utf-8")

    result = runner.invoke(
        app,
        ["audit", str(ds), "--baseline", str(invalid_schema)],
    )
    assert result.exit_code == ExitCode.INVALID_USAGE
    assert "Baseline snapshot file is malformed or unreadable" in result.stderr


def test_compare_cli_with_malformed_baseline_fails(tmp_path: Path):
    """compare command should fail with INVALID_USAGE when baseline is malformed."""
    malformed_base = tmp_path / "malformed.json"
    malformed_base.write_text("{bad json}", encoding="utf-8")

    curr_file = tmp_path / "curr.json"
    curr_snap = make_snapshot(fingerprint="curr222")
    curr_file.write_text(curr_snap.model_dump_json(), encoding="utf-8")

    result = runner.invoke(app, ["compare", str(malformed_base), str(curr_file)])
    assert result.exit_code == ExitCode.INVALID_USAGE
    assert "Failed to load baseline JSON" in result.stderr
