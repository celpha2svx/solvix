# CLI UX And Release Readiness

This document defines the next practical polish phase for Solvix before broader
public rollout.

The goals are:

1. make CLI help feel polished and self-explanatory
2. make long-running actions feel alive with clear progress/status language
3. make Windows `winget` publication operationally ready
4. define a real smoke-test matrix for install, update, and runtime validation

This is not a new intelligence stage.
It is product and release hardening.

## 1. CLI Help UX

The root `solvix --help` experience should immediately answer:

- what Solvix is
- the main commands
- the fastest common examples
- how to get project analysis
- how to enable optional AI

### Root help goals

`solvix --help` should clearly surface:

- one-line purpose
- common usage examples
- major commands:
  - `analyze`
  - `doctor`
  - `bootstrap-parsers`
- optional AI overlay note
- where to get detailed help for subcommands

### Suggested root help example block

Examples should include at least:

```text
solvix analyze app.py
solvix analyze src --project
solvix analyze src --project --json --output report.json
solvix analyze src --project --ai-mode assist
solvix doctor
solvix bootstrap-parsers --all
```

### `analyze --help` goals

This should explain:

- file mode vs project mode
- `--function`
- `--project`
- `--json`
- `--output`
- `--lang`
- `--ai-mode`
- `--ai-model`

It should include examples for:

- single file
- single function
- project report
- saved JSON
- AI overlay

### `doctor --help` goals

This should explain:

- parser health
- cache state
- what the user should do with the result

### `bootstrap-parsers --help` goals

This should explain:

- when to use it
- offline / restricted environments
- `--all`

### Help style rules

Help text should be:

- concise
- operational
- example-driven
- not overly technical

Avoid:

- vague descriptions without examples
- AI-specific wording dominating the core CLI
- making optional features sound required

## 2. Progress And Status UX

Solvix should feel alive during longer operations.

Progress/status should exist for:

- project analysis
- parser bootstrap
- curl/binary installation
- optional AI overlay

### Project analysis progress

Current project progress already exists.
Improve it so users can understand the analysis phases.

Suggested phase language:

- `Discovering source files`
- `Profiling repository`
- `Scoring functions`
- `Synthesizing project themes`
- `Preparing multi-lens views`
- `Generating AI overlay` (only if enabled)

Even if not every phase gets a separate progress bar yet, the user should at
least see a clear status transition.

Implemented status phases:

- `Discovering source files`
- `Profiling repository`
- `Scoring functions`
- `Synthesizing project themes`
- `Preparing multi-lens views`
- `Generating AI overlay` only when AI is enabled

### Parser bootstrap progress

When downloading parsers, show:

- how many languages are being prepared
- which language is currently downloading
- success/failure per language if appropriate

### Binary install/update progress

For installer and launcher flows, show:

- detecting platform
- locating version
- downloading binary
- verifying checksum
- installing/updating
- done

### AI overlay progress

Only if AI mode is enabled:

- `Compressing deterministic report`
- `Contacting AI provider`
- `Grounding overlay output`
- `AI overlay complete`

If AI fails:

- deterministic success must still be clear
- show a short non-alarming message such as:
  - `AI overlay skipped`
  - `AI overlay unavailable`

Implemented optional AI status phases:

- `Compressing deterministic report`
- `Contacting AI provider`
- `Grounding overlay output`
- `AI overlay complete`
- `AI overlay unavailable` on fail-soft overlay failures

## 3. Winget Readiness

Windows should become a first-class install path.

### Expected user experience

Install:

```powershell
winget install Solvix.Solvix
```

Update:

```powershell
winget upgrade Solvix.Solvix
```

### Readiness checklist

Before `winget` publication, confirm:

1. stable installer or binary artifact URL strategy
2. versioned GitHub release assets exist consistently
3. checksums exist for release artifacts
4. package metadata is ready:
   - publisher
   - package identifier
   - license
   - homepage
   - release notes URL if possible
5. silent install/update behavior is understood
6. uninstall path is understood

### Practical packaging recommendation

For the first `winget` shape, prefer one of:

- portable binary install
- lightweight installer that drops the binary into PATH

Portable is simpler if the binary/update story is already strong.

### Winget work items

The next implementation chat should:

- define the exact `winget` package identifier
- decide portable vs installer manifest
- create or prepare manifest files
- document update behavior
- verify installed `solvix --version`

