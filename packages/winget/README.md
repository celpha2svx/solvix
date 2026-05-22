# Solvix Winget Packaging

Solvix publishes to winget as `Solvix.Solvix`.

The release workflow generates winget-ready portable assets and manifests:

```text
solvix-windows-x64-portable.zip
solvix-windows-x64-portable.zip.sha256
winget/manifests/s/Solvix/Solvix/<version>/*.yaml
```

The portable zip contains:

```text
solvix.exe
```

This keeps the installed command stable as `solvix` while preserving the existing raw Windows binary assets for npm and manual download paths.

Generate locally:

```powershell
py -3 scripts/generate_winget_assets.py --asset-dir dist/release-assets --output-dir dist/release-metadata
py -3 scripts/generate_winget_manifest.py --version v0.X.Y --repo celpha2svx/solvix --asset-dir dist/release-metadata --output-dir dist/release-metadata/winget
```

Full policy and validation steps live in [docs/WINGET_READINESS.md](/C:/Users/Adminn/Solvix/docs/WINGET_READINESS.md).
