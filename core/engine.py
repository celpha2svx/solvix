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
from core.cost_estimator import build_cost_summary
from core.language_detector import SUPPORTED_LABEL, detect_language
from core.report import FileReport, FileSummary, FunctionReport, ParserInfo, ProjectReport, ProjectSummary
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


class AnalysisError(Exception):
    """Raised when analysis fails in a user-visible way."""


def analyze_path(target: Path, function_name: str | None = None, project_mode: bool = False, forced_language: str | None = None):
    if project_mode:
        return _analyze_project(target, forced_language)
    return _analyze_file(target, function_name, forced_language)


def _analyze_project(target: Path, forced_language: str | None) -> ProjectReport:
    if not target.exists():
        raise AnalysisError(f"Solvix: Cannot find file at {target}. Check the path and try again.")
    if not target.is_dir():
        raise AnalysisError("Solvix: --project requires a folder path.")

    files = []
    for root, _, filenames in os.walk(target):
        for filename in filenames:
            path = Path(root) / filename
            language = forced_language or detect_language(path)
            if language in ADAPTERS:
                files.append(path)

    if not files:
        raise AnalysisError(f"Solvix: No supported source files found in {target}. Supported: {supported_extensions()}")

    file_reports = [_analyze_file(path, None, forced_language) for path in files]
    top_functions = sorted(
        (
            {
                "label": function.context.adjusted_label,
                "file": report.file,
                "function": function.name,
            }
            for report in file_reports
            for function in report.functions
        ),
        key=lambda item: ["CHEAP", "MODERATE", "EXPENSIVE", "CRITICAL"].index(item["label"]),
        reverse=True,
    )[:10]
    total_functions = sum(report.summary.total_functions for report in file_reports)
    flagged_functions = sum(
        report.summary.moderate + report.summary.expensive + report.summary.critical
        for report in file_reports
    )
    summary = ProjectSummary(
        files_analyzed=len(file_reports),
        languages_found=sorted({report.language.title() for report in file_reports}),
        total_functions=total_functions,
        clean_functions=sum(report.summary.cheap for report in file_reports),
        flagged_functions=flagged_functions,
        top_functions=top_functions,
    )
    return ProjectReport(files=file_reports, summary=summary)


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
