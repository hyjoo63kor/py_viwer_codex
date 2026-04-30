from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = (
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
)
RECURSIVE_SKIP_DIRS = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "build",
        "dist",
    }
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean generated project artifacts.")
    parser.add_argument(
        "--dist",
        action="store_true",
        help="also remove dist/ and the generated executable",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be removed without deleting anything",
    )
    args = parser.parse_args()

    targets = [PROJECT_ROOT / name for name in DEFAULT_TARGETS]
    if args.dist:
        targets.append(PROJECT_ROOT / "dist")
    targets.extend(
        path
        for path in PROJECT_ROOT.rglob("__pycache__")
        if path.is_dir() and not _is_in_skipped_dir(path)
    )
    targets.extend(
        path
        for path in PROJECT_ROOT.rglob("*.pyc")
        if not _is_in_skipped_dir(path) and "__pycache__" not in path.parts
    )
    targets.extend(
        path
        for path in PROJECT_ROOT.rglob("*.pyo")
        if not _is_in_skipped_dir(path) and "__pycache__" not in path.parts
    )

    removed_count = 0
    for target in sorted(set(targets)):
        if not target.exists():
            continue
        _ensure_inside_project(target)
        action = "Would remove" if args.dry_run else "Removing"
        print(f"{action} {target.relative_to(PROJECT_ROOT)}")
        if not args.dry_run:
            _remove(target)
        removed_count += 1

    if removed_count == 0:
        print("Nothing to clean.")
    return 0


def _ensure_inside_project(path: Path) -> None:
    path.resolve().relative_to(PROJECT_ROOT)


def _is_in_skipped_dir(path: Path) -> bool:
    return any(part in RECURSIVE_SKIP_DIRS for part in path.relative_to(PROJECT_ROOT).parts)


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
