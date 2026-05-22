"""Main analysis engine for Solvix."""

from __future__ import annotations

import os
from pathlib import Path

from adapters.base import is_binary_text, maybe_generated, maybe_minified, supported_extensions
from adapters.c_adapter import CAdapter
from adapters.cpp_adapter import CppAdapter
from adapters.go_adapter import GoAdapter
from adapters.java_adapter import JavaAdapter
from adapters.javascript_adapter import JavaScriptAdapter
from adapters.kotlin_adapter import KotlinAdapter
from adapters.php_adapter import PHPAdapter
from adapters.python_adapter import PythonAdapter
from adapters.ruby_adapter import RubyAdapter
from adapters.rust_adapter import RustAdapter
from adapters.swift_adapter import SwiftAdapter
from adapters.typescript_adapter import TypeScriptAdapter
from context.context_analyzer import analyze_context
from core.ai_overlay import AI_OVERLAY_MODE_OFF, run_ai_overlay
from core.cost_estimator import build_cost_summary
from core.language_detector import SUPPORTED_LABEL, detect_language
from core.multi_lens_engine import build_multi_lens_summary
from core.project_profiler import profile_project
from core.report import FileReport, FileSummary, FunctionReport, ParserInfo, ProjectReport, ProjectSummary
from core.relevance_engine import attach_project_relevance
from core.synthesis_engine import build_project_synthesis
from patterns.pattern_registry import collect_patterns

ADAPTERS = {
    "python": PythonAdapter(),
    "javascript": JavaScriptAdapter(),
    "typescript": TypeScriptAdapter(),
    "java": JavaAdapter(),
    "c": CAdapter(),
    "cpp": CppAdapter(),
    "rust": RustAdapter(),
    "go": GoAdapter(),
    "ruby": RubyAdapter(),
    "php": PHPAdapter(),
    "swift": SwiftAdapter(),
    "kotlin": KotlinAdapter(),
}

PROJECT_SKIP_MESSAGES = (
    "No functions found in",
    " is empty. Nothing to analyze.",
    "This file appears to be binary.",
)


class AnalysisError(Exception):
    """Raised when analysis fails in a user-visible way."""


def analyze_path(
    target: Path,
    function_name: str | None = None,
    project_mode: bool = False,
    forced_language: str | None = None,
    progress_callback=None,
    ai_mode: str = AI_OVERLAY_MODE_OFF,
    ai_model: str | None = None,
    ai_provider=None,
    status_callback=None,
):
    if project_mode:
        return _analyze_project(
            target,
            forced_language,
            progress_callback,
            ai_mode=ai_mode,
            ai_model=ai_model,
            ai_provider=ai_provider,
            status_callback=status_callback,
        )
    if ai_mode != AI_OVERLAY_MODE_OFF:
        raise AnalysisError(
            "Solvix: Stage 5 AI overlay currently requires --project because it depends on project intelligence stages 1-4."
        )
    return _analyze_file(target, function_name, forced_language)


