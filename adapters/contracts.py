"""Shared adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from adapters.providers import ParserRuntimeInfo


@dataclass
class SolvixNode:
    node_type: str
    line_number: int
    depth: int
    name: str | None = None
    children: list["SolvixNode"] = field(default_factory=list)
    node_id: str = ""
    parent_id: str | None = None


@dataclass
class SolvixFunction:
    name: str
    line_start: int
    line_end: int
    arguments: list[str]
    nodes: list[SolvixNode]
    language: str


@dataclass
class ParseResult:
    functions: list[SolvixFunction]
    runtime: ParserRuntimeInfo
