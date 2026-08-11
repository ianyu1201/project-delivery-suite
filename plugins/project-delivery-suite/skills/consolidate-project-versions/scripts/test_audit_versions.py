#!/usr/bin/env python3
"""Focused standard-library tests for :mod:`audit_versions`."""

from __future__ import annotations

import hashlib
import io
import errno
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path

import audit_versions


SCRIPT = Path(__file__).with_name("audit_versions.py")


class AuditVersionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _require_safe_scan(self) -> None:
        capabilities, _gaps = audit_versions._detect_capabilities()
        if not all(capabilities.values()):
            self.skipTest("safe descriptor traversal is unavailable on this platform")

    def _require_symlink_support(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symbolic links are unavailable on this platform")
        probe_target = Path(self.temp_dir.name) / "symlink-probe-target"
        probe_link = Path(self.temp_dir.name) / "symlink-probe-link"
        probe_target.write_text("probe", encoding="utf-8")
        try:
            probe_link.symlink_to(probe_target)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symbolic links are unavailable on this platform: {error}")
        finally:
            if probe_link.is_symlink() or probe_link.exists():
                probe_link.unlink()
            if probe_target.exists():
                probe_target.unlink()

    def test_root_symlink_is_rejected(self) -> None:
        self._require_symlink_support()
        link = Path(self.temp_dir.name) / "project-link"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(audit_versions.RootError):
            audit_versions.scan(link)

    def test_validated_root_preserves_trusted_snapshot(self) -> None:
        validated = audit_versions.validate_root(self.root)
        self.assertIsInstance(validated, Path)
        self.assertEqual(validated, self.root.absolute())
        self.assertEqual(
            audit_versions._identity(validated._trusted_stat),
            audit_versions._identity(self.root.lstat()),
        )
        derived = validated.with_segments(validated, "child")
        self.assertEqual(type(derived), type(Path()))
        self.assertEqual(derived, self.root.absolute() / "child")

    def test_symlink_is_recorded_and_not_followed(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        outside = Path(self.temp_dir.name) / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("outside", encoding="utf-8")
        link = self.root / "linked"
        link.symlink_to(outside, target_is_directory=True)
        result = audit_versions.scan(self.root)
        self.assertEqual(result.files, [])
        self.assertEqual(result.symlinks, [{"path": "linked", "target": str(outside)}])

    def test_hardlinks_count_once_in_totals(self) -> None:
        self._require_safe_scan()
        content = b"hard link content"
        first = self.root / "v1" / "a.bin"
        first.parent.mkdir()
        first.write_bytes(content)
        second = self.root / "v1" / "b.bin"
        os.link(first, second)
        report = audit_versions.summary_report(audit_versions.scan(self.root), include_excluded=False)
        self.assertEqual(report["totals"]["regular_files"], 2)
        self.assertEqual(report["totals"]["unique_files"], 1)
        self.assertEqual(report["logical_bytes"], len(content))
        self.assertEqual(len(report["hardlink_groups"]), 1)

    def test_sparse_file_reports_logical_and_allocated_bytes(self) -> None:
        self._require_safe_scan()
        sparse = self.root / "sparse.dat"
        with sparse.open("wb") as handle:
            handle.seek(1024 * 1024)
            handle.write(b"x")
        result = audit_versions.scan(self.root)
        record = result.files[0]
        self.assertEqual(record.logical_bytes, 1024 * 1024 + 1)
        self.assertGreaterEqual(record.allocated_bytes, 0)
        if hasattr(os.stat(sparse), "st_blocks"):
            self.assertEqual(record.allocated_bytes, os.stat(sparse).st_blocks * 512)

    def test_default_excluded_directory_is_reported_and_include_option_scans_it(self) -> None:
        self._require_safe_scan()
        generated = self.root / "node_modules"
        generated.mkdir()
        (generated / "generated.js").write_text("generated", encoding="utf-8")
        excluded = audit_versions.summary_report(audit_versions.scan(self.root), include_excluded=False)
        self.assertEqual(excluded["files"], [])
        self.assertEqual(excluded["excluded_directories"][0]["path"], "node_modules")
        included_result = audit_versions.scan(self.root, include_excluded=True)
        self.assertEqual([item.path for item in included_result.files], ["node_modules/generated.js"])

    def test_version_directory_file_mismatch_is_reported(self) -> None:
        self._require_safe_scan()
        path = self.root / "v1.0" / "requirements-v2.0.md"
        path.parent.mkdir()
        path.write_text("mismatch", encoding="utf-8")
        result = audit_versions.scan(self.root)
        self.assertEqual(result.files[0].directory_version, "v1.0")
        self.assertEqual(result.files[0].file_version, "v2.0")
        self.assertEqual(result.files[0].version_status, "mismatch")
        self.assertEqual(result.version_mismatches[0]["path"], "v1.0/requirements-v2.0.md")

    def test_manifest_uses_complete_sha256_and_summary_does_not_hash(self) -> None:
        self._require_safe_scan()
        path = self.root / "v3" / "data.txt"
        path.parent.mkdir()
        payload = b"hello manifest"
        path.write_bytes(payload)
        summary = audit_versions.summary_report(audit_versions.scan(self.root), include_excluded=False)
        self.assertNotIn("sha256", json.dumps(summary))
        manifest = audit_versions.manifest_report(
            audit_versions.scan(self.root, hash_files=True), include_excluded=False
        )
        expected = hashlib.sha256(payload).hexdigest()
        self.assertEqual(manifest["files"][0]["sha256"], expected)
        self.assertEqual(len(manifest["files"][0]["sha256"]), 64)

    def test_manifest_hash_open_rejects_symlink_path(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        target = self.root / "target.txt"
        target.write_text("target", encoding="utf-8")
        link = self.root / "link.txt"
        link.symlink_to(target)
        with self.assertRaises(OSError):
            audit_versions.file_sha256(link, target.stat())

    def test_max_files_bounds_records_and_returns_error(self) -> None:
        self._require_safe_scan()
        (self.root / "a.txt").write_text("a", encoding="utf-8")
        (self.root / "b.txt").write_text("b", encoding="utf-8")
        result = audit_versions.scan(self.root, max_files=1)
        self.assertEqual(len(result.files), 1)
        self.assertTrue(any("max_files=1" in error for error in result.errors))

    def test_cross_filesystem_entry_is_reported_unresolved_and_skipped(self) -> None:
        self._require_safe_scan()
        base_stat = os.stat(self.root)
        values = list(base_stat)
        values[0] = stat.S_IFDIR | 0o755
        values[2] = base_stat.st_dev + 1
        foreign_stat = os.stat_result(values)
        foreign_path = str(self.root / "mounted")

        class ForeignEntry:
            name = "mounted"
            path = foreign_path

            @staticmethod
            def is_symlink() -> bool:
                return False

            @staticmethod
            def stat(*, follow_symlinks: bool) -> os.stat_result:
                return foreign_stat

        scanner = audit_versions.TreeScanner(
            self.root,
            include_excluded=False,
            hash_files=False,
            max_files=audit_versions.DEFAULT_MAX_FILES,
        )
        with patch.object(audit_versions.os, "scandir", return_value=[ForeignEntry()]):
            result = scanner.scan()
        self.assertEqual(result.files, [])
        self.assertEqual(result.cross_filesystem[0]["path"], "mounted")
        self.assertTrue(result.errors)

    def test_root_replacement_before_open_is_blocked_and_cli_is_nonzero(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        outside = Path(self.temp_dir.name) / "outside-root"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        original_root = Path(self.temp_dir.name) / "root-original"

        real_open_directory = audit_versions._open_directory

        def replace_root(path, expected_stat, *, dir_fd=None):
            if dir_fd is None:
                self.root.rename(original_root)
                self.root.symlink_to(outside, target_is_directory=True)
            return real_open_directory(path, expected_stat, dir_fd=dir_fd)

        try:
            output = io.StringIO()
            with patch.object(audit_versions, "_open_directory", side_effect=replace_root):
                with redirect_stdout(output):
                    return_code = audit_versions.main(["manifest", str(self.root)])
            report = json.loads(output.getvalue())
            self.assertNotEqual(return_code, 0)
            self.assertEqual(report["files"], [])
            self.assertTrue(report["errors"])
            self.assertNotIn("secret.txt", output.getvalue())
        finally:
            if self.root.is_symlink():
                self.root.unlink()
            original_root.rename(self.root)

    def test_nested_replacement_before_open_is_blocked_and_cli_is_nonzero(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        nested = self.root / "nested"
        nested.mkdir()
        outside = Path(self.temp_dir.name) / "outside-nested"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        nested_original = self.root / "nested-original"

        real_open_directory = audit_versions._open_directory

        def replace_nested(path, expected_stat, *, dir_fd=None):
            if dir_fd is not None and path == "nested":
                nested.rename(nested_original)
                nested.symlink_to(outside, target_is_directory=True)
            return real_open_directory(path, expected_stat, dir_fd=dir_fd)

        try:
            output = io.StringIO()
            with patch.object(audit_versions, "_open_directory", side_effect=replace_nested):
                with redirect_stdout(output):
                    return_code = audit_versions.main(["manifest", str(self.root)])
            report = json.loads(output.getvalue())
            self.assertNotEqual(return_code, 0)
            self.assertEqual(report["files"], [])
            self.assertTrue(report["errors"])
            self.assertNotIn("secret.txt", output.getvalue())
        finally:
            if nested.is_symlink():
                nested.unlink()
            if nested_original.exists():
                nested_original.rename(nested)

    def test_root_replacement_during_scandir_is_unresolved(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        outside = Path(self.temp_dir.name) / "outside-scandir-root"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        original_root = Path(self.temp_dir.name) / "root-scandir-original"
        real_scandir = audit_versions.os.scandir
        replaced = False

        def race_scandir(descriptor):
            nonlocal replaced
            if not replaced:
                self.root.rename(original_root)
                self.root.symlink_to(outside, target_is_directory=True)
                replaced = True
            return real_scandir(descriptor)

        try:
            output = io.StringIO()
            with patch.object(audit_versions.os, "scandir", side_effect=race_scandir):
                with redirect_stdout(output):
                    return_code = audit_versions.main(["manifest", str(self.root)])
            report = json.loads(output.getvalue())
            self.assertNotEqual(return_code, 0)
            self.assertEqual(report["files"], [])
            self.assertTrue(any("replaced" in error or "identity" in error for error in report["errors"]))
            self.assertNotIn("secret.txt", output.getvalue())
        finally:
            if self.root.is_symlink():
                self.root.unlink()
            if original_root.exists():
                original_root.rename(self.root)

    def test_nested_replacement_during_scandir_is_unresolved(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        nested = self.root / "nested-scandir"
        nested.mkdir()
        outside = Path(self.temp_dir.name) / "outside-scandir-nested"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        nested_original = self.root / "nested-scandir-original"
        nested_inode = nested.stat().st_ino
        real_scandir = audit_versions.os.scandir
        replaced = False

        def race_scandir(descriptor):
            nonlocal replaced
            if not replaced and os.fstat(descriptor).st_ino == nested_inode:
                nested.rename(nested_original)
                nested.symlink_to(outside, target_is_directory=True)
                replaced = True
            return real_scandir(descriptor)

        try:
            output = io.StringIO()
            with patch.object(audit_versions.os, "scandir", side_effect=race_scandir):
                with redirect_stdout(output):
                    return_code = audit_versions.main(["manifest", str(self.root)])
            report = json.loads(output.getvalue())
            self.assertNotEqual(return_code, 0)
            self.assertEqual(report["files"], [])
            self.assertTrue(any("replaced" in error or "identity" in error for error in report["errors"]))
            self.assertNotIn("secret.txt", output.getvalue())
        finally:
            if nested.is_symlink():
                nested.unlink()
            if nested_original.exists():
                nested_original.rename(nested)

    def test_scan_error_is_reported_and_cli_returns_nonzero(self) -> None:
        self._require_safe_scan()
        if os.name != "posix":
            self.skipTest("chmod-based permission behavior is POSIX-specific")
        # A dangling symlink is intentionally not an error; an unreadable
        # directory is an error when the test is run by a non-root user.
        blocked = self.root / "blocked"
        blocked.mkdir()
        (blocked / "hidden.txt").write_text("hidden", encoding="utf-8")
        blocked.chmod(0)
        try:
            result = audit_versions.scan(self.root)
            geteuid = getattr(os, "geteuid", lambda: -1)
            if geteuid() == 0:
                self.skipTest("root can read chmod-0 directories")
            self.assertTrue(result.errors)
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "summary", str(self.root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("errors", json.loads(completed.stdout))
        finally:
            blocked.chmod(stat.S_IRWXU)

    def test_markdown_escapes_path_delimiters(self) -> None:
        self._require_safe_scan()
        weird = self.root / "v1" / "pipe|tick`name.txt"
        weird.parent.mkdir()
        weird.write_text("x", encoding="utf-8")
        report = audit_versions.summary_report(audit_versions.scan(self.root), include_excluded=False)
        markdown = audit_versions.render(report, "markdown")
        self.assertIn(r"pipe\|tick", markdown)
        self.assertIn("tick`name.txt", markdown)

    def test_cli_help_and_explicit_subcommands(self) -> None:
        self._require_safe_scan()
        help_result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, check=False
        )
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("summary", help_result.stdout)
        self.assertIn("manifest", help_result.stdout)
        summary_result = subprocess.run(
            [sys.executable, str(SCRIPT), "summary", str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(summary_result.returncode, 0)
        self.assertEqual(json.loads(summary_result.stdout)["command"], "summary")
        global_limit_result = subprocess.run(
            [sys.executable, str(SCRIPT), "--max-files", "0", "summary", str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(global_limit_result.returncode, 0)

    def test_report_status_schema_and_coverage_for_findings(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        (self.root / "link").symlink_to(self.root / "missing")
        report = audit_versions.summary_report(
            audit_versions.scan(self.root), include_excluded=False
        )
        self.assertEqual(report["schema_version"], audit_versions.SCHEMA_VERSION)
        self.assertEqual(report["scanner_version"], audit_versions.SCANNER_VERSION)
        self.assertEqual(report["status"], "limited")
        self.assertTrue(report["coverage_gaps"])

    def test_max_entries_counts_all_entry_kinds(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        (self.root / "v1").mkdir()
        (self.root / "v1" / "one.txt").write_text("1", encoding="utf-8")
        (self.root / "special").symlink_to(self.root / "v1", target_is_directory=True)
        result = audit_versions.scan(self.root, max_entries=1)
        self.assertEqual(result.entries_seen, 2)
        self.assertEqual(result.status, "limited")
        self.assertTrue(any("max_entries=1" in error for error in result.errors))

    def test_regex_rejects_prd_beta_and_four_components_and_preserves_raw_root(self) -> None:
        self._require_safe_scan()
        self.assertIsNone(audit_versions.version_from_filename("PRD-001"))
        self.assertEqual(audit_versions.versions_from_filename("v1.2beta"), [])
        self.assertEqual(audit_versions.versions_from_filename("v1.2.3.4"), [])
        custom = self.root / "alpha-r1"
        custom.mkdir()
        (custom / "foo-v1-v2.txt").write_text("x", encoding="utf-8")
        result = audit_versions.scan(self.root)
        self.assertIn("alpha-r1", result.raw_root_entries)
        self.assertEqual(result.files[0].version_status, "ambiguous")
        self.assertEqual(result.files[0].file_versions, ["v1", "v2"])

    def test_file_mode_and_manifest_stability_change_are_reported(self) -> None:
        self._require_safe_scan()
        path = self.root / "script-v1.sh"
        path.write_text("echo one", encoding="utf-8")
        path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        real_hash = audit_versions._stable_file_sha256

        def mutate_then_hash(file_path, expected, *, dir_fd=None):
            changed = os.open(file_path, os.O_WRONLY, dir_fd=dir_fd)
            try:
                os.write(changed, b"echo two")
            finally:
                os.close(changed)
            return real_hash(file_path, expected, dir_fd=dir_fd)

        with patch.object(audit_versions, "_stable_file_sha256", side_effect=mutate_then_hash):
            result = audit_versions.scan(self.root, hash_files=True)
        record = result.files[0]
        self.assertTrue(record.executable)
        self.assertEqual(record.filemode, "-rwx------")
        self.assertEqual(record.stability_status, "changed")
        self.assertEqual(result.status, "limited")

    def test_unsupported_scandir_capability_is_structured(self) -> None:
        with patch.object(audit_versions.os, "scandir", side_effect=TypeError("fd unsupported")):
            result = audit_versions.scan(self.root)
        self.assertEqual(result.status, "unsupported")
        report = audit_versions.summary_report(result, include_excluded=False)
        self.assertEqual(report["status"], "unsupported")
        self.assertTrue(report["coverage_gaps"])

    def test_broad_root_requires_explicit_opt_in(self) -> None:
        with self.assertRaises(audit_versions.RootError):
            audit_versions.validate_root(Path.home())
        # The CLI returns a report rather than argparse's traceback/error text.
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "summary", str(Path.home())],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["status"], "limited")

    def test_global_and_trailing_max_entries_arguments(self) -> None:
        self._require_safe_scan()
        (self.root / "a").write_text("a", encoding="utf-8")
        for args in (
            ["--max-entries", "0", "summary", str(self.root)],
            ["summary", str(self.root), "--max-entries", "0"],
        ):
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), *args],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(json.loads(completed.stdout)["status"], "limited")

    def test_root_swap_after_validation_before_scanner_is_fail_closed(self) -> None:
        self._require_safe_scan()
        original = Path(self.temp_dir.name) / "root-original"
        outside = Path(self.temp_dir.name) / "outside-real"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        (self.root / "inside.txt").write_text("inside", encoding="utf-8")
        real_scanner = audit_versions.TreeScanner

        def swap_then_construct(*args, **kwargs):
            self.root.rename(original)
            self.root.mkdir()
            (self.root / "replacement.txt").write_text("replacement", encoding="utf-8")
            return real_scanner(*args, **kwargs)

        try:
            with patch.object(audit_versions, "TreeScanner", side_effect=swap_then_construct):
                result = audit_versions.scan(self.root)
            self.assertNotEqual(result.status, "complete")
            self.assertEqual(result.files, [])
            self.assertTrue(any("identity" in error or "changed" in error for error in result.errors))
            self.assertNotIn("replacement.txt", " ".join(record.path for record in result.files))
        finally:
            if self.root.exists():
                for child in self.root.iterdir():
                    child.unlink()
                self.root.rmdir()
            if original.exists():
                original.rename(self.root)

    def test_cli_root_swap_after_single_validation_is_fail_closed(self) -> None:
        self._require_safe_scan()
        original = Path(self.temp_dir.name) / "cli-root-original"
        (self.root / "inside.txt").write_text("inside", encoding="utf-8")
        real_validate = audit_versions.validate_root
        validated_once = False

        def validate_then_swap(value, *, allow_broad_root=False):
            nonlocal validated_once
            validated = real_validate(value, allow_broad_root=allow_broad_root)
            if not validated_once:
                validated_once = True
                self.root.rename(original)
                self.root.mkdir()
                (self.root / "replacement.txt").write_text("replacement", encoding="utf-8")
            return validated

        try:
            output = io.StringIO()
            with patch.object(audit_versions, "validate_root", side_effect=validate_then_swap):
                with redirect_stdout(output):
                    return_code = audit_versions.main(["summary", str(self.root)])
            report = json.loads(output.getvalue())
            self.assertNotEqual(return_code, 0)
            self.assertNotEqual(report["status"], "complete")
            self.assertEqual(report["files"], [])
            self.assertTrue(validated_once)
            self.assertNotIn("replacement.txt", output.getvalue())
        finally:
            if self.root.exists():
                for child in self.root.iterdir():
                    child.unlink()
                self.root.rmdir()
            if original.exists():
                original.rename(self.root)

    def test_reverse_scandir_produces_identical_report(self) -> None:
        self._require_safe_scan()
        self._require_symlink_support()
        for directory in ("V01", "release-1.0", "misc"):
            nested = self.root / directory
            nested.mkdir()
            (nested / f"artifact-{directory}-v1.txt").write_text(directory, encoding="utf-8")
        (self.root / "link").symlink_to(self.root / "missing")
        normal = audit_versions.summary_report(
            audit_versions.scan(self.root), include_excluded=False
        )
        real_scandir = audit_versions.os.scandir

        def reverse_scandir(descriptor):
            iterator = real_scandir(descriptor)
            try:
                entries = list(iterator)
            finally:
                iterator.close()
            return entries[::-1]

        with patch.object(audit_versions.os, "scandir", side_effect=reverse_scandir):
            reversed_report = audit_versions.summary_report(
                audit_versions.scan(self.root), include_excluded=False
            )
        self.assertEqual(normal, reversed_report)

    def test_raw_version_labels_are_preserved_and_normalization_is_only_heuristic(self) -> None:
        self._require_safe_scan()
        first = self.root / "V01"
        second = self.root / "release-1.0"
        first.mkdir()
        second.mkdir()
        (first / "artifact-v1.txt").write_text("one", encoding="utf-8")
        (second / "artifact-v1.0.txt").write_text("two", encoding="utf-8")
        (self.root / "mixed-v1-release-1.0.txt").write_text("three", encoding="utf-8")
        result = audit_versions.scan(self.root)
        by_path = {record.path: record for record in result.files}
        self.assertEqual(by_path["V01/artifact-v1.txt"].directory_version, "V01")
        self.assertEqual(by_path["V01/artifact-v1.txt"].normalized_directory_version, "v1")
        self.assertEqual(by_path["V01/artifact-v1.txt"].version_status, "ambiguous")
        self.assertEqual(by_path["release-1.0/artifact-v1.0.txt"].version_status, "ambiguous")
        self.assertEqual(by_path["mixed-v1-release-1.0.txt"].version_status, "ambiguous")
        self.assertEqual(
            audit_versions.version_from_directory("V01"),
            "V01",
        )
        self.assertEqual(
            audit_versions.normalized_version_from_directory("V01"),
            "v1",
        )
        self.assertEqual(
            audit_versions.versions_from_filename("mixed-v1-release-1.0.txt"),
            ["v1", "release-1.0"],
        )
        self.assertEqual(result.status, "limited")

    def test_version_directory_raw_label_collision_limits_even_when_empty(self) -> None:
        self._require_safe_scan()
        (self.root / "V01").mkdir()
        (self.root / "v1").mkdir()
        result = audit_versions.scan(self.root)
        report = audit_versions.summary_report(result, include_excluded=False)
        self.assertEqual(result.files, [])
        self.assertEqual(report["status"], "limited")
        self.assertEqual(len(report["version_collisions"]), 1)
        collision = report["version_collisions"][0]
        self.assertEqual(collision["normalized_version"], "v1")
        self.assertEqual(collision["raw_variants"], ["V01", "v1"])
        self.assertTrue(any("version naming collision" in gap for gap in report["coverage_gaps"]))

    def test_file_raw_label_collision_limits_across_files(self) -> None:
        self._require_safe_scan()
        (self.root / "artifact-V01.txt").write_text("one", encoding="utf-8")
        (self.root / "artifact-v1.txt").write_text("two", encoding="utf-8")
        result = audit_versions.scan(self.root)
        report = audit_versions.summary_report(result, include_excluded=False)
        self.assertEqual(report["status"], "limited")
        self.assertEqual(len(report["version_collisions"]), 1)
        collision = report["version_collisions"][0]
        self.assertEqual(collision["normalized_version"], "v1")
        self.assertEqual(collision["raw_variants"], ["V01", "v1"])
        self.assertEqual(
            [source["path"] for source in collision["sources"]],
            ["artifact-V01.txt", "artifact-v1.txt"],
        )

    def test_post_hash_entry_signature_race_clears_digest_and_is_limited(self) -> None:
        self._require_safe_scan()
        path = self.root / "artifact-v1.txt"
        path.write_text("before", encoding="utf-8")
        real_hash = audit_versions._stable_file_sha256

        def mutate_after_hash(file_path, expected, *, dir_fd=None):
            digest = real_hash(file_path, expected, dir_fd=dir_fd)
            descriptor = os.open(file_path, os.O_WRONLY, dir_fd=dir_fd)
            try:
                os.ftruncate(descriptor, 0)
                os.write(descriptor, b"after")
            finally:
                os.close(descriptor)
            return digest

        with patch.object(audit_versions, "_stable_file_sha256", side_effect=mutate_after_hash):
            result = audit_versions.scan(self.root, hash_files=True)
        record = result.files[0]
        self.assertIsNone(record.sha256)
        self.assertEqual(record.stability_status, "changed")
        self.assertEqual(result.status, "limited")

    def test_hash_oserror_statuses_distinguish_unreadable_replaced_and_unknown(self) -> None:
        self._require_safe_scan()
        path = self.root / "artifact-v1.txt"
        path.write_text("content", encoding="utf-8")
        for failure, expected_status in (
            (PermissionError(errno.EACCES, "denied"), "unreadable"),
            (FileNotFoundError(errno.ENOENT, "gone"), "replaced"),
            (OSError(errno.EIO, "read error"), "unknown"),
        ):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(audit_versions, "_stable_file_sha256", side_effect=failure):
                    result = audit_versions.scan(self.root, hash_files=True)
                record = result.files[0]
                self.assertEqual(record.stability_status, expected_status)
                self.assertIsNone(record.sha256)
                self.assertNotEqual(result.status, "complete")


if __name__ == "__main__":
    unittest.main()
