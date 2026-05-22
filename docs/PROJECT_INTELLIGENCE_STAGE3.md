# Project Intelligence Stage 3

This document defines Stage 3 of Solvix project intelligence.

Stage 1 gave Solvix deterministic project awareness.
Stage 2 gave Solvix deterministic relevance weighting.
Stage 3 gives Solvix deterministic **signal synthesis**.

The mission of Stage 3 is to turn many ranked findings into a smaller number of
clear, decision-ready insights.

## Mission

Stage 3 should answer:

- what are the main efficiency or risk themes in this repository
- which findings belong together
- what should a maintainer do first, second, and later
- why the repository feels noisy or clean overall
- how to compress hundreds of findings into a few useful stories

Stage 3 is still deterministic.
No AI should be required here.

## Why Stage 3 Exists

Even with Stage 2, a large repository can still produce too many individually
reasonable findings.

Users usually do not want:

- 400 isolated function entries
- 30 repeated variations of the same underlying issue
- a hotspot list without repo-level interpretation

Users usually do want:

- the top themes
- the top zones
- the top action buckets
- a sane execution order

So Stage 3 should transform:

- ranked findings

into:

- grouped insights
- prioritized remediation lanes
- project-level narrative

## Inputs

Stage 3 consumes:

- Stage 1 project profile
- Stage 1 per-file zone classification
- Stage 2 function relevance results
- Stage 2 file relevance results
- raw function pattern matches
- file summaries
- project summary counts

From Stage 1 specifically, Stage 3 should use:

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

From Stage 2 specifically, Stage 3 should use:

- `relevance.score`
- `relevance.level`
- `relevance.project_priority_label`
- `relevance.factors`
- project prioritized hotspots
- discounted-function counts

## Core Outcome

Stage 3 should produce a synthesis layer above individual findings.

At minimum, the project report should gain:

- grouped finding themes
- top zones by concentration and importance
- action lanes
- summary verdicts
- noise diagnostics

The output should help a user decide:

- where to start
- what can wait
- what is mostly repeated signal
- whether the repo has one big issue or many small ones

## Proposed Data Model

Stage 3 should introduce contracts roughly like:

```python
@dataclass
class InsightTheme:
    key: str
    title: str
    summary: str
    relevance_score: int
    priority_label: str
    pattern_families: list[str]
    representative_examples: list[dict[str, Any]]
    affected_files: int
    affected_functions: int
    critical_zone_hits: int
    noise_zone_hits: int

@dataclass
class ActionLane:
    key: str
    title: str
    why_now: str
    recommended_order: int
    related_theme_keys: list[str]
    representative_targets: list[dict[str, Any]]

@dataclass
class NoiseDiagnostic:
    discounted_functions: int
    dominant_noise_zones: list[str]
    summary: str

@dataclass
class SynthesisSummary:
    dominant_themes: list[InsightTheme]
    action_lanes: list[ActionLane]
    noise_diagnostic: NoiseDiagnostic
    repository_story: str
    maintainer_brief: str
```

These can be attached as:

- a new `synthesis` field on `ProjectReport`
- optionally condensed fields on `ProjectSummary`

Current implementation note:

- each theme key is formed as `lane_key:pattern_family`
- themes keep a `dominant_zone` and `repetition_score`
- the noise diagnostic also reports a deterministic `noise_ratio`

## Stage 3 Philosophy

Stage 3 should not invent new scores from nowhere.
It should compress and reorganize existing deterministic evidence.

Think of it as:

`repo guidance = grouped Stage 2 relevance + repeated pattern families + zone concentration + project objectives`

This means:

- ten similar request-path findings may become one request-path theme
- repeated test-only findings may become a noise diagnostic, not a top theme
- one urgent hotspot may remain an urgent singleton if it is uniquely severe
- multiple moderate findings in one critical zone may outrank one isolated expensive finding

## Deterministic Grouping Dimensions

Stage 3 should group findings using explicit, explainable dimensions.

### 1. Pattern Family

Raw pattern names should map into broader deterministic families, such as:

- `loop_amplification`
- `allocation_churn`
- `serialization_cost`
- `recursive_risk`
- `async_blocking`
- `data_copying`
- `control_flow_complexity`

Examples:

- `nested_loop` -> `loop_amplification`
- `string_concatenation_in_loop` -> `allocation_churn`
- `memory_allocation_in_loop` -> `allocation_churn`
- `data_copy_in_loop` -> `data_copying`
- `async_blocking_in_loop` -> `async_blocking`
- `deep_nesting` -> `control_flow_complexity`

### 2. Zone Concentration

Stage 3 should notice where findings accumulate:

- request-path/core zones
- startup zones
- background-job zones
- mobile/device zones
- extension/api zones
- noise zones

This should help distinguish:

- “many findings, but mostly in tests”
from:
- “many findings, clustered in production request paths”

### 3. Objective Pressure

Themes should be described in the language of the repo’s objectives.

Examples:

- API service:
  - “Request-path loop amplification is the dominant cost theme.”
- CLI:
  - “Startup-sensitive command preparation is the main issue.”
- Data pipeline:
  - “Batch throughput is being dragged by nested iteration.”
- Framework library:
  - “Dispatch and extension-path complexity dominate the follow-up list.”

### 4. Repetition Density

A theme with many medium findings can matter more than one isolated high finding.

Stage 3 should track:

- number of affected functions
- number of affected files
- whether they are concentrated in critical zones

This supports statements like:

- “The main issue is not one catastrophic hotspot, but repeated allocation churn across worker paths.”

### 5. Noise Pressure

Stage 3 should explicitly summarize when the repo is noisy.

