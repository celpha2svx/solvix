"""JSON formatter for Solvix reports."""

from __future__ import annotations

from core.report import ProjectReport, iso_timestamp, to_dict


def format_json_report(report: object) -> dict:
    if isinstance(report, ProjectReport):
        return {
            "solvix_version": "0.2.6",
            "analyzed_at": iso_timestamp(),
            "project": True,
            "summary": to_dict(report.summary),
            "files": to_dict(report.files),
        }

    payload = to_dict(report)
    return {
        "solvix_version": "0.2.6",
        "analyzed_at": iso_timestamp(),
        "file": payload["file"],
        "language": payload["language"],
        "parser": payload["parser"],
        "summary": {
            "total_functions": payload["summary"]["total_functions"],
            "cheap": payload["summary"]["cheap"],
            "moderate": payload["summary"]["moderate"],
            "expensive": payload["summary"]["expensive"],
            "critical": payload["summary"]["critical"],
        },
        "functions": [
            {
                "name": function["name"],
                "line_start": function["line_start"],
                "line_end": function["line_end"],
                "cost": {
                    "label": function["context"]["adjusted_label"],
                    "score": function["cost"]["score"],
                    "dominant_severity": function["cost"]["dominant_severity"],
                },
                "context": {
                    "is_hot_path": function["context"]["is_hot_path"],
                    "call_frequency": function["context"]["call_frequency"],
                    "urgency_modifier": function["context"]["urgency_modifier"],
                },
                "patterns": function["patterns"],
            }
            for function in payload["functions"]
        ],
    }
