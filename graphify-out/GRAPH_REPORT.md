# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 25 files · ~7,047 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 203 nodes · 458 edges · 14 communities (7 shown, 7 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 71 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fc2fe476`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models.py
- YoloParser
- audit
- PolicyConfig
- load_config
- test_cli.py
- DatasetManifest
- AGENTS.md
- GEMINI.md
- README.md
- datasetgate
- DatasetGateConfig

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 25 edges
2. `CocoParser` - 21 edges
3. `YoloParser` - 21 edges
4. `audit()` - 16 edges
5. `Severity` - 15 edges
6. `snapshot()` - 14 edges
7. `load_config()` - 14 edges
8. `Finding` - 14 edges
9. `DatasetManifest` - 14 edges
10. `compare()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `test_default_config_valid()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_generate_default_config_yaml_is_valid_yaml()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_yolo_parse_defect_annotations()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_yolo_parser.py → src/datasetgate/core/config.py
- `test_yolo_parse_valid_dataset()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_yolo_parser.py → src/datasetgate/core/config.py
- `test_cli_init_existing_without_force()` --uses--> `ExitCode`  [INFERRED]
  tests/test_cli.py → src/datasetgate/core/constants.py

## Import Cycles
- None detected.

## Communities (14 total, 7 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.10
Nodes (14): AuditSnapshot, BoundingBox, ComparisonResult, DatasetStatistics, Finding, FindingCategory, FindingDiff, ImageAnnotation (+6 more)

### Community 1 - "YoloParser"
Cohesion: 0.18
Nodes (5): YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "audit"
Cohesion: 0.09
Nodes (10): audit(), compare(), init(), main(), snapshot(), version(), compare_reports_cli(), ExitCode (+2 more)

### Community 3 - "PolicyConfig"
Cohesion: 0.22
Nodes (3): DatasetConfig, PolicyConfig, ReportingConfig

### Community 4 - "load_config"
Cohesion: 0.14
Nodes (12): ConfigError, DatasetFormat, generate_default_config_yaml(), load_config(), PolicyAction, test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on() (+4 more)

### Community 5 - "test_cli.py"
Cohesion: 0.28
Nodes (3): test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force()

### Community 13 - "DatasetGateConfig"
Cohesion: 0.17
Nodes (5): DatasetGateConfig, CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset()

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 87 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetGateConfig` to `models.py`, `YoloParser`, `audit`, `PolicyConfig`, `load_config`, `DatasetManifest`?**
  _High betweenness centrality (0.206) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `DatasetGateConfig` (e.g. with `run_audit()` and `run_snapshot()`) actually correct?**
  _`DatasetGateConfig` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `models.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09988385598141696 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `audit`, `DatasetGateConfig`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `CocoParser` (e.g. with `DatasetGateConfig` and `BoundingBox`) actually correct?**
  _`CocoParser` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `audit` be split into smaller, more focused modules?**
  _Cohesion score 0.08985200845665962 - nodes in this community are weakly interconnected._