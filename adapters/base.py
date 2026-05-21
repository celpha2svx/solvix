"""Base adapter utilities for Solvix."""

from __future__ import annotations

from typing import Any

from adapters.contracts import ParseResult, SolvixFunction, SolvixNode
from adapters.fallback_parser import HeuristicFunctionParser
from adapters.providers import ParserRuntimeInfo, build_provider_chain, runtime_info_for_provider


class BaseAdapter:
    language = ""
    extensions: list[str] = []

    def parse(self, source_code: str) -> ParseResult:
        raise NotImplementedError


class TreeSitterAdapter(BaseAdapter):
    function_types: set[str] = set()
    loop_types: set[str] = set()
    branch_types: set[str] = set()
    function_name_field = "name"
    parameter_field = "parameters"
    memory_keywords: set[str] = set()
    string_concat_operators: set[str] = set()
    string_concat_methods: set[str] = set()
    call_node_types: set[str] = {"call_expression"}
    recursion_label = None
    n_plus_one_keywords: tuple[str, ...] = ()
    async_node_types: set[str] = set()
    data_copy_keywords: set[str] = set()
    allocation_node_types: set[str] = set()

    def parse(self, source_code: str) -> ParseResult:
        provider_errors: list[str] = []

        for provider in build_provider_chain():
            if not provider.is_available():
                provider_errors.append(provider.describe())
                continue

            try:
                parser = provider.get_parser(self.language)
                tree = parser.parse(source_code)
                root = self._tree_root_node(tree)
                functions: list[SolvixFunction] = []
                for node in self._children(root):
                    functions.extend(self._find_functions(node, source_code))
                return ParseResult(
                    functions=functions,
                    runtime=runtime_info_for_provider(provider),
                )
            except Exception as exc:
                recovered = False
                ensure_language = getattr(provider, "ensure_language", None)
                if callable(ensure_language):
                    try:
                        recovered = bool(ensure_language(self.language))
                    except Exception as bootstrap_exc:
                        provider_errors.append(
                            f"{provider.name} bootstrap failed for {self.language}: {bootstrap_exc}"
                        )
                if recovered:
                    try:
                        parser = provider.get_parser(self.language)
                        tree = parser.parse(source_code)
                        root = self._tree_root_node(tree)
                        functions = []
                        for node in self._children(root):
                            functions.extend(self._find_functions(node, source_code))
                        return ParseResult(
                            functions=functions,
                            runtime=runtime_info_for_provider(
                                provider,
                                note_override=(
                                    f"{provider.describe()} Auto-downloaded parser artifact for "
                                    f"{self.language} on first use."
                                ),
                            ),
                        )
                    except Exception as retry_exc:
                        provider_errors.append(
                            f"{provider.name} failed after auto-bootstrap: {retry_exc}"
                        )
                else:
                    provider_errors.append(f"{provider.name} failed at runtime: {exc}")

        note = (
            "No native tree-sitter provider completed successfully. "
            "Solvix is using the built-in heuristic fallback parser for non-Python languages."
        )
        if provider_errors:
            note = f"{note} Provider diagnostics: {' | '.join(provider_errors)}"
        return ParseResult(
            functions=self._fallback_parse(source_code),
            runtime=ParserRuntimeInfo(
                backend="heuristic-fallback",
                quality="degraded",
                degraded=True,
                note=note,
            ),
        )

    def _find_functions(self, node: Any, source_code: str) -> list[SolvixFunction]:
        results: list[SolvixFunction] = []
        if self._node_kind(node) in self.function_types:
            results.append(self._build_function(node, source_code))
        for child in self._children(node):
            results.extend(self._find_functions(child, source_code))
        return results

    def _build_function(self, node: Any, source_code: str) -> SolvixFunction:
        name_node = node.child_by_field_name(self.function_name_field)
        name = self._node_text(name_node, source_code) if name_node else "<anonymous>"
        param_node = node.child_by_field_name(self.parameter_field)
        arguments = self._extract_parameters(param_node, source_code)
        nodes: list[SolvixNode] = []
        body = node.child_by_field_name("body") or node
        self._walk(body, source_code, name, nodes, None, 0, {})
        return SolvixFunction(
            name=name,
            line_start=self._start_point(node)[0] + 1,
            line_end=self._end_point(node)[0] + 1,
            arguments=arguments,
            nodes=nodes,
            language=self.language,
        )

    def _walk(
        self,
        node: Any,
        source_code: str,
        function_name: str,
        nodes: list[SolvixNode],
        parent_id: str | None,
        depth: int,
        ancestor_flags: dict[str, bool],
    ) -> None:
        node_type = self._map_node_type(node, source_code, function_name, ancestor_flags)
        current_parent = parent_id
        new_depth = depth
        current_flags = dict(ancestor_flags)
        if node_type:
            node_id = f"{function_name}:{len(nodes)}:{self._start_point(node)[0] + 1}"
            solvix_node = SolvixNode(
                node_type=node_type,
                line_number=self._start_point(node)[0] + 1,
                depth=depth,
                name=self._symbol_name(node, source_code, node_type, function_name),
                node_id=node_id,
                parent_id=parent_id,
            )
            nodes.append(solvix_node)
            current_parent = node_id
            new_depth = depth + 1
            if parent_id:
                parent = next((entry for entry in nodes if entry.node_id == parent_id), None)
                if parent:
                    parent.children.append(solvix_node)
            if node_type in {"loop", "nested_loop"}:
                current_flags["inside_loop"] = True

        for child in self._children(node):
            self._walk(child, source_code, function_name, nodes, current_parent, new_depth, current_flags)

    def _map_node_type(self, node: Any, source_code: str, function_name: str, flags: dict[str, bool]) -> str | None:
        kind = self._node_kind(node)
        if kind in self.loop_types:
            return "nested_loop" if flags.get("inside_loop") else "loop"
        if kind in self.branch_types:
            return "branch"
        if kind in self.async_node_types:
            return "async_block"
        if kind in self.call_node_types:
            call_name = self._extract_call_name(node, source_code)
            if call_name in self.string_concat_methods:
                return "string_concat"
            if call_name in self.memory_keywords:
                return "memory_alloc"
            if any(keyword in call_name.lower() for keyword in self.n_plus_one_keywords):
                return "function_call"
            if call_name == function_name:
                return "recursion"
            if call_name in self.data_copy_keywords:
                return "data_copy"
            return "function_call"
        if kind in self.allocation_node_types:
            return "memory_alloc"
        if self._is_string_concat(node, source_code):
            return "string_concat"
        if self._is_data_copy(node, source_code):
            return "data_copy"
        return None

    def _symbol_name(self, node: Any, source_code: str, node_type: str, function_name: str) -> str | None:
        if node_type == "function_call":
            name = self._extract_call_name(node, source_code)
            if any(keyword in name.lower() for keyword in self.n_plus_one_keywords):
                return "N+1 Query Pattern"
            return name
        if node_type == "recursion":
            return function_name
        return None

    def _extract_call_name(self, node: Any, source_code: str) -> str:
        callee = node.child_by_field_name("function") or node.child_by_field_name("name")
        if callee is None:
            children = self._children(node)
            callee = children[0] if children else None
        if callee:
            text = self._node_text(callee, source_code)
        else:
            text = self._node_text(node, source_code)
        text = text.replace("::", ".")
        for token in ("(", ")", "{", "}", "[", "]"):
            text = text.replace(token, " ")
        return text.strip().split()[-1].split(".")[-1]

    def _extract_parameters(self, node: Any, source_code: str) -> list[str]:
        if not node:
            return []
        text = self._node_text(node, source_code).strip()
        text = text.strip("(){}")
        if not text:
            return []
        return [part.strip().split(":")[0].split()[-1] for part in text.split(",") if part.strip()]

    def _is_string_concat(self, node: Any, source_code: str) -> bool:
        text = self._node_text(node, source_code)
        return self._node_kind(node) in {"binary_expression", "additive_expression"} and any(op in text for op in self.string_concat_operators)

    def _is_data_copy(self, node: Any, source_code: str) -> bool:
        text = self._node_text(node, source_code)
        return any(keyword in text for keyword in self.data_copy_keywords)

    @staticmethod
    def _node_text(node: Any, source_code: str) -> str:
        if not node:
            return ""
        start_byte = getattr(node, "start_byte", 0)
        end_byte = getattr(node, "end_byte", 0)
        start_byte = start_byte() if callable(start_byte) else start_byte
        end_byte = end_byte() if callable(end_byte) else end_byte
        return source_code[start_byte:end_byte]

    @staticmethod
    def _tree_root_node(tree: Any) -> Any:
        root_node = getattr(tree, "root_node")
        return root_node() if callable(root_node) else root_node

    @staticmethod
    def _children(node: Any) -> list[Any]:
        children = getattr(node, "children", None)
        if children is not None:
            return list(children() if callable(children) else children)
        child_count = getattr(node, "child_count", 0)
        if callable(child_count):
            child_count = child_count()
        child = getattr(node, "child", None)
        if child is None:
            return []
        return [child(index) for index in range(child_count)]

    @staticmethod
    def _node_kind(node: Any) -> str:
        kind = getattr(node, "type", None)
        if kind is not None:
            return kind() if callable(kind) else kind
        kind = getattr(node, "kind", "")
        return kind() if callable(kind) else kind

    @staticmethod
    def _start_point(node: Any) -> tuple[int, int]:
        point = getattr(node, "start_point", None)
        if point is not None:
            point = point() if callable(point) else point
            if hasattr(point, "row") and hasattr(point, "column"):
                return (point.row, point.column)
            return (point[0], point[1])
        position = getattr(node, "start_position", (0, 0))
        position = position() if callable(position) else position
        if hasattr(position, "row") and hasattr(position, "column"):
            return (position.row, position.column)
        return (position[0], position[1])

    @staticmethod
    def _end_point(node: Any) -> tuple[int, int]:
        point = getattr(node, "end_point", None)
        if point is not None:
            point = point() if callable(point) else point
            if hasattr(point, "row") and hasattr(point, "column"):
                return (point.row, point.column)
            return (point[0], point[1])
        position = getattr(node, "end_position", (0, 0))
        position = position() if callable(position) else position
        if hasattr(position, "row") and hasattr(position, "column"):
            return (position.row, position.column)
        return (position[0], position[1])

    def _fallback_parse(self, source_code: str) -> list[SolvixFunction]:
        return HeuristicFunctionParser().parse(
            language=self.language,
            source_code=source_code,
            memory_keywords=self.memory_keywords,
            data_copy_keywords=self.data_copy_keywords,
            string_concat_operators=self.string_concat_operators,
            string_concat_methods=self.string_concat_methods,
            async_node_types=self.async_node_types,
            n_plus_one_keywords=self.n_plus_one_keywords,
        )


def is_binary_text(raw_bytes: bytes) -> bool:
    return b"\x00" in raw_bytes


def maybe_minified(source_code: str) -> bool:
    return any(len(line) > 500 for line in source_code.splitlines())


def maybe_generated(source_code: str) -> bool:
    lowered = source_code.lower()
    markers = ("auto-generated", "do not edit", "generated by")
    return any(marker in lowered for marker in markers)


def supported_extensions() -> str:
    return ".py .js .ts .java .c .cpp .rs .go .rb .php .swift .kt"
