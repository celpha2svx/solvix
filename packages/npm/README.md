# Solvix npm Launcher

This npm package installs a thin launcher that downloads and runs the correct Solvix standalone binary for the current platform.

## What it does

- installs a global `solvix` command through npm
- downloads the matching Solvix binary from GitHub Releases
- runs the same CLI on Windows, Mac, and Linux

## Requirements

Install with:

```bash
npm install -g @celpha2svx/solvix
```

This package uses a scoped npm name because the unscoped public name `solvix` is not available on npm.

## Notes

- the launcher downloads binaries from GitHub Releases on first run
- if a matching release binary is missing, the launcher prints a clear error
- this package does not bundle the engine source itself; it installs the platform binary at runtime
