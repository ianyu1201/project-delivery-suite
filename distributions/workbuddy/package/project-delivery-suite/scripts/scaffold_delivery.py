#!/usr/bin/env python3
"""Preview or create a minimal governed delivery directory structure."""

from __future__ import annotations

import argparse
from pathlib import Path


def validate_component(raw: str) -> str:
    """Preserve a project-defined version name while keeping it one safe path part."""
    if not raw or raw in {".", ".."}:
        raise ValueError("version must be a non-empty directory name")
    if "\x00" in raw or "/" in raw or "\\" in raw:
        raise ValueError("version must be one directory name without path separators")
    if Path(raw).name != raw:
        raise ValueError("version must be one directory name")
    return raw


def relative_paths(scale: str, profile: str, version: str, topology: str) -> list[Path]:
    if topology == "numbered-lifecycle":
        paths = {
            Path("00_项目治理"),
            Path("01_产品") / version,
            Path("02_设计") / version,
            Path("03_工程"),
            Path("04_技术决策"),
            Path("90_历史归档"),
        }
        if scale in {"medium", "large"}:
            paths.add(Path("03_工程") / version / "验收证据")
        if scale == "large":
            paths.update({
                Path("03_工程") / version / "风险与迁移",
                Path("03_工程") / version / "发布与回滚",
            })
        if profile == "robotics":
            paths.update({
                Path("03_工程") / "接口",
                Path("03_工程") / "安全",
                Path("03_工程") / version / "验收证据" / "仿真",
                Path("03_工程") / version / "验收证据" / "台架",
                Path("03_工程") / version / "验收证据" / "实机",
            })
        elif profile == "hybrid":
            paths.update({
                Path("03_工程") / "接口",
                Path("03_工程") / "兼容性",
                Path("03_工程") / version / "验收证据" / "集成",
            })
    else:
        paths = {
            Path("docs/00_project"),
            Path("docs/10_product"),
            Path("docs/20_releases") / version,
            Path("evidence") / version,
            Path("media/reference/candidates"),
            Path("media/reference/confirmed"),
        }
        if scale in {"medium", "large"}:
            paths.update({
                Path("docs/20_releases") / version / name
                for name in ("scope", "design", "contracts", "delivery", "acceptance")
            })
            paths.add(Path("docs/30_engineering/decisions"))
        if scale == "large":
            paths.update({
                Path("docs/20_releases") / version / name
                for name in ("architecture", "risk", "migration", "release")
            })
            paths.add(Path("docs/30_engineering/interfaces"))
        if profile == "robotics":
            paths.update({
                Path("docs/30_engineering/interfaces"),
                Path("docs/30_engineering/safety"),
                Path("evidence") / version / "simulation",
                Path("evidence") / version / "bench",
                Path("evidence") / version / "device",
            })
        elif profile == "hybrid":
            paths.update({
                Path("docs/30_engineering/interfaces"),
                Path("docs/30_engineering/compatibility"),
                Path("evidence") / version / "integration",
            })
    return sorted(paths, key=lambda p: p.as_posix())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Existing project root")
    parser.add_argument("--scale", required=True, choices=("small", "medium", "large"))
    parser.add_argument(
        "--profile", required=True,
        choices=("software", "ios", "web", "robotics", "hybrid"),
    )
    parser.add_argument(
        "--topology",
        default="legacy-docs",
        choices=("numbered-lifecycle", "legacy-docs"),
        help=(
            "Approved first-project folder topology; legacy-docs remains the CLI "
            "compatibility default; never use this script for a later full-version copy"
        ),
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--apply", action="store_true", help="Create missing directories")
    args = parser.parse_args()

    root = Path(args.root).expanduser().absolute()
    if root.is_symlink() or not root.is_dir():
        raise SystemExit(f"Project root must already exist: {root}")
    try:
        version = validate_component(args.version)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    planned = relative_paths(args.scale, args.profile, version, args.topology)
    created: list[str] = []
    existing: list[str] = []
    for relative in planned:
        target = root / relative
        if target.exists():
            existing.append(relative.as_posix())
        elif args.apply:
            target.mkdir(parents=True, exist_ok=False)
            created.append(relative.as_posix())

    mode = "APPLY" if args.apply else "PREVIEW"
    print(f"mode: {mode}")
    print(f"root: {root}")
    print(
        f"profile: {args.profile}; scale: {args.scale}; "
        f"topology: {args.topology}; version: {version}"
    )
    print("planned:")
    for relative in planned:
        relative_text = relative.as_posix()
        if relative_text in existing:
            marker = "exists"
        elif relative_text in created:
            marker = "created"
        else:
            marker = "create"
        print(f"  [{marker}] {relative.as_posix()}")
    if args.apply:
        print(f"created: {len(created)}; already existed: {len(existing)}")
    else:
        print("No files or directories were changed. Re-run with --apply after approval.")


if __name__ == "__main__":
    main()
