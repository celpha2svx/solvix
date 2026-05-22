# Project Intelligence Stage 4

This document defines Stage 4 of Solvix project intelligence.

Stage 1 gave Solvix deterministic project awareness.
Stage 2 gave Solvix deterministic relevance weighting.
Stage 3 gave Solvix deterministic signal synthesis.
Stage 4 gives Solvix deterministic **multi-lens reporting**.

The mission of Stage 4 is to let the same repository be viewed through
different engineering priorities without changing the underlying facts.

## Mission

Stage 4 should answer:

- what matters most if I care about performance
- what matters most if I care about startup
- what matters most if I care about maintainability
- what matters most if I care about reliability
- what matters most if I care about cloud/runtime cost

Stage 4 is still deterministic.
No AI should be required here.

## Why Stage 4 Exists

By the end of Stage 3, Solvix can already:

- understand the repo
- rank findings by repo relevance
- group findings into themes
- produce action lanes

But large software systems still have multiple legitimate engineering lenses.

The same codebase may need different answers for:

- platform team
- performance team
- framework maintainer
- mobile engineer
- reliability engineer
- cloud-cost owner

Stage 4 should not create new raw findings.
It should re-interpret Stage 1–3 outputs through a selected deterministic lens.

## Core Idea

Stage 4 should introduce the concept of a **lens**.

A lens is a deterministic reporting profile that:

- reweights existing themes
- reorders action lanes
- changes which summaries are surfaced first
- explains why this lens changes the prioritization

Examples:

- `performance`
- `startup`
- `maintainability`
- `reliability`
- `cloud_cost`
- `battery`
- `api_stability`

## Inputs

Stage 4 consumes:

- Stage 1 project profile
- Stage 2 relevance results
- Stage 3 themes
- Stage 3 action lanes
- Stage 3 noise diagnostics
- project summary counts

From Stage 1 specifically, Stage 4 should use:

- `primary_profile`
- `secondary_profiles`
- `execution_models`
- `surfaces`
- `web_shape`
- `service_topology`
- `hybrid_shape`
- `primary_objectives`
- `secondary_objectives`

From Stage 2 specifically, Stage 4 should use:

- function relevance
- file relevance
- relevance factors

From Stage 3 specifically, Stage 4 should use:

- `dominant_themes`
- `action_lanes`
- `noise_diagnostic`
- `repository_story`
- `maintainer_brief`

## Core Outcome

Stage 4 should produce one or more lens-specific views of the same repo.

At minimum, project reports should gain:

- available lenses
- a default lens
- lens-specific top themes
- lens-specific action lanes
- lens-specific summary text

This should let users ask:

- “show me the performance view”
- “show me startup-first ordering”
- “show me reliability-first ordering”

without recomputing raw analysis differently.

## Proposed Data Model

Stage 4 should introduce contracts roughly like:

```python
@dataclass
class LensFactor:
    name: str
    weight: int
    reason: str

@dataclass
class LensThemeView:
    theme_key: str
    score: int
    priority_label: str
    reason: str
    factors: list[LensFactor]

@dataclass
class LensLaneView:
    lane_key: str
    score: int
    reason: str

@dataclass
class LensReport:
    lens: str
    title: str
    summary: str
    top_themes: list[LensThemeView]
    top_lanes: list[LensLaneView]
    recommended_first_action: str

@dataclass
class MultiLensSummary:
    default_lens: str
    available_lenses: list[str]
    reports: list[LensReport]
```

These can be attached as:

- a new `multi_lens` field on `ProjectReport`
- optionally a compact lens summary on `ProjectSummary`

## Lens Philosophy

Stage 4 must not change the truth.

It should change:

- ordering
- emphasis
- explanation

It should not change:

- raw findings
- Stage 1 profile
- Stage 2 relevance facts
- Stage 3 grouped themes

So the principle is:

`same evidence, different deterministic viewpoint`

## Initial Lens Set

Stage 4 should start with a small explicit lens family.

### 1. `performance`

Use when the user wants:

- hot path speed
- request throughput
- loop and allocation pressure

Should boost:

- loop amplification
- allocation churn
- data copying
- repeated compute
- request-path themes
- pipeline throughput lanes

### 2. `startup`

Use when the user wants:

- CLI responsiveness
- cold-start sensitivity
- app/server boot performance

Should boost:

- startup path themes
- serverless cold-start lanes
- command dispatch lanes

### 3. `maintainability`

Use when the user wants:

- simplification
- long-term code health
- complexity reduction

Should boost:

- control-flow complexity
- recursive risk
- repeated patterns across many files
- framework dispatch complexity

### 4. `reliability`

Use when the user wants:

