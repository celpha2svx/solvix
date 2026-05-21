"""Stage a generated Solvix formula into a checked-out Homebrew tap repo."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formula", required=True, help="Path to generated solvix.rb")
    parser.add_argument("--tap-repo", required=True, help="Path to local homebrew tap checkout")
    args = parser.parse_args()

    formula_path = Path(args.formula).resolve()
    tap_repo = Path(args.tap_repo).resolve()

    if not formula_path.exists():
        raise SystemExit(f"Formula file does not exist: {formula_path}")
    if not tap_repo.exists():
        raise SystemExit(f"Tap repository path does not exist: {tap_repo}")

    target_dir = tap_repo / "Formula"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "solvix.rb"
    shutil.copy2(formula_path, target_path)

    readme_path = tap_repo / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            "# homebrew-solvix\n\n"
            "Homebrew tap for Solvix.\n\n"
            "## Install\n\n"
            "```bash\n"
            "brew tap celpha2svx/solvix\n"
            "brew install solvix\n"
            "```\n",
            encoding="utf-8",
        )

    print(target_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
