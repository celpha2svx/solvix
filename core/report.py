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
class RelevanceFactor:
    name: str
    weight: int
    direction: str
    reason: str


@dataclass
class RelevanceResult:
    score: int
    level: str
    reason: str
    project_priority_label: str
    factors: list[RelevanceFactor] = field(default_factory=list)


@dataclass
class FunctionReport:
    name: str
    line_start: int
    line_end: int
    cost: CostSummary
    context: ContextResult
    patterns: list[PatternMatch] = field(default_factory=list)
    relevance: RelevanceResult | None = None


@dataclass
class FileSummary:
    file: str
    language: str
    total_functions: int
    cheap: int
    moderate: int
    expensive: int
    critical: int
    zone: str | None = None
    relevance_score: int | None = None
    relevance_level: str | None = None
    relevance_reason: str | None = None


@dataclass
class FileReport:
    file: str
    language: str
    parser: ParserInfo
    functions: list[FunctionReport]
    summary: FileSummary
    zone_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    relevance: RelevanceResult | None = None


@dataclass
class ProjectSummary:
    files_analyzed: int
    languages_found: list[str]
    total_functions: int
    clean_functions: int
    flagged_functions: int
    top_functions: list[dict[str, Any]]
    risk_level: str
    why_it_matters: str
    recommended_next_step: str
    prioritized_hotspots: list[dict[str, Any]] = field(default_factory=list)
    discounted_functions: int = 0


@dataclass
class InsightTheme:
    key: str
    title: str
    summary: str
    relevance_score: int
    priority_label: str
    pattern_families: list[str]
    representative_examples: list[dict[str, Any]]
    affected_files: int
    affected_functions: int
    critical_zone_hits: int
    noise_zone_hits: int
    dominant_zone: str
    repetition_score: int


@dataclass
class ActionLane:
    key: str
    title: str
    why_now: str
    recommended_order: int
    related_theme_keys: list[str]
    representative_targets: list[dict[str, Any]]


@dataclass
class NoiseDiagnostic:
    discounted_functions: int
    dominant_noise_zones: list[str]
    noise_ratio: float
    summary: str


@dataclass
class SynthesisSummary:
    dominant_themes: list[InsightTheme] = field(default_factory=list)
    action_lanes: list[ActionLane] = field(default_factory=list)
    noise_diagnostic: NoiseDiagnostic | None = None
    repository_story: str = ""
    maintainer_brief: str = ""


@dataclass
class LensFactor:
    name: str
    weight: int
    reason: str


@dataclass
class LensThemeView:
    theme_key: str
    title: str
    base_theme_score: int
    score: int
    priority_label: str
    reason: str
    factors: list[LensFactor] = field(default_factory=list)


@dataclass
class LensLaneView:
    lane_key: str
    title: str
    score: int
    reason: str
    related_theme_keys: list[str] = field(default_factory=list)


@dataclass
class LensReport:
    lens: str
    title: str
    summary: str
    top_themes: list[LensThemeView] = field(default_factory=list)
    top_lanes: list[LensLaneView] = field(default_factory=list)
    recommended_first_action: str = ""


@dataclass
class MultiLensSummary:
    default_lens: str
    default_lens_reason: str
    available_lenses: list[str] = field(default_factory=list)
    reports: list[LensReport] = field(default_factory=list)


@dataclass
class AIOverlayInputBudget:
    max_top_themes: int
    max_top_lanes: int
    max_top_hotspots: int
    max_examples_per_theme: int


@dataclass
class AIOverlayInput:
    project_profile: dict[str, Any]
    project_summary: dict[str, Any]
    synthesis_summary: dict[str, Any]
    default_lens: dict[str, Any]
    top_themes: list[dict[str, Any]] = field(default_factory=list)
    top_lanes: list[dict[str, Any]] = field(default_factory=list)
    top_hotspots: list[dict[str, Any]] = field(default_factory=list)
    noise_diagnostic: dict[str, Any] | None = None


@dataclass
class AIOverlayResult:
    mode: str
    model: str
    executive_summary: str
    maintainer_plan: list[str] = field(default_factory=list)
    lens_explanation: str = ""
    grounded_theme_keys: list[str] = field(default_factory=list)
    grounded_lane_keys: list[str] = field(default_factory=list)
    grounded_hotspots: list[dict[str, Any]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)


@dataclass
class AIOverlaySummary:
    enabled: bool
    mode: str
    status: str
    model: str | None
    provider: str | None
    input_budget: AIOverlayInputBudget
    input_payload: AIOverlayInput | None = None
    result: AIOverlayResult | None = None
    notes: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class DependencyEvidenceItem:
    marker: str
    manifest: str
    source: str


@dataclass
class ConfidenceFactor:
    name: str
    weight: int
    matched: bool
    evidence: str


@dataclass
class FileZoneClassification:
    file: str
    zone: str
    reasons: list[str]


@dataclass
class ProfileEvidence:
    dependency_markers: list[str]
    dependency_details: list[DependencyEvidenceItem]
    directory_markers: list[str]
    entrypoint_markers: list[str]
    language_markers: list[str]
    confidence_factors: list[ConfidenceFactor]


@dataclass
class ProjectProfile:
    primary_profile: str
    secondary_profiles: list[str]
    execution_models: list[str]
    surfaces: list[str]
    confidence: str
    confidence_score: int
    project_type: str
    primary_objectives: list[str]
    secondary_objectives: list[str]
    primary_languages: list[str]
    critical_zones: list[str]
    noise_zones: list[str]
    zone_classification: list[FileZoneClassification]
    detected_markers: list[str]
    evidence: ProfileEvidence
    explanation: str
    web_shape: str | None = None
    service_topology: str | None = None
    hybrid_shape: str | None = None


@dataclass
class ProjectReport:
    files: list[FileReport]
    summary: ProjectSummary
    profile: ProjectProfile
    synthesis: SynthesisSummary | None = None
    multi_lens: MultiLensSummary | None = None
    ai_overlay: AIOverlaySummary | None = None


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
