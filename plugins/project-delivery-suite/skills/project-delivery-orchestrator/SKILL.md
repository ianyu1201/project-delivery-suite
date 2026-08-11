---
name: project-delivery-orchestrator
description: 面向非专业开发者和 AI 协作团队的软件项目交付总控；将模糊想法或既有项目组织为可审计的建档、规模分级、编号式全生命周期目录、PRD/设计、实现与验收合同、Git/版本管理、阶段化 Codex 对话、独立验收和版本复盘。Use when starting or taking over a project, deciding what to do next, coordinating agents or chats, starting a release, rescuing an AI-built project, or asking whether a project is ready to build or release. When complete historical version folders, cross-version PRD conflicts, or predecessor archival exist, orchestrate `consolidate-project-versions` instead of creating the next complete version itself.
---

# 项目交付总控

把对话当作临时工作间，把仓库中的冻结文档、Git 提交和运行证据当作项目记忆。帮助不熟悉开发流程的用户从一句想法开始，也允许成熟项目从当前阶段接入。

## 核心合同

始终执行以下规则：

1. 先识别项目，再推荐流程；不要先套大型模板。
2. 先展示判断、目录、对话和 Git 方案；实际建档、创建对话或修改仓库前取得用户确认。
3. 按阶段创建干净对话；不要在需求未冻结时一次创建全部下游对话。
4. 将已确认事实、待验证假设、冲突和缺失信息分开记录。
5. 不把候选图当确认稿，不把当前代码反推成最终需求，不把测试通过当运行体验通过。
6. PRD 只回答产品的 what/why；进入开发前必须另有可执行的实现约束与运行验收合同。
7. 开发者不得自行批准自己的最终交付；使用固定提交进行独立验收。
8. 删除、重命名、覆盖、发布、推送、建分支或其他有影响的动作服从当前权限与用户授权。
9. 每次只推进当前门禁允许的下一阶段；发现上游未冻结就停止下游实施并回到缺口。
10. 使用用户的语言解释，不要求用户理解框架、布局 API、测试术语或 Git 细节。
11. 每次变更前锁定项目根目录、Git/worktree、版本和目标交付物；当前明确路径优先于旧对话记忆。
12. 把“全部完成、没有 Bug、完全一致”等愿望翻译为范围、严重度、环境、门禁和残余风险，不把绝对愿望伪装成可证明事实。
13. 总控只负责生命周期和对话编排；既有版本系列的下一版命名、完整候选目录和全部前序版本归档由 `consolidate-project-versions` 唯一负责。
14. 专业 PRD Skill 是可选增强能力，不是运行前提；缺失时使用内置最小 PRD 回退合同，不中断项目流程，也不要求用户额外安装。

## 入口判断

先识别四种入口：

- **新项目**：只有想法、参考资料或空目录。
- **既有项目**：已有文档、代码或 Git 历史；先做 brownfield 审计。
- **新版本**：上一版本已有固定基线；从版本差量开始。发现多个完整版本副本、历史 PRD 冲突、已有活动候选或全部前序版本待归档时，转入版本治理协作流程，不自行建立下一完整版本目录。
- **缺陷/救援**：已有实现但质量失控；先冻结现场、复现问题和建立缺陷合同。

用户材料不完整时，先从已有内容提取答案，只追问会改变项目方向、风险等级或下一步的关键问题。至少弄清：目标用户、问题、目标结果、平台/实体载体、已有资产、明确排除项和关键限制。

用户使用口语、语音转写或非技术表达时，不要求其先写专业 Prompt。先复述“我理解的对象、目标、当前状态、这一步动作、完成标准”，再把需求翻译为专业交付物。遇到“这个项目/当前文件夹/继续/开始前再加一个任务”等表达，按 [references/novice-intake-and-scope-control.md](references/novice-intake-and-scope-control.md) 锁定对象与范围。

