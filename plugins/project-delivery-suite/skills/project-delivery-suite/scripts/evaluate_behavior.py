#!/usr/bin/env python3
"""Score source-linked behavior observations; never invoke a model or mutate fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

KINDS = {
    "read", "file_write", "file_delete", "file_move", "external_write", "run_check",
    "request_confirmation", "new_task", "new_candidate", "full_governance",
    "task_complete", "gate_blocked", "coverage_declared", "archive", "candidate_selected",
    "evidence_inherited", "visual_capture",
}
MUTATIONS = {"file_write", "file_delete", "file_move", "external_write", "archive", "new_candidate"}


def read_pinned(root: Path, ref: Any) -> str:
    if not isinstance(ref, dict) or not isinstance(ref.get("file"), str):
        raise ValueError("raw trace reference missing")
    relative = Path(ref["file"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("trace must be inside the run directory")
    path = root.resolve(strict=True)
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ValueError("trace symlinks are unsupported")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != ref.get("sha256"):
        raise ValueError("raw trace hash mismatch")
    return data.decode("utf-8")


def matches(event: dict, pattern: dict) -> bool:
    return all(event.get(key) == value for key, value in pattern.items())


def score(case: dict, run: dict, root: Path) -> dict:
    if run.get("case_id") != case["id"]:
        raise ValueError("case ID mismatch")
    if run.get("run_kind") not in {"actual_model", "synthetic_fixture"}:
        raise ValueError("run_kind must identify actual or synthetic execution")
    for field in ("model", "skill_commit", "observer", "run_id"):
        if not isinstance(run.get(field), str) or not run[field].strip():
            raise ValueError(f"missing provenance: {field}")
    if run["run_kind"] == "actual_model":
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", run["skill_commit"]):
            raise ValueError("actual runs require a full Skill commit SHA")
        configuration = run.get("configuration")
        if not isinstance(configuration, dict) or any(not isinstance(configuration.get(k), str) or not configuration[k].strip() for k in ("reasoning_effort", "tool_policy", "input_snapshot_sha256")):
            raise ValueError("actual run configuration is missing")
        if not re.fullmatch(r"[0-9a-f]{64}", configuration["input_snapshot_sha256"]):
            raise ValueError("input snapshot SHA-256 is invalid")
    for field in ("total_tokens", "duration_seconds"):
        value = run.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError(f"invalid metric: {field}")
    lines = read_pinned(root, run.get("raw_trace")).splitlines()
    events = run.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("observed events missing")
    for event in events:
        if not isinstance(event, dict) or event.get("kind") not in KINDS:
            raise ValueError("unknown observation kind")
        evidence = event.get("evidence")
        if not isinstance(evidence, dict):
            raise ValueError("observation evidence missing")
        line, excerpt = evidence.get("line"), evidence.get("excerpt")
        if type(line) is not int or not 1 <= line <= len(lines):
            raise ValueError("invalid evidence line")
        if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in lines[line - 1]:
            raise ValueError("observation excerpt does not match raw trace")
    failures = []
    for pattern in case.get("required", []):
        if not any(matches(e, pattern) for e in events):
            failures.append({"rule": "required", "pattern": pattern})
    for pattern in case.get("forbidden", []):
        if any(matches(e, pattern) for e in events):
            failures.append({"rule": "forbidden", "pattern": pattern})
    if case.get("read_only") and any(e["kind"] in MUTATIONS or e["kind"] == "new_task" for e in events):
        failures.append({"rule": "read_only"})
    if "allowed_write_paths" in case:
        for event in events:
            if event["kind"] == "file_write" and event.get("path") not in case["allowed_write_paths"]:
                failures.append({"rule": "write_scope", "path": event.get("path")})
    for limit in case.get("maximum", []):
        count = sum(matches(e, limit["pattern"]) for e in events)
        if count > limit["count"]:
            failures.append({"rule": "maximum", "pattern": limit["pattern"], "observed": count})
    actual = run["run_kind"] == "actual_model"
    return {
        "case_id": case["id"], "run_id": run["run_id"], "model": run["model"],
        "skill_commit": run["skill_commit"], "run_kind": run["run_kind"],
        "configuration": run.get("configuration"),
        "observation_status": "expectations_met" if not failures else "expectations_failed",
        "model_behavior_status": "observations_scored" if actual else "not_run",
        "failures": failures,
        "metrics": {
            "confirmation_count": sum(e["kind"] == "request_confirmation" for e in events),
            "document_write_count": len({e.get("path") for e in events if e["kind"] == "file_write" and isinstance(e.get("path"), str) and e["path"].endswith(".md")}),
            "task_complete_observed": any(e["kind"] == "task_complete" for e in events),
            "total_tokens": run.get("total_tokens"), "duration_seconds": run.get("duration_seconds"),
        },
        "limitation": "Source links checked; observation classification and log authenticity require an independent trusted collector.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args()
    results, errors = [], []
    try:
        cases = {c["id"]: c for c in json.loads(args.cases.read_text())["cases"]}
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"error": f"invalid cases: {error}"})); return 1
    seen_run_ids = set()
    for path in args.runs:
        try:
            run = json.loads(path.read_text())
            result = score(cases[run["case_id"]], run, path.parent)
            if result["run_id"] in seen_run_ids:
                raise ValueError("duplicate run ID")
            seen_run_ids.add(result["run_id"])
            results.append(result)
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append({"run": str(path), "error": str(error)})
    actual = [r for r in results if r["run_kind"] == "actual_model"]
    passed = sum(r["observation_status"] == "expectations_met" for r in actual)
    groups = {}
    for result in actual:
        settings = {k: v for k, v in result["configuration"].items() if k != "input_snapshot_sha256"}
        key = (result["model"], result["skill_commit"], json.dumps(settings, sort_keys=True))
        groups.setdefault(key, []).append(result)
    comparisons = []
    for (model, commit, configuration), samples in groups.items():
        comparisons.append({
            "model": model, "skill_commit": commit, "configuration": json.loads(configuration),
            "run_count": len(samples),
            "expectation_match_rate": sum(not s["failures"] for s in samples) / len(samples),
            "cases_without_actual_model_runs": sorted(set(cases) - {s["case_id"] for s in samples}),
        })
    report = {
        "schema_version": 1, "results": results, "errors": errors,
        "comparison_groups": comparisons,
        "actual_model_run_count": len(actual),
        "actual_model_expectation_match_rate": passed / len(actual) if actual else None,
        "cases_without_actual_model_runs": sorted(set(cases) - {r["case_id"] for r in actual}),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors or any(r["failures"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
