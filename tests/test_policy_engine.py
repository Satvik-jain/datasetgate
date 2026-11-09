"""Unit tests for statistics calculation and policy engine."""

from pathlib import Path

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.models import (
    BoundingBox,
    DatasetManifest,
    DatasetStatistics,
    Finding,
    FindingCategory,
    ImageAnnotation,
    ImageMetadata,
    Severity,
)
from datasetgate.policies.engine import PolicyEngine
from datasetgate.validators.distribution import compute_dataset_statistics


def test_compute_dataset_statistics():
    manifest = DatasetManifest(
        format="yolo",
        dataset_root=Path("/fake"),
        splits=["train", "val"],
        classes={0: "car", 1: "truck", 2: "bicycle"},
        images=[
            ImageMetadata(relative_path="train/img1.jpg", split="train"),
            ImageMetadata(relative_path="train/img2.jpg", split="train"),
            ImageMetadata(relative_path="train/img3.jpg", split="train"),
            ImageMetadata(relative_path="val/img4.jpg", split="val"),
        ],
        annotations=[
            ImageAnnotation(
                image_relative_path="train/img1.jpg",
                split="train",
                boxes=[
                    BoundingBox(
                        class_id=0,
                        class_name="car",
                        x_min=0.1,
                        y_min=0.1,
                        x_max=0.3,
                        y_max=0.3,
                        width=0.2,
                        height=0.2,
                    ),
                    BoundingBox(
                        class_id=0,
                        class_name="car",
                        x_min=0.4,
                        y_min=0.4,
                        x_max=0.6,
                        y_max=0.6,
                        width=0.2,
                        height=0.2,
                    ),
                ],
            ),
            ImageAnnotation(
                image_relative_path="train/img2.jpg",
                split="train",
                boxes=[
                    BoundingBox(
                        class_id=1,
                        class_name="truck",
                        x_min=0.1,
                        y_min=0.1,
                        x_max=0.5,
                        y_max=0.5,
                        width=0.4,
                        height=0.4,
                    ),
                ],
            ),
            # Empty label
            ImageAnnotation(
                image_relative_path="train/img3.jpg",
                split="train",
                boxes=[],
                is_empty_label=True,
            ),
            ImageAnnotation(
                image_relative_path="val/img4.jpg",
                split="val",
                boxes=[
                    BoundingBox(
                        class_id=0,
                        class_name="car",
                        x_min=0.2,
                        y_min=0.2,
                        x_max=0.4,
                        y_max=0.4,
                        width=0.2,
                        height=0.2,
                    ),
                ],
            ),
        ],
    )

    stats = compute_dataset_statistics(manifest)

    assert stats.total_images == 4
    assert stats.total_annotations == 4
    assert stats.images_per_split == {"train": 3, "val": 1}
    assert stats.annotations_per_split == {"train": 3, "val": 1}
    assert stats.instances_per_class == {"car": 3, "truck": 1}
    assert stats.empty_label_counts == {"train": 1}
    assert stats.empty_label_rate == 0.25  # 1 out of 4 images
    assert stats.class_imbalance_ratio == 3.0  # max 3 / min 1

    # Missing bicycle in both train and val
    assert "bicycle" in stats.missing_classes_per_split["train"]
    assert "truck" in stats.missing_classes_per_split["val"]


def test_policy_engine_missing_class_in_train():
    manifest = DatasetManifest(
        format="yolo",
        dataset_root=Path("/fake"),
        splits=["train"],
        classes={0: "car", 1: "plane"},
        images=[ImageMetadata(relative_path="train/1.jpg", split="train")],
        annotations=[
            ImageAnnotation(
                image_relative_path="train/1.jpg",
                split="train",
                boxes=[
                    BoundingBox(
                        class_id=0,
                        class_name="car",
                        x_min=0,
                        y_min=0,
                        x_max=1,
                        y_max=1,
                        width=1,
                        height=1,
                    )
                ],
            )
        ],
    )

    stats = compute_dataset_statistics(manifest)
    engine = PolicyEngine()
    config = DatasetGateConfig()
    config.policy.require_all_classes_in_train = True

    findings, res = engine.evaluate(manifest, stats, [], config)
    assert res.passed is False
    assert res.status == "FAILED"
    assert any(f.rule_id == "MISSING_CLASS_IN_TRAIN" for f in findings)


