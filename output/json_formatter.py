"""JSON formatter for Solvix reports."""

from __future__ import annotations

from core.report import ProjectReport, iso_timestamp, to_dict
from core.version import get_solvix_version


def format_json_report(report: object) -> dict:
    solvix_version = get_solvix_version()
    if isinstance(report, ProjectReport):
        return {
            "solvix_version": solvix_version,
            "analyzed_at": iso_timestamp(),
            "project": True,
            "profile": to_dict(report.profile),
            "summary": to_dict(report.summary),
            "synthesis": to_dict(report.synthesis),
            "multi_lens": to_dict(report.multi_lens),
            "ai_overlay": to_dict(report.ai_overlay),
            "files": to_dict(report.files),
        }

    payload = to_dict(report)
    return {
        "solvix_version": solvix_version,
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
            "zone": payload["summary"].get("zone"),
            "relevance_score": payload["summary"].get("relevance_score"),
            "relevance_level": payload["summary"].get("relevance_level"),
            "relevance_reason": payload["summary"].get("relevance_reason"),
        },
        "zone_reasons": payload.get("zone_reasons", []),
        "relevance": payload.get("relevance"),
        "functions": [
            {
                "name": function["name"],
                "line_start": function["line_start"],
                "line_end": function["line_end"],
                "cost": {
                    "label": function["cost"]["label"],
                    "score": function["cost"]["score"],
                    "dominant_severity": function["cost"]["dominant_severity"],
                },
                "context": {
                    "is_hot_path": function["context"]["is_hot_path"],
                    "call_frequency": function["context"]["call_frequency"],
                    "urgency_modifier": function["context"]["urgency_modifier"],
                },
                "patterns": function["patterns"],
                "relevance": function.get("relevance"),
            }
            for function in payload["functions"]
        ],
    }
