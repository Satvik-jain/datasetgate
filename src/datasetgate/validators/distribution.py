"""Dataset statistics computation and distribution analysis."""

from __future__ import annotations

from collections import defaultdict

from datasetgate.core.models import (
    DatasetManifest,
    DatasetStatistics,
    Finding,
)


def compute_dataset_statistics(
    manifest: DatasetManifest,
    discovery_findings: list[Finding] | None = None,
) -> DatasetStatistics:
    """Compute comprehensive statistics across images, splits, annotations, and classes."""
    images_per_split: dict[str, int] = defaultdict(int)
    annotations_per_split: dict[str, int] = defaultdict(int)
    instances_per_class: dict[str, int] = defaultdict(int)
    instances_per_class_by_split: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    empty_label_counts: dict[str, int] = defaultdict(int)

    total_images = len(manifest.images)
    total_annotations = 0

    # Image counts per split
    for img in manifest.images:
        images_per_split[img.split] += 1

    # Annotation counts, class instances, empty labels
    for ann in manifest.annotations:
        split = ann.split
        num_boxes = len(ann.boxes)
        total_annotations += num_boxes
        annotations_per_split[split] += num_boxes

        if ann.is_empty_label or num_boxes == 0:
            empty_label_counts[split] += 1

        for box in ann.boxes:
            c_name = box.class_name or manifest.classes.get(box.class_id, f"class_{box.class_id}")
            instances_per_class[c_name] += 1
            instances_per_class_by_split[split][c_name] += 1

    # Missing classes per split
    missing_classes_per_split: dict[str, list[str]] = {}
    declared_class_names = [name for _, name in sorted(manifest.classes.items())]
    if not declared_class_names and instances_per_class:
        declared_class_names = list(instances_per_class.keys())

    for split in manifest.splits:
        split_classes = instances_per_class_by_split.get(split, {})
        missing = [c for c in declared_class_names if split_classes.get(c, 0) == 0]
        if missing:
            missing_classes_per_split[split] = missing

    # Empty label rate
    total_empty_labels = sum(empty_label_counts.values())
    empty_label_rate = round(total_empty_labels / total_images, 4) if total_images > 0 else 0.0

    # Imbalance ratio: max count / min count among present classes (>0 instances)
    counts = [c for c in instances_per_class.values() if c > 0]
    if len(counts) > 1:
        imbalance_ratio = round(max(counts) / min(counts), 2)
    else:
        imbalance_ratio = 1.0

    # Count duplicate and leakage groups from findings if provided
    duplicate_groups_count = 0
    leakage_groups_count = 0
    if discovery_findings:
        seen_dup_hashes: set[str] = set()
        seen_leak_hashes: set[str] = set()
        for f in discovery_findings:
            h = f.metadata.get("sha256")
            if f.rule_id == "EXACT_DUPLICATE_IMAGE" and h:
                if h not in seen_dup_hashes:
                    seen_dup_hashes.add(h)
                    duplicate_groups_count += 1
            elif f.rule_id == "SPLIT_LEAKAGE" and h:
                if h not in seen_leak_hashes:
                    seen_leak_hashes.add(h)
                    leakage_groups_count += 1

    return DatasetStatistics(
        total_images=total_images,
        total_annotations=total_annotations,
        images_per_split=dict(images_per_split),
        annotations_per_split=dict(annotations_per_split),
        instances_per_class=dict(instances_per_class),
        instances_per_class_by_split={s: dict(c) for s, c in instances_per_class_by_split.items()},
        missing_classes_per_split=missing_classes_per_split,
        empty_label_counts=dict(empty_label_counts),
        empty_label_rate=empty_label_rate,
        class_imbalance_ratio=imbalance_ratio,
        duplicate_groups_count=duplicate_groups_count,
        leakage_groups_count=leakage_groups_count,
    )
