# Graph Report - datasetgate  (2026-11-10)

## Corpus Check
- 31 files · ~8,423 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 243 nodes · 609 edges · 14 communities (7 shown, 7 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 114 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c3c9e29f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models.py
- YoloParser
- audit
- ImageMetadata
- load_config
- test_cli.py
- DatasetManifest
- AGENTS.md
- GEMINI.md
- README.md
- datasetgate
- DatasetGateConfig

## God Nodes (most connected - your core abstractions)
1. `DatasetGateConfig` - 41 edges
2. `DatasetManifest` - 30 edges
3. `Finding` - 26 edges
4. `Severity` - 22 edges
5. `CocoParser` - 21 edges
6. `YoloParser` - 21 edges
7. `audit()` - 16 edges
8. `FindingCategory` - 16 edges
9. `ImageMetadata` - 16 edges
10. `snapshot()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `test_default_config_valid()` --uses--> `PolicyAction`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_load_config_from_explicit_file()` --uses--> `PolicyAction`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_default_config_valid()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_generate_default_config_yaml_is_valid_yaml()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_config.py → src/datasetgate/core/config.py
- `test_annotation_validator_unlabeled_policy()` --uses--> `DatasetGateConfig`  [INFERRED]
  tests/test_validators.py → src/datasetgate/core/config.py

## Import Cycles
- None detected.

## Communities (14 total, 7 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.08
Nodes (17): AuditSnapshot, ComparisonResult, DatasetManifest, DatasetStatistics, Finding, FindingCategory, FindingDiff, ImageAnnotation (+9 more)

### Community 1 - "YoloParser"
Cohesion: 0.18
Nodes (5): YoloParser, test_yolo_can_parse_with_dirs(), test_yolo_can_parse_with_yaml(), test_yolo_parse_defect_annotations(), test_yolo_parse_valid_dataset()

### Community 2 - "audit"
Cohesion: 0.09
Nodes (11): audit(), compare(), init(), main(), snapshot(), version(), compare_reports_cli(), generate_default_config_yaml() (+3 more)

### Community 3 - "ImageMetadata"
Cohesion: 0.17
Nodes (8): PolicyAction, ImageMetadata, compute_file_sha256(), DuplicateValidator, create_sample_png_bytes(), test_duplicate_validator_cross_split_leakage(), test_duplicate_validator_intra_split(), test_image_integrity_validator()

### Community 4 - "load_config"
Cohesion: 0.10
Nodes (13): ConfigError, DatasetConfig, DatasetFormat, load_config(), PolicyConfig, ReportingConfig, test_default_config_valid(), test_generate_default_config_yaml_is_valid_yaml() (+5 more)

### Community 5 - "test_cli.py"
Cohesion: 0.28
Nodes (3): test_cli_init_creates_file(), test_cli_init_existing_with_force(), test_cli_init_existing_without_force()

### Community 13 - "DatasetGateConfig"
Cohesion: 0.16
Nodes (6): DatasetGateConfig, BoundingBox, CocoParser, test_coco_can_parse(), test_coco_parse_defects(), test_coco_parse_valid_dataset()

## Knowledge Gaps
- **1 isolated node(s):** `datasetgate`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 102 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatasetGateConfig` connect `DatasetGateConfig` to `models.py`, `YoloParser`, `audit`, `ImageMetadata`, `load_config`, `DatasetManifest`?**
  _High betweenness centrality (0.236) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `DatasetGateConfig` (e.g. with `run_audit()` and `run_snapshot()`) actually correct?**
  _`DatasetGateConfig` has 19 INFERRED edges - model-reasoned connections that need verification._
- **What connects `datasetgate` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `models.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08045977011494253 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `audit`, `DatasetGateConfig`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `DatasetManifest` (e.g. with `BaseParser` and `CocoParser`) actually correct?**
  _`DatasetManifest` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `audit` be split into smaller, more focused modules?**
  _Cohesion score 0.08585858585858586 - nodes in this community are weakly interconnected._