#!/usr/bin/env python3
"""Install the complete Superpowerpoint skill collection without overwriting files."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys


SKILL_NAMES = (
    "superpowerpoint",
    "planning-powerpoint",
    "designing-powerpoint",
    "building-powerpoint",
    "editing-powerpoint",
    "reviewing-powerpoint",
)


class InstallError(ValueError):
    """The collection cannot be installed safely at the requested location."""


def preflight(source_root: Path, destination: Path) -> list[tuple[Path, Path]]:
    """Check the complete collection and every destination before any write."""
    source_root = source_root.resolve()
    destination = destination.expanduser().absolute()
    sources = [(source_root / "skills" / name, destination / name) for name in SKILL_NAMES]
    errors: list[str] = []
    for source, target in sources:
        if not source.is_dir() or not (source / "SKILL.md").is_file():
            errors.append(f"Incomplete collection: {source / 'SKILL.md'} is missing")
            continue
        if source.is_symlink() or any(path.is_symlink() for path in source.rglob("*")):
            errors.append(f"Source skill contains a symbolic link: {source}")
        if os.path.lexists(target):
            errors.append(f"Destination already exists (will not overwrite): {target}")
    if os.path.lexists(destination) and not destination.is_dir():
        errors.append(f"Destination must be a directory: {destination}")
    # Installing into the source collection or one of its descendants is never useful.
    if destination.resolve().is_relative_to(source_root / "skills"):
        errors.append("Destination must be outside the source skills directory")
    if errors:
        raise InstallError("\n".join(errors))
    return sources


def install_skills(source_root: Path, destination: Path, *, dry_run: bool = False) -> list[Path]:
    pairs = preflight(source_root, destination)
    targets = [target for _, target in pairs]
    if dry_run:
        return targets
    destination = targets[0].parent
    destination.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        # Reserve every target exclusively, catching conflicts introduced after preflight.
        for target in targets:
            target.mkdir()
            created.append(target)
        for source, target in pairs:
            shutil.copytree(source, target, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    except (OSError, shutil.Error) as exc:
        # These are only directories this invocation created, directly under the
        # explicit destination. Existing targets are never added to this list.
        for target in reversed(created):
            if target.parent == destination and not target.is_symlink():
                shutil.rmtree(target)
        raise InstallError(f"Installation failed; newly created skill directories removed: {exc}") from exc
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, required=True, help="Explicit parent directory for the six installed skills")
    parser.add_argument("--dry-run", action="store_true", help="Validate and show the planned installation without writing")
    args = parser.parse_args(argv)
    try:
        targets = install_skills(Path(__file__).resolve().parents[1], args.dest, dry_run=args.dry_run)
    except (InstallError, OSError) as exc:
        print(f"Installation refused: {exc}", file=sys.stderr)
        return 1
    action = "Would install" if args.dry_run else "Installed"
    for target in targets:
        print(f"{action}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
