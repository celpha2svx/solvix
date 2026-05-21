# Solvix Architecture

## North Star

Solvix should survive changes in languages, editors, deployment models, and AI trends by keeping one invariant:

**all product surfaces consume the same analysis engine through stable contracts.**

That means:

- the CLI is a delivery surface, not the product core
- the VS Code extension is a presentation surface, not a forked analyzer
- the cloud service is an orchestration surface, not a rewrite
- language support is pluggable
- rule logic is data-driven where possible
- output formats are adapters, not branches in business logic

If we protect those boundaries, Solvix can evolve for decades without collapsing under its own success.

## Recommended Repository Shape

Use a monorepo, but make package ownership explicit.

```text
solvix/
├── pyproject.toml
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ADRs/
│   └── RFCs/
├── packages/
│   ├── core/
│   │   ├── src/solvix_core/
│   │   └── tests/
│   ├── cli/
│   │   ├── src/solvix_cli/
│   │   └── tests/
│   ├── plugin/
│   │   ├── vscode/
│   │   └── tests/
│   ├── cloud/
│   │   ├── src/solvix_cloud/
│   │   └── tests/
│   ├── schemas/
│   │   └── solvix_schema/
│   └── fixtures/
│       ├── samples/
│       └── corpora/
├── tooling/
│   ├── scripts/
│   └── ci/
└── .github/
    └── workflows/
```

## Why This Shape Wins Long Term

- `packages/core` owns parsing, normalization, rule evaluation, scoring, and context analysis.
- `packages/schemas` owns shared DTOs and versioned JSON schemas for reports and APIs.
- `packages/cli` depends on `core` and `schemas` only.
- `packages/plugin` depends on `schemas` for wire contracts and calls the CLI or cloud, depending on mode.
- `packages/cloud` depends on `core` and `schemas`, then adds persistence, auth, queues, and team workflows.
- `packages/fixtures` gives every surface the same gold-standard test inputs.

This avoids the classic failure mode where the editor, CLI, and service all drift into slightly different analyzers.

## Architectural Principles

1. Core first. Every capability must land in `core` before it lands anywhere else.
2. Contracts before convenience. Shared data models must be versioned and documented.
3. Deterministic by default. The same source input should yield the same analysis output across CLI, plugin, and cloud.
4. Offline-first local analysis. A developer should get value without internet access.
5. Policy outside engine. Team thresholds, CI gates, and org-specific rules belong in config and cloud policy layers.
6. Graceful degradation. If a language parser fails, Solvix should isolate the failure and keep the rest of the analysis running.
7. Forward compatibility. New node types, severities, and metadata fields must be additive, not breaking.

## Core Domain Model

The current `SolvixFunction` and `SolvixNode` idea is solid, but it should be formalized into a richer intermediate representation.

### IR Layers

1. `RawParseArtifact`
   - parser name
   - parser version
   - language
   - source hash
   - raw function spans

2. `NormalizedFunction`
   - stable function id
   - name
   - qualified name
   - file path
   - line range
   - arguments
   - modifiers
   - body nodes
   - diagnostics

3. `NormalizedNode`
   - node kind
   - source span
   - depth
   - parent id
   - child ids
   - symbol name
   - attributes
   - evidence

4. `PatternMatch`
   - pattern id
   - title
   - severity
   - confidence
   - evidence spans
   - explanation
   - suggestion
   - tags

5. `FunctionAssessment`
   - function metadata
   - pattern matches
   - raw score
   - adjusted score
   - cost label
   - context result
   - generated recommendations

### Why Add IDs and Attributes

Stable ids let us:

- diff results between runs
- support editor inline decorations
- store historical cloud results
- compare parser improvements across versions
- train future heuristics without changing frontends

## Runtime Pipeline

Every surface should call the same pipeline:

```text
Discover Inputs
  -> Detect Language
  -> Parse
  -> Normalize to IR
  -> Enrich Symbols/Context
  -> Run Universal Rules
  -> Run Language-Specific Rules
  -> Score
  -> Adjust for Context
  -> Render / Serialize / Persist
```

