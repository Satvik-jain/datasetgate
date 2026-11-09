# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 39 files · ~12,529 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 288 nodes · 823 edges · 14 communities (8 shown, 6 thin omitted)
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 178 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `03ad8e85`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DatasetManifest
- YoloParser
- core/engine.py
- models.py
- load_config
- test_cli.py
- audit
- AGENTS.md
- GEMINI.md
- README.md
- datasetgate
- DatasetGateConfig

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 48 edges
2. `DatasetManifest` - 41 edges
3. `Finding` - 37 edges
4. `Severity` - 27 edges
5. `run_audit()` - 23 edges
6. `CocoParser` - 23 edges
7. `YoloParser` - 23 edges
8. `FindingCategory` - 21 edges
9. `ImageMetadata` - 19 edges
10. `run_snapshot()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_default_config_valid()` --uses--> `PolicyAction`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_load_config_from_explicit_file()` --uses--> `PolicyAction`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_coco_parse_defects()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_coco_parser.py → src/datasetgate/core/config.py
- `test_coco_parse_valid_dataset()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_coco_parser.py → src/datasetgate/core/config.py
- `test_default_config_valid()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py

## Import Cycles
- None detected.

## Communities (14 total, 6 thin omitted)

### Community 0 - "DatasetManifest"
Cohesion: 0.11
Nodes (15): DatasetGateConfig, PolicyAction, DatasetManifest, Finding, ImageMetadata, AnnotationValidator, BaseValidator, compute_file_sha256() (+7 more)

### Community 1 - "YoloParser"
Cohesion: 0.18
Nodes (5): YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "core/engine.py"
Cohesion: 0.07
Nodes (13): main(), compare_reports_cli(), ExitCode, calculate_dataset_fingerprint(), parse_dataset(), _render_console_summary(), run_audit(), run_snapshot() (+5 more)

### Community 3 - "models.py"
Cohesion: 0.09
Nodes (18): AuditSnapshot, BoundingBox, DatasetStatistics, FindingCategory, FindingDiff, ImageAnnotation, PolicyCheckResult, PolicyResult (+10 more)

### Community 4 - "load_config"
Cohesion: 0.10
Nodes (14): ConfigError, DatasetConfig, DatasetFormat, generate_default_config_yaml(), load_config(), PolicyConfig, ReportingConfig, test_default_config_valid() (+6 more)

### Community 5 - "test_cli.py"
Cohesion: 0.28
Nodes (3): test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force()

### Community 6 - "audit"
Cohesion: 0.19
Nodes (5): audit(), compare(), init(), snapshot(), version()

### Community 13 - "DatasetGateConfig"
Cohesion: 0.10
Nodes (5): BaseParser, CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset()

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 120 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetManifest` to `YoloParser`, `core/engine.py`, `models.py`, `load_config`, `DatasetGateConfig`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `DatasetGateConfig` (e.g. with `parse_dataset()` and `run_audit()`) actually correct?**
  _`DatasetGateConfig` has 24 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DatasetManifest` be split into smaller, more focused modules?**
  _Cohesion score 0.10884353741496598 - nodes in this community are weakly interconnected._
- **Why does `run_audit()` connect `core/engine.py` to `DatasetManifest`, `models.py`, `DatasetGateConfig`, `audit`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `DatasetManifest` (e.g. with `calculate_dataset_fingerprint()` and `parse_dataset()`) actually correct?**
  _`DatasetManifest` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Should `core/engine.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06568832983927324 - nodes in this community are weakly interconnected._