- safer production behavior
- resilient pipelines
- stable firmware/cloud behavior

Should boost:

- recursive risk
- async blocking
- firmware pressure
- worker/control-plane paths

### 5. `cloud_cost`

Use when the user wants:

- repeated runtime cost
- unnecessary hot-path churn
- request fan-out
- startup waste in serverless/cloud services

Should boost:

- network roundtrips
- repeated compute
- request-path pressure
- startup in serverless
- cloud control lanes

### 6. `battery`

Use when the user wants:

- mobile/device efficiency
- polling sensitivity
- repeated render/update loops

Should boost:

- mobile lanes
- device lanes
- allocation churn
- loop amplification
- repeated update/poll patterns

### 7. `api_stability`

Use when the user wants:

- stable public contracts
- safer extension and dispatch surfaces
- clearer request/handler contract pressure
- SDK/client-facing behavior that is less fragile over time

Should boost:

- dispatch complexity
- request and handler contract pressure where appropriate
- SDK/client/API-surface lanes
- repeated compute or complexity when it affects stable public surfaces

## Deterministic Lens Factors

Each lens should score Stage 3 themes with explicit additive factors.

Suggested factor families:

### 1. Theme Family Fit

Example:

- `performance` boosts:
  - `loop_amplification`
  - `allocation_churn`
  - `data_copying`
  - `repeated_compute`

### 2. Lane Fit

Example:

- `startup` boosts:
  - `startup_path_cleanup`
  - `command_dispatch_cleanup`

- `cloud_cost` boosts:
  - `request_path_hotspots`
  - `cloud_control_path`

### 3. Project Objective Fit

Lens scoring should also respect Stage 1 objectives.

Example:

- `performance` aligns strongly with:
  - `latency`
  - `throughput`
  - `request_overhead`

- `maintainability` aligns with:
  - `maintainability`
  - `api_stability`
  - `extension_stability`

### 4. Surface Fit

Example:

- `battery` boosts mobile/device repos more
- `cloud_cost` boosts http/serverless/distributed service repos more
- `startup` boosts cli/serverless repos more

### 5. Execution Model Fit

Example:

- `startup` boosts serverless and cli-heavy repos
- `performance` boosts request-response and background jobs
- `cloud_cost` boosts distributed services and serverless

### 6. Noise Sanity

Lenses should not destroy Stage 3 noise handling.

Even if a lens boosts something, it should not let test-only or docs-only themes
dominate unless the repo itself is genuinely test-heavy.

## Suggested Scoring Shape

Do not overcomplicate this at first.

Use an additive score such as:

```text
lens_theme_score =
  stage3_theme_score
  + theme_family_fit
  + lane_fit
  + project_objective_fit
  + execution_model_fit
  + surface_fit
  - noise_guardrail
```

Then map to:

- `watch`
- `worth_reviewing`
- `high_priority`
- `fix_first`

The raw Stage 3 score should still remain visible somewhere.

## Implemented Scoring Notes

The current implementation sharpens the architecture in a few practical ways:

- all seven initial lenses are always available:
  - `performance`
  - `startup`
  - `maintainability`
  - `api_stability`
  - `reliability`
  - `cloud_cost`
  - `battery`
- the default lens is selected deterministically from the Stage 1 primary profile, with a stored `default_lens_reason`
- each lens theme view keeps both:
  - the raw Stage 3 theme score
  - the lens-adjusted score
- lens factors are explicit in `core/multi_lens_engine.py` and include:
  - Stage 3 base score
  - theme-family fit
  - lane fit
  - project-objective fit
  - surface fit
  - execution-model fit
  - a noise guardrail
- project-objective, surface, and execution-model boosts are capped explicitly so repo-wide metadata cannot overpower the underlying Stage 3 theme signal
- lens lane ordering is derived by regrouping lens-scored themes, not by mutating Stage 3 lanes in place
- the `api_stability` lens is tuned to favor:
  - dispatch and extension lanes in framework and SDK repositories
  - request-path contract pressure in HTTP-shaped repositories
  - SDK and client-facing surfaces when stable public behavior matters more than raw throughput
- text, terminal, and JSON outputs expose:
  - `default_lens`
  - `available_lenses`
  - default-lens top themes
  - default-lens top lanes
  - a deterministic first action for the default lens

## Default Lens Selection

Stage 4 should choose a deterministic default lens from the profile.

Examples:

- `web_backend` -> `performance`
- `framework_library` -> `maintainability`
- `cli_tool` -> `startup`
- `data_pipeline` -> `performance`
- `serverless_application` -> `startup`
- `mobile_application` -> `battery`
- `device_firmware` -> `reliability`
- `sdk_library` -> `maintainability`

