# Publishing Solvix

This guide shows how to publish Solvix to PyPI so users can later run `pip install solvix`.

For release-order discipline and version alignment policy, also read:

- [docs/RELEASE_OPERATIONS.md](/C:/Users/Adminn/Solvix/docs/RELEASE_OPERATIONS.md)
- [docs/WINGET_READINESS.md](/C:/Users/Adminn/Solvix/docs/WINGET_READINESS.md)
- [docs/SMOKE_TESTS.md](/C:/Users/Adminn/Solvix/docs/SMOKE_TESTS.md)

## Canonical Release Order

Always follow this order:

1. update version in every version-bearing file
2. verify `solvix --version`
3. run tests
4. commit and push `main`
5. create and push tag `v0.X.Y`
6. wait for PyPI and release-binary workflows
7. verify release assets
8. publish npm for the exact same version
9. update Homebrew tap
10. smoke-test install and update paths

Do not tag first and edit later.
Do not publish npm before the matching GitHub release exists.
Do not announce a release until version surfaces agree.

## Prerequisites

1. Create a PyPI account at [pypi.org](https://pypi.org).
2. Create a TestPyPI account at [test.pypi.org](https://test.pypi.org).
3. Create an API token for PyPI.
4. Create an API token for TestPyPI.
5. Install publishing tools:

```bash
python -m pip install --upgrade build twine
```

## Verify the package locally

From the project root:

```bash
python -m pip install --upgrade pip
python -m pip install .
solvix doctor
```

If you want an isolated test:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
solvix analyze tests/samples/sample.py
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
solvix analyze tests/samples/sample.py
```

## Build distribution files

From the project root:

```bash
python -m build
```

This creates:

- `dist/*.tar.gz`
- `dist/*.whl`

## Check the distribution

```bash
python -m twine check dist/*
```

## Publish to TestPyPI first

```bash
python -m twine upload --repository testpypi dist/*
```

When prompted:

- username: `__token__`
- password: your TestPyPI API token

Then test installation:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple solvix
```

## Publish to PyPI

```bash
python -m twine upload dist/*
```

When prompted:

- username: `__token__`
- password: your PyPI API token

After publishing, users can install with:

```bash
pip install solvix
```

## Publish to npm

The npm package is a launcher wrapper stored in `packages/npm/`.

Before publishing:

1. Make sure the version in `packages/npm/package.json` matches the Python release version.
2. Create or sign in to your account on [npmjs.com](https://www.npmjs.com/).
3. If browser-based login is unreliable, use terminal login instead:

```bash
npm login --auth-type=legacy
```

When prompted, enter:

- npm username
- npm password
- email address

4. Change into the npm package directory:

```bash
cd packages/npm
```

5. Build and publish GitHub release binaries for the same version tag before publishing npm.

This is required because the npm launcher downloads platform binaries from GitHub Releases on first run.

6. Check whether the plain package name is available:

```bash
npm view solvix version
```

If this returns a published version, the unscoped name is already taken and you should switch to a scoped name such as `@celpha2svx/solvix` before publishing.

7. Publish:

```bash
npm publish
```

After publishing, users can install the launcher with:

```bash
npm install -g @celpha2svx/solvix
```

The npm package requires:

- matching Solvix release binaries on GitHub Releases

## Publish the curl installer and release metadata

The binary release workflow now also publishes:

- per-binary `.sha256` files
- `solvix-release.json`
- `solvix-checksums.txt`
- `install.sh`
- `solvix.rb` for Homebrew tap usage
- winget portable zips and generated manifest YAML files

These are generated automatically from the same release binaries, so npm, curl install, and Homebrew all track one artifact set.

Users can install with:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

You can pin a version with:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/download/v0.3.1/install.sh | SOLVIX_VERSION=v0.3.1 sh
```

## Prepare winget publication

Solvix uses `Solvix.Solvix` as the exact winget package identifier.

The first winget manifest should be portable-first rather than installer-first. The release workflow creates a winget-specific zip containing `solvix.exe`, so Windows users get a stable `solvix` command alias through winget.

Generated release assets:

```text
solvix-windows-x64-portable.zip
solvix-windows-x64-portable.zip.sha256
winget/manifests/s/Solvix/Solvix/<version>/*.yaml
```

To generate locally from downloaded release binaries:

```powershell
py -3 scripts/generate_winget_assets.py --asset-dir dist/release-assets --output-dir dist/release-metadata
py -3 scripts/generate_winget_manifest.py --version v0.X.Y --repo celpha2svx/solvix --asset-dir dist/release-metadata --output-dir dist/release-metadata/winget
```

Validate on Windows before opening a PR to `microsoft/winget-pkgs`:

```powershell
winget validate dist\release-metadata\winget\manifests\s\Solvix\Solvix\0.X.Y
winget install --manifest dist\release-metadata\winget\manifests\s\Solvix\Solvix\0.X.Y
solvix --version
solvix doctor
winget uninstall Solvix.Solvix
```

Use [docs/WINGET_READINESS.md](/C:/Users/Adminn/Solvix/docs/WINGET_READINESS.md) for the full publication policy.

## Publish to Homebrew

Solvix Homebrew distribution is generated from the release assets rather than built separately.

After a release tag finishes:

1. download the generated `solvix.rb` asset from the GitHub Release
2. copy it into your tap repository under `Formula/solvix.rb`
3. commit and push the tap repository

If you have the tap repo checked out locally, you can stage it with:

```bash
python scripts/publish_homebrew_formula.py --formula dist/release-metadata/solvix.rb --tap-repo ../homebrew-solvix
```

Then users can install with:

```bash
brew tap celpha2svx/solvix
brew install solvix
```

## Build standalone binaries with Nuitka

Install Nuitka in your release environment:

```bash
python -m pip install nuitka
```

Build the platform binary from the project root:

```bash
python scripts/build_binary.py
```

This produces a onefile binary in:

```bash
dist/binaries/
```

The release workflow in `.github/workflows/release-binaries.yml` builds and uploads platform binaries automatically on version tags.

## GitHub Actions publishing

The workflow in `.github/workflows/publish.yml` publishes automatically when a version tag is pushed.

Example tag:

```bash
git tag v0.3.1
git push origin v0.3.1
```

Before using the workflows:

1. Add a PyPI trusted publisher for this repository in PyPI, or configure a `PYPI_API_TOKEN` secret if you prefer token-based upload.
2. Make sure the package version in `pyproject.toml` and `setup.py` matches the tag you are releasing.
3. Make sure the npm version matches the same release before publishing `@celpha2svx/solvix`.

## Release checklist

1. Update version numbers in all version-bearing files.
2. Verify `solvix --version`.
3. Run the test suite.
4. Run `solvix doctor`.
5. Build with `python -m build`.
6. Check with `python -m twine check dist/*`.
7. Publish to TestPyPI.
8. Smoke-test installation from TestPyPI.
9. Commit and push `main`.
10. Push the release tag.
11. Wait for PyPI and release binary workflows to finish.
12. Verify release assets match the same version.
13. Publish npm.
14. Update the Homebrew tap.
15. Smoke-test `npm install -g @celpha2svx/solvix`.
16. Smoke-test `curl -fsSL .../install.sh | sh`.
17. Smoke-test winget manifests with `winget validate` and `winget install --manifest` when publishing Windows package updates.
