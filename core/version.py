"""Shared Solvix version lookup."""

from __future__ import annotations

from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import tomllib


@lru_cache(maxsize=1)
def get_solvix_version() -> str:
    try:
        return package_version("solvix")
    except PackageNotFoundError:
        pass

    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return str(data["project"]["version"])
