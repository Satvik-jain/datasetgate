"""Integration tests for perceptual near-duplicate detection, exact duplicate suppression,
policy engine evaluation, and snapshot baseline comparison.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from datasetgate.comparison.engine import compare_snapshots
from datasetgate.core.config import (
    DatasetGateConfig,
    PolicyAction,
)
from datasetgate.core.constants import ExitCode
from datasetgate.core.engine import run_audit, run_snapshot
from datasetgate.core.models import (
    AuditSnapshot,
    DatasetManifest,
    DatasetStatistics,
    Finding,
    FindingCategory,
    ImageMetadata,
    PolicyResult,
    Severity,
)
from datasetgate.policies.engine import PolicyEngine
from datasetgate.validators.duplicates import DuplicateValidator


def create_pattern_image(color: tuple[int, int, int] = (100, 150, 200)) -> Image.Image:
    """Create a structured test image with recognizable geometric shapes."""
    img = Image.new("RGB", (320, 240), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, 120, 140], fill=(220, 50, 50))
    draw.ellipse([140, 50, 250, 160], fill=(50, 220, 50))
    draw.line([(0, 120), (320, 120)], fill=(255, 255, 0), width=4)
    return img


def create_different_image() -> Image.Image:
    """Create an image visually dissimilar from create_pattern_image."""
    img = Image.new("RGB", (320, 240), (20, 20, 20))
    draw = ImageDraw.Draw(img)
    for i in range(0, 320, 20):
        draw.line([(i, 0), (i, 240)], fill=(255, 255, 255), width=2)
    return img


# =========================================================================
# DuplicateValidator Perceptual & Suppression Tests
# =========================================================================


def test_duplicate_validator_disabled_by_default(tmp_path: Path):
    """When perceptual_hash.enabled is False, no perceptual findings are generated."""
    img = create_pattern_image()
    p1 = tmp_path / "img1.jpg"
    p2 = tmp_path / "img2.jpg"
    img.save(p1)
    # Save slightly resized version (perceptual duplicate, different SHA256)
    img.resize((280, 210)).save(p2)

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        images=[
            ImageMetadata(relative_path="img1.jpg", split="train"),
            ImageMetadata(relative_path="img2.jpg", split="train"),
        ],
    )
    config = DatasetGateConfig()
    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    assert len(findings) == 0
    assert validator.perceptual_coverage["enabled"] is False
    assert validator.perceptual_coverage["executed"] is False


def test_perceptual_duplicate_intra_split(tmp_path: Path):
    """Detects near-duplicates within the same split when enabled."""
    img = create_pattern_image()
    p1 = tmp_path / "img1.png"
    p2 = tmp_path / "img2.jpg"
    img.save(p1, format="PNG")
    # Save as JPEG with high compression (different SHA256, small Hamming distance)
    img.save(p2, format="JPEG", quality=40)

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        images=[
            ImageMetadata(relative_path="img1.png", split="train"),
            ImageMetadata(relative_path="img2.jpg", split="train"),
        ],
    )
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    config.policy.perceptual_hash.max_hamming_distance = 6

    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    dup_findings = [f for f in findings if f.rule_id == "PERCEPTUAL_DUPLICATE"]
    assert len(dup_findings) == 1
    f = dup_findings[0]
    assert f.file_path == "img1.png"
    assert f.related_paths == ["img2.jpg"]
    assert f.split == "train"
    assert f.metadata["algorithm"] == "phash-dct-63-ac-median"
    assert f.metadata["hash_bits"] == 63
    assert f.metadata["hamming_distance"] <= 6
    assert f.metadata["bit_agreement_pct"] >= 90.0


def test_perceptual_split_leakage_cross_split(tmp_path: Path):
    """Detects near-duplicates across different splits as cross-split leakage."""
    img = create_pattern_image()
    p_train = tmp_path / "train_01.png"
    p_val = tmp_path / "val_01.jpg"
    img.save(p_train, format="PNG")
    img.resize((300, 225)).save(p_val, format="JPEG", quality=85)

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train", "val"],
        images=[
            ImageMetadata(relative_path="train_01.png", split="train"),
            ImageMetadata(relative_path="val_01.jpg", split="val"),
        ],
    )
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True

    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    leak_findings = [f for f in findings if f.rule_id == "PERCEPTUAL_SPLIT_LEAKAGE"]
    assert len(leak_findings) == 1
    f = leak_findings[0]
    assert f.file_path == "train_01.png"
    assert f.related_paths == ["val_01.jpg"]
    assert f.metadata["split"] == "train"
    assert f.metadata["related_split"] == "val"


def test_exact_duplicate_pair_suppression(tmp_path: Path):
    """Exact duplicate pairs (identical SHA-256) are suppressed from perceptual results."""
    img = create_pattern_image()
    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    p3 = tmp_path / "c_resized.png"
    img.save(p1)
    img.save(p2)  # byte-identical to p1
    img.resize((290, 220)).save(p3)  # near-duplicate to p1 and p2, different SHA-256

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        images=[
            ImageMetadata(relative_path="a.png", split="train"),
            ImageMetadata(relative_path="b.png", split="train"),
            ImageMetadata(relative_path="c_resized.png", split="train"),
        ],
    )
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True

    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    # 1. Exact duplicate finding must be emitted for (a.png, b.png)
    exact_findings = [f for f in findings if f.rule_id == "EXACT_DUPLICATE_IMAGE"]
    assert len(exact_findings) >= 1

    # 2. Perceptual findings: (a.png, b.png) must be suppressed!
    # Only pairs involving c_resized.png (a.png, c_resized.png) and (b.png, c_resized.png) should appear.
    perceptual_findings = [f for f in findings if f.rule_id == "PERCEPTUAL_DUPLICATE"]
    for pf in perceptual_findings:
        pair = (pf.file_path, pf.related_paths[0])
        assert pair != ("a.png", "b.png")
        assert pair != ("b.png", "a.png")

    assert len(perceptual_findings) == 2


def test_exact_duplicate_suppression_three_images(tmp_path: Path):
    """When 3 images are byte-identical, all 3 exact pairs are suppressed from perceptual results."""
    img = create_pattern_image()
    p1 = tmp_path / "x1.png"
    p2 = tmp_path / "x2.png"
    p3 = tmp_path / "x3.png"
    img.save(p1)
    img.save(p2)
    img.save(p3)

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        images=[
            ImageMetadata(relative_path="x1.png", split="train"),
            ImageMetadata(relative_path="x2.png", split="train"),
            ImageMetadata(relative_path="x3.png", split="train"),
        ],
    )
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True

    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    # Exact findings present
    exact_findings = [f for f in findings if f.rule_id == "EXACT_DUPLICATE_IMAGE"]
    assert len(exact_findings) == 3

    # Perceptual findings must be 0 because all pairs are exact duplicates
    perceptual_findings = [f for f in findings if f.rule_id == "PERCEPTUAL_DUPLICATE"]
    assert len(perceptual_findings) == 0


def test_dissimilar_images_produce_no_perceptual_finding(tmp_path: Path):
    """Visually dissimilar images exceeding threshold produce 0 findings."""
    img1 = create_pattern_image()
    img2 = create_different_image()
    p1 = tmp_path / "scene.jpg"
    p2 = tmp_path / "lines.jpg"
    img1.save(p1)
    img2.save(p2)

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        images=[
            ImageMetadata(relative_path="scene.jpg", split="train"),
            ImageMetadata(relative_path="lines.jpg", split="train"),
        ],
    )
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    config.policy.perceptual_hash.max_hamming_distance = 6

    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    perceptual_findings = [
        f for f in findings if f.rule_id in ("PERCEPTUAL_DUPLICATE", "PERCEPTUAL_SPLIT_LEAKAGE")
    ]
    assert len(perceptual_findings) == 0


def test_perceptual_hash_unavailable_on_decode_error(tmp_path: Path):
    """An image causing a decode error emits PERCEPTUAL_HASH_UNAVAILABLE and does not crash audit."""
    good_img = create_pattern_image()
    p_good = tmp_path / "good.jpg"
    p_bad = tmp_path / "corrupted.jpg"
    good_img.save(p_good)
    # Write corrupt header bytes that pass file existence but fail decode
    p_bad.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00truncated_unreadable")

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        images=[
            ImageMetadata(relative_path="good.jpg", split="train", is_valid=True),
            ImageMetadata(relative_path="corrupted.jpg", split="train", is_valid=True),
        ],
    )
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True

    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    unavail = [f for f in findings if f.rule_id == "PERCEPTUAL_HASH_UNAVAILABLE"]
    assert len(unavail) == 1
    assert unavail[0].file_path == "corrupted.jpg"
    assert validator.perceptual_coverage["skipped_images_count"] == 1


def test_candidate_truncation_emits_finding_with_policy_action(tmp_path: Path):
    """Candidate limit exhaustion emits PERCEPTUAL_ANALYSIS_TRUNCATED with configured severity."""
    base_img = create_pattern_image()
    images = []
    # Create 5 images with subtle modifications so all pair up (10 pairs total)
    for i in range(5):
        p = tmp_path / f"img_{i}.jpg"
        # resize with 1 pixel difference
        base_img.resize((320 - i, 240)).save(p, format="JPEG", quality=85)
        images.append(ImageMetadata(relative_path=f"img_{i}.jpg", split="train"))

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        images=images,
    )
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    config.policy.perceptual_hash.max_candidate_pairs = 3  # Force truncation after 3 pairs
    config.policy.perceptual_hash.truncation_action = PolicyAction.WARN

    validator = DuplicateValidator()
    findings = validator.validate(manifest, config)

    trunc_findings = [f for f in findings if f.rule_id == "PERCEPTUAL_ANALYSIS_TRUNCATED"]
    assert len(trunc_findings) == 1
    assert trunc_findings[0].severity == Severity.WARNING
    assert trunc_findings[0].metadata["max_candidate_pairs"] == 3
    assert validator.perceptual_coverage["is_truncated"] is True
    assert validator.perceptual_coverage["complete"] is False


# =========================================================================
# PolicyEngine Integration Tests
# =========================================================================


def test_policy_engine_perceptual_actions(tmp_path: Path):
    """Test ignore, warn, and fail policy actions for perceptual rules."""
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    config.policy.perceptual_hash.duplicate_policy = PolicyAction.FAIL
    config.policy.perceptual_hash.split_leakage_policy = PolicyAction.WARN

    manifest = DatasetManifest(format="yolo", dataset_root=tmp_path, splits=["train", "val"])
    stats = DatasetStatistics(total_images=2)

    findings = [
        Finding(
            rule_id="PERCEPTUAL_DUPLICATE",
            severity=Severity.WARNING,  # should be upgraded to ERROR by duplicate_policy: fail
            category=FindingCategory.DUPLICATES_AND_LEAKAGE,
            message="Near-duplicate found",
        ),
        Finding(
            rule_id="PERCEPTUAL_SPLIT_LEAKAGE",
            severity=Severity.ERROR,  # should be downgraded to WARNING by split_leakage_policy: warn
            category=FindingCategory.DUPLICATES_AND_LEAKAGE,
            message="Leakage found",
        ),
    ]

    engine = PolicyEngine()
    evaluated_findings, result = engine.evaluate(manifest, stats, findings, config)

    f_dup = next(f for f in evaluated_findings if f.rule_id == "PERCEPTUAL_DUPLICATE")
    f_leak = next(f for f in evaluated_findings if f.rule_id == "PERCEPTUAL_SPLIT_LEAKAGE")

    assert f_dup.severity == Severity.ERROR
    assert f_leak.severity == Severity.WARNING
    assert result.passed is False  # Fails because fail_on: [error] and f_dup is ERROR


def test_policy_engine_rule_severity_override(tmp_path: Path):
    """Explicit rule_severities overrides perceptual policy action."""
    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    config.policy.perceptual_hash.duplicate_policy = PolicyAction.FAIL
    config.policy.rule_severities = {"PERCEPTUAL_DUPLICATE": Severity.WARNING}

    manifest = DatasetManifest(format="yolo", dataset_root=tmp_path, splits=["train"])
    stats = DatasetStatistics(total_images=2)

    findings = [
        Finding(
            rule_id="PERCEPTUAL_DUPLICATE",
            severity=Severity.ERROR,
            category=FindingCategory.DUPLICATES_AND_LEAKAGE,
            message="Near-duplicate found",
        ),
    ]

    engine = PolicyEngine()
    evaluated_findings, result = engine.evaluate(manifest, stats, findings, config)

    f_dup = evaluated_findings[0]
    assert f_dup.severity == Severity.WARNING
    assert result.passed is True  # Passed because warning does not trigger fail_on: [error]


# =========================================================================
# Snapshot and Baseline Comparison Tests
# =========================================================================


def test_comparison_legacy_baseline_without_coverage(tmp_path: Path):
    """Comparing against a legacy v0.1.2 baseline (no analysis_coverage) does not treat new perceptual findings as regressions."""
    # Legacy baseline snapshot without metadata["analysis_coverage"]
    baseline = AuditSnapshot(
        dataset_fingerprint="base123",
        format="yolo",
        dataset_name="demo",
        statistics=DatasetStatistics(total_images=10),
        findings=[],
        policy_result=PolicyResult(passed=True, status="PASSED"),
        metadata={},  # legacy: empty metadata
    )

    # Current snapshot with perceptual hashing enabled finding a near-duplicate error
    current = AuditSnapshot(
        dataset_fingerprint="base123",
        format="yolo",
        dataset_name="demo",
        statistics=DatasetStatistics(total_images=10),
        findings=[
            Finding(
                rule_id="PERCEPTUAL_DUPLICATE",
                severity=Severity.ERROR,
                category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                message="Perceptual duplicate detected",
            )
        ],
        policy_result=PolicyResult(passed=False, status="FAILED"),
        metadata={
            "analysis_coverage": {
                "perceptual_hash": {
                    "enabled": True,
                    "executed": True,
                    "complete": True,
                    "algorithm": "phash-dct-63-ac-median",
                    "max_hamming_distance": 6,
                }
            }
        },
    )

    diff = compare_snapshots(baseline, current)
    # Perceptual finding must NOT be classified as regression because baseline never executed perceptual check!
    assert diff.has_regressions is False
    assert len(diff.regressions) == 0
    assert any("not present in baseline" in note for note in diff.coverage_notes)


def test_comparison_disabled_current_does_not_resolve_baseline_perceptual_findings():
    """When current audit disables perceptual hash, baseline perceptual findings are not classified as resolved."""
    baseline = AuditSnapshot(
        dataset_fingerprint="base123",
        format="yolo",
        dataset_name="demo",
        statistics=DatasetStatistics(total_images=10),
        findings=[
            Finding(
                rule_id="PERCEPTUAL_DUPLICATE",
                severity=Severity.WARNING,
                category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                message="Perceptual duplicate in baseline",
            )
        ],
        policy_result=PolicyResult(passed=True, status="PASSED"),
        metadata={
            "analysis_coverage": {
                "perceptual_hash": {
                    "enabled": True,
                    "executed": True,
                    "complete": True,
                    "algorithm": "phash-dct-63-ac-median",
                    "max_hamming_distance": 6,
                }
            }
        },
    )

    current = AuditSnapshot(
        dataset_fingerprint="base123",
        format="yolo",
        dataset_name="demo",
        statistics=DatasetStatistics(total_images=10),
        findings=[],
        policy_result=PolicyResult(passed=True, status="PASSED"),
        metadata={
            "analysis_coverage": {
                "perceptual_hash": {
                    "enabled": False,
                    "executed": False,
                    "complete": True,
                }
            }
        },
    )

    diff = compare_snapshots(baseline, current)
    # The baseline finding must NOT be resolved because current audit did not evaluate it
    assert len(diff.findings_diff.resolved_findings) == 0
    assert any("not executed in current audit" in note for note in diff.coverage_notes)


def test_comparison_different_thresholds_marked_not_comparable():
    """Comparing snapshots with different Hamming distance thresholds marks coverage as not directly comparable."""
    baseline = AuditSnapshot(
        dataset_fingerprint="fp1",
        format="yolo",
        dataset_name="demo",
        statistics=DatasetStatistics(total_images=10),
        findings=[],
        policy_result=PolicyResult(passed=True, status="PASSED"),
        metadata={
            "analysis_coverage": {
                "perceptual_hash": {
                    "enabled": True,
                    "executed": True,
                    "complete": True,
                    "algorithm": "phash-dct-63-ac-median",
                    "max_hamming_distance": 4,
                }
            }
        },
    )

    current = AuditSnapshot(
        dataset_fingerprint="fp1",
        format="yolo",
        dataset_name="demo",
        statistics=DatasetStatistics(total_images=10),
        findings=[
            Finding(
                rule_id="PERCEPTUAL_DUPLICATE",
                severity=Severity.ERROR,
                category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                message="Candidate at distance 6",
            )
        ],
        policy_result=PolicyResult(passed=False, status="FAILED"),
        metadata={
            "analysis_coverage": {
                "perceptual_hash": {
                    "enabled": True,
                    "executed": True,
                    "complete": True,
                    "algorithm": "phash-dct-63-ac-median",
                    "max_hamming_distance": 8,  # Different threshold!
                }
            }
        },
    )

    diff = compare_snapshots(baseline, current)
    assert diff.has_regressions is False
    assert any("threshold differs" in note for note in diff.coverage_notes)


# =========================================================================
# End-to-End Audits on Synthetic YOLO & COCO Datasets
# =========================================================================


def test_end_to_end_yolo_audit_with_perceptual_hashing(tmp_path: Path):
    """Full end-to-end audit on a YOLO dataset with perceptual duplicate detection."""
    from datasetgate.synthetic.generator import generate_synthetic_yolo_dataset

    dataset_dir = tmp_path / "yolo_data"
    generate_synthetic_yolo_dataset(dataset_dir)

    # Add a near-duplicate image into train split
    train_img_dir = dataset_dir / "images" / "train"
    existing_img_path = next(train_img_dir.glob("*.jpg"))
    with Image.open(existing_img_path) as orig_img:
        near_dup = orig_img.resize((orig_img.width - 2, orig_img.height))
        near_dup_path = train_img_dir / "near_dup_train.jpg"
        near_dup.save(near_dup_path, format="JPEG", quality=80)

    # Empty label file for the new image
    train_lbl_dir = dataset_dir / "labels" / "train"
    (train_lbl_dir / "near_dup_train.txt").write_text("", encoding="utf-8")

    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    config.policy.perceptual_hash.duplicate_policy = PolicyAction.WARN
    config.reporting.output_dir = str(tmp_path / "reports")

    exit_code = run_audit(dataset_dir, config)
    assert exit_code in (ExitCode.SUCCESS, ExitCode.GATE_FAILED)

    report_json_path = tmp_path / "reports" / "report.json"
    assert report_json_path.is_file()

    report_data = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert "analysis_coverage" in report_data["metadata"]
    p_cov = report_data["metadata"]["analysis_coverage"]["perceptual_hash"]
    assert p_cov["enabled"] is True
    assert p_cov["executed"] is True
    assert p_cov["successfully_hashed_count"] > 0


def test_end_to_end_coco_audit_with_perceptual_hashing(tmp_path: Path):
    """Full end-to-end audit on a COCO dataset with perceptual duplicate detection."""
    from datasetgate.synthetic.generator import generate_synthetic_coco_dataset

    dataset_dir = tmp_path / "coco_data"
    generate_synthetic_coco_dataset(dataset_dir)

    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    config.policy.perceptual_hash.duplicate_policy = PolicyAction.WARN
    config.reporting.output_dir = str(tmp_path / "coco_reports")

    exit_code = run_audit(dataset_dir, config)
    assert exit_code in (ExitCode.SUCCESS, ExitCode.GATE_FAILED)

    report_json = tmp_path / "coco_reports" / "report.json"
    assert report_json.is_file()
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert data["format"] == "coco"
    assert data["metadata"]["analysis_coverage"]["perceptual_hash"]["enabled"] is True


def test_run_snapshot_persists_same_coverage_metadata(tmp_path: Path):
    """run_snapshot() persists identical analysis_coverage metadata as run_audit()."""
    from datasetgate.synthetic.generator import generate_synthetic_yolo_dataset

    dataset_dir = tmp_path / "yolo_data"
    generate_synthetic_yolo_dataset(dataset_dir)

    config = DatasetGateConfig()
    config.policy.perceptual_hash.enabled = True
    snapshot_path = tmp_path / "baseline_snap.json"

    code = run_snapshot(dataset_dir, config, snapshot_path)
    assert code == ExitCode.SUCCESS
    assert snapshot_path.is_file()

    snap_data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert "analysis_coverage" in snap_data["metadata"]
    assert snap_data["metadata"]["analysis_coverage"]["perceptual_hash"]["enabled"] is True
    assert (
        snap_data["metadata"]["analysis_coverage"]["perceptual_hash"]["algorithm"]
        == "phash-dct-63-ac-median"
    )
