"""Rich terminal formatter for Solvix."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.report import AIOverlaySummary, FileReport, ProjectReport

console = Console()

LABEL_STYLES = {
    "CHEAP": "green",
    "MODERATE": "yellow",
    "EXPENSIVE": "red",
    "CRITICAL": "bold red",
    "LOW": "dim white",
    "MEDIUM": "yellow",
    "HIGH": "red",
    "low": "dim white",
    "moderate": "yellow",
    "high": "red",
    "urgent": "bold red",
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
            f"Cost     : [{LABEL_STYLES[function.cost.label]}]{function.cost.label}[/]",
            f"Patterns : {len(function.patterns)} found",
        ]
        if function.relevance is not None:
            body_lines.extend(
                [
                    f"Relevance : [{LABEL_STYLES[function.relevance.level]}]{function.relevance.level.upper()}[/] ({function.relevance.score})",
                    f"Priority  : {function.relevance.project_priority_label}",
                ]
            )
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
        if function.relevance is not None:
            console.print(f"[dim italic]Relevance: {function.relevance.reason}[/dim italic]")
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
    summary.add_row("Zone", report.summary.zone or "Not classified")
    if report.summary.relevance_score is not None:
        summary.add_row(
            "Relevance",
            f"{report.summary.relevance_level} ({report.summary.relevance_score})",
        )
    console.print(summary)
    if report.zone_reasons:
        console.print(Panel("\n".join(report.zone_reasons), title="Zone Classification", expand=False))


def _print_project(report: ProjectReport) -> None:
    profile = Table(title="Solvix/A Project Profile")
    profile.add_column("Field")
    profile.add_column("Value")
    profile.add_row("Primary profile", report.profile.primary_profile.replace("_", " ").title())
    profile.add_row("Secondary profiles", ", ".join(report.profile.secondary_profiles) or "None")
    profile.add_row("Execution models", ", ".join(report.profile.execution_models))
    profile.add_row("Surfaces", ", ".join(report.profile.surfaces) or "Not inferred")
    profile.add_row("Web shape", report.profile.web_shape or "Not refined")
    profile.add_row("Service topology", report.profile.service_topology or "Not refined")
    profile.add_row("Hybrid shape", report.profile.hybrid_shape or "Not inferred")
    profile.add_row("Confidence", f"{report.profile.confidence.title()} ({report.profile.confidence_score})")
    profile.add_row("Primary objectives", ", ".join(report.profile.primary_objectives))
    profile.add_row("Secondary objectives", ", ".join(report.profile.secondary_objectives))
    profile.add_row("Primary languages", ", ".join(report.profile.primary_languages) or "Unknown")
    profile.add_row("Critical zones", ", ".join(report.profile.critical_zones) or "Not inferred yet")
    profile.add_row("Noise zones", ", ".join(report.profile.noise_zones) or "None detected")
    console.print(profile)
    console.print(Panel(report.profile.explanation, title="Profile Explanation", expand=False))
    evidence = Table(title="Stage 1 Evidence")
    evidence.add_column("Field")
    evidence.add_column("Value")
    evidence.add_row("Dependency markers", ", ".join(report.profile.evidence.dependency_markers) or "None")
    evidence.add_row(
        "Dependency detail",
        ", ".join(
            f"{item.manifest}:{item.source}->{item.marker}" for item in report.profile.evidence.dependency_details
        )
        or "None",
    )
    evidence.add_row("Directory markers", ", ".join(report.profile.evidence.directory_markers) or "None")
    evidence.add_row("Entrypoints", ", ".join(report.profile.evidence.entrypoint_markers) or "None")
    evidence.add_row("Language markers", ", ".join(report.profile.evidence.language_markers) or "Unknown")
    evidence.add_row(
        "Confidence factors",
        ", ".join(
            f"{item.name}={item.weight if item.matched else 0}/{item.weight}"
            for item in report.profile.evidence.confidence_factors
        )
        or "None",
    )
    console.print(evidence)

    summary = Table(title="Solvix/A Project Summary")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Files analyzed", str(report.summary.files_analyzed))
    summary.add_row("Languages found", ", ".join(report.summary.languages_found))
    summary.add_row("Total functions", str(report.summary.total_functions))
    summary.add_row("Clean functions", str(report.summary.clean_functions))
    summary.add_row("Flagged functions", str(report.summary.flagged_functions))
    summary.add_row("Discounted functions", str(report.summary.discounted_functions))
    summary.add_row("Risk level", report.summary.risk_level)
    console.print(summary)

    console.print(Panel(report.summary.why_it_matters, title="Why It Matters", expand=False))
    console.print(Panel(report.summary.recommended_next_step, title="Easiest Next Step", expand=False))

    if report.multi_lens is not None:
        default_report = next(
            (item for item in report.multi_lens.reports if item.lens == report.multi_lens.default_lens),
            None,
        )
        lens_table = Table(title="Stage 4 Multi-Lens")
        lens_table.add_column("Field")
        lens_table.add_column("Value")
        lens_table.add_row("Default lens", report.multi_lens.default_lens)
        lens_table.add_row("Available lenses", ", ".join(report.multi_lens.available_lenses))
        lens_table.add_row("Why this lens", report.multi_lens.default_lens_reason)
        console.print(lens_table)

        if default_report is not None:
            console.print(Panel(default_report.summary, title=f"{default_report.title} Summary", expand=False))
            if default_report.top_themes:
                themes = Table(title=f"Top Themes ({report.multi_lens.default_lens})")
                themes.add_column("#")
                themes.add_column("Theme")
                themes.add_column("Priority")
                themes.add_column("Lens Score")
                themes.add_column("Stage 3")
                for index, theme in enumerate(default_report.top_themes, start=1):
                    themes.add_row(
                        str(index),
                        theme.title,
                        theme.priority_label,
                        str(theme.score),
                        str(theme.base_theme_score),
                    )
                console.print(themes)
                for theme in default_report.top_themes:
                    console.print(f"[dim]{theme.reason}[/dim]")

            if default_report.top_lanes:
                lanes = Table(title=f"Top Lanes ({report.multi_lens.default_lens})")
                lanes.add_column("#")
                lanes.add_column("Lane")
                lanes.add_column("Lens Score")
                lanes.add_column("Why")
                for index, lane in enumerate(default_report.top_lanes, start=1):
                    lanes.add_row(str(index), lane.title, str(lane.score), lane.reason)
                console.print(lanes)

            if default_report.recommended_first_action:
                console.print(Panel(default_report.recommended_first_action, title="Lens First Action", expand=False))

    if report.synthesis is not None:
        console.print(Panel(report.synthesis.repository_story, title="Repository Story", expand=False))
        console.print(Panel(report.synthesis.maintainer_brief, title="Maintainer Brief", expand=False))

        if report.synthesis.dominant_themes:
            themes = Table(title="Top Themes")
            themes.add_column("#")
            themes.add_column("Theme")
            themes.add_column("Priority")
            themes.add_column("Score")
            themes.add_column("Zone")
            for index, theme in enumerate(report.synthesis.dominant_themes[:3], start=1):
                themes.add_row(
                    str(index),
                    theme.title,
                    theme.priority_label,
                    str(theme.relevance_score),
                    theme.dominant_zone,
                )
            console.print(themes)
            for theme in report.synthesis.dominant_themes[:3]:
                console.print(f"[dim]{theme.summary}[/dim]")

        if report.synthesis.action_lanes:
            lanes = Table(title="Action Lanes")
            lanes.add_column("Order")
            lanes.add_column("Lane")
            lanes.add_column("Why Now")
            for lane in report.synthesis.action_lanes[:3]:
                lanes.add_row(str(lane.recommended_order), lane.title, lane.why_now)
            console.print(lanes)

        if report.synthesis.noise_diagnostic is not None:
            noise = report.synthesis.noise_diagnostic
            console.print(
                Panel(
                    (
                        f"{noise.summary}\n"
                        f"Discounted functions: {noise.discounted_functions}\n"
                        f"Dominant noise zones: {', '.join(noise.dominant_noise_zones) or 'None'}"
                    ),
                    title="Noise Diagnostic",
                    expand=False,
                )
            )

    hotspots = report.summary.prioritized_hotspots or report.summary.top_functions
    if hotspots:
        console.print("Top Prioritized Hotspots:")
        for index, item in enumerate(hotspots, start=1):
            level = item.get("relevance_level", "low")
            style = LABEL_STYLES.get(level, "white")
            console.print(
                f"  {index}. [{style}]{str(item.get('project_priority_label', 'watch')).upper()}[/] "
                f"{item['file']} -> {item['function']}() "
                f"(relevance {item.get('relevance_score', 'n/a')}, cost {item['label']})"
            )
            if item.get("relevance_reason"):
                console.print(f"     [dim]{item['relevance_reason']}[/dim]")
    if report.profile.zone_classification:
        zones = Table(title="Per-File Zones")
        zones.add_column("Zone")
        zones.add_column("File")
        for item in report.profile.zone_classification[:20]:
            zones.add_row(item.zone, item.file)
        console.print(zones)
    _print_ai_overlay(report.ai_overlay)


def _print_ai_overlay(ai_overlay: AIOverlaySummary | None) -> None:
    if ai_overlay is None or not ai_overlay.enabled:
        return

    overlay = Table(title="Stage 5 AI Overlay")
    overlay.add_column("Field")
    overlay.add_column("Value")
    overlay.add_row("Source of truth", "Deterministic Stages 1-4")
    overlay.add_row("Status", ai_overlay.status)
    overlay.add_row("Mode", ai_overlay.mode)
    overlay.add_row("Model", ai_overlay.model or "n/a")
    overlay.add_row("Provider", ai_overlay.provider or "n/a")
    overlay.add_row(
        "Input budget",
        (
            f"themes={ai_overlay.input_budget.max_top_themes}, "
            f"lanes={ai_overlay.input_budget.max_top_lanes}, "
            f"hotspots={ai_overlay.input_budget.max_top_hotspots}, "
            f"examples/theme={ai_overlay.input_budget.max_examples_per_theme}"
        ),
    )
    console.print(overlay)

    if ai_overlay.result is not None:
        console.print(Panel(ai_overlay.result.executive_summary, title="AI Executive Summary", expand=False))
        if ai_overlay.result.maintainer_plan:
            plan = "\n".join(f"{index}. {step}" for index, step in enumerate(ai_overlay.result.maintainer_plan, start=1))
            console.print(Panel(plan, title="AI Maintainer Plan", expand=False))
        if ai_overlay.result.lens_explanation:
            console.print(Panel(ai_overlay.result.lens_explanation, title="AI Lens Explanation", expand=False))
        grounded = (
            f"Themes  : {', '.join(ai_overlay.result.grounded_theme_keys) or 'None'}\n"
            f"Lanes   : {', '.join(ai_overlay.result.grounded_lane_keys) or 'None'}\n"
            f"Hotspots: "
            + (
                ", ".join(
                    f"{item['file']} -> {item['function']}()"
                    for item in ai_overlay.result.grounded_hotspots
                )
                or "None"
            )
        )
        console.print(Panel(grounded, title="Grounded References", expand=False))
        if ai_overlay.result.caveats:
            console.print(Panel("\n".join(ai_overlay.result.caveats), title="AI Caveats", expand=False))
        return

    if ai_overlay.notes:
        console.print(Panel("\n".join(ai_overlay.notes), title="AI Notes", expand=False))
    if ai_overlay.error:
        console.print(Panel(ai_overlay.error, title="AI Error", expand=False))
