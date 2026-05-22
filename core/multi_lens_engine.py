"""Deterministic Stage 4 multi-lens reporting.

This module reorders Stage 3 themes and lanes through explicit engineering
lenses without mutating the underlying Stage 1-3 analysis.
"""

from __future__ import annotations

from collections import defaultdict

from core.report import (
    ActionLane,
    InsightTheme,
    LensFactor,
    LensLaneView,
    LensReport,
    LensThemeView,
    MultiLensSummary,
    ProjectProfile,
    SynthesisSummary,
)

LENS_ORDER = (
    "performance",
    "startup",
    "maintainability",
    "api_stability",
    "reliability",
    "cloud_cost",
    "battery",
)

LENS_PRIORITY_THRESHOLDS = (
    (140, "fix_first"),
    (90, "high_priority"),
    (35, "worth_reviewing"),
    (1, "watch"),
    (-10_000, "ignore_for_now"),
)

OBJECTIVE_SCORE_CAP = 20
SURFACE_SCORE_CAP = 12
EXECUTION_SCORE_CAP = 12
NOISE_GUARDRAIL_CAP = 34

LENS_DEFINITIONS = {
    "performance": {
        "title": "Performance Lens",
        "theme_families": {
            "loop_amplification": 18,
            "allocation_churn": 15,
            "data_copying": 12,
            "repeated_compute": 14,
            "network_roundtrips": 10,
            "large_object_pressure": 10,
            "async_blocking": 8,
            "control_flow_complexity": 4,
            "recursive_risk": 4,
            "general_efficiency": 6,
        },
        "lanes": {
            "request_path_hotspots": 12,
            "pipeline_throughput_fixes": 14,
            "service_entrypoint_review": 9,
            "frontend_responsiveness": 9,
            "cloud_control_path": 8,
            "device_memory_pressure": 7,
            "mobile_app_efficiency": 6,
            "startup_path_cleanup": 4,
            "command_dispatch_cleanup": 4,
            "dispatch_complexity_review": 3,
            "general_efficiency_review": 5,
            "noise_cleanup_only": -20,
        },
        "objectives": {
            "latency": 12,
            "throughput": 12,
            "request_overhead": 11,
            "memory_efficiency": 6,
            "serialization_efficiency": 5,
            "network_efficiency": 4,
        },
        "surfaces": {
            "http": 5,
            "web_ui": 5,
            "desktop": 3,
            "mobile": 3,
            "device": 3,
            "cli": 2,
            "sdk": 1,
        },
        "execution_models": {
            "request_response": 7,
            "background_jobs": 7,
            "distributed_services": 5,
            "serverless": 3,
            "library": 2,
            "monolith": 2,
        },
        "focus": "hot paths, request pressure, and throughput-sensitive work",
    },
    "startup": {
        "title": "Startup Lens",
        "theme_families": {
            "allocation_churn": 14,
            "data_copying": 12,
            "repeated_compute": 13,
            "loop_amplification": 7,
            "control_flow_complexity": 6,
            "network_roundtrips": 4,
            "async_blocking": 5,
            "general_efficiency": 5,
        },
        "lanes": {
            "startup_path_cleanup": 16,
            "command_dispatch_cleanup": 12,
            "request_path_hotspots": 4,
            "cloud_control_path": 5,
            "service_entrypoint_review": 4,
            "dispatch_complexity_review": 5,
            "frontend_responsiveness": 3,
            "pipeline_throughput_fixes": 3,
            "general_efficiency_review": 4,
            "noise_cleanup_only": -20,
        },
        "objectives": {
            "startup_time": 16,
            "user_feedback": 6,
            "latency": 4,
            "request_overhead": 3,
            "battery_efficiency": 2,
        },
        "surfaces": {
            "cli": 6,
            "desktop": 4,
            "mobile": 3,
            "http": 2,
            "web_ui": 2,
            "device": 2,
            "sdk": 1,
        },
        "execution_models": {
            "serverless": 10,
            "monolith": 4,
            "distributed_services": 3,
            "request_response": 2,
            "background_jobs": 2,
            "library": 2,
        },
        "focus": "cold-start, boot-time setup, and command responsiveness",
    },
    "maintainability": {
        "title": "Maintainability Lens",
        "theme_families": {
            "control_flow_complexity": 18,
            "recursive_risk": 14,
            "repeated_compute": 10,
            "async_blocking": 8,
            "allocation_churn": 6,
            "data_copying": 6,
            "loop_amplification": 6,
            "network_roundtrips": 5,
            "large_object_pressure": 4,
            "general_efficiency": 8,
        },
        "lanes": {
            "dispatch_complexity_review": 14,
            "general_efficiency_review": 10,
            "command_dispatch_cleanup": 6,
            "pipeline_throughput_fixes": 6,
            "request_path_hotspots": 5,
            "service_entrypoint_review": 6,
            "cloud_control_path": 6,
            "device_memory_pressure": 6,
            "mobile_app_efficiency": 5,
            "frontend_responsiveness": 5,
            "startup_path_cleanup": 5,
            "noise_cleanup_only": 2,
        },
        "objectives": {
            "maintainability": 14,
            "api_stability": 12,
            "extension_stability": 12,
            "test_reliability": 6,
            "feedback_speed": 4,
            "reliability": 4,
        },
        "surfaces": {
            "sdk": 4,
            "http": 3,
            "cli": 2,
            "desktop": 2,
            "mobile": 2,
            "web_ui": 2,
        },
        "execution_models": {
            "library": 8,
            "distributed_services": 3,
            "background_jobs": 3,
            "request_response": 2,
            "serverless": 1,
        },
        "focus": "complexity reduction, repetition cleanup, and stable core APIs",
    },
    "api_stability": {
        "title": "API Stability Lens",
        "theme_families": {
            "control_flow_complexity": 14,
            "repeated_compute": 12,
            "network_roundtrips": 11,
            "data_copying": 9,
            "recursive_risk": 8,
            "allocation_churn": 8,
            "loop_amplification": 7,
            "general_efficiency": 7,
            "async_blocking": 6,
            "large_object_pressure": 5,
        },
        "lanes": {
            "request_path_hotspots": 14,
            "dispatch_complexity_review": 12,
            "cloud_control_path": 8,
            "service_entrypoint_review": 7,
            "general_efficiency_review": 6,
            "startup_path_cleanup": 5,
            "frontend_responsiveness": 4,
            "device_memory_pressure": 4,
            "mobile_app_efficiency": 4,
            "command_dispatch_cleanup": 3,
            "pipeline_throughput_fixes": 3,
            "noise_cleanup_only": -18,
        },
        "objectives": {
            "api_stability": 16,
            "extension_stability": 14,
            "serialization_efficiency": 9,
            "request_overhead": 7,
            "maintainability": 6,
            "network_efficiency": 4,
        },
        "surfaces": {
            "sdk": 7,
            "http": 6,
            "web_ui": 2,
            "cli": 2,
            "desktop": 2,
            "mobile": 2,
        },
        "execution_models": {
            "library": 7,
            "request_response": 4,
            "distributed_services": 3,
            "serverless": 2,
            "background_jobs": 2,
        },
        "focus": "stable public contracts, extension surfaces, and request-facing API behavior",
    },
    "reliability": {
        "title": "Reliability Lens",
        "theme_families": {
            "async_blocking": 18,
            "recursive_risk": 16,
            "loop_amplification": 7,
            "allocation_churn": 7,
            "data_copying": 6,
            "network_roundtrips": 8,
            "large_object_pressure": 8,
            "control_flow_complexity": 6,
            "general_efficiency": 5,
        },
        "lanes": {
            "device_memory_pressure": 12,
            "cloud_control_path": 10,
            "pipeline_throughput_fixes": 9,
            "service_entrypoint_review": 8,
            "request_path_hotspots": 7,
            "mobile_app_efficiency": 8,
            "startup_path_cleanup": 6,
            "command_dispatch_cleanup": 5,
            "general_efficiency_review": 5,
            "dispatch_complexity_review": 4,
            "frontend_responsiveness": 4,
            "noise_cleanup_only": -18,
        },
        "objectives": {
            "reliability": 14,
            "device_constraints": 10,
            "test_reliability": 8,
            "memory_efficiency": 8,
            "latency": 5,
        },
        "surfaces": {
            "device": 6,
            "http": 4,
            "mobile": 4,
            "sdk": 2,
            "desktop": 2,
            "cli": 1,
        },
        "execution_models": {
            "background_jobs": 7,
            "serverless": 7,
            "distributed_services": 6,
            "request_response": 4,
            "library": 2,
        },
        "focus": "safer production behavior, resilient workers, and constrained runtimes",
    },
    "cloud_cost": {
        "title": "Cloud Cost Lens",
        "theme_families": {
            "network_roundtrips": 18,
            "repeated_compute": 14,
            "loop_amplification": 10,
            "allocation_churn": 10,
            "data_copying": 8,
            "large_object_pressure": 8,
            "async_blocking": 6,
            "general_efficiency": 6,
            "recursive_risk": 4,
            "control_flow_complexity": 4,
        },
        "lanes": {
            "cloud_control_path": 14,
            "request_path_hotspots": 12,
            "service_entrypoint_review": 10,
            "startup_path_cleanup": 9,
            "pipeline_throughput_fixes": 7,
            "general_efficiency_review": 5,
            "device_memory_pressure": 4,
            "mobile_app_efficiency": 4,
            "frontend_responsiveness": 4,
            "dispatch_complexity_review": 3,
            "noise_cleanup_only": -18,
        },
        "objectives": {
            "network_efficiency": 14,
            "request_overhead": 12,
            "startup_time": 10,
            "latency": 6,
            "serialization_efficiency": 6,
            "memory_efficiency": 5,
            "throughput": 4,
        },
        "surfaces": {
            "http": 6,
            "sdk": 4,
            "mobile": 3,
            "web_ui": 2,
            "cli": 2,
            "device": 2,
        },
        "execution_models": {
            "distributed_services": 8,
            "serverless": 8,
            "request_response": 6,
            "background_jobs": 4,
        },
        "focus": "repeated runtime spend, request fan-out, and serverless waste",
    },
    "battery": {
        "title": "Battery Lens",
        "theme_families": {
            "loop_amplification": 15,
            "allocation_churn": 14,
            "repeated_compute": 13,
            "data_copying": 10,
            "large_object_pressure": 8,
            "network_roundtrips": 7,
            "async_blocking": 8,
            "control_flow_complexity": 5,
            "recursive_risk": 5,
            "general_efficiency": 6,
        },
        "lanes": {
            "mobile_app_efficiency": 15,
            "device_memory_pressure": 13,
            "frontend_responsiveness": 8,
            "cloud_control_path": 5,
            "startup_path_cleanup": 5,
            "request_path_hotspots": 5,
            "pipeline_throughput_fixes": 4,
            "service_entrypoint_review": 4,
            "general_efficiency_review": 4,
            "command_dispatch_cleanup": 3,
            "dispatch_complexity_review": 3,
            "noise_cleanup_only": -18,
        },
        "objectives": {
            "battery_efficiency": 15,
            "device_constraints": 10,
            "memory_efficiency": 8,
            "network_efficiency": 8,
            "startup_time": 5,
            "user_feedback": 4,
        },
        "surfaces": {
            "mobile": 8,
            "device": 7,
            "web_ui": 4,
            "http": 3,
            "cli": 1,
        },
        "execution_models": {
            "background_jobs": 3,
            "distributed_services": 3,
            "request_response": 2,
            "serverless": 2,
            "library": 1,
        },
        "focus": "mobile and device efficiency, polling sensitivity, and repeated update work",
    },
}


