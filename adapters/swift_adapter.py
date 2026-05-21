"""Swift adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class SwiftAdapter(TreeSitterAdapter):
    language = "swift"
    extensions = [".swift"]
    function_types = {"function_declaration"}
    loop_types = {"for_in_statement", "while_statement", "repeat_while_statement"}
    call_node_types = {"call_expression"}
    memory_keywords = {"map", "filter", "reduce"}
