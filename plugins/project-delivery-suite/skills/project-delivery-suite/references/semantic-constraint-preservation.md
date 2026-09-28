# 跨版本语义约束保真

## 1. 目的和边界

目录收敛不证明语义完整。旧批准材料去权威化前，逐条证明所有重要约束已被保留、迁移、明确取代或保持未决。自然语言抽取和等价判断由 Agent 结合 authority 完成；确定性脚本只验证结构化结果，不能用关键词扫描代替语义判断。

## 2. 约束记录

每条记录至少包含：

- `id`：跨版本稳定 ID；
- `original_text`：批准原文，不先概括；
- `source.file / source.version / source.authority`；
- `category`：产品、交互、视觉、无障碍、结构、平台、兼容、技术、数据、安全、隐私、验收等；
- `scope` 和 `impact`；
- `change_policy`：`frozen / allowed / prohibited / open`；
- `disposition`：`preserved / relocated / explicitly_superseded / unresolved`；
- `target.file / target.excerpt / target.fidelity`，或完整 supersession 决策。

`preserved` 和 `relocated` 必须给出目标文件、可核对摘录及 `exact/equivalent` 保真判断。`explicitly_superseded` 必须记录 owner、authority scope、日期、证据和 replacement。沉默、文件归档、最新版本或宽泛探索授权均不能取代旧约束。

## 3. 跨文档路由

| 约束类型 | 主权威目标 | 最小入口摘要 |
|---|---|---|
| 产品价值、对象、行为、范围 | PRD | README / PROJECT_BRIEF 指向 PRD |
| 页面、交互、视觉、无障碍 | 设计规格 | AGENTS 列出不可回归边界 |
| 平台、兼容、专有技术、实现、运行验收 | 工程合同或 ADR | README / PROJECT_BRIEF 摘要关键冻结项 |
| 下游不看到就容易犯错 | AGENTS.md | 不复制全文，只写边界和权威路径 |
| 路径、阶段、候选和门禁状态 | PROJECT_STATE | 不复制产品需求 |

一条约束可在主权威文件完整保存，并在入口文件中使用稳定 ID 和短指针。所谓“PRD 只保留 what/why”只能触发 `relocated`，不能触发删除。

## 4. 变化边界

下游启动包必须显式携带：

```text
frozen_constraints
allowed_changes
prohibited_changes
open_decisions
source_authority
```

主题、颜色、材质或动效探索默认不授权修改信息架构、页面布局、导航、入口数量/顺序/语义、组件几何、业务行为或已批准平台技术。只有稳定 ID 或明确 scope 进入 `allowed_changes` 后才可改变。

## 5. 分层验证与兼容迁移

三个层次分别记录，不能互相替代：

1. **结构检查**：字段、唯一 ID、合法处置、来源 authority、边界分类无冲突。`structure_validation_status=valid` 仅说明结构完整。
2. **引用检查**：提供 `--root <project-root>`，检查固定清单、来源/目标文件及哈希、原文与目标摘录。`reference_validation_status=verified` 仅说明本轮读取的引用一致，不证明内容获得批准。
3. **语义复核**：Agent 从权威来源逐项核对清单完整性、等价迁移、批准人权限和真实取代决定，记录审阅者、来源固定点、结果与未决项。未做独立验收时不得声称独立复核。只有前两层通过且本层无未决项时，总控才能记录 `semantic_coverage_passed`。

```bash
python3 <skill-dir>/scripts/validate_semantic_coverage.py <coverage.json> --root <project-root>
```

不提供 `--root` 时仅做结构检查，引用状态为 `not_checked`。schema v2 不再返回 `semantic_coverage_status`、`anti_drift_status` 或 `archive_allowed`；旧消费者必须改为读取上述分层结果。返回码 0 只表示请求的机械检查通过。脚本始终返回 `semantic_review_status=required`；`semantic_archive_preconditions=pending_review` 也不是归档授权。

文件引用使用相对 root 的 `file` 和文件字节 SHA-256 `sha256`；来源引用保留 version/authority，目标保留 excerpt/fidelity。明确取代的 `supersession.evidence_ref` 同样引用一份固定决策文件；其存在和哈希匹配不能证明批准有效。

覆盖输入必须引用一份**在迁移之前已从权威来源复核并固定**的清单：

```json
{
  "inventory": {"file": "existing-evidence/approved-constraints.json", "sha256": "<64位小写哈希>"},
  "constraints": [],
  "boundary_snapshot": {}
}
```

示意省略了实际约束和边界字段；清单文件的结构为：

```json
{
  "constraint_ids": ["C-PLATFORM-01", "C-DATA-01"],
  "sources": [{"file": "approved/contract.md", "sha256": "<64位小写哈希>"}]
}
```

脚本比较清单与覆盖记录的 ID 集合，拒绝整条记录遗漏、额外 ID、未登记来源、文件变动及伪造摘录。若清单自身漏掉旧要求，脚本仍无法发现；不得用同一份未经复核的抽取结果同时充当基准与验证对象。等价性和批准真实性必须回到来源确认。

纯新项目无旧批准材料时，可记录语义迁移 `not-applicable` 并说明原因，不得捏造约束来通过非空清单校验。存在旧材料但尚未盘清时不能用 `not-applicable` 绕过门禁。

语义通过后才可发放涉及历史约束的下游启动包，并进入版本批准门禁。归档还需要有效版本批准、精确移动范围授权、候选完整性验证。只有单一入口、历史降权、冻结项可发现、边界快照和语义复核均成立时，才报告 `anti-drift enforced`；任一状态不得由输入布尔值自动证明。

## 6. 最小文档与证据留存

优先引用已有固定证据和权威文件。工作中的覆盖 JSON 可临时存在，但交接/归档所依据的固定清单、来源哈希、检查结果和语义复核结论须保存在已有证据位置或可恢复 Git 固定点，不得在删除唯一证据后继续标记门禁通过。无需另建平行治理文档。

## 7. 失败处理

以下任一情况阻断归档：无目标文件、专有技术只剩泛化描述、平台/兼容/导航/数据/安全/隐私/无障碍/验收去向不明、批准决定未迁移、宽泛探索范围可能覆盖冻结结构。输出缺失 ID、来源、影响和所需 authority，不自动选择最新版本。
