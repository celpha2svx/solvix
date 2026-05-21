"""Java adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class JavaAdapter(TreeSitterAdapter):
    language = "java"
    extensions = [".java"]
    function_types = {"method_declaration"}
    loop_types = {"for_statement", "enhanced_for_statement", "while_statement", "do_statement"}
    branch_types = {"if_statement", "try_statement", "synchronized_statement"}
    allocation_node_types = {"object_creation_expression"}
    string_concat_operators = {"+"}
    call_node_types = {"method_invocation"}
