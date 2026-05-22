"""Command-line entry point for Solvix."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from core.doctor import build_doctor_report
from core.engine import AnalysisError, analyze_path
from core.report import ProjectReport
from core.parser_bootstrap import SUPPORTED_TREE_SITTER_LANGUAGES, bootstrap_languages
from output.doctor_formatter import print_doctor_report
from output.json_formatter import format_json_report
from output.terminal_formatter import print_terminal_report
from output.text_formatter import format_text_report

VERSION_BANNER = "Solvix/A v0.3.1 - Computational Intelligence Layer"
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 100}

ROOT_HELP = """Solvix analyzes source code cost and points you to the next useful fix.

\b
Common examples:
  solvix analyze app.py
  solvix analyze src --project
  solvix analyze src --project --json --output report.json
  solvix analyze src --project --ai-mode assist
  solvix doctor
  solvix bootstrap-parsers --all

\b
AI is optional. Deterministic analysis runs without an API key.
Use "solvix COMMAND --help" for command-specific examples.
"""

ANALYZE_HELP = """Analyze one source file or a whole project.

\b
Modes:
  File mode    Analyze one file and list detected functions.
  Project mode Use --project on a folder for repo-aware summaries, themes, and lenses.

\b
Examples:
  solvix analyze app.py
  solvix analyze app.py --function parse_invoice
  solvix analyze src --project
  solvix analyze src --project --json --output report.json
  solvix analyze src --project --lang python
  solvix analyze src --project --ai-mode assist

\b
AI overlay notes:
  --ai-mode assist adds optional post-processing after deterministic project analysis.
  --ai-mode off is the default and never contacts an AI provider.
"""

BOOTSTRAP_HELP = """Pre-download native parser artifacts for offline or restricted machines.

\b
Use this during workstation, CI image, or base-container setup when first-run downloads
are not desirable. Python uses the built-in ast parser and does not need bootstrapping.

\b
Examples:
  solvix bootstrap-parsers --all
  solvix bootstrap-parsers javascript typescript rust
  solvix doctor
"""

DOCTOR_HELP = """Inspect parser health, cache state, and the next operational step.

\b
Use doctor after installation, on CI runners, or when parser behavior looks degraded.
It reports native parser availability, cached parser artifacts, and suggested fixes.

\b
Examples:
  solvix doctor
  solvix doctor --json
  solvix bootstrap-parsers --all
