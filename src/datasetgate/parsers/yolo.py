"""YOLO object-detection dataset parser."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from datasetgate.core.config import DatasetGateConfig
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


class YoloParser(BaseParser):
    """Parser for YOLO object detection datasets."""

    def can_parse(self, dataset_path: Path) -> bool:
        """Heuristically determine if directory is a YOLO dataset."""
        if not dataset_path.is_dir():
            return False

        # Look for YAML configuration
        for yaml_candidate in ["data.yaml", "dataset.yaml", "data.yml", "dataset.yml"]:
            if (dataset_path / yaml_candidate).is_file():
                return True

        # Look for conventional images/ and labels/ directories
        if (dataset_path / "images").is_dir() and (dataset_path / "labels").is_dir():
            return True

        # Look for nested split layout (e.g. train/images and train/labels)
        for split in ["train", "val", "test", "valid"]:
            if (dataset_path / split / "images").is_dir() or (
                dataset_path / split / "labels"
            ).is_dir():
                return True

        return False

    def parse(self, dataset_path: Path, config: DatasetGateConfig) -> DatasetManifest:
        """Parse YOLO dataset into a unified DatasetManifest."""
        dataset_root = dataset_path.resolve()
        findings: list[Finding] = []
        classes: dict[int, str] = {}
        splits: list[str] = []

        # 1. Discover or load YOLO YAML file
        yaml_info = self._load_yolo_yaml(dataset_root, config)
        if yaml_info:
            classes = yaml_info.get("classes", {})
            declared_splits = yaml_info.get("splits", {})
        else:
            declared_splits = {}

        # 2. Discover image and label pairings per split
        split_mappings = self._discover_splits(dataset_root, declared_splits)
        splits = list(split_mappings.keys())

        images: list[ImageMetadata] = []
        annotations: list[ImageAnnotation] = []
        unpaired_labels: list[str] = []

        valid_extensions = {ext.lower() for ext in config.dataset.image_extensions}

        for split_name, paths in split_mappings.items():
            image_dir = paths["images"]
            label_dir = paths["labels"]

            discovered_images: dict[str, Path] = {}
            if image_dir.exists():
                for file_path in image_dir.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                        rel_to_img_dir = file_path.relative_to(image_dir)
                        stem_key = str(rel_to_img_dir.with_suffix("")).replace("\\", "/")
                        discovered_images[stem_key] = file_path

            discovered_labels: dict[str, Path] = {}
            if label_dir.exists():
                for file_path in label_dir.rglob("*.txt"):
                    if file_path.is_file():
                        rel_to_lbl_dir = file_path.relative_to(label_dir)
                        stem_key = str(rel_to_lbl_dir.with_suffix("")).replace("\\", "/")
                        discovered_labels[stem_key] = file_path

            # Match images to labels
            for stem_key, img_path in discovered_images.items():
                rel_img_path = str(img_path.relative_to(dataset_root)).replace("\\", "/")
                file_size = img_path.stat().st_size if img_path.exists() else 0

                img_meta = ImageMetadata(
                    relative_path=rel_img_path,
                    split=split_name,
                    file_size_bytes=file_size,
                )
                images.append(img_meta)

                lbl_path = discovered_labels.get(stem_key)
                if lbl_path is None:
                    # Missing label file (distinct from empty label file)
                    annotations.append(
                        ImageAnnotation(
                            image_relative_path=rel_img_path,
                            split=split_name,
                            boxes=[],
                            has_label_file=False,
                            is_empty_label=True,
                            label_relative_path=None,
                        )
                    )
                else:
                    rel_lbl_path = str(lbl_path.relative_to(dataset_root)).replace("\\", "/")
                    boxes, is_empty, parse_findings = self._parse_label_file(
                        lbl_path=lbl_path,
                        rel_lbl_path=rel_lbl_path,
                        rel_img_path=rel_img_path,
                        split=split_name,
                        known_classes_count=len(classes) if classes else None,
                    )
                    findings.extend(parse_findings)
                    annotations.append(
                        ImageAnnotation(
                            image_relative_path=rel_img_path,
                            split=split_name,
                            boxes=boxes,
                            has_label_file=True,
                            is_empty_label=is_empty,
                            label_relative_path=rel_lbl_path,
                        )
                    )

            # Discover orphan labels (labels without matching images)
            for stem_key, lbl_path in discovered_labels.items():
                if stem_key not in discovered_images:
                    rel_lbl_path = str(lbl_path.relative_to(dataset_root)).replace("\\", "/")
                    unpaired_labels.append(rel_lbl_path)
                    findings.append(
                        Finding(
                            rule_id="ORPHAN_LABEL_FILE",
                            severity=Severity.WARNING,
                            category=FindingCategory.ANNOTATION_INTEGRITY,
                            message=f"Annotation label file '{rel_lbl_path}' has no matching image file in split '{split_name}'.",
                            file_path=rel_lbl_path,
                            split=split_name,
                            metadata={"stem": stem_key},
                        )
                    )

        return DatasetManifest(
            format="yolo",
            dataset_root=dataset_root,
            splits=splits,
            classes=classes,
            images=images,
            annotations=annotations,
            unpaired_labels=unpaired_labels,
            discovery_warnings=findings,
        )

    def _load_yolo_yaml(
        self, dataset_root: Path, config: DatasetGateConfig
    ) -> dict[str, Any] | None:
        """Find and parse data.yaml / dataset.yaml if present."""
        yaml_path: Path | None = None
        if config.dataset.yolo_data_yaml:
            custom_path = dataset_root / config.dataset.yolo_data_yaml
            if custom_path.is_file():
                yaml_path = custom_path

        if not yaml_path:
            for candidate in ["data.yaml", "dataset.yaml", "data.yml", "dataset.yml"]:
                cand_path = dataset_root / candidate
                if cand_path.is_file():
                    yaml_path = cand_path
                    break

        if not yaml_path:
            return None

        try:
            with open(yaml_path, encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except Exception:
            return None

        if not isinstance(content, dict):
            return None

        # Extract classes
        classes: dict[int, str] = {}
        raw_names = content.get("names")
        if isinstance(raw_names, list):
            classes = {idx: str(name) for idx, name in enumerate(raw_names)}
        elif isinstance(raw_names, dict):
            for k, v in raw_names.items():
                try:
                    classes[int(k)] = str(v)
                except ValueError:
                    pass

        # Extract split paths
        splits: dict[str, str] = {}
        for split_key in ["train", "val", "test", "valid"]:
            if split_key in content:
                val = content[split_key]
                if isinstance(val, str):
                    canonical_key = "val" if split_key == "valid" else split_key
                    splits[canonical_key] = val

        return {
            "classes": classes,
            "splits": splits,
            "raw": content,
        }

    def _discover_splits(
        self,
        dataset_root: Path,
        declared_splits: dict[str, str],
    ) -> dict[str, dict[str, Path]]:
        """Resolve images and labels directories for each dataset split."""
        split_mappings: dict[str, dict[str, Path]] = {}

        # If declared in YAML, attempt to resolve them
        if declared_splits:
            for split_name, path_str in declared_splits.items():
                target_path = Path(path_str)
                if not target_path.is_absolute():
                    resolved_path = (dataset_root / target_path).resolve()
                else:
                    resolved_path = target_path

                # Check if path points directly to image folder
                if resolved_path.exists():
                    # If resolved path is an 'images/train' folder
                    if "images" in resolved_path.parts:
                        label_path = Path(str(resolved_path).replace("images", "labels"))
                        split_mappings[split_name] = {
                            "images": resolved_path,
                            "labels": label_path,
                        }
                    else:
                        # Maybe resolved_path has images/ and labels/ subdirectories
                        img_sub = resolved_path / "images"
                        lbl_sub = resolved_path / "labels"
                        if img_sub.is_dir():
                            split_mappings[split_name] = {"images": img_sub, "labels": lbl_sub}
                        else:
                            split_mappings[split_name] = {
                                "images": resolved_path,
                                "labels": (dataset_root / "labels" / split_name),
                            }

        if split_mappings:
            return split_mappings

        # Standard Ultralytics layout: images/{train,val,test} and labels/{train,val,test}
        images_dir = dataset_root / "images"
        labels_dir = dataset_root / "labels"
        if images_dir.is_dir():
            found_sub = False
            for split_name in ["train", "val", "test", "valid"]:
                sub_img = images_dir / split_name
                if sub_img.is_dir():
                    found_sub = True
                    canonical = "val" if split_name == "valid" else split_name
                    split_mappings[canonical] = {
                        "images": sub_img,
                        "labels": labels_dir / split_name,
                    }
            if not found_sub:
                # Flat images directory
                split_mappings["train"] = {
                    "images": images_dir,
                    "labels": labels_dir,
                }
            return split_mappings

        # Nested split layout: train/{images,labels}, val/{images,labels}
        for split_name in ["train", "val", "test", "valid"]:
            split_dir = dataset_root / split_name
            if split_dir.is_dir():
                sub_img = split_dir / "images"
                sub_lbl = split_dir / "labels"
                if sub_img.is_dir():
                    canonical = "val" if split_name == "valid" else split_name
                    split_mappings[canonical] = {
                        "images": sub_img,
                        "labels": sub_lbl,
                    }

        if split_mappings:
            return split_mappings

        # Fallback: treat dataset_root as a single split
        split_mappings["train"] = {
            "images": dataset_root,
            "labels": dataset_root,
        }
        return split_mappings

    def _parse_label_file(
        self,
        lbl_path: Path,
        rel_lbl_path: str,
        rel_img_path: str,
        split: str,
        known_classes_count: int | None,
    ) -> tuple[list[BoundingBox], bool, list[Finding]]:
        """Parse YOLO annotation text file into BoundingBox list and detect format defects."""
        findings: list[Finding] = []
        boxes: list[BoundingBox] = []

        try:
            content = lbl_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = lbl_path.read_text(encoding="latin-1")
            except Exception as e:
                findings.append(
                    Finding(
                        rule_id="LABEL_FILE_UNREADABLE",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Cannot read label file '{rel_lbl_path}': {e}",
                        file_path=rel_lbl_path,
                        split=split,
                    )
                )
                return boxes, True, findings
        except Exception as e:
            findings.append(
                Finding(
                    rule_id="LABEL_FILE_UNREADABLE",
                    severity=Severity.ERROR,
                    category=FindingCategory.ANNOTATION_INTEGRITY,
                    message=f"Cannot read label file '{rel_lbl_path}': {e}",
                    file_path=rel_lbl_path,
                    split=split,
                )
            )
            return boxes, True, findings

        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        if not lines:
            # File exists but is empty -> legitimate negative sample
            return boxes, True, findings

        for line_num, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) != 5:
                findings.append(
                    Finding(
                        rule_id="MALFORMED_YOLO_ROW",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=(
                            f"Malformed YOLO row at {rel_lbl_path}:{line_num}. "
                            f"Expected 5 fields (<class_id> <x_center> <y_center> <width> <height>), found {len(parts)}."
                        ),
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={
                            "line_number": line_num,
                            "line_content": line,
                            "tokens_count": len(parts),
                        },
                    )
                )
                continue

            # Check numeric parsing
            try:
                class_id_float = float(parts[0])
                xc = float(parts[1])
                yc = float(parts[2])
                w = float(parts[3])
                h = float(parts[4])
            except ValueError:
                findings.append(
                    Finding(
                        rule_id="NON_NUMERIC_ANNOTATION",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Non-numeric values in {rel_lbl_path}:{line_num}: '{line}'.",
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={"line_number": line_num, "line_content": line},
                    )
                )
                continue

            # Check finite numbers
            if any(math.isnan(v) or math.isinf(v) for v in [class_id_float, xc, yc, w, h]):
                findings.append(
                    Finding(
                        rule_id="NON_FINITE_ANNOTATION",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Non-finite (NaN or Inf) coordinate values in {rel_lbl_path}:{line_num}.",
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={
                            "line_number": line_num,
                            "values": [class_id_float, xc, yc, w, h],
                        },
                    )
                )
                continue

            # Class ID must be integer >= 0
            if not class_id_float.is_integer() or class_id_float < 0:
                findings.append(
                    Finding(
                        rule_id="INVALID_CLASS_ID",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Invalid class ID '{parts[0]}' in {rel_lbl_path}:{line_num} (must be non-negative integer).",
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={"line_number": line_num, "class_id": parts[0]},
                    )
                )
                continue

            class_id = int(class_id_float)
            if known_classes_count is not None and class_id >= known_classes_count:
                findings.append(
                    Finding(
                        rule_id="INVALID_CLASS_ID",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=(
                            f"Class ID {class_id} in {rel_lbl_path}:{line_num} exceeds defined "
                            f"class count ({known_classes_count})."
                        ),
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={
                            "line_number": line_num,
                            "class_id": class_id,
                            "known_classes": known_classes_count,
                        },
                    )
                )

            # Dimensions positive check
            if w <= 0.0 or h <= 0.0:
                findings.append(
                    Finding(
                        rule_id="NON_POSITIVE_BBOX_DIMENSION",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Bounding box dimensions width={w}, height={h} must be > 0 at {rel_lbl_path}:{line_num}.",
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={"line_number": line_num, "width": w, "height": h},
                    )
                )

            # Normalized coordinate bounds check: center must be within [0, 1]
            if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0):
                findings.append(
                    Finding(
                        rule_id="INVALID_NORMALIZED_COORDINATES",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=f"Normalized center coordinates ({xc}, {yc}) outside [0, 1] at {rel_lbl_path}:{line_num}.",
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={"line_number": line_num, "x_center": xc, "y_center": yc},
                    )
                )

            # Check if bbox extends beyond normalized boundaries [0, 1]
            x_min = xc - w / 2.0
            y_min = yc - h / 2.0
            x_max = xc + w / 2.0
            y_max = yc + h / 2.0

            # Allow tiny floating point epsilon tolerance (e.g. 1e-4)
            eps = 1e-4
            if x_min < -eps or y_min < -eps or x_max > 1.0 + eps or y_max > 1.0 + eps:
                findings.append(
                    Finding(
                        rule_id="BBOX_OUT_OF_BOUNDS",
                        severity=Severity.ERROR,
                        category=FindingCategory.ANNOTATION_INTEGRITY,
                        message=(
                            f"Bounding box [{x_min:.3f}, {y_min:.3f}, {x_max:.3f}, {y_max:.3f}] "
                            f"extends outside normalized image bounds at {rel_lbl_path}:{line_num}."
                        ),
                        file_path=rel_lbl_path,
                        split=split,
                        metadata={
                            "line_number": line_num,
                            "bbox": [x_min, y_min, x_max, y_max],
                            "image_path": rel_img_path,
                        },
                    )
                )

            boxes.append(
                BoundingBox(
                    class_id=class_id,
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                    width=w,
                    height=h,
                    is_normalized=True,
                    metadata={"line_number": line_num},
                )
            )

        return boxes, False, findings