def build_multi_lens_summary(
    profile: ProjectProfile,
    synthesis: SynthesisSummary | None,
) -> MultiLensSummary | None:
    if synthesis is None:
        return None

    default_lens, default_reason = select_default_lens(profile)
    available_lenses = [default_lens] + [lens for lens in LENS_ORDER if lens != default_lens]
    lane_lookup = {lane.key: lane for lane in synthesis.action_lanes}

    reports: list[LensReport] = []
    for lens in available_lenses:
        lens_report = _build_lens_report(
            lens=lens,
            profile=profile,
            synthesis=synthesis,
            lane_lookup=lane_lookup,
        )
        reports.append(lens_report)

    return MultiLensSummary(
        default_lens=default_lens,
        default_lens_reason=default_reason,
        available_lenses=available_lenses,
        reports=reports,
    )


def select_default_lens(profile: ProjectProfile) -> tuple[str, str]:
    primary_profile = profile.primary_profile
    if primary_profile == "framework_library":
        return "maintainability", "Framework libraries default to maintainability so dispatch and extension complexity stays front and center."
    if primary_profile == "sdk_library":
        return "maintainability", "SDK-style repositories default to maintainability because stable client and API surfaces matter most."
    if primary_profile == "cli_tool":
        return "startup", "CLI repositories default to startup because command responsiveness and boot overhead shape the user experience."
    if primary_profile == "serverless_application":
        return "startup", "Serverless repositories default to startup because cold-start cost is part of the runtime path."
    if primary_profile == "mobile_application":
        return "battery", "Mobile repositories default to battery because repeated update work and network churn directly affect device efficiency."
    if primary_profile == "device_firmware":
        return "reliability", "Firmware-shaped repositories default to reliability because constrained device paths and control loops must stay safe first."
    if primary_profile == "data_pipeline":
        return "performance", "Data pipelines default to performance because throughput and repeated batch work dominate the follow-up list."
    if primary_profile == "test_heavy_repository":
        return "maintainability", "Test-heavy repositories default to maintainability so repeated complexity stays visible without pretending the repo is production-hot."
    if primary_profile == "desktop_application":
        return "startup", "Desktop applications default to startup because boot-time responsiveness is a first impression for users."
    if primary_profile == "web_backend":
        if profile.web_shape == "website_web_app":
            return "performance", "Website and web-app repos default to performance to keep render and request-facing responsiveness visible."
        return "performance", "API and service repositories default to performance because request-path overhead is usually the dominant production pressure."
    return "maintainability", "General repositories default to maintainability as the safest deterministic lens when no narrower priority dominates."


