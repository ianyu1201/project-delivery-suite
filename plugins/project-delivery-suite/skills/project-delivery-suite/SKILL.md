---
name: project-delivery-suite
description: 面向非专业开发者和 AI 协作团队的项目交付与版本治理单一入口；内部路由项目启动、PRD、设计与工程合同、Codex 阶段会话、开发与独立验收，以及多版本 PRD/Issue/完整代码整合、语义硬约束保真、下一完整版本和全部前序归档。Use when starting or taking over a project, creating a new project/version conversation, rescuing AI-built work, reconciling historical versions, preventing requirement drift, or deciding whether a candidate is ready to approve and archive. Start read-only, preserve approved constraints unless explicitly superseded, and never upload, delete, deploy, or access production automatically.
---

# Project Delivery Suite

把本 Skill 作为唯一用户入口，在“项目交付总控”和“版本治理”两个内部模块间路由。文件、批准证据、Git 固定点和运行证据是跨对话事实；聊天记忆不是权威。

## 核心合同

始终执行：

1. 先识别项目、版本拓扑、当前阶段和权限，再提出流程；Skill 调用默认只授权读取。
2. 写入、创建会话、移动历史、提交、发布或外部操作前，说明精确范围、路径、排除项、验证和回滚，并取得相应授权。
3. 不把最新目录、当前代码、绿色测试、合并 PR 或候选图自动当成批准需求、完成版本或确认设计。
4. 同一版本只维护一份现役 PRD；PRD 只回答产品 what/why，平台、兼容、实现和运行验收进入工程合同或 ADR。
5. 旧批准硬约束只能 `preserved / relocated / explicitly_superseded / unresolved`；沉默、归档或泛化措辞都不是取代证据。
6. 开发者不得批准自己的最终交付；独立验收和版本批准分开。
7. 不覆盖既有候选，不原地修改批准历史，不因验证失败重复增版。
8. 不自动上传、推送、部署、访问共享/生产数据库、移入废纸篓、删除或清空废纸篓。
9. 专业 PRD Skill 是可选增强；缺失时使用 [assets/MINIMUM_PRD.md](assets/MINIMUM_PRD.md)，流程不得中断。
10. 把绝对愿望转成有限范围、证据门禁和残余风险，不宣称绝对零 Bug。

## 内部路由

### 项目交付总控模块

处理新项目、既有项目接管、缺陷救援、阶段门禁、PRD/设计/工程合同、Codex 会话、开发编排、独立验收和版本冻结。按 `S0 启动 → S1 审计建档 → S2 产品设计 → S3 交付合同 → S4 开发准备 → S5 实施验证 → S6 独立验收 → S7 冻结复盘` 推进。

### 版本治理模块

发现多个完整版本、跨版本 PRD 冲突、活动候选、下一完整版本或全部前序归档时切入本模块。读取 [references/governance-model.md](references/governance-model.md)，独占：

- `latest_observed / current_approved / active_candidate` 分类；
- 沿用项目命名确定下一版；
- PRD、Issue、代码和硬约束整合；
- 不覆盖地物化完整候选；
- 新版本批准后的全部前序归档。

两个模块属于同一 Skill，不互相调用第二个 Skill。用 [references/version-governance-coordination.md](references/version-governance-coordination.md) 的内部交接状态避免并发写同一候选。

## 入口和目录身份

区分新项目、既有项目、新版本、缺陷/救援。版本治理前固定：

`workspace_root / active_version_root / archive_root / repo_root / staging_root`

保留项目自己的语言、大小写、前缀、分隔符和版本规则。没有规则时才询问是否采用 V1/V2/V3。跟踪三个独立身份：

- `latest_observed`：外观看起来最新，不代表权威；
- `current_approved`：有批准证据的当前版本；
- `active_candidate`：本周期正在修复的未批准版本，重试不增版。

先运行只读盘点：

```bash
python3 <skill-dir>/scripts/project_snapshot.py --root <project-root>
python3 <skill-dir>/scripts/audit_versions.py summary <project-root> --format markdown
```

将 partial/unsupported、命名歧义、symlink、ignored/untracked、LFS、submodule、数据库、uploads、密钥和未知数据保持 unresolved。

## 语义约束保真门禁

版本来源分类后、旧材料去权威化或归档前，完整读取 [references/semantic-constraint-preservation.md](references/semantic-constraint-preservation.md)。盘点每条已批准重要约束的稳定 ID、原文、来源/版本、authority、类别、范围、影响、变化策略、目标文件和处置证据。

跨文档路由：

- 产品价值、对象、行为和范围 → PRD；
- 页面、交互、视觉和无障碍体验 → 设计规格；
- 平台、兼容、专有技术、实现和运行验收 → 工程合同或 ADR；
- 下游不看到就容易犯错的边界 → AGENTS.md；
- 当前版本身份、关键冻结项和继续入口 → README / PROJECT_BRIEF；
- 路径、阶段和状态指针 → PROJECT_STATE。

不得用颜色、主题或视觉重新讨论范围覆盖仍冻结的平台技术、信息架构、导航、入口数量/顺序、组件几何或业务行为。不得用泛化词静默替代专有技术、接口、标准、平台或兼容要求。

可在临时目录生成结构化覆盖 JSON，不强制项目永久新增追踪文档。归档前运行：

