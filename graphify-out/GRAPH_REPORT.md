# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 50 files · ~20,263 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 452 nodes · 1161 edges · 19 communities (14 shown, 5 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 265 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e9cb858e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Finding
- DatasetGateConfig
- html.py
- calculate_dataset_fingerprint
- load_config
- CocoParser
- main.py
- AGENTS.md
- GEMINI.md
- DatasetGate
- datasetgate
- models.py
- comparison/engine.py
- steps
- policy
- DatasetGate Architecture & Design
- DatasetGate Rules & Defect Catalog

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 57 edges
2. `DatasetManifest` - 49 edges
3. `Finding` - 46 edges
4. `Severity` - 36 edges
5. `FindingCategory` - 27 edges
6. `run_audit()` - 26 edges
7. `CocoParser` - 24 edges
8. `YoloParser` - 24 edges
9. `ImageMetadata` - 22 edges
10. `PolicyEngine` - 22 edges

## Surprising Connections (you probably didn't know these)
- `v0.1.0 — Foundation (Current Release)` --references--> `init()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py
- `v0.1.0 — Foundation (Current Release)` --references--> `audit()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py
- `v0.1.0 — Foundation (Current Release)` --references--> `snapshot()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py
- `v0.1.0 — Foundation (Current Release)` --references--> `compare()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py
- `v0.1.0 — Foundation (Current Release)` --references--> `demo()`  [INFERRED]
  docs/ROADMAP.md → src/datasetgate/cli/main.py

## Import Cycles
- None detected.

## Communities (19 total, 5 thin omitted)

### Community 0 - "Finding"
Cohesion: 0.12
Nodes (17): PolicyConfig, DatasetStatistics, Finding, FindingCategory, PolicyCheckResult, PolicyResult, Severity, PolicyEngine (+9 more)

### Community 1 - "DatasetGateConfig"
Cohesion: 0.09
Nodes (8): DatasetConfig, DatasetGateConfig, ReportingConfig, YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "html.py"
Cohesion: 0.12
Nodes (9): _render_console_summary(), run_audit(), AuditSnapshot, ComparisonResult, generate_html_report(), generate_recommendations(), generate_json_report(), test_run_audit_end_to_end() (+1 more)

### Community 3 - "calculate_dataset_fingerprint"
Cohesion: 0.22
Nodes (9): calculate_dataset_fingerprint(), _build_sample_manifest(), test_fingerprint_changes_when_bounding_box_coordinate_changes(), test_fingerprint_changes_when_class_assignment_changes(), test_fingerprint_changes_when_image_content_changes(), test_fingerprint_changes_when_split_membership_changes(), test_fingerprint_deterministic_and_sha256_format(), test_fingerprint_order_independence() (+1 more)

### Community 4 - "load_config"
Cohesion: 0.19
Nodes (10): ConfigError, DatasetFormat, load_config(), test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on(), test_load_config_from_explicit_file(), test_load_config_invalid_yaml() (+2 more)

### Community 5 - "CocoParser"
Cohesion: 0.10
Nodes (14): 2. Ingestion & Manifest Normalization, parse_dataset(), BoundingBox, DatasetManifest, ImageAnnotation, ImageMetadata, CocoParser, compute_dataset_statistics() (+6 more)

### Community 6 - "main.py"
Cohesion: 0.06
Nodes (21): v0.1.0 — Foundation (Current Release), audit(), compare(), demo(), init(), snapshot(), version(), compare_reports_cli() (+13 more)

### Community 9 - "DatasetGate"
Cohesion: 0.06
Nodes (30): 10. Example Terminal & HTML Outputs, 11. Baseline Comparison & Regression Detection, 12. GitHub Actions Integration, 13. System Architecture, 14. Current Limitations, 15. Roadmap, 16. Contributing, 17. License (+22 more)

### Community 13 - "models.py"
Cohesion: 0.08
Nodes (13): 3. Validation Pipeline, PolicyAction, BaseParser, AnnotationValidator, BaseValidator, compute_file_sha256(), DuplicateValidator, ImageIntegrityValidator (+5 more)

### Community 14 - "comparison/engine.py"
Cohesion: 0.12
Nodes (11): compare_snapshots(), FindingDiff, make_snapshot(), test_audit_with_invalid_schema_baseline_fails(), test_audit_with_malformed_json_baseline_fails(), test_audit_with_missing_baseline_fails(), test_compare_cli_command(), test_compare_cli_with_malformed_baseline_fails() (+3 more)

### Community 15 - "steps"
Cohesion: 0.08
Nodes (25): jobs, validate-dataset, name, on, pull_request, push, workflow_dispatch, branches (+17 more)

### Community 16 - "policy"
Cohesion: 0.10
Nodes (20): dataset, format, image_extensions, policy, allow_unlabeled_images, corrupted_image_policy, duplicate_policy, fail_on (+12 more)

### Community 17 - "DatasetGate Architecture & Design"
Cohesion: 0.11
Nodes (15): 1. High-Level System Architecture, 4. Statistics and Policy Evaluation, 5. Baseline Comparison & Regression Detection, 6. Exit Codes, DatasetGate Architecture & Design, `dataset`, DatasetGate Configuration Guide, Field Descriptions (+7 more)

### Community 18 - "DatasetGate Rules & Defect Catalog"
Cohesion: 0.25
Nodes (7): 1. Image Integrity Rules, 2. Annotation Integrity Rules, 3. COCO Structural Rules, 4. Duplicates & Leakage Rules, 5. Distribution Rules, DatasetGate Rules & Defect Catalog, Overriding Severities

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 210 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetGateConfig` to `Finding`, `html.py`, `load_config`, `CocoParser`, `main.py`, `models.py`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `DatasetGateConfig` (e.g. with `demo()` and `parse_dataset()`) actually correct?**
  _`DatasetGateConfig` has 31 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Finding` be split into smaller, more focused modules?**
  _Cohesion score 0.12439024390243902 - nodes in this community are weakly interconnected._
- **Why does `DatasetGate` connect `DatasetGate` to `DatasetGate Architecture & Design`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `DatasetManifest` (e.g. with `2. Ingestion & Manifest Normalization` and `calculate_dataset_fingerprint()`) actually correct?**
  _`DatasetManifest` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Should `DatasetGateConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.09411764705882353 - nodes in this community are weakly interconnected._