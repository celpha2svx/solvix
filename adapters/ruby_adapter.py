"""Ruby adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class RubyAdapter(TreeSitterAdapter):
    language = "ruby"
    extensions = [".rb"]
    function_types = {"method"}
    loop_types = {"for", "while", "call"}
    call_node_types = {"call", "command"}
    memory_keywords = {"Array", "Hash"}
    n_plus_one_keywords = ("find", "where", "all", "first")
