# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 49 files · ~18,496 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 423 nodes · 1044 edges · 18 communities (12 shown, 6 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 209 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `61b95229`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DatasetManifest
- YoloParser
- core/engine.py
- load_config
- main.py
- AGENTS.md
- GEMINI.md
- DatasetGate
- datasetgate
- models.py
- Severity
- steps
- policy
- generator.py
- DatasetGate Rules & Defect Catalog

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 50 edges
2. `Finding` - 42 edges
3. `DatasetManifest` - 42 edges
4. `Severity` - 31 edges
5. `run_audit()` - 25 edges
6. `FindingCategory` - 23 edges
7. `CocoParser` - 23 edges
8. `YoloParser` - 23 edges
9. `ImageMetadata` - 20 edges
10. `AuditSnapshot` - 20 edges

## Surprising Connections (you probably didn't know these)
- `2. Ingestion & Manifest Normalization` --references--> `DatasetManifest`  [INFERRED]
  docs/ARCHITECTURE.md → src/datasetgate/core/models.py
- `v0.1.0 — Foundation (Current Release)` --references--> `init()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py
- `v0.1.0 — Foundation (Current Release)` --references--> `audit()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py
- `v0.1.0 — Foundation (Current Release)` --references--> `snapshot()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py
- `v0.1.0 — Foundation (Current Release)` --references--> `compare()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py

## Import Cycles
- None detected.

## Communities (18 total, 6 thin omitted)

### Community 0 - "DatasetManifest"
Cohesion: 0.08
Nodes (27): 3. Validation Pipeline, DatasetGateConfig, calculate_dataset_fingerprint(), _render_console_summary(), run_audit(), run_snapshot(), DatasetManifest, DatasetStatistics (+19 more)

### Community 1 - "YoloParser"
Cohesion: 0.16
Nodes (6): parse_dataset(), YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "core/engine.py"
Cohesion: 0.13
Nodes (8): AuditSnapshot, ComparisonResult, generate_html_report(), generate_recommendations(), generate_json_report(), test_generate_html_report(), test_generate_json_report(), test_run_audit_end_to_end()

### Community 4 - "load_config"
Cohesion: 0.17
Nodes (11): ConfigError, DatasetFormat, load_config(), PolicyAction, test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on(), test_load_config_from_explicit_file() (+3 more)

### Community 6 - "main.py"
Cohesion: 0.09
Nodes (14): DatasetGate Product Roadmap, v0.1.0 — Foundation (Current Release), v0.2.0 — Extended Formats & Auto-Remediation (Planned), v0.3.0 — Advanced Tasks & Modalities, v1.0.0 — Enterprise & Hosted Extension (Commercialization), audit(), compare(), demo() (+6 more)

### Community 9 - "DatasetGate"
Cohesion: 0.04
Nodes (41): 1. High-Level System Architecture, 4. Statistics and Policy Evaluation, 5. Baseline Comparison & Regression Detection, 6. Exit Codes, DatasetGate Architecture & Design, `dataset`, DatasetGate Configuration Guide, Field Descriptions (+33 more)

### Community 13 - "models.py"
Cohesion: 0.08
Nodes (10): 2. Ingestion & Manifest Normalization, BoundingBox, ImageAnnotation, ImageMetadata, BaseParser, CocoParser, test_coco_can_parse(), test_coco_parse_defects() (+2 more)

### Community 14 - "Severity"
Cohesion: 0.09
Nodes (12): compare_snapshots(), DatasetConfig, PolicyConfig, ReportingConfig, FindingDiff, Severity, make_snapshot(), test_compare_cli_command() (+4 more)

### Community 15 - "steps"
Cohesion: 0.08
Nodes (25): jobs, validate-dataset, name, on, pull_request, push, workflow_dispatch, branches (+17 more)

### Community 16 - "policy"
Cohesion: 0.10
Nodes (20): dataset, format, image_extensions, policy, allow_unlabeled_images, corrupted_image_policy, duplicate_policy, fail_on (+12 more)

### Community 17 - "generator.py"
Cohesion: 0.10
Nodes (10): create_demo_image(), generate_synthetic_coco_dataset(), generate_synthetic_yolo_dataset(), test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force(), test_cli_demo_command_audit(), test_cli_demo_command_yolo() (+2 more)

### Community 18 - "DatasetGate Rules & Defect Catalog"
Cohesion: 0.25
Nodes (7): 1. Image Integrity Rules, 2. Annotation Integrity Rules, 3. COCO Structural Rules, 4. Duplicates & Leakage Rules, 5. Distribution Rules, DatasetGate Rules & Defect Catalog, Overriding Severities

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 202 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetManifest` to `YoloParser`, `core/engine.py`, `.parse`, `load_config`, `main.py`, `models.py`, `Severity`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `DatasetGateConfig` (e.g. with `demo()` and `parse_dataset()`) actually correct?**
  _`DatasetGateConfig` has 25 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DatasetManifest` be split into smaller, more focused modules?**
  _Cohesion score 0.0762739370334307 - nodes in this community are weakly interconnected._
- **Why does `main()` connect `DatasetGate` to `main.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Finding` (e.g. with `compare_snapshots()` and `run_audit()`) actually correct?**
  _`Finding` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `core/engine.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12987012987012986 - nodes in this community are weakly interconnected._