"""Python adapter using the built-in AST module."""

from __future__ import annotations

import ast

from adapters.base import BaseAdapter
from adapters.contracts import ParseResult, SolvixFunction, SolvixNode
from adapters.providers import ParserRuntimeInfo

MEMORY_KEYWORDS = {
    "append",
    "extend",
    "insert",
    "copy",
    "deepcopy",
    "list",
    "dict",
    "set",
    "array",
    "bytearray",
    "memoryview",
}
SYNC_BLOCKERS = {"sleep", "wait", "result", "join"}


class PythonAdapter(BaseAdapter):
    language = "python"
    extensions = [".py"]

    def parse(self, source_code: str) -> ParseResult:
        tree = ast.parse(source_code)
        visitor = _FunctionVisitor(source_code)
        visitor.visit(tree)
        return ParseResult(
            functions=visitor.functions,
            runtime=ParserRuntimeInfo(
                backend="python-ast",
                quality="native",
                degraded=False,
                note="Native parser backend via Python ast module.",
            ),
        )


class _FunctionVisitor(ast.NodeVisitor):
    def __init__(self, source_code: str) -> None:
        self.source_code = source_code
        self.functions: list[SolvixFunction] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(self._build_function(node, async_mode=False))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(self._build_function(node, async_mode=True))
        self.generic_visit(node)

    def _build_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, async_mode: bool) -> SolvixFunction:
        collector = _NodeCollector(node.name, async_mode)
        for child in node.body:
            collector.visit(child)
        return SolvixFunction(
            name=node.name,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            arguments=[arg.arg for arg in node.args.args],
            nodes=collector.nodes,
            language="python",
        )


class _NodeCollector(ast.NodeVisitor):
    def __init__(self, function_name: str, async_mode: bool) -> None:
        self.function_name = function_name
        self.async_mode = async_mode
        self.nodes: list[SolvixNode] = []
        self.parents: list[str] = []
        self.depth = 0

    def _push(self, node_type: str, lineno: int, name: str | None = None) -> str:
        node_id = f"{self.function_name}:{len(self.nodes)}:{lineno}"
        solvix_node = SolvixNode(
            node_type=node_type,
            line_number=lineno,
            depth=self.depth,
            name=name,
            node_id=node_id,
            parent_id=self.parents[-1] if self.parents else None,
        )
        self.nodes.append(solvix_node)
        if self.parents:
            parent = next((entry for entry in self.nodes if entry.node_id == self.parents[-1]), None)
            if parent:
                parent.children.append(solvix_node)
        return node_id

    def _with_parent(self, node_type: str, lineno: int, name: str | None, visit_children) -> None:
        node_id = self._push(node_type, lineno, name)
        self.parents.append(node_id)
        self.depth += 1
        visit_children()
        self.depth -= 1
        self.parents.pop()

    def visit_For(self, node: ast.For) -> None:
        label = "nested_loop" if any(entry.node_type in {"loop", "nested_loop"} for entry in self._active_nodes()) else "loop"
        self._with_parent(label, node.lineno, None, lambda: self.generic_visit(node))

    def visit_While(self, node: ast.While) -> None:
        label = "nested_loop" if any(entry.node_type in {"loop", "nested_loop"} for entry in self._active_nodes()) else "loop"
        self._with_parent(label, node.lineno, None, lambda: self.generic_visit(node))

    def visit_If(self, node: ast.If) -> None:
        self._with_parent("branch", node.lineno, None, lambda: self.generic_visit(node))

    def visit_Try(self, node: ast.Try) -> None:
        self._with_parent("branch", node.lineno, None, lambda: self.generic_visit(node))

    def visit_With(self, node: ast.With) -> None:
        self._with_parent("branch", node.lineno, None, lambda: self.generic_visit(node))

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node)
        if name in MEMORY_KEYWORDS:
            self._push("memory_alloc", node.lineno, name)
        elif name == self.function_name:
            self._push("recursion", node.lineno, name)
        else:
            self._push("function_call", node.lineno, name)
            if self.async_mode and name in SYNC_BLOCKERS:
                self._push("async_block", node.lineno, name)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Add):
            self._push("string_concat", node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        value = node.value
        if isinstance(value, ast.Subscript):
            self._push("data_copy", node.lineno)
        elif isinstance(value, ast.Call) and self._call_name(value) in {"copy", "deepcopy", "list", "dict", "set"}:
            self._push("data_copy", node.lineno)
        self.generic_visit(node)

    def _call_name(self, node: ast.Call) -> str:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return "call"

    def _active_nodes(self) -> list[SolvixNode]:
        active_ids = set(self.parents)
        return [node for node in self.nodes if node.node_id in active_ids]
