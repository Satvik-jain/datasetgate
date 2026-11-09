# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 23 files · ~5,197 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 179 nodes · 374 edges · 13 communities (6 shown, 7 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 55 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e2ac4dcf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- core/__init__.py
- YoloParser
- audit
- config.py
- load_config
- test_cli.py
- DatasetManifest
- AGENTS.md
- GEMINI.md
- README.md
- datasetgate

## God Nodes (most connected - your core abstractions)
1. `YoloParser` - 21 edges
2. `DatasetGateConfig` - 18 edges
3. `audit()` - 16 edges
4. `snapshot()` - 14 edges
5. `load_config()` - 14 edges
6. `Severity` - 13 edges
7. `compare()` - 12 edges
8. `ExitCode` - 12 edges
9. `ConfigError` - 11 edges
10. `Finding` - 11 edges

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

## Communities (13 total, 7 thin omitted)

### Community 0 - "core/__init__.py"
Cohesion: 0.09
Nodes (14): AuditSnapshot, BoundingBox, ComparisonResult, DatasetStatistics, Finding, FindingCategory, FindingDiff, ImageAnnotation (+6 more)

### Community 1 - "YoloParser"
Cohesion: 0.18
Nodes (5): YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "audit"
Cohesion: 0.10
Nodes (9): audit(), compare(), init(), main(), snapshot(), version(), compare_reports_cli(), generate_default_config_yaml() (+1 more)

### Community 3 - "config.py"
Cohesion: 0.13
Nodes (6): DatasetConfig, DatasetGateConfig, PolicyConfig, ReportingConfig, run_audit(), run_snapshot()

### Community 4 - "load_config"
Cohesion: 0.17
Nodes (11): ConfigError, DatasetFormat, load_config(), PolicyAction, test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on(), test_load_config_from_explicit_file() (+3 more)

### Community 5 - "test_cli.py"
Cohesion: 0.28
Nodes (3): test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force()

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 79 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `config.py` to `core/__init__.py`, `YoloParser`, `load_config`, `DatasetManifest`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `YoloParser` (e.g. with `DatasetGateConfig` and `BoundingBox`) actually correct?**
  _`YoloParser` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `core/__init__.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09059233449477352 - nodes in this community are weakly interconnected._
- **Why does `YoloParser` connect `YoloParser` to `core/__init__.py`, `config.py`, `DatasetManifest`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `DatasetGateConfig` (e.g. with `run_audit()` and `run_snapshot()`) actually correct?**
  _`DatasetGateConfig` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `audit` be split into smaller, more focused modules?**
  _Cohesion score 0.09957325746799431 - nodes in this community are weakly interconnected._