# Solvix

Solvix is a lightweight computational intelligence CLI that analyzes functions and explains cost, cause, context, and one concrete fix.

Distribution targets:

- `pip install solvix` for Python users
- `npm install -g @celpha2svx/solvix` for binary-first npm users
- `curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh` for Linux and macOS
- standalone binaries via GitHub Releases for Windows, macOS, and Linux
- generated Homebrew formula from the same release artifacts

Solvix uses native parser backends by default:

- Python: built-in `ast`
- Other supported languages: `tree-sitter-language-pack`

On first multi-language use, Solvix will attempt to auto-download missing native parser artifacts. If native parser infrastructure is still unavailable, Solvix will explicitly report degraded parser mode instead of silently pretending fallback parsing is equivalent.

## Install

```bash
pip install -e .
```

## Usage

```bash
solvix analyze path/to/file.py
solvix analyze path/to/file.py --function my_function
solvix analyze path/to/project --project
solvix analyze path/to/file.py --json
solvix analyze path/to/file --lang python
solvix analyze path/to/file.py --output report.txt
solvix analyze path/to/file.py --output report.json
solvix doctor
solvix bootstrap-parsers --all
solvix --version
```

## Runtime Notes

- Recommended Python range: `3.10+`
- Preferred multi-language backend: `tree-sitter-language-pack`
- Legacy `tree-sitter-languages` is treated as compatibility-only if it happens to be installed
- Heuristic parsing is fallback-only and is surfaced in warnings and JSON output
- Solvix will try to auto-download a missing parser on first use
- For offline or restricted environments, run `solvix bootstrap-parsers --all` during machine setup to pre-download native parser artifacts
- Run `solvix doctor` to see parser health, cache state, active mode, and the exact next step to take