def _build_lens_report(
    lens: str,
    profile: ProjectProfile,
    synthesis: SynthesisSummary,
    lane_lookup: dict[str, ActionLane],
) -> LensReport:
    title = LENS_DEFINITIONS[lens]["title"]
    theme_views = _build_theme_views(lens, profile, synthesis)
    lane_views = _build_lane_views(lens, theme_views, lane_lookup)
    summary = _build_lens_summary_text(lens, profile, theme_views, lane_views)
    recommended_first_action = _build_first_action(lens, lane_views, lane_lookup)
    return LensReport(
        lens=lens,
        title=title,
        summary=summary,
        top_themes=theme_views[:3],
        top_lanes=lane_views[:3],
        recommended_first_action=recommended_first_action,
    )


def _build_theme_views(
    lens: str,
    profile: ProjectProfile,
    synthesis: SynthesisSummary,
) -> list[LensThemeView]:
    theme_views: list[LensThemeView] = []
    for theme in synthesis.dominant_themes:
        lane_key, _, _ = theme.key.partition(":")
        factors = [
            LensFactor(
                name="stage3_theme_score",
                weight=theme.relevance_score,
                reason=f"Stage 3 already scored this theme at {theme.relevance_score}.",
            ),
            _theme_family_factor(lens, theme),
            _lane_factor(lens, lane_key),
            _objective_factor(lens, profile),
            _surface_factor(lens, profile),
            _execution_factor(lens, profile),
            _noise_guardrail_factor(profile, synthesis, theme, lane_key),
        ]
        score = sum(factor.weight for factor in factors)
        priority_label = _priority_for_score(score)
        reason = _compose_theme_reason(lens, theme, factors)
        theme_views.append(
            LensThemeView(
                theme_key=theme.key,
                title=theme.title,
                base_theme_score=theme.relevance_score,
                score=score,
                priority_label=priority_label,
                reason=reason,
                factors=factors,
            )
        )
    theme_views.sort(
        key=lambda item: (
            item.score,
            item.base_theme_score,
            item.title,
        ),
        reverse=True,
    )
    return theme_views


