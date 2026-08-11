#!/usr/bin/env python3
"""Regression tests for the installed-package self-check entrypoint."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


DELIVERY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    DELIVERY_ROOT
    / "package"
    / "project-delivery-suite"
    / "scripts"
    / "self_check.py"
)


class SelfCheckTests(unittest.TestCase):
    def run_self_check(self) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        payload = json.loads(completed.stdout)
        return completed, payload

    def test_installed_package_self_check_passes(self) -> None:
        completed, payload = self.run_self_check()
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(
            {"total": 22, "passed": 22, "failed": 0},
            payload["summary"],
        )

    def test_self_check_validates_minimum_prd_asset(self) -> None:
        _, payload = self.run_self_check()
        checks = payload["checks"]
        minimum_prd = [
            item
            for item in checks
            if isinstance(item, dict)
            and item.get("category") == "asset"
            and item.get("target") == "MINIMUM_PRD.md"
        ]
        self.assertEqual(1, len(minimum_prd))
        self.assertEqual("pass", minimum_prd[0]["status"])

    def test_self_check_exercises_both_gate_fixtures(self) -> None:
        _, payload = self.run_self_check()
        checks = payload["checks"]
        self.assertIsInstance(checks, list)
        gate_checks = {
            str(item["target"]): item
            for item in checks
            if isinstance(item, dict) and item.get("category") == "gate"
        }
        self.assertEqual(8, len(gate_checks))
        for gate in ("status", "handoff", "version-approval", "archive"):
            self.assertEqual("pass", gate_checks[f"complete:{gate}"]["status"])
            self.assertIn("status=pass", gate_checks[f"complete:{gate}"]["detail"])
            self.assertEqual("pass", gate_checks[f"blocked:{gate}"]["status"])
            self.assertIn("status=fail", gate_checks[f"blocked:{gate}"]["detail"])


if __name__ == "__main__":
    unittest.main()
