#!/usr/bin/env python3
"""Compare the installed Codex Skill with the canonical GitHub plugin copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


SKILL_IDS = ("project-delivery-suite",)
IGNORED_DIRS = {".git", ".github", "__pycache__"}


def fingerprint_tree(root: Path) -> dict[str, tuple[str, str, bool]]:
    if not root.is_dir():
        raise ValueError(f"missing Skill directory: {root}")
    result: dict[str, tuple[str, str, bool]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        key = relative.as_posix()
        if path.is_symlink():
            result[key] = ("symlink", os.readlink(path), False)
        elif path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            result[key] = ("file", digest, bool(path.stat().st_mode & 0o111))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project Delivery Suite repository root",
    )
    parser.add_argument(
        "--local-skills-root",
        type=Path,
        default=Path.home() / ".codex" / "skills",
        help="Local Codex skills directory",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canonical_root = args.repo_root / "plugins" / "project-delivery-suite" / "skills"
    report: dict[str, str] = {}
    errors: list[str] = []
    for skill_id in SKILL_IDS:
        canonical = canonical_root / skill_id
        installed = args.local_skills_root / skill_id
        try:
            canonical_files = fingerprint_tree(canonical)
            installed_files = fingerprint_tree(installed)
        except ValueError as error:
            errors.append(str(error))
            report[skill_id] = "missing"
            continue
        if canonical_files == installed_files:
            report[skill_id] = "exact"
            continue
        report[skill_id] = "drift"
        for relative in sorted(canonical_files.keys() | installed_files.keys()):
            if canonical_files.get(relative) != installed_files.get(relative):
                errors.append(f"{skill_id}/{relative}")

    print(json.dumps({"skills": report, "differences": errors}, ensure_ascii=False, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
