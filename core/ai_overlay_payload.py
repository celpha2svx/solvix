"""Bounded Stage 5 payload builder for optional AI overlays."""

from __future__ import annotations

from core.report import (
    AIOverlayInput,
    AIOverlayInputBudget,
    MultiLensSummary,
    ProjectProfile,
    ProjectSummary,
    SynthesisSummary,
)

AI_OVERLAY_MAX_TOP_THEMES = 5
AI_OVERLAY_MAX_TOP_LANES = 3
AI_OVERLAY_MAX_TOP_HOTSPOTS = 8
AI_OVERLAY_MAX_EXAMPLES_PER_THEME = 2


def build_ai_overlay_payload(
    profile: ProjectProfile,
    summary: ProjectSummary,
    synthesis: SynthesisSummary | None,
    multi_lens: MultiLensSummary | None,
) -> tuple[AIOverlayInput, AIOverlayInputBudget]:
    """Compress deterministic Stage 1-4 output into a bounded Stage 5 payload."""

    budget = AIOverlayInputBudget(
        max_top_themes=AI_OVERLAY_MAX_TOP_THEMES,
        max_top_lanes=AI_OVERLAY_MAX_TOP_LANES,
        max_top_hotspots=AI_OVERLAY_MAX_TOP_HOTSPOTS,
        max_examples_per_theme=AI_OVERLAY_MAX_EXAMPLES_PER_THEME,
    )
    default_lens_report = _default_lens_report(multi_lens)

    top_themes: list[dict[str, object]] = []
    if synthesis is not None:
        for theme in synthesis.dominant_themes[: budget.max_top_themes]:
            top_themes.append(
                {
                    "key": theme.key,
                    "title": theme.title,
                    "summary": theme.summary,
                    "relevance_score": theme.relevance_score,
                    "priority_label": theme.priority_label,
                    "pattern_families": list(theme.pattern_families),
                    "affected_files": theme.affected_files,
                    "affected_functions": theme.affected_functions,
                    "critical_zone_hits": theme.critical_zone_hits,
                    "noise_zone_hits": theme.noise_zone_hits,
                    "dominant_zone": theme.dominant_zone,
                    "repetition_score": theme.repetition_score,
                    "representative_examples": [
                        {
                            "file": example.get("file"),
                            "function": example.get("function"),
                            "label": example.get("label"),
                            "zone": example.get("zone"),
                        }
                        for example in theme.representative_examples[: budget.max_examples_per_theme]
                    ],
                }
            )

    top_lanes: list[dict[str, object]] = []
    if default_lens_report is not None:
        for lane in default_lens_report.top_lanes[: budget.max_top_lanes]:
            top_lanes.append(
                {
                    "key": lane.lane_key,
                    "title": lane.title,
                    "score": lane.score,
                    "reason": lane.reason,
                    "related_theme_keys": list(lane.related_theme_keys),
                }
            )
    elif synthesis is not None:
        for lane in synthesis.action_lanes[: budget.max_top_lanes]:
            top_lanes.append(
                {
                    "key": lane.key,
                    "title": lane.title,
                    "reason": lane.why_now,
                    "recommended_order": lane.recommended_order,
                    "related_theme_keys": list(lane.related_theme_keys),
                }
            )

    top_hotspots = [
        {
            "file": item.get("file"),
            "function": item.get("function"),
            "label": item.get("label"),
            "relevance_score": item.get("relevance_score"),
            "relevance_level": item.get("relevance_level"),
            "project_priority_label": item.get("project_priority_label"),
            "relevance_reason": item.get("relevance_reason"),
            "zone": item.get("zone"),
        }
        for item in (summary.prioritized_hotspots or summary.top_functions)[: budget.max_top_hotspots]
    ]

    payload = AIOverlayInput(
        project_profile={
            "primary_profile": profile.primary_profile,
            "secondary_profiles": list(profile.secondary_profiles),
            "execution_models": list(profile.execution_models),
            "surfaces": list(profile.surfaces),
            "confidence": profile.confidence,
            "confidence_score": profile.confidence_score,
            "primary_objectives": list(profile.primary_objectives),
            "secondary_objectives": list(profile.secondary_objectives),
            "primary_languages": list(profile.primary_languages),
            "critical_zones": list(profile.critical_zones),
            "noise_zones": list(profile.noise_zones),
            "explanation": profile.explanation,
            "web_shape": profile.web_shape,
            "service_topology": profile.service_topology,
            "hybrid_shape": profile.hybrid_shape,
        },
        project_summary={
            "files_analyzed": summary.files_analyzed,
            "languages_found": list(summary.languages_found),
            "total_functions": summary.total_functions,
            "clean_functions": summary.clean_functions,
            "flagged_functions": summary.flagged_functions,
            "discounted_functions": summary.discounted_functions,
            "risk_level": summary.risk_level,
            "why_it_matters": summary.why_it_matters,
            "recommended_next_step": summary.recommended_next_step,
        },
        synthesis_summary={
            "repository_story": synthesis.repository_story if synthesis is not None else "",
            "maintainer_brief": synthesis.maintainer_brief if synthesis is not None else "",
            "theme_count": len(synthesis.dominant_themes) if synthesis is not None else 0,
            "lane_count": len(synthesis.action_lanes) if synthesis is not None else 0,
        },
        default_lens={
            "lens": multi_lens.default_lens if multi_lens is not None else None,
            "title": default_lens_report.title if default_lens_report is not None else None,
            "summary": default_lens_report.summary if default_lens_report is not None else None,
            "recommended_first_action": (
                default_lens_report.recommended_first_action if default_lens_report is not None else None
            ),
            "default_lens_reason": multi_lens.default_lens_reason if multi_lens is not None else None,
            "available_lenses": list(multi_lens.available_lenses) if multi_lens is not None else [],
        },
        top_themes=top_themes,
        top_lanes=top_lanes,
        top_hotspots=top_hotspots,
        noise_diagnostic=(
            {
                "discounted_functions": synthesis.noise_diagnostic.discounted_functions,
                "dominant_noise_zones": list(synthesis.noise_diagnostic.dominant_noise_zones),
                "noise_ratio": synthesis.noise_diagnostic.noise_ratio,
                "summary": synthesis.noise_diagnostic.summary,
            }
            if synthesis is not None and synthesis.noise_diagnostic is not None
            else None
        ),
    )
    return payload, budget


def _default_lens_report(multi_lens: MultiLensSummary | None):
    if multi_lens is None:
        return None
    for report in multi_lens.reports:
        if report.lens == multi_lens.default_lens:
            return report
    return None
