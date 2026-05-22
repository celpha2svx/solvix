# Project Intelligence Stage 2

This document defines Stage 2 of Solvix project intelligence.

Stage 1 gave Solvix deterministic project awareness.
Stage 2 gives Solvix deterministic **relevance weighting**.

The mission of Stage 2 is simple:

- not every finding matters equally
- not every file matters equally
- not every pattern matters equally in every kind of software

Stage 2 must use the Stage 1 project profile to rank findings in a way that matches the repository's likely objectives.

## Mission

Stage 2 should answer:

- which findings matter most in this repository
- which findings are probably noise
- which findings are urgent because of project objectives
- why the ranking changed from raw pattern severity

Stage 2 is still deterministic.
No AI should be required here.

## Inputs

Stage 2 consumes:

- raw function pattern findings
- function context analysis
- file summary information
- Stage 1 project profile
- Stage 1 per-file zone classification

From Stage 1 specifically, Stage 2 should use:

- `primary_profile`
- `secondary_profiles`
- `execution_models`
- `surfaces`
- `web_shape`
- `service_topology`
- `hybrid_shape`
- `primary_objectives`
- `secondary_objectives`
- `critical_zones`
- `noise_zones`
- `zone_classification`
- `confidence`

## Core Outcome

Stage 2 produces a relevance layer for each finding and for each function.

At minimum, each function should gain:

- `relevance_score`
- `relevance_level`
- `relevance_reason`
- `ranking_factors`
- `project_priority_label`

At file level, Solvix should gain:

- `file_relevance_score`
- `file_relevance_reason`

At project level, Solvix should gain:

- prioritized hotspots
- filtered/high-signal ranking
- project-aware “start here first” ordering

## Proposed Data Model

Stage 2 should introduce contracts roughly like:

```python
@dataclass
class RelevanceFactor:
    name: str
    weight: int
    direction: str  # boost | discount | neutral
    reason: str

@dataclass
class RelevanceResult:
    score: int
    level: str  # low | moderate | high | urgent
    reason: str
    project_priority_label: str
    factors: list[RelevanceFactor]
```

And attach it to:

- each `FunctionReport`
- optionally each `FileReport`

## Ranking Philosophy

Stage 2 should not replace raw pattern severity.
It should **reinterpret** raw severity through project context.

Think of it as:

`final priority = base pattern severity + function context + file zone + project objective fit`

This means:

- severe pattern in noise zone -> discounted
- moderate pattern in critical request path -> boosted
- cheap function in hot dispatch path -> may become worth surfacing
- expensive startup-only path in always-on API -> maybe less urgent
- expensive startup-only path in serverless -> more urgent

## Deterministic Weight Families

Stage 2 should use a fixed, explainable set of weight families.

### 1. Pattern Severity Weight

Base from Stage 0/1:

- `CRITICAL` pattern mix: strong boost
- `EXPENSIVE` pattern mix: boost
- `MODERATE` pattern mix: smaller boost
- `CHEAP`: neutral baseline

### 2. File Zone Weight

Based on Stage 1 `zone_classification`:

- `critical`: boost
- `supporting`: mild or neutral
- `noise`: discount

### 3. Project Objective Fit

Patterns should be reweighted depending on the project's objectives.

Examples:

- `request_overhead` objective:
  - boosts loop cost, allocation churn, serialization-heavy patterns
- `startup_time` objective:
  - boosts import-time, initialization, setup-path cost
- `battery_efficiency` objective:
  - boosts repeated computation and unnecessary polling/loop work
- `api_stability` objective:
  - may boost findings around extension or dispatch-heavy core flows differently

### 4. Execution Model Weight

Examples:

- `serverless`:
  - boost startup-heavy paths
- `request_response`:
  - boost request dispatch and serialization paths
- `background_jobs`:
  - boost loop throughput and memory churn
- `distributed_services`:
  - boost service entrypoints and cross-service orchestration layers

### 5. Surface Weight

Examples:

- `http`:
  - boost route handlers, serializers, middleware
- `cli`:
  - boost command startup and command dispatch
- `web_ui`:
  - boost render/build-heavy paths
- `device`:
  - boost memory-constrained or polling-sensitive code

### 6. Function Context Weight

Already partly available:

- `hot_path`
- `in_loop`
- `once`
- `test-like`
- event/handler naming

Stage 2 should consume these more explicitly rather than only as display notes.

### 7. Noise Discount

Examples:

- tests
- fixtures
- examples
- docs
- typing/type_check

These should be discounted by default unless the user explicitly asks to include them.

## Suggested Scoring Shape

Do not overcomplicate this at first.

Use a weighted additive score such as:

```text
relevance_score =
  severity_weight
  + zone_weight
  + objective_fit_weight
  + execution_model_weight
  + surface_weight
  + context_weight
  - noise_discount
```

Then map score to:

- `low`
- `moderate`
- `high`
- `urgent`

Keep thresholds explicit and documented.

## Suggested Priority Labels

Stage 2 should expose project-facing labels such as:

