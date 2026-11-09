"""COCO object-detection dataset parser."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from datasetgate.core.config import DatasetGateConfig, PolicyAction
from datasetgate.core.models import (
    BoundingBox,
    DatasetManifest,
    Finding,
    FindingCategory,
    ImageAnnotation,
    ImageMetadata,
    Severity,
)
from datasetgate.parsers.base import BaseParser


class CocoParser(BaseParser):
    """Parser for COCO object detection format datasets."""

    def can_parse(self, dataset_path: Path) -> bool:
        """Heuristically determine if path is a COCO dataset or annotation file."""
        if dataset_path.is_file() and dataset_path.suffix.lower() == ".json":
            return self._is_coco_json(dataset_path)

        if dataset_path.is_dir():
            # Check for annotations/*.json or *.json in root
            candidates = list(dataset_path.glob("annotations/*.json")) + list(
                dataset_path.glob("*.json")
            )
            for cand in candidates:
                if self._is_coco_json(cand):
                    return True

        return False

    def _is_coco_json(self, json_path: Path) -> bool:
        """Check if json file contains standard COCO top-level keys."""
        try:
            with open(json_path, encoding="utf-8") as f:
                # Read a small chunk or parse structure safely
                data = json.load(f)
                if isinstance(data, dict):
                    return "images" in data and "annotations" in data and "categories" in data
        except Exception:
            return False
        return False

    def parse(self, dataset_path: Path, config: DatasetGateConfig) -> DatasetManifest:
        """Parse COCO dataset into a unified DatasetManifest."""
        dataset_root = dataset_path.resolve()
        if dataset_root.is_file():
            dataset_dir = dataset_root.parent
            split_files = {"default": dataset_root}
        else:
            dataset_dir = dataset_root
            split_files = self._discover_coco_splits(dataset_dir, config)

        all_findings: list[Finding] = []
        all_classes: dict[int, str] = {}
        all_images: list[ImageMetadata] = []
        all_annotations: list[ImageAnnotation] = []
        splits: list[str] = list(split_files.keys())

        for split_name, json_file in split_files.items():
            split_manifest = self._parse_single_coco_file(
                json_file=json_file,
                split_name=split_name,
                dataset_root=dataset_dir,
                config=config,
            )
            all_findings.extend(split_manifest.discovery_warnings)
            all_classes.update(split_manifest.classes)
            all_images.extend(split_manifest.images)
            all_annotations.extend(split_manifest.annotations)

        return DatasetManifest(
            format="coco",
            dataset_root=dataset_dir,
            splits=splits,
            classes=all_classes,
            images=all_images,
            annotations=all_annotations,
            unpaired_labels=[],
            discovery_warnings=all_findings,
        )

    def _discover_coco_splits(
        self,
        dataset_dir: Path,
        config: DatasetGateConfig,
    ) -> dict[str, Path]:
        """Discover COCO annotation files for each split."""
        split_files: dict[str, Path] = {}

        # 1. Config override
        if config.dataset.coco_annotation_files:
            for split, rel_path in config.dataset.coco_annotation_files.items():
                target = (dataset_dir / rel_path).resolve()
                if target.is_file():
                    split_files[split] = target

        if split_files:
            return split_files

        # 2. Search annotations/ folder or root
        candidates = list(dataset_dir.glob("annotations/*.json")) + list(dataset_dir.glob("*.json"))
        for cand in candidates:
            if not self._is_coco_json(cand):
                continue

            name_lower = cand.stem.lower()
            if "train" in name_lower:
                split_name = "train"
            elif "val" in name_lower or "valid" in name_lower:
                split_name = "val"
            elif "test" in name_lower:
                split_name = "test"
            else:
                split_name = cand.stem

            # Avoid collisions by prefixing if already taken
            if split_name in split_files:
                split_name = f"{split_name}_{cand.stem}"
            split_files[split_name] = cand

        if not split_files:
            # Fallback
            for cand in candidates:
                split_files[cand.stem] = cand
                break

        return split_files

    def _resolve_image_path(
        self,
        file_name: str,
        split_name: str,
        dataset_root: Path,
        json_file: Path,
    ) -> Path | None:
        """Find the image on disk across conventional COCO layout directories."""
        # Candidates to check
        search_dirs = [
            dataset_root / "images" / split_name,
            dataset_root / split_name,
            dataset_root / "images",
            dataset_root,
            json_file.parent.parent / "images" / split_name,
            json_file.parent.parent / split_name,
            json_file.parent.parent / "images",
            json_file.parent / split_name,
        ]

        # Also strip split from json name (e.g. instances_train2017.json -> train2017)
        json_stem = json_file.stem
        if "_" in json_stem:
            split_suffix = json_stem.split("_")[-1]
            search_dirs.insert(0, dataset_root / split_suffix)
            search_dirs.insert(1, dataset_root / "images" / split_suffix)

        for d in search_dirs:
            candidate = d / file_name
            if candidate.is_file():
                return candidate

        return None

    def _parse_single_coco_file(
        self,
        json_file: Path,
        split_name: str,
        dataset_root: Path,
        config: DatasetGateConfig,
    ) -> DatasetManifest:
        """Parse one COCO JSON annotation file."""
        findings: list[Finding] = []
        rel_json_path = (
            str(json_file.relative_to(dataset_root)).replace("\\", "/")
            if dataset_root in json_file.parents
            else json_file.name
        )

        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            findings.append(
                Finding(
                    rule_id="CORRUPTED_COCO_JSON",
                    severity=Severity.ERROR,
                    category=FindingCategory.STRUCTURE,
                    message=f"Failed to parse COCO JSON '{rel_json_path}': {e}",
                    file_path=rel_json_path,
                    split=split_name,
                )
            )
            return DatasetManifest(
                format="coco",
                dataset_root=dataset_root,
                splits=[split_name],
                classes={},
                images=[],
                annotations=[],
                unpaired_labels=[],
                discovery_warnings=findings,
            )

        if not isinstance(data, dict):
            findings.append(
                Finding(
                    rule_id="INVALID_COCO_STRUCTURE",
                    severity=Severity.ERROR,
                    category=FindingCategory.STRUCTURE,
                    message=f"COCO JSON root must be an object/dict in '{rel_json_path}'.",
                    file_path=rel_json_path,
                    split=split_name,
                )
            )
            return DatasetManifest(
                format="coco",
                dataset_root=dataset_root,
                splits=[split_name],
                classes={},
                images=[],
                annotations=[],
                unpaired_labels=[],
                discovery_warnings=findings,
            )

        raw_images = data.get("images", [])
        raw_annotations = data.get("annotations", [])
        raw_categories = data.get("categories", [])

        # Validate categories
        classes: dict[int, str] = {}
        seen_category_ids: set[int] = set()
        for cat in raw_categories:
            if not isinstance(cat, dict) or "id" not in cat:
                continue
            cat_id = cat["id"]
            if cat_id in seen_category_ids:
                findings.append(
                    Finding(
                        rule_id="DUPLICATE_CATEGORY_ID",
                        severity=Severity.ERROR,
                        category=FindingCategory.STRUCTURE,
                        message=f"Duplicate category ID {cat_id} in '{rel_json_path}'.",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"category_id": cat_id},
                    )
                )
            seen_category_ids.add(cat_id)
            classes[cat_id] = str(cat.get("name", f"category_{cat_id}"))

        # Validate images
        images_by_id: dict[int, dict[str, Any]] = {}
        image_metadata_list: list[ImageMetadata] = []
        seen_image_ids: set[int] = set()

        for img in raw_images:
            if not isinstance(img, dict) or "id" not in img:
                findings.append(
                    Finding(
                        rule_id="MALFORMED_IMAGE_ENTRY",
                        severity=Severity.ERROR,
                        category=FindingCategory.STRUCTURE,
                        message=f"Image item missing required 'id' in '{rel_json_path}'.",
                        file_path=rel_json_path,
                        split=split_name,
                    )
                )
                continue

            img_id = img["id"]
            if img_id in seen_image_ids:
                findings.append(
                    Finding(
                        rule_id="DUPLICATE_IMAGE_ID",
                        severity=Severity.ERROR,
                        category=FindingCategory.STRUCTURE,
                        message=f"Duplicate image ID {img_id} in '{rel_json_path}'.",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"image_id": img_id},
                    )
                )
            seen_image_ids.add(img_id)
            images_by_id[img_id] = img

            file_name = img.get("file_name", "")
            width = img.get("width")
            height = img.get("height")

            # Check image existence
            resolved_file = self._resolve_image_path(file_name, split_name, dataset_root, json_file)
            if resolved_file is None:
                rel_img_path = f"{split_name}/{file_name}" if file_name else f"image_id_{img_id}"
                missing_action = config.policy.missing_image_policy
                if missing_action != PolicyAction.IGNORE:
                    missing_sev = (
                        Severity.ERROR if missing_action == PolicyAction.FAIL else Severity.WARNING
                    )
                    findings.append(
                        Finding(
                            rule_id="MISSING_IMAGE_FILE",
                            severity=missing_sev,
                            category=FindingCategory.IMAGE_INTEGRITY,
                            message=f"Referenced image file '{file_name}' (ID {img_id}) not found on disk in split '{split_name}'.",
                            file_path=rel_img_path,
                            split=split_name,
                            metadata={"image_id": img_id, "file_name": file_name},
                        )
                    )
                image_metadata_list.append(
                    ImageMetadata(
                        relative_path=rel_img_path,
                        split=split_name,
                        width=width if isinstance(width, int) else None,
                        height=height if isinstance(height, int) else None,
                        is_valid=False,
                        error_message="File not found on disk",
                    )
                )
            else:
                rel_img_path = (
                    str(resolved_file.relative_to(dataset_root)).replace("\\", "/")
                    if dataset_root in resolved_file.parents
                    else str(resolved_file)
                )
                file_size = resolved_file.stat().st_size if resolved_file.exists() else 0
                image_metadata_list.append(
                    ImageMetadata(
                        relative_path=rel_img_path,
                        split=split_name,
                        width=width if isinstance(width, int) else None,
                        height=height if isinstance(height, int) else None,
                        file_size_bytes=file_size,
                    )
                )

        # Validate annotations
        seen_ann_ids: set[int] = set()
        annotations_by_img_id: dict[int, list[BoundingBox]] = {
            img_id: [] for img_id in images_by_id
        }

        for ann in raw_annotations:
            if not isinstance(ann, dict) or "id" not in ann:
                findings.append(
                    Finding(
                        rule_id="MALFORMED_ANNOTATION_ENTRY",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation item missing required 'id' in '{rel_json_path}'.",
                        file_path=rel_json_path,
                        split=split_name,
                    )
                )
                continue

            ann_id = ann["id"]
            if ann_id in seen_ann_ids:
                findings.append(
                    Finding(
                        rule_id="DUPLICATE_ANNOTATION_ID",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Duplicate annotation ID {ann_id} in '{rel_json_path}'.",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id},
                    )
                )
            seen_ann_ids.add(ann_id)

            image_id = ann.get("image_id")
            if image_id not in images_by_id:
                findings.append(
                    Finding(
                        rule_id="MISSING_IMAGE_REFERENCE",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation {ann_id} references non-existent image_id {image_id} in '{rel_json_path}'.",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id, "image_id": image_id},
                    )
                )
                continue

            category_id = ann.get("category_id")
            if category_id not in classes:
                findings.append(
                    Finding(
                        rule_id="MISSING_CATEGORY_REFERENCE",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation {ann_id} references non-existent category_id {category_id} in '{rel_json_path}'.",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id, "category_id": category_id},
                    )
                )

            # Check bbox structure
            bbox = ann.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                findings.append(
                    Finding(
                        rule_id="INVALID_COCO_BBOX",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation {ann_id} has invalid bbox array (must be 4 numbers: [x, y, w, h]).",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id, "bbox": bbox},
                    )
                )
                continue

            # Check numeric & finite
            try:
                x, y, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            except (ValueError, TypeError):
                findings.append(
                    Finding(
                        rule_id="NON_NUMERIC_ANNOTATION",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation {ann_id} has non-numeric bbox coordinates: {bbox}.",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id, "bbox": bbox},
                    )
                )
                continue

            if any(math.isnan(v) or math.isinf(v) for v in [x, y, w, h]):
                findings.append(
                    Finding(
                        rule_id="NON_FINITE_ANNOTATION",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation {ann_id} has non-finite (NaN/Inf) bbox values: {bbox}.",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id, "bbox": bbox},
                    )
                )
                continue

            # Check positive dimensions
            if w <= 0.0 or h <= 0.0:
                findings.append(
                    Finding(
                        rule_id="NON_POSITIVE_BBOX_DIMENSION",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation {ann_id} has non-positive width/height ({w}, {h}).",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id, "width": w, "height": h},
                    )
                )

            # Check negative coordinates
            if x < 0.0 or y < 0.0:
                findings.append(
                    Finding(
                        rule_id="NEGATIVE_BBOX_COORDINATE",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Annotation {ann_id} has negative coordinates ({x}, {y}).",
                        file_path=rel_json_path,
                        split=split_name,
                        metadata={"annotation_id": ann_id, "x": x, "y": y},
                    )
                )

            # Check image boundaries if image width/height are available
            img_info = images_by_id[image_id]
            img_w = img_info.get("width")
            img_h = img_info.get("height")
            if isinstance(img_w, (int, float)) and isinstance(img_h, (int, float)):
                if x + w > img_w or y + h > img_h:
                    oob_action = config.policy.out_of_bounds_policy
                    if oob_action != PolicyAction.IGNORE:
                        oob_sev = (
                            Severity.ERROR if oob_action == PolicyAction.FAIL else Severity.WARNING
                        )
                        findings.append(
                            Finding(
                                rule_id="BBOX_OUT_OF_BOUNDS",
                                severity=oob_sev,
                                category=FindingCategory.ANNOTATION_INTEGRITY,
                                message=(
                                    f"Annotation {ann_id} bbox [{x}, {y}, {w}, {h}] extends outside "
                                    f"image dimensions ({img_w}x{img_h})."
                                ),
                                file_path=rel_json_path,
                                split=split_name,
                                metadata={
                                    "annotation_id": ann_id,
                                    "bbox": [x, y, w, h],
                                    "image_id": image_id,
                                    "image_dimensions": [img_w, img_h],
                                },
                            )
                        )

            # Store box (normalize if image dims available, otherwise keep absolute)
            box_obj = BoundingBox(
                class_id=int(category_id) if category_id is not None else 0,
                class_name=classes.get(category_id),
                x_min=x,
                y_min=y,
                x_max=x + w,
                y_max=y + h,
                width=w,
                height=h,
                is_normalized=False,
                metadata={"annotation_id": ann_id},
            )
            annotations_by_img_id[image_id].append(box_obj)

        # Assemble ImageAnnotation list
        final_annotations: list[ImageAnnotation] = []
        for img_id, img_info in images_by_id.items():
            file_name = img_info.get("file_name", "")
            resolved_file = self._resolve_image_path(file_name, split_name, dataset_root, json_file)
            rel_path = (
                str(resolved_file.relative_to(dataset_root)).replace("\\", "/")
                if resolved_file and dataset_root in resolved_file.parents
                else f"{split_name}/{file_name}"
            )
            boxes = annotations_by_img_id.get(img_id, [])

            final_annotations.append(
                ImageAnnotation(
                    image_relative_path=rel_path,
                    split=split_name,
                    boxes=boxes,
                    has_label_file=True,
                    is_empty_label=len(boxes) == 0,
                    label_relative_path=rel_json_path,
                )
            )

        return DatasetManifest(
            format="coco",
            dataset_root=dataset_root,
            splits=[split_name],
            classes=classes,
            images=image_metadata_list,
            annotations=final_annotations,
            unpaired_labels=[],
            discovery_warnings=findings,
        )
