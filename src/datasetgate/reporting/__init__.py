"""Reporting modules for JSON and HTML formats."""

from datasetgate.reporting.html import generate_html_report
from datasetgate.reporting.json import generate_json_report

__all__ = ["generate_html_report", "generate_json_report"]
