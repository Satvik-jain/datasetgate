"""Validator for image file existence, decodability, formats, and dimensions."""

from __future__ import annotations

from PIL import Image, UnidentifiedImageError

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.models import DatasetManifest, Finding, FindingCategory, Severity
from datasetgate.validators.base import BaseValidator


class ImageIntegrityValidator(BaseValidator):
    """Validates physical image files on disk."""

    def validate(self, manifest: DatasetManifest, config: DatasetGateConfig) -> list[Finding]:
        findings: list[Finding] = []
        dataset_root = manifest.dataset_root
        allowed_extensions = {ext.lower() for ext in config.dataset.image_extensions}

        for img_meta in manifest.images:
            abs_path = (dataset_root / img_meta.relative_path).resolve()

            # 1. Check existence
            if not abs_path.is_file():
                img_meta.is_valid = False
                img_meta.error_message = "File does not exist on disk"
                findings.append(
                    Finding(
                        rule_id="MISSING_IMAGE_FILE",
                        severity=Severity.ERROR,
                        category=FindingCategory.IMAGE_INTEGRITY,
                        message=f"Image file '{img_meta.relative_path}' is missing on disk.",
                        file_path=img_meta.relative_path,
                        split=img_meta.split,
                    )
                )
                continue

            # 2. Check empty file (0 bytes)
            file_size = abs_path.stat().st_size
            img_meta.file_size_bytes = file_size
            if file_size == 0:
                img_meta.is_valid = False
                img_meta.error_message = "File is empty (0 bytes)"
                findings.append(
                    Finding(
                        rule_id="EMPTY_IMAGE_FILE",
                        severity=Severity.ERROR,
                        category=FindingCategory.IMAGE_INTEGRITY,
                        message=f"Image file '{img_meta.relative_path}' is empty (0 bytes).",
                        file_path=img_meta.relative_path,
                        split=img_meta.split,
                    )
                )
                continue

            # 3. Check format extension
            ext = abs_path.suffix.lower()
            if ext not in allowed_extensions:
                findings.append(
                    Finding(
                        rule_id="UNSUPPORTED_IMAGE_FORMAT",
                        severity=Severity.WARNING,
                        category=FindingCategory.IMAGE_INTEGRITY,
                        message=f"Image '{img_meta.relative_path}' extension '{ext}' is not in allowed extensions list.",
                        file_path=img_meta.relative_path,
                        split=img_meta.split,
                        metadata={"extension": ext, "allowed": list(allowed_extensions)},
                    )
                )

            # 4. Check image decoding & dimensions with Pillow
            try:
                # verify() ensures file header / integrity
                with Image.open(abs_path) as img:
                    img.verify()

                # Re-open to read width, height and format
                with Image.open(abs_path) as img:
                    w, h = img.size
                    img_format = img.format

                if w <= 0 or h <= 0:
                    img_meta.is_valid = False
                    img_meta.error_message = f"Invalid dimensions: {w}x{h}"
                    findings.append(
                        Finding(
                            rule_id="INVALID_IMAGE_DIMENSIONS",
                            severity=Severity.ERROR,
                            category=FindingCategory.IMAGE_INTEGRITY,
                            message=f"Image '{img_meta.relative_path}' has non-positive dimensions ({w}x{h}).",
                            file_path=img_meta.relative_path,
                            split=img_meta.split,
                            metadata={"width": w, "height": h},
                        )
                    )
                else:
                    img_meta.width = w
                    img_meta.height = h
                    img_meta.format = img_format
                    img_meta.is_valid = True

            except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as e:
                img_meta.is_valid = False
                img_meta.error_message = str(e)
                findings.append(
                    Finding(
                        rule_id="CORRUPTED_IMAGE",
                        severity=Severity.ERROR,
                        category=FindingCategory.IMAGE_INTEGRITY,
                        message=f"Corrupted or unreadable image file '{img_meta.relative_path}': {e}",
                        file_path=img_meta.relative_path,
                        split=img_meta.split,
                        metadata={"error": str(e)},
                    )
                )

        return findings