Examples:

- “Most discounted findings are in tests and examples.”
- “The repo is test-heavy; only two findings remain high-signal after discounting.”

This is better than silently hiding everything.

## Theme Scoring

Stage 3 should score themes explicitly.

A first deterministic shape could be:

```text
theme_score =
  sum(relevance_score of member functions, capped per file)
  + critical_zone_bonus
  + repetition_bonus
  - noise_penalty
```

Important guardrail:

- cap per-file contribution so one huge file does not monopolize the whole project story

Current implementation note:

- per-file contribution is capped explicitly in `core/synthesis_engine.py`
- the current default cap is `75` points per file per theme

Suggested ingredients:

- member relevance sum
- number of affected critical files
- number of affected functions
- number of unique files
- noise-zone ratio

## Action Lanes

Stage 3 should not stop at themes.
It should also define action lanes.

An action lane is a deterministic remediation bucket, for example:

- `request_path_hotspots`
- `startup_path_cleanup`
- `pipeline_throughput_fixes`
- `device_memory_pressure`
- `dispatch_complexity_review`
- `noise_cleanup_only`

Each lane should answer:

- why this lane exists
- which themes feed into it
- what a maintainer should inspect first

This makes the report feel actionable rather than descriptive only.

## Output Requirements

Stage 3 must improve output, not just add hidden clustering.

### Terminal Output

Project mode should show:

- repository story
- top 3 themes
- top 3 action lanes
- a short noise diagnostic

It should still allow drill-down into hotspots, but themes should come first.

### Text Output

Saved text reports should include:

- a synthesis section
- grouped themes
- action lanes
- maintainer brief

### JSON Output

Project JSON should include:

- synthesis summary
- themes
- action lanes
- noise diagnostic

Function-level detail should remain available for machine consumers.

## Realistic Scenario Matrix

Stage 3 must behave sensibly in these cases.

### 1. Framework Library

Expected behavior:

- group routing/dispatch findings into one core theme
- suppress test/example sprawl into noise diagnostics
- action lane should point toward framework core, not fixtures

### 2. API Service

Expected behavior:

- merge handler/serializer/middleware findings into request-path themes
- separate startup-only themes from request-hot themes

### 3. Website / Web App

Expected behavior:

- group UI/render/update work into a front-end responsiveness theme
- docs/examples mostly shift into noise diagnostic

### 4. CLI Tool

Expected behavior:

- emphasize startup and command dispatch themes
- avoid over-promoting helper noise

### 5. Data Pipeline

Expected behavior:

- group throughput-related loop and allocation issues into one dominant lane
- show whether the pain is concentrated in one pipeline or many jobs

### 6. Serverless

Expected behavior:

- separate cold-start/init concerns from request-handler concerns
- make startup-sensitive actions visually first-class

### 7. Mobile App

Expected behavior:

- surface battery/network/render themes
- distinguish polling or update-loop repetition from isolated helpers

### 8. Device Firmware + Cloud

Expected behavior:

- produce at least two clear lanes when appropriate:
  - device-side pressure
  - cloud-side request/control pressure

### 9. Microservices Repo

Expected behavior:

- group by service-entrypoint and worker/gateway lanes
- make it obvious whether the problem is broad or service-local

### 10. Test-Heavy Repo

Expected behavior:

- produce a strong noise diagnostic
- avoid pretending the repo has major production hotspots when it mostly has test churn

## Completion Criteria

Stage 3 is complete when:

1. A deterministic synthesis engine exists.
2. Function findings are grouped into explainable themes.
3. Themes produce stable action lanes.
4. Noise is summarized explicitly, not just discounted silently.
5. Terminal/text/json outputs expose synthesis clearly.
6. Realistic scenario tests prove grouped outputs are meaningfully better than flat hotspot lists.

## Recommended Implementation Order

1. Add Stage 3 report contracts.
2. Create a deterministic synthesis engine in a module such as `core/synthesis_engine.py`.
3. Map raw patterns into theme families.
4. Group functions into themes using:
   - pattern family
   - zone
   - project objective pressure
5. Score themes and derive action lanes.
6. Attach synthesis to `ProjectReport`.
7. Update terminal/text/json output.
8. Add tests for the scenario matrix.

## Guardrails

Do not do these in Stage 3:

- no AI summarization
- no embedding clustering
- no opaque grouping heuristics
- no dropping raw findings

Keep it:

- deterministic
- explainable
- additive
- compatible with Stage 1 and Stage 2

## Prompt For Implementation Chat

Use this exact prompt in another chat:

```text
Continue Solvix from:
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE1.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE2.md
- C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE3.md

Implement Stage 3 deterministic signal synthesis.

Goals:
1. Add Stage 3 synthesis contracts to the report model.
2. Create a deterministic synthesis engine that:
   - maps raw patterns into theme families
   - groups findings into repo-level themes
   - scores themes using Stage 2 relevance plus zone concentration and repetition
   - derives action lanes
   - produces a noise diagnostic
3. Attach synthesis to project reports.
4. Update terminal/text/json outputs to expose:
   - repository story
   - top themes
   - action lanes
   - noise diagnostic
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
- keep raw function detail available
- preserve backward compatibility where practical
- update C:\Users\Adminn\Solvix\docs\PROJECT_INTELLIGENCE_STAGE3.md if implementation sharpens the architecture

Implementation expectations:
- add a module like C:\Users\Adminn\Solvix\core\synthesis_engine.py
- keep grouping rules and theme-family mappings explicit in code
- cap per-file contribution when scoring themes
- ensure tests pass with `py -3 -m unittest tests.test_all`
```
