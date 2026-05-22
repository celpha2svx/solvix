"""Stage 5 optional AI overlay orchestration."""

from __future__ import annotations

import json
from typing import Any, Protocol

from core.ai_overlay_payload import build_ai_overlay_payload
from core.report import AIOverlayResult, AIOverlaySummary, MultiLensSummary, ProjectProfile, ProjectSummary, SynthesisSummary, to_dict

AI_OVERLAY_MODE_OFF = "off"
AI_OVERLAY_MODE_ASSIST = "assist"
AI_OVERLAY_MODE_INTERACTIVE = "interactive"

AI_OVERLAY_DEFAULT_ASSIST_MODEL = "gpt-5.4-mini"
AI_OVERLAY_PREMIUM_MODEL = "gpt-5.5"
AI_OVERLAY_PREVIEW_MODEL = "gpt-5.4-nano"

AI_OVERLAY_SYSTEM_PROMPT = (
    "You are producing a Stage 5 AI overlay for Solvix. "
    "Stages 1 through 4 are the source of truth. Use only the supplied structured payload. "
    "Do not invent files, findings, scores, lanes, themes, or repository facts. "
    "Keep the response concise, actionable, and explicitly grounded in the provided payload."
)

AI_OVERLAY_RESPONSE_FORMAT = {
    "format": {
        "type": "json_schema",
        "name": "solvix_stage5_overlay",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "executive_summary": {"type": "string"},
                "maintainer_plan": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 3,
                },
                "lens_explanation": {"type": "string"},
                "grounded_theme_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 5,
                },
                "grounded_lane_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
                "grounded_hotspots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "function": {"type": "string"},
                        },
                        "required": ["file", "function"],
                        "additionalProperties": False,
                    },
                    "maxItems": 4,
                },
                "caveats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 4,
                },
            },
            "required": [
                "executive_summary",
                "maintainer_plan",
                "lens_explanation",
                "grounded_theme_keys",
                "grounded_lane_keys",
                "grounded_hotspots",
                "caveats",
            ],
            "additionalProperties": False,
        },
    }
}


class AIOverlayError(RuntimeError):
    """Raised when the optional AI overlay cannot complete."""


class AIOverlayProvider(Protocol):
    provider_name: str

    def generate(
        self,
        *,
        mode: str,
        model: str,
        payload: Any,
        system_prompt: str,
        user_prompt: str,
    ) -> Any:
        """Generate a raw overlay response for normalization."""


class OpenAIResponsesProvider:
    """Best-effort OpenAI Responses API provider for Stage 5 assist mode."""

    provider_name = "openai_responses"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def generate(
        self,
        *,
        mode: str,
        model: str,
        payload: Any,
        system_prompt: str,
        user_prompt: str,
    ) -> Any:
        client = self._client or _build_openai_client()
        try:
            response = client.responses.create(
                model=model,
                instructions=system_prompt,
                input=user_prompt,
                text=AI_OVERLAY_RESPONSE_FORMAT,
                max_output_tokens=900,
                store=False,
            )
        except Exception as exc:
            raise AIOverlayError(f"OpenAI assist call failed: {exc}") from exc
        output_text = getattr(response, "output_text", "")
        if not output_text:
            raise AIOverlayError("OpenAI assist call returned an empty response.")
        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise AIOverlayError("OpenAI assist call returned invalid structured JSON.") from exc


