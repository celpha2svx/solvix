"""C++ adapter using tree-sitter."""

from __future__ import annotations

from adapters.c_adapter import CAdapter


class CppAdapter(CAdapter):
    language = "cpp"
    extensions = [".cpp", ".cc", ".cxx", ".hpp"]
    memory_keywords = CAdapter.memory_keywords | {"push_back", "insert", "emplace_back"}
    allocation_node_types = {"new_expression"}
    string_concat_operators = {"+"}
