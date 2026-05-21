# Solvix npm Launcher

This npm package is a thin launcher for the Python version of Solvix.

## What it does

- installs a global `solvix` command through npm
- detects Python on Windows, Mac, and Linux
- forwards all CLI arguments to the Python Solvix CLI

## Requirements

You must have:

1. Python `3.10` or higher installed
2. the Python Solvix package installed

Install the Python package with:

```bash
pip install solvix
```

Then the npm launcher can be installed with:

```bash
npm install -g solvix
```

If the public npm name `solvix` is already taken at publish time, the fallback package name should be a scoped name such as:

```bash
npm install -g @celpha2svx/solvix
```

## Notes

- if Python is missing, the launcher prints a clear setup message
- if the Python Solvix package is missing, the launcher tells you to run `pip install solvix`
- this package does not contain the analysis engine itself; it only launches the Python CLI
