#!/usr/bin/env python3
"""Validate the WorkBuddy-compatible Project Delivery Suite package."""

from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path


DELIVERY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = DELIVERY_ROOT / "package" / "project-delivery-suite"
ZIP_PATH = DELIVERY_ROOT / "dist" / "project-delivery-suite.zip"
EXPECTED_SCRIPT_HASHES = {
    "audit_versions.py": "ee5fd92e02d10b4e0558dc7001d31e2618e16b4c07969a3704a91498157af061",
    "project_snapshot.py": "70472262146292078a706108c2a776481d7dac594f421baee9ac2161b033a5e0",
    "scaffold_delivery.py": "529afbbda544d036b30208f9ed0940fd5296ed617c91734f924e31566785a0e5",
    "self_check.py": "d2a71bb544c23edc448650ff374e549f1aa71fccac3d39e8516823f4a23a9951",
    "validate_project_state.py": "20815175f448a8bbe74854acd241f1662f9d56efb8a3135c6e7448d98ed8ef4a",
}
FORBIDDEN_PARTS = {
    ".git",
    ".DS_Store",
    "__MACOSX",
    "__pycache__",
    "node_modules",
    "agents",
    "evals",
}
FORBIDDEN_FILES = {
    ".env",
    "plugin.json",
    "marketplace.json",
    "openai.yaml",
    "_user_meta.json",
    "_skillhub_meta.json",
    "_knot_meta.json",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~+/-]{16,}"),
)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)


def fail(message: str) -> None:
    raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}\s*:\s*(.+?)\s*$", frontmatter)
    return match.group(1).strip().strip("\"'") if match else ""


def validate_tree() -> list[Path]:
    if not SKILL_ROOT.is_dir():
        fail(f"skill root missing: {SKILL_ROOT}")
    if SKILL_ROOT.name != "project-delivery-suite":
        fail("skill directory name changed")
    if SKILL_ROOT.is_symlink():
        fail("skill root must not be a symlink")

    files = sorted(path for path in SKILL_ROOT.rglob("*") if path.is_file())
    if not files:
        fail("skill package is empty")
    for path in SKILL_ROOT.rglob("*"):
        rel = path.relative_to(SKILL_ROOT)
        if path.is_symlink():
            fail(f"symlink forbidden: {rel}")
        if FORBIDDEN_PARTS.intersection(rel.parts):
            fail(f"forbidden path component: {rel}")
        if path.name in FORBIDDEN_FILES or path.suffix == ".pyc":
            fail(f"forbidden file: {rel}")
    return files


def validate_frontmatter() -> None:
    skill_md = SKILL_ROOT / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        fail("SKILL.md has invalid frontmatter delimiters")
    frontmatter = match.group(1)
    name = parse_scalar(frontmatter, "name")
    slug = parse_scalar(frontmatter, "slug")
    display_name = parse_scalar(frontmatter, "displayName")
    description = parse_scalar(frontmatter, "description")
    if name != SKILL_ROOT.name:
        fail("frontmatter name must match directory")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        fail("skill name must use hyphen-case")
    if slug != name:
        fail("SkillHub slug must match the WorkBuddy skill name")
    if display_name != "Project Delivery Suite":
        fail("SkillHub displayName changed unexpectedly")
    if len(name) > 40:
        fail("skill name exceeds WorkBuddy initializer's 40-character rule")
    if not description or "TODO" in description or "<" in description or ">" in description:
        fail("description is missing, placeholder text, or contains angle brackets")
    if parse_scalar(frontmatter, "agent_created") != "true":
        fail("agent_created: true is required by WorkBuddy skill_manage")
    if parse_scalar(frontmatter, "version") != "0.6.0":
        fail("package version must match the canonical 0.6.0 release")
    if parse_scalar(frontmatter, "license") != "MIT":
        fail("license must remain MIT")


