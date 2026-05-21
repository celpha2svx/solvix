"""Cost estimation for Solvix."""

from __future__ import annotations

from core.report import CostSummary, PatternMatch

SEVERITY_WEIGHTS = {"LOW": 1, "MEDIUM": 3, "HIGH": 7, "CRITICAL": 15}
LABEL_ORDER = ["CHEAP", "MODERATE", "EXPENSIVE", "CRITICAL"]


def score_to_label(score: int) -> str:
    if score == 0:
        return "CHEAP"
    if 1 <= score <= 3:
        return "MODERATE"
    if 4 <= score <= 10:
        return "EXPENSIVE"
    return "CRITICAL"


def adjust_label(label: str, modifier: str) -> str:
    index = LABEL_ORDER.index(label)
    if modifier == "upgrade":
        return LABEL_ORDER[min(index + 1, len(LABEL_ORDER) - 1)]
    if modifier == "downgrade":
        return LABEL_ORDER[max(index - 1, 0)]
    return label


def build_cost_summary(patterns: list[PatternMatch]) -> CostSummary:
    score = sum(SEVERITY_WEIGHTS.get(pattern.severity, 0) for pattern in patterns)
    label = score_to_label(score)
    top_pattern = max(patterns, key=lambda item: SEVERITY_WEIGHTS.get(item.severity, 0), default=None)
    dominant_severity = top_pattern.severity if top_pattern else "LOW"
    return CostSummary(
        score=score,
        label=label,
        dominant_severity=dominant_severity,
        pattern_count=len(patterns),
        top_pattern=top_pattern,
    )
