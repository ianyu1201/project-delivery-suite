#!/usr/bin/env python3
"""Regression tests for the V0.2.6 state and anti-drift gate."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


DELIVERY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    DELIVERY_ROOT
    / "package"
    / "project-delivery-suite"
    / "scripts"
    / "validate_project_state.py"
)
SPEC = importlib.util.spec_from_file_location("validate_project_state", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProjectFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.version = "V0.2.0"
        self.active = root / self.version
        self.archive = root / "90_历史归档"
        self.prd = self.active / "01_产品" / "PRD.md"
        self.ui = self.active / "02_设计" / "UI_CONTRACT.md"
        self.governance = self.active / "00_项目治理"
        self.state = root / "PROJECT_STATE.md"
        self._create()

    def _create(self) -> None:
        self.prd.parent.mkdir(parents=True)
        self.ui.parent.mkdir(parents=True)
        self.governance.mkdir(parents=True)
        self.archive.mkdir()
        self.prd.write_text(
            """---
version: "V0.2.0"
status: "approved"
candidate_state: "current"
validation_status: "passed"
acceptance_status: "accepted"
version_approval_status: "approved"
---

# Demo V0.2.0 PRD

| ID | Testable requirement | Acceptance evidence | Source | Status |
|---|---|---|---|---|
| REQ-001 | Main path works | RUN-001 | approved scope | active |
| REQ-N1-001 | Filter records | RUN-002 | approved change | active |
""",
            encoding="utf-8",
        )
        self.ui.write_text(
            """# Demo V0.2.0 UI 实现与运行验收合同

> 状态：frozen
> 产品合同：V0.2.0/01_产品/PRD.md

## 需求追踪

