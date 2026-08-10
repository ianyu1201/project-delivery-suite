#!/usr/bin/env python3
"""Build the bundled Skill snapshots from authoritative local checkouts."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


SKILL_NAMES = ("ai-project-delivery-orchestrator", "consolidate-project-versions")
IGNORED_NAMES = {".git", ".github", "__pycache__", ".DS_Store"}


def git_commit(source: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()


def copy_skill(source: Path, destination: Path) -> None:
    if not (source / "SKILL.md").is_file():
        raise ValueError(f"not a Skill checkout: {source}")
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staged = Path(temporary) / destination.name
        shutil.copytree(
            source,
            staged,
            ignore=shutil.ignore_patterns(*IGNORED_NAMES),
            symlinks=False,
        )
        if destination.exists():
            shutil.rmtree(destination)
        staged.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orchestrator", type=Path, required=True)
    parser.add_argument("--consolidator", type=Path, required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    skills_root = root / "plugins" / "ai-project-delivery-suite" / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    sources = {
        SKILL_NAMES[0]: args.orchestrator.resolve(),
        SKILL_NAMES[1]: args.consolidator.resolve(),
    }
    upstreams = {"skills": {}}
    for name, source in sources.items():
        copy_skill(source, skills_root / name)
        upstreams["skills"][name] = {
            "repository": subprocess.check_output(
                ["git", "remote", "get-url", "origin"], cwd=source, text=True
            ).strip(),
            "commit": git_commit(source),
        }
    (root / "UPSTREAMS.json").write_text(
        json.dumps(upstreams, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
