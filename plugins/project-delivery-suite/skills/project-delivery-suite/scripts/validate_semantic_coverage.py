#!/usr/bin/env python3
"""Validate structured cross-version constraint coverage without extracting semantics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DISPOSITIONS = {"preserved", "relocated", "explicitly_superseded", "unresolved"}
FIDELITIES = {"exact", "equivalent", "generalized", "unknown"}
IMPACTS = {"low", "medium", "high"}
CHANGE_POLICIES = {"frozen", "allowed", "prohibited", "open"}
ENTRYPOINT_FIELDS = (
    "single_active_entry",
    "historical_deauthorized",
    "readme_exposes_current_constraints",
    "agents_exposes_current_constraints",
    "project_brief_exposes_current_constraints",
    "downstream_boundary_snapshot_attached",
)
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


def validate(payload: dict[str, Any]) -> dict[str, Any]:
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
        boundary_sets[field] = {str(item) for item in value if _nonempty(str(item))}

    source_authority = boundary.get("source_authority")
    if not isinstance(source_authority, dict):
        errors.append(_issue("source_authority_missing"))
        source_authority = {}

    entrypoints = payload.get("entrypoints")
    if not isinstance(entrypoints, dict):
        entrypoints = {}

    seen: set[str] = set()
    unresolved = False
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
        if impact not in IMPACTS:
            errors.append(_issue("impact_invalid", constraint_id))
        policy = raw.get("change_policy")
        if policy not in CHANGE_POLICIES:
            errors.append(_issue("change_policy_invalid", constraint_id))

        disposition = raw.get("disposition")
        if disposition not in DISPOSITIONS:
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
            if fidelity not in FIDELITIES:
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
            unresolved = True
            issue = _issue("constraint_unresolved", constraint_id)
            (errors if impact == "high" else warnings).append(issue)

        if disposition != "explicitly_superseded":
            expected_field = {
                "frozen": "frozen_constraints",
                "allowed": "allowed_changes",
                "prohibited": "prohibited_changes",
                "open": "open_decisions",
            }.get(policy)
            if expected_field and constraint_id not in boundary_sets[expected_field]:
                errors.append(_issue("boundary_policy_not_carried", constraint_id, expected_field))

    covered_ids = set(source_authority)
    unknown_authority_ids = covered_ids - seen
    for constraint_id in sorted(unknown_authority_ids):
        warnings.append(_issue("source_authority_without_constraint", constraint_id))

    if errors:
        semantic_status = "semantic_coverage_failed"
    elif warnings:
        semantic_status = "semantic_coverage_limited"
    else:
        semantic_status = "semantic_coverage_passed"

    entrypoints_complete = all(entrypoints.get(field) is True for field in ENTRYPOINT_FIELDS)
    anti_drift = "anti-drift enforced" if semantic_status == "semantic_coverage_passed" and entrypoints_complete else "anti-drift limited"
    # Semantic coverage is the precondition for deauthorizing history.  It must
    # therefore be possible to pass this gate before history is deauthorized.
    # Entry-point convergence is evaluated separately as the anti-drift gate.
    archive_allowed = semantic_status == "semantic_coverage_passed" and not unresolved
    if entrypoints.get("historical_deauthorized") is True and semantic_status != "semantic_coverage_passed":
        errors.append(_issue("history_deauthorized_before_semantic_coverage"))
        semantic_status = "semantic_coverage_failed"
        anti_drift = "anti-drift limited"
        archive_allowed = False

    return {
        "schema_version": 1,
        "semantic_coverage_status": semantic_status,
        "anti_drift_status": anti_drift,
        "archive_allowed": archive_allowed,
        "constraint_count": len(seen),
        "errors": errors,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Structured semantic coverage JSON")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"semantic_coverage_status": "semantic_coverage_failed", "errors": [{"code": "input_error", "detail": str(error)}]}))
        return 1
    if not isinstance(payload, dict):
        print(json.dumps({"semantic_coverage_status": "semantic_coverage_failed", "errors": [{"code": "input_not_object"}]}))
        return 1
    result = validate(payload)
    if args.format == "markdown":
        print(f"# Semantic coverage\n\nStatus: `{result['semantic_coverage_status']}`  ")
        print(f"Anti-drift: `{result['anti_drift_status']}`  ")
        print(f"Archive allowed: `{str(result['archive_allowed']).lower()}`")
        for label in ("errors", "warnings"):
            if result[label]:
                print(f"\n## {label.title()}")
                for item in result[label]:
                    print(f"- `{item['code']}` — {item.get('constraint_id') or item.get('detail') or ''}")
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["semantic_coverage_status"] == "semantic_coverage_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
