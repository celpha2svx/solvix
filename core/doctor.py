"""Operational health checks for Solvix."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from adapters.providers import build_provider_chain
from core.parser_bootstrap import SUPPORTED_TREE_SITTER_LANGUAGES


@dataclass
class ProviderStatus:
    name: str
    quality: str
    available: bool
    detail: str


@dataclass
class DoctorReport:
    overall_status: str
    mode: str
    parser_backend_status: str
    cache_path: str | None
    cached_languages: list[str]
    missing_languages: list[str]
    providers: list[ProviderStatus]
    next_steps: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def build_doctor_report() -> DoctorReport:
    provider_statuses = [
        ProviderStatus(
            name=provider.name,
            quality=provider.quality,
            available=provider.is_available(),
            detail=provider.describe(),
        )
        for provider in build_provider_chain()
    ]

    cache_path, cached_languages = _language_pack_cache_state()
    cached_set = set(cached_languages)
    missing_languages = sorted(
        language for language in SUPPORTED_TREE_SITTER_LANGUAGES if language not in cached_set
    )

    native_provider = next(
        (provider for provider in provider_statuses if provider.name == "tree-sitter-language-pack"),
        None,
    )

    if native_provider and native_provider.available:
        if missing_languages:
            overall_status = "READY_WITH_AUTO_BOOTSTRAP"
            mode = "native-auto-bootstrap"
            parser_backend_status = (
                "Native backend is available. Some parser artifacts are not cached yet, "
                "but Solvix can auto-download them on first use."
            )
            next_steps = [
                "Run `solvix bootstrap-parsers --all` on CI runners, base images, or offline machines.",
                "Use `solvix analyze ...` normally for local development. Missing parsers will be fetched automatically.",
            ]
        else:
            overall_status = "READY"
            mode = "native"
            parser_backend_status = (
                "Native backend is available and all supported parser artifacts are cached."
            )
            next_steps = [
                "No action required. Solvix is fully ready for native multi-language analysis.",
            ]
    else:
        overall_status = "DEGRADED"
        mode = "degraded"
        parser_backend_status = (
            "Native multi-language parsing is not fully available. Solvix will fall back to heuristic parsing "
            "for non-Python languages."
        )
        next_steps = [
            "Install `tree-sitter-language-pack` in the same Python environment as Solvix.",
            "Run `solvix bootstrap-parsers --all` after installation to pre-cache native parser artifacts.",
            "If the machine is network-restricted, pre-download parser artifacts during image setup or CI bootstrap.",
        ]

    if cache_path is None and native_provider and native_provider.available:
        next_steps.append(
            "Run a first analysis or `solvix bootstrap-parsers --all` to create the parser cache."
        )

    return DoctorReport(
        overall_status=overall_status,
        mode=mode,
        parser_backend_status=parser_backend_status,
        cache_path=cache_path,
        cached_languages=cached_languages,
        missing_languages=missing_languages,
        providers=provider_statuses,
        next_steps=next_steps,
    )


def _language_pack_cache_state() -> tuple[str | None, list[str]]:
    try:
        from tree_sitter_language_pack import cache_dir, downloaded_languages
    except Exception:
        return None, []

    return cache_dir(), sorted(downloaded_languages())
