"""JavaScript adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class JavaScriptAdapter(TreeSitterAdapter):
    language = "javascript"
    extensions = [".js", ".jsx"]
    function_types = {"function_declaration", "arrow_function", "method_definition", "function_expression"}
    loop_types = {"for_statement", "for_in_statement", "for_of_statement", "while_statement"}
    memory_keywords = {"push", "concat", "splice", "slice", "Array", "assign", "parse", "stringify"}
    string_concat_operators = {"+"}
    async_node_types = {"await_expression"}
