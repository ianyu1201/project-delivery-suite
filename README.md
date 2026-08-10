# AI Project Delivery Suite

[![Bundle CI](https://github.com/ianyu1201/ai-project-delivery-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/ianyu1201/ai-project-delivery-suite/actions/workflows/ci.yml)
[![Python 3.11 / 3.13](https://img.shields.io/badge/Python-3.11%20%7C%203.13-blue.svg)](.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向非专业开发者和 AI 协作团队的一站式 Codex 项目交付组合包。

一次安装即可获得项目生命周期总控和跨版本治理两项能力：从项目预备、需求澄清、开发会话、验证与独立验收，到完整下一版本生成、历史版本归档和后续迭代入口，形成一条连续、可审计的 AI 项目开发流程。

> 组合包不是把两个 Skill 粗暴合并成一份说明。它保留两个清晰职责，通过显式交接避免两个 Agent 同时修改同一个候选版本。

## 适合谁

- 不熟悉 PRD、Git、测试、发布和项目管理，但希望用 AI 完整开发软件的用户；
- 已经通过 AI 生成多个版本文件夹，开始出现 PRD 冲突、代码漂移和历史目录混乱的项目；
- 希望每次迭代都得到一份完整、可继续开发的新版本，而不是零散补丁或残缺分支的团队；
- 需要把需求、Issue、代码、验证证据和历史版本放入同一治理流程的个人开发者；
- 希望开源项目具备明确权限门禁，不让 Skill 自动删除、上传或操作生产环境的维护者。

## 特色功能：从用户对话创建 Codex 会话和版本工作区

用户不需要先理解线程、worktree、阶段门禁或版本治理术语。组合包可以从自然语言中识别用户当前想做的是：

- 启动一个新项目；
- 接管当前文件夹；
- 继续当前版本的下一阶段；
- 为当前版本开启一个干净的新会话；
- 基于已批准版本开始下一版本；
- 修复尚未通过验证的活动候选；
- 对多个历史版本进行整合和归档。

识别后，它会先复述项目、版本、当前状态、本次动作和完成标准，再给出需要创建的 Codex 会话与目录方案。用户确认后：

1. 平台支持会话创建工具时，直接创建并命名新的 Codex 会话；
2. 记录会话 ID、职责、工作目录、Git 分支、固定起点和必读文件；
3. 如果平台不能直接创建会话，则生成可复制的标题、工作目录和完整启动 Prompt；
4. 如果属于既有版本系列的增版，先让版本治理 Skill 生成完整下一版本文件夹；
5. 只有候选目录安全物化后，才在新版本目录中创建开发和独立验收会话。

例如：

```text
用户：“基于 V3 开发下一版，并帮我创建新的 Codex 会话。”
                         │
                         ▼
识别：新版本请求，而不是普通续聊
                         │
                         ▼
确认 V3 是否 current_approved，是否已有 active_candidate
                         │
                         ▼
生成完整 V4 候选目录（名称以项目实际规则为准）
                         │
                         ▼
创建并登记：
  项目｜V4｜01 产品与设计
  项目｜V4｜02 开发总控
  项目｜V4｜03 独立验收
```

这里有一个重要边界：**新建会话不等于新建项目版本**。同一个 V3 可以因为产品、开发、验收职责不同而拥有多个干净会话；只有用户确实开启新治理周期，并且不存在需要继续修复的同名活动候选时，才会生成下一版本文件夹。V4 验证失败时继续修复 V4，不会因重试自动生成 V5。

## 包含的两个 Skill

| Skill | 定位 | 主要负责 | 不负责 |
|---|---|---|---|
| [`ai-project-delivery-orchestrator`](https://github.com/ianyu1201/ai-project-delivery-orchestrator) | 主控 / 用户入口 | 项目启动、规模判断、阶段门禁、文件化状态、Codex 对话编排、开发交接、独立验收和版本冻结 | 不自行处理既有多版本目录，不与版本治理器并发写候选 |
| [`consolidate-project-versions`](https://github.com/ianyu1201/consolidate-project-versions) | 专业版本治理器 | 历史版本审计、PRD 冲突、Issue 延续、完整代码候选、版本一致性验证和全部前序版本归档 | 不负责项目全生命周期对话，不自动删除、上传、部署或访问生产数据库 |

两者不是 Git 主分支与功能分支的关系，而是两个独立维护、独立测试、协同运行的 Skill。

## 协作方式

```text
用户需求或既有项目
        │
        ▼
ai-project-delivery-orchestrator
识别项目 → 建档 → 阶段门禁 → 产品/设计/交付合同
        │
        │ 发现多个完整版本、跨版本 PRD 冲突或待归档前序版本
        ▼
consolidate-project-versions
只读审计 → 权威确认 → 单一候选 PRD → 完整下一版目录
        │
        │ 返回候选路径、来源谱系、治理周期和验证计划
        ▼
ai-project-delivery-orchestrator
开发会话 → 本地验证 → 独立验收 → 版本批准
        │
        ▼
consolidate-project-versions
一致性复核 → 全部前序版本归档 → 当前版本入口收敛
```

主控在版本治理器返回完整候选之前不会开启并行开发；版本治理器在交回候选后也不会与主控同时写入同一目录。

## 能处理什么

### 1. 从一个想法启动项目

主控会先判断入口、规模、风险和当前阶段，再按需建立：

- 项目简报与范围；
- 当前状态和下一步；
- 产品需求、设计约束和实现合同；
- UI 真实运行验收合同；
- 开发对话和独立验收对话；
- Git 固定基线、证据和交接信息。

它不会一开始就生成大量空模板，也不会在需求尚未冻结时提前创建所有开发任务。

### 2. 接管已有 AI 项目

面对已经存在的代码和文档，先做只读快照，区分：

- 已确认事实；
- 代码当前行为；
- PRD 期望行为；
- 待验证假设；
- 未解决冲突；
- 缺失证据。

测试通过、PR 已合并或 Git 工作区干净，都不会被直接推导成“产品已完成”。

### 3. 治理多个完整版本

例如当前项目有：

```text
V1/  PRD + Issue + 完整代码
V2/  PRD + Issue + 完整代码
V3/  PRD + Issue + 完整代码
```

治理后可以形成：

```text
V4/                       唯一活动版本
  最终 PRD
  未解决 Issue
  完整源代码、测试、配置、迁移、锁文件和必要资产

90_历史归档/
  V1/                     非权威历史
  V2/                     非权威历史
  V3/                     非权威历史
```

其中：

- `V4` 只是示例。实际名称沿用项目现有语言、大小写、前缀、分隔符和版本规律；
- 如果最高版本是尚未批准的活动候选，继续修复同一版本，不会因为重试再次递增；
- 新版本必须是独立、完整、可以继续迭代的项目目录，不是残缺补丁；
- 新版本批准前，上一批准版本保持当前权威，历史目录不会提前移动；
- 新版本批准后，治理系列的全部前序版本才会进入历史归档。

### 4. 处理 PRD 冲突和 AI 漂移

版本治理不会简单执行“最新版本优先”。它会区分：

- 当前授权负责人明确决定；
- 已批准变更记录；
- 最新已批准 PRD；
- 活动候选或草稿；
- 历史证据。

对于数据删除、安全、隐私、兼容性、验收等重要冲突，证据不足时保持未解决并询问用户，不会把某个版本中的沉默理解为需求已删除。

最终活动版本只保留一份权威 PRD。旧 PRD 跟随历史版本保留，但明确标记为非权威，避免后续 AI 把历史需求重新带回开发。

### 5. 延续 Issue，而不是永久堆积

- `resolved-and-verified`：不再进入下一版本活动清单，但历史证据仍保留；
- `changed-not-verified`、`open`、`deferred`、`reopened`：使用稳定 ID 延续到新版本；
- 改变产品行为的 Issue：先更新 PRD，再进入实现和关闭；
- 没有未解决问题时，不会为了形式创建空 Issue 文件。

### 6. 管理目录和历史

Skill 优先复用项目已有结构。没有现有约定时，可以提议 NOTE1 风格的编号式全生命周期目录：

```text
00_项目治理/
01_产品/
02_设计/
03_工程/
04_技术决策/
05_独立实验/
90_历史归档/
```

该结构是建议，不是强制模板。只创建实际有内容的分类，并优先使用用户项目当前可理解的文件夹名称。

## 空间治理原则

组合包会识别以下可再生候选，但不会把它们简单集中到一个共享目录：

- `node_modules` 和包管理器可恢复依赖；
- 虚拟环境；
- 缓存、日志、覆盖率和构建中间文件；
- 可以依据确定工具链重新生成的输出。

判断可再生前，需要验证依赖声明、锁文件、工具链、构建脚本和恢复方式。数据库、uploads、用户数据、密钥、模型文件和未知非 Git 内容默认受保护。

历史版本默认只移动到归档目录。同一磁盘内归档不会释放空间；如需释放空间，由用户在治理完成后自行选择归档内容并移入操作系统废纸篓。本组合包不会执行该操作，也不会清空废纸篓或永久删除。

## 安装

### 前提

- 已安装支持插件命令的 Codex CLI；
- 本机可以访问 GitHub；
- Git 市场安装需要本地 Git 环境。

### 推荐：通过插件市场安装

```bash
codex plugin marketplace add ianyu1201/ai-project-delivery-suite
codex plugin add ai-project-delivery-suite@ai-project-delivery-suite
```

这只安装一个插件，但插件中同时包含两个 Skill。安装完成后请新建一个 Codex 任务，让新 Skill 被加载。

### 使用安装脚本

```bash
git clone https://github.com/ianyu1201/ai-project-delivery-suite.git
cd ai-project-delivery-suite
./install.sh
```

安装脚本只调用 Codex 插件市场和插件安装命令，不需要管理员权限。

### 检查安装结果

```bash
codex plugin list --json
```

输出中应出现：

```text
ai-project-delivery-suite@ai-project-delivery-suite
```

## 升级和卸载

刷新 GitHub 市场快照：

```bash
codex plugin marketplace upgrade ai-project-delivery-suite
```

卸载组合插件：

```bash
codex plugin remove ai-project-delivery-suite@ai-project-delivery-suite
```

升级或重新安装后，请新建 Codex 任务，避免旧任务继续使用已缓存的 Skill 内容。

## 如何开始使用

可以直接对 Codex 说：

- “我只有一个产品想法，帮我把项目完整启动起来。”
- “接管当前文件夹，判断项目现在处于哪个阶段。”
- “当前有 V1、V2、V3，整合 PRD、Issue 和代码，生成完整下一版。”
- “V3 代码不满足最终 PRD，生成一个可以继续迭代的完整候选。”
- “新版本批准后，把全部前序版本整理到历史归档。”
- “检查历史版本的可再生内容，但不要删除任何文件。”

Skill 会先说明已确认事实、推断、缺口和拟执行动作。默认调用只授权读取，不自动授权创建候选、移动目录、运行有副作用的脚本或发布到远程。

## 权限与安全边界

组合包不会因为被调用就自动执行以下操作：

- 删除文件、移入废纸篓或清空废纸篓；
- 覆盖已有候选或原地修改已批准历史版本；
- 创建 GitHub 仓库、修改可见性、提交、打标签、上传或推送；
- 部署、发布、连接共享/生产数据库或执行生产迁移；
- 把环境中的密钥传入未知项目脚本；
- 使用“最新版优先”静默裁决重要需求冲突。

写入项目前会明确阶段、精确路径、变更、排除项、验证和回滚方式。远程发布、外部副作用和生产操作必须进入单独的授权流程。

## 完成状态不是一句“全部完成”

执行过程中会报告最窄、可核实的状态，例如：

- `audit complete / limited / unsupported`；
- `awaiting naming / authority / requirement decision`；
- `candidate incomplete / materialized`；
- `validation pending / failed / passed`；
- `version approval pending / approved`；
- `archive pending / organized`；
- `anti-drift enforced / limited`；
- `remote recovery pending / verified / declined`。

只有 PRD、实现、验证、版本批准、活动 Issue 和历史归档均达到对应门禁时，才会宣称治理周期完成。

## 仓库结构

```text
.agents/plugins/marketplace.json          Codex 插件市场入口
plugins/ai-project-delivery-suite/
  .codex-plugin/plugin.json               插件清单
  skills/
    ai-project-delivery-orchestrator/     主控 Skill 快照
    consolidate-project-versions/         版本治理 Skill 快照
scripts/
  sync_from_upstreams.py                  从权威仓库同步 Skill
  validate_bundle.py                      组合包结构校验
UPSTREAMS.json                            上游仓库和精确提交
install.sh                                安装脚本
```

## 源码权威与贡献方式

组合仓库是经过验证的分发快照。两个 Skill 的权威开发仓库分别是：

- <https://github.com/ianyu1201/ai-project-delivery-orchestrator>
- <https://github.com/ianyu1201/consolidate-project-versions>

功能修改应先进入对应权威仓库并通过其 CI，再通过 `scripts/sync_from_upstreams.py` 更新组合包及 `UPSTREAMS.json`。不要只修改组合包中的副本，否则下次同步时会被权威版本替换。

## 测试与质量门禁

每个 PR 和 `main` 更新都会在 Python 3.11、3.13 上执行：

- 插件清单、市场入口、MIT License 和上游提交记录校验；
- 两个 Skill 的 Python 编译检查；
- 主控脚本单元测试；
- 版本审计器单元测试；
- 三个 CLI 的 `--help` 启动检查。

`main` 已启用分支保护：必须通过 PR，所有 CI 检查成功后才能合并；管理员同样不能绕过，禁止强制推送和删除默认分支。

## 常见问题

### 用户还需要分别下载两个 Skill 吗？

不需要。安装本组合插件后，两个 Skill 会同时出现在插件缓存中。单独仓库主要用于权威开发、审计和独立发布。

### 会自动把项目上传到 GitHub 吗？

不会。是否使用 GitHub、GitLab、NAS 或其他离设备恢复方案由用户决定。任何远程创建和上传都需要明确目的地与数据范围授权。

### 归档后会自动释放磁盘空间吗？

不会。同盘归档只是整理。用户可以在确认恢复路径后手动删除选定历史内容，本组合包不会代替用户清理。

### 是否强制使用 V1、V2、V3？

不会。优先识别项目自己的命名规律；没有规律时才把该格式作为可选建议。

### 是否适合直接操作生产项目？

可以治理生产项目的本地副本和文档，但不会部署、访问生产数据库或执行生产迁移。这些动作需要独立、受控的专业流程。

## License

[MIT](LICENSE)
