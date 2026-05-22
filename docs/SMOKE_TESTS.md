# Smoke Tests

Use this checklist before announcing a release. Every path should confirm the same Solvix version.

Set the expected version once:

```powershell
$env:SOLVIX_EXPECTED_VERSION="0.X.Y"
```

On macOS/Linux:

```bash
export SOLVIX_EXPECTED_VERSION="0.X.Y"
```

## Windows Winget Path

Install or upgrade:

```powershell
winget install Solvix.Solvix
winget upgrade Solvix.Solvix
```

Validate:

```powershell
solvix --version
solvix doctor
solvix analyze tests\samples\sample.py
solvix analyze tests\samples --project
```

Expected:

- `solvix --version` reports the release version.
- `solvix doctor` reports native, native-auto-bootstrap, or explicit degraded parser status.
- file and project analysis complete without requiring an AI key.

For pre-submission manifest testing:

```powershell
winget validate dist\release-metadata\winget\manifests\s\Solvix\Solvix\$env:SOLVIX_EXPECTED_VERSION
winget install --manifest dist\release-metadata\winget\manifests\s\Solvix\Solvix\$env:SOLVIX_EXPECTED_VERSION
```

## macOS Homebrew Path

Install or upgrade:

```bash
brew tap celpha2svx/solvix
brew install solvix
brew upgrade solvix
```

Validate:

```bash
solvix --version
solvix doctor
solvix analyze tests/samples/sample.py
solvix analyze tests/samples --project
```

Expected:

- `solvix` is available globally.
- the reported version matches the release tag.
- project analysis remains deterministic with AI off by default.

## Linux Curl Path

Install or update:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

Validate:

```bash
solvix --version
solvix doctor
solvix analyze tests/samples/sample.py
solvix analyze tests/samples --project
```

Expected:

- rerunning the installer replaces or refreshes the binary in place.
- checksum verification happens before install.
- the installed binary reports the release version.

## Python Optional Path

Install or upgrade:

```bash
python -m pip install --upgrade solvix
```

Validate:

```bash
solvix --version
solvix doctor
solvix analyze tests/samples/sample.py
```

Expected:

- the PyPI package version, CLI version, and JSON `solvix_version` agree.
- no uninstall is required before upgrade.

## npm Optional Path

Install or upgrade:

```bash
npm install -g @celpha2svx/solvix@latest
```

Validate:

```bash
solvix --version
solvix doctor
solvix analyze tests/samples/sample.py
```

Expected:

- first run downloads the matching GitHub release binary.
- checksum verification happens before launch.
- status messages go to stderr so JSON output stays safe.

## AI Optional Path

Without a key:

```bash
unset OPENAI_API_KEY
solvix analyze tests/samples --project --ai-mode assist
```

Windows PowerShell:

```powershell
Remove-Item Env:\OPENAI_API_KEY -ErrorAction SilentlyContinue
solvix analyze tests\samples --project --ai-mode assist
```

Expected:

- deterministic Stage 1-4 project analysis succeeds.
- the AI overlay reports unavailable or skipped without failing the command.

With a key:

```bash
export OPENAI_API_KEY="sk-..."
solvix analyze tests/samples --project --ai-mode assist
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
solvix analyze tests\samples --project --ai-mode assist
```

Expected:

- deterministic report still appears as the source of truth.
- AI overlay output is clearly separated.
- model and mode are shown in saved JSON or summary output when applicable.

## Fast Local Regression

Run this before any release commit:

```powershell
py -3 -m unittest tests.test_all
py -3 -m cli.main --version
py -3 -m cli.main --help
py -3 -m cli.main analyze --help
```
