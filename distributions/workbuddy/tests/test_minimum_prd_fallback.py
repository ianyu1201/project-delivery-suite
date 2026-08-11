#!/usr/bin/env python3
"""Regression tests for the built-in minimum PRD fallback contract."""

from __future__ import annotations

import unittest
from pathlib import Path


SKILL_ROOT = (
    Path(__file__).resolve().parents[1]
    / "package"
    / "project-delivery-suite"
)
SKILL_TEXT = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
PRD_TEXT = (SKILL_ROOT / "assets" / "MINIMUM_PRD.md").read_text(encoding="utf-8")


class MinimumPrdFallbackTests(unittest.TestCase):
    def test_skill_routes_to_optional_specialist_then_builtin_fallback(self) -> None:
        specialist = SKILL_TEXT.index("检查当前 WorkBuddy 是否真实安装")
        existing = SKILL_TEXT.index("先复用项目现有的权威 PRD")
        fallback = SKILL_TEXT.index("完整读取 [MINIMUM_PRD.md]")
        self.assertLess(specialist, existing)
        self.assertLess(existing, fallback)
        self.assertIn("不要求用户额外安装", SKILL_TEXT)
        self.assertIn("不声称已经调用", SKILL_TEXT)

    def test_minimum_prd_covers_scope_traceability_and_acceptance(self) -> None:
        for required in (
            "## 文档状态",
            "## 1. 产品目标",
            "## 2. 用户与核心场景",
            "## 3. 本版本范围",
            "### 明确不包含",
            "## 4. 产品需求",
            "REQ-001",
            "## 5. 状态、异常与边界",
            "## 6. 数据与约束",
            "## 7. 验收条件",
            "AC-001",
            "## 8. 开放问题与冲突",
            "DEC-001",
            "## 9. 追溯与变更",
        ):
            self.assertIn(required, PRD_TEXT)

    def test_prd_approval_stays_separate_from_delivery_approval(self) -> None:
        self.assertIn("状态必须保持 `draft`", PRD_TEXT)
        self.assertIn(
            "批准 PRD 只批准产品范围，不代表代码完成、验收通过、版本批准或已经发布",
            PRD_TEXT,
        )
        self.assertIn("同一版本只维护一份现役 PRD", SKILL_TEXT)


if __name__ == "__main__":
    unittest.main()
