# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 50 files · ~20,476 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 458 nodes · 1178 edges · 18 communities (13 shown, 5 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 269 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7de67a18`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Finding
- DatasetGateConfig
- html.py
- calculate_dataset_fingerprint
- generator.py
- CocoParser
- audit
- AGENTS.md
- GEMINI.md
- DatasetGate
- datasetgate
- models.py
- comparison/engine.py
- steps
- policy
- DatasetGate Rules & Defect Catalog

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 58 edges
2. `DatasetManifest` - 49 edges
3. `Finding` - 46 edges
4. `Severity` - 36 edges
5. `FindingCategory` - 27 edges
6. `CocoParser` - 27 edges
7. `run_audit()` - 26 edges
8. `YoloParser` - 24 edges
9. `ImageMetadata` - 22 edges
10. `PolicyEngine` - 22 edges

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

## Communities (18 total, 5 thin omitted)

### Community 0 - "Finding"
Cohesion: 0.10
Nodes (21): 2. Ingestion & Manifest Normalization, run_snapshot(), BoundingBox, DatasetStatistics, Finding, FindingCategory, ImageAnnotation, ImageMetadata (+13 more)

### Community 1 - "DatasetGateConfig"
Cohesion: 0.14
Nodes (7): DatasetFormat, parse_dataset(), YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "html.py"
Cohesion: 0.12
Nodes (11): _render_console_summary(), run_audit(), AuditSnapshot, ComparisonResult, generate_html_report(), generate_recommendations(), generate_json_report(), test_generate_html_report() (+3 more)

### Community 3 - "calculate_dataset_fingerprint"
Cohesion: 0.16
Nodes (10): calculate_dataset_fingerprint(), compute_file_sha256(), _build_sample_manifest(), test_fingerprint_changes_when_bounding_box_coordinate_changes(), test_fingerprint_changes_when_class_assignment_changes(), test_fingerprint_changes_when_image_content_changes(), test_fingerprint_changes_when_split_membership_changes(), test_fingerprint_deterministic_and_sha256_format() (+2 more)

### Community 4 - "generator.py"
Cohesion: 0.17
Nodes (7): create_demo_image(), generate_synthetic_coco_dataset(), generate_synthetic_yolo_dataset(), test_cli_demo_command_audit(), test_cli_demo_command_yolo(), test_generate_synthetic_coco_dataset(), test_generate_synthetic_yolo_dataset()

### Community 5 - "CocoParser"
Cohesion: 0.15
Nodes (5): CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset(), test_coco_parser_json_caching_eliminates_redundant_loads()

### Community 6 - "audit"
Cohesion: 0.09
Nodes (20): DatasetGate Product Roadmap, v0.1.0 — Foundation (Current Release), v0.2.0 — Extended Formats & Auto-Remediation (Planned), v0.3.0 — Advanced Tasks & Modalities, v1.0.0 — Enterprise & Hosted Extension (Commercialization), audit(), compare(), demo() (+12 more)

### Community 9 - "DatasetGate"
Cohesion: 0.04
Nodes (41): 1. High-Level System Architecture, 4. Statistics and Policy Evaluation, 5. Baseline Comparison & Regression Detection, 6. Exit Codes, DatasetGate Architecture & Design, `dataset`, DatasetGate Configuration Guide, Field Descriptions (+33 more)

### Community 13 - "models.py"
Cohesion: 0.07
Nodes (20): 3. Validation Pipeline, DatasetConfig, DatasetGateConfig, PolicyAction, PolicyConfig, ReportingConfig, DatasetManifest, Severity (+12 more)

### Community 14 - "comparison/engine.py"
Cohesion: 0.08
Nodes (16): compare_reports_cli(), compare_snapshots(), ExitCode, FindingDiff, test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force(), make_snapshot() (+8 more)

### Community 15 - "steps"
Cohesion: 0.08
Nodes (25): jobs, validate-dataset, name, on, pull_request, push, workflow_dispatch, branches (+17 more)

### Community 16 - "policy"
Cohesion: 0.10
Nodes (20): dataset, format, image_extensions, policy, allow_unlabeled_images, corrupted_image_policy, duplicate_policy, fail_on (+12 more)

### Community 18 - "DatasetGate Rules & Defect Catalog"
Cohesion: 0.25
Nodes (7): 1. Image Integrity Rules, 2. Annotation Integrity Rules, 3. COCO Structural Rules, 4. Duplicates & Leakage Rules, 5. Distribution Rules, DatasetGate Rules & Defect Catalog, Overriding Severities

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 212 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `models.py` to `Finding`, `DatasetGateConfig`, `html.py`, `CocoParser`, `audit`, `comparison/engine.py`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `DatasetGateConfig` (e.g. with `demo()` and `parse_dataset()`) actually correct?**
  _`DatasetGateConfig` has 32 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Finding` be split into smaller, more focused modules?**
  _Cohesion score 0.09877551020408164 - nodes in this community are weakly interconnected._
- **Why does `main()` connect `DatasetGate` to `comparison/engine.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `DatasetManifest` (e.g. with `2. Ingestion & Manifest Normalization` and `calculate_dataset_fingerprint()`) actually correct?**
  _`DatasetManifest` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Should `DatasetGateConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.13538461538461538 - nodes in this community are weakly interconnected._