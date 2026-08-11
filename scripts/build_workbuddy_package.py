#!/usr/bin/env python3
"""Build a deterministic WorkBuddy/SkillHub ZIP from the canonical source."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "distributions" / "workbuddy" / "package" / "project-delivery-suite"
DEFAULT_OUTPUT = ROOT / "distributions" / "workbuddy" / "dist" / "project-delivery-suite.zip"
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def build(output: Path) -> tuple[int, str]:
    files = sorted(path for path in SOURCE.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"WorkBuddy source is empty: {SOURCE}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = Path(SOURCE.name) / path.relative_to(SOURCE)
            info = zipfile.ZipInfo(relative.as_posix(), FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return len(files), digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count, digest = build(args.output.resolve())
    print(f"built={args.output.resolve()}")
    print(f"files={count}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
