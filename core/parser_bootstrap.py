"""Bootstrap helpers for native parser backends."""

from __future__ import annotations

from core.language_detector import EXTENSION_MAP

SUPPORTED_TREE_SITTER_LANGUAGES = sorted(
    {
        language
        for language in EXTENSION_MAP.values()
        if language != "python"
    }
)


def bootstrap_languages(languages: list[str] | None = None) -> tuple[int, str]:
    """Download parser artifacts for the requested languages."""

    targets = languages or SUPPORTED_TREE_SITTER_LANGUAGES
    try:
        from tree_sitter_language_pack import cache_dir, download
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "tree-sitter-language-pack is not installed or could not be loaded."
        ) from exc

    downloaded = download(targets)
    return downloaded, cache_dir()
