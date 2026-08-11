#!/usr/bin/env python3
"""Validate the Codex plugin and both bundled Skill release versions."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "project-delivery-suite"
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")


def main() -> int:
    canonical = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert SEMVER_RE.fullmatch(canonical), f"invalid canonical version: {canonical}"
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    observed = {
        "canonical": canonical,
        "codex_plugin": manifest["version"],
        "orchestrator_snapshot": (PLUGIN / "skills" / "project-delivery-orchestrator" / "VERSION").read_text(encoding="utf-8").strip(),
        "consolidator_snapshot": (PLUGIN / "skills" / "consolidate-project-versions" / "VERSION").read_text(encoding="utf-8").strip(),
    }
    mismatches = {name: value for name, value in observed.items() if value != canonical}
    assert not mismatches, f"release version drift: {mismatches}"

    print(json.dumps(observed, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
