#!/usr/bin/env python3
"""Validate Project Delivery Suite state and cross-file anti-drift gates.

This validator is intentionally local and read-only.  It checks deterministic
facts that must not be bypassed by conversational approval: path identity,
state ordering, evidence presence, and version alignment across the active
PRD, UI contract, AGENTS.md, README.md, and SESSION_REGISTRY.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


GATES = ("status", "handoff", "version-approval", "archive")
EMPTY_VALUES = {
    "",
    "none",
    "null",
    "n/a",
    "na",
    "pending",
    "待定",
    "无",
    "(无)",
    "(未创建)",
    "(未固定)",
    "<path>",
}
ADVANCED_VERSION_STATES = {
    "validation_passed",
    "accepted",
    "version_approved-current",
    "predecessors_archived",
    "released-live_verified",
}
VERSION_RE = re.compile(r"(?i)\b(v\d+(?:\.\d+){0,3})\b")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
ABSOLUTE_PATH_RE = re.compile(r"(?<![\w.-])(/[A-Za-z0-9_./+\-\u4e00-\u9fff]+)")
REQUIREMENT_RE = re.compile(r"(?m)^\|\s*((?:REQ|FR|NFR)-[A-Za-z0-9_.-]+)\s*\|")


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    message: str
    path: str | None = None


class Audit:
    def __init__(self, root: Path, gate: str) -> None:
        self.root = root
        self.gate = gate
        self.findings: list[Finding] = []

    def add(self, check_id: str, severity: str, message: str, path: Path | None = None) -> None:
        self.findings.append(
            Finding(check_id, severity, message, str(path) if path is not None else None)
        )

    def error(self, check_id: str, message: str, path: Path | None = None) -> None:
        self.add(check_id, "error", message, path)

    def warning(self, check_id: str, message: str, path: Path | None = None) -> None:
        self.add(check_id, "warning", message, path)


def strip_scalar(value: str) -> str:
    value = value.strip().strip("\"'").strip()
    if "#" in value and not value.startswith("/"):
        value = value.split("#", 1)[0].rstrip()
    return value


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    values: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if not raw_line or raw_line[0].isspace() or raw_line.lstrip().startswith("#"):
            continue
        key, separator, value = raw_line.partition(":")
        if separator and re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", key.strip()):
            values[key.strip()] = strip_scalar(value)
    return values


LEGACY_PATTERNS: dict[str, tuple[str, ...]] = {
    "workspace_root": (r"工作区根\s*`workspace_root`\s*[：:]\s*(.+)",),
    "active_version_root": (r"活动版本根\s*`active_version_root`\s*[：:]\s*(.+)",),
    "archive_root": (r"历史归档根\s*`archive_root`\s*[：:]\s*(.+)",),
    "repo_root": (r"Git 根\s*`repo_root`\s*[：:]\s*(.+)",),
    "staging_root": (r"候选暂存根\s*`staging_root`\s*[：:]\s*(.+)",),
    "topology": (r"目录拓扑[：:]\s*(.+)",),
    "latest_observed": (r"最新观察版本\s*`latest_observed`\s*[：:]\s*(.+)",),
    "current_approved": (r"当前批准版本\s*`current_approved`\s*[：:]\s*(.+)",),
    "active_candidate": (r"活动候选\s*`active_candidate`\s*[：:]\s*(.+)",),
    "source_lineage": (r"源谱系\s*`source_lineage`\s*[：:]\s*(.+)",),
    "governance_cycle_id": (r"治理周期\s*`governance_cycle_id`\s*[：:]\s*(.+)",),
    "prd_status": (r"PRD 状态[：:]\s*(.+)",),
    "ui_contract_status": (r"UI (?:合同|交付合同)状态[：:]\s*(.+)",),
    "validation_status": (r"验证状态[：:]\s*(.+)",),
    "acceptance_status": (r"独立验收[：:]\s*(.+)",),
    "version_approval_status": (r"版本批准[：:]\s*(.+)",),
    "archive_status": (r"归档状态[：:]\s*(.+)",),
    "version_status": (r"版本状态[：:]\s*(.+)",),
    "phase": (r"当前阶段[：:]\s*(.+)",),
    "fixed_point": (r"(?:固定基线 commit/tag|候选 commit|固定点)[：:]\s*(.+)",),
}


def parse_legacy_state(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, patterns in LEGACY_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                values[key] = strip_scalar(match.group(1))
                break
    return values


def state_token(value: str | None, allowed: Iterable[str]) -> str:
    lower = (value or "").lower()
    for token in allowed:
        if re.search(rf"(?<![a-z_-]){re.escape(token.lower())}(?![a-z_-])", lower):
            return token
    return ""


def meaningful(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in EMPTY_VALUES:
        return False
    return not any(marker in normalized for marker in ("<", ">", "待填写", "未创建", "未固定"))


def first_version(value: str | None) -> str:
    match = VERSION_RE.search(value or "")
    return match.group(1) if match else ""


def same_version(left: str, right: str) -> bool:
    return bool(left and right and left.casefold() == right.casefold())


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not meaningful(value):
        return None
    raw = Path((value or "").strip())
    return raw if raw.is_absolute() else root / raw


def find_single(root: Path | None, predicate) -> Path | None:
    if root is None or not root.is_dir():
        return None
    matches = sorted(path for path in root.rglob("*.md") if predicate(path))
    return matches[0] if len(matches) == 1 else None


def declared_or_discovered(
    project_root: Path,
    active_root: Path | None,
    state: dict[str, str],
    key: str,
    predicate,
) -> Path | None:
    declared = resolve_path(project_root, state.get(key))
    if declared is not None:
        return declared
    return find_single(active_root, predicate)


def text_or_error(audit: Audit, path: Path | None, check_id: str, label: str) -> str:
    if path is None:
        audit.error(check_id, f"{label} path is not declared and cannot be uniquely discovered")
        return ""
    if not path.is_file():
        audit.error(check_id, f"{label} file does not exist: {path}", path)
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        audit.error(check_id, f"{label} is not UTF-8", path)
        return ""


def check_declared_path(
    audit: Audit,
    state: dict[str, str],
    key: str,
    label: str,
    *,
    required: bool,
    must_be_dir: bool = False,
) -> Path | None:
    path = resolve_path(audit.root, state.get(key))
    if path is None:
        if required:
            audit.error(f"PATH-{key.upper()}", f"{label} is missing")
        return None
    if not path.exists():
        audit.error(f"PATH-{key.upper()}", f"{label} does not exist: {path}", path)
        return path
    if must_be_dir and not path.is_dir():
        audit.error(f"PATH-{key.upper()}", f"{label} is not a directory: {path}", path)
    return path


def extract_label_value(text: str, label_pattern: str) -> str:
    match = re.search(label_pattern + r"[^\n：:]*[：:]\s*([^\n]+)", text, re.IGNORECASE)
    return strip_scalar(match.group(1)) if match else ""


def check_cross_file_state(
    audit: Audit,
    state: dict[str, str],
    active_version: str,
    prd_path: Path | None,
    prd_text: str,
    ui_path: Path | None,
    ui_text: str,
) -> None:
    prd_meta = parse_frontmatter(prd_text)
    prd_version = first_version(prd_meta.get("version"))
    if active_version and not same_version(active_version, prd_version):
        audit.error(
            "DRIFT-PRD-VERSION",
            f"active version {active_version} does not match PRD version {prd_version or '(missing)'}",
            prd_path,
        )

    state_prd = state_token(state.get("prd_status"), ("draft", "approved"))
    file_prd = state_token(prd_meta.get("status"), ("draft", "approved"))
    if state_prd and file_prd and state_prd != file_prd:
        audit.error(
            "DRIFT-PRD-STATUS",
            f"PROJECT_STATE prd_status={state_prd} but PRD status={file_prd}",
            prd_path,
        )

    ui_head = "\n".join(ui_text.splitlines()[:20])
    if active_version and active_version.casefold() not in ui_head.casefold():
        audit.error(
            "DRIFT-UI-VERSION",
            f"UI contract header does not identify active version {active_version}",
            ui_path,
        )
    if prd_path is not None and ui_text:
        relative_prd = ""
        try:
            relative_prd = prd_path.relative_to(audit.root).as_posix()
        except ValueError:
            pass
        product_contract = extract_label_value(ui_head, r"产品合同")
        if product_contract and relative_prd and relative_prd not in product_contract:
            audit.error(
                "DRIFT-UI-PRD",
                f"UI contract points to {product_contract}, expected {relative_prd}",
                ui_path,
            )

    ui_status = state_token(
        extract_label_value(ui_head, r"状态"), ("draft", "confirmed", "frozen")
    )
    state_ui = state_token(
        state.get("ui_contract_status"), ("draft", "confirmed", "frozen")
    )
    if state_ui and ui_status and state_ui != ui_status:
        audit.error(
            "DRIFT-UI-STATUS",
            f"PROJECT_STATE ui_contract_status={state_ui} but UI contract status={ui_status}",
            ui_path,
        )

    if audit.gate in {"handoff", "version-approval", "archive"}:
        requirement_ids = set(REQUIREMENT_RE.findall(prd_text))
        missing = sorted(req for req in requirement_ids if req not in ui_text)
        if missing:
            audit.error(
                "DRIFT-UI-TRACE",
                "UI contract lacks requirement trace entries: " + ", ".join(missing),
                ui_path,
            )

    agents_path = audit.root / "AGENTS.md"
    if agents_path.is_file():
        agents_text = agents_path.read_text(encoding="utf-8")
        agents_version = first_version(extract_label_value(agents_text, r"当前版本"))
        if active_version and agents_version and not same_version(active_version, agents_version):
            audit.error(
                "DRIFT-AGENTS-VERSION",
                f"AGENTS current version {agents_version} does not match {active_version}",
                agents_path,
            )
        agents_root = extract_label_value(agents_text, r"项目根(?:目录)?")
        if agents_root and Path(agents_root).is_absolute():
            if Path(agents_root).resolve() != audit.root.resolve():
                audit.error(
                    "DRIFT-AGENTS-PATH",
                    f"AGENTS project root is stale: {agents_root}",
                    agents_path,
                )
    else:
        audit.warning("DRIFT-AGENTS-MISSING", "AGENTS.md is absent; AI entrypoint anti-drift is limited")

    readme_path = audit.root / "README.md"
    if readme_path.is_file() and active_version:
        readme_text = readme_path.read_text(encoding="utf-8")
        section = re.search(r"(?is)#+\s*当前版本\s*(.*?)(?:\n#+\s|\Z)", readme_text)
        if section:
            readme_version = first_version(section.group(1))
            if readme_version and not same_version(active_version, readme_version):
                audit.error(
                    "DRIFT-README-VERSION",
                    f"README current version {readme_version} does not match {active_version}",
                    readme_path,
                )

    session_path = resolve_path(audit.root, state.get("session_registry_path"))
    if session_path is None:
        candidate = audit.root / "SESSION_REGISTRY.md"
        session_path = candidate if candidate.is_file() else None
    if session_path is not None and session_path.is_file():
        session_text = session_path.read_text(encoding="utf-8")
        for match in ABSOLUTE_PATH_RE.finditer(session_text):
            raw_path = match.group(1).rstrip(".,;:，。；：)`]")
            if raw_path.startswith("/Users/") and not Path(raw_path).exists():
                audit.error(
                    "DRIFT-SESSION-PATH",
                    f"SESSION_REGISTRY contains a stale absolute path: {raw_path}",
                    session_path,
                )


def check_state_order(
    audit: Audit,
    state: dict[str, str],
    prd_text: str,
    ui_text: str,
) -> None:
    prd_status = state_token(state.get("prd_status"), ("draft", "approved"))
    validation = state_token(state.get("validation_status"), ("pending", "failed", "passed"))
    acceptance = state_token(state.get("acceptance_status"), ("pending", "rejected", "accepted"))
    approval = state_token(state.get("version_approval_status"), ("pending", "approved"))
    archive = state_token(state.get("archive_status"), ("not-applicable", "pending", "organized"))
    version_status = state_token(state.get("version_status"), ADVANCED_VERSION_STATES)
    ui_head = "\n".join(ui_text.splitlines()[:20])
    ui_status = state_token(
        state.get("ui_contract_status") or extract_label_value(ui_head, r"状态"),
        ("draft", "confirmed", "frozen"),
    )

    claims_approved = approval == "approved" or version_status in {
        "version_approved-current",
        "predecessors_archived",
        "released-live_verified",
    }
    if claims_approved:
        if prd_status != "approved":
            audit.error("STATE-APPROVAL-PRD", "version approval requires prd_status=approved")
        if ui_status not in {"confirmed", "frozen"}:
            audit.error(
                "STATE-APPROVAL-UI", "version approval requires a confirmed or frozen UI contract"
            )
        if validation != "passed":
            audit.error(
                "STATE-APPROVAL-VALIDATION", "version approval requires validation_status=passed"
            )
        if acceptance != "accepted":
            audit.error(
                "STATE-APPROVAL-ACCEPTANCE", "version approval requires acceptance_status=accepted"
            )

    if archive == "organized" and approval != "approved":
        audit.error(
            "STATE-ARCHIVE-ORDER", "archive_status=organized requires version_approval_status=approved"
        )

    if audit.gate in {"handoff", "version-approval", "archive"}:
        if prd_status != "approved":
            audit.error("GATE-PRD", f"{audit.gate} gate requires an approved PRD")
        if ui_status not in {"confirmed", "frozen"}:
            audit.error(
                "GATE-UI", f"{audit.gate} gate requires a confirmed or frozen UI contract"
            )
        if re.search(r"(?im)^\|[^\n]*\|\s*unresolved(?:\s*[^|]*)?\|\s*$", prd_text):
            audit.error(
                "GATE-CONFLICT", f"{audit.gate} gate is blocked by unresolved PRD conflicts"
            )

    if audit.gate in {"version-approval", "archive"}:
        if validation != "passed":
            audit.error("GATE-VALIDATION", f"{audit.gate} gate requires validation_status=passed")
        if acceptance != "accepted":
            audit.error("GATE-ACCEPTANCE", f"{audit.gate} gate requires acceptance_status=accepted")
        fixed_point = state.get("fixed_point") or state.get("candidate_commit")
        if not meaningful(fixed_point):
            audit.error("GATE-FIXED-POINT", f"{audit.gate} gate requires a fixed candidate point")

    if audit.gate == "archive":
        if approval != "approved":
            audit.error("GATE-APPROVAL", "archive gate requires version_approval_status=approved")


def check_evidence(audit: Audit, state: dict[str, str]) -> None:
    if audit.gate not in {"version-approval", "archive"}:
        return
    required = {
        "development_handoff_path": "development handoff",
        "evidence_manifest_path": "evidence manifest",
        "acceptance_report_path": "acceptance report",
        "candidate_manifest_path": "candidate manifest",
    }
    for key, label in required.items():
        path = resolve_path(audit.root, state.get(key))
        if path is None or not path.is_file():
            audit.error(
                f"EVIDENCE-{key.upper()}",
                f"{audit.gate} gate requires an existing {label} file",
                path,
            )


def audit_project(root: Path, gate: str) -> dict[str, object]:
    root = root.resolve()
    audit = Audit(root, gate)
    if not root.is_dir():
        audit.error("ROOT-MISSING", f"project root is not a directory: {root}", root)
        return result_payload(audit)
    if root.is_symlink():
        audit.error("ROOT-SYMLINK", "project root must not be a symlink", root)

    state_path = root / "PROJECT_STATE.md"
    if not state_path.is_file():
        audit.error("STATE-MISSING", "PROJECT_STATE.md is required", state_path)
        return result_payload(audit)
    state_text = state_path.read_text(encoding="utf-8")
    state = parse_frontmatter(state_text)
    if "state_schema" not in state:
        legacy = parse_legacy_state(state_text)
        state = {**legacy, **state}
        audit.warning(
            "STATE-LEGACY",
            "PROJECT_STATE.md lacks structured state_schema frontmatter; legacy parsing is limited",
            state_path,
        )
        if gate != "status":
            audit.error(
                "STATE-SCHEMA-GATE",
                f"{gate} gate requires structured PROJECT_STATE state_schema=1.0",
                state_path,
            )
    elif state.get("state_schema") != "1.0":
        audit.error(
            "STATE-SCHEMA-VERSION",
            f"unsupported PROJECT_STATE state_schema={state.get('state_schema')!r}",
            state_path,
        )

    workspace_root = check_declared_path(
        audit, state, "workspace_root", "workspace_root", required=True, must_be_dir=True
    )
    if workspace_root is not None and workspace_root.exists():
        if workspace_root.resolve() != root:
            audit.error(
                "DRIFT-WORKSPACE-PATH",
                f"PROJECT_STATE workspace_root resolves to {workspace_root}, actual root is {root}",
                state_path,
            )

    active_root = check_declared_path(
        audit, state, "active_version_root", "active_version_root", required=True, must_be_dir=True
    )
    archive_root = check_declared_path(
        audit,
        state,
        "archive_root",
        "archive_root",
        required=gate == "archive",
        must_be_dir=True,
    )
    if active_root is not None and active_root.exists():
        if not is_within(active_root, root):
            audit.error("PATH-ACTIVE-SCOPE", "active_version_root is outside workspace_root", active_root)
        if archive_root is not None and archive_root.exists() and is_within(active_root, archive_root):
            audit.error("PATH-ACTIVE-ARCHIVED", "active_version_root is inside archive_root", active_root)

    active_version = first_version(active_root.name if active_root is not None else "")
    if not active_version:
        active_version = first_version(state.get("active_candidate")) or first_version(
            state.get("current_approved")
        )
    if not active_version:
        audit.error("STATE-ACTIVE-VERSION", "cannot determine the active version identity", state_path)

    prd_path = declared_or_discovered(
        root,
        active_root,
        state,
        "prd_path",
        lambda path: path.name.casefold() == "prd.md" or "prd" in path.stem.casefold(),
    )
    ui_path = declared_or_discovered(
        root,
        active_root,
        state,
        "ui_contract_path",
        lambda path: "ui" in path.stem.casefold() and "contract" in path.stem.casefold(),
    )
    prd_text = text_or_error(audit, prd_path, "PRD-MISSING", "active PRD")
    ui_text = text_or_error(audit, ui_path, "UI-MISSING", "active UI contract")

    check_cross_file_state(audit, state, active_version, prd_path, prd_text, ui_path, ui_text)
    check_state_order(audit, state, prd_text, ui_text)
    check_evidence(audit, state)

    current = first_version(state.get("current_approved"))
    approval = state_token(state.get("version_approval_status"), ("pending", "approved"))
    if current and same_version(current, active_version) and approval != "approved":
        audit.error(
            "STATE-CURRENT-APPROVAL",
            "current_approved identifies the active version but version_approval_status is not approved",
            state_path,
        )
    if gate == "archive" and not same_version(current, active_version):
        audit.error(
            "GATE-CURRENT",
            "archive gate requires current_approved to equal the active version",
            state_path,
        )

    return result_payload(audit)


def result_payload(audit: Audit) -> dict[str, object]:
    errors = sum(1 for finding in audit.findings if finding.severity == "error")
    warnings = sum(1 for finding in audit.findings if finding.severity == "warning")
    return {
        "schema": "ai-project-delivery-state-audit/1.0",
        "status": "fail" if errors else "pass",
        "gate": audit.gate,
        "root": str(audit.root),
        "summary": {"errors": errors, "warnings": warnings},
        "findings": [asdict(finding) for finding in audit.findings],
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    assert isinstance(summary, dict)
    lines = [
        f"# Project-state gate: `{result['gate']}`",
        "",
        f"Status: `{result['status']}`  ",
        f"Root: `{result['root']}`  ",
        f"Errors: {summary['errors']}  ",
        f"Warnings: {summary['warnings']}",
        "",
        "| Severity | Check | Message | Path |",
        "|---|---|---|---|",
    ]
    findings = result["findings"]
    assert isinstance(findings, list)
    if not findings:
        lines.append("| — | — | No drift or illegal state transition detected | — |")
    for finding in findings:
        assert isinstance(finding, dict)
        values = [
            str(finding.get("severity", "")),
            str(finding.get("id", "")),
            str(finding.get("message", "")),
            str(finding.get("path") or "—"),
        ]
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only state-order and cross-file anti-drift validator."
    )
    parser.add_argument("root", type=Path, help="Existing project root containing PROJECT_STATE.md")
    parser.add_argument("--gate", choices=GATES, default="status")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = audit_project(args.root, args.gate)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
