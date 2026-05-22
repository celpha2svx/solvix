"""Package Windows release binaries into winget-friendly portable zips."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_winget_portable_zips(asset_dir: Path, output_dir: Path) -> list[Path]:
    asset_dir = asset_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    for binary in sorted(asset_dir.glob("solvix-windows-*.exe")):
        arch = binary.name.removeprefix("solvix-windows-").removesuffix(".exe")
        zip_path = output_dir / f"solvix-windows-{arch}-portable.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(binary, arcname="solvix.exe")
        checksum_path = zip_path.with_name(zip_path.name + ".sha256")
        checksum_path.write_text(
            f"{sha256_file(zip_path)}  {zip_path.name}\n",
            encoding="utf-8",
        )
        created.extend([zip_path, checksum_path])

    if not created:
        raise RuntimeError(f"No Windows release binaries found in {asset_dir}")

    return created


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    created = build_winget_portable_zips(
        asset_dir=Path(args.asset_dir),
        output_dir=Path(args.output_dir),
    )
    for path in created:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
