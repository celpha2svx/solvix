"""Heuristic fallback parser used only when native parser providers are unavailable."""

from __future__ import annotations

import re

from adapters.contracts import SolvixFunction, SolvixNode


class HeuristicFunctionParser:
    """Best-effort parser for environments without native tree-sitter support."""

    def parse(self, language: str, source_code: str, memory_keywords: set[str], data_copy_keywords: set[str], string_concat_operators: set[str], string_concat_methods: set[str], async_node_types: set[str], n_plus_one_keywords: tuple[str, ...]) -> list[SolvixFunction]:
        if language == "ruby":
            return self._parse_ruby(language, source_code, memory_keywords, data_copy_keywords, string_concat_operators, string_concat_methods, async_node_types, n_plus_one_keywords)
        return self._parse_braces(language, source_code, memory_keywords, data_copy_keywords, string_concat_operators, string_concat_methods, async_node_types, n_plus_one_keywords)

    def _parse_braces(self, language: str, source_code: str, memory_keywords: set[str], data_copy_keywords: set[str], string_concat_operators: set[str], string_concat_methods: set[str], async_node_types: set[str], n_plus_one_keywords: tuple[str, ...]) -> list[SolvixFunction]:
        lines = source_code.splitlines()
        functions: list[SolvixFunction] = []
        index = 0
        while index < len(lines):
            match = self._match_brace_function(lines[index])
            if not match:
                index += 1
                continue

            name, arguments = match
            start = index
            brace_balance = lines[index].count("{") - lines[index].count("}")
            body_lines = [lines[index]]
            index += 1
            while index < len(lines):
                body_lines.append(lines[index])
                brace_balance += lines[index].count("{") - lines[index].count("}")
                if brace_balance <= 0:
                    break
                index += 1

            nodes = self._scan_lines_for_nodes(
                body_lines=body_lines[1:],
                function_name=name,
                start_line=start + 2,
                memory_keywords=memory_keywords,
                data_copy_keywords=data_copy_keywords,
                string_concat_operators=string_concat_operators,
                string_concat_methods=string_concat_methods,
                async_node_types=async_node_types,
                n_plus_one_keywords=n_plus_one_keywords,
            )
            functions.append(
                SolvixFunction(
                    name=name,
                    line_start=start + 1,
                    line_end=min(index + 1, len(lines)),
                    arguments=arguments,
                    nodes=nodes,
                    language=language,
                )
            )
            index += 1
        return functions

    def _parse_ruby(self, language: str, source_code: str, memory_keywords: set[str], data_copy_keywords: set[str], string_concat_operators: set[str], string_concat_methods: set[str], async_node_types: set[str], n_plus_one_keywords: tuple[str, ...]) -> list[SolvixFunction]:
        lines = source_code.splitlines()
        functions: list[SolvixFunction] = []
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line.startswith("def "):
                index += 1
                continue

            signature = line[4:]
            name = signature.split("(")[0].strip()
            args_text = signature.split("(", 1)[1].rsplit(")", 1)[0] if "(" in signature else ""
            arguments = [arg.strip() for arg in args_text.split(",") if arg.strip()]
            start = index
            depth = 1
            body_lines = [lines[index]]
            index += 1
            while index < len(lines):
                current = lines[index].strip()
                body_lines.append(lines[index])
                if current.startswith(("def ", "if ", "while ", "for ")) or ".each" in current:
                    depth += 1
                if current == "end":
                    depth -= 1
                    if depth == 0:
                        break
                index += 1

            nodes = self._scan_lines_for_nodes(
                body_lines=body_lines[1:],
                function_name=name,
                start_line=start + 2,
                memory_keywords=memory_keywords,
                data_copy_keywords=data_copy_keywords,
                string_concat_operators=string_concat_operators,
                string_concat_methods=string_concat_methods,
                async_node_types=async_node_types,
                n_plus_one_keywords=n_plus_one_keywords,
            )
            functions.append(
                SolvixFunction(
                    name=name,
                    line_start=start + 1,
                    line_end=min(index + 1, len(lines)),
                    arguments=arguments,
                    nodes=nodes,
                    language=language,
                )
            )
            index += 1
        return functions

    def _match_brace_function(self, line: str) -> tuple[str, list[str]] | None:
        stripped = line.strip()
        patterns = [
            r"^(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\(([^)]*)\)",
            r"^(?:public|private|protected|static|\s)*\s*func\s+([A-Za-z_]\w*)\s*\(([^)]*)\)",
            r"^(?:public|private|protected|static|\s)*\s*fun\s+([A-Za-z_]\w*)\s*\(([^)]*)\)",
            r"^(?:public|private|protected|static|\s)*\s*fn\s+([A-Za-z_]\w*)\s*\(([^)]*)\)",
            r"^(?:public|private|protected|static|\s)*\s*[\w:<>\[\]\?&\s]+\*\s*([A-Za-z_]\w*)\s*\(([^)]*)\)",
            r"^(?:public|private|protected|static|\s)*\s*[\w:<>\[\]\?&\*]+\s+([A-Za-z_]\w*)\s*\(([^)]*)\)",
        ]
        for pattern in patterns:
            match = re.search(pattern, stripped)
            if match and "if " not in stripped and "for " not in stripped and "while " not in stripped:
                arguments = [
                    part.strip().split(":")[0].split()[-1].replace("$", "")
                    for part in match.group(2).split(",")
                    if part.strip()
                ]
                return match.group(1), arguments
        return None

    def _scan_lines_for_nodes(self, body_lines: list[str], function_name: str, start_line: int, memory_keywords: set[str], data_copy_keywords: set[str], string_concat_operators: set[str], string_concat_methods: set[str], async_node_types: set[str], n_plus_one_keywords: tuple[str, ...]) -> list[SolvixNode]:
        nodes: list[SolvixNode] = []
        parents: list[str] = []
        loop_depth = 0
        for offset, line in enumerate(body_lines):
            line_number = start_line + offset
            stripped = line.strip()
            node_type = None
            name = None

            if re.search(r"\b(for|while|foreach)\b", stripped) or any(token in stripped for token in ("each do", ".each do", ".map do", ".times do", ".upto do")):
                node_type = "nested_loop" if loop_depth > 0 else "loop"
            elif re.search(r"\b(if|try|catch|with|switch|synchronized)\b", stripped):
                node_type = "branch"
            elif any(keyword in stripped for keyword in async_node_types) or "await " in stripped or stripped.startswith("go "):
                node_type = "async_block"
            else:
                for keyword in sorted(memory_keywords, key=len, reverse=True):
                    if keyword and keyword in stripped:
                        node_type = "memory_alloc"
                        name = keyword
                        break
                if node_type is None:
                    for keyword in sorted(data_copy_keywords, key=len, reverse=True):
                        if keyword and keyword in stripped:
                            node_type = "data_copy"
                            name = keyword
                            break
                if node_type is None and function_name in stripped and "(" in stripped and not re.search(r"^(def|function|func|fn|fun)\b", stripped):
                    node_type = "recursion"
                    name = function_name
                if node_type is None and any(method in stripped for method in string_concat_methods):
                    node_type = "string_concat"
                if node_type is None and any(operator in stripped for operator in string_concat_operators) and "=" in stripped:
                    node_type = "string_concat"
                if node_type is None and re.search(r"[A-Za-z_]\w*\s*\(", stripped) and not re.search(r"^(if|for|while|switch|return)\b", stripped):
                    node_type = "function_call"
                    call_name = stripped.split("(", 1)[0].split()[-1].split(".")[-1].replace("$", "")
                    if any(keyword in call_name.lower() for keyword in n_plus_one_keywords):
                        name = "N+1 Query Pattern"
                    else:
                        name = call_name

            if node_type:
                node_id = f"{function_name}:{len(nodes)}:{line_number}"
                node = SolvixNode(
                    node_type=node_type,
                    line_number=line_number,
                    depth=len(parents),
                    name=name,
                    node_id=node_id,
                    parent_id=parents[-1] if parents else None,
                )
                nodes.append(node)
                if parents:
                    parent = next((entry for entry in nodes if entry.node_id == parents[-1]), None)
                    if parent:
                        parent.children.append(node)
                if node_type in {"loop", "nested_loop", "branch"}:
                    parents.append(node_id)
                if node_type in {"loop", "nested_loop"}:
                    loop_depth += 1

            closing_braces = stripped.count("}") + (1 if stripped == "end" else 0)
            for _ in range(min(closing_braces, len(parents))):
                popped = parents.pop()
                popped_node = next((entry for entry in nodes if entry.node_id == popped), None)
                if popped_node and popped_node.node_type in {"loop", "nested_loop"} and loop_depth > 0:
                    loop_depth -= 1
        return nodes