This gives clean extension points and makes profiling easier.

## Package Responsibilities

### `packages/core`

Owns:

- language detection
- file safety checks
- parser adapters
- AST normalization
- universal pattern engine
- language-specific pattern packs
- scoring
- context analysis
- report assembly

Suggested internal modules:

```text
solvix_core/
├── analysis/
│   ├── engine.py
│   ├── pipeline.py
│   ├── scoring.py
│   └── context.py
├── contracts/
│   ├── ir.py
│   ├── reports.py
│   └── errors.py
├── discovery/
│   ├── files.py
│   └── language.py
├── parsing/
│   ├── base.py
│   ├── python_ast.py
│   ├── treesitter.py
│   └── registry.py
├── rules/
│   ├── engine.py
│   ├── universal/
│   ├── language_specific/
│   └── metadata.py
├── render/
│   ├── report_builder.py
│   └── summaries.py
└── utils/
```

### `packages/schemas`

Owns external contracts:

- JSON schema for CLI `--json`
- API request and response schemas
- plugin transport payloads
- future SARIF export schema mapping

This should be versioned independently so external integrations can trust it.

### `packages/cli`

Owns:

- Click or Typer command surface
- terminal rendering with `rich`
- exit codes
- config loading
- local cache handling

The CLI should remain thin. If a logic change requires edits here and in `core`, that is a warning sign.

### `packages/plugin`

Owns:

- VS Code commands
- inline decorations
- code lens and hover presentation
- file-watch debouncing
- local CLI bridge
- optional cloud handoff

The plugin should prefer calling the local CLI in development mode so results stay aligned with the user's installed engine.

### `packages/cloud`

Owns:

- authenticated API
- repository ingestion
- background analysis jobs
- results storage
- historical diffs
- team policy and thresholds
- CI status integration

Cloud should not invent new analysis semantics. It should orchestrate and persist the same engine.

## Parser Strategy

Your current spec uses Python `ast` plus tree-sitter for everything else. That is a good starting point and should stay.

For longevity:

- keep parser adapters isolated from rule logic
- produce the same normalized node vocabulary regardless of parser source
- store parser diagnostics beside successful partial results
- support parser capability flags per language

Example capability flags:

- `supports_async_semantics`
- `supports_symbol_resolution`
- `supports_qualified_names`
- `supports_comment_scan`

This prevents forcing fake parity where language grammars differ.

### Native Parser Operations

For long-term durability, native parser infrastructure should be treated as an operational dependency, not a lucky import:

- `tree-sitter-language-pack` is the preferred multi-language backend
- parser artifacts should be pre-downloaded during workstation or CI bootstrap
- Solvix should expose whether it is running in native, compatibility, or degraded mode
- heuristic parsing must remain a last-resort fallback, never a silent substitute

## Rule Engine Design

Do not hardcode all intelligence as `if/else` branches forever. That becomes brittle.

Use a hybrid model:

- structural rules implemented in Python for complex traversal
- metadata-driven pattern definitions for naming, severity defaults, suggestions, and docs

Each rule should expose:

- `rule_id`
- `applies_to`
- `required_capabilities`
- `run(function, context) -> list[PatternMatch]`

That allows:

- selective rule execution
- performance profiling by rule
- feature flags
- enterprise policy packs later

## Scoring Model

Keep the current weighted severity model, but separate:

- `base_score`
- `context_adjusted_score`
- `cost_label`
- `confidence`

Why:

- score explains the mechanical cost
- label explains the user-facing interpretation
- confidence explains how certain Solvix is

That confidence field matters once you support many languages and partial parser fallbacks.

## Context Intelligence

The proposed lightweight context analyzer is the right seed, but it should be treated as a module that grows in layers.

### Context Tiers

1. Local context
   - same-file call sites
   - loop containment
   - function naming

2. Project context
   - cross-file references
   - framework lifecycle hooks
   - test path detection

3. Runtime context
   - optional profiling imports
   - optional coverage hot paths
   - optional benchmark metadata

CLI v1 can ship with tier 1. The architecture should leave room for tiers 2 and 3 without redesign.

