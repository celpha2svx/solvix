# Publishing Solvix

This guide shows how to publish Solvix to PyPI so users can later run `pip install solvix`.

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

These are generated automatically from the same release binaries, so npm, curl install, and Homebrew all track one artifact set.

Users can install with:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/latest/download/install.sh | sh
```

You can pin a version with:

```bash
curl -fsSL https://github.com/celpha2svx/solvix/releases/download/v0.2.6/install.sh | SOLVIX_VERSION=v0.2.6 sh
```

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
git tag v0.2.6
git push origin v0.2.6
```

Before using the workflows:

1. Add a PyPI trusted publisher for this repository in PyPI, or configure a `PYPI_API_TOKEN` secret if you prefer token-based upload.
2. Make sure the package version in `pyproject.toml` and `setup.py` matches the tag you are releasing.
3. Make sure the npm version matches the same release before publishing `@celpha2svx/solvix`.

## Release checklist

1. Update version numbers.
2. Run the test suite.
3. Run `solvix doctor`.
4. Build with `python -m build`.
5. Check with `python -m twine check dist/*`.
6. Publish to TestPyPI.
7. Smoke-test installation from TestPyPI.
8. Push the release tag.
9. Wait for PyPI and release binary workflows to finish.
10. Publish npm.
11. Smoke-test `npm install -g @celpha2svx/solvix`.
12. Smoke-test `curl -fsSL .../install.sh | sh`.