def _analyze_project(
    target: Path,
    forced_language: str | None,
    progress_callback=None,
    *,
    ai_mode: str = AI_OVERLAY_MODE_OFF,
    ai_model: str | None = None,
    ai_provider=None,
    status_callback=None,
) -> ProjectReport:
    if not target.exists():
        raise AnalysisError(f"Solvix: Cannot find file at {target}. Check the path and try again.")
    if not target.is_dir():
        raise AnalysisError("Solvix: --project requires a folder path.")

    _emit_status(status_callback, "Discovering source files")
    files = []
    for root, _, filenames in os.walk(target):
        for filename in filenames:
            path = Path(root) / filename
            language = forced_language or detect_language(path)
            if language in ADAPTERS:
                files.append(path)

    if not files:
        raise AnalysisError(f"Solvix: No supported source files found in {target}. Supported: {supported_extensions()}")

    _emit_status(status_callback, "Profiling repository")
    profile = profile_project(target, files)
    zone_lookup = {item.file: item for item in profile.zone_classification}

    _emit_status(status_callback, "Scoring functions")
    file_reports: list[FileReport] = []
    skipped_files = 0
    total_files = len(files)
    for index, path in enumerate(files, start=1):
        try:
            report = _analyze_file(path, None, forced_language)
        except AnalysisError as exc:
            message = str(exc)
            if any(fragment in message for fragment in PROJECT_SKIP_MESSAGES):
                skipped_files += 1
                if progress_callback is not None:
                    progress_callback(index, total_files, path)
                continue
            raise
        relative_path = str(path.resolve().relative_to(target.resolve()))
        zone_info = zone_lookup.get(relative_path)
        if zone_info is not None:
            report.summary.zone = zone_info.zone
            report.zone_reasons = zone_info.reasons
        file_reports.append(report)
        if progress_callback is not None:
            progress_callback(index, total_files, path)

    if not file_reports:
        if skipped_files:
            raise AnalysisError(
                "Solvix: Supported source files were found, but none contained analyzable functions."
            )
        raise AnalysisError(f"Solvix: No supported source files found in {target}. Supported: {supported_extensions()}")
    file_reports = attach_project_relevance(file_reports, profile, target)
    prioritized_hotspots = sorted(
        (
            {
                "label": function.context.adjusted_label,
                "file": report.file,
                "function": function.name,
                "relevance_score": function.relevance.score if function.relevance is not None else None,
                "relevance_level": function.relevance.level if function.relevance is not None else None,
                "project_priority_label": (
                    function.relevance.project_priority_label if function.relevance is not None else None
                ),
                "relevance_reason": function.relevance.reason if function.relevance is not None else None,
                "zone": report.summary.zone,
            }
            for report in file_reports
            for function in report.functions
        ),
        key=lambda item: (
            item["relevance_score"] if item["relevance_score"] is not None else -1,
            ["CHEAP", "MODERATE", "EXPENSIVE", "CRITICAL"].index(item["label"]),
        ),
        reverse=True,
    )[:10]
    total_functions = sum(report.summary.total_functions for report in file_reports)
    flagged_functions = sum(
        report.summary.moderate + report.summary.expensive + report.summary.critical
        for report in file_reports
    )
    discounted_functions = sum(
        1
        for report in file_reports
        for function in report.functions
        if function.relevance is not None and function.relevance.project_priority_label == "ignore_for_now"
    )
    risk_level = _project_risk_level(total_functions, flagged_functions)
    summary = ProjectSummary(
        files_analyzed=len(file_reports),
        languages_found=sorted({report.language.title() for report in file_reports}),
        total_functions=total_functions,
        clean_functions=sum(report.summary.cheap for report in file_reports),
        flagged_functions=flagged_functions,
        top_functions=prioritized_hotspots,
        risk_level=risk_level,
        why_it_matters=_project_why_it_matters(flagged_functions, total_functions, prioritized_hotspots),
        recommended_next_step=_project_next_step(prioritized_hotspots, flagged_functions),
        prioritized_hotspots=prioritized_hotspots,
        discounted_functions=discounted_functions,
    )
    _emit_status(status_callback, "Synthesizing project themes")
    synthesis = build_project_synthesis(file_reports, profile, summary, target)
    _emit_status(status_callback, "Preparing multi-lens views")
    multi_lens = build_multi_lens_summary(profile, synthesis)
    try:
        if (ai_mode or "").strip().lower() != AI_OVERLAY_MODE_OFF:
            _emit_status(status_callback, "Generating AI overlay")
        ai_overlay = run_ai_overlay(
            profile,
            summary,
            synthesis,
            multi_lens,
            mode=ai_mode,
            model=ai_model,
            provider=ai_provider,
            status_callback=status_callback,
        )
    except Exception as exc:
        raise AnalysisError(f"Solvix: Failed to initialize Stage 5 AI overlay. {exc}") from exc
    return ProjectReport(
        files=file_reports,
        summary=summary,
        profile=profile,
        synthesis=synthesis,
        multi_lens=multi_lens,
        ai_overlay=ai_overlay,
    )