Implemented policy:

- package identifier: `Solvix.Solvix`
- first manifest shape: portable zip, not installer-first
- winget-specific release asset: `solvix-windows-<arch>-portable.zip`
- portable alias inside manifest: `solvix`
- operational doc: [docs/WINGET_READINESS.md](/C:/Users/Adminn/Solvix/docs/WINGET_READINESS.md)
- generated manifests: `dist/release-metadata/winget/manifests/s/Solvix/Solvix/<version>/`

## 4. Smoke-Test Matrix

These are the real user-facing smoke tests that should pass before pushing hard.

### A. Windows binary-first path

Install:

- `winget install ...` when ready
or current fallback:
- GitHub binary / npm path

Verify:

- `solvix --version`
- `solvix doctor`
- `solvix analyze sample.py`
- `solvix analyze repo --project`

Update:

- `winget upgrade ...`
or reinstall/update fallback

Verify:

- version increased correctly
- command still works

### B. macOS Homebrew path

Install:

```bash
brew tap celpha2svx/solvix
brew install solvix
```

Verify:

- `solvix --version`
- `solvix doctor`
- `solvix analyze sample.py`

Update:

```bash
brew upgrade solvix
```

Verify version alignment.

### C. Linux / curl path

Install:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

Verify:

- `solvix --version`
- `solvix doctor`
- `solvix analyze sample.py`

Update:

- rerun installer

Verify:

- binary replaced in place
- version increased

### D. Python optional path

Install:

```bash
pip install solvix
```

Update:

```bash
pip install --upgrade solvix
```

Verify:

- `solvix --version`
- `solvix doctor`

### E. npm optional path

Install:

```bash
npm install -g @celpha2svx/solvix
```

Update:

```bash
npm install -g @celpha2svx/solvix@latest
```

Verify:

- `solvix --version`
- downloaded binary matches release version

### F. AI optional path

With key:

- set `OPENAI_API_KEY`
- run `solvix analyze . --project --ai-mode assist`

Verify:

- deterministic report succeeds
- AI overlay appears
- model/mode shown correctly

Without key:

- run same command without key

Verify:

- deterministic report still succeeds
- AI overlay fails soft

The canonical smoke-test checklist now lives in:

- [docs/SMOKE_TESTS.md](/C:/Users/Adminn/Solvix/docs/SMOKE_TESTS.md)

## 5. Release Readiness Definition

The next release should be considered ready only if:

1. help output is polished
2. progress/status wording feels alive
3. Windows `winget` path is prepared or clearly staged
4. install/update smoke tests are written down and executable
5. version alignment policy from `docs/RELEASE_OPERATIONS.md` is followed

## Prompt For Implementation Chat

Use this exact prompt in another chat:

```text
Continue Solvix from:
- C:\Users\Adminn\Solvix\docs\RELEASE_OPERATIONS.md
- C:\Users\Adminn\Solvix\docs\CLI_UX_AND_RELEASE_READINESS.md

Implement the next CLI UX and release-readiness polish pass.

Goals:
1. Polish `solvix --help` and subcommand help so they are example-driven and operational.
2. Improve progress/status wording across:
   - project analysis
   - parser bootstrap
   - optional AI overlay
   - any installer/update scripts that are part of this repo
3. Prepare Windows `winget` publication readiness:
   - choose or document the exact package identifier
   - decide portable vs installer-first manifest approach
   - add any repo-side docs/templates/manifests needed
4. Add a real smoke-test checklist or scriptable test docs for:
   - Windows
   - macOS
   - Linux
   - pip optional path
   - npm optional path
   - AI optional path

Constraints:
- keep Solvix fast-by-default
- AI remains optional
- preserve backward compatibility where practical
- do not break deterministic analysis to improve UX
- update docs if implementation sharpens the policy

Implementation expectations:
- improve Click help text and examples in C:\Users\Adminn\Solvix\cli\main.py
- improve progress/status messages where the code already has progress hooks
- add or update docs/manifests/checklists for winget readiness
- add tests where practical for CLI help output and progress/status text
- run `py -3 -m unittest tests.test_all`

Also perform real local validation where practical and summarize:
- files changed
- help output improvements
- progress/status improvements
- winget readiness artifacts
- smoke-test artifacts added
- test results
```
