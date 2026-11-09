"""Tests for dataset fingerprint deterministic calculation and sensitivity."""

import random
from pathlib import Path

from datasetgate.core.engine import calculate_dataset_fingerprint
from datasetgate.core.models import (
    BoundingBox,
    DatasetManifest,
    DatasetStatistics,
    ImageAnnotation,
    ImageMetadata,
)


def _build_sample_manifest(
    box_xmin: float = 0.1,
    box_class: int = 0,
    img_hash: str = "abc123sha",
    img_path: str = "images/train/img1.jpg",
    split: str = "train",
    fmt: str = "yolo",
) -> tuple[DatasetManifest, DatasetStatistics]:
    """Helper to construct a deterministic test manifest and statistics."""
    images = [
        ImageMetadata(
            relative_path=img_path,
            split=split,
            sha256=img_hash,
            file_size_bytes=1024,
            width=640,
            height=480,
        ),
        ImageMetadata(
            relative_path="images/train/img2.jpg",
            split=split,
            sha256="def456sha",
            file_size_bytes=2048,
            width=640,
            height=480,
        ),
    ]

    annotations = [
        ImageAnnotation(
            image_relative_path=img_path,
            split=split,
            boxes=[
                BoundingBox(
                    class_id=box_class,
                    x_min=box_xmin,
                    y_min=0.2,
                    x_max=0.5,
                    y_max=0.6,
                    width=0.4,
                    height=0.4,
                ),
                BoundingBox(
                    class_id=1,
                    x_min=0.3,
                    y_min=0.3,
                    x_max=0.8,
                    y_max=0.8,
                    width=0.5,
                    height=0.5,
                ),
            ],
            has_label_file=True,
            is_empty_label=False,
            label_relative_path="labels/train/img1.txt",
        ),
        ImageAnnotation(
            image_relative_path="images/train/img2.jpg",
            split=split,
            boxes=[
                BoundingBox(
                    class_id=0,
                    x_min=0.0,
                    y_min=0.0,
                    x_max=0.5,
                    y_max=0.5,
                    width=0.5,
                    height=0.5,
                )
            ],
            has_label_file=True,
            is_empty_label=False,
            label_relative_path="labels/train/img2.txt",
        ),
    ]

    manifest = DatasetManifest(
        format=fmt,
        dataset_root=Path("/fake/dataset"),
        splits=["train", "val"],
        classes={0: "dog", 1: "cat"},
        images=images,
        annotations=annotations,
        unpaired_labels=[],
    )

    stats = DatasetStatistics(
        total_images=2,
        total_annotations=3,
        images_per_split={"train": 2},
        annotations_per_split={"train": 3},
        instances_per_class={"dog": 2, "cat": 1},
        class_imbalance_ratio=2.0,
    )

    return manifest, stats


def test_fingerprint_deterministic_and_sha256_format():
    manifest, stats = _build_sample_manifest()
    fp1 = calculate_dataset_fingerprint(manifest, stats)
    fp2 = calculate_dataset_fingerprint(manifest, stats)

    assert fp1 == fp2
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)


def test_fingerprint_changes_when_bounding_box_coordinate_changes():
    """Ensure fingerprint changes even if image count, annotation count, and class counts are identical."""
    manifest1, stats1 = _build_sample_manifest(box_xmin=0.10)
    manifest2, stats2 = _build_sample_manifest(box_xmin=0.15)  # slight shift in box coordinate

    # Total counts and class distributions are identical
    assert stats1.total_annotations == stats2.total_annotations
    assert stats1.instances_per_class == stats2.instances_per_class

    fp1 = calculate_dataset_fingerprint(manifest1, stats1)
    fp2 = calculate_dataset_fingerprint(manifest2, stats2)

    assert fp1 != fp2, "Fingerprint must change when a bounding box coordinate changes!"


def test_fingerprint_changes_when_class_assignment_changes():
    manifest1, stats1 = _build_sample_manifest(box_class=0)
    manifest2, stats2 = _build_sample_manifest(box_class=1)

    fp1 = calculate_dataset_fingerprint(manifest1, stats1)
    fp2 = calculate_dataset_fingerprint(manifest2, stats2)

    assert fp1 != fp2


def test_fingerprint_changes_when_image_content_changes():
    manifest1, stats1 = _build_sample_manifest(img_hash="hash_v1")
    manifest2, stats2 = _build_sample_manifest(img_hash="hash_v2")

    fp1 = calculate_dataset_fingerprint(manifest1, stats1)
    fp2 = calculate_dataset_fingerprint(manifest2, stats2)

    assert fp1 != fp2


def test_fingerprint_changes_when_split_membership_changes():
    manifest1, stats1 = _build_sample_manifest(split="train")
    manifest2, stats2 = _build_sample_manifest(split="val")

    fp1 = calculate_dataset_fingerprint(manifest1, stats1)
    fp2 = calculate_dataset_fingerprint(manifest2, stats2)

    assert fp1 != fp2


def test_fingerprint_order_independence():
    """Fingerprint must remain identical regardless of traversal or list order."""
    manifest, stats = _build_sample_manifest()

    # Shuffled images
    shuffled_images = list(manifest.images)
    random.Random(42).shuffle(shuffled_images)

    # Shuffled annotations and boxes within annotations
    shuffled_annotations = []
    for ann in manifest.annotations:
        shuffled_boxes = list(ann.boxes)
        random.Random(42).shuffle(shuffled_boxes)
        shuffled_annotations.append(
            ImageAnnotation(
                image_relative_path=ann.image_relative_path,
                split=ann.split,
                boxes=shuffled_boxes,
                has_label_file=ann.has_label_file,
                is_empty_label=ann.is_empty_label,
                label_relative_path=ann.label_relative_path,
            )
        )
    random.Random(42).shuffle(shuffled_annotations)

    shuffled_manifest = DatasetManifest(
        format=manifest.format,
        dataset_root=manifest.dataset_root,
        splits=["val", "train"],  # out of order
        classes={1: "cat", 0: "dog"},  # out of order
        images=shuffled_images,
        annotations=shuffled_annotations,
        unpaired_labels=["labels/unpaired2.txt", "labels/unpaired1.txt"],
    )
    manifest.unpaired_labels = ["labels/unpaired1.txt", "labels/unpaired2.txt"]
    # Re-calculate base_fp with unpaired labels
    expected_fp = calculate_dataset_fingerprint(manifest, stats)
    shuffled_fp = calculate_dataset_fingerprint(shuffled_manifest, stats)

    assert shuffled_fp == expected_fp


def test_fingerprint_path_separator_cross_platform_normalization():
    """Windows backslash vs Unix forward slash paths must yield the exact same fingerprint."""
    manifest1, stats = _build_sample_manifest(img_path="images/train/img1.jpg")
    manifest2, _ = _build_sample_manifest(img_path="images\\train\\img1.jpg")

    fp1 = calculate_dataset_fingerprint(manifest1, stats)
    fp2 = calculate_dataset_fingerprint(manifest2, stats)

    assert fp1 == fp2