| Requirement ID | Contract / RUN | Status |
|---|---|---|
| REQ-001 | RUN-001 | covered |
| REQ-N1-001 | RUN-002 | covered |
""",
            encoding="utf-8",
        )
        evidence_files = {
            "DEVELOPMENT_HANDOFF.md": "# Development handoff\n",
            "EVIDENCE_MANIFEST.md": "# Evidence manifest\n",
            "ACCEPTANCE_REPORT.md": "# Acceptance report\n\nResult: accepted\n",
            "CANDIDATE_MANIFEST.json": '{"status":"verified"}\n',
        }
        for name, content in evidence_files.items():
            (self.governance / name).write_text(content, encoding="utf-8")
        (self.root / "AGENTS.md").write_text(
            f"# Agent rules\n\n- 项目根目录：{self.root}\n- 当前版本：{self.version}（current）\n",
            encoding="utf-8",
        )
        (self.root / "README.md").write_text(
            f"# Demo\n\n## 当前版本\n\n- **{self.version}**（current）\n",
            encoding="utf-8",
        )
        (self.root / "SESSION_REGISTRY.md").write_text(
            f"# Sessions\n\nWorking directory: {self.active}\n",
            encoding="utf-8",
        )
        self.write_state()

    def state_values(self) -> dict[str, str]:
        return {
            "state_schema": "1.0",
            "workspace_root": str(self.root),
            "active_version_root": str(self.active),
            "archive_root": str(self.archive),
            "repo_root": str(self.root),
            "staging_root": "",
            "topology": "complete-snapshot",
            "latest_observed": self.version,
            "current_approved": self.version,
            "active_candidate": "",
            "source_lineage": "V0.1.0 -> V0.2.0",
            "governance_cycle_id": "GC-V0.2.0-001",
            "prd_status": "approved",
            "ui_contract_status": "frozen",
            "validation_status": "passed",
            "acceptance_status": "accepted",
            "version_approval_status": "approved",
            "version_approval_intent": "received",
            "archive_status": "pending",
            "anti_drift_status": "enforced",
            "version_status": "version_approved-current",
            "phase": "S7",
            "fixed_point": "sha256:0123456789abcdef",
            "prd_path": "V0.2.0/01_产品/PRD.md",
            "ui_contract_path": "V0.2.0/02_设计/UI_CONTRACT.md",
            "development_handoff_path": "V0.2.0/00_项目治理/DEVELOPMENT_HANDOFF.md",
            "evidence_manifest_path": "V0.2.0/00_项目治理/EVIDENCE_MANIFEST.md",
            "acceptance_report_path": "V0.2.0/00_项目治理/ACCEPTANCE_REPORT.md",
            "candidate_manifest_path": "V0.2.0/00_项目治理/CANDIDATE_MANIFEST.json",
            "session_registry_path": "SESSION_REGISTRY.md",
        }

    def write_state(self, **overrides: str) -> None:
        values = self.state_values()
        values.update(overrides)
        lines = ["---"]
        lines.extend(f'{key}: {json.dumps(value, ensure_ascii=False)}' for key, value in values.items())
        lines.extend(
            [
                "---",
                "",
                "# Demo 项目状态",
                "",
                "> YAML frontmatter is the machine-readable authority.",
                "",
            ]
        )
        self.state.write_text("\n".join(lines), encoding="utf-8")


def ids(result: dict[str, object]) -> set[str]:
    findings = result["findings"]
    assert isinstance(findings, list)
    return {str(item["id"]) for item in findings}


class ValidateProjectStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = ProjectFixture(Path(self.temporary.name) / "project")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def audit(self, gate: str = "status") -> dict[str, object]:
        return MODULE.audit_project(self.fixture.root, gate)

    def test_happy_path_passes_all_gates(self) -> None:
        for gate in MODULE.GATES:
            with self.subTest(gate=gate):
                result = self.audit(gate)
                self.assertEqual("pass", result["status"], result)

    def test_draft_prd_cannot_be_version_approved(self) -> None:
        self.fixture.write_state(prd_status="draft")
        text = self.fixture.prd.read_text(encoding="utf-8").replace(
            'status: "approved"', 'status: "draft"', 1
        )
        self.fixture.prd.write_text(text, encoding="utf-8")
        result = self.audit()
        self.assertEqual("fail", result["status"])
        self.assertIn("STATE-APPROVAL-PRD", ids(result))

    def test_pending_validation_cannot_be_approved(self) -> None:
        self.fixture.write_state(validation_status="pending")
        result = self.audit()
        self.assertIn("STATE-APPROVAL-VALIDATION", ids(result))

    def test_pending_acceptance_cannot_be_approved(self) -> None:
        self.fixture.write_state(acceptance_status="pending")
        result = self.audit()
        self.assertIn("STATE-APPROVAL-ACCEPTANCE", ids(result))

    def test_archive_cannot_precede_approval(self) -> None:
        self.fixture.write_state(
            current_approved="",
            version_approval_status="pending",
            archive_status="organized",
            version_status="accepted",
        )
        result = self.audit("archive")
        result_ids = ids(result)
        self.assertIn("STATE-ARCHIVE-ORDER", result_ids)
        self.assertIn("GATE-APPROVAL", result_ids)

    def test_moved_workspace_path_is_detected(self) -> None:
        missing = self.fixture.root.parent / "old-location"
        self.fixture.write_state(workspace_root=str(missing))
        result = self.audit()
        self.assertIn("PATH-WORKSPACE_ROOT", ids(result))

    def test_stale_agents_version_is_detected(self) -> None:
        agents = self.fixture.root / "AGENTS.md"
        agents.write_text(
            f"# Rules\n\n- 项目根目录：{self.fixture.root}\n- 当前版本：V0.1.0（active）\n",
            encoding="utf-8",
        )
        result = self.audit()
        self.assertIn("DRIFT-AGENTS-VERSION", ids(result))

    def test_stale_ui_version_is_detected(self) -> None:
        text = self.fixture.ui.read_text(encoding="utf-8").replace("V0.2.0", "V0.1.0")
        self.fixture.ui.write_text(text, encoding="utf-8")
        result = self.audit()
        self.assertIn("DRIFT-UI-VERSION", ids(result))
        self.assertIn("DRIFT-UI-PRD", ids(result))

    def test_missing_requirement_trace_blocks_handoff(self) -> None:
        text = self.fixture.ui.read_text(encoding="utf-8").replace(
            "| REQ-N1-001 | RUN-002 | covered |\n", ""
        )
        self.fixture.ui.write_text(text, encoding="utf-8")
        result = self.audit("handoff")
        self.assertIn("DRIFT-UI-TRACE", ids(result))

    def test_missing_evidence_blocks_version_approval(self) -> None:
        (self.fixture.governance / "ACCEPTANCE_REPORT.md").unlink()
        result = self.audit("version-approval")
        self.assertIn("EVIDENCE-ACCEPTANCE_REPORT_PATH", ids(result))

    def test_unresolved_conflict_blocks_handoff(self) -> None:
        with self.fixture.prd.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n| ID | Sources | Impact | Options | Authority | Status |\n"
                "|---|---|---|---|---|---|\n"
                "| CF-001 | A/B | behavior | choose | owner | unresolved |\n"
            )
        result = self.audit("handoff")
        self.assertIn("GATE-CONFLICT", ids(result))

    def test_legacy_state_is_diagnostic_only_for_mutation_gates(self) -> None:
        values = self.fixture.state_values()
        self.fixture.state.write_text(
            "\n".join(
                [
                    "# Legacy state",
                    f"- 工作区根 `workspace_root`：{values['workspace_root']}",
                    f"- 活动版本根 `active_version_root`：{values['active_version_root']}",
                    f"- 历史归档根 `archive_root`：{values['archive_root']}",
                    f"- 当前批准版本 `current_approved`：{values['current_approved']}",
                    "- PRD 状态：approved",
                    "- UI 合同状态：frozen",
                    "- 验证状态：passed",
                    "- 独立验收：accepted",
                    "- 版本批准：approved",
                    "- 归档状态：pending",
                    "- 版本状态：version_approved-current",
                    f"- 固定点：{values['fixed_point']}",
                ]
            ),
            encoding="utf-8",
        )
        result = self.audit("handoff")
        self.assertIn("STATE-SCHEMA-GATE", ids(result))

    def test_cli_returns_nonzero_and_json_for_invalid_state(self) -> None:
        self.fixture.write_state(validation_status="pending")
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(self.fixture.root),
                "--gate",
                "status",
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(1, completed.returncode)
        payload = json.loads(completed.stdout)
        self.assertEqual("fail", payload["status"])


if __name__ == "__main__":
    unittest.main()
