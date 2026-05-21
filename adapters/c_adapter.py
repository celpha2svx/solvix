"""C adapter using tree-sitter."""

from __future__ import annotations

from adapters.base import TreeSitterAdapter


class CAdapter(TreeSitterAdapter):
    language = "c"
    extensions = [".c", ".h"]
    function_types = {"function_definition"}
    loop_types = {"for_statement", "while_statement", "do_statement"}
    branch_types = {"if_statement", "switch_statement"}
    call_node_types = {"call_expression"}
    memory_keywords = {"malloc", "calloc", "realloc"}
    data_copy_keywords = {"memcpy", "memmove", "strcpy", "strcat"}