def _build_lane_views(
    lens: str,
    theme_views: list[LensThemeView],
    lane_lookup: dict[str, ActionLane],
) -> list[LensLaneView]:
    grouped: dict[str, list[LensThemeView]] = defaultdict(list)
    for theme_view in theme_views:
        lane_key, _, _ = theme_view.theme_key.partition(":")
        grouped[lane_key].append(theme_view)

    lane_views: list[LensLaneView] = []
    for lane_key, items in grouped.items():
        items.sort(key=lambda item: (item.score, item.base_theme_score, item.title), reverse=True)
        lane = lane_lookup.get(lane_key)
        title = lane.title if lane is not None else lane_key.replace("_", " ").title()
        score = sum(item.score for item in items)
        lead_theme = items[0]
        lane_views.append(
            LensLaneView(
                lane_key=lane_key,
                title=title,
                score=score,
                reason=(
                    f"{lead_theme.title} leads this lane under the {lens} lens "
                    f"and {len(items)} ranked theme(s) reinforce it."
                ),
                related_theme_keys=[item.theme_key for item in items],
            )
        )

    lane_views.sort(
        key=lambda item: (
            item.score,
            len(item.related_theme_keys),
            item.title,
        ),
        reverse=True,
    )
    return lane_views


def _theme_family_factor(lens: str, theme: InsightTheme) -> LensFactor:
    weights = LENS_DEFINITIONS[lens]["theme_families"]
    matched: list[str] = []
    score = 0
    for family in theme.pattern_families:
        weight = int(weights.get(family, 0))
        if weight:
            matched.append(f"{family}={weight}")
            score += weight
    return LensFactor(
        name="theme_family_fit",
        weight=score,
        reason="Theme family fit matched " + (", ".join(matched) if matched else "no special family boosts") + ".",
    )


