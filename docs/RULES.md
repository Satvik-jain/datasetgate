# DatasetGate Rules & Defect Catalog

This catalog documents all defect rules checked by DatasetGate, their default severity, root cause, and recommended developer remediation.

## 1. Image Integrity Rules

| Rule ID | Default Severity | Category | Description & Remediation |
|---|---|---|---|
| `MISSING_IMAGE_FILE` | `ERROR` | `IMAGE_INTEGRITY` | Referenced image does not exist on disk. Verify file paths, unzip completion, or regenerate dataset split. |
| `EMPTY_IMAGE_FILE` | `ERROR` | `IMAGE_INTEGRITY` | Image file has 0 bytes. Caused by aborted downloads or disk write errors. Remove or re-download. |
| `CORRUPTED_IMAGE` | `ERROR` | `IMAGE_INTEGRITY` | Image header is invalid or undecodable by Pillow. Will crash training DataLoader workers. Repair or discard image. |
| `INVALID_IMAGE_DIMENSIONS` | `ERROR` | `IMAGE_INTEGRITY` | Image width or height is $\le 0$. Replace with valid image file. |
| `UNSUPPORTED_IMAGE_FORMAT` | `WARNING` | `IMAGE_INTEGRITY` | Image format extension is not in `image_extensions` list. Convert to JPEG/PNG or update configuration. |

## 2. Annotation Integrity Rules

| Rule ID | Default Severity | Category | Description & Remediation |
|---|---|---|---|
| `MALFORMED_YOLO_ROW` | `ERROR` | `ANNOTATION_INTEGRITY` | Line does not contain exactly 5 tokens (`class_id x_center y_center width height`). Correct exporter. |
| `NON_NUMERIC_ANNOTATION` | `ERROR` | `ANNOTATION_INTEGRITY` | Token cannot be parsed as a floating-point number. |
| `NON_FINITE_ANNOTATION` | `ERROR` | `ANNOTATION_INTEGRITY` | Coordinate contains `NaN` or `Inf`. Replace with valid finite coordinates. |
| `INVALID_CLASS_ID` | `ERROR` | `ANNOTATION_INTEGRITY` | Class ID is negative, non-integer, or exceeds the defined class count. Align with `data.yaml` or categories. |
| `NON_POSITIVE_BBOX_DIMENSION` | `ERROR` | `ANNOTATION_INTEGRITY` | Bounding box width or height is $\le 0$. Remove inverted or collapsed annotations. |
| `INVALID_NORMALIZED_COORDINATES` | `ERROR` | `ANNOTATION_INTEGRITY` | Center coordinate is outside normalized range $[0, 1]$ in YOLO. |
| `BBOX_OUT_OF_BOUNDS` | `ERROR` | `ANNOTATION_INTEGRITY` | Bounding box boundary extends outside $[0, 1]$ (YOLO) or image pixel width/height (COCO). Apply bounding box clipping. |
| `ORPHAN_LABEL_FILE` | `WARNING` | `ANNOTATION_INTEGRITY` | Label file exists in `labels/` without a corresponding image in `images/`. Remove orphan label or restore image. |
| `LABEL_FILE_UNREADABLE` | `ERROR` | `ANNOTATION_INTEGRITY` | Label file cannot be read due to file permissions or encoding corruption. |
| `UNLABELED_IMAGE_MISSING` | `ERROR` | `ANNOTATION_INTEGRITY` | Image has no label file when `allow_unlabeled_images: false`. Provide annotation or enable unlabeled images. |
| `UNLABELED_IMAGE_EMPTY` | `ERROR` | `ANNOTATION_INTEGRITY` | Image has an empty label file when `allow_unlabeled_images: false`. |

## 3. COCO Structural Rules

| Rule ID | Default Severity | Category | Description & Remediation |
|---|---|---|---|
| `CORRUPTED_COCO_JSON` | `ERROR` | `STRUCTURE` | JSON file is syntactically invalid or cannot be decoded. |
| `INVALID_COCO_STRUCTURE` | `ERROR` | `STRUCTURE` | Top-level JSON is not an object or lacks required arrays (`images`, `annotations`, `categories`). |
| `DUPLICATE_IMAGE_ID` | `ERROR` | `STRUCTURE` | Multiple images share the same `id`. Re-index image IDs. |
| `DUPLICATE_ANNOTATION_ID` | `ERROR` | `STRUCTURE` | Multiple annotations share the same `id`. Re-index annotation IDs. |
| `DUPLICATE_CATEGORY_ID` | `ERROR` | `STRUCTURE` | Multiple categories share the same `id`. |
| `MISSING_IMAGE_REFERENCE` | `ERROR` | `ANNOTATION_INTEGRITY` | Annotation `image_id` references a nonexistent image. |
| `MISSING_CATEGORY_REFERENCE` | `ERROR` | `ANNOTATION_INTEGRITY` | Annotation `category_id` references a nonexistent category. |
| `INVALID_COCO_BBOX` | `ERROR` | `ANNOTATION_INTEGRITY` | `bbox` array is not a 4-element numeric array `[x, y, w, h]`. |
| `NEGATIVE_BBOX_COORDINATE` | `ERROR` | `ANNOTATION_INTEGRITY` | `x` or `y` coordinate is negative. |

## 4. Duplicates & Leakage Rules

| Rule ID | Default Severity | Category | Description & Remediation |
|---|---|---|---|
| `SPLIT_LEAKAGE` | `ERROR` | `DUPLICATES_AND_LEAKAGE` | Identical image bytes appear in multiple splits (e.g., `train` and `val`). Remove duplicate from validation/test splits to ensure truthful performance metrics. |
| `EXACT_DUPLICATE_IMAGE` | `WARNING` | `DUPLICATES_AND_LEAKAGE` | Exact byte-for-byte duplicate images exist within the same split. Deduplicate to save GPU training time. |

## 5. Distribution Rules

| Rule ID | Default Severity | Category | Description & Remediation |
|---|---|---|---|
| `MISSING_CLASS_IN_TRAIN` | `ERROR` | `DISTRIBUTION` | A declared class has 0 annotations in the train split. Model cannot learn to detect this class. |
| `MISSING_CLASS_IN_VAL` | `ERROR` | `DISTRIBUTION` | A declared class has 0 annotations in the val split when `require_all_classes_in_val: true`. |
| `EXCESSIVE_EMPTY_LABELS` | `ERROR` | `DISTRIBUTION` | Percentage of unannotated images exceeds `max_empty_label_rate`. |
| `EXCESSIVE_CLASS_IMBALANCE` | `WARNING` | `DISTRIBUTION` | Imbalance ratio between most and least frequent class exceeds `max_class_imbalance_ratio`. |

## Overriding Severities

Any rule severity can be overridden in `datasetgate.yaml`:

```yaml
policy:
  rule_severities:
    BBOX_OUT_OF_BOUNDS: warning
    EXACT_DUPLICATE_IMAGE: error
```
