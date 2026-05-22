"""Deterministic Stage 2 relevance weighting.

The goal of this module is to explain why a finding matters in this specific
repository, not just how expensive the pattern looks in isolation.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from core.report import (
    FileReport,
    FileZoneClassification,
    FunctionReport,
    ProjectProfile,
    RelevanceFactor,
    RelevanceResult,
)

# Severity is the base signal. Higher raw pattern cost should still matter,
# but Stage 2 can later boost or discount it with project context.
SEVERITY_WEIGHTS = {
    "CHEAP": 0,
    "MODERATE": 14,
    "EXPENSIVE": 26,
    "CRITICAL": 40,
}

# File zones come from Stage 1. Critical zones are production-facing paths,
# supporting zones are neutral, and noise zones should usually sink.
ZONE_WEIGHTS = {
    "critical": 12,
    "supporting": 2,
    "noise": -18,
}

# Function context from the context analyzer maps directly into weighting.
CALL_FREQUENCY_WEIGHTS = {
    "in_loop": 12,
    "frequently": 8,
    "once": -6,
    "rarely": -10,
    "unknown": 0,
}

HOT_PATH_WEIGHT = 4

RELEVANCE_THRESHOLDS = (
    (60, "urgent", "fix_first"),
    (40, "high", "high_priority"),
    (20, "moderate", "worth_reviewing"),
    (8, "low", "watch"),
    (-10_000, "low", "ignore_for_now"),
)

OBJECTIVE_BOOSTS = {
    "request_overhead": {
        "pattern_names": {
            "nested_loop",
            "n_plus_one_query_pattern",
            "repeated_expensive_function_call",
            "string_concatenation_in_loop",
            "memory_allocation_in_loop",
            "data_copy_in_loop",
        },
        "path_tokens": {"api", "apis", "route", "routes", "handler", "handlers", "middleware", "schema", "schemas", "serializer", "serializers"},
        "function_tokens": {"route", "request", "handler", "dispatch", "serialize"},
        "surface_bonus": {"http": 3},
        "execution_bonus": {"request_response": 3},
        "base": 4,
    },
    "latency": {
        "pattern_names": {
            "nested_loop",
            "async_blocking_in_loop",
            "n_plus_one_query_pattern",
            "repeated_expensive_function_call",
        },
        "path_tokens": {"api", "routes", "handlers", "gateway", "service"},
        "function_tokens": {"handle", "dispatch", "process", "route"},
        "surface_bonus": {"http": 2, "device": 2},
        "execution_bonus": {"request_response": 2, "serverless": 2},
        "base": 3,
    },
    "startup_time": {
        "pattern_names": {
            "memory_allocation_in_loop",
            "data_copy_in_loop",
            "repeated_expensive_function_call",
        },
        "path_tokens": {"main", "app", "boot", "bootstrap", "startup", "init", "config", "load", "functions", "lambda"},
        "function_tokens": {"main", "boot", "start", "startup", "init", "setup", "load", "config"},
        "surface_bonus": {"cli": 2},
        "execution_bonus": {"serverless": 6},
        "base": 0,
    },
    "throughput": {
        "pattern_names": {
            "nested_loop",
            "memory_allocation_in_loop",
            "data_copy_in_loop",
            "large_object_in_deep_loop",
            "repeated_expensive_function_call",
            "string_concatenation_in_loop",
        },
        "path_tokens": {"pipeline", "pipelines", "job", "jobs", "worker", "workers", "etl", "batch"},
        "function_tokens": {"run", "process", "drain", "batch", "pipeline", "worker"},
        "surface_bonus": {},
        "execution_bonus": {"background_jobs": 5},
        "base": 4,
    },
    "memory_efficiency": {
        "pattern_names": {
            "memory_allocation_in_loop",
            "data_copy_in_loop",
            "large_object_in_deep_loop",
            "string_concatenation_in_loop",
        },
        "path_tokens": {"firmware", "drivers", "driver", "embedded", "device", "pipeline", "workers"},
        "function_tokens": {"alloc", "buffer", "copy", "render", "tick"},
        "surface_bonus": {"device": 4, "mobile": 2},
        "execution_bonus": {"background_jobs": 2},
        "base": 3,
    },
    "api_stability": {
        "pattern_names": {"deep_nesting", "repeated_expensive_function_call"},
        "path_tokens": {"src", "core", "lib", "package", "extensions", "blueprints", "dispatch", "routing"},
        "function_tokens": {"dispatch", "register", "extend", "route"},
        "surface_bonus": {"http": 2, "sdk": 2},
        "execution_bonus": {"library": 2},
        "base": 3,
    },
    "extension_stability": {
        "pattern_names": {"deep_nesting", "repeated_expensive_function_call"},
        "path_tokens": {"extensions", "blueprints", "plugins", "middleware", "dispatch", "routing"},
        "function_tokens": {"dispatch", "register", "extend", "middleware"},
        "surface_bonus": {"http": 1, "sdk": 2},
        "execution_bonus": {"library": 1},
        "base": 3,
    },
    "user_feedback": {
        "pattern_names": {
            "nested_loop",
            "async_blocking_in_loop",
            "repeated_expensive_function_call",
            "string_concatenation_in_loop",
        },
        "path_tokens": {"cli", "commands", "pages", "components", "frontend", "ui", "render"},
        "function_tokens": {"render", "draw", "update", "main", "command"},
        "surface_bonus": {"cli": 4, "web_ui": 4, "desktop": 3},
        "execution_bonus": {},
        "base": 2,
    },
    "battery_efficiency": {
        "pattern_names": {
            "nested_loop",
            "async_blocking_in_loop",
            "repeated_expensive_function_call",
            "memory_allocation_in_loop",
        },
        "path_tokens": {"android", "ios", "mobile", "device", "firmware", "poll", "polling"},
        "function_tokens": {"tick", "loop", "poll", "update", "render"},
        "surface_bonus": {"mobile": 4, "device": 4},
        "execution_bonus": {},
        "base": 2,
    },
    "network_efficiency": {
        "pattern_names": {"n_plus_one_query_pattern", "repeated_expensive_function_call"},
        "path_tokens": {"api", "client", "gateway", "cloud", "services"},
        "function_tokens": {"fetch", "request", "route", "dispatch"},
        "surface_bonus": {"http": 3, "mobile": 2},
        "execution_bonus": {"distributed_services": 2},
        "base": 2,
    },
    "serialization_efficiency": {
        "pattern_names": {
            "string_concatenation_in_loop",
            "data_copy_in_loop",
            "memory_allocation_in_loop",
        },
        "path_tokens": {"schema", "schemas", "serializer", "serializers", "json", "api"},
        "function_tokens": {"serialize", "encode", "decode", "marshal"},
        "surface_bonus": {"http": 2, "sdk": 2},
        "execution_bonus": {"request_response": 2},
        "base": 2,
    },
    "reliability": {
        "pattern_names": {"async_blocking_in_loop", "recursion_without_memoization"},
        "path_tokens": {"firmware", "drivers", "worker", "workers", "functions", "lambda"},
        "function_tokens": {"retry", "recover", "process", "handle"},
        "surface_bonus": {"device": 2},
        "execution_bonus": {"serverless": 2, "background_jobs": 2},
        "base": 2,
    },
    "device_constraints": {
        "pattern_names": {
            "memory_allocation_in_loop",
            "data_copy_in_loop",
            "large_object_in_deep_loop",
            "nested_loop",
        },
        "path_tokens": {"firmware", "drivers", "hal", "mcu", "embedded", "bootloader"},
        "function_tokens": {"read", "write", "tick", "loop", "sensor"},
        "surface_bonus": {"device": 5},
        "execution_bonus": {},
        "base": 4,
    },
    "feedback_speed": {
        "pattern_names": {"nested_loop", "repeated_expensive_function_call"},
        "path_tokens": {"tests", "specs", "fixtures"},
        "function_tokens": {"test", "spec"},
        "surface_bonus": {},
        "execution_bonus": {},
        "base": 1,
    },
    "test_reliability": {
        "pattern_names": {"async_blocking_in_loop", "recursion_without_memoization"},
        "path_tokens": {"tests", "specs", "fixtures"},
        "function_tokens": {"test", "spec"},
        "surface_bonus": {},
        "execution_bonus": {},
        "base": 1,
    },
    "maintainability": {
        "pattern_names": {"deep_nesting", "recursion_without_memoization"},
        "path_tokens": {"src", "core", "app", "lib"},
        "function_tokens": {"process", "handle", "run"},
        "surface_bonus": {},
        "execution_bonus": {},
        "base": 1,
    },
    "efficiency": {
        "pattern_names": {
            "nested_loop",
            "memory_allocation_in_loop",
            "data_copy_in_loop",
            "repeated_expensive_function_call",
        },
        "path_tokens": {"src", "core", "app", "lib"},
        "function_tokens": {"run", "process", "handle"},
        "surface_bonus": {},
        "execution_bonus": {},
        "base": 2,
    },
}

SURFACE_BOOSTS = {
    "http": {"path_tokens": {"api", "routes", "handlers", "middleware", "schemas", "serializers"}, "function_tokens": {"route", "request", "handler", "dispatch", "serialize"}, "weight": 5},
    "cli": {"path_tokens": {"cli", "commands", "bin"}, "function_tokens": {"main", "command", "run"}, "weight": 5},
    "web_ui": {"path_tokens": {"frontend", "pages", "components", "templates", "ui"}, "function_tokens": {"render", "draw", "update"}, "weight": 5},
    "device": {"path_tokens": {"firmware", "drivers", "hal", "mcu", "embedded"}, "function_tokens": {"tick", "loop", "read", "write", "sensor"}, "weight": 6},
    "mobile": {"path_tokens": {"android", "ios", "mobile"}, "function_tokens": {"render", "update", "poll"}, "weight": 5},
    "sdk": {"path_tokens": {"client", "sdk", "package", "lib"}, "function_tokens": {"client", "request", "serialize"}, "weight": 4},
    "desktop": {"path_tokens": {"desktop", "window", "ui"}, "function_tokens": {"render", "draw", "main"}, "weight": 4},
}

EXECUTION_MODEL_BOOSTS = {
    "request_response": {"path_tokens": {"api", "routes", "handlers", "middleware", "gateway"}, "function_tokens": {"route", "request", "handler", "dispatch"}, "weight": 5},
    "serverless": {"path_tokens": {"functions", "lambda", "lambdas"}, "function_tokens": {"main", "handler", "boot", "init"}, "weight": 7},
    "background_jobs": {"path_tokens": {"pipeline", "pipelines", "jobs", "workers", "etl"}, "function_tokens": {"run", "process", "drain", "worker"}, "weight": 6},
    "distributed_services": {"path_tokens": {"services", "gateway", "workers", "cloud"}, "function_tokens": {"route", "dispatch", "process", "handle"}, "weight": 5},
    "library": {"path_tokens": {"src", "core", "lib", "package"}, "function_tokens": {"dispatch", "register", "extend"}, "weight": 3},
    "monolith": {"path_tokens": {"app", "src", "main"}, "function_tokens": {"main", "run", "handle"}, "weight": 2},
}

NOISE_REASON_CODES = {
    "noise_directory",
}


def score_function_relevance(
    function_report: FunctionReport,
    file_path: str,
    zone_info: FileZoneClassification | None,
    profile: ProjectProfile,
) -> RelevanceResult:
    path = Path(file_path)
    file_tokens = _path_tokens(path)
    function_tokens = _name_tokens(function_report.name)
    pattern_names = {pattern.name for pattern in function_report.patterns}
    factors = [
        _severity_factor(function_report),
        _zone_factor(zone_info),
        _objective_factor(profile, pattern_names, file_tokens, function_tokens),
        _execution_factor(profile, file_tokens, function_tokens),
        _surface_factor(profile, file_tokens, function_tokens),
        _context_factor(function_report, profile, file_tokens, function_tokens),
        _noise_factor(zone_info, profile, file_tokens, function_tokens),
    ]
    score = sum(factor.weight for factor in factors)
    level, priority = _score_to_level(score)
    reason = _compose_reason(function_report, zone_info, profile, factors)
    return RelevanceResult(
        score=score,
        level=level,
        reason=reason,
        project_priority_label=priority,
        factors=factors,
    )


def summarize_file_relevance(file_report: FileReport) -> RelevanceResult | None:
    relevant_functions = [function.relevance for function in file_report.functions if function.relevance is not None]
    if not relevant_functions:
        return None
    top_result = max(relevant_functions, key=lambda item: item.score)
    level, priority = _score_to_level(top_result.score)
    return RelevanceResult(
        score=top_result.score,
        level=level,
        reason=f"Highest function relevance in this file is {top_result.score} ({top_result.project_priority_label}). {top_result.reason}",
        project_priority_label=priority,
        factors=list(top_result.factors),
    )


def attach_project_relevance(
    file_reports: list[FileReport],
    profile: ProjectProfile,
    root: Path,
) -> list[FileReport]:
    zone_lookup = {item.file: item for item in profile.zone_classification}
    updated_reports: list[FileReport] = []
    for report in file_reports:
        relative_path = str(Path(report.file).resolve().relative_to(root.resolve()))
        zone_info = zone_lookup.get(relative_path)
        updated_functions: list[FunctionReport] = []
        for function in report.functions:
            relevance = score_function_relevance(function, relative_path, zone_info, profile)
            updated_functions.append(replace(function, relevance=relevance))
        updated_summary = replace(report.summary)
        updated_report = replace(report, functions=updated_functions, summary=updated_summary)
        file_relevance = summarize_file_relevance(updated_report)
        if file_relevance is not None:
            updated_report = replace(updated_report, relevance=file_relevance)
            updated_report.summary.relevance_score = file_relevance.score
            updated_report.summary.relevance_level = file_relevance.level
            updated_report.summary.relevance_reason = file_relevance.reason
        updated_reports.append(updated_report)
    return updated_reports


def _severity_factor(function_report: FunctionReport) -> RelevanceFactor:
    label = function_report.cost.label
    weight = SEVERITY_WEIGHTS.get(label, 0)
    return RelevanceFactor(
        name="pattern_severity",
        weight=weight,
        direction=_direction(weight),
        reason=f"Raw pattern severity is {label.lower()}, which contributes {weight} points before context weighting.",
    )


def _zone_factor(zone_info: FileZoneClassification | None) -> RelevanceFactor:
    zone = zone_info.zone if zone_info is not None else "supporting"
    weight = ZONE_WEIGHTS.get(zone, 0)
    return RelevanceFactor(
        name="file_zone",
        weight=weight,
        direction=_direction(weight),
        reason=f"Stage 1 classified this file as {zone}, contributing {weight} points.",
    )


def _objective_factor(
    profile: ProjectProfile,
    pattern_names: set[str],
    file_tokens: set[str],
    function_tokens: set[str],
) -> RelevanceFactor:
    score = 0
    matched: list[str] = []
    objectives = list(dict.fromkeys(profile.primary_objectives + profile.secondary_objectives[:2]))
    for objective in objectives:
        rule = OBJECTIVE_BOOSTS.get(objective)
        if rule is None:
            continue
        objective_score = 0
        direct_match = False
        if pattern_names & rule["pattern_names"]:
            objective_score += int(rule["base"]) + 2
            direct_match = True
        if file_tokens & rule["path_tokens"]:
            objective_score += 2
            direct_match = True
        if function_tokens & rule["function_tokens"]:
            objective_score += 2
            direct_match = True
        if objective == "startup_time":
            startup_bonus = _startup_context_bonus(function_tokens)
            objective_score += startup_bonus
            direct_match = direct_match or startup_bonus > 0
        if objective == "battery_efficiency":
            battery_bonus = _battery_context_bonus(function_tokens)
            objective_score += battery_bonus
            direct_match = direct_match or battery_bonus > 0
        if direct_match:
            for surface, bonus in rule["surface_bonus"].items():
                if surface in profile.surfaces:
                    objective_score += bonus
            for model, bonus in rule["execution_bonus"].items():
                if model in profile.execution_models:
                    objective_score += bonus
        if objective_score > 0:
            matched.append(f"{objective}={objective_score}")
            score += min(objective_score, 10)
    return RelevanceFactor(
        name="project_objectives",
        weight=score,
        direction=_direction(score),
        reason=(
            "Objective fit matched "
            + (", ".join(matched) if matched else "no strong primary objective signals")
            + "."
        ),
    )


def _execution_factor(
    profile: ProjectProfile,
    file_tokens: set[str],
    function_tokens: set[str],
) -> RelevanceFactor:
    score = 0
    matched: list[str] = []
    for model in profile.execution_models:
        rule = EXECUTION_MODEL_BOOSTS.get(model)
        if rule is None:
            continue
        model_score = 0
        if file_tokens & rule["path_tokens"]:
            model_score += rule["weight"]
        if function_tokens & rule["function_tokens"]:
            model_score += 2
        if model == "serverless" and {"main", "handler", "init", "boot"} & function_tokens:
            model_score += 2
        if model_score > 0:
            matched.append(f"{model}={model_score}")
            score += min(model_score, 8)
    return RelevanceFactor(
        name="execution_model",
        weight=score,
        direction=_direction(score),
        reason=(
            "Execution model weighting matched "
            + (", ".join(matched) if matched else "no direct execution-model signal")
            + "."
        ),
    )


def _surface_factor(
    profile: ProjectProfile,
    file_tokens: set[str],
    function_tokens: set[str],
) -> RelevanceFactor:
    score = 0
    matched: list[str] = []
    for surface in profile.surfaces:
        rule = SURFACE_BOOSTS.get(surface)
        if rule is None:
            continue
        surface_score = 0
        if file_tokens & rule["path_tokens"]:
            surface_score += rule["weight"]
        if function_tokens & rule["function_tokens"]:
            surface_score += 2
        if surface_score > 0:
            matched.append(f"{surface}={surface_score}")
            score += min(surface_score, 7)
    return RelevanceFactor(
        name="surface_alignment",
        weight=score,
        direction=_direction(score),
        reason="Surface weighting matched " + (", ".join(matched) if matched else "no direct surface signal") + ".",
    )


def _context_factor(
    function_report: FunctionReport,
    profile: ProjectProfile,
    file_tokens: set[str],
    function_tokens: set[str],
) -> RelevanceFactor:
    context = function_report.context
    score = CALL_FREQUENCY_WEIGHTS.get(context.call_frequency, 0)
    if context.is_hot_path:
        score += HOT_PATH_WEIGHT
    if context.call_frequency == "once" and {"main", "boot", "init", "setup", "load"} & function_tokens:
        score += 1
    if (
        context.call_frequency == "once"
        and "serverless" in profile.execution_models
        and {"functions", "lambda", "lambdas"} & file_tokens
        and {"main", "boot", "handler", "init", "setup", "load"} & function_tokens
    ):
        score += 8
    if context.call_frequency == "rarely" and {"tests", "specs", "fixtures", "examples", "docs"} & file_tokens:
        score -= 3
    return RelevanceFactor(
        name="function_context",
        weight=score,
        direction=_direction(score),
        reason=(
            f"Function context is {context.call_frequency} with hot_path={context.is_hot_path}, "
            f"contributing {score} points."
        ),
    )


def _noise_factor(
    zone_info: FileZoneClassification | None,
    profile: ProjectProfile,
    file_tokens: set[str],
    function_tokens: set[str],
) -> RelevanceFactor:
    if zone_info is None:
        return RelevanceFactor(
            name="noise_discount",
            weight=0,
            direction="neutral",
            reason="No Stage 1 noise-zone match was present.",
        )

    score = 0
    reasons: list[str] = []
    if any(reason in NOISE_REASON_CODES for reason in zone_info.reasons):
        score -= 8
        reasons.append("noise directory")
    if file_tokens & {"tests", "test", "specs", "fixtures", "examples", "docs", "doc", "typing", "type_check"}:
        score -= 4
        reasons.append("noise-like path")
    if profile.primary_profile == "test_heavy_repository" and {"tests", "test", "specs"} & file_tokens:
        score += 2
        reasons.append("test-heavy repo partial recovery")
    if {"core", "src", "app", "api", "routes", "services", "firmware"} & file_tokens:
        score += 2
        reasons.append("production path recovery")
    if {"test", "spec"} & function_tokens:
        score -= 2
        reasons.append("test-like function")
    return RelevanceFactor(
        name="noise_discount",
        weight=score,
        direction=_direction(score),
        reason=(
            "Noise discount applied from "
            + (", ".join(reasons) if reasons else "no noise indicators")
            + "."
        ),
    )


def _score_to_level(score: int) -> tuple[str, str]:
    for threshold, level, priority in RELEVANCE_THRESHOLDS:
        if score >= threshold:
            return level, priority
    return "low", "ignore_for_now"


def _compose_reason(
    function_report: FunctionReport,
    zone_info: FileZoneClassification | None,
    profile: ProjectProfile,
    factors: list[RelevanceFactor],
) -> str:
    strongest = [factor for factor in factors if factor.weight != 0]
    strongest.sort(key=lambda item: abs(item.weight), reverse=True)
    leading = ", ".join(f"{factor.name}={factor.weight}" for factor in strongest[:3]) or "neutral weighting"
    zone = zone_info.zone if zone_info is not None else "supporting"
    return (
        f"{function_report.name}() ranks against a {profile.primary_profile.replace('_', ' ')} profile. "
        f"The file is in a {zone} zone. Strongest weighting: {leading}."
    )


def _startup_context_bonus(function_tokens: set[str]) -> int:
    if {"main", "boot", "start", "startup", "init", "setup", "load", "config"} & function_tokens:
        return 4
    return 0


def _battery_context_bonus(function_tokens: set[str]) -> int:
    if {"tick", "loop", "poll", "update", "render"} & function_tokens:
        return 3
    return 0


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


def _direction(weight: int) -> str:
    if weight > 0:
        return "boost"
    if weight < 0:
        return "discount"
    return "neutral"
