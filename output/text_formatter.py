"""Plain text formatter for saved Solvix reports."""

from __future__ import annotations

from core.report import AIOverlaySummary, FileReport, ProjectReport


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
                f"Cost     : {function.cost.label}",
                f"Patterns : {len(function.patterns)} found",
                f"Relevance: {function.relevance.level.upper()} ({function.relevance.score})" if function.relevance is not None else "Relevance: Not project-scored",
                f"Priority : {function.relevance.project_priority_label}" if function.relevance is not None else "Priority : n/a",
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
        if function.relevance is not None:
            lines.append(f"Relevance why: {function.relevance.reason}")
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
            f"Zone      : {report.summary.zone or 'Not classified'}",
            f"Relevance : {report.summary.relevance_level} ({report.summary.relevance_score})" if report.summary.relevance_score is not None else "Relevance : Not project-scored",
        ]
    )
    if report.zone_reasons:
        lines.append(f"Zone why  : {'; '.join(report.zone_reasons)}")
    if report.summary.relevance_reason:
        lines.append(f"Why now   : {report.summary.relevance_reason}")
    return "\n".join(lines).rstrip() + "\n"


def _format_project(report: ProjectReport) -> str:
    lines = [
        "=== Solvix/A Project Profile ===",
        f"Primary profile   : {report.profile.primary_profile}",
        f"Secondary profiles: {', '.join(report.profile.secondary_profiles) or 'None'}",
        f"Execution models  : {', '.join(report.profile.execution_models)}",
        f"Surfaces          : {', '.join(report.profile.surfaces) or 'Not inferred'}",
        f"Web shape         : {report.profile.web_shape or 'Not refined'}",
        f"Service topology  : {report.profile.service_topology or 'Not refined'}",
        f"Hybrid shape      : {report.profile.hybrid_shape or 'Not inferred'}",
        f"Confidence        : {report.profile.confidence} ({report.profile.confidence_score})",
        f"Primary objectives: {', '.join(report.profile.primary_objectives)}",
        f"Secondary goals   : {', '.join(report.profile.secondary_objectives)}",
        f"Primary languages : {', '.join(report.profile.primary_languages) or 'Unknown'}",
        f"Critical zones    : {', '.join(report.profile.critical_zones) or 'Not inferred yet'}",
        f"Noise zones       : {', '.join(report.profile.noise_zones) or 'None detected'}",
        f"Explanation       : {report.profile.explanation}",
        "",
        "=== Stage 1 Evidence ===",
        f"Dependency markers: {', '.join(report.profile.evidence.dependency_markers) or 'None'}",
        f"Dependency detail : {', '.join(f'{item.manifest}:{item.source}->{item.marker}' for item in report.profile.evidence.dependency_details) or 'None'}",
        f"Directory markers : {', '.join(report.profile.evidence.directory_markers) or 'None'}",
        f"Entrypoints       : {', '.join(report.profile.evidence.entrypoint_markers) or 'None'}",
        f"Language markers  : {', '.join(report.profile.evidence.language_markers) or 'Unknown'}",
        f"Confidence factors: {', '.join(f'{item.name}={item.weight if item.matched else 0}/{item.weight}' for item in report.profile.evidence.confidence_factors) or 'None'}",
        "",
        "=== Solvix/A Project Summary ===",
        f"Files analyzed    : {report.summary.files_analyzed}",
        f"Languages found   : {', '.join(report.summary.languages_found)}",
        f"Total functions   : {report.summary.total_functions}",
        f"Clean functions   : {report.summary.clean_functions}",
        f"Flagged functions : {report.summary.flagged_functions}",
        f"Discounted funcs  : {report.summary.discounted_functions}",
        f"Risk level        : {report.summary.risk_level}",
        "",
        "Why it matters:",
        report.summary.why_it_matters,
        "",
        "Easiest next step:",
        report.summary.recommended_next_step,
        "",
    ]
    if report.multi_lens is not None:
        default_report = next(
            (item for item in report.multi_lens.reports if item.lens == report.multi_lens.default_lens),
            None,
        )
        lines.extend(
            [
                "=== Stage 4 Multi-Lens ===",
                f"Default lens     : {report.multi_lens.default_lens}",
                f"Available lenses : {', '.join(report.multi_lens.available_lenses)}",
                f"Why this lens    : {report.multi_lens.default_lens_reason}",
                "",
            ]
        )
        if default_report is not None:
            lines.extend(
                [
                    "Default lens summary:",
                    default_report.summary,
                    "",
                ]
            )
            if default_report.top_themes:
                lines.append("Top Themes For Default Lens:")
                for index, theme in enumerate(default_report.top_themes, start=1):
                    lines.append(
                        f"{index}. {theme.priority_label} {theme.title} "
                        f"(lens score {theme.score}, stage3 {theme.base_theme_score})"
                    )
                    lines.append(f"   {theme.reason}")
            if default_report.top_lanes:
                lines.extend(["", "Top Lanes For Default Lens:"])
                for index, lane in enumerate(default_report.top_lanes, start=1):
                    lines.append(f"{index}. {lane.title} (lens score {lane.score})")
                    lines.append(f"   {lane.reason}")
            if default_report.recommended_first_action:
                lines.extend(["", "Lens First Action:", default_report.recommended_first_action, ""])
    if report.synthesis is not None:
        lines.extend(
            [
                "=== Stage 3 Synthesis ===",
                "Repository story:",
                report.synthesis.repository_story,
                "",
                "Maintainer brief:",
                report.synthesis.maintainer_brief,
                "",
            ]
        )
        if report.synthesis.dominant_themes:
            lines.append("Top Themes:")
            for index, theme in enumerate(report.synthesis.dominant_themes[:3], start=1):
                lines.append(
                    f"{index}. {theme.priority_label} {theme.title} "
                    f"(score {theme.relevance_score}, zone {theme.dominant_zone}, functions {theme.affected_functions})"
                )
                lines.append(f"   {theme.summary}")
        if report.synthesis.action_lanes:
            lines.extend(["", "Action Lanes:"])
            for lane in report.synthesis.action_lanes[:3]:
                lines.append(f"{lane.recommended_order}. {lane.title}")
                lines.append(f"   {lane.why_now}")
        if report.synthesis.noise_diagnostic is not None:
            noise = report.synthesis.noise_diagnostic
            lines.extend(
                [
                    "",
                    "Noise Diagnostic:",
                    (
                        f"{noise.summary} Discounted functions: {noise.discounted_functions}. "
                        f"Dominant noise zones: {', '.join(noise.dominant_noise_zones) or 'None'}."
                    ),
                    "",
                ]
            )
    hotspots = report.summary.prioritized_hotspots or report.summary.top_functions
    if hotspots:
        lines.append("Top Prioritized Hotspots:")
        for index, item in enumerate(hotspots, start=1):
            lines.append(
                f"{index}. {item.get('project_priority_label', 'watch')} "
                f"{item['file']} -> {item['function']}() "
                f"(relevance {item.get('relevance_score', 'n/a')}, cost {item['label']})"
            )
            if item.get("relevance_reason"):
                lines.append(f"   why: {item['relevance_reason']}")
    if report.profile.zone_classification:
        lines.extend(["", "=== Per-File Zones ==="])
        for item in report.profile.zone_classification[:20]:
            lines.append(f"{item.zone:<10} {item.file}")
    _append_ai_overlay(lines, report.ai_overlay)
    return "\n".join(lines).rstrip() + "\n"


