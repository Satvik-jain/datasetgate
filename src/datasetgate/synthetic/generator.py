"""Synthetic dataset generator for testing and demonstration."""

from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image, ImageDraw


def create_demo_image(
    width: int = 256, height: int = 256, color: str = "blue", text: str = ""
) -> bytes:
    """Generate image bytes in memory."""
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    # Simple geometric markings
    draw.rectangle([20, 20, 80, 80], outline="white", width=2)
    draw.ellipse([120, 120, 180, 180], outline="yellow", width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def generate_synthetic_yolo_dataset(target_dir: Path) -> Path:
    """Generate a realistic synthetic YOLO dataset with both valid data and deliberate defects."""
    target_dir.mkdir(parents=True, exist_ok=True)

    img_train = target_dir / "images" / "train"
    img_val = target_dir / "images" / "val"
    lbl_train = target_dir / "labels" / "train"
    lbl_val = target_dir / "labels" / "val"

    for d in [img_train, img_val, lbl_train, lbl_val]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. data.yaml
    data_yaml = target_dir / "data.yaml"
    data_yaml.write_text(
        """# DatasetGate Demo Dataset Configuration
train: images/train
val: images/val
nc: 3
names:
  0: person
  1: vehicle
  2: traffic_sign
""",
        encoding="utf-8",
    )

    # 2. Valid Train Images & Labels
    img1_bytes = create_demo_image(300, 300, "#1f2937")
    (img_train / "train_01.jpg").write_bytes(img1_bytes)
    (lbl_train / "train_01.txt").write_text(
        "0 0.25 0.25 0.20 0.30\n1 0.70 0.70 0.25 0.25\n", encoding="utf-8"
    )

    img2_bytes = create_demo_image(400, 400, "#111827")
    (img_train / "train_02.jpg").write_bytes(img2_bytes)
    (lbl_train / "train_02.txt").write_text("0 0.50 0.50 0.30 0.40\n", encoding="utf-8")

    # 3. Legitimate Negative Sample (Empty Label)
    img3_bytes = create_demo_image(320, 320, "#374151")
    (img_train / "train_empty.jpg").write_bytes(img3_bytes)
    (lbl_train / "train_empty.txt").write_text("", encoding="utf-8")

    # 4. Deliberate Defect: Bounding Box Out of Bounds
    img4_bytes = create_demo_image(350, 350, "#4b5563")
    (img_train / "train_oob.jpg").write_bytes(img4_bytes)
    # Box center 0.95 with width 0.4 extends to 1.15 (out of bounds)
    (lbl_train / "train_oob.txt").write_text("0 0.95 0.50 0.40 0.30\n", encoding="utf-8")

    # 5. Deliberate Defect: Corrupted Image
    (img_train / "train_corrupted.jpg").write_bytes(b"CORRUPTED_RAW_NON_IMAGE_DATA_BYTES")
    (lbl_train / "train_corrupted.txt").write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    # 6. Deliberate Defect: Split Leakage!
    # Identical bytes written to both train and val
    leaked_bytes = create_demo_image(280, 280, "#dc2626")
    (img_train / "train_leaked.jpg").write_bytes(leaked_bytes)
    (lbl_train / "train_leaked.txt").write_text("0 0.4 0.4 0.2 0.2\n", encoding="utf-8")

    (img_val / "val_leaked.jpg").write_bytes(leaked_bytes)
    (lbl_val / "val_leaked.txt").write_text("0 0.4 0.4 0.2 0.2\n", encoding="utf-8")

    # 7. Valid Val Image
    val1_bytes = create_demo_image(360, 360, "#065f46")
    (img_val / "val_01.jpg").write_bytes(val1_bytes)
    (lbl_val / "val_01.txt").write_text("1 0.6 0.6 0.3 0.3\n", encoding="utf-8")

    return target_dir


def generate_synthetic_coco_dataset(target_dir: Path) -> Path:
    """Generate a realistic synthetic COCO dataset with images and annotations."""
    target_dir.mkdir(parents=True, exist_ok=True)
    images_dir = target_dir / "images"
    annotations_dir = target_dir / "annotations"
    images_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    img1_bytes = create_demo_image(640, 480, "#1e3a8a")
    (images_dir / "img_001.jpg").write_bytes(img1_bytes)

    img2_bytes = create_demo_image(640, 480, "#14532d")
    (images_dir / "img_002.jpg").write_bytes(img2_bytes)

    # Duplicate image in same split
    (images_dir / "img_002_dup.jpg").write_bytes(img2_bytes)

    coco_data = {
        "images": [
            {"id": 1, "file_name": "img_001.jpg", "width": 640, "height": 480},
            {"id": 2, "file_name": "img_002.jpg", "width": 640, "height": 480},
            {"id": 3, "file_name": "img_002_dup.jpg", "width": 640, "height": 480},
        ],
        "categories": [
            {"id": 1, "name": "person", "supercategory": "human"},
            {"id": 2, "name": "bicycle", "supercategory": "vehicle"},
        ],
        "annotations": [
            {
                "id": 101,
                "image_id": 1,
                "category_id": 1,
                "bbox": [50.0, 50.0, 100.0, 150.0],
                "area": 15000.0,
                "iscrowd": 0,
            },
            {
                "id": 102,
                "image_id": 2,
                "category_id": 2,
                "bbox": [100.0, 100.0, 200.0, 150.0],
                "area": 30000.0,
                "iscrowd": 0,
            },
            # Out of bounds annotation (x=600, w=100 > 640)
            {
                "id": 103,
                "image_id": 1,
                "category_id": 1,
                "bbox": [600.0, 50.0, 100.0, 100.0],
                "area": 10000.0,
                "iscrowd": 0,
            },
        ],
    }

    json_file = annotations_dir / "instances_train.json"
    json_file.write_text(json.dumps(coco_data, indent=2), encoding="utf-8")
    return target_dir