def run_ai_overlay(
    profile: ProjectProfile,
    summary: ProjectSummary,
    synthesis: SynthesisSummary | None,
    multi_lens: MultiLensSummary | None,
    *,
    mode: str = AI_OVERLAY_MODE_OFF,
    model: str | None = None,
    provider: AIOverlayProvider | None = None,
    status_callback=None,
) -> AIOverlaySummary:
    """Run the optional Stage 5 AI overlay without risking deterministic output."""

    normalized_mode = _normalize_mode(mode)
    payload = None
    budget = build_ai_overlay_payload(profile, summary, synthesis, multi_lens)[1]
    if normalized_mode == AI_OVERLAY_MODE_OFF:
        return AIOverlaySummary(
            enabled=False,
            mode=normalized_mode,
            status="disabled",
            model=None,
            provider=None,
            input_budget=budget,
            notes=["AI overlay is off. Deterministic Stage 1-4 output remains the source of truth."],
        )

    _emit_status(status_callback, "Compressing deterministic report")
    payload, budget = build_ai_overlay_payload(profile, summary, synthesis, multi_lens)
    resolved_model = _resolve_model(normalized_mode, model)

    if normalized_mode == AI_OVERLAY_MODE_INTERACTIVE:
        _emit_status(status_callback, "AI overlay complete")
        return AIOverlaySummary(
            enabled=True,
            mode=normalized_mode,
            status="scaffolded",
            model=resolved_model,
            provider="scaffold",
            input_budget=budget,
            input_payload=payload,
            notes=[
                "Interactive mode is scaffolded in this pass.",
                "The bounded deterministic payload is ready for follow-up AI Q&A, but no conversation session is started yet.",
            ],
        )

    overlay_provider = provider or OpenAIResponsesProvider()
    provider_name = getattr(overlay_provider, "provider_name", overlay_provider.__class__.__name__)
    try:
        _emit_status(status_callback, "Contacting AI provider")
        raw_result = overlay_provider.generate(
            mode=normalized_mode,
            model=resolved_model,
            payload=payload,
            system_prompt=AI_OVERLAY_SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(normalized_mode, payload),
        )
        _emit_status(status_callback, "Grounding overlay output")
        result = _normalize_result(raw_result, normalized_mode, resolved_model, payload)
        _emit_status(status_callback, "AI overlay complete")
        return AIOverlaySummary(
            enabled=True,
            mode=normalized_mode,
            status="completed",
            model=resolved_model,
            provider=provider_name,
            input_budget=budget,
            input_payload=payload,
            result=result,
        )
    except Exception as exc:
        error = str(exc) or "Unknown AI overlay error."
        _emit_status(status_callback, "AI overlay unavailable")
        return AIOverlaySummary(
            enabled=True,
            mode=normalized_mode,
            status="failed",
            model=resolved_model,
            provider=provider_name,
            input_budget=budget,
            input_payload=payload,
            notes=["AI overlay unavailable; deterministic report completed successfully."],
            error=error,
        )


def _emit_status(status_callback, message: str) -> None:
    if status_callback is not None:
        status_callback(message)


def _build_openai_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIOverlayError(
            "OpenAI Python SDK is not installed. Install `openai` to enable the Stage 5 assist overlay."
        ) from exc
    try:
        return OpenAI()
    except Exception as exc:
        raise AIOverlayError(
            "OpenAI client initialization failed. Ensure OPENAI_API_KEY is configured for Stage 5 assist mode."
        ) from exc


def _build_user_prompt(mode: str, payload: Any) -> str:
    return (
        f"Solvix Stage 5 mode: {mode}\n"
        "Return a concise executive summary, a short maintainer plan, and a lens explanation.\n"
        "Use only the payload below. Do not invent new findings or references.\n"
        "Payload JSON:\n"
        f"{json.dumps(to_dict(payload), indent=2)}"
    )


def _normalize_mode(mode: str) -> str:
    normalized = (mode or AI_OVERLAY_MODE_OFF).strip().lower()
    if normalized not in {AI_OVERLAY_MODE_OFF, AI_OVERLAY_MODE_ASSIST, AI_OVERLAY_MODE_INTERACTIVE}:
        raise AIOverlayError(f"Unsupported AI overlay mode: {mode}")
    return normalized


def _resolve_model(mode: str, model: str | None) -> str | None:
    if mode == AI_OVERLAY_MODE_OFF:
        return None
    if model:
        return model.strip()
    if mode == AI_OVERLAY_MODE_ASSIST:
        return AI_OVERLAY_DEFAULT_ASSIST_MODEL
    return AI_OVERLAY_PREMIUM_MODEL


