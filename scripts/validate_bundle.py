#!/usr/bin/env python3
"""Validate the distributable plugin and its single bundled Skill."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "project-delivery-suite"
SKILL_NAME = "project-delivery-suite"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
    marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert manifest["name"] == "project-delivery-suite"
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", manifest["version"])
    assert manifest["license"] == "MIT"
    assert marketplace["plugins"][0]["name"] == manifest["name"]
    assert marketplace["plugins"][0]["source"]["path"] == "./plugins/project-delivery-suite"
    skill_root = PLUGIN / "skills" / SKILL_NAME
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert f"name: {SKILL_NAME}" in text.split("---", 2)[1]
    assert (skill_root / "LICENSE").is_file()
    assert len([path for path in (PLUGIN / "skills").iterdir() if path.is_dir()]) == 1
    fallback = skill_root / "assets" / "MINIMUM_PRD.md"
    assert fallback.is_file()
    assert "assets/MINIMUM_PRD.md" in text
    assert "同一版本只维护一份现役 PRD" in text
    assert "validate_semantic_coverage.py" in text
    assert "prd_skill_unavailable" in (skill_root / "evals" / "scenarios.json").read_text(
        encoding="utf-8"
    )
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