## Output Boundaries

Never let rendering logic leak back into analysis.

Output should be built from report contracts through formatter adapters:

- terminal formatter
- JSON formatter
- SARIF formatter
- LSP/editor formatter
- cloud API serializer

This is how you avoid rebuilding the same summary logic five times.

## Storage and Caching

Even local CLI should have a small cache layer.

Suggested cache keys:

- file content hash
- parser version
- rule pack version
- config version

Suggested local cache uses:

- avoid re-parsing unchanged files
- speed editor integrations
- compare before/after analysis

Cloud storage should separate:

- immutable analysis artifacts
- repository snapshots
- team policies
- user comments and triage state

## Config Model

Adopt one root config file early:

```text
solvix.toml
```

Possible fields:

- include/exclude globs
- severity thresholds
- language overrides
- disabled rules
- project tags
- framework hints
- output defaults

If config lands late, every surface invents its own flags and the platform drifts.

## Versioning Strategy

Version these independently:

- core engine version
- schema version
- rule pack version
- parser bundle version

Why this matters:

- plugin can warn when CLI schema is outdated
- cloud can re-run old artifacts against new rule packs
- users can reproduce historical analysis results

## API and Cloud Evolution

When you build cloud, expose analysis as jobs, not synchronous giant requests.

Core endpoints should look conceptually like:

- submit analysis job
- fetch job status
- fetch artifact summary
- fetch function assessments
- compare two runs
- fetch project hotspots

Use asynchronous job execution from day one. Repo-scale analysis will outgrow request-response quickly.

## Observability

If Solvix is meant to grow into infrastructure, make it observable early.

Track:

- parse time by language
- rule execution time by rule id
- files skipped by reason
- syntax failures by language
- result counts by severity

This will tell you where the engine is slow, weak, or noisy.

## Testing Strategy

Testing should mirror the architecture.

### Core tests

- parser contract tests per language
- IR normalization snapshot tests
- rule unit tests
- scoring tests
- context analyzer tests

### Cross-surface tests

- CLI golden output tests
- JSON schema validation tests
- plugin transport contract tests
- cloud API contract tests

### Long-life safety nets

- fixture corpus for real-world repositories
- regression tests for false positives
- performance benchmarks on large repositories

Do not rely only on toy samples. Samples prove basics; corpora prove durability.

## Security and Trust

Solvix reads source code, so trust boundaries matter.

Non-negotiables:

- never execute analyzed code
- treat files as untrusted input
- isolate parser failures
- redact secrets from cloud uploads where possible
- make cloud upload opt-in

For the plugin and cloud era, privacy posture becomes a product feature.

## Release Phases

### Phase 1: Local Engine

Ship:

- `core`
- `cli`
- JSON schema v1
- parser adapters for the first language set
- universal rules

### Phase 2: Editor Experience

Ship:

- plugin shell
- local CLI bridge
- inline diagnostics
- debounce and cache

### Phase 3: Team Platform

Ship:

- cloud API
- job queue
- persistence
- project dashboards
- CI integration

### Phase 4: Intelligence Expansion

Ship:

- rule packs
- framework-aware context
- historical trend analysis
- performance baselining

## Immediate Recommendation

Do not build the original flat folder layout exactly as written if the goal is true longevity. It is good for a prototype, but it will tighten into knots once plugin and cloud arrive.

Build this instead:

1. Start with the monorepo now.
2. Put all analysis semantics in `packages/core`.
3. Define versioned contracts in `packages/schemas`.
4. Keep the CLI thin in `packages/cli`.
5. Treat plugin and cloud as future consumers, not future rewrites.

## Final Architectural Bet

The winning long-term architecture for Solvix is:

- **monorepo**
- **shared core engine**
- **versioned schemas**
- **thin delivery surfaces**
- **pluggable parsers**
- **rule-engine isolation**
- **async cloud orchestration later**

That gives you something strong enough to start small, but clean enough to still make sense when Solvix has a CLI, an editor presence, CI hooks, team dashboards, and years of rule evolution behind it.
