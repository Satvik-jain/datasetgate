"""Validator for annotation integrity and labeling policy adherence."""

from __future__ import annotations

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.models import DatasetManifest, Finding, FindingCategory, Severity
from datasetgate.validators.base import BaseValidator


class AnnotationValidator(BaseValidator):
    """Validates annotation integrity and label requirements."""

    def validate(self, manifest: DatasetManifest, config: DatasetGateConfig) -> list[Finding]:
        findings: list[Finding] = list(manifest.discovery_warnings)

        # Image lookup for dimension checking
        img_by_path = {img.relative_path: img for img in manifest.images}

        # Check unlabeled images policy
        if not config.policy.allow_unlabeled_images:
            for ann in manifest.annotations:
                if ann.is_empty_label or len(ann.boxes) == 0:
                    if not ann.has_label_file:
                        findings.append(
                            Finding(
                                rule_id="UNLABELED_IMAGE_MISSING",
                                severity=Severity.ERROR,
                                category=FindingCategory.ANNOTATION_INTEGRITY,
                                message=f"Image '{ann.image_relative_path}' has no annotation file, violating policy (allow_unlabeled_images=false).",
                                file_path=ann.image_relative_path,
                                split=ann.split,
                            )
                        )
                    else:
                        findings.append(
                            Finding(
                                rule_id="UNLABELED_IMAGE_EMPTY",
                                severity=Severity.ERROR,
                                category=FindingCategory.ANNOTATION_INTEGRITY,
                                message=f"Image '{ann.image_relative_path}' has an empty annotation file, violating policy (allow_unlabeled_images=false).",
                                file_path=ann.image_relative_path,
                                split=ann.split,
                            )
                        )

        # Additional cross checks between boxes and physical image dimensions
        for ann in manifest.annotations:
            img = img_by_path.get(ann.image_relative_path)
            if not img or not img.is_valid or not img.width or not img.height:
                continue

            for box in ann.boxes:
                # If absolute COCO box, re-verify against actual decoded image dimensions
                if not box.is_normalized:
                    if box.x_max > img.width or box.y_max > img.height:
                        # Avoid duplicating if parser already reported
                        already_reported = any(
                            f.rule_id == "BBOX_OUT_OF_BOUNDS"
                            and f.metadata.get("annotation_id") == box.metadata.get("annotation_id")
                            for f in findings
                        )
                        if not already_reported:
                            findings.append(
                                Finding(
                                    rule_id="BBOX_OUT_OF_BOUNDS",
                                    severity=Severity.ERROR,
                                    category=FindingCategory.ANNOTATION_INTEGRITY,
                                    message=(
                                        f"Bounding box [{box.x_min}, {box.y_min}, {box.width}, {box.height}] "
                                        f"exceeds actual image dimensions ({img.width}x{img.height}) for '{ann.image_relative_path}'."
                                    ),
                                    file_path=ann.image_relative_path,
                                    split=ann.split,
                                    metadata={
                                        "bbox": [box.x_min, box.y_min, box.width, box.height],
                                        "actual_size": [img.width, img.height],
                                    },
                                )
                            )

        return findings
