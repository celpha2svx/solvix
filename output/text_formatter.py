"""Plain text formatter for saved Solvix reports."""

from __future__ import annotations

from core.report import FileReport, ProjectReport


def format_text_report(report: object) -> str:
    if isinstance(report, ProjectReport):
        return _format_project(report)
    return _format_file(report)


def _format_file(report: FileReport) -> str:
    lines: list[str] = []
    for warning in report.warnings:
        lines.append(warning)
    for function in report.functions:
        lines.extend(
            [
                "=== Solvix/A Report ===",
                f"Function : {function.name}",
                f"Language : {report.language.title()}",
                f"Parser   : {report.parser.backend}",
                f"Cost     : {function.context.adjusted_label}",
                f"Patterns : {len(function.patterns)} found",
                "",
            ]
        )
        for pattern in function.patterns:
            lines.extend(
                [
                    f"[{pattern.severity}] Line {pattern.line} - {pattern.name.replace('_', ' ').title()}",
                    pattern.explanation,
                    f"-> {pattern.suggestion}",
                    "",
                ]
            )
        lines.append(f"Context: {function.context.context_note}")
        lines.append(
            f"Urgency: {function.context.adjusted_label} - modifier {function.context.urgency_modifier}"
        )
        lines.append("")

    lines.extend(
        [
            "=== Solvix/A File Summary ===",
            f"File      : {report.summary.file}",
            f"Language  : {report.summary.language.title()}",
            f"Parser    : {report.parser.backend}",
            f"Functions : {report.summary.total_functions}",
            f"Clean     : {report.summary.cheap}",
            f"Flagged   : {report.summary.moderate + report.summary.expensive + report.summary.critical}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _format_project(report: ProjectReport) -> str:
    lines = [
        "=== Solvix/A Project Summary ===",
        f"Files analyzed    : {report.summary.files_analyzed}",
        f"Languages found   : {', '.join(report.summary.languages_found)}",
        f"Total functions   : {report.summary.total_functions}",
        f"Clean functions   : {report.summary.clean_functions}",
        f"Flagged functions : {report.summary.flagged_functions}",
        "",
    ]
    if report.summary.top_functions:
        lines.append("Top 10 Most Expensive Functions:")
        for index, item in enumerate(report.summary.top_functions, start=1):
            lines.append(f"{index}. {item['label']}  {item['file']} -> {item['function']}()")
    return "\n".join(lines).rstrip() + "\n"
