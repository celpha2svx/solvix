"""Kotlin adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class KotlinAdapter(TreeSitterAdapter):
    language = "kotlin"
    extensions = [".kt", ".kts"]
    function_types = {"function_declaration"}
    loop_types = {"for_statement", "while_statement", "do_while_statement"}
    call_node_types = {"call_expression"}
    memory_keywords = {"map", "filter", "forEach"}
    async_node_types = {"call_expression"}
    n_plus_one_keywords = ("query", "fetch", "find", "request", "select")
