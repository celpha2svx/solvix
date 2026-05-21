"""Write sha256 sidecar files for release assets."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("Usage: write_checksums.py <asset_dir>")

    asset_dir = Path(argv[1]).resolve()
    if not asset_dir.exists():
        raise SystemExit(f"Asset directory does not exist: {asset_dir}")

    for asset in sorted(asset_dir.iterdir()):
        if not asset.is_file() or asset.name.endswith(".sha256"):
            continue
        checksum_path = asset.with_name(asset.name + ".sha256")
        checksum_path.write_text(
            f"{sha256_file(asset)}  {asset.name}\n",
            encoding="utf-8",
        )
        print(checksum_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
