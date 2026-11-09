# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 40 files · ~13,378 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 299 nodes · 877 edges · 15 communities (9 shown, 6 thin omitted)
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 193 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `09efbcf5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DatasetManifest
- YoloParser
- core/engine.py
- models.py
- load_config
- Finding
- main.py
- AGENTS.md
- GEMINI.md
- README.md
- datasetgate
- DatasetGateConfig
- test_cli.py

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 48 edges
2. `Finding` - 42 edges
3. `DatasetManifest` - 41 edges
4. `Severity` - 31 edges
5. `run_audit()` - 24 edges
6. `FindingCategory` - 23 edges
7. `CocoParser` - 23 edges
8. `YoloParser` - 23 edges
9. `AuditSnapshot` - 20 edges
10. `ImageMetadata` - 19 edges

## Surprising Connections (you probably didn't know these)
- `test_default_config_valid()` --uses--> `DatasetFormat`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_load_config_from_explicit_file()` --uses--> `DatasetFormat`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_load_config_from_explicit_file()` --uses--> `PolicyAction`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_coco_parse_defects()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_coco_parser.py → src/datasetgate/core/config.py
- `test_coco_parse_valid_dataset()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_coco_parser.py → src/datasetgate/core/config.py

## Import Cycles
- None detected.

## Communities (15 total, 6 thin omitted)

### Community 0 - "DatasetManifest"
Cohesion: 0.10
Nodes (14): DatasetGateConfig, PolicyAction, DatasetManifest, AnnotationValidator, BaseValidator, compute_file_sha256(), DuplicateValidator, ImageIntegrityValidator (+6 more)

### Community 1 - "YoloParser"
Cohesion: 0.12
Nodes (10): BoundingBox, ImageAnnotation, ImageMetadata, YoloParser, test_compute_dataset_statistics(), test_policy_engine_missing_class_in_train(), test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml() (+2 more)

### Community 2 - "core/engine.py"
Cohesion: 0.08
Nodes (10): DatasetFormat, calculate_dataset_fingerprint(), parse_dataset(), _render_console_summary(), run_audit(), ComparisonResult, generate_html_report(), generate_recommendations() (+2 more)

### Community 3 - "models.py"
Cohesion: 0.13
Nodes (3): DatasetConfig, PolicyConfig, ReportingConfig

### Community 4 - "load_config"
Cohesion: 0.25
Nodes (8): ConfigError, load_config(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on(), test_load_config_from_explicit_file(), test_load_config_invalid_yaml(), test_load_config_nonexistent_file(), test_load_config_validation_error()

### Community 5 - "Finding"
Cohesion: 0.08
Nodes (22): compare_snapshots(), run_snapshot(), AuditSnapshot, DatasetStatistics, Finding, FindingCategory, FindingDiff, PolicyCheckResult (+14 more)

### Community 6 - "main.py"
Cohesion: 0.12
Nodes (9): audit(), compare(), init(), main(), snapshot(), version(), compare_reports_cli(), generate_default_config_yaml() (+1 more)

### Community 13 - "DatasetGateConfig"
Cohesion: 0.10
Nodes (5): BaseParser, CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset()

### Community 14 - "test_cli.py"
Cohesion: 0.28
Nodes (3): test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force()

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 122 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetManifest` to `YoloParser`, `core/engine.py`, `models.py`, `load_config`, `Finding`, `DatasetGateConfig`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `DatasetGateConfig` (e.g. with `parse_dataset()` and `run_audit()`) actually correct?**
  _`DatasetGateConfig` has 24 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DatasetManifest` be split into smaller, more focused modules?**
  _Cohesion score 0.10106382978723404 - nodes in this community are weakly interconnected._
- **Why does `Finding` connect `Finding` to `DatasetManifest`, `YoloParser`, `core/engine.py`, `models.py`, `DatasetGateConfig`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Finding` (e.g. with `compare_snapshots()` and `run_audit()`) actually correct?**
  _`Finding` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Should `YoloParser` be split into smaller, more focused modules?**
  _Cohesion score 0.12473118279569892 - nodes in this community are weakly interconnected._