# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 35 files · ~9,709 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 259 nodes · 684 edges · 13 communities (6 shown, 7 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 145 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4332ac62`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DatasetManifest
- YoloParser
- audit
- models.py
- load_config
- DatasetManifest
- AGENTS.md
- GEMINI.md
- README.md
- datasetgate
- DatasetGateConfig

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 46 edges
2. `DatasetManifest` - 38 edges
3. `Finding` - 32 edges
4. `Severity` - 25 edges
5. `CocoParser` - 21 edges
6. `YoloParser` - 21 edges
7. `FindingCategory` - 19 edges
8. `ImageMetadata` - 19 edges
9. `audit()` - 16 edges
10. `snapshot()` - 14 edges

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

## Communities (13 total, 7 thin omitted)

### Community 0 - "DatasetManifest"
Cohesion: 0.10
Nodes (15): DatasetGateConfig, PolicyAction, DatasetManifest, Finding, ImageMetadata, AnnotationValidator, BaseValidator, compute_file_sha256() (+7 more)

### Community 1 - "YoloParser"
Cohesion: 0.18
Nodes (5): YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "audit"
Cohesion: 0.07
Nodes (14): audit(), compare(), init(), main(), snapshot(), version(), compare_reports_cli(), generate_default_config_yaml() (+6 more)

### Community 3 - "models.py"
Cohesion: 0.07
Nodes (19): DatasetConfig, PolicyConfig, ReportingConfig, AuditSnapshot, ComparisonResult, DatasetStatistics, FindingCategory, FindingDiff (+11 more)

### Community 4 - "load_config"
Cohesion: 0.19
Nodes (10): ConfigError, DatasetFormat, load_config(), test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml(), test_load_config_empty_fail_on(), test_load_config_from_explicit_file(), test_load_config_invalid_yaml() (+2 more)

### Community 13 - "DatasetGateConfig"
Cohesion: 0.16
Nodes (5): BoundingBox, CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset()

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 107 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetManifest` to `YoloParser`, `audit`, `models.py`, `load_config`, `DatasetManifest`, `DatasetGateConfig`?**
  _High betweenness centrality (0.240) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `DatasetGateConfig` (e.g. with `run_audit()` and `run_snapshot()`) actually correct?**
  _`DatasetGateConfig` has 22 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DatasetManifest` be split into smaller, more focused modules?**
  _Cohesion score 0.10352941176470588 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `DatasetManifest`, `audit`, `models.py`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `DatasetManifest` (e.g. with `BaseParser` and `CocoParser`) actually correct?**
  _`DatasetManifest` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Should `audit` be split into smaller, more focused modules?**
  _Cohesion score 0.06848357791754019 - nodes in this community are weakly interconnected._