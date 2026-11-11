"""Validator for exact image duplicates, cross-split leakage, and perceptual near-duplicates."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from datasetgate.core.config import DatasetGateConfig, PolicyAction
from datasetgate.core.models import (
    DatasetManifest,
    Finding,
    FindingCategory,
    ImageMetadata,
    Severity,
)
from datasetgate.validators.base import BaseValidator
from datasetgate.validators.phash import (
    HASH_BITS,
    PHASH_ALGORITHM_ID,
    PHashDecodeError,
    bit_agreement_pct,
    compute_phash,
    find_candidate_pairs,
    phash_to_hex,
)


def compute_file_sha256(path: Path, chunk_size: int = 65536) -> str:
    """Compute deterministic SHA-256 hash of a file streaming in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def canonical_pair_paths(path_a: str, path_b: str) -> tuple[str, str]:
    """Return deterministically sorted pair of normalized relative paths."""
    norm_a = path_a.replace("\\", "/")
    norm_b = path_b.replace("\\", "/")
    return (norm_a, norm_b) if norm_a < norm_b else (norm_b, norm_a)


class DuplicateValidator(BaseValidator):
    """Detects exact byte duplicates and perceptual near-duplicates within and across splits."""

    def __init__(self) -> None:
        self.perceptual_coverage: dict[str, Any] = {}

    def validate(self, manifest: DatasetManifest, config: DatasetGateConfig) -> list[Finding]:
        findings: list[Finding] = []
        dataset_root = manifest.dataset_root

        # -----------------------------------------------------------------
        # 1. Exact SHA-256 Duplicate & Leakage Detection
        # -----------------------------------------------------------------
        images_by_hash: dict[str, list[ImageMetadata]] = defaultdict(list)
        exact_duplicate_pairs: set[tuple[str, str]] = set()

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

            # Record all exact duplicate pairs in this group for suppression in perceptual pass
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    exact_duplicate_pairs.add(
                        canonical_pair_paths(group[i].relative_path, group[j].relative_path)
                    )

            splits = {img.split for img in group}
            all_paths = [img.relative_path for img in group]

            # Case A: Cross-split exact leakage
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
                # Case B: Intra-split exact duplicates
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

        # -----------------------------------------------------------------
        # 2. Perceptual Duplicate & Leakage Detection (pHash)
        # -----------------------------------------------------------------
        phash_cfg = config.policy.perceptual_hash

        if not phash_cfg.enabled:
            self.perceptual_coverage = {
                "enabled": False,
                "algorithm": PHASH_ALGORITHM_ID,
                "hash_bits": HASH_BITS,
                "max_hamming_distance": phash_cfg.max_hamming_distance,
                "max_candidate_pairs": phash_cfg.max_candidate_pairs,
                "executed": False,
                "complete": True,
            }
            return findings

        # Filter eligible valid images on disk
        eligible_images: list[ImageMetadata] = sorted(
            [
                img
                for img in manifest.images
                if img.is_valid and (dataset_root / img.relative_path).is_file()
            ],
            key=lambda img: img.relative_path.replace("\\", "/"),
        )

        path_to_meta: dict[str, ImageMetadata] = {
            img.relative_path.replace("\\", "/"): img for img in eligible_images
        }
        path_to_phash: dict[str, int] = {}
        items_for_pairing: list[tuple[str, int]] = []
        skipped_images_count = 0

        # Compute pHash once per eligible image (audit-local cache)
        for img_meta in eligible_images:
            norm_rel_path = img_meta.relative_path.replace("\\", "/")
            abs_path = (dataset_root / img_meta.relative_path).resolve()

            try:
                h_val = compute_phash(abs_path)
                path_to_phash[norm_rel_path] = h_val
                items_for_pairing.append((norm_rel_path, h_val))
            except PHashDecodeError as e:
                skipped_images_count += 1
                findings.append(
                    Finding(
                        rule_id="PERCEPTUAL_HASH_UNAVAILABLE",
                        severity=Severity.WARNING,
                        category=FindingCategory.IMAGE_INTEGRITY,
                        message=(
                            f"Perceptual hashing unavailable for image '{img_meta.relative_path}': {e}"
                        ),
                        file_path=img_meta.relative_path,
                        split=img_meta.split,
                        metadata={
                            "error": str(e),
                            "reason": "decode_failure",
                        },
                    )
                )

        # Search candidate near-duplicate pairs
        candidate_pairs, is_truncated = find_candidate_pairs(
            items_for_pairing,
            max_dist=phash_cfg.max_hamming_distance,
            max_candidate_pairs=phash_cfg.max_candidate_pairs,
        )

        p_duplicate_action = phash_cfg.duplicate_policy
        p_leakage_action = phash_cfg.split_leakage_policy

        p_duplicate_severity = (
            Severity.ERROR if p_duplicate_action == PolicyAction.FAIL else Severity.WARNING
        )
        p_leakage_severity = (
            Severity.ERROR if p_leakage_action == PolicyAction.FAIL else Severity.WARNING
        )

        perceptual_duplicate_count = 0
        perceptual_leakage_count = 0
        generated_perceptual_findings = 0

        for path_a_raw, path_b_raw, dist in candidate_pairs:
            p_a, p_b = canonical_pair_paths(path_a_raw, path_b_raw)

            # Suppress candidate pair if it is already an exact SHA-256 duplicate pair
            if (p_a, p_b) in exact_duplicate_pairs:
                continue

            meta_a = path_to_meta[p_a]
            meta_b = path_to_meta[p_b]
            split_a = meta_a.split
            split_b = meta_b.split

            h_a_val = path_to_phash[p_a]
            h_b_val = path_to_phash[p_b]
            agreement = bit_agreement_pct(dist, total_bits=HASH_BITS)

            finding_metadata = {
                "hamming_distance": dist,
                "max_allowed_hamming_distance": phash_cfg.max_hamming_distance,
                "bit_agreement_pct": agreement,
                "algorithm": PHASH_ALGORITHM_ID,
                "hash_bits": HASH_BITS,
                "primary_hash": phash_to_hex(h_a_val),
                "related_hash": phash_to_hex(h_b_val),
                "split": split_a,
                "related_split": split_b,
            }

            if split_a == split_b:
                perceptual_duplicate_count += 1
                if p_duplicate_action != PolicyAction.IGNORE:
                    generated_perceptual_findings += 1
                    findings.append(
                        Finding(
                            rule_id="PERCEPTUAL_DUPLICATE",
                            severity=p_duplicate_severity,
                            category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                            message=(
                                f"Perceptual near-duplicate image detected within split '{split_a}'. "
                                f"Matches '{p_b}' with Hamming distance {dist} ({agreement:.1f}% bit agreement)."
                            ),
                            file_path=p_a,
                            related_paths=[p_b],
                            split=split_a,
                            metadata=finding_metadata,
                        )
                    )
            else:
                perceptual_leakage_count += 1
                if p_leakage_action != PolicyAction.IGNORE:
                    generated_perceptual_findings += 1
                    findings.append(
                        Finding(
                            rule_id="PERCEPTUAL_SPLIT_LEAKAGE",
                            severity=p_leakage_severity,
                            category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                            message=(
                                f"Perceptual duplicate image leaked across splits ('{split_a}' vs '{split_b}'). "
                                f"Matches '{p_b}' with Hamming distance {dist} ({agreement:.1f}% bit agreement)."
                            ),
                            file_path=p_a,
                            related_paths=[p_b],
                            split=split_a,
                            metadata=finding_metadata,
                        )
                    )

        # Handle candidate truncation explicitly
        if is_truncated:
            trunc_sev = (
                Severity.ERROR
                if phash_cfg.truncation_action == PolicyAction.FAIL
                else Severity.WARNING
            )
            findings.append(
                Finding(
                    rule_id="PERCEPTUAL_ANALYSIS_TRUNCATED",
                    severity=trunc_sev,
                    category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                    message=(
                        f"Perceptual duplicate analysis was truncated after reaching the limit of "
                        f"{phash_cfg.max_candidate_pairs} candidate pairs. "
                        f"Generated {generated_perceptual_findings} perceptual candidate finding(s); "
                        "additional near-duplicates may exist."
                    ),
                    metadata={
                        "max_candidate_pairs": phash_cfg.max_candidate_pairs,
                        "candidate_pairs_found": len(candidate_pairs),
                        "findings_generated": generated_perceptual_findings,
                        "is_truncated": True,
                        "additional_candidates_may_exist": True,
                    },
                )
            )

        # Record structured analysis coverage metadata
        self.perceptual_coverage = {
            "enabled": True,
            "algorithm": PHASH_ALGORITHM_ID,
            "hash_bits": HASH_BITS,
            "max_hamming_distance": phash_cfg.max_hamming_distance,
            "max_candidate_pairs": phash_cfg.max_candidate_pairs,
            "executed": True,
            "complete": not is_truncated,
            "eligible_images_count": len(eligible_images),
            "successfully_hashed_count": len(items_for_pairing),
            "skipped_images_count": skipped_images_count,
            "candidate_pairs_generated": len(candidate_pairs),
            "perceptual_duplicate_pairs": perceptual_duplicate_count,
            "perceptual_leakage_pairs": perceptual_leakage_count,
            "is_truncated": is_truncated,
        }

        return findings
