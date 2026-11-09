"""Self-contained, responsive HTML report generator."""

from __future__ import annotations

import datetime
from pathlib import Path

from jinja2 import Environment

from datasetgate.core.models import AuditSnapshot, ComparisonResult

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DatasetGate Audit Report — {{ snapshot.dataset_name }}</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --text: #c9d1d9;
      --text-muted: #8b949e;
      --text-bright: #f0f6fc;
      --primary: #58a6ff;
      --success: #238636;
      --success-bg: rgba(46, 160, 67, 0.15);
      --danger: #da3633;
      --danger-bg: rgba(248, 81, 73, 0.15);
      --warning: #d29922;
      --warning-bg: rgba(210, 153, 34, 0.15);
      --info: #388bfd;
      --info-bg: rgba(56, 139, 253, 0.15);
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      font-size: 14px;
      line-height: 1.5;
      padding: 24px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand h1 { font-size: 20px; color: var(--text-bright); font-weight: 600; letter-spacing: -0.5px; }
    .brand .tagline { font-size: 12px; color: var(--text-muted); }
    .meta-badge { font-family: var(--mono); font-size: 11px; color: var(--text-muted); background: var(--card-bg); padding: 4px 10px; border-radius: 6px; border: 1px solid var(--card-border); }

    /* Status Banner */
    .banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      border-radius: 8px;
      margin-bottom: 24px;
      border: 1px solid;
    }
    .banner.passed { background: var(--success-bg); border-color: var(--success); }
    .banner.failed { background: var(--danger-bg); border-color: var(--danger); }
    .banner-title { display: flex; align-items: center; gap: 14px; }
    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 20px;
      font-weight: 700;
      font-size: 13px;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }
    .badge.passed { background: var(--success); color: #fff; }
    .badge.failed { background: var(--danger); color: #fff; }
    .badge.warning { background: var(--warning); color: #161b22; }
    .badge.error { background: var(--danger); color: #fff; }
    .badge.info { background: var(--info); color: #fff; }

    /* Metric Grid */
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
    }
    .card-title { font-size: 12px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; margin-bottom: 8px; }
    .card-value { font-size: 26px; font-weight: 700; color: var(--text-bright); font-family: var(--mono); }
    .card-sub { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

    /* Section layout */
    .section { margin-bottom: 28px; }
    .section-header { font-size: 16px; font-weight: 600; color: var(--text-bright); margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }

    /* Tables */
    table { width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 8px; overflow: hidden; border: 1px solid var(--card-border); }
    th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--card-border); }
    th { background: rgba(255, 255, 255, 0.03); color: var(--text-bright); font-size: 12px; text-transform: uppercase; font-weight: 600; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }
    .mono { font-family: var(--mono); font-size: 12px; }

    /* Distribution bar */
    .dist-bar-container { display: flex; align-items: center; gap: 10px; width: 100%; }
    .dist-bar { height: 8px; background: var(--primary); border-radius: 4px; }
    .dist-pct { font-size: 11px; color: var(--text-muted); min-width: 40px; }

    /* Filter Controls */
    .filters { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
    .filter-btn {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
    }
    .filter-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }
    .search-box {
      flex: 1;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-bright);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
    }

    /* Recommendations */
    .rec-box {
      background: rgba(88, 166, 255, 0.08);
      border: 1px solid rgba(88, 166, 255, 0.3);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 24px;
    }
    .rec-item { display: flex; gap: 10px; margin-bottom: 8px; }
    .rec-item:last-child { margin-bottom: 0; }
    .rec-bullet { color: var(--primary); font-weight: bold; }

    /* Regressions */
    .reg-box {
      background: var(--danger-bg);
      border: 1px solid var(--danger);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 24px;
    }

    footer { text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--card-border); }
  </style>
</head>
<body>
<div class="container">
  <header>
    <div class="brand">
      <div>
        <h1>DatasetGate Audit</h1>
        <div class="tagline">Local-first computer-vision dataset quality gate</div>
      </div>
    </div>
    <div style="display: flex; gap: 8px;">
      <span class="meta-badge">Dataset: {{ snapshot.dataset_name }}</span>
      <span class="meta-badge">Format: {{ snapshot.format|upper }}</span>
      <span class="meta-badge">Fingerprint: {{ snapshot.dataset_fingerprint }}</span>
    </div>
  </header>

  <!-- Overall Status Banner -->
  <div class="banner {{ 'passed' if snapshot.policy_result.passed else 'failed' }}">
    <div class="banner-title">
      <span class="badge {{ 'passed' if snapshot.policy_result.passed else 'failed' }}">
        {{ snapshot.policy_result.status }}
      </span>
      <div>
        <strong style="color: var(--text-bright); font-size: 16px;">
          {% if snapshot.policy_result.passed %}
            Dataset quality gate passed all required policies.
          {% else %}
            Dataset failed configured release quality policies.
          {% endif %}
        </strong>
        <div style="color: var(--text-muted); font-size: 12px; margin-top: 2px;">
          {{ snapshot.policy_result.passed_checks|length }} passed checks &bull;
          {{ snapshot.policy_result.errors|length }} error findings &bull;
          {{ snapshot.policy_result.warnings|length }} warnings &bull;
          {{ snapshot.policy_result.skipped_checks|length }} skipped checks
        </div>
      </div>
    </div>
    <div class="mono" style="color: var(--text-muted); font-size: 12px;">
      {{ timestamp }}
    </div>
  </div>

  <!-- Key Metrics -->
  <div class="grid">
    <div class="card">
      <div class="card-title">Total Images</div>
      <div class="card-value">{{ snapshot.statistics.total_images }}</div>
      <div class="card-sub">{{ snapshot.statistics.images_per_split|length }} splits</div>
    </div>
    <div class="card">
      <div class="card-title">Total Annotations</div>
      <div class="card-value">{{ snapshot.statistics.total_annotations }}</div>
      <div class="card-sub">{{ snapshot.statistics.instances_per_class|length }} classes</div>
    </div>
    <div class="card">
      <div class="card-title">Empty Label Rate</div>
      <div class="card-value">{{ "%.1f"|format(snapshot.statistics.empty_label_rate * 100) }}%</div>
      <div class="card-sub">{{ snapshot.statistics.empty_label_counts.values()|sum }} unannotated images</div>
    </div>
    <div class="card">
      <div class="card-title">Class Imbalance</div>
      <div class="card-value">{{ "%.1f"|format(snapshot.statistics.class_imbalance_ratio) }}:1</div>
      <div class="card-sub">Max / Min class ratio</div>
    </div>
    <div class="card">
      <div class="card-title">Duplicate Groups</div>
      <div class="card-value" style="{{ 'color: var(--danger);' if snapshot.statistics.duplicate_groups_count > 0 else '' }}">
        {{ snapshot.statistics.duplicate_groups_count }}
      </div>
      <div class="card-sub">Exact content hashes</div>
    </div>
    <div class="card">
      <div class="card-title">Cross-Split Leakage</div>
      <div class="card-value" style="{{ 'color: var(--danger);' if snapshot.statistics.leakage_groups_count > 0 else '' }}">
        {{ snapshot.statistics.leakage_groups_count }}
      </div>
      <div class="card-sub">Train/Val/Test overlaps</div>
    </div>
  </div>

  <!-- Recommendations -->
  {% if recommendations %}
  <div class="rec-box">
    <div style="font-weight: 600; color: var(--primary); margin-bottom: 8px;">Actionable Recommendations</div>
    {% for rec in recommendations %}
    <div class="rec-item">
      <span class="rec-bullet">&rsaquo;</span>
      <span>{{ rec }}</span>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Baseline Regression Alert (if present) -->
  {% if comparison and comparison.has_regressions %}
  <div class="reg-box">
    <div style="font-weight: 600; color: var(--danger); margin-bottom: 8px;">Regressions Detected Relative to Baseline</div>
    {% for reg in comparison.regressions %}
    <div class="rec-item">
      <span style="color: var(--danger); font-weight: bold;">&times;</span>
      <span>{{ reg }}</span>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Per-Split Breakdown -->
  <div class="section">
    <div class="section-header">Split Breakdown</div>
    <table>
      <thead>
        <tr>
          <th>Split</th>
          <th>Images</th>
          <th>Annotations</th>
          <th>Unannotated</th>
          <th>Missing Classes</th>
        </tr>
      </thead>
      <tbody>
        {% for split, img_cnt in snapshot.statistics.images_per_split.items() %}
        <tr>
          <td><strong style="color: var(--text-bright);">{{ split }}</strong></td>
          <td class="mono">{{ img_cnt }}</td>
          <td class="mono">{{ snapshot.statistics.annotations_per_split.get(split, 0) }}</td>
          <td class="mono">{{ snapshot.statistics.empty_label_counts.get(split, 0) }}</td>
          <td>
            {% set missing = snapshot.statistics.missing_classes_per_split.get(split, []) %}
            {% if missing %}
              <span class="badge warning" style="font-size: 11px;">{{ missing|join(", ") }}</span>
            {% else %}
              <span style="color: var(--text-muted); font-size: 12px;">None</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Class Distribution -->
  <div class="section">
    <div class="section-header">Class Distribution</div>
    <table>
      <thead>
        <tr>
          <th style="width: 25%;">Class Name</th>
          <th style="width: 15%;">Instances</th>
          <th style="width: 40%;">Relative Distribution</th>
          <th style="width: 20%;">Per Split</th>
        </tr>
      </thead>
      <tbody>
        {% set max_count = 1 %}
        {% for count in snapshot.statistics.instances_per_class.values() %}
          {% if count > max_count %}{% set max_count = count %}{% endif %}
        {% endfor %}
        {% for c_name, count in snapshot.statistics.instances_per_class.items() %}
        <tr>
          <td><strong style="color: var(--text-bright);">{{ c_name }}</strong></td>
          <td class="mono">{{ count }}</td>
          <td>
            <div class="dist-bar-container">
              {% set pct = (count / snapshot.statistics.total_annotations * 100) if snapshot.statistics.total_annotations > 0 else 0 %}
              <div class="dist-bar" style="width: {{ (count / max_count * 100)|round(1) }}%;"></div>
              <span class="dist-pct mono">{{ "%.1f"|format(pct) }}%</span>
            </div>
          </td>
          <td class="mono" style="font-size: 11px; color: var(--text-muted);">
            {% for split, split_counts in snapshot.statistics.instances_per_class_by_split.items() %}
              {{ split }}: {{ split_counts.get(c_name, 0) }}{% if not loop.last %} | {% endif %}
            {% endfor %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Findings Table with Client-Side Filter -->
  <div class="section">
    <div class="section-header">
      <span>Findings & Defect Details ({{ snapshot.findings|length }})</span>
    </div>

    <div class="filters">
      <button class="filter-btn active" onclick="filterFindings('all')">All ({{ snapshot.findings|length }})</button>
      <button class="filter-btn" onclick="filterFindings('error')">Errors ({{ snapshot.policy_result.errors|length }})</button>
      <button class="filter-btn" onclick="filterFindings('warning')">Warnings ({{ snapshot.policy_result.warnings|length }})</button>
      <input type="text" id="searchFindings" class="search-box" placeholder="Filter by rule, path, or message..." onkeyup="searchTable()">
    </div>

    <table id="findingsTable">
      <thead>
        <tr>
          <th style="width: 120px;">Severity</th>
          <th style="width: 220px;">Rule ID</th>
          <th style="width: 90px;">Split</th>
          <th style="width: 250px;">File Path</th>
          <th>Explanation</th>
        </tr>
      </thead>
      <tbody>
        {% if snapshot.findings %}
          {% for f in snapshot.findings %}
          <tr data-severity="{{ f.severity.value }}">
            <td><span class="badge {{ f.severity.value }}">{{ f.severity.value }}</span></td>
            <td><strong class="mono" style="color: var(--text-bright);">{{ f.rule_id }}</strong></td>
            <td><span class="mono">{{ f.split or "—" }}</span></td>
            <td>
              {% if f.file_path %}
                <span class="mono" style="color: var(--primary);">{{ f.file_path }}</span>
              {% else %}
                <span style="color: var(--text-muted);">—</span>
              {% endif %}
            </td>
            <td>
              <div>{{ f.message }}</div>
              {% if f.related_paths %}
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
                  Related paths: <span class="mono">{{ f.related_paths|join(', ') }}</span>
                </div>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        {% else %}
          <tr>
            <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">
              No defects detected. Dataset passed all validation checks cleanly!
            </td>
          </tr>
        {% endif %}
      </tbody>
    </table>
  </div>

  <footer>
    DatasetGate v0.1.0 &bull; Local-first Computer Vision Dataset Validation & Release Gating &bull; Apache-2.0
  </footer>
</div>

<script>
  function filterFindings(sev) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    const rows = document.querySelectorAll('#findingsTable tbody tr');
    rows.forEach(row => {
      const rowSev = row.getAttribute('data-severity');
      if (sev === 'all' || rowSev === sev) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  }

  function searchTable() {
    const query = document.getElementById('searchFindings').value.toLowerCase();
    const rows = document.querySelectorAll('#findingsTable tbody tr');
    rows.forEach(row => {
      const text = row.innerText.toLowerCase();
      row.style.display = text.includes(query) ? '' : 'none';
    });
  }
</script>
</body>
</html>
"""


def generate_recommendations(snapshot: AuditSnapshot) -> list[str]:
    """Generate tailored, actionable recommendations based on audit results."""
    recs: list[str] = []
    rule_counts: dict[str, int] = {}
    for f in snapshot.findings:
        rule_counts[f.rule_id] = rule_counts.get(f.rule_id, 0) + 1

    if rule_counts.get("SPLIT_LEAKAGE", 0) > 0:
        recs.append(
            f"Fix Cross-Split Leakage: {rule_counts['SPLIT_LEAKAGE']} image instances appear across multiple splits. "
            "Remove duplicate copies from validation/test splits to ensure truthful performance metrics."
        )

    if rule_counts.get("CORRUPTED_IMAGE", 0) > 0:
        recs.append(
            f"Repair or Remove Corrupted Images: Found {rule_counts['CORRUPTED_IMAGE']} undecodable image files. "
            "These will cause worker crashes during DataLoader batch processing."
        )

    if rule_counts.get("BBOX_OUT_OF_BOUNDS", 0) > 0:
        recs.append(
            f"Clip Bounding Boxes: {rule_counts['BBOX_OUT_OF_BOUNDS']} bounding boxes extend outside normalized/image boundaries. "
            "Apply bounding box coordinate clipping [0, 1] to avoid negative loss spikes."
        )

    if rule_counts.get("MISSING_CLASS_IN_TRAIN", 0) > 0:
        missing = snapshot.statistics.missing_classes_per_split.get("train", [])
        recs.append(
            f"Address Missing Classes: Train split has 0 instances for declared class(es): {', '.join(missing)}. "
            "The model will never learn to detect these classes."
        )

    if snapshot.statistics.class_imbalance_ratio > 20.0:
        recs.append(
            f"High Class Imbalance: Imbalance ratio is {snapshot.statistics.class_imbalance_ratio:.1f}:1. "
            "Consider focal loss, class-weighted sampling, or augmenting under-represented classes."
        )

    if rule_counts.get("ORPHAN_LABEL_FILE", 0) > 0:
        recs.append(
            f"Clean Orphan Labels: {rule_counts['ORPHAN_LABEL_FILE']} label files exist without corresponding images. "
            "Remove or pair them before archiving dataset release."
        )

    if not recs:
        recs.append(
            "Dataset structure and annotations meet all configured quality policies. Ready for training."
        )

    return recs


def generate_html_report(
    snapshot: AuditSnapshot,
    output_path: Path,
    comparison: ComparisonResult | None = None,
) -> Path:
    """Render self-contained HTML report from AuditSnapshot."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    env = Environment(autoescape=True)
    template = env.from_string(HTML_TEMPLATE)

    recommendations = generate_recommendations(snapshot)
    rendered = template.render(
        snapshot=snapshot,
        comparison=comparison,
        recommendations=recommendations,
        timestamp=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    output_path.write_text(rendered, encoding="utf-8")
    return output_path
