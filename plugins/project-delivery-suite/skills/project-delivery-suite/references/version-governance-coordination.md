# 版本治理协作合同

## 1. 职责边界

`project-delivery-suite` 是唯一 Skill 和用户入口。其项目交付总控模块负责项目建档、阶段门禁、Codex 对话、开发编排、独立验收和项目状态。

同一 Skill 内的版本治理模块独占以下决定和动作：

- 识别 `latest_observed / current_approved / active_candidate`；
- 沿用项目规则确定下一版本名称；
- 建立不覆盖的完整候选版本目录；
- 在失败后继续修复同一 `active_candidate`；
- 新版本批准后将治理系列的全部前序版本移入历史归档。

总控模块不得并行创建第二个候选目录，也不得在版本治理模块尚未返回候选路径时启动开发对话。内部路由不加载第二个 Skill ID，但必须明确报告模块切换和交接状态。

## 2. 五类路径身份

| 字段 | 含义 |
|---|---|
| `workspace_root` | 项目容器，容纳现役区域和历史归档 |
| `active_version_root` | 当前完整活动版本或当前单仓库工程根 |
| `archive_root` | 历史、非权威内容的归档根 |
| `repo_root` | 实际 Git 仓库根，可与前两者之一相同 |
| `staging_root` | 未提升的唯一候选暂存目录 |

路径必须是绝对路径并记录当前 Git/worktree 身份。未分清“发布文档版本目录”和“完整项目版本目录”时禁止写入。

## 3. 目录拓扑

先沿用项目现有结构。无规则时向用户提议，不自动强制。

### 完整版本快照模式

每个版本是可独立理解和继续开发的完整目录。例如 V4 批准后：

```text
<workspace_root>/
├── 00_项目治理/
├── V4/                       # 唯一活动完整版本
└── 90_历史归档/
    ├── V1/
    ├── V2/
    └── V3/
```

### 编号式单仓库生命周期模式

参考 NOTE1 的分层逻辑，可以使用：

```text
<workspace_root>/
├── 00_项目治理/              # 入口、交接、索引和状态
├── 01_产品/<version>/             # PRD、范围和待决策项
├── 02_设计/<version>/             # 设计规格、候选与确认基线
├── 03_工程/                       # 唯一现役代码、测试和验收证据
├── 04_技术决策/                  # 已接受的长期 ADR
├── 05_独立实验/                  # 只在真有独立实验时存在
├── 90_历史归档/<version>/         # 非现役文档、证据或快照
├── AGENTS.md
└── README.md
```

编号表示生命周期和阅读顺序，不表示每个目录都必须预建。源码只有一份现役路径，旧代码由 Git 固定点或经确认的历史快照恢复。

在此模式中，“完整候选”是从批准 Git 基线建立的隔离完整 worktree/staging，而不是第二个永久现役源码目录。总控在该隔离候选中开发和验收；版本批准后再依项目 Git 策略把候选固定为唯一现役代码路径。分支或 worktree 自身不等于批准，也不能代替完整候选内容验证。

## 4. 权威文档和状态

- PRD 是唯一产品需求权威。
- `PROJECT_STATE.md` 只保存路径指针、阶段、状态和下一步。
- 版本章程或交付合同引用 PRD，不复制产品范围。
- 没有未解决问题时不创建空 Issue 清单。

统一状态顺序：

```text
draft
→ active_candidate
→ validation_passed
→ accepted
→ version_approved/current
→ predecessors_archived
→ released/live_verified   # 仅适用时
```

PRD 批准只授权产品范围。`accepted` 只证明独立验收结论。只有单独的版本批准才能设置 `current_approved`并触发全部前序版本归档。

## 5. 交接字段

版本治理每次返回并由总控写入现有 `PROJECT_STATE.md`：

```text
workspace_root
active_version_root
archive_root
repo_root
staging_root
topology
latest_observed
current_approved
active_candidate
source_lineage
governance_cycle_id
prd_status
validation_status
acceptance_status
version_approval_status
archive_status
anti_drift_status
semantic_coverage_status
constraint_coverage_evidence
boundary_snapshot_status
```

不为这些字段另建一份治理文档。

## 6. 严格时序

1. 总控完成入口、范围和项目身份锁定。
2. 版本治理只读盘点，返回拓扑、当前批准版本和命名提案。
3. 版本治理盘点旧批准硬约束，完成跨文档路由并运行语义覆盖门禁。
4. 用户或授权产品负责人批准唯一候选 PRD；其他工程/设计约束由对应 authority 文件承载。
5. 版本治理在唯一 staging 中物化完整候选，通过 manifest 后提升并返回 `candidate_materialized`。
6. 总控只在 `semantic_coverage_passed` 且边界快照附带后启动开发、测试和独立验收。
7. 失败时修复同一候选，不增版。
8. 独立验收通过后由授权者单独批准版本。
9. 版本治理只在版本批准且语义覆盖仍通过后归档全部前序版本。
10. 总控更新全局指针、下一周期起点和对话状态。

历史归档只负责组织和去权威化，不声称释放空间。本 Skill 的两个模块都不移入 Trash、不永久删除、不清空废纸篓；用户需要释放空间时自行处理已归档内容。
