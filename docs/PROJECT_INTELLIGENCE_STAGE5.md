# Project Intelligence Stage 5

This document defines Stage 5 of Solvix project intelligence.

Stage 1 gave Solvix deterministic project awareness.
Stage 2 gave Solvix deterministic relevance weighting.
Stage 3 gave Solvix deterministic signal synthesis.
Stage 4 gave Solvix deterministic multi-lens reporting.
Stage 5 gives Solvix an **optional AI overlay**.

The mission of Stage 5 is to add compression, explanation, and advisory help
without making AI part of the truth engine or the critical path.

## Mission

Stage 5 should answer:

- how do we explain deterministic findings in simpler language
- how do we compress a large report into a short executive summary
- how do we generate a clear maintainer action plan
- how do we compare multiple deterministic lenses in human-friendly prose
- how do we keep the system fast and safe while adding AI

Stage 5 must be optional.
AI should never be required to generate the core Solvix report.

## Core Principle

AI must not live inside the truth pipeline.

Stages 1–4 remain the source of truth.
Stage 5 only consumes their structured outputs.

That means:

- AI does not parse code
- AI does not classify project type
- AI does not assign deterministic relevance
- AI does not synthesize raw themes from scratch
- AI does not override deterministic scores silently

Instead AI should:

- explain
- compress
- narrate
- compare
- recommend next steps from deterministic evidence

## Why Stage 5 Exists

By Stage 4, Solvix can already produce high-quality deterministic structure:

- project profile
- relevance weighting
- synthesis themes
- action lanes
- multi-lens views

But users still often want:

- a short executive summary
- a human-readable “what this means”
- a concrete prioritized plan
- different summaries for different audiences

Stage 5 should provide that without slowing down the base analysis path.

## Operating Modes

Stage 5 should support three deterministic operating modes around the AI overlay.

### 1. `off`

Default base path.

- no AI call
- full deterministic analysis only
- fastest path

### 2. `assist`

Optional post-processing overlay.

- AI receives a compressed structured summary
- AI returns:
  - executive summary
  - maintainer action plan
  - lens-aware explanation
- no new findings

### 3. `interactive`

Optional follow-up mode.

- user asks questions against an already-generated report
- AI answers from structured report data
- examples:
  - “Why is this first?”
  - “Explain the startup lens simply”
  - “Which lane matters most for cloud cost?”

## Performance Rule

Stage 5 must run **after** Stages 1–4 complete.

This means the pipeline is:

1. Stage 1 profile
2. Stage 2 relevance
3. Stage 3 synthesis
4. Stage 4 multi-lens
5. Stage 5 optional AI overlay

Never the reverse.

## Compression Contract

Stage 5 must not send the whole repo or the whole raw report to the model by default.

Instead it should build a bounded structured payload such as:

```python
@dataclass
class AIOverlayInput:
    project_profile: dict[str, Any]
    project_summary: dict[str, Any]
    synthesis_summary: dict[str, Any]
    default_lens: dict[str, Any]
    top_themes: list[dict[str, Any]]
    top_lanes: list[dict[str, Any]]
    top_hotspots: list[dict[str, Any]]
    noise_diagnostic: dict[str, Any] | None
```

Recommended caps:

- top themes: 5
- top lanes: 3
- top hotspots: 8
- examples per theme: 2

This keeps the AI input:

- small
- fast
- cheap
- grounded

## Grounding Rules

Stage 5 AI must be grounded in deterministic artifacts only.

Grounding rules:

1. AI may summarize supplied findings.
2. AI may compare supplied lenses.
3. AI may recommend actions from supplied themes/lanes.
4. AI may not invent new facts outside the provided payload.
5. AI may not silently contradict Stage 1–4 outputs.
6. If the AI wants to express uncertainty, it should say so explicitly.

## Proposed Data Model

Stage 5 should introduce contracts roughly like:

```python
@dataclass
class AIOverlayInput:
    project_profile: dict[str, Any]
    project_summary: dict[str, Any]
    synthesis_summary: dict[str, Any]
    default_lens: dict[str, Any]
    top_themes: list[dict[str, Any]]
    top_lanes: list[dict[str, Any]]
    top_hotspots: list[dict[str, Any]]
    noise_diagnostic: dict[str, Any] | None

@dataclass
class AIOverlayResult:
    mode: str
    model: str
    executive_summary: str
    maintainer_plan: list[str]
    lens_explanation: str
    grounded_theme_keys: list[str]
    grounded_lane_keys: list[str]
    grounded_hotspots: list[dict[str, Any]]
    caveats: list[str]

@dataclass
class AIOverlaySummary:
    enabled: bool
    mode: str
    status: str
    provider: str | None
    input_budget: dict[str, int]
    input_payload: AIOverlayInput | None
    result: AIOverlayResult | None
    notes: list[str]
    error: str | None
```