def test_policy_engine_severity_override():
    manifest = DatasetManifest(
        format="yolo",
        dataset_root=Path("/fake"),
        splits=["train"],
        classes={0: "car"},
        images=[ImageMetadata(relative_path="train/1.jpg", split="train")],
        annotations=[
            ImageAnnotation(
                image_relative_path="train/1.jpg",
                split="train",
                boxes=[
                    BoundingBox(
                        class_id=0,
                        class_name="car",
                        x_min=0,
                        y_min=0,
                        x_max=1,
                        y_max=1,
                        width=1,
                        height=1,
                    )
                ],
            )
        ],
    )

    stats = compute_dataset_statistics(manifest)
    initial_findings = [
        Finding(
            rule_id="BBOX_OUT_OF_BOUNDS",
            severity=Severity.ERROR,
            category=FindingCategory.ANNOTATION_INTEGRITY,
            message="Bounding box exceeds edge by 1px",
        )
    ]

    engine = PolicyEngine()
    config = DatasetGateConfig()
    # Override rule severity from error to warning
    config.policy.rule_severities = {"BBOX_OUT_OF_BOUNDS": Severity.WARNING}
    config.policy.fail_on = [Severity.ERROR]

    updated_findings, res = engine.evaluate(manifest, stats, initial_findings, config)
    assert updated_findings[0].severity == Severity.WARNING
    assert res.passed is True
    assert res.status == "PASSED"


def test_corrupted_image_policy_actions():
    manifest = DatasetManifest(format="yolo", dataset_root=Path("/fake"))
    stats = DatasetStatistics(total_images=1)
    engine = PolicyEngine()

    raw_finding = Finding(
        rule_id="CORRUPTED_IMAGE",
        severity=Severity.ERROR,
        category=FindingCategory.IMAGE_INTEGRITY,
        message="Corrupted header",
    )

    # Test ignore
    cfg_ignore = DatasetGateConfig()
    cfg_ignore.policy.corrupted_image_policy = "ignore"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_ignore)
    assert len(findings) == 0
    assert res.passed is True

    # Test warn
    cfg_warn = DatasetGateConfig()
    cfg_warn.policy.corrupted_image_policy = "warn"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_warn)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert res.passed is True  # default fail_on: [error]

    # Test fail
    cfg_fail = DatasetGateConfig()
    cfg_fail.policy.corrupted_image_policy = "fail"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_fail)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert res.passed is False


def test_missing_image_policy_actions():
    manifest = DatasetManifest(format="coco", dataset_root=Path("/fake"))
    stats = DatasetStatistics(total_images=1)
    engine = PolicyEngine()

    raw_finding = Finding(
        rule_id="MISSING_IMAGE_FILE",
        severity=Severity.ERROR,
        category=FindingCategory.IMAGE_INTEGRITY,
        message="File not on disk",
    )

    # Test ignore
    cfg_ignore = DatasetGateConfig()
    cfg_ignore.policy.missing_image_policy = "ignore"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_ignore)
    assert len(findings) == 0
    assert res.passed is True

    # Test warn
    cfg_warn = DatasetGateConfig()
    cfg_warn.policy.missing_image_policy = "warn"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_warn)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert res.passed is True

    # Test fail
    cfg_fail = DatasetGateConfig()
    cfg_fail.policy.missing_image_policy = "fail"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_fail)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert res.passed is False


def test_out_of_bounds_policy_actions():
    manifest = DatasetManifest(format="yolo", dataset_root=Path("/fake"))
    stats = DatasetStatistics(total_images=1, total_annotations=1)
    engine = PolicyEngine()

    raw_finding = Finding(
        rule_id="BBOX_OUT_OF_BOUNDS",
        severity=Severity.ERROR,
        category=FindingCategory.ANNOTATION_INTEGRITY,
        message="Box outside [0, 1]",
    )

    # Test ignore
    cfg_ignore = DatasetGateConfig()
    cfg_ignore.policy.out_of_bounds_policy = "ignore"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_ignore)
    assert len(findings) == 0
    assert res.passed is True

    # Test warn
    cfg_warn = DatasetGateConfig()
    cfg_warn.policy.out_of_bounds_policy = "warn"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_warn)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert res.passed is True

    # Test fail
    cfg_fail = DatasetGateConfig()
    cfg_fail.policy.out_of_bounds_policy = "fail"
    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg_fail)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert res.passed is False


def test_rule_severities_overrides_policy_action():
    manifest = DatasetManifest(format="yolo", dataset_root=Path("/fake"))
    stats = DatasetStatistics(total_images=1, total_annotations=1)
    engine = PolicyEngine()

    raw_finding = Finding(
        rule_id="BBOX_OUT_OF_BOUNDS",
        severity=Severity.ERROR,
        category=FindingCategory.ANNOTATION_INTEGRITY,
        message="Box outside [0, 1]",
    )

    # Policy action says warn, but rule_severities says error
    cfg = DatasetGateConfig()
    cfg.policy.out_of_bounds_policy = "warn"
    cfg.policy.rule_severities = {"BBOX_OUT_OF_BOUNDS": Severity.ERROR}
    cfg.policy.fail_on = [Severity.ERROR]

    findings, res = engine.evaluate(manifest, stats, [raw_finding], cfg)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert res.passed is False
