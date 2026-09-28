#!/usr/bin/env python3
"""Validate structured cross-version constraint coverage without extracting semantics."""

from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
from pathlib import Path
from typing import Any


DISPOSITIONS = {"preserved", "relocated", "explicitly_superseded", "unresolved"}
FIDELITIES = {"exact", "equivalent", "generalized", "unknown"}
IMPACTS = {"low", "medium", "high"}
CHANGE_POLICIES = {"frozen", "allowed", "prohibited", "open"}
BOUNDARY_FIELDS = (
    "frozen_constraints",
    "allowed_changes",
    "prohibited_changes",
    "open_decisions",
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _issue(code: str, constraint_id: str | None = None, detail: str | None = None) -> dict[str, str]:
    item = {"code": code}
    if constraint_id:
        item["constraint_id"] = constraint_id
    if detail:
        item["detail"] = detail
    return item


def validate(payload: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    constraints = payload.get("constraints")
    if not isinstance(constraints, list) or not constraints:
        errors.append(_issue("constraints_missing"))
        constraints = []

    boundary = payload.get("boundary_snapshot")
    if not isinstance(boundary, dict):
        errors.append(_issue("boundary_snapshot_missing"))
        boundary = {}
    boundary_sets: dict[str, set[str]] = {}
    for field in BOUNDARY_FIELDS:
        value = boundary.get(field)
        if not isinstance(value, list):
            errors.append(_issue("boundary_field_missing", detail=field))
            value = []
        if any(not _nonempty(item) for item in value):
            errors.append(_issue("boundary_id_invalid", detail=field))
        boundary_sets[field] = {item for item in value if _nonempty(item)}

    source_authority = boundary.get("source_authority")
    if not isinstance(source_authority, dict):
        errors.append(_issue("source_authority_missing"))
        source_authority = {}

    seen: set[str] = set()
    for raw in constraints:
        if not isinstance(raw, dict):
            errors.append(_issue("constraint_not_object"))
            continue
        constraint_id = raw.get("id") if _nonempty(raw.get("id")) else None
        if not constraint_id:
            errors.append(_issue("constraint_id_missing"))
            continue
        if constraint_id in seen:
            errors.append(_issue("constraint_id_duplicate", constraint_id))
            continue
        seen.add(constraint_id)

        for field in ("original_text", "category", "scope"):
            if not _nonempty(raw.get(field)):
                errors.append(_issue("constraint_field_missing", constraint_id, field))
        source = raw.get("source")
        if not isinstance(source, dict):
            errors.append(_issue("source_missing", constraint_id))
            source = {}
        for field in ("file", "version", "authority"):
            if not _nonempty(source.get(field)):
                errors.append(_issue("source_field_missing", constraint_id, field))
        if source_authority.get(constraint_id) != source.get("authority"):
            errors.append(_issue("source_authority_not_carried", constraint_id))

        impact = raw.get("impact")
        if not isinstance(impact, str) or impact not in IMPACTS:
            errors.append(_issue("impact_invalid", constraint_id))
        policy = raw.get("change_policy")
        if not isinstance(policy, str) or policy not in CHANGE_POLICIES:
            errors.append(_issue("change_policy_invalid", constraint_id))

        disposition = raw.get("disposition")
        if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
            errors.append(_issue("disposition_invalid", constraint_id))
            continue
        if disposition in {"preserved", "relocated"}:
            target = raw.get("target")
            if not isinstance(target, dict):
                errors.append(_issue("target_missing", constraint_id))
                target = {}
            for field in ("file", "excerpt"):
                if not _nonempty(target.get(field)):
                    errors.append(_issue("target_evidence_missing", constraint_id, field))
            fidelity = target.get("fidelity")
            if not isinstance(fidelity, str) or fidelity not in FIDELITIES:
                errors.append(_issue("fidelity_invalid", constraint_id))
            elif fidelity == "generalized":
                errors.append(_issue("semantic_generalization_detected", constraint_id))
            elif fidelity == "unknown":
                warnings.append(_issue("semantic_fidelity_unverified", constraint_id))
        elif disposition == "explicitly_superseded":
            decision = raw.get("supersession")
            if not isinstance(decision, dict):
                errors.append(_issue("supersession_evidence_missing", constraint_id))
                decision = {}
            for field in ("owner", "scope", "date", "evidence", "replacement"):
                if not _nonempty(decision.get(field)):
                    errors.append(_issue("supersession_field_missing", constraint_id, field))
        else:
            issue = _issue("constraint_unresolved", constraint_id)
            (errors if impact == "high" else warnings).append(issue)

        if disposition != "explicitly_superseded":
            expected_field = {
                "frozen": "frozen_constraints",
                "allowed": "allowed_changes",
                "prohibited": "prohibited_changes",
                "open": "open_decisions",
            }.get(policy) if isinstance(policy, str) else None
            if expected_field and constraint_id not in boundary_sets[expected_field]:
                errors.append(_issue("boundary_policy_not_carried", constraint_id, expected_field))

    covered_ids = set(source_authority)
    unknown_authority_ids = covered_ids - seen
    for constraint_id in sorted(unknown_authority_ids):
        warnings.append(_issue("source_authority_without_constraint", constraint_id))

    for field, ids in boundary_sets.items():
        for constraint_id in ids - seen:
            errors.append(_issue("boundary_unknown_id", constraint_id, field))
        for other, other_ids in boundary_sets.items():
            if field < other:
                for constraint_id in ids & other_ids:
                    errors.append(_issue("boundary_policy_conflict", constraint_id, f"{field}/{other}"))

    structure_status = "invalid" if errors else "limited" if warnings else "valid"
    reference_errors: list[dict[str, str]] = []
    if root is not None:
        verify_references(payload, root, reference_errors)
    reference_status = "not_checked" if root is None else "failed" if reference_errors else "verified"
    # These are mechanical checks. Neither authored labels nor booleans establish
    # semantic equivalence, inventory completeness, approval, or archive authority.
    return {
        "schema_version": 2,
        "structure_validation_status": structure_status,
        "reference_validation_status": reference_status,
        "semantic_review_status": "required",
        "semantic_archive_preconditions": "pending_review" if structure_status == "valid" and reference_status == "verified" else "not_met",
        "constraint_count": len(seen),
        "errors": errors + reference_errors,
        "warnings": warnings,
    }


def pinned_file(root: Path, record: Any) -> str:
    """Verify a pinned UTF-8 source inside root. This does not authenticate its author."""
    if not isinstance(record, dict) or not _nonempty(record.get("file")):
        raise ValueError("file reference missing")
    relative = Path(record["file"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("file reference must be relative to root")
    base = root.resolve(strict=True)
    path = base
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ValueError("symlink reference rejected")
    path.resolve(strict=True).relative_to(base)
    digest = record.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("sha256 pin missing or invalid")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("sha256 pin mismatch")
    return data.decode("utf-8")


def verify_references(payload: dict[str, Any], root: Path, errors: list[dict[str, str]]) -> None:
    """Check references against a separately reviewed, pinned constraint inventory."""
    def read(record: Any, label: str, excerpt: Any = None) -> str | None:
        try:
            text = pinned_file(root, record)
            if excerpt is not None and (not _nonempty(excerpt) or excerpt not in text):
                raise ValueError("excerpt not found")
            return text
        except (OSError, ValueError, UnicodeError) as error:
            errors.append(_issue("reference_invalid", detail=f"{label}: {error}"))
            return None

    items = payload.get("constraints", [])
    if not isinstance(items, list):
        items = []
    inventory_text = read(payload.get("inventory"), "inventory")
    if inventory_text is not None:
        try:
            inventory = json.loads(inventory_text)
            ids = inventory["constraint_ids"]
            sources = inventory["sources"]
            if not isinstance(ids, list) or not ids or any(not _nonempty(i) for i in ids) or len(set(ids)) != len(ids):
                raise ValueError("inventory must contain unique constraint IDs")
            if not isinstance(sources, list) or not sources:
                raise ValueError("inventory sources missing")
            actual = {item.get("id") for item in items if isinstance(item, dict) and _nonempty(item.get("id"))}
            if set(ids) != actual:
                raise ValueError("constraint IDs do not match the pinned inventory")
            pinned_sources = set()
            for source in sources:
                read(source, "inventory source")
                if isinstance(source, dict) and _nonempty(source.get("file")) and _nonempty(source.get("sha256")):
                    pinned_sources.add((source["file"], source["sha256"]))
            for item in items:
                source = item.get("source", {}) if isinstance(item, dict) else {}
                if not isinstance(source, dict) or not isinstance(source.get("file"), str) or not isinstance(source.get("sha256"), str) or (source["file"], source["sha256"]) not in pinned_sources:
                    raise ValueError("constraint source is absent from pinned inventory")
        except (KeyError, TypeError, ValueError) as error:
            errors.append(_issue("inventory_invalid", detail=str(error)))
    for item in items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("id", "unknown"))
        read(item.get("source"), label + " source", item.get("original_text", ""))
        if item.get("disposition") in {"preserved", "relocated"}:
            target = item.get("target")
            read(target, label + " target", target.get("excerpt", "") if isinstance(target, dict) else "")
        elif item.get("disposition") == "explicitly_superseded":
            decision = item.get("supersession")
            read(decision.get("evidence_ref") if isinstance(decision, dict) else None, label + " decision")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Structured semantic coverage JSON")
    parser.add_argument("--root", type=Path, help="Verify pinned inventory and source/target files inside this root")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"schema_version": 2, "structure_validation_status": "invalid", "errors": [{"code": "input_error", "detail": str(error)}]}))
        return 1
    if not isinstance(payload, dict):
        print(json.dumps({"schema_version": 2, "structure_validation_status": "invalid", "errors": [{"code": "input_not_object"}]}))
        return 1
    result = validate(payload, args.root)
    if args.format == "markdown":
        print(f"# Constraint evidence checks\n\nStructure: `{result['structure_validation_status']}`")
        print(f"References: `{result['reference_validation_status']}`")
        print("Semantic review: `required`; this report does not authorize archival.")
        for label in ("errors", "warnings"):
            if result[label]:
                print(f"\n## {label.title()}")
                for item in result[label]:
                    print(f"- `{item['code']}` — {item.get('constraint_id') or item.get('detail') or ''}")
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["structure_validation_status"] == "valid" and result["reference_validation_status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
