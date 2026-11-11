"""Configuration models and loading for DatasetGate."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from datasetgate.core.models import Severity


class DatasetFormat(StrEnum):
    """Supported dataset formats."""

    AUTO = "auto"
    YOLO = "yolo"
    COCO = "coco"


class PolicyAction(StrEnum):
    """Action to take on specific policy violations."""

    IGNORE = "ignore"
    WARN = "warn"
    FAIL = "fail"


class DatasetConfig(BaseModel):
    """Dataset ingestion settings."""

    format: DatasetFormat = Field(
        default=DatasetFormat.AUTO,
        description="Dataset format to parse ('auto', 'yolo', 'coco')",
    )
    image_extensions: list[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"],
        description="Supported image file extensions (lowercase)",
    )
    yolo_data_yaml: str | None = Field(
        default=None,
        description="Optional explicit path to YOLO data.yaml",
    )
    coco_annotation_files: dict[str, str] = Field(
        default_factory=dict,
        description="Optional mapping of split name to COCO json annotation file path",
    )


class PerceptualHashConfig(BaseModel):
    """Perceptual near-duplicate and cross-split leakage detection settings."""

    enabled: bool = Field(
        default=False,
        description="Enable perceptual near-duplicate and leakage detection (pHash)",
    )
    max_hamming_distance: int = Field(
        default=6,
        ge=0,
        le=63,
        description="Maximum Hamming distance threshold for candidate near-duplicates (0 to 63)",
    )
    duplicate_policy: PolicyAction = Field(
        default=PolicyAction.WARN,
        description="Action on approximate duplicate images within a split ('ignore', 'warn', 'fail')",
    )
    split_leakage_policy: PolicyAction = Field(
        default=PolicyAction.WARN,
        description="Action on approximate duplicate images leaked across splits ('ignore', 'warn', 'fail')",
    )
    max_candidate_pairs: int = Field(
        default=10000,
        gt=0,
        description="Maximum candidate pairs to evaluate before truncating analysis (must be positive)",
    )
    truncation_action: PolicyAction = Field(
        default=PolicyAction.FAIL,
        description="Action when candidate pair limit is exceeded ('warn', 'fail')",
    )

    @field_validator("truncation_action")
    @classmethod
    def validate_truncation_action(cls, v: PolicyAction) -> PolicyAction:
        if v == PolicyAction.IGNORE:
            raise ValueError(
                "truncation_action cannot be 'ignore'; truncated analysis must be flagged as 'warn' or 'fail'"
            )
        return v


class PolicyConfig(BaseModel):
    """Configurable quality policy rules and thresholds."""

    require_all_classes_in_train: bool = Field(
        default=True,
        description="Fail if any declared class has 0 annotations in the train split",
    )
    require_all_classes_in_val: bool = Field(
        default=False,
        description="Fail if any declared class has 0 annotations in the val split",
    )
    allow_unlabeled_images: bool = Field(
        default=True,
        description="Whether images without annotations (empty or missing labels) are allowed",
    )
    max_empty_label_rate: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Maximum allowed fraction of unlabeled images across the dataset (0.0 to 1.0)",
    )
    max_class_imbalance_ratio: float | None = Field(
        default=25.0,
        gt=0.0,
        description="Maximum allowed ratio between most and least frequent class counts (None disables)",
    )
    duplicate_policy: PolicyAction = Field(
        default=PolicyAction.WARN,
        description="Action on exact duplicate images within a split ('ignore', 'warn', 'fail')",
    )
    split_leakage_policy: PolicyAction = Field(
        default=PolicyAction.FAIL,
        description="Action when identical images appear across train/val/test splits ('ignore', 'warn', 'fail')",
    )
    corrupted_image_policy: PolicyAction = Field(
        default=PolicyAction.FAIL,
        description="Action when unreadable or corrupted images are detected ('ignore', 'warn', 'fail')",
    )
    missing_image_policy: PolicyAction = Field(
        default=PolicyAction.FAIL,
        description="Action when referenced images do not exist on disk ('ignore', 'warn', 'fail')",
    )
    out_of_bounds_policy: PolicyAction = Field(
        default=PolicyAction.FAIL,
        description="Action on bounding boxes that extend outside image bounds ('ignore', 'warn', 'fail')",
    )
    perceptual_hash: PerceptualHashConfig = Field(
        default_factory=PerceptualHashConfig,
        description="Perceptual near-duplicate and leakage detection settings",
    )
    rule_severities: dict[str, Severity] = Field(
        default_factory=dict,
        description="Custom severity overrides per rule ID (e.g. {'BBOX_OUT_OF_BOUNDS': 'warning'})",
    )
    fail_on: list[Severity] = Field(
        default_factory=lambda: [Severity.ERROR],
        description="Finding severities that cause overall quality gate failure",
    )

    @field_validator("fail_on")
    @classmethod
    def validate_fail_on(cls, v: list[Severity]) -> list[Severity]:
        if not v:
            raise ValueError("fail_on list must contain at least one severity (e.g. ['error'])")
        return v


class ReportingConfig(BaseModel):
    """Output and reporting settings."""

    output_dir: str = Field(default="reports", description="Default report output directory")
    generate_html: bool = Field(default=True, description="Whether to generate HTML report")
    generate_json: bool = Field(default=True, description="Whether to generate JSON report")


class DatasetGateConfig(BaseModel):
    """Top-level configuration schema for DatasetGate."""

    version: int = Field(default=1, description="Configuration schema version")
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


class ConfigError(Exception):
    """Raised when configuration file cannot be found or parsed."""

    pass


def load_config(config_path: Path | str | None = None) -> DatasetGateConfig:
    """Load and validate DatasetGate configuration from file or default.

    If config_path is None, attempts to find 'datasetgate.yaml' or 'datasetgate.yml'
    in current directory. If neither exists, returns default configuration.
    """
    if config_path is None:
        for candidate in [Path("datasetgate.yaml"), Path("datasetgate.yml")]:
            if candidate.is_file():
                config_path = candidate
                break

    if config_path is None:
        return DatasetGateConfig()

    path = Path(config_path)
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML in {path}: {e}") from e
    except Exception as e:
        raise ConfigError(f"Could not read configuration file {path}: {e}") from e

    if not isinstance(raw_data, dict):
        raise ConfigError(
            f"Invalid configuration in {path}: expected YAML mapping, got {type(raw_data).__name__}"
        )

    try:
        return DatasetGateConfig.model_validate(raw_data)
    except Exception as e:
        raise ConfigError(f"Configuration validation error in {path}:\n{e}") from e


def generate_default_config_yaml() -> str:
    """Generate documented default YAML configuration content."""
    return """# DatasetGate Configuration File