- `ignore_for_now`
- `watch`
- `worth_reviewing`
- `high_priority`
- `fix_first`

## Implemented Scoring Notes

The current implementation sharpens the architecture in a few practical ways:

- raw pattern severity uses the function's unadjusted cost label
- function context is scored separately instead of being folded into severity
- file-level relevance is derived from the highest-relevance function in that file
- project hotspot ranking uses relevance first and raw cost as a tie-breaker
- `top_functions` is preserved for compatibility, but now carries prioritized hotspots

Current score thresholds:

- `>= 60` -> `urgent` / `fix_first`
- `>= 40` -> `high` / `high_priority`
- `>= 20` -> `moderate` / `worth_reviewing`
- `>= 8` -> `low` / `watch`
- `< 8` -> `low` / `ignore_for_now`

Current weight families are explicit in `core/relevance_engine.py`:

- severity base
- Stage 1 file zone
- project objective fit
- execution model fit
- surface fit
- function context
- noise discount

This keeps Stage 2 deterministic while making the reasoning inspectable in JSON and text output.

These are easier for users than only numeric scores.

## Realistic Scenario Matrix

Stage 2 must behave sensibly in these cases.

### 1. Framework Library

Example: Flask-like repo

Expected behavior:

- tests/examples discounted
- dispatch/routing/blueprints boosted
- extension/core API paths boosted
- tiny helper functions in tests mostly suppressed

### 2. API Service

Example: FastAPI or Express service

Expected behavior:

- request handlers boosted
- serializers and middleware boosted
- startup-only setup paths lower than request hot paths unless serverless

### 3. Website / Web App

Expected behavior:

- UI/render paths matter
- route/controller/render glue matters
- docs/examples discounted

### 4. CLI Tool

Expected behavior:

- startup paths matter
- command dispatch matters
- one-off helper functions less important

### 5. Data Pipeline

Expected behavior:

- loops, batching, allocations, recursion on large data paths heavily boosted
- throughput-oriented logic prioritized

### 6. Serverless

Expected behavior:

- startup and cold-start paths boosted
- large initialization cost becomes more important

### 7. Mobile App

Expected behavior:

- startup, battery, network-sensitive paths boosted
- background polling and unnecessary loops boosted

### 8. Device Firmware + Cloud

Expected behavior:

- embedded loops and memory-sensitive code boosted
- cloud control-plane paths also important
- hybrid shape affects ranking on both sides

### 9. Microservices Repo

Expected behavior:

- service entrypoints, gateways, workers boosted
- internal tests and examples discounted

### 10. Test-Heavy Repo

Expected behavior:

- avoid surfacing noise as core priority
- explicitly note that most findings are in non-production zones

## Output Requirements

Stage 2 must improve output, not just add hidden scores.

### Terminal Output

For project mode:

- show top prioritized hotspots, not only top expensive ones
- include relevance label and reason
- surface why something was boosted or discounted

### Text Output

- include prioritized findings summary
- include “why this ranks high in this repo”

### JSON Output

Each function should include:

- raw cost
- context
- relevance result

Project JSON should include:

- prioritized hotspot list
- any filtered/discounted counts if available

## Completion Criteria

Stage 2 is complete when:

1. A deterministic relevance engine exists.
2. Relevance is attached to function reports.
3. Project summaries rank findings by relevance, not only raw severity.
4. Noise zones are discounted deterministically.
5. Critical zones and objective fit boost findings deterministically.
6. Terminal/text/json outputs expose relevance clearly.
7. Realistic scenario tests prove the ranking logic changes behavior meaningfully.

## Recommended Implementation Order

1. Add Stage 2 report contracts.
2. Build `core/relevance_engine.py`.
3. Feed Stage 1 profile + function context + patterns into relevance scoring.
4. Attach relevance results to functions.
5. Change project ranking to use relevance first, raw severity second.
6. Update formatters.
7. Add realistic tests per scenario.

## Guardrails

Do not do these in Stage 2:

- no AI
- no LLM ranking
- no dynamic/telemetry-based scoring
- no hidden magic weights without documentation

Keep it:

- explicit
- testable
- explainable
- stable

## Prompt For Implementation Chat

Use this exact prompt in another chat:

```text
Continue Solvix from C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE2.md.

Implement Stage 2 deterministic relevance weighting.

Goals:
1. Add Stage 2 relevance contracts to the report model.
2. Create a deterministic relevance engine that combines:
   - pattern severity
   - file zone classification
   - project objectives
   - execution models
   - surfaces
   - function context
   - noise-zone discounting
3. Attach relevance results to function reports.
4. Make project hotspot ranking use relevance first.
5. Update terminal/text/json output to expose relevance clearly.
6. Add tests for:
   - framework library
   - api service
   - website/web app
   - cli tool
   - data pipeline
   - serverless
   - firmware + cloud
   - microservices
   - test-heavy repository

Constraints:
- deterministic only
- no AI/model dependency
- weights must be explicit and explainable
- preserve backward compatibility where practical
- update docs/PROJECT_INTELLIGENCE_STAGE2.md if implementation sharpens the architecture
```
