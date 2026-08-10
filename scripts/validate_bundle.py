#!/usr/bin/env python3
"""Validate the distributable plugin and both bundled Skill snapshots."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "ai-project-delivery-suite"
SKILL_NAMES = ("ai-project-delivery-orchestrator", "consolidate-project-versions")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
    marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    upstreams = load_json(ROOT / "UPSTREAMS.json")
    assert manifest["name"] == "ai-project-delivery-suite"
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", manifest["version"])
    assert manifest["license"] == "MIT"
    assert marketplace["plugins"][0]["name"] == manifest["name"]
    assert marketplace["plugins"][0]["source"]["path"] == "./plugins/ai-project-delivery-suite"
    for name in SKILL_NAMES:
        skill_root = PLUGIN / "skills" / name
        text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert f"name: {name}" in text.split("---", 2)[1]
        commit = upstreams["skills"][name]["commit"]
        assert re.fullmatch(r"[0-9a-f]{7,40}", commit)
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
