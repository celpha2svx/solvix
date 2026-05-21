"""Go adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class GoAdapter(TreeSitterAdapter):
    language = "go"
    extensions = [".go"]
    function_types = {"function_declaration", "method_declaration"}
    loop_types = {"for_statement"}
    call_node_types = {"call_expression"}
    memory_keywords = {"make", "append"}
    async_node_types = {"go_statement"}
    string_concat_operators = {"+"}
