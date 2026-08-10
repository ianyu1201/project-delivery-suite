# Consolidate Project Versions

[![Bundle CI](https://github.com/ianyu1201/ai-project-delivery-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/ianyu1201/ai-project-delivery-suite/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向 AI 开发项目的跨版本治理 Codex Skill。它审计现有版本目录，整合 PRD、未解决 Issue 和完整代码，生成一份可继续迭代的下一版本；新版本批准后，将该系列的全部前序版本移入项目的历史归档。

## 解决的问题

典型现场如下：

```text
V1/  PRD + Issue + 完整代码
V2/  PRD + Issue + 完整代码
V3/  PRD + Issue + 完整代码
```

治理目标不是把旧文件直接拼接，也不是只创建一个 Git 分支，而是：

```text
V4/              唯一活动版本：最终 PRD + 活动 Issue + 完整代码
90_历史归档/
  V1/            非权威历史
  V2/            非权威历史
  V3/            非权威历史
```

上面的名称只是示例。Skill 优先识别并沿用项目现有的语言、大小写、分隔符、目录层级和版本规则；没有可靠规则时才向用户询问，不会强制使用 `V1/V2/V3` 或 `90_历史归档`。

## 主要能力

- 区分 `latest_observed`、`current_approved` 和 `active_candidate`；
- 识别跨版本 PRD 冲突，不使用简单的“最新版优先”；
- 建立一份候选 PRD，并记录授权、来源和被替代行为；
- 延续 `open`、`deferred`、`reopened`、`changed-not-verified` Issue；
- 从已批准代码谱系生成独立、完整、可继续开发的下一版本目录；
- 逐条验证 PRD、Issue、代码、测试、配置、迁移、锁文件和资产；
- 新版本批准后，归档治理系列中的全部前序版本；
- 识别 `node_modules`、缓存和构建中间物等可再生候选，但不自动清理；
- 可选评估 Git/GitHub 等离设备恢复方案，但不自动上传。

## 与主控 Skill 的关系

`ai-project-delivery-orchestrator` 是用户入口和项目生命周期总控；本 Skill 是版本目录治理的专业执行器。

协同时，本 Skill 负责命名、PRD/Issue 整合和完整候选物化，然后把候选路径、来源谱系、治理周期、PRD 状态和验证计划交回主控。主控负责后续开发对话和独立验收；本 Skill 最后复核一致性并归档全部前序版本。

两个 Skill 不允许并发修改同一候选目录。

## 推荐安装

推荐使用组合包，一次安装主控和版本治理能力：

```bash
codex plugin marketplace add ianyu1201/ai-project-delivery-suite
codex plugin add ai-project-delivery-suite@ai-project-delivery-suite
```

组合包仓库：<https://github.com/ianyu1201/ai-project-delivery-suite>

本 Skill 也可以独立调用；独立调用时仍然遵守相同的审计、授权、候选和归档门禁。

## 使用示例

- “整合 V1、V2、V3 的 PRD 和代码，生成完整 V4。”
- “V3 的代码不满足最终 PRD，生成一个可以继续迭代的完整下一版。”
- “保留当前版本，把全部前序版本整理到历史归档。”
- “检查旧版本中的 node_modules、缓存和 uploads，告诉我哪些可再生。”
- “PRD 对订单删除方式存在冲突，先帮我整理需要裁决的内容。”

默认从只读审计开始。调用 Skill 本身只代表允许检查，不代表允许创建候选、移动版本、上传远程或执行项目脚本。

## 归档与空间说明

- 历史版本默认归档，不自动删除；
- 同一磁盘内移动到归档文件夹只改变组织方式，不会释放空间；
- 用户如需释放空间，应自行选择归档内容并移入操作系统废纸篓；
- Skill 不移动内容到废纸篓、不清空废纸篓，也不永久删除；
- 数据库、uploads、用户数据、秘密和未知非 Git 内容默认受保护；
- 可再生目录必须先验证锁文件、工具链和恢复方式，不能只凭目录名判断。

## 目录

```text
SKILL.md       核心治理流程
references/    权威、候选、归档、Git 和安全模型
assets/        无现有项目规范时使用的候选文档模板
scripts/       只读版本与存储审计器
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

- 不覆盖已有候选，不原地修改已批准历史版本；
- 不静默裁决 PRD 的行为、数据、安全、隐私或破坏性冲突；
- 不自动创建远程、提交、打标签、上传或推送；
- 不部署，不访问共享或生产数据库；
- 任何不完整扫描、未知授权、符号链接、跨文件系统或未分类数据都保持未解决状态。

## License

[MIT](LICENSE)
