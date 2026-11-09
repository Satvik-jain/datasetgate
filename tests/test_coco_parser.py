"""Unit tests for COCO dataset parser."""

import json
from pathlib import Path

from datasetgate.core.config import DatasetGateConfig
from datasetgate.parsers.coco import CocoParser


def test_coco_can_parse(tmp_path: Path):
    parser = CocoParser()
    assert parser.can_parse(tmp_path) is False

    coco_file = tmp_path / "annotations.json"
    coco_file.write_text(
        json.dumps({"images": [], "annotations": [], "categories": []}),
        encoding="utf-8",
    )
    assert parser.can_parse(coco_file) is True
    assert parser.can_parse(tmp_path) is True


def test_coco_parse_valid_dataset(tmp_path: Path):
    images_dir = tmp_path / "train"
    images_dir.mkdir(parents=True)
    img_file = images_dir / "0001.jpg"
    img_file.write_bytes(b"fake_image_content")

    data = {
        "images": [
            {"id": 1, "file_name": "0001.jpg", "width": 640, "height": 480},
            {"id": 2, "file_name": "0002.jpg", "width": 640, "height": 480},  # unannotated image
        ],
        "categories": [
            {"id": 10, "name": "pedestrian", "supercategory": "person"},
        ],
        "annotations": [
            {
                "id": 100,
                "image_id": 1,
                "category_id": 10,
                "bbox": [10.0, 20.0, 50.0, 100.0],
                "area": 5000.0,
                "iscrowd": 0,
            }
        ],
    }

    # Also write unannotated image to disk
    (images_dir / "0002.jpg").write_bytes(b"unannotated_image")

    json_file = tmp_path / "instances_train.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    parser = CocoParser()
    config = DatasetGateConfig()
    manifest = parser.parse(tmp_path, config)

    assert manifest.format == "coco"
    assert manifest.classes == {10: "pedestrian"}
    assert len(manifest.images) == 2
    assert len(manifest.annotations) == 2

    # Check annotated image
    ann_1 = next(a for a in manifest.annotations if "0001.jpg" in a.image_relative_path)
    assert len(ann_1.boxes) == 1
    assert ann_1.is_empty_label is False
    assert ann_1.boxes[0].width == 50.0
    assert ann_1.boxes[0].class_name == "pedestrian"

    # Check unannotated image
    ann_2 = next(a for a in manifest.annotations if "0002.jpg" in a.image_relative_path)
    assert len(ann_2.boxes) == 0
    assert ann_2.is_empty_label is True


def test_coco_parse_defects(tmp_path: Path):
    data = {
        "images": [
            {"id": 1, "file_name": "exists.jpg", "width": 100, "height": 100},
            {"id": 1, "file_name": "dup_id.jpg", "width": 100, "height": 100},  # duplicate image id
            {
                "id": 2,
                "file_name": "missing_file.jpg",
                "width": 100,
                "height": 100,
            },  # missing from disk
        ],
        "categories": [
            {"id": 1, "name": "cat"},
            {"id": 1, "name": "cat_duplicate"},  # duplicate category id
        ],
        "annotations": [
            # Duplicate annotation id
            {"id": 10, "image_id": 1, "category_id": 1, "bbox": [5, 5, 20, 20]},
            {"id": 10, "image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20]},
            # Missing image reference
            {"id": 11, "image_id": 999, "category_id": 1, "bbox": [5, 5, 20, 20]},
            # Missing category reference
            {"id": 12, "image_id": 1, "category_id": 888, "bbox": [5, 5, 20, 20]},
            # Invalid bbox structure
            {"id": 13, "image_id": 1, "category_id": 1, "bbox": [5, 5, 20]},
            # Non-numeric coordinate
            {"id": 14, "image_id": 1, "category_id": 1, "bbox": [5, "bad", 20, 20]},
            # Non-finite coordinate
            {"id": 15, "image_id": 1, "category_id": 1, "bbox": [5, float("nan"), 20, 20]},
            # Negative dimension
            {"id": 16, "image_id": 1, "category_id": 1, "bbox": [5, 5, -10, 20]},
            # Negative coordinate
            {"id": 17, "image_id": 1, "category_id": 1, "bbox": [-5, 5, 10, 20]},
            # Out of bounds
            {"id": 18, "image_id": 1, "category_id": 1, "bbox": [80, 80, 50, 50]},
        ],
    }

    # Only create exists.jpg
    (tmp_path / "exists.jpg").write_bytes(b"content")

    json_file = tmp_path / "train.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    parser = CocoParser()
    config = DatasetGateConfig()
    manifest = parser.parse(tmp_path, config)

    rule_ids = {f.rule_id for f in manifest.discovery_warnings}
    assert "DUPLICATE_IMAGE_ID" in rule_ids
    assert "DUPLICATE_CATEGORY_ID" in rule_ids
    assert "DUPLICATE_ANNOTATION_ID" in rule_ids
    assert "MISSING_IMAGE_FILE" in rule_ids
    assert "MISSING_IMAGE_REFERENCE" in rule_ids
    assert "MISSING_CATEGORY_REFERENCE" in rule_ids
    assert "INVALID_COCO_BBOX" in rule_ids
    assert "NON_NUMERIC_ANNOTATION" in rule_ids
    assert "NON_FINITE_ANNOTATION" in rule_ids
    assert "NON_POSITIVE_BBOX_DIMENSION" in rule_ids
    assert "NEGATIVE_BBOX_COORDINATE" in rule_ids
    assert "BBOX_OUT_OF_BOUNDS" in rule_ids
