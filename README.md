# Solvix

Solvix is a fast, binary-first code intelligence CLI for real repositories.

It analyzes source code, identifies costly or risky function patterns, understands the kind of system it is looking at, ranks what matters in that repository, groups repeated signals into themes, and presents focused views such as performance, startup, maintainability, reliability, cloud cost, and battery efficiency.

Solvix is designed to feel practical:

- fast by default
- deterministic first
- optional AI overlay
- global `solvix` command on every platform

## Why Solvix

Most code analysis tools either:

- stop at raw findings
- flood you with too much detail
- or rely too early on AI

Solvix takes a different path:

1. deterministic project profiling
2. deterministic relevance weighting
3. deterministic signal synthesis
4. deterministic multi-lens reporting
5. optional AI explanation on top

That means the core report stays:

- explainable
- stable
- fast
- usable without network access or API keys

## Install

Recommended install channels:

### Windows

```powershell
winget install Solvix.Solvix
```

### macOS

```bash
brew tap celpha2svx/solvix
brew install solvix
```

### Linux / Cloud / Generic Unix

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

Optional ecosystem channels:

### Python

```bash
pip install solvix
```

### npm

```bash
npm install -g @celpha2svx/solvix
```

### Local development

```bash
pip install -e .
```

## Update

Use the same channel you installed with.

### Windows

```powershell
winget upgrade Solvix.Solvix
```

### macOS

```bash
brew upgrade solvix
```

### Linux / Cloud / Generic Unix

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

### Python

```bash
pip install --upgrade solvix
```

### npm

```bash
npm install -g @celpha2svx/solvix@latest
```

## Quick Start

```bash
solvix doctor
solvix analyze app.py
solvix analyze src --project
solvix analyze src --project --json --output report.json
```

## Common Commands

```bash
solvix --help
solvix analyze path/to/file.py
solvix analyze path/to/file.py --function my_function
solvix analyze path/to/project --project
solvix analyze path/to/project --project --json --output report.json
solvix analyze path/to/project --project --ai-mode assist
solvix doctor
solvix bootstrap-parsers --all
solvix --version
```

## Optional AI Overlay

The deterministic engine does not require any API key.

If you want the optional AI overlay, set `OPENAI_API_KEY` first.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
solvix analyze . --project --ai-mode assist
```

macOS / Linux:

```bash
export OPENAI_API_KEY="sk-..."
solvix analyze . --project --ai-mode assist
```

If the key is missing, deterministic analysis should still succeed and the AI overlay should fail soft.

## Documentation

Repo docs:

- [Architecture](docs/ARCHITECTURE.md)
- [Release operations](docs/RELEASE_OPERATIONS.md)
- [CLI UX and release readiness](docs/CLI_UX_AND_RELEASE_READINESS.md)
- [Smoke tests](docs/SMOKE_TESTS.md)
- [Winget readiness](docs/WINGET_READINESS.md)

Planned GitHub Pages site:

- `docs/index.html`

Once Pages is enabled for this repo, the docs site can be served from the same repository.

## Runtime Notes

- Recommended Python: `3.10+`
- Preferred multi-language backend: `tree-sitter-language-pack`
- Solvix auto-downloads missing native parser artifacts when needed
- For offline or restricted environments, run `solvix bootstrap-parsers --all`
- `solvix doctor` shows parser health, cache state, active mode, and next steps
- AI overlay is optional and post-processing only; it does not change deterministic analysis correctness

## Release Discipline

Before any release tag:

1. update version in all version-bearing files
2. verify `solvix --version`
3. run tests
4. commit and push `main`
5. create and push the tag
6. wait for release workflows
7. publish npm / Homebrew / other channels only after the matching release exists

Full policy:

- [Release operations](docs/RELEASE_OPERATIONS.md)