def _lane_factor(lens: str, lane_key: str) -> LensFactor:
    weight = int(LENS_DEFINITIONS[lens]["lanes"].get(lane_key, 0))
    return LensFactor(
        name="lane_fit",
        weight=weight,
        reason=f"The {lane_key.replace('_', ' ')} lane contributes {weight} points under this lens.",
    )


def _objective_factor(lens: str, profile: ProjectProfile) -> LensFactor:
    weights = LENS_DEFINITIONS[lens]["objectives"]
    matched: list[str] = []
    objectives = list(dict.fromkeys(profile.primary_objectives + profile.secondary_objectives[:2]))
    score = 0
    for objective in objectives:
        weight = int(weights.get(objective, 0))
        if weight:
            matched.append(f"{objective}={weight}")
            score += weight
    score = min(score, OBJECTIVE_SCORE_CAP)
    return LensFactor(
        name="project_objective_fit",
        weight=score,
        reason="Project objective fit matched " + (", ".join(matched) if matched else "no direct objective boosts") + ".",
    )


def _surface_factor(lens: str, profile: ProjectProfile) -> LensFactor:
    weights = LENS_DEFINITIONS[lens]["surfaces"]
    matched: list[str] = []
    score = 0
    for surface in profile.surfaces:
        weight = int(weights.get(surface, 0))
        if weight:
            matched.append(f"{surface}={weight}")
            score += weight
    score = min(score, SURFACE_SCORE_CAP)
    return LensFactor(
        name="surface_fit",
        weight=score,
        reason="Surface fit matched " + (", ".join(matched) if matched else "no direct surface boosts") + ".",
    )


def _execution_factor(lens: str, profile: ProjectProfile) -> LensFactor:
    weights = LENS_DEFINITIONS[lens]["execution_models"]
    matched: list[str] = []
    score = 0
    for model in profile.execution_models:
        weight = int(weights.get(model, 0))
        if weight:
            matched.append(f"{model}={weight}")
            score += weight
    score = min(score, EXECUTION_SCORE_CAP)
    return LensFactor(
        name="execution_model_fit",
        weight=score,
        reason="Execution-model fit matched " + (", ".join(matched) if matched else "no direct execution-model boosts") + ".",
    )


