"""Command-line entry point for Solvix."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from core.doctor import build_doctor_report
from core.engine import AnalysisError, analyze_path
from core.parser_bootstrap import SUPPORTED_TREE_SITTER_LANGUAGES, bootstrap_languages
from output.doctor_formatter import print_doctor_report
from output.json_formatter import format_json_report
from output.terminal_formatter import print_terminal_report
from output.text_formatter import format_text_report

VERSION_BANNER = "Solvix/A v0.2.6 - Computational Intelligence Layer"


@click.group(invoke_without_command=True)
@click.version_option(version="0.2.6", prog_name="Solvix/A")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Solvix CLI."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("target", type=click.Path(path_type=Path))
@click.option("--function", "function_name", help="Analyze one function by name.")
@click.option("--project", is_flag=True, help="Analyze a project folder recursively.")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON report.")
@click.option("--lang", "forced_language", help="Force a specific language.")
@click.option("--output", "output_path", type=click.Path(path_type=Path), help="Save the report to a file.")
def analyze(
    target: Path,
    function_name: str | None,
    project: bool,
    json_output: bool,
    forced_language: str | None,
    output_path: Path | None,
) -> None:
    """Analyze a file or folder."""
    try:
        report = analyze_path(
            target=target,
            function_name=function_name,
            project_mode=project,
            forced_language=forced_language,
        )
    except AnalysisError as exc:
        click.echo(str(exc))
        sys.exit(1)

    if output_path:
        _save_report(report, output_path)

    if json_output:
        click.echo(json.dumps(format_json_report(report), indent=2))
        return

    print_terminal_report(report)
    if output_path:
        click.echo(f"Solvix: Report saved to {output_path}")


@main.command("bootstrap-parsers")
@click.option("--all", "bootstrap_all", is_flag=True, help="Download parser artifacts for all supported non-Python languages.")
@click.argument("languages", nargs=-1)
def bootstrap_parsers(bootstrap_all: bool, languages: tuple[str, ...]) -> None:
    """Pre-download native parser artifacts for offline or locked-down environments."""

    requested = list(languages)
    if bootstrap_all or not requested:
        requested = SUPPORTED_TREE_SITTER_LANGUAGES

    try:
        downloaded, cache_path = bootstrap_languages(requested)
    except RuntimeError as exc:
        click.echo(f"Solvix: {exc}")
        sys.exit(1)

    click.echo(
        f"Solvix: Downloaded {downloaded} parser artifacts to {cache_path}."
    )


@main.command()
@click.option("--json", "json_output", is_flag=True, help="Emit doctor report as JSON.")
def doctor(json_output: bool) -> None:
    """Inspect parser health, cache state, and next steps."""

    report = build_doctor_report()
    if json_output:
        click.echo(json.dumps(report.to_dict(), indent=2))
        return
    print_doctor_report(report)


def _save_report(report: object, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".json":
        output_path.write_text(
            json.dumps(format_json_report(report), indent=2),
            encoding="utf-8",
        )
        return
    output_path.write_text(format_text_report(report), encoding="utf-8")


if __name__ == "__main__":
    main()
