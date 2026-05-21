"""Pattern registry for Solvix."""

from __future__ import annotations

from adapters.contracts import SolvixFunction
from core.report import PatternMatch
from patterns.universal import run_universal_patterns


def collect_patterns(function: SolvixFunction) -> list[PatternMatch]:
    return run_universal_patterns(function)
