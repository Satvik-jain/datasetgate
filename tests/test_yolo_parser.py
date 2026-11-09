"""Unit tests for YOLO dataset parser."""

from pathlib import Path

from datasetgate.core.config import DatasetGateConfig
from datasetgate.parsers.yolo import YoloParser


def test_yolo_can_parse_with_yaml(tmp_path: Path):
    parser = YoloParser()
    assert parser.can_parse(tmp_path) is False

    (tmp_path / "data.yaml").write_text("names: ['car', 'person']\n", encoding="utf-8")
    assert parser.can_parse(tmp_path) is True


def test_yolo_can_parse_with_dirs(tmp_path: Path):
    parser = YoloParser()
    (tmp_path / "images").mkdir()
    (tmp_path / "labels").mkdir()
    assert parser.can_parse(tmp_path) is True


def test_yolo_parse_valid_dataset(tmp_path: Path):
    # Setup standard YOLO directory structure
    images_train = tmp_path / "images" / "train"
    labels_train = tmp_path / "labels" / "train"
    images_train.mkdir(parents=True)
    labels_train.mkdir(parents=True)

    yaml_file = tmp_path / "data.yaml"
    yaml_file.write_text(
        """
train: images/train
val: images/val
nc: 2
names: ['dog', 'cat']
""",
        encoding="utf-8",
    )

    # Valid image and valid label
    (images_train / "img01.jpg").write_bytes(b"dummy_image_data")
    (labels_train / "img01.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n1 0.3 0.3 0.1 0.1\n", encoding="utf-8"
    )

    # Image with empty label (negative sample)
    (images_train / "img02.jpg").write_bytes(b"dummy_image_data_2")
    (labels_train / "img02.txt").write_text("", encoding="utf-8")

    # Image with missing label
    (images_train / "img03.jpg").write_bytes(b"dummy_image_data_3")

    # Orphan label (no matching image)
    (labels_train / "orphan.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    parser = YoloParser()
    config = DatasetGateConfig()
    manifest = parser.parse(tmp_path, config)

    assert manifest.format == "yolo"
    assert manifest.classes == {0: "dog", 1: "cat"}
    assert len(manifest.images) == 3

    # Check annotations
    ann_map = {a.image_relative_path: a for a in manifest.annotations}
    assert ann_map["images/train/img01.jpg"].has_label_file is True
    assert ann_map["images/train/img01.jpg"].is_empty_label is False
    assert len(ann_map["images/train/img01.jpg"].boxes) == 2

    assert ann_map["images/train/img02.jpg"].has_label_file is True
    assert ann_map["images/train/img02.jpg"].is_empty_label is True
    assert len(ann_map["images/train/img02.jpg"].boxes) == 0

    assert ann_map["images/train/img03.jpg"].has_label_file is False
    assert ann_map["images/train/img03.jpg"].is_empty_label is True

    # Check orphan label warning
    orphan_warnings = [f for f in manifest.discovery_warnings if f.rule_id == "ORPHAN_LABEL_FILE"]
    assert len(orphan_warnings) == 1
    assert "orphan.txt" in orphan_warnings[0].file_path


def test_yolo_parse_defect_annotations(tmp_path: Path):
    images_train = tmp_path / "images" / "train"
    labels_train = tmp_path / "labels" / "train"
    images_train.mkdir(parents=True)
    labels_train.mkdir(parents=True)

    (tmp_path / "data.yaml").write_text("names: ['vehicle']\n", encoding="utf-8")

    (images_train / "defects.jpg").write_bytes(b"dummy")
    (labels_train / "defects.txt").write_text(
        """
0 0.5 0.5 0.2
0 0.5 non_numeric 0.2 0.2
0 0.5 nan 0.2 0.2
-1 0.5 0.5 0.2 0.2
5 0.5 0.5 0.2 0.2
0 0.5 0.5 -0.1 0.2
0 1.5 0.5 0.2 0.2
0 0.9 0.9 0.4 0.4
""",
        encoding="utf-8",
    )

    parser = YoloParser()
    config = DatasetGateConfig()
    manifest = parser.parse(tmp_path, config)

    rule_ids = [w.rule_id for w in manifest.discovery_warnings]
    assert "MALFORMED_YOLO_ROW" in rule_ids
    assert "NON_NUMERIC_ANNOTATION" in rule_ids
    assert "NON_FINITE_ANNOTATION" in rule_ids
    assert "INVALID_CLASS_ID" in rule_ids
    assert "NON_POSITIVE_BBOX_DIMENSION" in rule_ids
    assert "INVALID_NORMALIZED_COORDINATES" in rule_ids
    assert "BBOX_OUT_OF_BOUNDS" in rule_ids