def _normalize_result(raw_result: Any, mode: str, model: str, payload: Any) -> AIOverlayResult:
    data = _coerce_mapping(raw_result)
    supported_theme_keys = {item["key"] for item in to_dict(payload.top_themes)}
    supported_lane_keys = {item["key"] for item in to_dict(payload.top_lanes)}
    supported_hotspots = {
        (item["file"], item["function"]): item
        for item in to_dict(payload.top_hotspots)
        if item.get("file") and item.get("function")
    }

    caveats = _coerce_string_list(data.get("caveats"), limit=4)
    grounded_theme_keys, dropped_theme_keys = _filter_supported_strings(
        data.get("grounded_theme_keys"),
        supported_theme_keys,
        limit=min(5, len(supported_theme_keys) or 5),
    )
    grounded_lane_keys, dropped_lane_keys = _filter_supported_strings(
        data.get("grounded_lane_keys"),
        supported_lane_keys,
        limit=min(3, len(supported_lane_keys) or 3),
    )
    grounded_hotspots, dropped_hotspots = _filter_supported_hotspots(
        data.get("grounded_hotspots"),
        supported_hotspots,
        limit=min(4, len(supported_hotspots) or 4),
    )

    if not grounded_theme_keys:
        grounded_theme_keys = [item["key"] for item in to_dict(payload.top_themes[:2])]
    if not grounded_lane_keys:
        grounded_lane_keys = [item["key"] for item in to_dict(payload.top_lanes[:2])]
    if not grounded_hotspots:
        grounded_hotspots = to_dict(payload.top_hotspots[:2])

    if dropped_theme_keys or dropped_lane_keys or dropped_hotspots:
        caveats.append("Unsupported grounded references were dropped to keep the overlay aligned with deterministic data.")
    caveats = caveats[:4]

    executive_summary = _coerce_text(data.get("executive_summary")) or (
        "AI overlay completed from the bounded deterministic Stage 1-4 payload."
    )
    lens_explanation = _coerce_text(data.get("lens_explanation")) or (
        "The default deterministic lens shaped the overlay summary and action ordering."
    )
    maintainer_plan = _coerce_string_list(data.get("maintainer_plan"), limit=3)
    if not maintainer_plan:
        maintainer_plan = _fallback_plan(payload)

    return AIOverlayResult(
        mode=mode,
        model=model,
        executive_summary=executive_summary,
        maintainer_plan=maintainer_plan,
        lens_explanation=lens_explanation,
        grounded_theme_keys=grounded_theme_keys,
        grounded_lane_keys=grounded_lane_keys,
        grounded_hotspots=grounded_hotspots,
        caveats=caveats,
    )


def _coerce_mapping(raw_result: Any) -> dict[str, Any]:
    if isinstance(raw_result, AIOverlayResult):
        return to_dict(raw_result)
    if isinstance(raw_result, str):
        try:
            parsed = json.loads(raw_result)
        except json.JSONDecodeError as exc:
            raise AIOverlayError("AI overlay provider returned a non-JSON string.") from exc
        if not isinstance(parsed, dict):
            raise AIOverlayError("AI overlay provider returned JSON, but not an object.")
        return parsed
    if not isinstance(raw_result, dict):
        raise AIOverlayError("AI overlay provider returned an unsupported result shape.")
    return raw_result


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _coerce_string_list(value: Any, *, limit: int) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _filter_supported_strings(value: Any, supported: set[str], *, limit: int) -> tuple[list[str], list[str]]:
    filtered: list[str] = []
    dropped: list[str] = []
    for item in _coerce_string_list(value, limit=max(limit, 8)):
        if item in supported and item not in filtered:
            filtered.append(item)
            if len(filtered) >= limit:
                break
        else:
            dropped.append(item)
    return filtered, dropped


def _filter_supported_hotspots(
    value: Any,
    supported: dict[tuple[str, str], dict[str, Any]],
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(value, list):
        return [], []

    filtered: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            dropped.append({"file": "", "function": str(item)})
            continue
        file_path = str(item.get("file", "")).strip()
        function_name = str(item.get("function", "")).strip()
        key = (file_path, function_name)
        if key in supported and not any(
            existing.get("file") == file_path and existing.get("function") == function_name for existing in filtered
        ):
            filtered.append(supported[key])
            if len(filtered) >= limit:
                break
        else:
            dropped.append({"file": file_path, "function": function_name})
    return filtered, dropped


def _fallback_plan(payload: Any) -> list[str]:
    top_lanes = to_dict(payload.top_lanes)
    if top_lanes:
        plan = [f"Start with {lane['title']} because it leads the deterministic lane ordering." for lane in top_lanes[:3]]
        return plan[:3]
    top_hotspots = to_dict(payload.top_hotspots)
    if top_hotspots:
        first = top_hotspots[0]
        return [
            f"Start with {first['function']} in {first['file']} because it leads the bounded hotspot list.",
            "Validate whether the highest-priority hotspots share the same production zone.",
            "Use the deterministic lane ordering to sequence the next round of fixes.",
        ]
    return ["Review the deterministic Stage 1-4 report first because no bounded AI plan inputs were available."]
