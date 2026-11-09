# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 49 files · ~18,447 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 422 nodes · 1033 edges · 19 communities (13 shown, 6 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 199 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `06795572`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DatasetManifest
- YoloParser
- core/engine.py
- BaseParser
- load_config
- models.py
- main.py
- AGENTS.md
- GEMINI.md
- DatasetGate
- datasetgate
- DatasetGateConfig
- test_comparison.py
- steps
- policy
- generator.py
- DatasetGate Rules & Defect Catalog

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 50 edges
2. `DatasetManifest` - 42 edges
3. `Finding` - 42 edges
4. `Severity` - 31 edges
5. `run_audit()` - 25 edges
6. `YoloParser` - 23 edges
7. `CocoParser` - 23 edges
8. `FindingCategory` - 23 edges
9. `AuditSnapshot` - 20 edges
10. `ImageMetadata` - 20 edges

## Surprising Connections (you probably didn't know these)
- `2. Ingestion & Manifest Normalization` --references--> `ImageMetadata`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/core/models.py
- `3. Validation Pipeline` --references--> `AnnotationValidator`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/validators/annotations.py
- `3. Validation Pipeline` --references--> `DuplicateValidator`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/validators/duplicates.py
- `3. Validation Pipeline` --references--> `ImageIntegrityValidator`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/validators/image_integrity.py
- `2. Ingestion & Manifest Normalization` --references--> `BoundingBox`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/core/models.py

## Import Cycles
- None detected.

## Communities (19 total, 6 thin omitted)

### Community 0 - "DatasetManifest"
Cohesion: 0.07
Nodes (18): DatasetConfig, DatasetGateConfig, PolicyAction, PolicyConfig, ReportingConfig, FindingCategory, ImageMetadata, Severity (+10 more)

### Community 1 - "YoloParser"
Cohesion: 0.16
Nodes (6): parse_dataset(), YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "core/engine.py"
Cohesion: 0.12
Nodes (9): _render_console_summary(), run_audit(), AuditSnapshot, ComparisonResult, generate_html_report(), generate_recommendations(), generate_json_report(), test_generate_html_report() (+1 more)

### Community 4 - "load_config"
Cohesion: 0.16
Nodes (11): ConfigError, DatasetFormat, generate_default_config_yaml(), load_config(), test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on(), test_load_config_from_explicit_file() (+3 more)

### Community 5 - "models.py"
Cohesion: 0.09
Nodes (18): 2. Ingestion & Manifest Normalization, calculate_dataset_fingerprint(), run_snapshot(), BoundingBox, DatasetManifest, DatasetStatistics, Finding, ImageAnnotation (+10 more)

### Community 6 - "main.py"
Cohesion: 0.15
Nodes (11): DatasetGate Product Roadmap, v0.1.0 — Foundation (Current Release), v0.2.0 — Extended Formats & Auto-Remediation (Planned), v0.3.0 — Advanced Tasks & Modalities, v1.0.0 — Enterprise & Hosted Extension (Commercialization), audit(), compare(), demo() (+3 more)

### Community 9 - "DatasetGate"
Cohesion: 0.05
Nodes (39): 1. High-Level System Architecture, 3. Validation Pipeline, 4. Statistics and Policy Evaluation, 5. Baseline Comparison & Regression Detection, 6. Exit Codes, DatasetGate Architecture & Design, `dataset`, DatasetGate Configuration Guide (+31 more)

### Community 13 - "DatasetGateConfig"
Cohesion: 0.18
Nodes (4): CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset()

### Community 14 - "test_comparison.py"
Cohesion: 0.08
Nodes (13): main(), compare_reports_cli(), compare_snapshots(), ExitCode, FindingDiff, test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force() (+5 more)

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

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 203 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetManifest` to `YoloParser`, `core/engine.py`, `BaseParser`, `load_config`, `models.py`, `main.py`, `DatasetGateConfig`, `test_comparison.py`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `DatasetGateConfig` (e.g. with `parse_dataset()` and `run_audit()`) actually correct?**
  _`DatasetGateConfig` has 24 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DatasetManifest` be split into smaller, more focused modules?**
  _Cohesion score 0.07135135135135136 - nodes in this community are weakly interconnected._
- **Why does `DatasetGate Architecture & Design` connect `DatasetGate` to `models.py`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `DatasetManifest` (e.g. with `2. Ingestion & Manifest Normalization` and `calculate_dataset_fingerprint()`) actually correct?**
  _`DatasetManifest` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `core/engine.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._