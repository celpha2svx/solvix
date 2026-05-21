"""Generate a Homebrew formula from release assets."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--asset-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    version = args.version.removeprefix("v")
    asset_dir = Path(args.asset_dir).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    intel_name = "solvix-macos-x64"
    arm_name = "solvix-macos-arm64"
    intel_path = asset_dir / intel_name
    arm_path = asset_dir / arm_name
    if not intel_path.exists() or not arm_path.exists():
        missing = [name for name, path in ((intel_name, intel_path), (arm_name, arm_path)) if not path.exists()]
        raise RuntimeError(f"Missing macOS release assets: {', '.join(missing)}")

    base_url = f"https://github.com/{args.repo}/releases/download/v{version}"
    formula = f"""class Solvix < Formula
  desc "Computational intelligence layer for developers"
  homepage "https://github.com/{args.repo}"
  version "{version}"

  on_macos do
    if Hardware::CPU.intel?
      url "{base_url}/{intel_name}"
      sha256 "{sha256_file(intel_path)}"
    end

    if Hardware::CPU.arm?
      url "{base_url}/{arm_name}"
      sha256 "{sha256_file(arm_path)}"
    end
  end

  def install
    if Hardware::CPU.intel?
      bin.install "{intel_name}" => "solvix"
    else
      bin.install "{arm_name}" => "solvix"
    end
  end

  test do
    assert_match version.to_s, shell_output("#{{bin}}/solvix --version")
  end
end
"""
    output_path.write_text(formula, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
