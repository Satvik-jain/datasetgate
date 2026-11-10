# DatasetGate Product Roadmap

DatasetGate follows a transparent, community-driven roadmap focused on local-first engineering workflows.

## v0.1.2 — Foundation & Reliability (Current Release)

- [x] Ingestion for YOLO object detection datasets (`data.yaml`, Ultralytics layout, nested splits).
- [x] Ingestion for COCO object detection datasets (`images`, `annotations`, `categories`) with JSON caching for fast single-pass parsing.
- [x] Physical image integrity verification (Pillow validation, corruption detection, dimension checking).
- [x] Annotation format and boundary checking (negative dims, NaN/Inf, out-of-bounds bounding boxes).
- [x] Exact duplicate detection via chunked streaming SHA-256 hashes.
- [x] Cross-split data leakage detection (train vs val vs test).
- [x] Dataset distribution statistics and imbalance calculations.
- [x] Configurable quality policy actions (`ignore`, `warn`, `fail`) and rule severity overrides.
- [x] Deterministic 64-character SHA-256 dataset fingerprinting incorporating image content hashes and canonicalized bounding box coordinates.
- [x] Machine-readable `report.json` and interactive, self-contained `report.html`.
- [x] Baseline comparison engine and regression detection with actionable error handling for missing or malformed baselines.
- [x] CLI interface with `init`, `audit`, `snapshot`, `compare`, `demo`, and `version`.
- [x] GitHub Actions workflow integration and automated pipeline gating.

---

## v0.2.0 — Extended Formats & Auto-Remediation (Planned)

- [ ] **VOC / XML Format Support**: Ingestion of Pascal VOC XML annotation structures.
- [ ] **Automated Remediation Commands**:
  - `datasetgate fix --clip-boxes`: Automatically clips out-of-bounds bounding boxes to $[0, 1]$.
  - `datasetgate fix --remove-leakage`: Automatically removes leaked images from validation splits.
  - `datasetgate fix --remove-orphans`: Safely removes unpaired `.txt` label files.
- [ ] **Dataset Slicing & Export**: Export cleaned datasets stripped of corrupted files and duplicates.
- [ ] **Perceptual Hash Duplicate Detection**: Support for pHash / dHash to catch resized or re-encoded duplicate images without heavy neural networks.

---

## v0.3.0 — Advanced Tasks & Modalities

- [ ] **Segmentation Support**: YOLO polygon segmentation (`class x1 y1 x2 y2 ...`) and COCO RLE / polygon masks.
- [ ] **Keypoint / Pose Detection**: Validation of keypoint annotations and visibility flags.
- [ ] **Classification Datasets**: Validation of folder-per-class image classification structures.
- [ ] **Small Object Analysis**: Statistics and warnings for bounding boxes smaller than configurable pixel thresholds (e.g. $< 12 \times 12$ px) that models struggle to detect.

---

## v1.0.0 — Enterprise & Hosted Extension (Commercialization)

- [ ] Optional self-hosted server mode for team dataset registry.
- [ ] Webhook triggers on S3 / GCS bucket uploads.
- [ ] Deep learning model performance correlation: track whether passing the gate directly correlates with mAP gains.
- [ ] Multi-user approval workflow for releasing gold-standard training datasets.