需要详细分级、版本策略或救援流程时，完整读取 [references/lifecycle-and-scaling.md](references/lifecycle-and-scaling.md)。

## 阶段状态机

把项目标记在一个且仅一个当前阶段。每次输出“当前阶段、已满足门禁、缺口、建议下一步”。

| 阶段 | 目的 | 离开阶段的最低门禁 |
|---|---|---|
| S0 启动 | 理解想法与边界 | 项目简报、入口类型、初始风险 |
| S1 审计与建档 | 建立真实现状和唯一入口 | 文件/代码/证据清单、事实冲突、治理方案获确认 |
| S2 产品与设计 | 冻结本版本要解决的问题和体验 | PRD/差量范围、确认视觉或明确无视觉基线、开放问题已裁决或隔离 |
| S3 交付合同 | 把意图翻译为可实现、可验收的合同 | 实现约束、状态矩阵、运行验收、非回归和证据要求获确认 |
| S4 开发准备 | 切分可执行工作 | 固定基线、计划、文件所有权、Git/回滚方案、开发启动包 |
| S5 实施与验证 | 分片开发并持续验证 | 约定测试通过、真实关键路径验证、证据清单、无未处理阻断问题 |
| S6 独立验收 | 在干净上下文复验固定提交 | 合同逐项结论、缺陷分级、发布建议 |
| S7 冻结与复盘 | 形成可复现版本和下一版起点 | 版本标签/等价固定点、交接、已知问题、知识收尾 |

不要用“文档很多”代替门禁，也不要用“AI 表示完成”代替证据。详细证据层级读取 [references/quality-and-evidence.md](references/quality-and-evidence.md)。

## 版本治理协作

完整读取 [references/version-governance-coordination.md](references/version-governance-coordination.md) 后再处理新版本目录、多版本冲突或历史归档。总控先固定 `workspace_root / active_version_root / archive_root / repo_root / staging_root`，再让版本治理返回下一版命名、候选目录和狭义状态。候选目录物化后，总控才能在该完整目录中启动开发和独立验收对话。

## UI 强制门禁

项目含任何图形界面时，S3 必须生成《UI 实现与运行验收合同》。即使用户已经提供完整 PRD 和参考图，也不能跳过。

合同至少覆盖：

- 页面目标、信息层级、容器与系统区域所有权；
- 尺寸关系、对齐、间距、滚动、自适应和安全区规则；
- 默认、空、加载、错误、禁用、编辑、完成等状态；
- 导航、按钮、手势、阈值、反馈、数据变化和持久化；
- 字体放大、窄屏、键盘、横竖屏（如支持）、无障碍；
- V-1 不可丢失能力和禁止使用的投机性实现；
- 目标设备/环境上的实际操作步骤、预期结果和证据格式；
- 候选视觉、确认视觉、真实运行证据的明确身份与路径。
- 视觉证据覆盖矩阵：先汇总全部任务，再按同一 commit、页面状态、数据与设备环境批量取证；一份证据可关联多条合同 ID，任一等价条件变化后重新取证。

完整读取 [references/ui-implementation-and-runtime-acceptance.md](references/ui-implementation-and-runtime-acceptance.md)，并从 [assets/UI_IMPLEMENTATION_AND_RUNTIME_ACCEPTANCE_CONTRACT.md](assets/UI_IMPLEMENTATION_AND_RUNTIME_ACCEPTANCE_CONTRACT.md) 生成项目文件。只有用户确认可观察结果后，才能进入 S4。

## 项目分级与对话拓扑

按不确定性、系统耦合、平台数量、数据/安全风险、迁移难度和失败影响分级，不按代码行数分级：

- **小型**：通常使用“交付 + 独立验收”两个阶段对话。
- **中型**：通常使用“产品与设计 + 开发总控 + 独立验收”三个阶段对话。
- **大型/高风险**：增加版本总控、架构/安全、多个工作包、系统测试或发布对话。