# https://github.com/Satvik-jain/datasetgate
version: 1

dataset:
  # Ingestion format: 'auto', 'yolo', or 'coco'
  format: auto

  # Supported image extensions
  image_extensions:
    - .jpg
    - .jpeg
    - .png
    - .bmp
    - .webp
    - .tif
    - .tiff

policy:
  # Split coverage rules
  require_all_classes_in_train: true
  require_all_classes_in_val: false

  # Label distribution rules
  allow_unlabeled_images: true
  max_empty_label_rate: 0.20
  max_class_imbalance_ratio: 25.0

  # Leakage and duplicates: 'ignore', 'warn', 'fail'
  duplicate_policy: warn
  split_leakage_policy: fail

  # Perceptual near-duplicate detection (pHash)
  perceptual_hash:
    enabled: false
    max_hamming_distance: 6
    duplicate_policy: warn
    split_leakage_policy: warn
    max_candidate_pairs: 10000
    truncation_action: fail

  # Integrity policies: 'ignore', 'warn', 'fail'
  corrupted_image_policy: fail
  missing_image_policy: fail
  out_of_bounds_policy: fail

  # Overall gate failure trigger
  fail_on:
    - error

  # Optional rule severity overrides:
  # rule_severities:
  #   BBOX_OUT_OF_BOUNDS: warning

reporting:
  output_dir: reports
  generate_html: true
  generate_json: true
"""
