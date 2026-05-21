"""Rich formatter for `solvix doctor`."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.doctor import DoctorReport

console = Console()

STATUS_STYLES = {
    "READY": "green",
    "READY_WITH_AUTO_BOOTSTRAP": "yellow",
    "DEGRADED": "bold red",
}


def print_doctor_report(report: DoctorReport) -> None:
    style = STATUS_STYLES.get(report.overall_status, "white")
    console.print(
        Panel(
            "\n".join(
                [
                    f"Status : [{style}]{report.overall_status}[/]",
                    f"Mode   : {report.mode}",
                    f"Backend: {report.parser_backend_status}",
                ]
            ),
            title="Solvix Doctor",
            expand=False,
        )
    )

    provider_table = Table(title="Parser Providers")
    provider_table.add_column("Provider")
    provider_table.add_column("Quality")
    provider_table.add_column("Available")
    provider_table.add_column("Detail")
    for provider in report.providers:
        provider_table.add_row(
            provider.name,
            provider.quality,
            "yes" if provider.available else "no",
            provider.detail,
        )
    console.print(provider_table)

    cache_table = Table(title="Parser Cache")
    cache_table.add_column("Field")
    cache_table.add_column("Value")
    cache_table.add_row("Cache path", report.cache_path or "not available")
    cache_table.add_row("Cached languages", ", ".join(report.cached_languages) or "none")
    cache_table.add_row("Missing languages", ", ".join(report.missing_languages) or "none")
    console.print(cache_table)

    console.print("Recommended next steps:")
    for step in report.next_steps:
        console.print(f"  - {step}")