def _analyze_file(target: Path, function_name: str | None, forced_language: str | None) -> FileReport:
    if not target.exists():
        raise AnalysisError(f"Solvix: Cannot find file at {target}. Check the path and try again.")
    if target.is_dir():
        raise AnalysisError("Solvix: analyze expects a file path unless --project is used.")

    try:
        raw_bytes = target.read_bytes()
    except PermissionError as exc:
        raise AnalysisError(f"Solvix: Cannot read {target.name}. Check file permissions.") from exc

    if is_binary_text(raw_bytes):
        raise AnalysisError("Solvix: This file appears to be binary. Solvix analyzes source code only.")

    source_code = raw_bytes.decode("utf-8")
    if not source_code.strip():
        raise AnalysisError(f"Solvix: {target.name} is empty. Nothing to analyze.")

    language = forced_language or detect_language(target, source_code)
    if language == "unsupported" or language not in ADAPTERS:
        raise AnalysisError(f"Solvix: {target.suffix or target.name} is not yet supported. Current languages: {SUPPORTED_LABEL}")

    warnings: list[str] = []
    if maybe_minified(source_code):
        warnings.append("Solvix: This file appears to be minified. Solvix works best on readable source code. Consider analyzing the unminified version.")
    if maybe_generated(source_code):
        warnings.append("Solvix: This file appears to be auto-generated. Analysis may not reflect developer-written patterns.")

    adapter = ADAPTERS[language]
    try:
        parse_result = adapter.parse(source_code)
    except SyntaxError as exc:
        line_number = getattr(exc, "lineno", "?")
        raise AnalysisError(f"Solvix: {target.name} has a syntax error at line {line_number}. Fix the syntax and run again.") from exc
    except Exception as exc:
        raise AnalysisError(f"Solvix: Analysis failed for {target.name}. {exc}") from exc

    functions = parse_result.functions

    if not functions:
        raise AnalysisError(f"Solvix: No functions found in {target.name}. Solvix analyzes at the function level.")

    if parse_result.runtime.degraded:
        warnings.append(f"Solvix: Parser backend is running in degraded mode. {parse_result.runtime.note}")

    if function_name:
        functions = [function for function in functions if function.name == function_name]
        if not functions:
            raise AnalysisError(f"Solvix: Function '{function_name}' not found in {target.name}. Run 'solvix analyze {target}' to see all detected functions.")

    function_reports: list[FunctionReport] = []
    for function in functions:
        patterns = collect_patterns(function)
        cost = build_cost_summary(patterns)
        context = analyze_context(function, source_code, target, cost.label)
        function_reports.append(
            FunctionReport(
                name=function.name,
                line_start=function.line_start,
                line_end=function.line_end,
                cost=cost,
                context=context,
                patterns=patterns,
            )
        )

    summary = _build_summary(target, language, function_reports)
    return FileReport(
        file=str(target),
        language=language,
        parser=ParserInfo(
            backend=parse_result.runtime.backend,
            quality=parse_result.runtime.quality,
            degraded=parse_result.runtime.degraded,
            note=parse_result.runtime.note,
        ),
        functions=function_reports,
        summary=summary,
        warnings=warnings,
    )


def _emit_status(status_callback, message: str) -> None:
    if status_callback is not None:
        status_callback(message)


def _build_summary(target: Path, language: str, function_reports: list[FunctionReport]) -> FileSummary:
    counts = {"CHEAP": 0, "MODERATE": 0, "EXPENSIVE": 0, "CRITICAL": 0}
    for report in function_reports:
        counts[report.context.adjusted_label] += 1
    return FileSummary(
        file=str(target),
        language=language,
        total_functions=len(function_reports),
        cheap=counts["CHEAP"],
        moderate=counts["MODERATE"],
        expensive=counts["EXPENSIVE"],
        critical=counts["CRITICAL"],
    )


def _project_risk_level(total_functions: int, flagged_functions: int) -> str:
    if flagged_functions == 0:
        return "LOW"
    ratio = flagged_functions / max(total_functions, 1)
    if ratio >= 0.3:
        return "HIGH"
    if ratio >= 0.1:
        return "MODERATE"
    return "LOW"


def _project_why_it_matters(
    flagged_functions: int,
    total_functions: int,
    top_functions: list[dict[str, str]],
) -> str:
    if flagged_functions == 0:
        return "No flagged functions were found. This codebase looks inexpensive at the function-pattern level."
    if top_functions:
        hottest = top_functions[0]
        return (
            f"{flagged_functions} of {total_functions} functions were flagged. "
            f"The highest-priority hotspot right now is {hottest['function']}() in {hottest['file']} "
            f"with relevance {hottest.get('relevance_score', 'n/a')} ({hottest.get('project_priority_label', 'watch')})."
        )
    return f"{flagged_functions} of {total_functions} functions were flagged for follow-up."


def _project_next_step(top_functions: list[dict[str, str]], flagged_functions: int) -> str:
    if flagged_functions == 0:
        return "Spot-check a few core request or data-processing paths to confirm the cheap classification matches real behavior."
    if top_functions:
        hottest = top_functions[0]
        return (
            f"Start with {hottest['function']}() in {hottest['file']} because its repo-aware relevance ranked it first, "
            f"then move through the remaining prioritized hotspots."
        )
    return "Start with the flagged functions in the project summary and verify whether they sit on request, loop, or startup paths."
