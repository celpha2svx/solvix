# Winget Readiness

This document defines the Windows Package Manager publication shape for Solvix.

## Package Identity

Use this exact package identifier:

```powershell
Solvix.Solvix
```

User-facing commands:

```powershell
winget install Solvix.Solvix
winget upgrade Solvix.Solvix
winget uninstall Solvix.Solvix
```

## Manifest Approach

Solvix should publish to winget as a portable zip first.

Reason:

- Solvix is already binary-first.
- The release pipeline already creates standalone Windows binaries.
- A portable manifest avoids installer behavior before Solvix has a dedicated MSI/EXE installer.
- The winget zip can contain `solvix.exe`, giving users the stable `solvix` command instead of an arch-specific filename.

The raw GitHub release binary remains available for npm and manual downloads:

```text
solvix-windows-x64.exe
```

The winget-specific release asset is generated from that binary:

```text
solvix-windows-x64-portable.zip
```

Inside the zip:

```text
solvix.exe
```

When Windows ARM64 release binaries are produced, the same generator supports:

```text
solvix-windows-arm64-portable.zip
```

## Generated Manifests

The release workflow generates winget manifests under:

```text
dist/release-metadata/winget/manifests/s/Solvix/Solvix/<version>/
```

Expected files:

```text
Solvix.Solvix.yaml
Solvix.Solvix.locale.en-US.yaml
Solvix.Solvix.installer.yaml
```

The manifest generator uses:

- `PackageIdentifier: Solvix.Solvix`
- `InstallerType: zip`
- `NestedInstallerType: portable`
- `PortableCommandAlias: solvix`
- versioned GitHub release URLs
- SHA-256 hashes computed from the generated portable zips

## Generate Locally

After release binaries are available in `dist/release-assets`:

```powershell
py -3 scripts/generate_winget_assets.py --asset-dir dist/release-assets --output-dir dist/release-metadata
py -3 scripts/generate_winget_manifest.py --version v0.X.Y --repo celpha2svx/solvix --asset-dir dist/release-metadata --output-dir dist/release-metadata/winget
```

## Validate Before Submission

From a Windows machine with winget installed:

```powershell
winget validate dist\release-metadata\winget\manifests\s\Solvix\Solvix\0.X.Y
winget install --manifest dist\release-metadata\winget\manifests\s\Solvix\Solvix\0.X.Y
solvix --version
solvix doctor
winget uninstall Solvix.Solvix
```

## Submission Notes

Submit the generated manifest directory to `microsoft/winget-pkgs` at:

```text
manifests/s/Solvix/Solvix/<version>/
```

Current package metadata policy:

- Publisher: `Solvix Contributors`
- Package name: `Solvix`
- Package identifier: `Solvix.Solvix`
- License: `UNLICENSED`, matching the current npm package metadata
- Homepage: `https://github.com/celpha2svx/solvix`
- Release notes URL: `https://github.com/celpha2svx/solvix/releases/tag/v0.X.Y`

If Solvix adopts a public license before submission, update the npm metadata and winget manifest generator together before opening the winget PR.

## Update Behavior

Winget updates should be manager-native:

```powershell
winget upgrade Solvix.Solvix
```

Do not introduce a Solvix `self-update` command as the primary Windows update path yet. The winget manifest points to versioned release assets and checksums, so upgrades remain auditable through the package manager.
