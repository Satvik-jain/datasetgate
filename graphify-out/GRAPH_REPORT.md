# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 49 files · ~19,377 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 429 nodes · 1105 edges · 21 communities (15 shown, 6 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 254 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4885f053`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DatasetManifest
- YoloParser
- core/engine.py
- load_config
- CocoParser
- main.py
- AGENTS.md
- GEMINI.md
- DatasetGate
- datasetgate
- models.py
- test_comparison.py
- steps
- policy
- generator.py
- DatasetGate Rules & Defect Catalog
- ImageMetadata
- DatasetGate Architecture & Design

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 57 edges
2. `DatasetManifest` - 47 edges
3. `Finding` - 46 edges
4. `Severity` - 36 edges
5. `FindingCategory` - 27 edges
6. `run_audit()` - 26 edges
7. `CocoParser` - 24 edges
8. `YoloParser` - 24 edges
9. `PolicyEngine` - 22 edges
10. `ImageMetadata` - 21 edges

## Surprising Connections (you probably didn't know these)
- `2. Ingestion & Manifest Normalization` --references--> `ImageMetadata`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/core/models.py
- `2. Ingestion & Manifest Normalization` --references--> `BoundingBox`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/core/models.py
- `2. Ingestion & Manifest Normalization` --references--> `ImageAnnotation`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/core/models.py
- `2. Ingestion & Manifest Normalization` --references--> `DatasetManifest`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/core/models.py
- `3. Validation Pipeline` --references--> `DuplicateValidator`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/validators/duplicates.py

## Import Cycles
- None detected.

## Communities (21 total, 6 thin omitted)

### Community 0 - "DatasetManifest"
Cohesion: 0.13
Nodes (15): DatasetManifest, DatasetStatistics, Finding, PolicyCheckResult, PolicyResult, PolicyEngine, compute_dataset_statistics(), test_audit_snapshot_serialization() (+7 more)

### Community 1 - "YoloParser"
Cohesion: 0.12
Nodes (9): DatasetConfig, DatasetGateConfig, ReportingConfig, parse_dataset(), YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations() (+1 more)

### Community 2 - "core/engine.py"
Cohesion: 0.10
Nodes (14): compare_snapshots(), calculate_dataset_fingerprint(), _render_console_summary(), run_audit(), run_snapshot(), AuditSnapshot, ComparisonResult, generate_html_report() (+6 more)

### Community 4 - "load_config"
Cohesion: 0.19
Nodes (10): ConfigError, DatasetFormat, load_config(), test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on(), test_load_config_from_explicit_file(), test_load_config_invalid_yaml() (+2 more)

### Community 5 - "CocoParser"
Cohesion: 0.18
Nodes (4): CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset()

### Community 6 - "main.py"
Cohesion: 0.09
Nodes (15): DatasetGate Product Roadmap, v0.1.0 — Foundation (Current Release), v0.2.0 — Extended Formats & Auto-Remediation (Planned), v0.3.0 — Advanced Tasks & Modalities, v1.0.0 — Enterprise & Hosted Extension (Commercialization), audit(), compare(), demo() (+7 more)

### Community 9 - "DatasetGate"
Cohesion: 0.06
Nodes (30): 10. Example Terminal & HTML Outputs, 11. Baseline Comparison & Regression Detection, 12. GitHub Actions Integration, 13. System Architecture, 14. Current Limitations, 15. Roadmap, 16. Contributing, 17. License (+22 more)

### Community 13 - "models.py"
Cohesion: 0.08
Nodes (12): 3. Validation Pipeline, PolicyAction, PolicyConfig, BoundingBox, FindingCategory, ImageAnnotation, Severity, BaseParser (+4 more)

### Community 14 - "test_comparison.py"
Cohesion: 0.15
Nodes (8): test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force(), make_snapshot(), test_compare_cli_command(), test_compare_identical_snapshots(), test_compare_new_error_regression(), test_compare_resolved_finding()

### Community 15 - "steps"
Cohesion: 0.08
Nodes (25): jobs, validate-dataset, name, on, pull_request, push, workflow_dispatch, branches (+17 more)

### Community 16 - "policy"
Cohesion: 0.10
Nodes (20): dataset, format, image_extensions, policy, allow_unlabeled_images, corrupted_image_policy, duplicate_policy, fail_on (+12 more)

### Community 17 - "generator.py"
Cohesion: 0.16
Nodes (7): create_demo_image(), generate_synthetic_coco_dataset(), generate_synthetic_yolo_dataset(), test_cli_demo_command_audit(), test_cli_demo_command_yolo(), test_generate_synthetic_coco_dataset(), test_generate_synthetic_yolo_dataset()

### Community 18 - "DatasetGate Rules & Defect Catalog"
Cohesion: 0.25
Nodes (7): 1. Image Integrity Rules, 2. Annotation Integrity Rules, 3. COCO Structural Rules, 4. Duplicates & Leakage Rules, 5. Distribution Rules, DatasetGate Rules & Defect Catalog, Overriding Severities

### Community 19 - "ImageMetadata"
Cohesion: 0.18
Nodes (9): ImageMetadata, compute_file_sha256(), DuplicateValidator, create_sample_png_bytes(), test_annotation_validator_unlabeled_policy(), test_duplicate_validator_cross_split_leakage(), test_duplicate_validator_intra_split(), test_image_integrity_policy_actions() (+1 more)

### Community 20 - "DatasetGate Architecture & Design"
Cohesion: 0.12
Nodes (12): 1. High-Level System Architecture, 2. Ingestion & Manifest Normalization, 4. Statistics and Policy Evaluation, 5. Baseline Comparison & Regression Detection, 6. Exit Codes, DatasetGate Architecture & Design, `dataset`, DatasetGate Configuration Guide (+4 more)

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 202 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `YoloParser` to `DatasetManifest`, `core/engine.py`, `.parse`, `load_config`, `CocoParser`, `main.py`, `models.py`, `ImageMetadata`?**
  _High betweenness centrality (0.132) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `DatasetGateConfig` (e.g. with `demo()` and `parse_dataset()`) actually correct?**
  _`DatasetGateConfig` has 31 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DatasetManifest` be split into smaller, more focused modules?**
  _Cohesion score 0.13229018492176386 - nodes in this community are weakly interconnected._
- **Why does `DatasetGate` connect `DatasetGate` to `DatasetGate Architecture & Design`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `DatasetManifest` (e.g. with `2. Ingestion & Manifest Normalization` and `calculate_dataset_fingerprint()`) actually correct?**
  _`DatasetManifest` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Should `YoloParser` be split into smaller, more focused modules?**
  _Cohesion score 0.12413793103448276 - nodes in this community are weakly interconnected._