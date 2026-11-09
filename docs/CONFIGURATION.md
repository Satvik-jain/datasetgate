# DatasetGate Configuration Guide

DatasetGate is configured using a `datasetgate.yaml` (or `datasetgate.yml`) file located in the project root or passed explicitly via `--config <path>`.

To initialize a recommended configuration file:

```bash
datasetgate init
```

## Schema Reference

```yaml
version: 1

dataset:
  # Ingestion format: 'auto', 'yolo', or 'coco'
  format: auto

  # Supported image extensions (case-insensitive)
  image_extensions:
    - .jpg
    - .jpeg
    - .png
    - .bmp
    - .webp
    - .tif
    - .tiff

  # Optional explicit path to YOLO data.yaml
  yolo_data_yaml: null

  # Optional mapping of split name to COCO json annotation file
  coco_annotation_files: {}

policy:
  # Split coverage rules
  require_all_classes_in_train: true
  require_all_classes_in_val: false

  # Label distribution rules
  allow_unlabeled_images: true
  max_empty_label_rate: 0.20
  max_class_imbalance_ratio: 25.0

  # Duplicates and Leakage policies: 'ignore', 'warn', 'fail'
  duplicate_policy: warn
  split_leakage_policy: fail

  # Physical integrity policies: 'ignore', 'warn', 'fail'
  corrupted_image_policy: fail
  missing_image_policy: fail
  out_of_bounds_policy: fail

  # Overall gate failure trigger severities
  fail_on:
    - error

  # Custom rule severity overrides
  rule_severities:
    # Example: demote bounding box boundary errors to warnings
    # BBOX_OUT_OF_BOUNDS: warning

reporting:
  output_dir: reports
  generate_html: true
  generate_json: true
```

## Field Descriptions

### `dataset`

| Field | Type | Default | Description |
|---|---|---|---|
| `format` | string | `auto` | Dataset ingestion parser: `auto`, `yolo`, or `coco`. |
| `image_extensions` | list[str] | `[.jpg, .jpeg, .png, ...]` | Allowed image extensions. Images with other extensions generate `UNSUPPORTED_IMAGE_FORMAT`. |
| `yolo_data_yaml` | string / null | `null` | Optional path to `data.yaml` relative to dataset root. |
| `coco_annotation_files` | map | `{}` | Optional mapping of split names to COCO JSON annotation files. |

### `policy`

| Field | Type | Default | Description |
|---|---|---|---|
| `require_all_classes_in_train` | bool | `true` | Fails the gate if any declared class has 0 annotations in the train split. |
| `require_all_classes_in_val` | bool | `false` | Fails the gate if any declared class has 0 annotations in the val split. |
| `allow_unlabeled_images` | bool | `true` | When `false`, flags unannotated or missing label images as policy errors. |
| `max_empty_label_rate` | float | `0.20` | Maximum allowable fraction of unannotated images ($0.0$ to $1.0$). |
| `max_class_imbalance_ratio` | float / null | `25.0` | Maximum allowable ratio of most-frequent to least-frequent class instance counts. |
| `duplicate_policy` | string | `warn` | Action on exact duplicate images within the same split: `ignore`, `warn`, `fail`. |
| `split_leakage_policy` | string | `fail` | Action when an exact duplicate image appears across multiple splits: `ignore`, `warn`, `fail`. |
| `corrupted_image_policy` | string | `fail` | Action on undecodable or damaged image files. |
| `missing_image_policy` | string | `fail` | Action when an image referenced by an annotation is missing on disk. |
| `out_of_bounds_policy` | string | `fail` | Action when bounding boxes exceed image boundaries. |
| `fail_on` | list[str] | `["error"]` | Severities that cause the gate to exit with code `1`. Use `["error", "warning"]` for strict CI. |
| `rule_severities` | map | `{}` | Key-value overrides mapping any Rule ID to `info`, `warning`, or `error`. |

### `reporting`

| Field | Type | Default | Description |
|---|---|---|---|
| `output_dir` | string | `reports` | Directory where `report.json` and `report.html` are written. |
| `generate_html` | bool | `true` | Whether to render the visual self-contained HTML report. |
| `generate_json` | bool | `true` | Whether to write the machine-readable JSON report. |
