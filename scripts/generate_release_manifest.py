"""Generate release metadata from uploaded binaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_asset(name: str) -> tuple[str, str, str] | None:
    stem = name.removesuffix(".exe")
    parts = stem.split("-")
    if len(parts) != 3 or parts[0] != "solvix":
        return None
    if parts[1] not in {"windows", "linux", "macos"} or parts[2] not in {"x64", "arm64"}:
        return None
    return parts[1], parts[2], name


def build_manifest(version: str, repo: str, asset_dir: Path) -> dict:
    assets: dict[str, dict[str, str]] = {}
    for asset in sorted(asset_dir.iterdir()):
        if not asset.is_file() or asset.name.endswith(".sha256"):
            continue
        classified = classify_asset(asset.name)
        if classified is None:
            continue
        platform_name, arch, filename = classified
        key = f"{platform_name}-{arch}"
        assets[key] = {
            "platform": platform_name,
            "arch": arch,
            "filename": filename,
            "sha256": sha256_file(asset),
            "url": f"https://github.com/{repo}/releases/download/v{version}/{filename}",
            "sha256_url": f"https://github.com/{repo}/releases/download/v{version}/{filename}.sha256",
        }

    if not assets:
        raise RuntimeError(f"No release assets found in {asset_dir}")

    return {
        "version": version,
        "repo": repo,
        "assets": assets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--asset-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    version = args.version.removeprefix("v")
    asset_dir = Path(args.asset_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(version=version, repo=args.repo, asset_dir=asset_dir)

    checksums_path = output_dir / "solvix-checksums.txt"
    checksums = []
    for asset in sorted(manifest["assets"].values(), key=lambda entry: entry["filename"]):
        checksums.append(f'{asset["sha256"]}  {asset["filename"]}')
    checksums_path.write_text("\n".join(checksums) + "\n", encoding="utf-8")

    manifest_path = output_dir / "solvix-release.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(manifest_path)
    print(checksums_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
