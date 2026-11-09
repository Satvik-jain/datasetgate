"""Integration tests for synthetic dataset generator and demo CLI command."""

from pathlib import Path

from typer.testing import CliRunner

from datasetgate.cli.main import app
from datasetgate.core.constants import ExitCode
from datasetgate.synthetic.generator import (
    generate_synthetic_coco_dataset,
    generate_synthetic_yolo_dataset,
)

runner = CliRunner()


def test_generate_synthetic_yolo_dataset(tmp_path: Path):
    out = tmp_path / "yolo_demo"
    res = generate_synthetic_yolo_dataset(out)
    assert res.exists()
    assert (res / "data.yaml").is_file()
    assert (res / "images" / "train").is_dir()
    assert (res / "images" / "val").is_dir()
    assert (res / "labels" / "train").is_dir()
    assert (res / "labels" / "val").is_dir()
    # Check that leaked file exists in both train and val
    assert (res / "images" / "train" / "train_leaked.jpg").is_file()
    assert (res / "images" / "val" / "val_leaked.jpg").is_file()


def test_generate_synthetic_coco_dataset(tmp_path: Path):
    out = tmp_path / "coco_demo"
    res = generate_synthetic_coco_dataset(out)
    assert res.exists()
    assert (res / "annotations" / "instances_train.json").is_file()
    assert (res / "images" / "img_001.jpg").is_file()


def test_cli_demo_command_yolo(tmp_path: Path):
    target = tmp_path / "demo_run"
    # Run demo with audit=False to check creation
    result = runner.invoke(app, ["demo", "--output-dir", str(target), "--no-audit"])
    assert result.exit_code == 0
    assert "Created synthetic YOLO demo dataset" in result.stdout
    assert (target / "data.yaml").exists()


def test_cli_demo_command_audit(tmp_path: Path):
    target = tmp_path / "demo_audit_run"
    # Running demo with audit=True runs the audit and fails the gate (ExitCode.GATE_FAILED)
    # because the demo deliberately contains defects (split leakage, corrupted image, out of bounds)!
    result = runner.invoke(app, ["demo", "--output-dir", str(target), "--audit"])
    assert result.exit_code == ExitCode.GATE_FAILED
    assert "DatasetGate Audit:" in result.stdout
    assert "QUALITY GATE FAILED" in result.stdout
    assert (target / "reports" / "report.json").exists()
    assert (target / "reports" / "report.html").exists()
