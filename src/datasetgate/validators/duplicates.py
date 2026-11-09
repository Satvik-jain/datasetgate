"""Validator for exact image duplicates and cross-split leakage."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from datasetgate.core.config import DatasetGateConfig, PolicyAction
from datasetgate.core.models import (
    DatasetManifest,
    Finding,
    FindingCategory,
    ImageMetadata,
    Severity,
)
from datasetgate.validators.base import BaseValidator


def compute_file_sha256(path: Path, chunk_size: int = 65536) -> str:
    """Compute deterministic SHA-256 hash of a file streaming in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


class DuplicateValidator(BaseValidator):
    """Detects exact byte-for-byte duplicate images and cross-split data leakage."""

    def validate(self, manifest: DatasetManifest, config: DatasetGateConfig) -> list[Finding]:
        findings: list[Finding] = []
        dataset_root = manifest.dataset_root

        # 1. Compute SHA-256 for all existing valid images
        images_by_hash: dict[str, list[ImageMetadata]] = defaultdict(list)

        for img_meta in manifest.images:
            if not img_meta.is_valid:
                continue

            abs_path = (dataset_root / img_meta.relative_path).resolve()
            if not abs_path.is_file():
                continue

            if not img_meta.sha256:
                try:
                    img_meta.sha256 = compute_file_sha256(abs_path)
                except Exception:
                    continue

            images_by_hash[img_meta.sha256].append(img_meta)

        # 2. Analyze duplicate groups
        leakage_action = config.policy.split_leakage_policy
        duplicate_action = config.policy.duplicate_policy

        leakage_severity = (
            Severity.ERROR if leakage_action == PolicyAction.FAIL else Severity.WARNING
        )
        duplicate_severity = (
            Severity.ERROR if duplicate_action == PolicyAction.FAIL else Severity.WARNING
        )

        for sha256, group in images_by_hash.items():
            if len(group) <= 1:
                continue

            splits = {img.split for img in group}
            all_paths = [img.relative_path for img in group]

            # Case A: Cross-split leakage
            if len(splits) > 1:
                if leakage_action != PolicyAction.IGNORE:
                    splits_str = ", ".join(sorted(splits))
                    for img in group:
                        other_paths = [p for p in all_paths if p != img.relative_path]
                        findings.append(
                            Finding(
                                rule_id="SPLIT_LEAKAGE",
                                severity=leakage_severity,
                                category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                                message=(
                                    f"Exact duplicate image leaked across splits ({splits_str}). "
                                    f"Found in split '{img.split}', duplicates: {', '.join(other_paths)}."
                                ),
                                file_path=img.relative_path,
                                related_paths=other_paths,
                                split=img.split,
                                metadata={
                                    "sha256": sha256,
                                    "splits_involved": sorted(splits),
                                    "duplicate_count": len(group),
                                },
                            )
                        )
            else:
                # Case B: Intra-split duplicates
                if duplicate_action != PolicyAction.IGNORE:
                    split_name = next(iter(splits))
                    for img in group:
                        other_paths = [p for p in all_paths if p != img.relative_path]
                        findings.append(
                            Finding(
                                rule_id="EXACT_DUPLICATE_IMAGE",
                                severity=duplicate_severity,
                                category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                                message=(
                                    f"Exact duplicate image detected within split '{split_name}'. "
                                    f"Identical to: {', '.join(other_paths)}."
                                ),
                                file_path=img.relative_path,
                                related_paths=other_paths,
                                split=split_name,
                                metadata={
                                    "sha256": sha256,
                                    "split": split_name,
                                    "duplicate_count": len(group),
                                },
                            )
                        )

        return findings
