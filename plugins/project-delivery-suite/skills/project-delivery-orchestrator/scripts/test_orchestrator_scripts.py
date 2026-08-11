from __future__ import annotations

import tempfile
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
