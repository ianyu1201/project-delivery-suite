---
state_schema: "1.0"
workspace_root: "<absolute project root>"
active_version_root: "<absolute active version root>"
archive_root: "<absolute archive root or pending>"
repo_root: "<absolute Git root or pending>"
staging_root: "<absolute staging root or empty>"
topology: "complete-snapshot | numbered-lifecycle | project-defined"
latest_observed: "<version or none>"
current_approved: "<version or empty>"
active_candidate: "<version or empty>"
source_lineage: "<approved source -> candidate>"
governance_cycle_id: "<stable cycle id>"
prd_status: "draft"
ui_contract_status: "draft"
validation_status: "pending"
acceptance_status: "pending"
version_approval_status: "pending"
version_approval_intent: "none"
archive_status: "pending"
anti_drift_status: "pending"
version_status: "defining"
phase: "S0"
fixed_point: "<commit, tag, digest, or pending>"
prd_path: "<project-relative active PRD path>"
ui_contract_path: "<project-relative active UI contract path>"
development_handoff_path: "<project-relative path or pending>"
evidence_manifest_path: "<project-relative path or pending>"
acceptance_report_path: "<project-relative path or pending>"
candidate_manifest_path: "<project-relative path or pending>"
session_registry_path: "SESSION_REGISTRY.md"
---

# <PROJECT> 项目状态

> 这是跨对话恢复入口。只记录现役状态，不写聊天流水账。YAML frontmatter 是机器校验权威；正文不得与其冲突。

## 当前指针

- 工作区根 `workspace_root`：
- 活动版本根 `active_version_root`：
- 历史归档根 `archive_root`：
- Git 根 `repo_root`：
- 候选暂存根 `staging_root`：
- 目录拓扑：complete-snapshot / numbered-lifecycle / project-defined
- 最新观察版本 `latest_observed`：
- 当前批准版本 `current_approved`：
- 活动候选 `active_candidate`：
- 源谱系 `source_lineage`：
- 治理周期 `governance_cycle_id`：
- PRD 状态：draft / approved
- UI 交付合同状态：draft / confirmed / frozen
- 验证状态：pending / failed / passed
- 独立验收：pending / rejected / accepted
- 版本批准：pending / approved
- 版本批准意图：none / received（只记录用户授权，不推进事实状态）
- 归档状态：not-applicable / pending / organized
- Anti-drift：pending / enforced / failed / limited
- 版本状态：idea / defining / contracted / building / active_candidate / validation_passed / accepted / version_approved-current / predecessors_archived / released-live_verified
- 当前阶段：S0–S7
- 当前分支：
- 固定基线 commit/tag：
- 候选 commit：
- 开发交接：
- 证据 manifest：
- 独立验收报告：
- 候选 manifest：
- 当前主对话：
- 更新时间：

## 已满足门禁

- [ ] <待补充>

## 当前缺口与阻断

| ID | 级别 | 事实/问题 | 所需决定或证据 | 责任人 | 状态 |
|---|---|---|---|---|---|

## 权威入口

1. 当前唯一 PRD：
2. 当前未解决 Issue（如有）：
3. 代码、测试和运行入口：
4. 设计/实现与验收合同：

## 下一步

1. <待补充>

## 不要做

- 不从历史归档提取现役指令。
- 不在版本治理器之外自行增版或创建第二个候选。
- 不将历史内容移入 Trash 或永久删除。
- 不用用户口头批准替代 validation passed、accepted、固定点或证据文件。
- 不在 `validate_project_state.py` 对相应 gate 返回非零时交接、批准或归档。
