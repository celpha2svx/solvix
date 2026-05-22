# Project Intelligence Stage 1

This document is the continuity plan for Solvix Stage 1 project intelligence. It is written so another chat or teammate can continue the work without reconstructing the design from memory.

## Mission

Stage 1 gives Solvix deterministic project awareness.

The goal is not to add AI yet. The goal is to make Solvix infer:

- what kind of repository this is
- what the repository is likely optimizing for
- which directories matter most
- which directories are mostly noise

This lets later ranking, filtering, and explanation systems operate on project intent instead of only raw computational patterns.

## Architecture Summary

Stage 1 introduces a deterministic profiling layer:

- source: [project_profiler.py](/C:/Users/Adminn/Solvix/core/project_profiler.py)
- contracts: [report.py](/C:/Users/Adminn/Solvix/core/report.py)
- integration: [engine.py](/C:/Users/Adminn/Solvix/core/engine.py)
- output surfaces:
  - [terminal_formatter.py](/C:/Users/Adminn/Solvix/output/terminal_formatter.py)
  - [text_formatter.py](/C:/Users/Adminn/Solvix/output/text_formatter.py)
  - [json_formatter.py](/C:/Users/Adminn/Solvix/output/json_formatter.py)

## What Stage 1 Currently Does

The profiler currently derives:

- `primary_profile`
- `secondary_profiles`
- `execution_models`
- `surfaces`
- `web_shape`
- `service_topology`
- `hybrid_shape`
- `confidence`
- `evidence`
- `project_type` as a compatibility alias for the primary profile
- `primary_objectives`
- `secondary_objectives`
- `primary_languages`
- `critical_zones`
- `noise_zones`
- `detected_markers`
- `explanation`

It does this from deterministic signals only:

- supported source file paths
- directory names
- known config files
- dependency/framework markers in config content
- entrypoint filename hints

## Current Profile Types

Current inferred primary or secondary profiles:

- `web_backend`
- `framework_library`
- `cli_tool`
- `data_pipeline`
- `sdk_library`
- `desktop_application`
- `mobile_application`
- `device_firmware`
- `serverless_application`
- `test_heavy_repository`
- `general_application`

These are coarse on purpose. Stage 1 should be stable and explainable before it becomes subtle.

Current refinement dimensions:

- `web_shape`
  - `api_service`
  - `website_web_app`
  - `mixed_web_surface`
- `service_topology`
  - `distributed_monolith`
  - `microservices`
- `hybrid_shape`
  - `device_firmware_cloud`
  - `device_firmware_serverless`

## Current Objective Mapping

Current deterministic objective bundles:

- `web_backend`
  - primary: `request_overhead`, `latency`, `maintainability`
  - secondary: `startup_time`, `serialization_efficiency`
- `framework_library`
  - primary: `api_stability`, `extension_stability`, `maintainability`
  - secondary: `request_overhead`, `startup_time`
- `cli_tool`
  - primary: `startup_time`, `user_feedback`, `maintainability`
  - secondary: `memory_efficiency`, `throughput`
- `data_pipeline`
  - primary: `throughput`, `memory_efficiency`, `reliability`
  - secondary: `startup_time`, `maintainability`
- `sdk_library`
  - primary: `api_stability`, `serialization_efficiency`, `maintainability`
  - secondary: `request_overhead`, `memory_efficiency`
- `desktop_application`
  - primary: `startup_time`, `user_feedback`, `maintainability`
  - secondary: `memory_efficiency`, `api_stability`
- `mobile_application`
  - primary: `startup_time`, `battery_efficiency`, `network_efficiency`
  - secondary: `maintainability`, `memory_efficiency`
- `device_firmware`
  - primary: `reliability`, `memory_efficiency`, `device_constraints`
  - secondary: `latency`, `maintainability`
- `serverless_application`
  - primary: `startup_time`, `latency`, `reliability`
  - secondary: `request_overhead`, `memory_efficiency`
- `test_heavy_repository`
  - primary: `maintainability`, `feedback_speed`, `test_reliability`
  - secondary: `startup_time`
- `general_application`
  - primary: `maintainability`, `efficiency`, `readability`
  - secondary: `startup_time`, `memory_efficiency`

## Current Deterministic Rules

### Dependency markers

Framework or runtime hints are detected from:

- `pyproject.toml`
- `requirements.txt`
- `package.json`
- `go.mod`
- `Cargo.toml`
- `Gemfile`
- `composer.json`
- `pom.xml`
- `build.gradle`
- `build.gradle.kts`

Marker families:

- web: `flask`, `django`, `fastapi`, `starlette`, `uvicorn`, `gunicorn`, `express`, `koa`, `rails`, `spring`
- CLI: `click`, `typer`, `argparse`, `commander`, `yargs`, `cobra`
- data: `airflow`, `pandas`, `spark`, `dbt`, `dask`, `beam`
- SDK/client: `sdk`, `client`, `clients`, `api_client`, `http_client`
- serverless: `serverless`, `lambda`, `functions-framework`, `azure-functions`
- desktop: `electron`, `tauri`, `pyqt`, `pyside`, `wpf`, `winforms`
- mobile: `react-native`, `flutter`, `android`, `ios`, `swiftui`, `jetpack`
- firmware: `freertos`, `stm32`, `zephyr`, `arduino`, `esp-idf`
- website: `react`, `next`, `nextjs`, `nuxt`, `vue`, `angular`, `sveltekit`, `gatsby`, `remix`

