from __future__ import annotations

import tempfile
import os
from unittest import mock
import unittest
from pathlib import Path

import project_snapshot
import scaffold_delivery


class ScaffoldDeliveryTests(unittest.TestCase):
    def test_preserves_project_defined_version_name(self) -> None:
        self.assertEqual(scaffold_delivery.validate_component("alpha-r3"), "alpha-r3")
        self.assertEqual(scaffold_delivery.validate_component("第三版"), "第三版")

    def test_rejects_path_like_version(self) -> None:
        for value in ("", ".", "..", "V1/V2", "V1\\V2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scaffold_delivery.validate_component(value)

    def test_numbered_lifecycle_is_minimal_and_has_archive(self) -> None:
        paths = {
            path.as_posix()
            for path in scaffold_delivery.relative_paths(
                "small", "software", "alpha-r1", "numbered-lifecycle"
            )
        }
        self.assertIn("00_项目治理", paths)
        self.assertIn("01_产品/alpha-r1", paths)
        self.assertIn("02_设计/alpha-r1", paths)
        self.assertIn("03_工程", paths)
        self.assertIn("04_技术决策", paths)
        self.assertIn("90_历史归档", paths)
        self.assertNotIn("05_独立实验", paths)

    def test_legacy_docs_remains_available_for_existing_convention(self) -> None:
        paths = {
            path.as_posix()
            for path in scaffold_delivery.relative_paths(
                "small", "web", "release-2026-08", "legacy-docs"
            )
        }
        self.assertIn("docs/20_releases/release-2026-08", paths)

    def test_intermediate_symlink_blocks_entire_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, outside = base / "project", base / "outside"
            root.mkdir(); outside.mkdir()
            (root / "docs").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                scaffold_delivery.create_directories(root, [Path("first"), Path("docs/next")])
            self.assertFalse((root / "first").exists())
            self.assertEqual(list(outside.iterdir()), [])

    def test_late_file_conflict_is_detected_before_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").write_text("user data")
            with self.assertRaises(ValueError):
                scaffold_delivery.create_directories(root, [Path("first"), Path("docs/next")])
            self.assertFalse((root / "first").exists())
            self.assertEqual((root / "docs").read_text(), "user data")

    def test_safe_creation_can_be_repeated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = [Path("docs/product"), Path("evidence/v1")]
            created, existing = scaffold_delivery.create_directories(root, plan)
            self.assertEqual(len(created), 2)
            self.assertEqual(existing, [])
            created, existing = scaffold_delivery.create_directories(root, plan)
            self.assertEqual(created, [])
            self.assertEqual(len(existing), 2)

    def test_broken_link_and_traversal_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "broken").symlink_to(root / "absent")
            for path in (Path("broken/child"), Path("../outside"), root / "absolute"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    scaffold_delivery.preflight(root, [path])

    def test_link_introduced_after_preflight_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, outside = base / "project", base / "outside"
            root.mkdir(); outside.mkdir()
            (root / "docs").mkdir()
            real_open = os.open
            switched = False
            def replace_on_open(path, flags, *args, **kwargs):
                nonlocal switched
                if path == "docs" and not switched:
                    switched = True
                    (root / "docs").rmdir()
                    (root / "docs").symlink_to(outside, target_is_directory=True)
                return real_open(path, flags, *args, **kwargs)
            with mock.patch.object(os, "open", side_effect=replace_on_open) as patched:
                with mock.patch.object(os, "supports_dir_fd", os.supports_dir_fd | {patched}):
                    with self.assertRaises(OSError):
                        scaffold_delivery.create_directories(root, [Path("docs/child")])
            self.assertTrue(switched)
            self.assertEqual(list(outside.iterdir()), [])


class ProjectSnapshotTests(unittest.TestCase):
    def test_complete_scan_for_plain_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("ok", encoding="utf-8")
            report = project_snapshot.scan(root, max_files=10, max_entries=10)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["files_scanned"], 1)

    def test_excluded_directory_is_a_coverage_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "unique.js").write_text("x", encoding="utf-8")
            report = project_snapshot.scan(root, max_files=10, max_entries=10)
        self.assertEqual(report["status"], "limited")
        self.assertIn("node_modules", report["excluded_directories"])
        self.assertIn("excluded-directories-not-scanned", report["coverage_gaps"])

    def test_entry_limit_is_fail_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(3):
                (root / f"{index}.txt").write_text("x", encoding="utf-8")
            report = project_snapshot.scan(root, max_files=10, max_entries=2)
        self.assertEqual(report["status"], "limited")
        self.assertTrue(report["scan_truncated"])

    def test_symlink_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside.txt"
            outside.write_text("secret", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            report = project_snapshot.scan(root, max_files=10, max_entries=10)
        self.assertEqual(report["status"], "limited")
        self.assertIn("link.txt", report["symlinks"])
        self.assertEqual(report["files_scanned"], 1)


if __name__ == "__main__":
    unittest.main()
