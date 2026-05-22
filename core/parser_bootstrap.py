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


def bootstrap_languages(languages: list[str] | None = None, progress_callback=None) -> tuple[int, str]:
    """Download parser artifacts for the requested languages."""

    targets = list(dict.fromkeys(languages or SUPPORTED_TREE_SITTER_LANGUAGES))
    try:
        from tree_sitter_language_pack import cache_dir, download
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "tree-sitter-language-pack is not installed or could not be loaded."
        ) from exc

    downloaded_count = 0
    total = len(targets)
    for index, language in enumerate(targets, start=1):
        _emit_progress(progress_callback, "start", language, index, total)
        try:
            downloaded_count += int(download([language]) or 0)
        except Exception as exc:  # pragma: no cover - environment/network dependent
            _emit_progress(progress_callback, "failed", language, index, total)
            raise RuntimeError(f"Could not download parser artifacts for {language}. {exc}") from exc
        _emit_progress(progress_callback, "complete", language, index, total)
    return downloaded_count, cache_dir()


def _emit_progress(progress_callback, event: str, language: str, current: int, total: int) -> None:
    if progress_callback is not None:
        progress_callback(event, language, current, total)
