"""Configurable dataset quality policy evaluation engine."""

from __future__ import annotations

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.models import (
    DatasetManifest,
    DatasetStatistics,
    Finding,
    FindingCategory,
    PolicyCheckResult,
    PolicyResult,
    Severity,
)


class PolicyEngine:
    """Evaluates dataset statistics and defect findings against configured quality policies."""

    def evaluate(
        self,
        manifest: DatasetManifest,
        stats: DatasetStatistics,
        findings: list[Finding],
        config: DatasetGateConfig,
    ) -> tuple[list[Finding], PolicyResult]:
        policy = config.policy
        all_findings = [f.model_copy() for f in findings]

        check_results: list[PolicyCheckResult] = []
        passed_checks: list[str] = []
        warnings_list: list[str] = []
        errors_list: list[str] = []
        skipped_checks: list[str] = []

        # 1. Apply user rule severity overrides
        if policy.rule_severities:
            for f in all_findings:
                if f.rule_id in policy.rule_severities:
                    f.severity = policy.rule_severities[f.rule_id]

        # 2. Check: require_all_classes_in_train
        if policy.require_all_classes_in_train:
            train_splits = [s for s in manifest.splits if s in ("train", "default")]
            if train_splits:
                missing = stats.missing_classes_per_split.get(
                    "train"
                ) or stats.missing_classes_per_split.get("default")
                if missing:
                    msg = f"Train split is missing annotations for {len(missing)} declared class(es): {', '.join(missing)}."
                    all_findings.append(
                        Finding(
                            rule_id="MISSING_CLASS_IN_TRAIN",
                            severity=Severity.ERROR,
                            category=FindingCategory.DISTRIBUTION,
                            message=msg,
                            split="train",
                            metadata={"missing_classes": missing},
                        )
                    )
                    check_results.append(
                        PolicyCheckResult(
                            name="require_all_classes_in_train",
                            passed=False,
                            status="ERROR",
                            message=msg,
                        )
                    )
                else:
                    passed_checks.append("require_all_classes_in_train")
                    check_results.append(
                        PolicyCheckResult(
                            name="require_all_classes_in_train",
                            passed=True,
                            status="PASSED",
                            message="All declared classes have annotations in train split.",
                        )
                    )
            else:
                skipped_checks.append("require_all_classes_in_train (no train split declared)")
        else:
            skipped_checks.append("require_all_classes_in_train (disabled by policy)")

        # 3. Check: require_all_classes_in_val
        if policy.require_all_classes_in_val:
            val_splits = [s for s in manifest.splits if s in ("val", "valid")]
            if val_splits:
                val_key = val_splits[0]
                missing = stats.missing_classes_per_split.get(val_key, [])
                if missing:
                    msg = f"Validation split '{val_key}' is missing annotations for {len(missing)} class(es): {', '.join(missing)}."
                    all_findings.append(
                        Finding(
                            rule_id="MISSING_CLASS_IN_VAL",
                            severity=Severity.ERROR,
                            category=FindingCategory.DISTRIBUTION,
                            message=msg,
                            split=val_key,
                            metadata={"missing_classes": missing},
                        )
                    )
                    check_results.append(
                        PolicyCheckResult(
                            name="require_all_classes_in_val",
                            passed=False,
                            status="ERROR",
                            message=msg,
                        )
                    )
                else:
                    passed_checks.append("require_all_classes_in_val")
                    check_results.append(
                        PolicyCheckResult(
                            name="require_all_classes_in_val",
                            passed=True,
                            status="PASSED",
                            message="All declared classes have annotations in val split.",
                        )
                    )
            else:
                skipped_checks.append("require_all_classes_in_val (no val split declared)")
        else:
            skipped_checks.append("require_all_classes_in_val (disabled by policy)")

        # 4. Check: max_empty_label_rate
        if stats.empty_label_rate > policy.max_empty_label_rate:
            msg = (
                f"Empty label rate {stats.empty_label_rate * 100:.1f}% exceeds maximum allowed "
                f"{policy.max_empty_label_rate * 100:.1f}%."
            )
            all_findings.append(
                Finding(
                    rule_id="EXCESSIVE_EMPTY_LABELS",
                    severity=Severity.ERROR,
                    category=FindingCategory.DISTRIBUTION,
                    message=msg,
                    metadata={
                        "rate": stats.empty_label_rate,
                        "max_allowed": policy.max_empty_label_rate,
                    },
                )
            )
            check_results.append(
                PolicyCheckResult(
                    name="max_empty_label_rate", passed=False, status="ERROR", message=msg
                )
            )
        else:
            passed_checks.append("max_empty_label_rate")
            check_results.append(
                PolicyCheckResult(
                    name="max_empty_label_rate",
                    passed=True,
                    status="PASSED",
                    message=f"Empty label rate {stats.empty_label_rate * 100:.1f}% is within threshold ({policy.max_empty_label_rate * 100:.1f}%).",
                )
            )

        # 5. Check: max_class_imbalance_ratio
        if policy.max_class_imbalance_ratio is not None and len(stats.instances_per_class) > 1:
            if stats.class_imbalance_ratio > policy.max_class_imbalance_ratio:
                msg = (
                    f"Class imbalance ratio {stats.class_imbalance_ratio:.1f} exceeds threshold "
                    f"{policy.max_class_imbalance_ratio:.1f}."
                )
                all_findings.append(
                    Finding(
                        rule_id="EXCESSIVE_CLASS_IMBALANCE",
                        severity=Severity.WARNING,
                        category=FindingCategory.DISTRIBUTION,
                        message=msg,
                        metadata={
                            "ratio": stats.class_imbalance_ratio,
                            "max_allowed": policy.max_class_imbalance_ratio,
                            "counts": stats.instances_per_class,
                        },
                    )
                )
                check_results.append(
                    PolicyCheckResult(
                        name="max_class_imbalance_ratio",
                        passed=False,
                        status="WARNING",
                        message=msg,
                    )
                )
            else:
                passed_checks.append("max_class_imbalance_ratio")
                check_results.append(
                    PolicyCheckResult(
                        name="max_class_imbalance_ratio",
                        passed=True,
                        status="PASSED",
                        message=f"Class imbalance ratio {stats.class_imbalance_ratio:.1f} is within threshold ({policy.max_class_imbalance_ratio:.1f}).",
                    )
                )
        else:
            skipped_checks.append("max_class_imbalance_ratio (not evaluated)")

        # 6. Check duplicates & split leakage
        has_leakage = any(f.rule_id == "SPLIT_LEAKAGE" for f in all_findings)
        if not has_leakage and len(manifest.splits) > 1:
            passed_checks.append("split_leakage_free")
            check_results.append(
                PolicyCheckResult(
                    name="split_leakage_free",
                    passed=True,
                    status="PASSED",
                    message="No cross-split image leakage detected.",
                )
            )

        has_corrupt = any(f.rule_id == "CORRUPTED_IMAGE" for f in all_findings)
        if not has_corrupt and len(manifest.images) > 0:
            passed_checks.append("images_decodable")
            check_results.append(
                PolicyCheckResult(
                    name="images_decodable",
                    passed=True,
                    status="PASSED",
                    message="All image files are readable and valid.",
                )
            )

        has_oob = any(f.rule_id == "BBOX_OUT_OF_BOUNDS" for f in all_findings)
        if not has_oob and stats.total_annotations > 0:
            passed_checks.append("bounding_boxes_within_bounds")
            check_results.append(
                PolicyCheckResult(
                    name="bounding_boxes_within_bounds",
                    passed=True,
                    status="PASSED",
                    message="All bounding boxes fall within image boundaries.",
                )
            )

        # 7. Overall gate determination based on fail_on criteria
        fail_severities = set(policy.fail_on)
        failing_findings = [f for f in all_findings if f.severity in fail_severities]

        for f in all_findings:
            if f.severity == Severity.ERROR:
                errors_list.append(f"{f.rule_id}: {f.message}")
            elif f.severity == Severity.WARNING:
                warnings_list.append(f"{f.rule_id}: {f.message}")

        gate_passed = len(failing_findings) == 0
        overall_status = "PASSED" if gate_passed else "FAILED"

        policy_result = PolicyResult(
            passed=gate_passed,
            status=overall_status,
            passed_checks=passed_checks,
            warnings=warnings_list,
            errors=errors_list,
            skipped_checks=skipped_checks,
            check_results=check_results,
        )

        return all_findings, policy_result
