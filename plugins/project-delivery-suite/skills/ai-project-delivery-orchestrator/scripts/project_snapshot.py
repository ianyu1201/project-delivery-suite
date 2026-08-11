#!/usr/bin/env python3
"""Create a bounded, read-only project inventory for delivery planning."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
from collections import Counter
from pathlib import Path


EXCLUDED = {
    ".git", ".build", ".cache", ".next", ".swiftpm", ".venv", "DerivedData",
    "Pods", "build", "coverage", "dist", "node_modules", "vendor", "xcuserdata",
}
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt"}
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".mov"}
TEST_MARKERS = ("test", "tests", "spec", "specs", "uitest", "xctest")
EVIDENCE_MARKERS = ("evidence", "验收证据", "运行证据", "证据")


def git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def scan(root: Path, max_files: int, max_entries: int) -> dict:
    counts = Counter()
    docs: list[str] = []
    media_count = 0
    evidence_count = 0
    test_count = 0
    total_bytes = 0
    scanned = 0
    entries_seen = 0
    truncated = False
    excluded_directories: list[str] = []
    symlinks: list[str] = []
    scan_errors: list[str] = []

    pending = [root]
    while pending and not truncated:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    entries_seen += 1
                    if entries_seen > max_entries:
                        truncated = True
                        scan_errors.append(f"entry limit reached: {max_entries}")
                        break
                    path = Path(entry.path)
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except OSError as error:
                        scan_errors.append(f"{path}: {error}")
                        continue
                    relative = path.relative_to(root).as_posix()
                    if stat.S_ISLNK(info.st_mode):
                        if len(symlinks) < 200:
                            symlinks.append(relative)
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        if entry.name in EXCLUDED:
                            if len(excluded_directories) < 200:
                                excluded_directories.append(relative)
                            continue
                        pending.append(path)
                        continue
                    if not stat.S_ISREG(info.st_mode):
                        scan_errors.append(f"special file skipped: {relative}")
                        continue
                    scanned += 1
                    if scanned > max_files:
                        truncated = True
                        scan_errors.append(f"file limit reached: {max_files}")
                        break
                    suffix = path.suffix.lower() or "[no-extension]"
                    counts[suffix] += 1
                    total_bytes += info.st_size
                    lower_parts = [part.lower() for part in path.parts]
                    if suffix in DOC_SUFFIXES and len(docs) < 200:
                        docs.append(relative)
                    if suffix in MEDIA_SUFFIXES:
                        media_count += 1
                    if any(marker in part for part in lower_parts for marker in EVIDENCE_MARKERS):
                        evidence_count += 1
                    if any(marker in part for part in lower_parts for marker in TEST_MARKERS):
                        test_count += 1
        except OSError as error:
            scan_errors.append(f"{directory}: {error}")
            continue

    try:
        with os.scandir(root) as iterator:
            top_level = sorted(entry.name for entry in iterator)
    except OSError as error:
        top_level = []
        scan_errors.append(f"{root}: {error}")
    status = git(root, "status", "--short")
    coverage_gaps = []
    if symlinks:
        coverage_gaps.append("symlinks-not-followed")
    if excluded_directories:
        coverage_gaps.append("excluded-directories-not-scanned")
    if scan_errors or truncated:
        coverage_gaps.append("scan-incomplete")
    return {
        "status": "limited" if coverage_gaps else "complete",
        "root": str(root),
        "top_level": top_level,
        "files_scanned": min(scanned, max_files),
        "entries_seen": min(entries_seen, max_entries),
        "scan_truncated": truncated,
        "approx_bytes": total_bytes,
        "extensions": dict(counts.most_common(30)),
        "documents": sorted(docs),
        "media_files": media_count,
        "evidence_files": evidence_count,
        "test_like_files": test_count,
        "excluded_directories": sorted(excluded_directories),
        "symlinks": sorted(symlinks),
        "scan_errors": sorted(set(scan_errors)),
        "coverage_gaps": sorted(set(coverage_gaps)),
        "git": {
            "is_repository": git(root, "rev-parse", "--is-inside-work-tree") == "true",
            "branch": git(root, "branch", "--show-current"),
            "head": git(root, "rev-parse", "HEAD"),
            "status_entries": 0 if not status else len(status.splitlines()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Existing project directory")
    parser.add_argument("--max-files", type=int, default=50_000)
    parser.add_argument("--max-entries", type=int, default=100_000)
    args = parser.parse_args()
    root = Path(args.root).expanduser().absolute()
    if root.is_symlink() or not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")
    if args.max_files < 1:
        raise SystemExit("--max-files must be positive")
    if args.max_entries < 1:
        raise SystemExit("--max-entries must be positive")
    report = scan(root, args.max_files, args.max_entries)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
