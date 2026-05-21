"""Build standalone Solvix binaries with Nuitka."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "binaries"


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    output_name = binary_name()
    output_path = DIST / output_name

    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--assume-yes-for-downloads",
        "--follow-imports",
        "--include-package=adapters",
        "--include-package=cli",
        "--include-package=context",
        "--include-package=core",
        "--include-package=output",
        "--include-package=patterns",
        "--output-dir=" + str(DIST),
        "--output-filename=" + output_name,
        str(ROOT / "cli" / "main.py"),
    ]

    subprocess.run(command, cwd=ROOT, check=True)
    if not output_path.exists():
        raise FileNotFoundError(f"Expected binary at {output_path}")

    print(output_path)
    return 0


def binary_name() -> str:
    system = platform.system().lower()
    machine = normalize_arch(platform.machine().lower())

    if system == "windows":
        return f"solvix-windows-{machine}.exe"
    if system == "darwin":
        return f"solvix-macos-{machine}"
    if system == "linux":
        return f"solvix-linux-{machine}"
    raise RuntimeError(f"Unsupported build platform: {system}/{machine}")


def normalize_arch(machine: str) -> str:
    mapping = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    if machine not in mapping:
        raise RuntimeError(f"Unsupported architecture: {machine}")
    return mapping[machine]


if __name__ == "__main__":
    raise SystemExit(main())
