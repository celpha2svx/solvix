"""Language detection for Solvix."""

from __future__ import annotations

from pathlib import Path

EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
}

SHEBANG_MAP = {
    "python": "python",
    "node": "javascript",
    "ruby": "ruby",
    "php": "php",
}

SUPPORTED_LABEL = (
    "Python, JavaScript, TypeScript, Java, C, C++, Rust, Go, Ruby, PHP, Swift, Kotlin."
)


def detect_language(filepath: Path, source_code: str | None = None) -> str:
    language = EXTENSION_MAP.get(filepath.suffix.lower())
    if language:
        return language

    if source_code:
        first_line = source_code.splitlines()[0] if source_code.splitlines() else ""
        if first_line.startswith("#!"):
            for marker, mapped in SHEBANG_MAP.items():
                if marker in first_line:
                    return mapped
    return "unsupported"
