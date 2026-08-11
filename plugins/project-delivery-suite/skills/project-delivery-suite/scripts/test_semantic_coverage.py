from __future__ import annotations

import copy
import unittest

from validate_semantic_coverage import validate


def constraint(
    constraint_id: str,
    text: str,
    *,
    category: str = "platform",
    policy: str = "frozen",
    disposition: str = "preserved",
    target_file: str = "03_工程/工程合同.md",
    fidelity: str = "exact",
) -> dict:
    item = {
        "id": constraint_id,
        "original_text": text,
        "source": {"file": "V3/已批准规格.md", "version": "V3", "authority": "DEC-APPROVED-03"},
        "category": category,
        "scope": "current and future versions until explicitly superseded",
        "impact": "high",
        "change_policy": policy,
        "disposition": disposition,
    }
    if disposition in {"preserved", "relocated"}:
        item["target"] = {"file": target_file, "excerpt": text, "fidelity": fidelity}
    return item


def payload(items: list[dict]) -> dict:
    boundary = {
        "frozen_constraints": [item["id"] for item in items if item.get("change_policy") == "frozen" and item.get("disposition") != "explicitly_superseded"],
        "allowed_changes": [item["id"] for item in items if item.get("change_policy") == "allowed" and item.get("disposition") != "explicitly_superseded"],
        "prohibited_changes": [item["id"] for item in items if item.get("change_policy") == "prohibited" and item.get("disposition") != "explicitly_superseded"],
        "open_decisions": [item["id"] for item in items if item.get("change_policy") == "open" and item.get("disposition") != "explicitly_superseded"],
        "source_authority": {item["id"]: item["source"]["authority"] for item in items},
    }
    return {
        "constraints": items,
        "boundary_snapshot": boundary,
        "entrypoints": {
            "single_active_entry": True,
            "historical_deauthorized": True,
            "readme_exposes_current_constraints": True,
            "agents_exposes_current_constraints": True,
            "project_brief_exposes_current_constraints": True,
            "downstream_boundary_snapshot_attached": True,
        },
    }


class SemanticCoverageFixtures(unittest.TestCase):
    def test_fixture_a_preserves_proprietary_technology_while_theme_is_open(self) -> None:
        technology = constraint("C-TECH-01", "iOS 26 uses Liquid Glass; iOS 17–25 uses a visually homologous SwiftUI material fallback")
        theme = constraint("C-THEME-01", "Color, transparency, and tint may be explored", category="visual", policy="allowed", target_file="02_设计/设计规格.md")
        result = validate(payload([technology, theme]))
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_passed")
        self.assertEqual(result["anti_drift_status"], "anti-drift enforced")

    def test_fixture_a_rejects_generalized_replacement(self) -> None:
        technology = constraint("C-TECH-01", "iOS 26 uses Liquid Glass", fidelity="generalized")
        result = validate(payload([technology]))
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_failed")
        self.assertIn("semantic_generalization_detected", {item["code"] for item in result["errors"]})

    def test_fixture_b_freezes_structure_and_allows_theme(self) -> None:
        navigation = constraint("C-NAV-01", "Keep four primary entries in the approved order", category="navigation", policy="prohibited", target_file="02_设计/设计规格.md")
        theme = constraint("C-COLOR-01", "Theme colors may change", category="visual", policy="allowed", target_file="02_设计/设计规格.md")
        result = validate(payload([navigation, theme]))
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_passed")

    def test_fixture_c_allows_cross_document_relocation(self) -> None:
        platform = constraint("C-PLATFORM-01", "Support iOS 17 and later", disposition="relocated", target_file="03_工程/工程合同.md")
        result = validate(payload([platform]))
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_passed")
        self.assertTrue(result["archive_allowed"])

    def test_semantic_preflight_passes_before_history_is_deauthorized(self) -> None:
        platform = constraint("C-PLATFORM-02", "Retain the approved compatibility renderer")
        data = payload([platform])
        data["entrypoints"]["historical_deauthorized"] = False
        result = validate(data)
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_passed")
        self.assertTrue(result["archive_allowed"])
        self.assertEqual(result["anti_drift_status"], "anti-drift limited")

    def test_fixture_d_blocks_silent_omission_and_archival(self) -> None:
        omitted = constraint("C-DATA-01", "All local data remains encrypted at rest")
        omitted.pop("target")
        result = validate(payload([omitted]))
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_failed")
        self.assertEqual(result["anti_drift_status"], "anti-drift limited")
        self.assertFalse(result["archive_allowed"])
        self.assertIn("target_missing", {item["code"] for item in result["errors"]})

    def test_fixture_e_accepts_authorized_supersession(self) -> None:
        legacy = constraint("C-TECH-OLD", "Use the legacy rendering engine", disposition="explicitly_superseded")
        legacy["supersession"] = {
            "owner": "authorized product owner",
            "scope": "rendering technology",
            "date": "2026-08-11",
            "evidence": "DEC-RENDER-04",
            "replacement": "Use the new rendering engine",
        }
        result = validate(payload([legacy]))
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_passed")

    def test_unresolved_high_impact_constraint_is_failed(self) -> None:
        unresolved = constraint("C-PRIVACY-01", "Do not upload personal data", disposition="unresolved")
        data = payload([unresolved])
        data["entrypoints"]["historical_deauthorized"] = False
        result = validate(data)
        self.assertEqual(result["semantic_coverage_status"], "semantic_coverage_failed")

    def test_boundary_snapshot_cannot_silently_drop_frozen_id(self) -> None:
        frozen = constraint("C-STRUCT-01", "Keep the approved information architecture")
        data = payload([frozen])
        data["boundary_snapshot"]["frozen_constraints"] = []
        result = validate(data)
        self.assertIn("boundary_policy_not_carried", {item["code"] for item in result["errors"]})


if __name__ == "__main__":
    unittest.main()
