"""Unit tests for DatasetGate CLI commands."""

from pathlib import Path

from typer.testing import CliRunner

from datasetgate.cli.main import app
from datasetgate.core.constants import ExitCode

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "DatasetGate version" in result.stdout


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "DatasetGate" in result.stdout
    assert "init" in result.stdout
    assert "audit" in result.stdout
    assert "snapshot" in result.stdout
    assert "compare" in result.stdout


def test_cli_init_creates_file(tmp_path: Path):
    target_config = tmp_path / "datasetgate.yaml"
    result = runner.invoke(app, ["init", "--path", str(target_config)])
    assert result.exit_code == 0
    assert target_config.exists()
    content = target_config.read_text(encoding="utf-8")
    assert "version: 1" in content
    assert "policy:" in content


def test_cli_init_existing_without_force(tmp_path: Path):
    target_config = tmp_path / "datasetgate.yaml"
    target_config.write_text("existing content", encoding="utf-8")
    result = runner.invoke(app, ["init", "--path", str(target_config)])
    assert result.exit_code == ExitCode.INVALID_USAGE
    assert "already exists" in result.output


def test_cli_init_existing_with_force(tmp_path: Path):
    target_config = tmp_path / "datasetgate.yaml"
    target_config.write_text("existing content", encoding="utf-8")
    result = runner.invoke(app, ["init", "--path", str(target_config), "--force"])
    assert result.exit_code == 0
    assert "version: 1" in target_config.read_text(encoding="utf-8")