```bash
python3 <skill-dir>/scripts/validate_semantic_coverage.py <coverage.json>
```

非 `semantic_coverage_passed` 时不得去权威化旧材料、归档、发放下游启动包或报告 `anti-drift enforced`。脚本验证结构化处置证据，不负责从自然语言自动抽取语义；Agent 必须结合权威来源完成判断。

## 单一候选 PRD、Issue 和完整代码

1. 按 authority 分类 current-approved、historical-approved、active-candidate、draft、superseded、unknown。
2. 展示唯一候选 PRD 的精确内容；授权产品负责人批准后再实现改变的产品行为。
3. `resolved-and-verified` 不进入下一活动 Issue；`open / deferred / reopened / changed-not-verified` 用稳定 ID、证据和验收条件延续。
4. 目标目录必须不存在；在相邻唯一 staging 从 `current_approved` 谱系复制完整源、测试、配置、迁移、锁文件、必要资产、已批准 PRD 和活动 Issue。
5. 默认不复制 `.git`、secrets、数据库、uploads、运行时数据、依赖、缓存和日志；逐项分类并比较 manifest、路径、哈希、mode、symlink 和排除项。
6. PRD、代码、Issue 验收、版本字段和语义覆盖全部通过后，才允许独立版本批准。

完整候选必须可独立理解和继续迭代，不得只是残缺补丁或一个未经验证的分支。

## 下游边界快照与会话

创建产品、设计、开发或验收会话前，必须从现役权威文件生成并附带：

- `frozen_constraints`；
- `allowed_changes`；
- `prohibited_changes`；
- `open_decisions`；
- `source_authority`。

主题、颜色、材质或动效探索默认只能改变已列入 `allowed_changes` 的语义颜色、材质参数、透明度、阴影、描边和反馈；不得自动改变信息架构、布局、导航、入口、组件几何、图标语义、文案或业务行为。

若环境提供会话创建工具，在用户确认、上游冻结、语义覆盖通过且候选物化后直接创建并记录真实 ID；否则生成完整可复制标题、工作目录、固定起点和启动 Prompt。详细规则读取 [references/conversation-orchestration.md](references/conversation-orchestration.md)。

## 副作用、数据与归档门禁

- 先检查项目命令；仅在确认目标的候选本地环境运行 lint/typecheck/unit/build。
- 网络测试、外部 API、远程缓存等先说明并授权；生产迁移、部署和共享数据库操作永不在本 Skill 执行。
- 依赖、虚拟环境、缓存、日志和可重建中间物可作为独立候选；数据库、uploads、用户数据、密钥、模型和未知数据默认受保护。
- 新版本获批且 `semantic_coverage_passed` 后，才按项目既有归档名移动全部前序版本；任一约束无去向、被泛化、未裁决或无取代证据时报告 `archive pending`。
- 同盘归档只整理、不释放空间；用户需要空间时自行处理归档，本 Skill 不执行删除。

## 文件化状态和最小文档

优先补齐现有权威文件，不强制创建平行真相。最小集合通常是：

- `PROJECT_BRIEF.md`：定位、边界和关键冻结项摘要；
- `PROJECT_STATE.md`：五类路径、阶段、候选、语义覆盖、anti-drift 和下一步；
- `THREAD_REGISTRY.md`：会话、职责、工作目录、分支和状态；
- 当前版本现有 PRD、设计规格、工程合同/ADR、Issue 和证据索引。

约束覆盖矩阵可临时存在；必要结果应嵌入正确的现役权威文件。最小文档不等于可以跳过语义覆盖。

## 完成状态

只报告最窄状态：`audit complete/limited/unsupported`、`awaiting naming/authority/requirement decision`、`semantic_coverage_passed/limited/failed`、`candidate incomplete/materialized`、`validation pending/failed/passed`、`accepted/rejected`、`version approval pending/approved`、`archive pending/organized`、`anti-drift enforced/limited`。

`anti-drift enforced` 必须同时满足：唯一现役入口、历史明确非权威、所有批准硬约束已保留/迁移/明确取代、无未决高影响约束、README/AGENTS/PROJECT_BRIEF 可定位冻结项、下游边界快照已附带。只完成指针收敛时必须报告 `anti-drift limited`。

## 资源导航

- [references/semantic-constraint-preservation.md](references/semantic-constraint-preservation.md)：约束清单、跨文档路由、覆盖和归档阻断。
- [references/governance-model.md](references/governance-model.md)：版本命名、authority、完整候选、Issue、归档和恢复。
- [references/version-governance-coordination.md](references/version-governance-coordination.md)：两个内部模块的交接状态。
- [references/lifecycle-and-scaling.md](references/lifecycle-and-scaling.md)：入口、阶段与规模。
- [references/conversation-orchestration.md](references/conversation-orchestration.md)：会话创建与启动包。
- [references/artifact-and-folder-governance.md](references/artifact-and-folder-governance.md)：权威文件与目录。
- [references/ui-implementation-and-runtime-acceptance.md](references/ui-implementation-and-runtime-acceptance.md)：UI 合同。
- [references/quality-and-evidence.md](references/quality-and-evidence.md)：测试、运行与独立验收。
- [assets](assets/)：最小 PRD、项目状态、交接和验收模板。
