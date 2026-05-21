"""Shared report contracts for Solvix."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PatternMatch:
    name: str
    severity: str
    line: int
    explanation: str
    suggestion: str
    label: str | None = None


@dataclass
class CostSummary:
    score: int
    label: str
    dominant_severity: str
    pattern_count: int
    top_pattern: PatternMatch | None


@dataclass
class ContextResult:
    is_hot_path: bool
    call_frequency: str
    context_note: str
    urgency_modifier: str
    adjusted_label: str


@dataclass
class ParserInfo:
    backend: str
    quality: str
    degraded: bool
    note: str


@dataclass
class FunctionReport:
    name: str
    line_start: int
    line_end: int
    cost: CostSummary
    context: ContextResult
    patterns: list[PatternMatch] = field(default_factory=list)


@dataclass
class FileSummary:
    file: str
    language: str
    total_functions: int
    cheap: int
    moderate: int
    expensive: int
    critical: int


@dataclass
class FileReport:
    file: str
    language: str
    parser: ParserInfo
    functions: list[FunctionReport]
    summary: FileSummary
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProjectSummary:
    files_analyzed: int
    languages_found: list[str]
    total_functions: int
    clean_functions: int
    flagged_functions: int
    top_functions: list[dict[str, Any]]


@dataclass
class ProjectReport:
    files: list[FileReport]
    summary: ProjectSummary


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_dict(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "__dataclass_fields__"):
        return {key: to_dict(value) for key, value in asdict(obj).items()}
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: to_dict(value) for key, value in obj.items()}
    return obj
