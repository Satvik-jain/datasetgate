"""Unit tests for domain models."""

from datasetgate.core.models import (
    AuditSnapshot,
    DatasetStatistics,
    Finding,
    FindingCategory,
    PolicyResult,
    Severity,
)


def test_finding_creation_and_fingerprint():
    f1 = Finding(
        rule_id="BBOX_OUT_OF_BOUNDS",
        severity=Severity.ERROR,
        category=FindingCategory.ANNOTATION_INTEGRITY,
        message="Bounding box exceeds image width",
        file_path="images/train/img01.jpg",
        split="train",
        metadata={"bbox": [0.5, 0.5, 1.2, 0.8]},
    )
    f2 = Finding(
        rule_id="BBOX_OUT_OF_BOUNDS",
        severity=Severity.ERROR,
        category=FindingCategory.ANNOTATION_INTEGRITY,
        message="Bounding box exceeds image width",
        file_path="images/train/img01.jpg",
        split="train",
        metadata={"bbox": [0.5, 0.5, 1.2, 0.8]},
    )
    assert f1.fingerprint() == f2.fingerprint()
    assert len(f1.fingerprint()) == 16


def test_audit_snapshot_serialization():
    stats = DatasetStatistics(
        total_images=10,
        total_annotations=25,
        images_per_split={"train": 8, "val": 2},
        annotations_per_split={"train": 20, "val": 5},
        instances_per_class={"cat": 15, "dog": 10},
        empty_label_counts={"train": 1, "val": 0},
        empty_label_rate=0.1,
        class_imbalance_ratio=1.5,
    )
    finding = Finding(
        rule_id="CORRUPTED_IMAGE",
        severity=Severity.ERROR,
        category=FindingCategory.IMAGE_INTEGRITY,
        message="Image file cannot be decoded",
        file_path="images/train/broken.jpg",
        split="train",
    )
    policy_res = PolicyResult(
        passed=False,
        status="FAILED",
        errors=["CORRUPTED_IMAGE violation"],
        passed_checks=["no_split_leakage"],
    )
    snapshot = AuditSnapshot(
        dataset_fingerprint="abc123def456",
        format="yolo",
        dataset_name="demo_dataset",
        statistics=stats,
        findings=[finding],
        policy_result=policy_res,
    )
    json_data = snapshot.model_dump_json()
    assert "abc123def456" in json_data
    assert "CORRUPTED_IMAGE" in json_data
    restored = AuditSnapshot.model_validate_json(json_data)
    assert restored.statistics.total_images == 10
    assert restored.policy_result.passed is False
