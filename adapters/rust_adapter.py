"""Rust adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class RustAdapter(TreeSitterAdapter):
    language = "rust"
    extensions = [".rs"]
    function_types = {"function_item"}
    loop_types = {"for_expression", "while_expression", "loop_expression"}
    call_node_types = {"call_expression"}
    memory_keywords = {"new", "to_string", "to_owned"}
    string_concat_operators = {"+"}
    string_concat_methods = {"push_str"}
    data_copy_keywords = {".clone()"}