def _append_ai_overlay(lines: list[str], ai_overlay: AIOverlaySummary | None) -> None:
    if ai_overlay is None or not ai_overlay.enabled:
        return

    lines.extend(
        [
            "",
            "=== Stage 5 AI Overlay ===",
            "Deterministic Stages 1-4 remain the source of truth.",
            f"Status           : {ai_overlay.status}",
            f"Mode             : {ai_overlay.mode}",
            f"Model            : {ai_overlay.model or 'n/a'}",
            f"Provider         : {ai_overlay.provider or 'n/a'}",
            (
                "Input budget     : "
                f"themes={ai_overlay.input_budget.max_top_themes}, "
                f"lanes={ai_overlay.input_budget.max_top_lanes}, "
                f"hotspots={ai_overlay.input_budget.max_top_hotspots}, "
                f"examples/theme={ai_overlay.input_budget.max_examples_per_theme}"
            ),
        ]
    )
    if ai_overlay.result is not None:
        lines.extend(
            [
                "",
                "AI Executive Summary:",
                ai_overlay.result.executive_summary,
                "",
                "AI Maintainer Plan:",
            ]
        )
        for index, step in enumerate(ai_overlay.result.maintainer_plan, start=1):
            lines.append(f"{index}. {step}")
        lines.extend(
            [
                "",
                "AI Lens Explanation:",
                ai_overlay.result.lens_explanation,
                "",
                "Grounded References:",
                f"Themes  : {', '.join(ai_overlay.result.grounded_theme_keys) or 'None'}",
                f"Lanes   : {', '.join(ai_overlay.result.grounded_lane_keys) or 'None'}",
                (
                    "Hotspots: "
                    + (
                        ", ".join(
                            f"{item['file']} -> {item['function']}()"
                            for item in ai_overlay.result.grounded_hotspots
                        )
                        or "None"
                    )
                ),
            ]
        )
        if ai_overlay.result.caveats:
            lines.extend(["", "AI Caveats:"])
            for caveat in ai_overlay.result.caveats:
                lines.append(f"- {caveat}")
    else:
        if ai_overlay.notes:
            lines.extend(["", "AI Notes:"])
            for note in ai_overlay.notes:
                lines.append(f"- {note}")
        if ai_overlay.error:
            lines.extend(["", "AI Error:", ai_overlay.error])
