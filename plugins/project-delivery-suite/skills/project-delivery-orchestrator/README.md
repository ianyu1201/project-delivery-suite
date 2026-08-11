# Project Delivery Orchestrator

[![Bundle CI](https://github.com/ianyu1201/project-delivery-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/ianyu1201/project-delivery-suite/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向非专业开发者和 AI 协作团队的 Codex 项目交付总控 Skill。它把模糊想法或既有项目组织成可以审计、分阶段推进并独立验收的软件交付流程。

## 主要能力

- 判断新项目、既有项目、新版本或缺陷救援入口；
- 建立项目简报、状态、交付合同、证据和对话登记；
- 按 S0–S7 阶段门禁推进需求、设计、开发、验证、验收和冻结；
- 根据项目风险选择轻量、中型或大型交付拓扑；
- 为 UI 项目建立实现与真实运行验收合同；
- 固定 Git 基线、工作范围、交付证据和回滚路径；
- 在需要跨版本整合时调用 `consolidate-project-versions`。

它不会把一次聊天当作项目记忆，也不会把“代码能运行”直接等同于“项目已交付”。权威状态应落在项目文件、固定 Git 提交和可复核证据中。

## 特色功能：识别对话并创建 Codex 阶段会话

用户可以直接使用自然语言表达“启动这个项目”“继续当前版本”“开始下一版”“开一个新的开发会话”或“帮我独立验收”。主控会先识别项目身份、入口类型、当前版本、阶段和目标责任，再提出需要创建的会话与工作目录。

用户确认后：

- 平台支持会话创建工具时，直接创建并命名 Codex 会话；
- 平台不支持时，生成可复制的会话标题、工作目录和完整启动 Prompt；
- 在 `THREAD_REGISTRY.md` 中登记 thread ID、职责、版本、工作目录、分支、固定起点和状态；
- 前一阶段未冻结时不提前创建下游会话；
- 新版本存在多个完整目录或 PRD 冲突时，先调用 `consolidate-project-versions` 生成完整候选文件夹；
- 候选返回 `candidate_materialized` 后，才在该目录中创建开发和独立验收会话。

典型命名如下：

```text
项目｜V4｜01 产品与设计
项目｜V4｜02 开发总控
项目｜V4｜03 独立验收
```

新建干净会话不会自动递增项目版本。同一版本可以有多个阶段会话；验证失败时继续修复同一 `active_candidate`，不会因为重试从 V4 自动变成 V5。

## 与版本治理 Skill 的关系

```text
project-delivery-orchestrator
项目生命周期、阶段门禁、开发对话和独立验收
                    │
                    └── 调用 consolidate-project-versions
                        PRD/Issue/代码整合、完整下一版、历史归档
```

两者是主控 Skill 与专业 Skill 的协作关系，不是同一仓库里的主分支与功能分支。

当项目中存在多个完整版本目录、跨版本 PRD 冲突、未批准候选或待归档前序版本时，主控不会自行建立第二个候选目录，而是把版本目录治理交给专业 Skill。候选物化后，主控再接管开发对话和独立验收。

## 推荐安装

推荐安装组合包，一次获得两个 Skill：

```bash
codex plugin marketplace add ianyu1201/project-delivery-suite
codex plugin add project-delivery-suite@project-delivery-suite
```

组合包仓库：<https://github.com/ianyu1201/project-delivery-suite>

如果只安装本 Skill，项目启动、建档和交付编排仍可使用；但跨版本 PRD、完整代码候选和历史版本归档能力不可用。

## 使用示例

- “我只有一个产品想法，帮我把项目启动起来。”
- “接管这个 AI 开发的项目，判断现在能不能继续开发。”
- “为这个新版本建立 PRD、开发计划和验收合同。”
- “当前有 V1、V2、V3，请组织下一版治理流程。”
- “帮我判断这个版本是否可以发布。”

Skill 默认先读取现场、说明判断和提出方案；创建目录、修改项目、建立对话、提交或推送等动作仍受用户授权和运行环境权限约束。

## 目录

```text
SKILL.md       核心执行说明
references/    生命周期、目录、质量、Git、UI 和协作规则
assets/        项目简报、状态、交接、验收和证据模板
scripts/       只读快照与首次建档工具
evals/         场景和触发测试样例
agents/        Codex 展示与调用配置
```

## 验证

GitHub Actions 在 PR 和 `main` 更新时自动执行：

- Python 3.11 与 3.13 双版本检查；
- Skill 元数据、Agent 配置、MIT License 和 Evals JSON 检查；
- Python 编译、单元测试和 CLI 基础启动检查。

`main` 已启用分支保护，CI 未通过时不能合并。

## 安全边界

- 默认先审计、后提案，再取得写入授权；
- 不把 AI 自述完成当作验收证据；
- 不允许开发者自行批准最终交付；
- 不隐式创建分支、推送、发布、部署或执行破坏性操作；
- 遇到生产数据库、外部系统或未知副作用时进入单独受控流程。

## License

[MIT](LICENSE)
