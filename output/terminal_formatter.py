"""Rich terminal formatter for Solvix."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.report import FileReport, ProjectReport

console = Console()

LABEL_STYLES = {
    "CHEAP": "green",
    "MODERATE": "yellow",
    "EXPENSIVE": "red",
    "CRITICAL": "bold red",
    "LOW": "dim white",
    "MEDIUM": "yellow",
    "HIGH": "red",
}


def print_terminal_report(report: object) -> None:
    if isinstance(report, ProjectReport):
        _print_project(report)
        return
    _print_file(report)


def _print_file(report: FileReport) -> None:
    for warning in report.warnings:
        console.print(f"[dim]{warning}[/dim]")
    for function in report.functions:
        body_lines = [
            f"Function : {function.name}",
            f"Language : {report.language.title()}",
            f"Parser   : {report.parser.backend}",
            f"Cost     : [{LABEL_STYLES[function.context.adjusted_label]}]{function.context.adjusted_label}[/]",
            f"Patterns : {len(function.patterns)} found",
        ]
        console.print(Panel("\n".join(body_lines), title="Solvix/A Report", expand=False))
        for pattern in function.patterns:
            style = LABEL_STYLES.get(pattern.severity, "white")
            console.print(f"[{style}][{pattern.severity}][/]{' '}Line {pattern.line} - {pattern.name.replace('_', ' ').title()}")
            console.print(pattern.explanation)
            console.print(f"[cyan]-> {pattern.suggestion}[/cyan]")
            console.print()
        console.print(f"[dim italic]Context: {function.context.context_note}[/dim italic]")
        console.print(
            f"[dim italic]Urgency: {function.context.adjusted_label} - modifier {function.context.urgency_modifier}[/dim italic]"
        )
        console.print()

    summary = Table(title="Solvix/A File Summary")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("File", report.summary.file)
    summary.add_row("Language", report.summary.language.title())
    summary.add_row("Parser", report.parser.backend)
    summary.add_row("Functions", str(report.summary.total_functions))
    summary.add_row("Clean", str(report.summary.cheap))
    summary.add_row("Flagged", str(report.summary.moderate + report.summary.expensive + report.summary.critical))
    console.print(summary)


def _print_project(report: ProjectReport) -> None:
    summary = Table(title="Solvix/A Project Summary")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Files analyzed", str(report.summary.files_analyzed))
    summary.add_row("Languages found", ", ".join(report.summary.languages_found))
    summary.add_row("Total functions", str(report.summary.total_functions))
    summary.add_row("Clean functions", str(report.summary.clean_functions))
    summary.add_row("Flagged functions", str(report.summary.flagged_functions))
    console.print(summary)

    if report.summary.top_functions:
        console.print("Top 10 Most Expensive Functions:")
        for index, item in enumerate(report.summary.top_functions, start=1):
            console.print(f"  {index}. {item['label']}  {item['file']} -> {item['function']}()")
