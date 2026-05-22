"""Generate Windows Package Manager manifests for Solvix release assets."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

WINGET_PACKAGE_IDENTIFIER = "Solvix.Solvix"
WINGET_MANIFEST_VERSION = "1.12.0"
WINGET_DEFAULT_LOCALE = "en-US"


@dataclass(frozen=True)
class WingetAsset:
    arch: str
    filename: str
    sha256: str
    url: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def discover_winget_assets(version: str, repo: str, asset_dir: Path) -> list[WingetAsset]:
    version = version.removeprefix("v")
    assets: list[WingetAsset] = []
    for archive in sorted(asset_dir.resolve().glob("solvix-windows-*-portable.zip")):
        arch = archive.name.removeprefix("solvix-windows-").removesuffix("-portable.zip")
        if arch not in {"x64", "arm64"}:
            continue
        assets.append(
            WingetAsset(
                arch=arch,
                filename=archive.name,
                sha256=sha256_file(archive),
                url=f"https://github.com/{repo}/releases/download/v{version}/{archive.name}",
            )
        )
    if not assets:
        raise RuntimeError(f"No winget portable zip assets found in {asset_dir}")
    return assets


def build_winget_manifests(
    *,
    version: str,
    repo: str,
    asset_dir: Path,
    output_dir: Path,
    package_identifier: str = WINGET_PACKAGE_IDENTIFIER,
    publisher: str = "Solvix Contributors",
    license_name: str = "UNLICENSED",
) -> list[Path]:
    version = version.removeprefix("v")
    assets = discover_winget_assets(version, repo, asset_dir)
    publisher_key, package_key = package_identifier.split(".", 1)
    manifest_dir = (
        output_dir.resolve()
        / "manifests"
        / publisher_key[0].lower()
        / publisher_key
        / package_key
        / version
    )
    manifest_dir.mkdir(parents=True, exist_ok=True)

    version_path = manifest_dir / f"{package_identifier}.yaml"
    locale_path = manifest_dir / f"{package_identifier}.locale.en-US.yaml"
    installer_path = manifest_dir / f"{package_identifier}.installer.yaml"

    version_path.write_text(
        _version_manifest(package_identifier, version),
        encoding="utf-8",
    )
    locale_path.write_text(
        _locale_manifest(package_identifier, version, publisher, license_name, repo),
        encoding="utf-8",
    )
    installer_path.write_text(
        _installer_manifest(package_identifier, version, assets),
        encoding="utf-8",
    )

    return [version_path, locale_path, installer_path]


def _version_manifest(package_identifier: str, version: str) -> str:
    return "\n".join(
        [
            f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.version.{WINGET_MANIFEST_VERSION}.schema.json",
            f"PackageIdentifier: {_q(package_identifier)}",
            f"PackageVersion: {_q(version)}",
            f"DefaultLocale: {_q(WINGET_DEFAULT_LOCALE)}",
            'ManifestType: "version"',
            f"ManifestVersion: {_q(WINGET_MANIFEST_VERSION)}",
            "",
        ]
    )


def _locale_manifest(
    package_identifier: str,
    version: str,
    publisher: str,
    license_name: str,
    repo: str,
) -> str:
    return "\n".join(
        [
            f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.defaultLocale.{WINGET_MANIFEST_VERSION}.schema.json",
            f"PackageIdentifier: {_q(package_identifier)}",
            f"PackageVersion: {_q(version)}",
            f"PackageLocale: {_q(WINGET_DEFAULT_LOCALE)}",
            f"Publisher: {_q(publisher)}",
            f"PublisherUrl: {_q(f'https://github.com/{repo}')}",
            'PackageName: "Solvix"',
            f"PackageUrl: {_q(f'https://github.com/{repo}')}",
            f"License: {_q(license_name)}",
            'ShortDescription: "Computational intelligence CLI for developers."',
            (
                'Description: "Solvix analyzes source code functions and project structure '
                'to explain cost, cause, context, and the next useful fix."'
            ),
            'Moniker: "solvix"',
            "Tags:",
            '- "cli"',
            '- "code-analysis"',
            '- "developer-tools"',
            '- "performance"',
            '- "static-analysis"',
            f"ReleaseNotesUrl: {_q(f'https://github.com/{repo}/releases/tag/v{version}')}",
            'ManifestType: "defaultLocale"',
            f"ManifestVersion: {_q(WINGET_MANIFEST_VERSION)}",
            "",
        ]
    )


def _installer_manifest(package_identifier: str, version: str, assets: list[WingetAsset]) -> str:
    lines = [
        f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.installer.{WINGET_MANIFEST_VERSION}.schema.json",
        f"PackageIdentifier: {_q(package_identifier)}",
        f"PackageVersion: {_q(version)}",
        'InstallerType: "zip"',
        'NestedInstallerType: "portable"',
        "NestedInstallerFiles:",
        '- RelativeFilePath: "solvix.exe"',
        '  PortableCommandAlias: "solvix"',
        "Commands:",
        '- "solvix"',
        "ArchiveBinariesDependOnPath: true",
        "Installers:",
    ]
    for asset in assets:
        lines.extend(
            [
                f"- Architecture: {_q(asset.arch)}",
                f"  InstallerUrl: {_q(asset.url)}",
                f"  InstallerSha256: {_q(asset.sha256)}",
            ]
        )
    lines.extend(
        [
            'ManifestType: "installer"',
            f"ManifestVersion: {_q(WINGET_MANIFEST_VERSION)}",
            "",
        ]
    )
    return "\n".join(lines)


def _q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--asset-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--package-identifier", default=WINGET_PACKAGE_IDENTIFIER)
    parser.add_argument("--publisher", default="Solvix Contributors")
    parser.add_argument("--license", default="UNLICENSED")
    args = parser.parse_args()

    manifest_paths = build_winget_manifests(
        version=args.version,
        repo=args.repo,
        asset_dir=Path(args.asset_dir),
        output_dir=Path(args.output_dir),
        package_identifier=args.package_identifier,
        publisher=args.publisher,
        license_name=args.license,
    )
    for path in manifest_paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
