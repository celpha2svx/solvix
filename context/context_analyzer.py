"""Context-aware urgency adjustments."""

from __future__ import annotations

import re
from pathlib import Path

from adapters.contracts import SolvixFunction
from core.cost_estimator import adjust_label
from core.report import ContextResult

ONCE_KEYWORDS = ("init", "setup", "config", "load", "start", "boot", "once")
HOT_KEYWORDS = ("render", "draw", "update", "tick", "frame", "loop", "run", "process", "handle", "on_", "event")


def analyze_context(function: SolvixFunction, source_code: str, filepath: Path, base_label: str) -> ContextResult:
    name = function.name.lower()
    tokens = tuple(token for token in re.split(r"[^a-z0-9]+", name) if token)
    is_hot_path = False
    call_frequency = "unknown"
    note = "No strong usage context detected in this file."
    modifier = "neutral"

    if any(keyword in name for keyword in ONCE_KEYWORDS):
        call_frequency = "once"
        note = "This function name suggests startup or one-time execution."
        modifier = "downgrade"
    elif _is_called_inside_loop(function.name, source_code):
        call_frequency = "in_loop"
        is_hot_path = True
        note = f"This function is called inside a loop in {filepath.name}."
        modifier = "upgrade"
    elif any(_matches_hot_keyword(name, tokens, keyword) for keyword in HOT_KEYWORDS):
        call_frequency = "frequently"
        is_hot_path = True
        note = "This function name suggests a hot path or event-driven call site."
        modifier = "upgrade"
    elif name.startswith("test_") or name.endswith("_test"):
        call_frequency = "rarely"
        note = "This appears to be a test function."
        modifier = "downgrade"

    return ContextResult(
        is_hot_path=is_hot_path,
        call_frequency=call_frequency,
        context_note=note,
        urgency_modifier=modifier,
        adjusted_label=adjust_label(base_label, modifier),
    )


def _is_called_inside_loop(function_name: str, source_code: str) -> bool:
    lines = source_code.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if re.search(rf"\b{re.escape(function_name)}\s*\(", stripped):
            if re.search(r"^(def|function|func|fn)\b", stripped):
                continue
            window = "\n".join(lines[max(0, index - 4):index])
            if re.search(r"\b(for|while|foreach|each)\b", window):
                return True
    return False


def _matches_hot_keyword(name: str, tokens: tuple[str, ...], keyword: str) -> bool:
    if keyword == "on_":
        return name.startswith("on_")
    return keyword in tokens