"""


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS, help=ROOT_HELP)
@click.version_option(version="0.3.1", prog_name="Solvix/A")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Solvix CLI."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command(help=ANALYZE_HELP, short_help="Analyze one file or an entire project.")
@click.argument("target", type=click.Path(path_type=Path))
@click.option("--function", "function_name", metavar="NAME", help="Analyze only one detected function by name.")
@click.option("--project", is_flag=True, help="Treat TARGET as a folder and run repo-aware project analysis.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of terminal output.")
@click.option("--lang", "forced_language", metavar="LANGUAGE", help="Force language detection, for example python or rust.")
@click.option("--output", "output_path", type=click.Path(path_type=Path), help="Save the report to a .txt or .json file.")
@click.option(
    "--ai-mode",
    type=click.Choice(["off", "assist", "interactive"], case_sensitive=False),
    default="off",
    show_default=True,
    help="Optional AI overlay after deterministic project analysis. Requires --project.",
)
@click.option(
    "--ai-model",
    metavar="MODEL",
    help="Override the optional AI model. Defaults: assist=gpt-5.4-mini, interactive=gpt-5.5.",
)
def analyze(
    target: Path,
    function_name: str | None,
    project: bool,
    json_output: bool,
    forced_language: str | None,
    output_path: Path | None,
    ai_mode: str,
    ai_model: str | None,
) -> None:
    try:
        report = _run_analysis_with_progress(
            target=target,
            function_name=function_name,
            project_mode=project,
            forced_language=forced_language,
            ai_mode=ai_mode,
            ai_model=ai_model,
        )
        if output_path:
            _save_report(report, output_path)

        if json_output:
            if output_path:
                _print_json_mode_summary(report, output_path)
                return
            click.echo(json.dumps(format_json_report(report), indent=2))
            return

        print_terminal_report(report)
        if output_path:
            click.echo(f"Solvix: Report saved to {output_path}")
    except AnalysisError as exc:
        click.echo(str(exc))
        sys.exit(1)


@main.command("bootstrap-parsers", help=BOOTSTRAP_HELP, short_help="Pre-download native parser artifacts.")
@click.option("--all", "bootstrap_all", is_flag=True, help="Prepare every supported non-Python parser artifact.")
@click.argument("languages", nargs=-1, metavar="[LANGUAGES]...")
def bootstrap_parsers(bootstrap_all: bool, languages: tuple[str, ...]) -> None:
    requested = list(languages)
    if bootstrap_all or not requested:
        requested = SUPPORTED_TREE_SITTER_LANGUAGES

    try:
        downloaded, cache_path = _bootstrap_languages_with_progress(requested)
    except RuntimeError as exc:
        click.echo(f"Solvix: {exc}")
        sys.exit(1)

    click.echo(
        f"Solvix: Parser bootstrap complete. Prepared {downloaded} artifact(s) "
        f"for {len(requested)} language(s) in {cache_path}."
    )


@main.command(help=DOCTOR_HELP, short_help="Inspect parser health and cache state.")
@click.option("--json", "json_output", is_flag=True, help="Emit the doctor report as JSON for automation.")
def doctor(json_output: bool) -> None:
    report = build_doctor_report()
    if json_output:
        click.echo(json.dumps(report.to_dict(), indent=2))
        return
    print_doctor_report(report)


def _save_report(report: object, output_path: Path) -> None:
    try:
        if output_path.exists() and output_path.is_dir():
            raise AnalysisError(
                f"Solvix: Cannot write report to {output_path}. Check file permissions or choose a different output path."
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() == ".json":
            output_path.write_text(
                json.dumps(format_json_report(report), indent=2),
                encoding="utf-8",
            )
            return
        output_path.write_text(format_text_report(report), encoding="utf-8")
    except (PermissionError, IsADirectoryError) as exc:
        raise AnalysisError(
            f"Solvix: Cannot write report to {output_path}. Check file permissions or choose a different output path."
        ) from exc


def _run_analysis_with_progress(
    target: Path,
    function_name: str | None,
    project_mode: bool,
    forced_language: str | None,
    ai_mode: str,
    ai_model: str | None,
):
    if not project_mode:
        return analyze_path(
            target=target,
            function_name=function_name,
            project_mode=project_mode,
            forced_language=forced_language,
            ai_mode=ai_mode,
            ai_model=ai_model,
        )

    current_path = {"value": "Starting"}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("{task.fields[current_file]}"),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task_id = progress.add_task(
            "Discovering source files",
            total=100,
            current_file=current_path["value"],
        )

        def on_status(message: str) -> None:
            progress.update(task_id, description=message, current_file="")

        def on_progress(current: int, total: int, path: Path) -> None:
            current_path["value"] = path.name
            progress.update(
                task_id,
                description="Scoring functions",
                total=total,
                completed=current,
                current_file=current_path["value"],
            )

        return analyze_path(
            target=target,
            function_name=function_name,
            project_mode=project_mode,
            forced_language=forced_language,
            progress_callback=on_progress,
            status_callback=on_status,
            ai_mode=ai_mode,
            ai_model=ai_model,
        )


def _bootstrap_languages_with_progress(requested: list[str]) -> tuple[int, str]:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task_id = progress.add_task(
            f"Preparing {len(requested)} parser language(s)",
            total=len(requested),
        )

        def on_parser_progress(event: str, language: str, current: int, total: int) -> None:
            descriptions = {
                "start": f"Downloading parser for {language}",
                "complete": f"Prepared parser for {language}",
                "failed": f"Parser download failed for {language}",
            }
            completed = current if event in {"complete", "failed"} else max(current - 1, 0)
            progress.update(
                task_id,
                total=total,
                completed=completed,
                description=descriptions.get(event, f"Preparing parser for {language}"),
            )

        return bootstrap_languages(requested, progress_callback=on_parser_progress)


def _print_json_mode_summary(report: object, output_path: Path) -> None:
    if isinstance(report, ProjectReport):
        click.echo("Solvix: Full JSON project report saved.")
        click.echo(f"Files analyzed : {report.summary.files_analyzed}")
        click.echo(f"Total functions: {report.summary.total_functions}")
        click.echo(f"Flagged        : {report.summary.flagged_functions}")
        click.echo(f"Risk level     : {report.summary.risk_level}")
        if report.ai_overlay is not None and report.ai_overlay.enabled:
            click.echo(f"AI overlay     : {report.ai_overlay.status}")
            click.echo(f"AI mode        : {report.ai_overlay.mode}")
            if report.ai_overlay.model is not None:
                click.echo(f"AI model       : {report.ai_overlay.model}")
            if report.ai_overlay.result is not None:
                click.echo(f"AI summary     : {report.ai_overlay.result.executive_summary}")
            elif report.ai_overlay.error:
                click.echo(f"AI note        : {report.ai_overlay.error}")
            elif report.ai_overlay.notes:
                click.echo(f"AI note        : {' '.join(report.ai_overlay.notes)}")
        if report.multi_lens is not None:
            default_report = next(
                (item for item in report.multi_lens.reports if item.lens == report.multi_lens.default_lens),
                None,
            )
            click.echo(f"Default lens   : {report.multi_lens.default_lens}")
            click.echo(f"Lens options   : {', '.join(report.multi_lens.available_lenses)}")
            click.echo(f"Lens why       : {report.multi_lens.default_lens_reason}")
            if default_report is not None:
                top_themes = ", ".join(theme.title for theme in default_report.top_themes) or "None"
                click.echo(f"Lens themes    : {top_themes}")
                top_lanes = ", ".join(lane.title for lane in default_report.top_lanes) or "None"
                click.echo(f"Lens lanes     : {top_lanes}")
                if default_report.recommended_first_action:
                    click.echo(f"Lens action    : {default_report.recommended_first_action}")
        if report.synthesis is not None:
            click.echo(f"Repo story     : {report.synthesis.repository_story}")
            top_themes = ", ".join(theme.title for theme in report.synthesis.dominant_themes[:3]) or "None"
            click.echo(f"Top themes     : {top_themes}")
            top_lanes = ", ".join(lane.title for lane in report.synthesis.action_lanes[:3]) or "None"
            click.echo(f"Action lanes   : {top_lanes}")
            if report.synthesis.noise_diagnostic is not None:
                click.echo(f"Noise          : {report.synthesis.noise_diagnostic.summary}")
        click.echo(f"Why it matters : {report.summary.why_it_matters}")
        click.echo(f"Next step      : {report.summary.recommended_next_step}")
        click.echo(f"Saved to       : {output_path}")
        return
    click.echo(f"Solvix: JSON report saved to {output_path}")


if __name__ == "__main__":
    main()
