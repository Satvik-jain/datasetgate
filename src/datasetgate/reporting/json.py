"""JSON report generation."""

from __future__ import annotations

from pathlib import Path

from datasetgate.core.models import AuditSnapshot


def generate_json_report(snapshot: AuditSnapshot, output_path: Path) -> Path:
    """Serialize AuditSnapshot to a formatted, deterministic JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_str = snapshot.model_dump_json(indent=2)
    output_path.write_text(json_str, encoding="utf-8")
    return output_path