Users should later be able to override this with a CLI flag such as:

- `--focus performance`
- `--focus startup`
- `--focus maintainability`

But the first implementation can compute the lens reports without adding the CLI
switch yet, if that keeps the change safer.

## Output Requirements

Stage 4 must improve output, not just add hidden structures.

### Terminal Output

Project mode should show:

- default lens
- top themes for that lens
- top lanes for that lens
- one-line explanation of why that lens was chosen

### Text Output

Saved text reports should include:

- available lenses
- default lens
- lens-specific top themes
- lens-specific first action

### JSON Output

Project JSON should include:

- available lenses
- default lens
- lens reports

Function-level detail should still remain available separately.

## Realistic Scenario Matrix

Stage 4 must behave sensibly in these cases.

### 1. Framework Library

Expected behavior:

- default lens: `maintainability`
- dispatch complexity ranks above raw loop-only helper noise

### 2. API Service

Expected behavior:

- default lens: `performance`
- request-path themes lead
- `cloud_cost` lens also gives sensible alternative ordering

### 3. Website / Web App

Expected behavior:

- default lens: `performance`
- frontend responsiveness themes lead
- maintainability still promotes repeated complexity

### 4. CLI Tool

Expected behavior:

- default lens: `startup`
- command dispatch and boot themes lead

### 5. Data Pipeline

Expected behavior:

- default lens: `performance`
- throughput lanes dominate
- reliability lens still surfaces worker fragility differently

### 6. Serverless

Expected behavior:

- default lens: `startup`
- cold-start themes lead
- performance lens gives a different but still sane ranking

### 7. Mobile App

Expected behavior:

- default lens: `battery`
- polling/render/update themes lead

### 8. Device Firmware + Cloud

Expected behavior:

- default lens: `reliability`
- device and cloud lanes remain visible
- cloud_cost lens should raise cloud-control themes

### 9. Microservices Repo

Expected behavior:

- default lens: `performance`
- service entrypoints stay important
- cloud_cost lens promotes fan-out and request churn

### 10. Test-Heavy Repo

Expected behavior:

- default lens: `maintainability`
- noise diagnostics still dominate interpretation
- no lens should pretend the repo is production-hot if it mostly is not

## Completion Criteria

Stage 4 is complete when:

1. A deterministic multi-lens engine exists.
2. The project report exposes available lenses and a default lens.
3. Lens-specific theme ordering differs meaningfully where appropriate.
4. Lens scoring remains explainable and testable.
5. Noise guardrails still hold under every lens.
6. Terminal/text/json outputs expose the default lens clearly.
7. Scenario tests prove lens-specific ordering changes in realistic repos.

## Recommended Implementation Order

1. Add Stage 4 report contracts.
2. Create a module such as `core/multi_lens_engine.py`.
3. Define explicit lens families and weights.
4. Score Stage 3 themes per lens.
5. Derive lane views and a recommended first action per lens.
6. Attach multi-lens output to `ProjectReport`.
7. Update terminal/text/json output.
8. Add scenario tests.

## Guardrails

Do not do these in Stage 4:

- no AI summarization
- no opaque ranking
- no mutation of raw Stage 3 truth
- no per-user personalization yet

Keep it:

- deterministic
- explainable
- additive
- lens-based rather than magical

## Prompt For Implementation Chat

Use this exact prompt in another chat:

```text
Continue Solvix from:
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE1.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE2.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE3.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE4.md

Implement Stage 4 deterministic multi-lens reporting.

Goals:
1. Add Stage 4 multi-lens contracts to the report model.
2. Create a deterministic multi-lens engine that:
   - defines explicit lenses
   - scores Stage 3 themes per lens
   - derives lens-specific lane ordering
   - selects a deterministic default lens from the project profile
   - produces lens-specific summary text and first actions
3. Attach multi-lens output to project reports.
4. Update terminal/text/json outputs to expose:
   - default lens
   - available lenses
   - top themes for the default lens
   - top lanes for the default lens
5. Add tests for:
   - framework library
   - api service
   - website/web app
   - cli tool
   - data pipeline
   - serverless
   - mobile app
   - device firmware + cloud
   - microservices
   - test-heavy repository

Constraints:
- deterministic only
- no AI/model dependency
- do not mutate raw Stage 3 themes
- preserve backward compatibility where practical
- keep noise guardrails intact
- update C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE4.md if implementation sharpens the architecture

Implementation expectations:
- add a module like C:\Users\Adminn\Solvix\core\multi_lens_engine.py
- keep lens weights explicit in code
- ensure different lenses can produce meaningfully different ordering
- ensure tests pass with `py -3 -m unittest tests.test_all`
```
