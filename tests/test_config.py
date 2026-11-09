"""Unit tests for configuration parsing and validation."""

from pathlib import Path

import pytest
import yaml

from datasetgate.core.config import (
    ConfigError,
    DatasetFormat,
    DatasetGateConfig,
    PolicyAction,
    generate_default_config_yaml,
    load_config,
)
from datasetgate.core.models import Severity


def test_default_config_valid():
    cfg = DatasetGateConfig()
    assert cfg.version == 1
    assert cfg.dataset.format == DatasetFormat.AUTO
    assert cfg.policy.require_all_classes_in_train is True
    assert cfg.policy.require_all_classes_in_val is False
    assert cfg.policy.allow_unlabeled_images is True
    assert cfg.policy.max_empty_label_rate == 0.20
    assert cfg.policy.max_class_imbalance_ratio == 25.0
    assert cfg.policy.duplicate_policy == PolicyAction.WARN
    assert cfg.policy.split_leakage_policy == PolicyAction.FAIL
    assert Severity.ERROR in cfg.policy.fail_on


def test_generate_default_config_yaml_is_valid_yaml(tmp_path: Path):
    yaml_text = generate_default_config_yaml()
    assert "version: 1" in yaml_text
    data = yaml.safe_load(yaml_text)
    assert isinstance(data, dict)
    loaded = DatasetGateConfig.model_validate(data)
    assert loaded.version == 1


def test_load_config_from_explicit_file(tmp_path: Path):
    cfg_file = tmp_path / "custom.yaml"
    cfg_file.write_text(
        """
version: 1
dataset:
  format: yolo
policy:
  require_all_classes_in_train: false
  max_empty_label_rate: 0.10
  max_class_imbalance_ratio: 15.0
  duplicate_policy: fail
  fail_on:
    - error
    - warning
""",
        encoding="utf-8",
    )
    loaded = load_config(cfg_file)
    assert loaded.dataset.format == DatasetFormat.YOLO
    assert loaded.policy.require_all_classes_in_train is False
    assert loaded.policy.max_empty_label_rate == 0.10
    assert loaded.policy.duplicate_policy == PolicyAction.FAIL
    assert Severity.ERROR in loaded.policy.fail_on
    assert Severity.WARNING in loaded.policy.fail_on


def test_load_config_nonexistent_file():
    with pytest.raises(ConfigError, match="not found"):
        load_config(Path("non_existent_file.yaml"))


def test_load_config_invalid_yaml(tmp_path: Path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("invalid: [yaml: foo", encoding="utf-8")
    with pytest.raises(ConfigError, match="Failed to parse YAML"):
        load_config(bad_file)


def test_load_config_validation_error(tmp_path: Path):
    invalid_file = tmp_path / "invalid_policy.yaml"
    invalid_file.write_text(
        """
version: 1
policy:
  max_empty_label_rate: 5.5  # must be between 0.0 and 1.0
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="validation error"):
        load_config(invalid_file)


def test_load_config_empty_fail_on(tmp_path: Path):
    invalid_file = tmp_path / "empty_fail_on.yaml"
    invalid_file.write_text(
        """
version: 1
policy:
  fail_on: []
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="at least one severity"):
        load_config(invalid_file)