def validate_text_and_links(files: list[Path]) -> None:
    for path in files:
        data = path.read_bytes()
        if b"\x00" in data:
            fail(f"binary/NUL content is not expected: {path.relative_to(SKILL_ROOT)}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            fail(f"non-UTF-8 file: {path.relative_to(SKILL_ROOT)}: {error}")
        if "/Users/yusiyuan" in text or "file://" in text:
            fail(f"host-specific absolute path found: {path.relative_to(SKILL_ROOT)}")
        if re.search(r"(?i)\bcodex\b", text):
            fail(f"upstream Codex-specific wording remains: {path.relative_to(SKILL_ROOT)}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                fail(f"possible secret found: {path.relative_to(SKILL_ROOT)}")
        if path.suffix.lower() != ".md":
            continue
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0]
            if not target or re.match(r"^(?:https?|mailto):", target):
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(SKILL_ROOT.resolve())
            except ValueError:
                fail(f"Markdown link escapes package: {path.name} -> {raw_target}")
            if not resolved.exists():
                fail(f"broken Markdown link: {path.name} -> {raw_target}")


def validate_scripts() -> None:
    for name, expected in EXPECTED_SCRIPT_HASHES.items():
        path = SKILL_ROOT / "scripts" / name
        if not path.is_file():
            fail(f"missing script: {name}")
        actual = sha256(path)
        if actual != expected:
            fail(f"expected script hash changed: {name}: {actual}")


def validate_release_contract() -> None:
    required = {
        "assets/AGENTS.md",
        "assets/MINIMUM_PRD.md",
        "assets/PROJECT_STATE.md",
        "assets/UI_IMPLEMENTATION_AND_RUNTIME_ACCEPTANCE_CONTRACT.md",
        "scripts/self_check.py",
        "scripts/validate_project_state.py",
    }
    missing = sorted(rel for rel in required if not (SKILL_ROOT / rel).is_file())
    if missing:
        fail(f"V0.2.6 contract files missing: {missing}")

    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    for required_term in (
        "WorkBuddy 5.3.11",
        "task creation unsupported",
        "SkillHub/公开发布",
        "--gate handoff",
        "--gate version-approval",
        "--gate archive",
        "scripts/self_check.py",
        "用户授权与事实门禁分开",
        "<待用户确认的项目根>",
        "不得写死发布者机器的安装路径",
        "## 它能解决什么问题",
        "## 主要功能",
        "## 特色",
        "## 直接这样开始",
        "## PRD 能力检测与最小回退",
        "不要求用户额外安装",
        "[MINIMUM_PRD.md](assets/MINIMUM_PRD.md)",
    ):
        if required_term not in skill_text:
            fail(f"SKILL.md does not enforce the WorkBuddy release contract: {required_term}")

    state_text = (SKILL_ROOT / "assets" / "PROJECT_STATE.md").read_text(encoding="utf-8")
    for key in (
        "state_schema:",
        "prd_status:",
        "ui_contract_status:",
        "validation_status:",
        "acceptance_status:",
        "version_approval_status:",
        "version_approval_intent:",
        "anti_drift_status:",
        "candidate_manifest_path:",
    ):
        if key not in state_text:
            fail(f"PROJECT_STATE template lacks structured key: {key}")

    minimum_prd = (SKILL_ROOT / "assets" / "MINIMUM_PRD.md").read_text(encoding="utf-8")
    for required_term in (
        "## 文档状态",
        "状态必须保持 `draft`",
        "## 3. 本版本范围",
        "### 明确不包含",
        "REQ-001",
        "## 7. 验收条件",
        "AC-001",
        "DEC-001",
        "## 9. 追溯与变更",
    ):
        if required_term not in minimum_prd:
            fail(f"MINIMUM_PRD.md lacks required contract term: {required_term}")


def validate_zip(files: list[Path]) -> None:
    if not ZIP_PATH.is_file():
        fail(f"zip package missing: {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = sorted(name for name in archive.namelist() if not name.endswith("/"))
        expected_names = sorted(
            f"{SKILL_ROOT.name}/{path.relative_to(SKILL_ROOT).as_posix()}" for path in files
        )
        if names != expected_names:
            missing = sorted(set(expected_names) - set(names))
            extra = sorted(set(names) - set(expected_names))
            fail(f"zip/source mismatch; missing={missing}, extra={extra}")
        if f"{SKILL_ROOT.name}/SKILL.md" not in names:
            fail("zip must have one top-level skill folder containing SKILL.md")
        if any(FORBIDDEN_PARTS.intersection(Path(name).parts) for name in names):
            fail("zip contains a forbidden path")


def main() -> int:
    files = validate_tree()
    validate_frontmatter()
    validate_text_and_links(files)
    validate_scripts()
    validate_release_contract()
    validate_zip(files)
    print(f"PASS: {len(files)} package files and {ZIP_PATH.name} validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