### Noise zones

Current default noise-zone directory names:

- `test`, `tests`, `testing`
- `spec`, `specs`
- `fixtures`
- `examples`, `example`
- `docs`, `doc`
- `benchmarks`, `benchmark`
- `migrations`
- `type_check`, `typing`

### Critical zones

Current critical-zone inference prefers:

- `src`, `app`, `apps`, `flask`, `core`, `lib`, `package`
- web/framework add-ons:
  - `views`, `routes`, `routing`, `dispatch`, `templates`, `blueprints`
- CLI add-ons:
  - `cli`, `commands`, `bin`
- data add-ons:
  - `pipeline`, `pipelines`, `jobs`, `etl`

If no known critical zones are found, the profiler falls back to the first few non-noise top-level source directories.

### Per-file zones

Each analyzed file is also classified into:

- `critical`
- `supporting`
- `noise`

Stable reason codes currently include:

- `noise_directory`
- `critical_directory`
- `entrypoint_file`
- `web_route_path`
- `website_ui_path`
- `cli_surface_path`
- `pipeline_execution_path`
- `firmware_path`
- `serverless_function_path`
- `mobile_platform_path`
- `hybrid_cloud_control_path`
- `service_root_path`
- `production_code_path`
- `supporting_code_path`

## Multi-Dimensional Model

Stage 1 no longer treats a repository as one rigid bucket.

It now models several dimensions independently:

- primary profile
- secondary profiles
- execution models
- surfaces
- web shape
- service topology
- hybrid repo shape
- objectives
- critical zones
- noise zones
- evidence and confidence

This lets mixed repositories express shapes like:

- web backend + CLI tool
- device firmware + cloud API
- framework library + request path
- serverless application + background jobs

## What This Enables

Stage 1 is the base for the next systems:

- Stage 2 relevance weighting
- Stage 3 zone classification refinement
- Stage 4 multi-lens reporting
- Stage 5 optional AI overlay

Without Stage 1, the tool only knows code patterns.
With Stage 1, the tool starts to know what the repo is trying to be.

## Current Gaps

Stage 1 is intentionally incomplete.

Known gaps:

- profile taxonomy is still coarse
- no per-file relevance weighting yet
- no test/example exclusion switch yet
- no framework-specific path weighting yet
- no import-graph or call-graph awareness
- confidence still needs continued calibration for more edge-case repos
- evidence is improving but still does not use import-graph or call-graph structure
- language mix is only top-three counts, not full distribution
- dependency extraction is only partially schema-aware today

## Completed Stage 1B

These deterministic improvements are now complete inside Stage 1:

1. Parse `pyproject.toml` and `package.json` structurally instead of string matching.
2. Introduce weighted evidence scoring instead of flat confidence heuristics.
3. Detect “repo zones” per file, not just project-wide lists.
4. Split `web_backend` into API service vs website/web app where evidence supports it.
5. Distinguish distributed monoliths from true microservice layouts more carefully.
6. Add a `--focus` concept later, but not until Stage 2 weighting exists.
7. Add optional exclusion summaries:
   - tests
   - examples
   - docs
   - generated code

Still deferred until later stages:

1. Add a `--focus` concept after Stage 2 weighting exists.
2. Add optional exclusion summaries in user-facing reporting, not just internal zone detection.
3. Introduce import-graph and call-graph aware evidence.

## Stage 2 Preview

Stage 2 should not reinvent profiling.

It should consume Stage 1 profile output and weight findings such as:

- pattern severity
- project critical zone
- project type
- objective relevance
- noise-zone discount

That means Stage 2 should likely introduce:

- `relevance_score`
- `relevance_reason`
- `zone_classification`

at file and function level.

## Testing Strategy

Current coverage exists in:

- [test_all.py](/C:/Users/Adminn/Solvix/tests/test_all.py)

Current tests verify:

- project reports include profile fields
- framework-shaped fake repos infer `framework_library`
- noise zones and critical zones are attached
- JSON saved project mode prints a compact summary instead of terminal flood
- API services vs website web apps
- distributed monoliths vs microservices
- firmware cloud vs firmware serverless hybrids
- serverless, mobile, desktop, CLI, data pipeline, SDK, and test-heavy repo shapes

Recommended next tests:

- mixed-language repo shape
- repos with disagreeing manifests
- deliberately ambiguous repos that should stay moderate confidence
- “general application” fallback

## Release Note Guidance

If shipping this work:

- describe it as “Stage 1 deterministic project profiling”
- do not describe it as AI
- do not promise objective-perfect prioritization yet
- emphasize that it adds project-type and objective inference to improve future prioritization

## Continuation Instruction

If another chat continues from here, the next instruction should be:

“Continue Stage 1 project intelligence by calibrating ambiguous edge-case repos and preparing Stage 2 relevance weighting on top of the deterministic Stage 1 profile.”

“Continue Stage 1 project intelligence by improving schema-aware dependency parsing, weighted evidence scoring, and per-file zone classification before Stage 2 relevance weighting.”
