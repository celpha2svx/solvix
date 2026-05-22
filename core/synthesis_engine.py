"""Deterministic Stage 3 signal synthesis.

This module compresses many Stage 2 findings into repo-level themes and
action lanes without hiding the raw function-level evidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from core.report import ActionLane, FileReport, InsightTheme, NoiseDiagnostic, ProjectProfile, ProjectSummary, SynthesisSummary

PATTERN_FAMILY_MAP = {
    "nested_loop": "loop_amplification",
    "memory_allocation_in_loop": "allocation_churn",
    "string_concatenation_in_loop": "allocation_churn",
    "data_copy_in_loop": "data_copying",
    "async_blocking_in_loop": "async_blocking",
    "deep_nesting": "control_flow_complexity",
    "recursion_without_memoization": "recursive_risk",
    "repeated_expensive_function_call": "repeated_compute",
    "n_plus_one_query_pattern": "network_roundtrips",
    "large_object_in_deep_loop": "large_object_pressure",
}

PATTERN_FAMILY_TITLES = {
    "loop_amplification": "Loop Amplification",
    "allocation_churn": "Allocation Churn",
    "data_copying": "Data Copying",
    "async_blocking": "Async Blocking",
    "control_flow_complexity": "Control-Flow Complexity",
    "recursive_risk": "Recursive Risk",
    "repeated_compute": "Repeated Compute",
    "network_roundtrips": "Network Roundtrips",
    "large_object_pressure": "Large-Object Pressure",
    "general_efficiency": "General Efficiency Pressure",
}

PATTERN_FAMILY_SUMMARY = {
    "loop_amplification": "nested iteration is stacking up in hot code",
    "allocation_churn": "allocation-heavy work keeps repeating",
    "data_copying": "copy-heavy work is adding avoidable churn",
    "async_blocking": "async or concurrent work is being blocked or spawned too aggressively",
    "control_flow_complexity": "deep branching is making the core path harder to optimize",
    "recursive_risk": "recursive work needs tighter caching or flattening",
    "repeated_compute": "the same expensive work is being recalculated",
    "network_roundtrips": "query or request fan-out is inflating roundtrips",
    "large_object_pressure": "large allocations or copies are amplified by nesting depth",
    "general_efficiency": "repeated efficiency pressure is visible across the repo",
}

LANE_DEFINITIONS = [
    {
        "key": "noise_cleanup_only",
        "title": "Noise Cleanup Only",
        "theme_prefix": "Noise-Only",
    },
    {
        "key": "device_memory_pressure",
        "title": "Device-Side Pressure",
        "theme_prefix": "Device-Side",
    },
    {
        "key": "mobile_app_efficiency",
        "title": "Mobile Update Pressure",
        "theme_prefix": "Mobile",
    },
    {
        "key": "cloud_control_path",
        "title": "Cloud Control Pressure",
        "theme_prefix": "Cloud Control",
    },
    {
        "key": "frontend_responsiveness",
        "title": "Frontend Responsiveness",
        "theme_prefix": "Frontend",
    },
    {
        "key": "pipeline_throughput_fixes",
        "title": "Pipeline Throughput Fixes",
        "theme_prefix": "Pipeline",
    },
    {
        "key": "service_entrypoint_review",
        "title": "Service Entrypoint Review",
        "theme_prefix": "Service Entrypoint",
    },
    {
        "key": "request_path_hotspots",
        "title": "Request-Path Hotspots",
        "theme_prefix": "Request-Path",
    },
    {
        "key": "command_dispatch_cleanup",
        "title": "Command Dispatch Cleanup",
        "theme_prefix": "Command Dispatch",
    },
    {
        "key": "startup_path_cleanup",
        "title": "Startup Path Cleanup",
        "theme_prefix": "Startup",
    },
    {
        "key": "dispatch_complexity_review",
        "title": "Dispatch Complexity Review",
        "theme_prefix": "Dispatch / Extension",
    },
    {
        "key": "general_efficiency_review",
        "title": "General Efficiency Review",
        "theme_prefix": "Repository-Wide",
    },
]

LANE_METADATA = {item["key"]: item for item in LANE_DEFINITIONS}

NOISE_TOKENS = {"tests", "test", "specs", "spec", "fixtures", "fixture", "examples", "example", "docs", "doc"}
DEVICE_TOKENS = {"firmware", "drivers", "driver", "hal", "mcu", "embedded", "sensor", "bootloader"}
MOBILE_TOKENS = {"android", "ios", "mobile", "reactnative", "react", "native", "poll", "polling"}
WEB_UI_TOKENS = {"frontend", "pages", "components", "ui", "render", "template", "templates"}
PIPELINE_TOKENS = {"pipeline", "pipelines", "etl", "batch", "job", "jobs", "worker", "workers"}
SERVICE_TOKENS = {"services", "service", "gateway", "cloud"}
REQUEST_TOKENS = {"api", "apis", "route", "routes", "handler", "handlers", "middleware", "schema", "schemas", "serializer", "serializers", "request"}
REQUEST_FUNCTION_TOKENS = {"handle", "request", "route", "dispatch", "serialize", "middleware", "controller"}
CLI_TOKENS = {"cli", "commands", "command", "bin"}
STARTUP_TOKENS = {"main", "boot", "start", "startup", "init", "setup", "load", "config", "bootstrap"}
LIBRARY_TOKENS = {"src", "core", "lib", "package", "extensions", "extension", "dispatch", "routing", "plugins", "middleware"}
WEB_UI_FUNCTION_TOKENS = {"render", "draw", "update", "paint", "hydrate"}
DEVICE_FUNCTION_TOKENS = {"tick", "sensor", "buffer", "read", "write", "loop", "poll"}
MOBILE_FUNCTION_TOKENS = {"render", "update", "poll", "refresh", "sync"}
PIPELINE_FUNCTION_TOKENS = {"run", "process", "drain", "batch", "pipeline", "worker", "queue", "ingest"}
DISPATCH_FUNCTION_TOKENS = {"dispatch", "register", "extend", "plugin", "middleware"}

ZONE_REASON_WEB_ROUTE = "web_route_path"
ZONE_REASON_WEBSITE_UI = "website_ui_path"
ZONE_REASON_CLI = "cli_surface_path"
ZONE_REASON_PIPELINE = "pipeline_execution_path"
ZONE_REASON_FIRMWARE = "firmware_path"
ZONE_REASON_SERVERLESS = "serverless_function_path"
ZONE_REASON_MOBILE = "mobile_platform_path"
ZONE_REASON_HYBRID_CLOUD = "hybrid_cloud_control_path"
ZONE_REASON_SERVICE_ROOT = "service_root_path"
ZONE_REASON_ENTRYPOINT = "entrypoint_file"

THEME_FILE_SCORE_CAP = 75
THEME_REPETITION_FUNCTION_WEIGHT = 3
THEME_REPETITION_FILE_WEIGHT = 4
THEME_CRITICAL_ZONE_BONUS = 6
THEME_ZONE_CONCENTRATION_WEIGHT = 2
THEME_ZONE_CONCENTRATION_CAP = 14
THEME_NOISE_PENALTY_WEIGHT = 7

THEME_PRIORITY_THRESHOLDS = (
    (120, "fix_first"),
    (70, "high_priority"),
    (30, "worth_reviewing"),
    (1, "watch"),
    (-10_000, "ignore_for_now"),
)


def build_project_synthesis(
    file_reports: list[FileReport],
    profile: ProjectProfile,
    summary: ProjectSummary,
    root: Path,
) -> SynthesisSummary:
    contributions = _collect_contributions(file_reports, profile, root)
    themes = _build_themes(contributions, profile)
    lanes = _build_action_lanes(themes)
    noise = _build_noise_diagnostic(file_reports, profile, summary, root)
    story = _build_repository_story(profile, themes, lanes, noise)
    brief = _build_maintainer_brief(themes, lanes, noise)
    return SynthesisSummary(
        dominant_themes=themes,
        action_lanes=lanes,
        noise_diagnostic=noise,
        repository_story=story,
        maintainer_brief=brief,
    )


def _collect_contributions(file_reports: list[FileReport], profile: ProjectProfile, root: Path) -> list[dict[str, Any]]:
    contributions: list[dict[str, Any]] = []
    root_resolved = root.resolve()
    for report in file_reports:
        relative_file = str(Path(report.file).resolve().relative_to(root_resolved))
        path_tokens = _path_tokens(Path(relative_file))
        zone = report.summary.zone or "supporting"
        zone_label = _dominant_zone_label(relative_file, profile, zone)
        for function in report.functions:
            if not function.patterns:
                continue
            function_tokens = _name_tokens(function.name)
            families = sorted(
                {
                    PATTERN_FAMILY_MAP.get(pattern.name, "general_efficiency")
                    for pattern in function.patterns
                }
            )
            lane_key = _derive_lane_key(profile, zone, path_tokens, function_tokens, report.zone_reasons)
            relevance_score = function.relevance.score if function.relevance is not None else 0
            priority_label = function.relevance.project_priority_label if function.relevance is not None else "watch"
            pattern_names = sorted({pattern.name for pattern in function.patterns})
            function_example = {
                "file": relative_file,
                "function": function.name,
                "line_start": function.line_start,
                "zone": zone,
                "relevance_score": relevance_score,
                "project_priority_label": priority_label,
                "cost_label": function.context.adjusted_label,
                "pattern_names": pattern_names,
                "pattern_families": families,
            }
            for family in families:
                contributions.append(
                    {
                        "theme_key": f"{lane_key}:{family}",
                        "lane_key": lane_key,
                        "family": family,
                        "file": relative_file,
                        "function": function.name,
                        "zone": zone,
                        "zone_label": zone_label,
                        "relevance_score": relevance_score,
                        "priority_label": priority_label,
                        "example": function_example,
                    }
                )
    return contributions


def _build_themes(contributions: list[dict[str, Any]], profile: ProjectProfile) -> list[InsightTheme]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in contributions:
        bucket = grouped.setdefault(
            item["theme_key"],
            {
                "lane_key": item["lane_key"],
                "family": item["family"],
                "file_scores": defaultdict(int),
                "files": set(),
                "functions": set(),
                "critical_zone_hits": 0,
                "noise_zone_hits": 0,
                "zone_labels": Counter(),
                "examples": [],
            },
        )
        bucket["file_scores"][item["file"]] += int(item["relevance_score"])
        bucket["files"].add(item["file"])
        bucket["functions"].add((item["file"], item["function"]))
        if item["zone"] == "critical":
            bucket["critical_zone_hits"] += 1
        if item["zone"] == "noise":
            bucket["noise_zone_hits"] += 1
        bucket["zone_labels"][item["zone_label"]] += 1
        bucket["examples"].append(item["example"])

    themes: list[InsightTheme] = []
    for theme_key, bucket in grouped.items():
        dominant_zone, dominant_zone_hits = _counter_top(bucket["zone_labels"], fallback="supporting")
        capped_file_score = sum(min(score, THEME_FILE_SCORE_CAP) for score in bucket["file_scores"].values())
        affected_functions = len(bucket["functions"])
        affected_files = len(bucket["files"])
        repetition_score = min(
            (affected_functions * THEME_REPETITION_FUNCTION_WEIGHT)
            + (max(affected_files - 1, 0) * THEME_REPETITION_FILE_WEIGHT),
            30,
        )
        critical_zone_bonus = min(bucket["critical_zone_hits"] * THEME_CRITICAL_ZONE_BONUS, 30)
        zone_concentration_bonus = min(dominant_zone_hits * THEME_ZONE_CONCENTRATION_WEIGHT, THEME_ZONE_CONCENTRATION_CAP)
        if dominant_zone in profile.critical_zones:
            zone_concentration_bonus += 4
        noise_penalty = min(bucket["noise_zone_hits"] * THEME_NOISE_PENALTY_WEIGHT, 28)
        total_score = capped_file_score + critical_zone_bonus + repetition_score + zone_concentration_bonus - noise_penalty
        title = _theme_title(bucket["lane_key"], bucket["family"])
        summary = _theme_summary(
            title=title,
            family=bucket["family"],
            profile=profile,
            dominant_zone=dominant_zone,
            affected_functions=affected_functions,
            affected_files=affected_files,
            noise_zone_hits=bucket["noise_zone_hits"],
        )
        priority_label = _theme_priority(total_score)
        representative_examples = _sorted_examples(bucket["examples"])[:3]
        themes.append(
            InsightTheme(
                key=theme_key,
                title=title,
                summary=summary,
                relevance_score=total_score,
                priority_label=priority_label,
                pattern_families=[bucket["family"]],
                representative_examples=representative_examples,
                affected_files=affected_files,
                affected_functions=affected_functions,
                critical_zone_hits=bucket["critical_zone_hits"],
                noise_zone_hits=bucket["noise_zone_hits"],
                dominant_zone=dominant_zone,
                repetition_score=repetition_score,
            )
        )

    themes.sort(
        key=lambda item: (
            item.relevance_score,
            item.affected_functions,
            item.affected_files,
            item.title,
        ),
        reverse=True,
    )
    return themes


def _build_action_lanes(themes: list[InsightTheme]) -> list[ActionLane]:
    grouped: dict[str, list[InsightTheme]] = defaultdict(list)
    for theme in themes:
        lane_key, _, _ = theme.key.partition(":")
        grouped[lane_key].append(theme)

    ranked_lanes = sorted(
        grouped.items(),
        key=lambda item: (
            sum(theme.relevance_score for theme in item[1]),
            max(theme.affected_functions for theme in item[1]),
            LANE_METADATA[item[0]]["title"],
        ),
        reverse=True,
    )

    lanes: list[ActionLane] = []
    for index, (lane_key, lane_themes) in enumerate(ranked_lanes, start=1):
        representative_targets = _merge_lane_targets(lane_themes)
        lead_theme = lane_themes[0]
        why_now = (
            f"{lead_theme.title} leads this lane with score {lead_theme.relevance_score} "
            f"and clusters in {lead_theme.dominant_zone} across {lead_theme.affected_functions} functions."
        )
        lanes.append(
            ActionLane(
                key=lane_key,
                title=LANE_METADATA[lane_key]["title"],
                why_now=why_now,
                recommended_order=index,
                related_theme_keys=[theme.key for theme in lane_themes],
                representative_targets=representative_targets,
            )
        )
    return lanes


def _build_noise_diagnostic(
    file_reports: list[FileReport],
    profile: ProjectProfile,
    summary: ProjectSummary,
    root: Path,
) -> NoiseDiagnostic:
    root_resolved = root.resolve()
    noise_counts: Counter[str] = Counter()
    for report in file_reports:
        relative_file = str(Path(report.file).resolve().relative_to(root_resolved))
        zone = report.summary.zone or "supporting"
        zone_label = _dominant_zone_label(relative_file, profile, zone)
        if zone == "noise" or zone_label in profile.noise_zones:
            noise_counts[zone_label] += sum(1 for function in report.functions if function.patterns)
    noise_ratio = round(summary.discounted_functions / max(summary.flagged_functions, 1), 2)
    dominant_noise_zones = [zone for zone, _ in noise_counts.most_common(3)] or list(profile.noise_zones[:3])
    if summary.discounted_functions == 0:
        note = "Noise stayed contained: no flagged functions were discounted after repo-aware weighting."
    elif profile.primary_profile == "test_heavy_repository" or noise_ratio >= 0.6:
        note = (
            "The repository is noise-heavy right now; most discounted findings cluster in "
            + (", ".join(dominant_noise_zones) if dominant_noise_zones else "test and example paths")
            + "."
        )
    elif noise_ratio >= 0.3:
        note = (
            "A meaningful share of follow-up is noise-adjacent, mainly in "
            + (", ".join(dominant_noise_zones) if dominant_noise_zones else "secondary paths")
            + "."
        )
    else:
        note = (
            "Noise exists but does not dominate; discounted findings mostly sit in "
            + (", ".join(dominant_noise_zones) if dominant_noise_zones else "side paths")
            + "."
        )
    return NoiseDiagnostic(
        discounted_functions=summary.discounted_functions,
        dominant_noise_zones=dominant_noise_zones,
        noise_ratio=noise_ratio,
        summary=note,
    )


def _build_repository_story(
    profile: ProjectProfile,
    themes: list[InsightTheme],
    lanes: list[ActionLane],
    noise: NoiseDiagnostic,
) -> str:
    profile_label = profile.primary_profile.replace("_", " ")
    if not themes:
        return f"This {profile_label} repository has no grouped hotspots after deterministic relevance weighting."

    top_theme = themes[0]
    lane = lanes[0].title if lanes else "General Efficiency Review"
    story = (
        f"This {profile_label} repository is mainly about {top_theme.title.lower()} in {top_theme.dominant_zone}. "
        f"The lead remediation lane is {lane.lower()}."
    )
    if len(themes) > 1:
        story += f" Secondary pressure comes from {themes[1].title.lower()}."
    if noise.discounted_functions > 0:
        story += f" {noise.summary}"
    return story


def _build_maintainer_brief(
    themes: list[InsightTheme],
    lanes: list[ActionLane],
    noise: NoiseDiagnostic,
) -> str:
    if not lanes:
        return "No Stage 3 action lanes were needed."

    first_lane = lanes[0]
    targets = ", ".join(
        f"{item['file']} -> {item['function']}()"
        for item in first_lane.representative_targets[:2]
    )
    brief = f"Start with {first_lane.title.lower()} by checking {targets or 'the highest-ranked targets'}."
    if len(lanes) > 1:
        brief += f" Then move to {lanes[1].title.lower()}."
    if noise.noise_ratio >= 0.5:
        brief += " Keep test and example churn deprioritized while you work the production path."
    elif themes:
        brief += f" The main repeated theme is {themes[0].pattern_families[0].replace('_', ' ')}."
    return brief


def _derive_lane_key(
    profile: ProjectProfile,
    zone: str,
    path_tokens: set[str],
    function_tokens: set[str],
    zone_reasons: list[str] | None = None,
) -> str:
    zone_reason_set = {reason.lower() for reason in (zone_reasons or [])}
    has_cloud_local = bool("cloud" in path_tokens or ZONE_REASON_HYBRID_CLOUD in zone_reason_set)
    has_device_local = bool(
        path_tokens & DEVICE_TOKENS
        or function_tokens & DEVICE_FUNCTION_TOKENS
        or ZONE_REASON_FIRMWARE in zone_reason_set
    )
    has_mobile_local = bool(
        path_tokens & MOBILE_TOKENS
        or function_tokens & MOBILE_FUNCTION_TOKENS
        or ZONE_REASON_MOBILE in zone_reason_set
    )
    has_ui_local = bool(
        path_tokens & WEB_UI_TOKENS
        or function_tokens & WEB_UI_FUNCTION_TOKENS
        or ZONE_REASON_WEBSITE_UI in zone_reason_set
    )
    has_pipeline_local = bool(
        path_tokens & PIPELINE_TOKENS
        or function_tokens & PIPELINE_FUNCTION_TOKENS
        or ZONE_REASON_PIPELINE in zone_reason_set
    )
    has_service_local = bool(path_tokens & SERVICE_TOKENS or ZONE_REASON_SERVICE_ROOT in zone_reason_set)
    has_cli_local = bool(path_tokens & CLI_TOKENS or ZONE_REASON_CLI in zone_reason_set)
    has_startup_local = bool(
        function_tokens & STARTUP_TOKENS
        or path_tokens & {"main", "app", "functions", "lambda", "lambdas"}
        or ZONE_REASON_ENTRYPOINT in zone_reason_set
        or ZONE_REASON_SERVERLESS in zone_reason_set
    )
    has_dispatch_local = bool(path_tokens & LIBRARY_TOKENS or function_tokens & DISPATCH_FUNCTION_TOKENS)
    has_request_local = bool(
        path_tokens & REQUEST_TOKENS
        or function_tokens & REQUEST_FUNCTION_TOKENS
        or ZONE_REASON_WEB_ROUTE in zone_reason_set
        or ZONE_REASON_HYBRID_CLOUD in zone_reason_set
    )

    if zone == "noise" or path_tokens & NOISE_TOKENS:
        return "noise_cleanup_only"
    if (
        profile.hybrid_shape == "device_firmware_cloud"
        and has_cloud_local
    ) or (has_cloud_local and {"http", "sdk"} & set(profile.surfaces)):
        return "cloud_control_path"
    if has_device_local and ("device" in profile.surfaces or path_tokens & DEVICE_TOKENS):
        return "device_memory_pressure"
    if has_mobile_local and ("mobile" in profile.surfaces or path_tokens & MOBILE_TOKENS):
        return "mobile_app_efficiency"
    if has_ui_local and ("web_ui" in profile.surfaces or path_tokens & WEB_UI_TOKENS):
        return "frontend_responsiveness"
    if has_pipeline_local and ("background_jobs" in profile.execution_models or path_tokens & PIPELINE_TOKENS):
        return "pipeline_throughput_fixes"
    if (
        profile.service_topology == "microservices"
        or ("distributed_services" in profile.execution_models and has_service_local)
    ) and has_service_local:
        return "service_entrypoint_review"
    if ("cli" in profile.surfaces or has_cli_local) and (
        function_tokens & (CLI_TOKENS | STARTUP_TOKENS) or has_cli_local
    ):
        return "command_dispatch_cleanup"
    if has_startup_local and function_tokens & STARTUP_TOKENS and (
        "serverless" in profile.execution_models
        or path_tokens & {"app", "main", "functions", "lambda", "lambdas"}
        or "cli" in profile.surfaces
    ):
        return "startup_path_cleanup"
    if (
        profile.primary_profile in {"framework_library", "sdk_library"}
        or "library" in profile.execution_models
    ) and has_dispatch_local:
        return "dispatch_complexity_review"
    if has_request_local and (
        "http" in profile.surfaces
        or "request_response" in profile.execution_models
        or ("serverless" in profile.execution_models and (ZONE_REASON_SERVERLESS in zone_reason_set or "functions" in path_tokens))
    ):
        return "request_path_hotspots"
    return "general_efficiency_review"


def _theme_title(lane_key: str, family: str) -> str:
    prefix = LANE_METADATA[lane_key]["theme_prefix"]
    family_title = PATTERN_FAMILY_TITLES.get(family, PATTERN_FAMILY_TITLES["general_efficiency"])
    return f"{prefix} {family_title}"


def _theme_summary(
    title: str,
    family: str,
    profile: ProjectProfile,
    dominant_zone: str,
    affected_functions: int,
    affected_files: int,
    noise_zone_hits: int,
) -> str:
    objective = (profile.primary_objectives or ["efficiency"])[0].replace("_", " ")
    summary = (
        f"{title} stands out because {PATTERN_FAMILY_SUMMARY.get(family, PATTERN_FAMILY_SUMMARY['general_efficiency'])}. "
        f"It is concentrated in {dominant_zone} across {affected_functions} functions in {affected_files} files, "
        f"which lines up with {objective} pressure for this repo."
    )
    if noise_zone_hits:
        summary += f" {noise_zone_hits} member findings still sit in discounted noise zones."
    return summary


def _theme_priority(score: int) -> str:
    for threshold, label in THEME_PRIORITY_THRESHOLDS:
        if score >= threshold:
            return label
    return "ignore_for_now"


def _merge_lane_targets(themes: list[InsightTheme]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for theme in themes:
        for example in theme.representative_examples:
            key = (example["file"], example["function"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(example)
    merged.sort(
        key=lambda item: (
            item["relevance_score"],
            item["project_priority_label"],
            item["file"],
            item["function"],
        ),
        reverse=True,
    )
    return merged[:3]


def _sorted_examples(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for example in examples:
        key = (example["file"], example["function"])
        current = deduped.get(key)
        if current is None or example["relevance_score"] > current["relevance_score"]:
            deduped[key] = example
    return sorted(
        deduped.values(),
        key=lambda item: (
            item["relevance_score"],
            item["project_priority_label"],
            item["file"],
            item["function"],
        ),
        reverse=True,
    )


def _dominant_zone_label(relative_file: str, profile: ProjectProfile, zone: str) -> str:
    path_tokens = _path_tokens(Path(relative_file))
    for zone_name in profile.critical_zones:
        if zone_name.lower() in path_tokens:
            return zone_name
    for zone_name in profile.noise_zones:
        if zone_name.lower() in path_tokens:
            return zone_name
    parts = Path(relative_file).parts
    if len(parts) > 1:
        return parts[0]
    return zone


def _counter_top(counter: Counter[str], fallback: str) -> tuple[str, int]:
    if not counter:
        return fallback, 0
    value, count = sorted(counter.items(), key=lambda item: (item[1], item[0]), reverse=True)[0]
    return value, count


def _path_tokens(path: Path) -> set[str]:
    tokens: set[str] = set()
    for part in path.parts:
        tokens.update(_split_tokens(part))
    return tokens


def _name_tokens(name: str) -> set[str]:
    return _split_tokens(name)


def _split_tokens(value: str) -> set[str]:
    normalized = value.replace("\\", "/").replace("-", "_").replace(".", "_").lower()
    return {token for token in normalized.replace("/", "_").split("_") if token}
