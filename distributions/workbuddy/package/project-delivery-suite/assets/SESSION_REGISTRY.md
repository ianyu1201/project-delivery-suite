# <PROJECT> WorkBuddy 任务/对话登记表

> 项目根：<absolute project root>
> 当前活动版本：<version>
> 状态权威：PROJECT_STATE.md
> 项目移动后先重绑定全部绝对路径并通过 status gate；旧启动包立即失效。

| 标题 | 平台真实 Task ID（如有） | 阶段/职责 | 状态 | 工作目录 | 分支 | 起点 SHA | 交付 SHA | 必读入口/启动 Prompt | 创建/关闭日期 |
|---|---|---|---|---|---|---|---|---|---|
| | | | planned / active / handed-off / accepted / archived | | | | | | |

## 规则

- 只在上游交付物冻结后创建下游对话。
- 每个对话只有一个主要责任。
- 对话完成后把结论写入仓库，再登记交付 SHA。
- 独立验收不得直接继承开发者结论。
- WorkBuddy 5.3.11 当前未验证到可调用的任务创建 API；默认只记录 planned 项和启动 Prompt，由用户手动新建任务，不填写虚构 ID。
- 开发启动包发放前必须通过 `validate_project_state.py --gate handoff`。
- 启动包中每个绝对路径必须在生成时存在；不要复制已移动项目的旧路径。
