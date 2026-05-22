# Solvix Release Operations

This document is the operational policy for packaging, publishing, updating,
and version alignment across every Solvix distribution channel.

It exists to prevent release drift such as:

- Git tag says `0.2.9`
- binary says `0.2.7`
- npm says `0.2.8`
- CLI `--version` says something else

That must not happen.

## Product Positioning

Solvix is now a **binary-first** product.

Recommended install channels:

- Windows: `winget`
- macOS: `brew`
- Linux / servers: `curl ... | sh`

Optional ecosystem channels:

- `pip install solvix`
- `npm install -g @celpha2svx/solvix`

The intended user experience is:

1. install once
2. get a global `solvix` command
3. run it anywhere
4. update using the same package manager used for install

## Official Install Matrix

### Windows

Recommended:

```powershell
winget install Solvix.Solvix
```

Update:

```powershell
winget upgrade Solvix.Solvix
```

Winget package identity is fixed as `Solvix.Solvix`.

Initial winget publication should use the portable zip manifest path documented in:

- [docs/WINGET_READINESS.md](/C:/Users/Adminn/Solvix/docs/WINGET_READINESS.md)

### macOS

Recommended:

```bash
brew tap celpha2svx/solvix
brew install solvix
```

Update:

```bash
brew upgrade solvix
```

### Linux / Cloud / Generic Unix

Recommended:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

Update:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

The installer should replace or refresh the existing binary in place.

### Python Optional Channel

Install:

```bash
pip install solvix
```

Update:

```bash
pip install --upgrade solvix
```

### npm Optional Channel

Install:

```bash
npm install -g @celpha2svx/solvix
```

Update:

```bash
npm install -g @celpha2svx/solvix@latest
```

## Official Update Policy

Users should **not** need to uninstall first.

Use manager-native upgrades:

- `winget upgrade Solvix.Solvix`
- `brew upgrade solvix`
- rerun `install.sh`
- `pip install --upgrade solvix`
- `npm install -g @celpha2svx/solvix@latest`

Do not make `self-update` the primary path yet.
Native package manager update commands are simpler and more trustworthy.

## Version Alignment Policy

Before creating any release tag, all version-bearing surfaces must be updated
to the exact same version.

At minimum, check and align:

- `pyproject.toml`
- `setup.py`
- `cli/main.py`
- `output/json_formatter.py` only if it still carries a static version fallback
- `packages/npm/package.json`
- any shared version helper such as `core/version.py`
- `PUBLISHING.md` if it contains pinned version examples
- install-script pinned version examples if present

Also verify runtime version surfaces:

- `solvix --version`
- JSON `solvix_version`
- npm package version
- Git tag version

## Required Release Order

This is the required first-order policy for every public release.

### 1. Update version in all version-bearing files

Do this before anything else.

### 2. Run validation locally

At minimum:

```powershell
py -3 -m unittest tests.test_all
py -3 -m cli.main --version
```

And if npm channel changed:

```powershell
cd packages/npm
npm pkg get version
```

### 3. Commit the aligned version bump

Example:

```powershell
git add .
git commit -m "Bump unified release to 0.X.Y"
git push origin main
```

### 4. Create and push the Git tag

Example:

```powershell
git tag v0.X.Y
git push origin v0.X.Y
```

### 5. Wait for release automation

Required workflows:

- PyPI publish
- release binaries

Do not publish npm, update Homebrew, or announce the release until these pass.

### 6. Verify GitHub release assets

At minimum verify:

- Windows binary
- Windows winget portable zip
- Linux binary
- macOS binaries
- checksums
- `solvix-release.json`
- `install.sh`
- `solvix.rb`
- generated winget manifests when publishing Windows package updates

### 7. Publish npm for the same version

Only after the GitHub release exists for the exact same version.

### 8. Update Homebrew tap

Use the generated formula from the exact same release.

### 9. Validate install paths

At minimum test:

- binary/global command
- `solvix --version`
- `solvix doctor`

Use the complete smoke-test matrix in:

- [docs/SMOKE_TESTS.md](/C:/Users/Adminn/Solvix/docs/SMOKE_TESTS.md)

## What Must Never Happen

These are release failures:

- tag version and CLI version differ
- npm package points at a GitHub release version that does not exist
- GitHub release binaries exist but report an older CLI version
- PyPI package version differs from CLI version
- docs recommend an install command that cannot update cleanly

If any of these happen, fix alignment before moving on.

## AI Overlay Policy

AI is optional.

The deterministic engine must always work without any API key.

Recommended auth shape:

- `OPENAI_API_KEY`

Examples:

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

If the key is missing and AI mode is requested:

- deterministic analysis must still succeed
- AI overlay should fail soft

## Packaging Priority

Recommended priority order for public packaging:

1. `winget`
2. `brew`
3. `curl`
4. `pip` optional
5. `npm` optional

Reason:

- users should get a machine-global `solvix` command with minimal setup
- Python and npm remain valuable channels, but they are no longer the center

## Release Checklist

1. Update all version-bearing files.
2. Verify `solvix --version`.
3. Run the full test suite.
4. Commit the version bump.
5. Push `main`.
6. Create and push tag `v0.X.Y`.
7. Wait for PyPI and binary workflows to pass.
8. Verify release assets.
9. Publish npm for the same version.
10. Update Homebrew tap from the generated formula.
11. Smoke-test install and update paths.
12. Only then announce the release.

Use [docs/SMOKE_TESTS.md](/C:/Users/Adminn/Solvix/docs/SMOKE_TESTS.md) as the canonical smoke-test checklist.