当前启动对话可以承担轻量总控，但要把状态写入文件。只在前一阶段交付物已冻结时创建下一阶段对话；创建后记录 thread ID、工作目录、分支、基线提交和职责。

若运行环境提供对话创建工具，在用户确认方案后直接创建并命名；否则生成完整、可复制的启动包。详细规则读取 [references/conversation-orchestration.md](references/conversation-orchestration.md)。

## 执行流程

### 1. 建立只读快照

对既有目录优先运行：

```bash
python3 <skill-dir>/scripts/project_snapshot.py --root <project-root>
```

先把 `<skill-dir>` 解析为本 `SKILL.md` 所在目录；不要假设当前项目包含这些脚本。

读取项目规则、README、文档索引、代码入口、测试、Git 状态和现有证据。对大仓库先机械枚举，再按风险读取；只有用户明确要求全量审计或索引失效时才全文读取全部内容。

### 2. 给出启动提案

在写入前向用户展示：

- 已理解的项目目标和当前阶段；
- 新项目/既有项目/新版本/救援判断；
- 小型/中型/大型判断及依据；
- 推荐目录（只列新增或调整项）；
- 推荐对话及创建时机；
- Git 与版本基线；
- 当前缺口、风险和第一步。

提案开头先给一个用户可直接判断的简版：`你要做什么 → 我判断现在在哪 → 这一步只做什么 → 做完看到什么`。详细阶段名、合同和 Git 术语放在其后。

不要把可逆的细节问题一次问完。涉及方向性选择时给出推荐项及影响。

发送启动提案前逐项自检，任何 profile 都不得遗漏：`入口类型、唯一规模等级、当前阶段、最小版本闭环、目录变化、对话拓扑及创建时机、Git/固定基线、当前门禁与下一步`。使用 `small / medium / large-high-risk` 中一个主等级；可以说明采用轻量裁剪，但不要创造含糊的混合等级。项目含 Web、App、显示屏或控制面板时，必须显式列出 UI 实现与运行验收合同，即使主要风险来自硬件。

### 3. 经确认后建档

按 [references/artifact-and-folder-governance.md](references/artifact-and-folder-governance.md) 选择最小结构。可先预览：

```bash
python3 <skill-dir>/scripts/scaffold_delivery.py --root <project-root> --scale <small|medium|large> --profile <software|ios|web|robotics|hybrid> --topology numbered-lifecycle --version <project-version-name>
```

用户确认后增加 `--apply`。此脚本只用于没有现役结构的新项目首次建档，不得用于既有版本系列的下一完整版本。脚本只创建不存在的目录，不覆盖文件；模板仍由 Agent 按项目事实填充。

### 4. 调用专业能力

总控只负责编排。根据当前环境发现并使用最匹配的专业 Skill：

- 多版本文件夹、PRD/代码整合和全部前序归档：优先 `consolidate-project-versions`；
- 其他项目知识收尾/目录治理：优先 `neat-freak` 或同类能力；
- PRD：优先 `prd-development` 或同类产品能力；缺失时不要阻断或假装已调用，改用 [assets/MINIMUM_PRD.md](assets/MINIMUM_PRD.md) 生成最小但可批准、可追溯的 PRD；
- Git/版本：优先 `git-workflow-and-versioning` 或同类能力；
- UI 设计与审计：使用平台/框架对应的设计能力；
- 实施、测试、性能、安全、硬件：按项目 profile 选择对应能力。

调用专业 Skill 前遵循其完整说明。专业 Skill 与本总控冲突时，用户、系统和项目规则优先；本总控的阶段门禁不得被“直接开始编码”隐式绕过。

PRD 回退遵循以下顺序：先复用项目现有的权威 PRD 文件名、语言和结构；只有没有可用约定时才适配 `MINIMUM_PRD.md`。同一版本只维护一份现役 PRD，不另建“最终版”“汇总版”或平行基线。先展示草稿并处理开放问题，只有授权产品负责人批准精确内容并留下批准证据后才把状态改为 `approved`。PRD 批准不等于实现、验收或版本批准。

