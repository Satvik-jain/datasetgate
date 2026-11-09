"""Unit tests for JSON and HTML reporting."""

import json
from pathlib import Path

from PIL import Image

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.engine import run_audit
from datasetgate.core.models import (
    AuditSnapshot,
    DatasetStatistics,
    Finding,
    FindingCategory,
    PolicyResult,
    Severity,
)
from datasetgate.reporting.html import generate_html_report
from datasetgate.reporting.json import generate_json_report


def test_generate_json_report(tmp_path: Path):
    snapshot = AuditSnapshot(
        dataset_fingerprint="1234567890abcdef",
        format="yolo",
        dataset_name="test_ds",
        statistics=DatasetStatistics(total_images=5, total_annotations=10),
        findings=[
            Finding(
                rule_id="BBOX_OUT_OF_BOUNDS",
                severity=Severity.ERROR,
                category=FindingCategory.ANNOTATION_INTEGRITY,
                message="Box outside bounds",
            )
        ],
        policy_result=PolicyResult(passed=False, status="FAILED", errors=["Error"]),
    )

    out_file = tmp_path / "reports" / "report.json"
    res = generate_json_report(snapshot, out_file)
    assert res.exists()
    content = json.loads(res.read_text(encoding="utf-8"))
    assert content["dataset_fingerprint"] == "1234567890abcdef"
    assert len(content["findings"]) == 1


def test_generate_html_report(tmp_path: Path):
    snapshot = AuditSnapshot(
        dataset_fingerprint="1234567890abcdef",
        format="coco",
        dataset_name="coco_sample",
        statistics=DatasetStatistics(
            total_images=10,
            total_annotations=20,
            images_per_split={"train": 8, "val": 2},
            annotations_per_split={"train": 15, "val": 5},
            instances_per_class={"car": 12, "person": 8},
            class_imbalance_ratio=1.5,
        ),
        findings=[
            Finding(
                rule_id="SPLIT_LEAKAGE",
                severity=Severity.ERROR,
                category=FindingCategory.DUPLICATES_AND_LEAKAGE,
                message="Leakage detected",
                file_path="train/img1.jpg",
                related_paths=["val/img1_dup.jpg"],
            )
        ],
        policy_result=PolicyResult(
            passed=False,
            status="FAILED",
            errors=["SPLIT_LEAKAGE: Leakage detected"],
            passed_checks=["images_decodable"],
        ),
    )

    out_html = tmp_path / "report.html"
    res = generate_html_report(snapshot, out_html)
    assert res.exists()
    html_text = res.read_text(encoding="utf-8")

    assert "<!DOCTYPE html>" in html_text
    assert "coco_sample" in html_text
    assert "1234567890abcdef" in html_text
    assert "SPLIT_LEAKAGE" in html_text
    assert "FAILED" in html_text
    assert "Fix Cross-Split Leakage" in html_text


def test_run_audit_end_to_end(tmp_path: Path):
    # Setup miniature YOLO dataset
    img_dir = tmp_path / "images" / "train"
    lbl_dir = tmp_path / "labels" / "train"
    img_dir.mkdir(parents=True)
    lbl_dir.mkdir(parents=True)

    img = Image.new("RGB", (64, 64), color="blue")
    img.save(img_dir / "sample.png")
    (lbl_dir / "sample.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    yaml_file = tmp_path / "data.yaml"
    yaml_file.write_text("train: images/train\nnames: ['object']\nnc: 1\n", encoding="utf-8")

    report_dir = tmp_path / "out_reports"
    config = DatasetGateConfig()

    exit_code = run_audit(
        dataset_path=tmp_path,
        config=config,
        output_dir=report_dir,
        quiet=True,
    )

    assert exit_code == 0
    assert (report_dir / "report.json").exists()
    assert (report_dir / "report.html").exists()


def test_run_audit_policy_actions_exit_codes(tmp_path: Path):
    # Setup miniature YOLO dataset with deliberate out-of-bounds bbox
    img_dir = tmp_path / "images" / "train"
    lbl_dir = tmp_path / "labels" / "train"
    img_dir.mkdir(parents=True)
    lbl_dir.mkdir(parents=True)

    img = Image.new("RGB", (64, 64), color="red")
    img.save(img_dir / "oob.png")
    # center 0.9, width 0.4 -> extends to 1.1 (out of bounds)
    (lbl_dir / "oob.txt").write_text("0 0.9 0.5 0.4 0.2\n", encoding="utf-8")

    yaml_file = tmp_path / "data.yaml"
    yaml_file.write_text("train: images/train\nnames: ['object']\nnc: 1\n", encoding="utf-8")

    # 1. Action = fail -> ExitCode.GATE_FAILED (1)
    cfg_fail = DatasetGateConfig()
    cfg_fail.policy.out_of_bounds_policy = "fail"
    cfg_fail.policy.fail_on = ["error"]
    res_fail = run_audit(
        dataset_path=tmp_path, config=cfg_fail, output_dir=tmp_path / "rep_fail", quiet=True
    )
    assert res_fail == 1

    # 2. Action = warn -> ExitCode.SUCCESS (0) because fail_on is only ['error']
    cfg_warn = DatasetGateConfig()
    cfg_warn.policy.out_of_bounds_policy = "warn"
    cfg_warn.policy.fail_on = ["error"]
    res_warn = run_audit(
        dataset_path=tmp_path, config=cfg_warn, output_dir=tmp_path / "rep_warn", quiet=True
    )
    assert res_warn == 0

    # 3. Action = ignore -> ExitCode.SUCCESS (0) and no finding in report
    cfg_ignore = DatasetGateConfig()
    cfg_ignore.policy.out_of_bounds_policy = "ignore"
    cfg_ignore.policy.fail_on = ["error"]
    res_ignore = run_audit(
        dataset_path=tmp_path, config=cfg_ignore, output_dir=tmp_path / "rep_ignore", quiet=True
    )
    assert res_ignore == 0
    rep_data = json.loads((tmp_path / "rep_ignore" / "report.json").read_text(encoding="utf-8"))
    assert not any(f["rule_id"] == "BBOX_OUT_OF_BOUNDS" for f in rep_data["findings"])
