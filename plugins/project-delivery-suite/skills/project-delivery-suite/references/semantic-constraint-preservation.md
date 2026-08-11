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

## 5. 机械门禁

使用临时 JSON 调用：

```bash
python3 <skill-dir>/scripts/validate_semantic_coverage.py <coverage.json>
```

脚本检查：必需字段、稳定 ID、authority 携带、合法处置、目标证据、保真分类、明确取代证据、边界快照、入口可见性和归档资格。`generalized` 不是等价；`unknown` 至少是 limited；高影响 unresolved 为 failed。

语义覆盖是归档前置门，不能要求“先去权威化再验证”。因此 `semantic_coverage_passed` 可以在 `historical_deauthorized=false` 时成立并给出归档预检资格；只有完成单一入口收敛、历史降权和入口约束暴露后，才可报告 `anti-drift enforced`。

只有 `semantic_coverage_passed` 才允许进入以下后续门禁：

- 按已批准的精确路径执行旧批准材料去权威化或归档；
- 发放下游设计/开发/验收启动包；
- 在历史已经降权且所有入口字段完整后报告 `anti-drift enforced`；
- 把新版本标记为可进入最终批准门禁。

## 6. 最小文档

覆盖 JSON 可以存在于系统临时目录并在验证后删除。把必要结果写入项目已有 PRD、设计规格、工程合同/ADR、AGENTS、README/PROJECT_BRIEF 和 PROJECT_STATE。只有项目已有约定或用户明确要求时才长期保存独立矩阵。

## 7. 失败处理

以下任一情况阻断归档：无目标文件、专有技术只剩泛化描述、平台/兼容/导航/数据/安全/隐私/无障碍/验收去向不明、批准决定未迁移、宽泛探索范围可能覆盖冻结结构。输出缺失 ID、来源、影响和所需 authority，不自动选择最新版本。
