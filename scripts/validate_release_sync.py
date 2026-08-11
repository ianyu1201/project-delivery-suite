#!/usr/bin/env python3
"""Validate one release version without erasing platform-specific behavior.

The Codex plugin directories are the canonical Skill snapshots. A separate
local-install comparison verifies ~/.codex/skills when publishing from a
maintainer workstation. WorkBuddy intentionally keeps a flattened package and
manual task-Prompt fallback, so only declared shared core files are hash-equal.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "project-delivery-suite"
WORKBUDDY = ROOT / "distributions" / "workbuddy" / "package" / "project-delivery-suite"
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def workbuddy_version() -> str:
    text = (WORKBUDDY / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"(?m)^version:\s*([^\s]+)\s*$", text)
    if not match:
        raise AssertionError("WorkBuddy SKILL.md lacks version")
    return match.group(1)


def main() -> int:
    canonical = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert SEMVER_RE.fullmatch(canonical), f"invalid canonical version: {canonical}"
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    observed = {
        "canonical": canonical,
        "codex_plugin": manifest["version"],
        "orchestrator_snapshot": (PLUGIN / "skills" / "project-delivery-orchestrator" / "VERSION").read_text(encoding="utf-8").strip(),
        "consolidator_snapshot": (PLUGIN / "skills" / "consolidate-project-versions" / "VERSION").read_text(encoding="utf-8").strip(),
        "workbuddy": workbuddy_version(),
    }
    mismatches = {name: value for name, value in observed.items() if value != canonical}
    assert not mismatches, f"release version drift: {mismatches}"

    shared = [
        (
            PLUGIN / "skills" / "project-delivery-orchestrator" / "assets" / "MINIMUM_PRD.md",
            WORKBUDDY / "assets" / "MINIMUM_PRD.md",
        ),
        (
            PLUGIN / "skills" / "project-delivery-orchestrator" / "scripts" / "project_snapshot.py",
            WORKBUDDY / "scripts" / "project_snapshot.py",
        ),
        (
            PLUGIN / "skills" / "project-delivery-orchestrator" / "scripts" / "scaffold_delivery.py",
            WORKBUDDY / "scripts" / "scaffold_delivery.py",
        ),
        (
            PLUGIN / "skills" / "consolidate-project-versions" / "scripts" / "audit_versions.py",
            WORKBUDDY / "scripts" / "audit_versions.py",
        ),
    ]
    for codex_path, workbuddy_path in shared:
        assert sha256(codex_path) == sha256(workbuddy_path), (
            f"shared source drift: {codex_path.relative_to(ROOT)} != {workbuddy_path.relative_to(ROOT)}"
        )

    forbidden = "ai-project-delivery-orchestrator"
    for path in WORKBUDDY.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".txt", ".py"}:
            assert forbidden not in path.read_text(encoding="utf-8"), f"legacy Skill ID remains: {path}"
    print(json.dumps(observed, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
