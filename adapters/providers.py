"""Parser provider infrastructure for Solvix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ParserProvider(Protocol):
    """Provides parser instances for tree-sitter-backed adapters."""

    name: str
    quality: str

    def is_available(self) -> bool:
        """Return True when the provider can serve parsers."""

    def get_parser(self, language: str) -> Any:
        """Return a parser instance for the requested language."""

    def describe(self) -> str:
        """Return a short human-readable description."""

    def ensure_language(self, language: str) -> bool:
        """Attempt to make a language parser available. Return True if work was done."""


@dataclass(frozen=True)
class ParserRuntimeInfo:
    backend: str
    quality: str
    degraded: bool
    note: str


class TreeSitterLanguagePackProvider:
    """Primary tree-sitter provider backed by maintained language-pack wheels."""

    name = "tree-sitter-language-pack"
    quality = "native"

    def __init__(self) -> None:
        self._import_error: Exception | None = None
        self._get_parser = None
        self._download = None
        try:
            from tree_sitter_language_pack import download, get_parser

            self._download = download
            self._get_parser = get_parser
        except Exception as exc:  # pragma: no cover - depends on environment
            self._import_error = exc

    def is_available(self) -> bool:
        return self._get_parser is not None

    def get_parser(self, language: str) -> Any:
        if self._get_parser is None:
            raise RuntimeError(self.describe())
        return self._get_parser(language)

    def describe(self) -> str:
        if self._import_error is None:
            return "Native parser backend via tree-sitter-language-pack."
        return f"tree-sitter-language-pack unavailable: {self._import_error}"

    def ensure_language(self, language: str) -> bool:
        if self._download is None:
            return False
        self._download([language])
        return True


class LegacyTreeSitterLanguagesProvider:
    """Compatibility provider for older tree-sitter-languages installs."""

    name = "tree-sitter-languages"
    quality = "legacy"

    def __init__(self) -> None:
        self._import_error: Exception | None = None
        self._get_parser = None
        try:
            from tree_sitter_languages import get_parser

            self._get_parser = get_parser
        except Exception as exc:  # pragma: no cover - depends on environment
            self._import_error = exc

    def is_available(self) -> bool:
        return self._get_parser is not None

    def get_parser(self, language: str) -> Any:
        if self._get_parser is None:
            raise RuntimeError(self.describe())
        return self._get_parser(language)

    def describe(self) -> str:
        if self._import_error is None:
            return "Compatibility parser backend via tree-sitter-languages."
        return f"tree-sitter-languages unavailable: {self._import_error}"

    def ensure_language(self, language: str) -> bool:
        return False


def build_provider_chain() -> list[ParserProvider]:
    """Return providers ordered from preferred to least preferred."""

    return [
        TreeSitterLanguagePackProvider(),
        LegacyTreeSitterLanguagesProvider(),
    ]


def resolve_parser_provider() -> tuple[ParserProvider | None, ParserRuntimeInfo]:
    """Pick the best available parser provider and return runtime diagnostics."""

    for provider in build_provider_chain():
        if provider.is_available():
            degraded = provider.quality != "native"
            note = provider.describe()
            if degraded:
                note = f"{note} Running in compatibility mode."
            return provider, ParserRuntimeInfo(
                backend=provider.name,
                quality=provider.quality,
                degraded=degraded,
                note=note,
            )

    return None, ParserRuntimeInfo(
        backend="heuristic-fallback",
        quality="degraded",
        degraded=True,
        note=(
            "No native tree-sitter provider is available. "
            "Solvix is using the built-in heuristic fallback parser for non-Python languages."
        ),
    )


def runtime_info_for_provider(provider: ParserProvider, note_override: str | None = None) -> ParserRuntimeInfo:
    """Build runtime metadata for a provider."""

    degraded = provider.quality != "native"
    note = note_override or provider.describe()
    if degraded and "compatibility mode" not in note.lower():
        note = f"{note} Running in compatibility mode."
    return ParserRuntimeInfo(
        backend=provider.name,
        quality=provider.quality,
        degraded=degraded,
        note=note,
    )