### 5. 维护文件化状态

至少维护：

- `PROJECT_BRIEF.md`：稳定项目定位和边界；
- `PROJECT_STATE.md`：五类根路径、当前批准版本、活动候选、阶段、固定提交、门禁和下一步；
- `THREAD_REGISTRY.md`：对话、职责、分支和状态；
- 当前版本目录：范围、设计、合同、交付、验收和证据索引。

使用 [assets](assets/) 中的模板，但先适配现场目录，不强行创建平行真相。已有权威文件时就地补齐或建立短指针。

### 6. 分阶段交接

每个阶段结束时：

1. 固定交付物和 Git 状态；
2. 更新 `PROJECT_STATE.md`；
3. 生成下游启动包，明确必读文件、范围、禁止事项、验收和回报格式；
4. 创建下一阶段对话或让用户确认启动；
5. 下游先复述理解，发现冲突就停止实施并回报上游。

## 版本迭代

- PATCH：通常创建一个缺陷交付对话和一次独立复验，不重建全部产品流程。
- MINOR/常规版本：创建新的产品与设计、开发总控、独立验收阶段对话。
- MAJOR/高风险版本：重新评估架构、安全、迁移、兼容和发布策略。
- 新版本从上一版固定标签和非回归矩阵开始，不从旧对话记忆开始。
- 既有版本系列的增版和归档执行 [references/version-governance-coordination.md](references/version-governance-coordination.md)；验证失败时继续同一 `active_candidate`，不重复增版。

Git 与发布细则读取 [references/git-and-release-control.md](references/git-and-release-control.md)。

## 完成判定

只有同时满足以下条件才可称为版本完成：

- 合同范围已实现或显式移出本版本；
- 无未处置的 P0/P1，允许遗留项有负责人/策略；
- 约定自动化检查通过；
- 用户关键路径在目标运行环境验证；
- UI 风险按合同完成最小充分视觉与无障碍证据；
- 相同视觉证据没有按任务重复采集，所有复用关系和失效记录可追踪；
- 独立验收基于固定提交完成；
- 项目状态、已知问题、证据索引和版本固定点一致；
- 文档/规则/工作区知识收尾完成或明确列为待办。

不要承诺“绝对零 Bug”。使用“范围完成、无已知阻断问题、证据支持的稳定基线”。

## 资源导航

- [references/lifecycle-and-scaling.md](references/lifecycle-and-scaling.md)：入口、规模、阶段和版本策略。
- [references/conversation-orchestration.md](references/conversation-orchestration.md)：对话创建、命名、上下文和子智能体。
- [references/artifact-and-folder-governance.md](references/artifact-and-folder-governance.md)：目录、权威来源、素材和文档治理。
- [references/ui-implementation-and-runtime-acceptance.md](references/ui-implementation-and-runtime-acceptance.md)：UI 实现约束与运行验收合同。
- [references/quality-and-evidence.md](references/quality-and-evidence.md)：测试、运行验证、独立验收和证据。
- [references/git-and-release-control.md](references/git-and-release-control.md)：Git、worktree、提交、标签和版本。
- [references/project-profiles.md](references/project-profiles.md)：软件、iOS、Web、机器人和混合项目差异。
- [references/novice-intake-and-scope-control.md](references/novice-intake-and-scope-control.md)：口语需求还原、对象锁定、范围变化和绝对目标翻译。
- [references/version-governance-coordination.md](references/version-governance-coordination.md)：两个 Skill 的路径、状态、候选和归档交接合同。
- [assets](assets/)：建档、合同、交接和验收模板。
- [assets/MINIMUM_PRD.md](assets/MINIMUM_PRD.md)：没有专业 PRD Skill 或项目既有规范时的最小 PRD 回退模板。