These can be attached as:

- a new `ai_overlay` field on `ProjectReport`
- or emitted separately as an adjunct artifact

## Model Strategy

Stage 5 should use a tiered model strategy.

### Default recommendation

Use **Responses API** with:

- default assist model: `gpt-5.4-mini`
- premium deep-explain model: `gpt-5.5`
- low-cost bulk/preview mode: `gpt-5.4-nano`

## Why these models

Current official guidance says:

- if you are not sure where to start, use `gpt-5.5` for complex reasoning and coding
- if optimizing for latency and cost, use smaller variants like `gpt-5.4-mini` or `gpt-5.4-nano`
- `gpt-5.4-nano` is recommended for speed/cost-sensitive workloads like classification, extraction, ranking, and sub-agents

Stage 5 needs:

- good summarization quality
- fast response
- low enough cost for optional CLI usage

So the best architecture is:

### `gpt-5.4-mini`

Use as the **default Stage 5 assist model**.

Why:

- better quality than ultra-cheap nano
- still fast enough for CLI post-processing
- appropriate for explanation, compression, and structured advisory output

### `gpt-5.5`

Use as the **premium deep-analysis / explicit opt-in model**.

Why:

- best fit when the user asks for richer reasoning
- useful for deeper maintainer narratives or more nuanced lens comparison
- should not be the default because it is more expensive and can add latency

### `gpt-5.4-nano`

Use as the **cheap preview/bulk mode**.

Why:

- suitable for short summaries, terse previews, or high-volume batch reporting
- not ideal as the default if output quality matters more than pure speed/cost

## Prompting Strategy

Stage 5 should not send huge free-form prompts.

It should use:

- one stable system prompt
- one compact structured payload
- one small user instruction depending on mode

Example system purpose:

- “You are explaining deterministic Solvix analysis. Use only the supplied structured report. Do not invent findings. Prefer concise actionable guidance.”

Example tasks:

- executive summary
- maintainer plan
- lens explanation
- audience-specific summary

## Output Shapes

Stage 5 should support deterministic output templates such as:

### 1. Executive summary

- one short paragraph
- top issue
- top lane
- why it matters

### 2. Maintainer plan

- 3-step action plan
- grounded in top lanes and top themes

### 3. Lens explanation

- explain why the default lens was chosen
- explain why another lens would reorder things differently

### 4. Audience summary

Optional later:

- platform owner summary
- framework maintainer summary
- cloud-cost owner summary

## Latency Guardrails

Stage 5 should remain smooth by design.

Rules:

1. AI is off by default unless explicitly enabled.
2. AI input must be compressed first.
3. AI response length should be bounded.
4. AI should never block saving the deterministic report.
5. Later, AI results may be cached by report hash.

Suggested first implementation:

- deterministic report finishes
- optional AI overlay runs afterward
- if AI fails, deterministic result still succeeds
- interactive mode may ship first as a scaffolded bounded payload rather than a live follow-up session

## Implementation Notes

The current Stage 5 implementation sharpens the architecture in a few practical ways:

- Stage 5 is attached directly to `ProjectReport.ai_overlay`
- assist mode uses a bounded payload builder with explicit caps in code:
  - top themes: 5
  - top lanes: 3
  - top hotspots: 8
  - examples per theme: 2
- the OpenAI Responses integration is lazy and optional:
  - deterministic analysis does not depend on the OpenAI SDK
  - assist mode can use an injectable provider for tests or alternative runtimes
- interactive mode is scaffolded in the first pass:
  - the bounded payload is prepared
  - no live follow-up session is started yet
- grounded AI output keeps explicit references back to deterministic artifacts:
  - theme keys
  - lane keys
  - hotspot file/function pairs
- unsupported grounded references are dropped during normalization so the overlay cannot silently drift away from Stage 1-4 truth

## Failure Behavior

If AI fails:

- do not fail the base analysis
- preserve the deterministic report
- emit a small note such as:
  - “AI overlay unavailable; deterministic report completed successfully.”

This is critical.

## Output Requirements

Stage 5 must expose:

### Terminal Output

If AI is enabled:

- short AI executive summary
- short AI action plan
- explicit note that this is an AI overlay on deterministic analysis

### Text Output

If AI is enabled:

- append an `AI Overlay` section

### JSON Output

If AI is enabled:

- include:
  - whether AI was enabled
  - mode
  - model
  - input budget
  - grounded result fields

## Realistic Scenario Matrix

Stage 5 must behave sensibly in these cases.

### 1. Framework Library

Expected behavior:

- explain dispatch complexity in maintainer-friendly language
- avoid pretending raw loop cost alone is the whole story

### 2. API Service

Expected behavior:

- summarize request-path pressure clearly
- compare performance vs cloud_cost lens cleanly

### 3. Website / Web App

Expected behavior:

- describe responsiveness themes simply
- avoid flooding with internal detail

### 4. CLI Tool

Expected behavior:

- give concise startup-focused guidance

### 5. Data Pipeline

Expected behavior:

- translate throughput and repetition into actionable batch-optimization advice

### 6. Serverless

Expected behavior:

- explain cold-start vs request-path tradeoffs clearly

### 7. Mobile App

Expected behavior:

- emphasize battery/network/update-loop concerns

### 8. Device Firmware + Cloud

Expected behavior:

- explain device-side and cloud-side lanes separately

### 9. Microservices Repo

Expected behavior:

- summarize service-entrypoint and cloud-cost tradeoffs

### 10. Test-Heavy Repo

Expected behavior:

- keep the explanation honest about noise
- avoid inventing production urgency

## Completion Criteria

Stage 5 is complete when:

1. AI overlay is optional and off by default.
2. AI consumes compressed structured payloads only.
3. Deterministic analysis succeeds even if AI fails.
4. Model selection is explicit and configurable.
5. Output clearly distinguishes deterministic vs AI overlay content.
6. The default model choice is fast and practical.
7. Tests cover payload compression, optional execution, and failure-safe behavior.

## Recommended Implementation Order

1. Add Stage 5 report contracts.
2. Create a compression builder such as `core/ai_overlay_payload.py`.
3. Create an overlay orchestrator such as `core/ai_overlay.py`.
4. Keep AI disabled by default.
5. Add explicit model selection and mode selection.
6. Update JSON/text/terminal outputs for optional overlay sections.
7. Add tests for:
   - compression caps
   - off/assist mode behavior
   - failure-safe fallback
   - grounded output wiring

## Guardrails

Do not do these in Stage 5:

- no AI in parsing
- no AI in deterministic scoring
- no AI-only repo analysis
- no hidden reprioritization
- no giant raw-repo prompts by default

Keep it:

- optional
- post-processing only
- compressed
- grounded
- failure-safe

## Prompt For Implementation Chat

Use this exact prompt in another chat:

```text
Continue Solvix from:
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE1.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE2.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE3.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE4.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE5.md

Implement Stage 5 as an optional AI overlay on top of the deterministic system.

Goals:
1. Add Stage 5 AI overlay contracts to the report model.
2. Create a deterministic compression builder that prepares a bounded AI payload from Stage 1–4 outputs.
3. Create an AI overlay orchestrator that supports:
   - `off`
   - `assist`
   - `interactive` (scaffold only if full interactive mode is too large for first pass)
4. Keep AI off by default.
5. Make deterministic analysis succeed even if AI overlay fails.
6. Add explicit model/mode configuration with this recommended strategy:
   - default assist model: `gpt-5.4-mini`
   - premium deep reasoning model: `gpt-5.5`
   - low-cost preview model: `gpt-5.4-nano`
7. Update terminal/text/json outputs so AI overlay output is clearly separated from deterministic output.
8. Add tests for:
   - payload compression caps
   - off mode
   - assist mode wiring
   - failure-safe fallback
   - grounded output structure

Constraints:
- deterministic layers remain the source of truth
- AI must be post-processing only
- no AI/model dependency in parsing, relevance, synthesis, or lens computation
- do not send the whole raw repo or full raw findings by default
- preserve backward compatibility where practical
- update C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE5.md if implementation sharpens the architecture

Implementation expectations:
- add modules like:
  - C:\Users\Adminn\Solvix\core\ai_overlay_payload.py
  - C:\Users\Adminn\Solvix\core\ai_overlay.py
- keep compression caps explicit in code
- keep model strings explicit in code
- ensure deterministic report generation never fails because of AI overlay issues
- ensure tests pass with `py -3 -m unittest tests.test_all`
```
