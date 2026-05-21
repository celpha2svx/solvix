"""PHP adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class PHPAdapter(TreeSitterAdapter):
    language = "php"
    extensions = [".php"]
    function_types = {"function_definition", "method_declaration"}
    loop_types = {"for_statement", "foreach_statement", "while_statement", "do_statement"}
    call_node_types = {"function_call_expression", "member_call_expression"}
    n_plus_one_keywords = ("query", "fetch", "select", "find")
    string_concat_operators = {"."}
