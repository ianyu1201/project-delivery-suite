#!/usr/bin/env python3
"""Run a dependency-free installed-package self-check in temporary directories.

The check never edits a real project. It compiles and imports the bundled
runtime scripts, exercises their CLI help, then runs every project-state gate
against one complete fixture and one deliberately blocked fixture.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ASSET_DIR = SCRIPT_DIR.parent / "assets"
RUNTIME_SCRIPTS = (
    "audit_versions.py",
    "project_snapshot.py",
    "scaffold_delivery.py",
    "validate_project_state.py",
)
GATES = ("status", "handoff", "version-approval", "archive")


@dataclass(frozen=True)
class Check:
    category: str
    target: str
    status: str
    detail: str


def record(checks: list[Check], category: str, target: str, passed: bool, detail: str) -> None:
    checks.append(Check(category, target, "pass" if passed else "fail", detail))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def state_text(root: Path, *, complete: bool) -> str:
    version = "V0.6.0"
    active = root / version
    values = {
        "state_schema": "1.0",
        "workspace_root": str(root),
        "active_version_root": str(active),
        "archive_root": str(root / "90_历史归档"),
        "repo_root": str(root),
        "staging_root": "",
        "topology": "complete-snapshot",
        "latest_observed": version,
        "current_approved": version,
        "active_candidate": "" if complete else version,
        "source_lineage": "synthetic self-check fixture",
        "governance_cycle_id": "GC-SELF-CHECK-001",
        "prd_status": "approved" if complete else "draft",
        "ui_contract_status": "frozen" if complete else "draft",
        "validation_status": "passed" if complete else "pending",
        "acceptance_status": "accepted" if complete else "pending",
        "version_approval_status": "approved" if complete else "pending",
        "version_approval_intent": "received" if complete else "none",
        "archive_status": "pending",
        "anti_drift_status": "enforced",
        "version_status": "version_approved-current" if complete else "candidate_materialized",
        "phase": "S7" if complete else "S0",
        "fixed_point": "sha256:self-check-fixed-point" if complete else "",
        "prd_path": f"{version}/01_产品/PRD.md",
        "ui_contract_path": f"{version}/02_设计/UI_CONTRACT.md",
        "development_handoff_path": f"{version}/00_项目治理/DEVELOPMENT_HANDOFF.md",
        "evidence_manifest_path": f"{version}/00_项目治理/EVIDENCE_MANIFEST.md",
        "acceptance_report_path": f"{version}/00_项目治理/ACCEPTANCE_REPORT.md",
        "candidate_manifest_path": f"{version}/00_项目治理/CANDIDATE_MANIFEST.json",
        "session_registry_path": "SESSION_REGISTRY.md",
    }
    lines = ["---"]
    lines.extend(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in values.items())
    lines.extend(["---", "", "# Synthetic self-check project state", ""])
    return "\n".join(lines)


def create_fixture(root: Path, *, complete: bool) -> None:
    version = "V0.6.0"
    active = root / version
    governance = active / "00_项目治理"
    (root / "90_历史归档").mkdir(parents=True)
    prd_status = "approved" if complete else "draft"
    ui_status = "frozen" if complete else "draft"
    write(
        active / "01_产品" / "PRD.md",
        f'''---
version: "{version}"
status: "{prd_status}"
---

# Synthetic PRD

| ID | Testable requirement | Evidence | Source | Status |
|---|---|---|---|---|
| REQ-SELF-001 | Self-check path works | RUN-SELF-001 | test fixture | active |
''',
    )
    write(
        active / "02_设计" / "UI_CONTRACT.md",
        f'''# Synthetic {version} UI contract

> 状态：{ui_status}
> 产品合同：{version}/01_产品/PRD.md

| Requirement ID | Contract / RUN | Status |
|---|---|---|
| REQ-SELF-001 | RUN-SELF-001 | covered |
''',
    )
    if complete:
        for name, content in {
            "DEVELOPMENT_HANDOFF.md": "# Synthetic development handoff\n",
            "EVIDENCE_MANIFEST.md": "# Synthetic evidence manifest\n",
            "ACCEPTANCE_REPORT.md": "# Synthetic acceptance report\n\nResult: accepted\n",
            "CANDIDATE_MANIFEST.json": '{"fixture":"synthetic","status":"verified"}\n',
        }.items():
            write(governance / name, content)
    write(root / "PROJECT_STATE.md", state_text(root, complete=complete))
    write(root / "AGENTS.md", f"# Synthetic rules\n\n- 项目根目录：{root}\n- 当前版本：{version}\n")
    write(root / "README.md", f"# Synthetic fixture\n\n## 当前版本\n\n- {version}\n")
    write(root / "SESSION_REGISTRY.md", f"# Synthetic sessions\n\nWorking directory: {active}\n")


def smoke_scripts(checks: list[Check], scratch: Path) -> None:
    sys.dont_write_bytecode = True
    scripts = (Path(__file__).resolve(),) + tuple(SCRIPT_DIR / name for name in RUNTIME_SCRIPTS)
    for script in scripts:
        try:
            py_compile.compile(
                str(script), cfile=str(scratch / f"{script.stem}.pyc"), doraise=True
            )
            record(checks, "compile", script.name, True, "syntax valid")
        except py_compile.PyCompileError as error:
            record(checks, "compile", script.name, False, str(error))

    for script_name in RUNTIME_SCRIPTS:
        script = SCRIPT_DIR / script_name
        module_name = f"ai_delivery_self_check_{script.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, script)
            if spec is None or spec.loader is None:
                raise RuntimeError("cannot create import specification")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            record(checks, "import", script_name, True, "imported without side effects")
        except Exception as error:  # noqa: BLE001 - report every installed-package failure
            record(checks, "import", script_name, False, f"{type(error).__name__}: {error}")
        finally:
            sys.modules.pop(module_name, None)

        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        record(
            checks,
            "cli-help",
            script_name,
            completed.returncode == 0,
            f"exit={completed.returncode}",
        )


def check_minimum_prd(checks: list[Check]) -> None:
    path = ASSET_DIR / "MINIMUM_PRD.md"
    required = (
        "## 文档状态",
        "## 1. 产品目标",
        "## 3. 本版本范围",
        "## 4. 产品需求",
        "REQ-001",
        "## 7. 验收条件",
        "AC-001",
        "## 8. 开放问题与冲突",
        "## 9. 追溯与变更",
        "状态必须保持 `draft`",
    )
    try:
        text = path.read_text(encoding="utf-8")
        missing = [token for token in required if token not in text]
        record(
            checks,
            "asset",
            path.name,
            not missing,
            "minimum PRD fallback contract present"
            if not missing
            else f"missing required content: {', '.join(missing)}",
        )
    except OSError as error:
        record(checks, "asset", path.name, False, f"{type(error).__name__}: {error}")


def exercise_gates(checks: list[Check], scratch: Path) -> None:
    validator = SCRIPT_DIR / "validate_project_state.py"
    fixtures = {
        "complete": (scratch / "fixture-complete", True, 0, "pass"),
        "blocked": (scratch / "fixture-blocked", False, 1, "fail"),
    }
    for label, (root, complete, expected_exit, expected_status) in fixtures.items():
        create_fixture(root, complete=complete)
        for gate in GATES:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    str(root),
                    "--gate",
                    gate,
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
            try:
                payload = json.loads(completed.stdout)
                actual_status = payload.get("status")
                summary = payload.get("summary", {})
                errors = summary.get("errors", "?") if isinstance(summary, dict) else "?"
                parsed = True
            except json.JSONDecodeError:
                actual_status = "invalid-json"
                errors = "?"
                parsed = False
            passed = (
                parsed
                and completed.returncode == expected_exit
                and actual_status == expected_status
            )
            record(
                checks,
                "gate",
                f"{label}:{gate}",
                passed,
                f"exit={completed.returncode}, status={actual_status}, errors={errors}",
            )


def result_payload(checks: list[Check]) -> dict[str, object]:
    passed = sum(check.status == "pass" for check in checks)
    failed = len(checks) - passed
    return {
        "schema": "ai-project-delivery-self-check/1.0",
        "status": "pass" if failed == 0 else "fail",
        "scope": "installed package; synthetic temporary fixtures only",
        "summary": {"total": len(checks), "passed": passed, "failed": failed},
        "checks": [asdict(check) for check in checks],
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    assert isinstance(summary, dict)
    lines = [
        "# Project Delivery Suite self-check",
        "",
        f"Status: `{result['status']}`  ",
        f"Scope: `{result['scope']}`  ",
        f"Checks: {summary['passed']}/{summary['total']} passed",
        "",
        "| Category | Target | Status | Detail |",
        "|---|---|---|---|",
    ]
    checks = result["checks"]
    assert isinstance(checks, list)
    for check in checks:
        assert isinstance(check, dict)
        values = [str(check[key]).replace("|", "\\|") for key in ("category", "target", "status", "detail")]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dependency-free installed-package self-check; writes only temporary fixtures."
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checks: list[Check] = []
    check_minimum_prd(checks)
    with tempfile.TemporaryDirectory(prefix="ai-project-delivery-self-check-") as temporary:
        scratch = Path(temporary)
        smoke_scripts(checks, scratch)
        exercise_gates(checks, scratch)
    result = result_payload(checks)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
