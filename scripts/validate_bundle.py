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
    # Validate navigability and data shape, not exact instruction wording.
    for document in [skill_root / "SKILL.md", *sorted((skill_root / "references").glob("*.md"))]:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                resolved = (document.parent / target.split("#", 1)[0]).resolve()
                assert resolved.is_relative_to(skill_root.resolve()), f"reference outside Skill: {target}"
                assert resolved.exists(), f"broken reference in {document.name}: {target}"
    cases = load_json(skill_root / "evals" / "behavior-cases.json")["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert case["prompt"] and case["fixture_files"] and case["required"]
        for path in case["fixture_files"]:
            assert not Path(path).is_absolute() and ".." not in Path(path).parts
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
