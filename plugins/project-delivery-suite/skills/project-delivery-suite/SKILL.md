---
name: project-delivery-suite
description: 项目启动与接管、交付流程裁剪、多版本需求和代码整合、跨版本约束保真、版本验收与历史归档。Use for project kickoff or takeover, delivery coordination, reconciling historical versions, or release-governance decisions. A routine code explanation or local edit does not need full project governance; when explicitly invoked for a small change, use the local delivery path.
---

# Project Delivery Suite

一个用户入口，按目标选择局部交付、项目交付总控或版本治理。文件、批准记录、Git 固定点和运行证据承载跨会话事实。

## 不可丢失的边界

1. **继承授权**：只提出审阅或目标不明时先只读；用户明确要求实现、修复或按批准方案继续时，在已有授权内连续完成。不得因写入、验证、提交等步骤切换重复确认。目标、外部影响、权限或不可逆风险实质变化，或业务约束冲突时才询问。创建新任务、推送、上传、发布须有覆盖该动作及目标的明确授权。
2. **区分事实与批准**：最新目录、当前代码、绿色测试、合并 PR 和候选图都不自动成为批准需求、确认设计或批准版本。自测不等于独立验收；开发者不得自行批准正式版本。未执行的门禁如实标记。
3. **保持单一权威**：同一版本只维护一份现役 PRD，回答产品 what/why；设计规格、工程合同/ADR 承载其余约束。优先更新现有文件；专业 PRD Skill 缺失时使用 [最小 PRD](assets/MINIMUM_PRD.md)。
4. **保留硬约束**：批准约束只能 preserved / relocated / explicitly_superseded / unresolved。沉默、泛化、最新草案或归档不是取代证据。视觉探索不扩大已授权变化边界；涉及 UI 时读取专项合同。
5. **保护候选与历史**：不覆盖已有候选或原地修改批准历史；失败继续同一候选，不自动增版。完整候选必须包含继续开发所需的完整内容，不能仅交残缺补丁。
6. **保留操作边界**：本 Skill 不执行生产部署、共享/生产数据库操作、Trash 或删除。明确提出这些目标时，说明本 Skill 的能力边界并交由适用流程；不把能力边界变成对用户目标的全局拒绝。历史归档须有批准与移动授权，同盘归档不声称释放空间。
7. **有限且可证明的完成**：把“全部完成、零 Bug”转为明确范围、适用检查及残余风险；机械检查不代替语义复核或业务批准。

## 路由：只加载当前分支

| 当前目标 | 处理路径与参考资料 |
|---|---|
| 只读代码审阅或局部问题分析，无接管、版本或发布判定 | 在当前对象内完成只读审阅；先读相关源码与已有说明，只在具体问题需要时加载参考资料 |
| 明确、局部、可逆的修复或小功能，无历史整合/重要产品决策 | 当前会话完成局部交付；[规模裁剪](references/lifecycle-and-scaling.md) |
| 新项目、既有项目接管、多个交付阶段或高风险变化 | 项目总控；[规模与阶段](references/lifecycle-and-scaling.md)、[新手需求与范围](references/novice-intake-and-scope-control.md) |
| 多个完整版本、PRD 冲突、下一完整候选或历史归档 | 版本治理；[治理模型](references/governance-model.md)、[模块交接](references/version-governance-coordination.md) |
| 批准约束迁移、历史去权威化或相关下游交接 | [语义约束保真](references/semantic-constraint-preservation.md)，按结构、引用、语义三层检查 |
| UI、主题、材质或交互变化 | [UI 实现与运行验收](references/ui-implementation-and-runtime-acceptance.md)；保留 frozen/allowed/prohibited/open/source-authority 边界 |
| 需要创建/交接任务或已有任务协调 | [会话编排](references/conversation-orchestration.md)；新任务须用户明确请求，具备独立目标和冻结输入 |
| 验证、证据复用或独立验收 | [质量与证据](references/quality-and-evidence.md)；按风险选择检查 |
| Git 固定点、提交与版本号 | [Git 与发布控制](references/git-and-release-control.md) |
| 整理权威文件或目录 | [文件治理](references/artifact-and-folder-governance.md)；不为局部任务预建全套目录 |

只读审阅不自动升级为项目接管或发布验收。围绕请求报告有证据的问题、影响与不确定性；缺少 Git、PRD 或治理目录本身不是功能缺陷或高优先级阻塞。只有请求或已有约束要求这些产物时才评估其缺失，不为普通审阅遍历治理参考或执行全项目盘点。

## 版本治理入口

仅在版本治理路径固定 `workspace_root / active_version_root / archive_root / repo_root / staging_root`。沿用项目命名与拓扑，区分 `latest_observed / current_approved / active_candidate`；无足够依据时保留未决，不以名称替代批准。

需要盘点时运行：

```bash
python3 <skill-dir>/scripts/project_snapshot.py --root <project-root>
python3 <skill-dir>/scripts/audit_versions.py summary <project-root> --format markdown
```

partial/unsupported、未知数据、symlink、ignored/untracked、LFS/submodule、数据库/uploads 与密钥须显式处置；扫描省略不等于可丢弃。完整候选采用相邻唯一 staging 或项目约定的隔离 worktree，验证源谱系、manifest、哈希、mode、链接和排除项后提升；具体门禁见治理模型。

语义迁移使用 `validate_semantic_coverage.py <coverage.json> --root <project-root>`；schema v2 仅验证结构和固定引用。完成权威来源复核后才记录 `semantic_coverage_passed`，归档还须版本批准及路径授权。纯新项目无旧批准约束时可有依据地记录 not-applicable。证据和兼容迁移说明见语义约束参考。

`resolved-and-verified` Issue 退出活动清单；open/deferred/reopened/changed-not-verified 以稳定 ID 和验收条件延续。版本总控与治理模块不得并发创建或写同一候选。

## 文件与结束状态

按任务需要复用 [模板](assets/)：局部任务通常只更新已有文件和交付说明；跨会话才补恢复入口，实际创建任务才记录 THREAD_REGISTRY。PROJECT_STATE 保存路径、状态、证据指针和下一步，不复制产品需求。无需强制每个项目同时拥有 README、AGENTS 和 PROJECT_BRIEF；实际入口必须能找到适用冻结项。

报告已改内容、适用检查、证据与未验证项。局部交付可结束为 completed / blocked；正式版本区分 validation、独立 acceptance、version approval、archive 和 release 状态。仅在唯一入口、历史明确非权威、批准约束均有有效处置、无未决高影响约束、冻结项可发现且下游边界快照已附带时，才报告 `anti-drift enforced`；只有指针收敛时是 limited。

维护本 Skill 时，使用 [行为评估协议](references/behavior-evaluation.md) 检查授权、路由、证据和恢复行为；单元测试与合成轨迹不构成真实模型评估。
