"""TypeScript adapter using tree-sitter."""

from __future__ import annotations

from adapters.javascript_adapter import JavaScriptAdapter


class TypeScriptAdapter(JavaScriptAdapter):
    language = "typescript"
    extensions = [".ts", ".tsx"]
    data_copy_keywords = {" as ", "<", ">"}