def _noise_guardrail_factor(
    profile: ProjectProfile,
    synthesis: SynthesisSummary,
    theme: InsightTheme,
    lane_key: str,
) -> LensFactor:
    score = 0
    reasons: list[str] = []
    if theme.noise_zone_hits:
        penalty = min(theme.noise_zone_hits * 6, 18)
        score -= penalty
        reasons.append(f"noise hits={penalty}")
    if theme.dominant_zone in profile.noise_zones:
        score -= 8
        reasons.append("dominant noise zone")
    if lane_key == "noise_cleanup_only":
        score -= 10
        reasons.append("noise-only lane")
    if synthesis.noise_diagnostic is not None and synthesis.noise_diagnostic.noise_ratio >= 0.5:
        score -= 4
        reasons.append("repo noise pressure")
    if profile.primary_profile == "test_heavy_repository":
        score += 10
        reasons.append("test-heavy repo partial recovery")
    score = max(score, -NOISE_GUARDRAIL_CAP)
    return LensFactor(
        name="noise_guardrail",
        weight=score,
        reason="Noise guardrail applied from " + (", ".join(reasons) if reasons else "no additional noise penalties") + ".",
    )


def _build_lens_summary_text(
    lens: str,
    profile: ProjectProfile,
    theme_views: list[LensThemeView],
    lane_views: list[LensLaneView],
) -> str:
    focus = LENS_DEFINITIONS[lens]["focus"]
    profile_label = profile.primary_profile.replace("_", " ")
    if not theme_views or not lane_views:
        return f"The {lens} lens found no additional repo-level ordering beyond Stage 3 for this {profile_label} repository."

    top_theme = theme_views[0]
    top_lane = lane_views[0]
    lens_specific = _strongest_lens_specific_factors(top_theme)
    reason_note = ", ".join(lens_specific) if lens_specific else "base Stage 3 score"
    return (
        f"Under the {lens} lens, this {profile_label} repository emphasizes {focus}. "
        f"{top_theme.title} leads and pushes {top_lane.title.lower()} to the front. "
        f"The main drivers are {reason_note}."
    )


def _build_first_action(
    lens: str,
    lane_views: list[LensLaneView],
    lane_lookup: dict[str, ActionLane],
) -> str:
    if not lane_views:
        return f"No {lens} follow-up is needed after deterministic Stage 3 synthesis."

    lane_view = lane_views[0]
    lane = lane_lookup.get(lane_view.lane_key)
    if lane is None or not lane.representative_targets:
        return f"Start with {lane_view.title.lower()} because it ranks first under the {lens} lens."

    targets = ", ".join(
        f"{item['file']} -> {item['function']}()"
        for item in lane.representative_targets[:2]
    )
    follow_up = ""
    if len(lane_views) > 1:
        follow_up = f" Then move to {lane_views[1].title.lower()}."
    return f"Start with {lane_view.title.lower()} by checking {targets}.{follow_up}".rstrip()


def _compose_theme_reason(lens: str, theme: InsightTheme, factors: list[LensFactor]) -> str:
    strongest = _strongest_lens_specific_factors_from_list(factors)
    strongest_note = ", ".join(strongest) if strongest else "base Stage 3 carry-over"
    return (
        f"{theme.title} stays visible under the {lens} lens because of {strongest_note}. "
        f"Stage 3 base score: {theme.relevance_score}."
    )


def _strongest_lens_specific_factors(theme_view: LensThemeView) -> list[str]:
    return _strongest_lens_specific_factors_from_list(theme_view.factors)


def _strongest_lens_specific_factors_from_list(factors: list[LensFactor]) -> list[str]:
    candidates = [
        factor
        for factor in factors
        if factor.name not in {"stage3_theme_score", "noise_guardrail"} and factor.weight > 0
    ]
    candidates.sort(key=lambda item: (item.weight, item.name), reverse=True)
    return [f"{factor.name}={factor.weight}" for factor in candidates[:3]]


def _priority_for_score(score: int) -> str:
    for threshold, label in LENS_PRIORITY_THRESHOLDS:
        if score >= threshold:
            return label
    return "ignore_for_now"
