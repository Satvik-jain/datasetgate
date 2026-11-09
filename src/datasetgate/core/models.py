"""Core domain models for DatasetGate."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Severity levels for findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingCategory(StrEnum):
    """Categories of dataset defects."""

    IMAGE_INTEGRITY = "image_integrity"
    ANNOTATION_INTEGRITY = "annotation_integrity"
    DUPLICATES_AND_LEAKAGE = "duplicates_and_leakage"
    DISTRIBUTION = "distribution"
    STRUCTURE = "structure"


class Finding(BaseModel):
    """Structured defect finding."""

    rule_id: str = Field(
        description="Unique rule identifier, e.g. IMAGE_CORRUPTED, BBOX_OUT_OF_BOUNDS"
    )
    severity: Severity = Field(description="Severity of this finding")
    category: FindingCategory = Field(description="High-level defect category")
    message: str = Field(description="Actionable human-readable explanation of defect")
    file_path: str | None = Field(default=None, description="Path relative to dataset root")
    related_paths: list[str] = Field(
        default_factory=list, description="Associated paths, e.g. duplicate files"
    )
    split: str | None = Field(default=None, description="Dataset split, e.g. train, val, test")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured defect metadata")

    def fingerprint(self) -> str:
        """Deterministic fingerprint for matching across audits."""
        import hashlib
        import json

        raw = f"{self.rule_id}:{self.file_path or ''}:{self.split or ''}:{self.message}:{json.dumps(self.metadata, sort_keys=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class ImageMetadata(BaseModel):
    """Inspected image file metadata."""

    relative_path: str
    split: str
    width: int | None = None
    height: int | None = None
    format: str | None = None
    sha256: str | None = None
    file_size_bytes: int = 0
    is_valid: bool = True
    error_message: str | None = None


class BoundingBox(BaseModel):
    """Normalized or absolute bounding box."""

    class_id: int
    class_name: str | None = None
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    width: float
    height: float
    is_normalized: bool = True
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageAnnotation(BaseModel):
    """Annotations associated with an image."""

    image_relative_path: str
    split: str
    boxes: list[BoundingBox] = Field(default_factory=list)
    has_label_file: bool = True
    is_empty_label: bool = False
    label_relative_path: str | None = None


class DatasetManifest(BaseModel):
    """Parsed dataset representation independent of raw format."""

    format: str
    dataset_root: Path
    splits: list[str] = Field(default_factory=list)
    classes: dict[int, str] = Field(default_factory=dict)
    images: list[ImageMetadata] = Field(default_factory=list)
    annotations: list[ImageAnnotation] = Field(default_factory=list)
    unpaired_labels: list[str] = Field(default_factory=list)
    discovery_warnings: list[Finding] = Field(default_factory=list)


class DatasetStatistics(BaseModel):
    """Statistical summary of the dataset."""

    total_images: int = 0
    total_annotations: int = 0
    images_per_split: dict[str, int] = Field(default_factory=dict)
    annotations_per_split: dict[str, int] = Field(default_factory=dict)
    instances_per_class: dict[str, int] = Field(default_factory=dict)
    instances_per_class_by_split: dict[str, dict[str, int]] = Field(default_factory=dict)
    missing_classes_per_split: dict[str, list[str]] = Field(default_factory=dict)
    empty_label_counts: dict[str, int] = Field(default_factory=dict)
    empty_label_rate: float = 0.0
    class_imbalance_ratio: float = 0.0
    duplicate_groups_count: int = 0
    leakage_groups_count: int = 0


class PolicyCheckResult(BaseModel):
    """Result of a single policy rule check."""

    name: str
    passed: bool
    status: str  # PASSED, WARNING, ERROR, SKIPPED
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class PolicyResult(BaseModel):
    """Evaluation result from the policy engine."""

    passed: bool
    status: str  # PASSED or FAILED
    passed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    skipped_checks: list[str] = Field(default_factory=list)
    check_results: list[PolicyCheckResult] = Field(default_factory=list)


class AuditSnapshot(BaseModel):
    """Versioned serializable audit report and snapshot."""

    schema_version: str = "1.0.0"
    dataset_fingerprint: str
    format: str
    dataset_name: str
    statistics: DatasetStatistics
    findings: list[Finding] = Field(default_factory=list)
    policy_result: PolicyResult
    metadata: dict[str, Any] = Field(default_factory=dict)


class FindingDiff(BaseModel):
    """Diff of findings between baseline and current audit."""

    new_findings: list[Finding] = Field(default_factory=list)
    resolved_findings: list[Finding] = Field(default_factory=list)
    persisting_findings_count: int = 0


class ComparisonResult(BaseModel):
    """Deterministic comparison between a baseline and a current audit."""

    baseline_fingerprint: str
    current_fingerprint: str
    is_identical: bool
    image_count_diff: int
    annotation_count_diff: int
    class_distribution_diff: dict[str, int] = Field(default_factory=dict)
    findings_diff: FindingDiff
    regressions: list[str] = Field(default_factory=list)
    has_regressions: bool = False
    policy_status_changed: bool = False
    summary: str = ""
