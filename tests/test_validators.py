"""Unit tests for dataset integrity and duplicate validators."""

import io
from pathlib import Path

from PIL import Image

from datasetgate.core.config import DatasetGateConfig, PolicyAction
from datasetgate.core.models import (
    DatasetManifest,
    ImageAnnotation,
    ImageMetadata,
    Severity,
)
from datasetgate.validators.annotations import AnnotationValidator
from datasetgate.validators.duplicates import DuplicateValidator
from datasetgate.validators.image_integrity import ImageIntegrityValidator


def create_sample_png_bytes(width: int = 100, height: int = 100, color: str = "red") -> bytes:
    """Helper to generate valid PNG bytes in memory."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_integrity_validator(tmp_path: Path):
    # Setup test images
    valid_png = tmp_path / "valid.png"
    valid_png.write_bytes(create_sample_png_bytes(64, 48, "blue"))

    corrupted_jpg = tmp_path / "broken.jpg"
    corrupted_jpg.write_bytes(b"corrupted_non_image_header_bytes")

    empty_png = tmp_path / "empty.png"
    empty_png.write_bytes(b"")

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        classes={0: "obj"},
        images=[
            ImageMetadata(relative_path="valid.png", split="train"),
            ImageMetadata(relative_path="broken.jpg", split="train"),
            ImageMetadata(relative_path="empty.png", split="train"),
            ImageMetadata(relative_path="does_not_exist.png", split="train"),
        ],
        annotations=[],
    )

    validator = ImageIntegrityValidator()
    config = DatasetGateConfig()
    findings = validator.validate(manifest, config)

    rule_ids = {f.rule_id for f in findings}
    assert "MISSING_IMAGE_FILE" in rule_ids
    assert "EMPTY_IMAGE_FILE" in rule_ids
    assert "CORRUPTED_IMAGE" in rule_ids

    # Check that valid image was properly updated
    valid_meta = next(img for img in manifest.images if img.relative_path == "valid.png")
    assert valid_meta.is_valid is True
    assert valid_meta.width == 64
    assert valid_meta.height == 48


def test_image_integrity_policy_actions(tmp_path: Path):
    corrupted_jpg = tmp_path / "broken.jpg"
    corrupted_jpg.write_bytes(b"bad_header")

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        classes={0: "obj"},
        images=[
            ImageMetadata(relative_path="broken.jpg", split="train"),
            ImageMetadata(relative_path="missing.jpg", split="train"),
        ],
    )

    validator = ImageIntegrityValidator()

    # Test ignore
    cfg_ignore = DatasetGateConfig()
    cfg_ignore.policy.corrupted_image_policy = PolicyAction.IGNORE
    cfg_ignore.policy.missing_image_policy = PolicyAction.IGNORE
    findings = validator.validate(manifest, cfg_ignore)
    assert not any(f.rule_id in ("CORRUPTED_IMAGE", "MISSING_IMAGE_FILE") for f in findings)

    # Test warn
    cfg_warn = DatasetGateConfig()
    cfg_warn.policy.corrupted_image_policy = PolicyAction.WARN
    cfg_warn.policy.missing_image_policy = PolicyAction.WARN
    findings = validator.validate(manifest, cfg_warn)
    severities = {f.rule_id: f.severity for f in findings}
    assert severities.get("CORRUPTED_IMAGE") == Severity.WARNING
    assert severities.get("MISSING_IMAGE_FILE") == Severity.WARNING

    # Test fail
    cfg_fail = DatasetGateConfig()
    cfg_fail.policy.corrupted_image_policy = PolicyAction.FAIL
    cfg_fail.policy.missing_image_policy = PolicyAction.FAIL
    findings = validator.validate(manifest, cfg_fail)
    severities = {f.rule_id: f.severity for f in findings}
    assert severities.get("CORRUPTED_IMAGE") == Severity.ERROR
    assert severities.get("MISSING_IMAGE_FILE") == Severity.ERROR


def test_duplicate_validator_intra_split(tmp_path: Path):
    png_bytes = create_sample_png_bytes(50, 50, "green")
    img1 = tmp_path / "train_1.png"
    img2 = tmp_path / "train_2.png"
    img1.write_bytes(png_bytes)
    img2.write_bytes(png_bytes)

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train"],
        classes={0: "item"},
        images=[
            ImageMetadata(relative_path="train_1.png", split="train", is_valid=True),
            ImageMetadata(relative_path="train_2.png", split="train", is_valid=True),
        ],
        annotations=[],
    )

    validator = DuplicateValidator()
    config = DatasetGateConfig()
    findings = validator.validate(manifest, config)

    rule_ids = {f.rule_id for f in findings}
    assert "EXACT_DUPLICATE_IMAGE" in rule_ids
    assert "SPLIT_LEAKAGE" not in rule_ids


def test_duplicate_validator_cross_split_leakage(tmp_path: Path):
    png_bytes = create_sample_png_bytes(50, 50, "yellow")
    img_train = tmp_path / "train.png"
    img_val = tmp_path / "val.png"
    img_train.write_bytes(png_bytes)
    img_val.write_bytes(png_bytes)

    manifest = DatasetManifest(
        format="yolo",
        dataset_root=tmp_path,
        splits=["train", "val"],
        classes={0: "item"},
        images=[
            ImageMetadata(relative_path="train.png", split="train", is_valid=True),
            ImageMetadata(relative_path="val.png", split="val", is_valid=True),
        ],
        annotations=[],
    )

    validator = DuplicateValidator()
    config = DatasetGateConfig()
    config.policy.split_leakage_policy = PolicyAction.FAIL
    findings = validator.validate(manifest, config)

    rule_ids = {f.rule_id for f in findings}
    assert "SPLIT_LEAKAGE" in rule_ids
    leakage_findings = [f for f in findings if f.rule_id == "SPLIT_LEAKAGE"]
    assert len(leakage_findings) == 2
    assert leakage_findings[0].severity == Severity.ERROR


def test_annotation_validator_unlabeled_policy():
    manifest = DatasetManifest(
        format="yolo",
        dataset_root=Path("/fake"),
        splits=["train"],
        classes={0: "item"},
        images=[
            ImageMetadata(relative_path="img1.jpg", split="train", is_valid=True),
            ImageMetadata(relative_path="img2.jpg", split="train", is_valid=True),
        ],
        annotations=[
            ImageAnnotation(
                image_relative_path="img1.jpg",
                split="train",
                boxes=[],
                has_label_file=False,
                is_empty_label=True,
            ),
            ImageAnnotation(
                image_relative_path="img2.jpg",
                split="train",
                boxes=[],
                has_label_file=True,
                is_empty_label=True,
            ),
        ],
    )

    validator = AnnotationValidator()

    # Policy allows unlabeled images (default)
    config = DatasetGateConfig()
    assert config.policy.allow_unlabeled_images is True
    findings = validator.validate(manifest, config)
    assert not any(f.rule_id.startswith("UNLABELED_IMAGE") for f in findings)

    # Disallow unlabeled images
    config.policy.allow_unlabeled_images = False
    findings_strict = validator.validate(manifest, config)
    rule_ids = {f.rule_id for f in findings_strict}
    assert "UNLABELED_IMAGE_MISSING" in rule_ids
    assert "UNLABELED_IMAGE_EMPTY" in rule_ids
