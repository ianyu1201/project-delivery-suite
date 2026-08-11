# <PROJECT> — Agent 规则

> 只记录下次 Agent 不看到就会犯错的规则、命令和边界；不复制 PRD。

## 项目身份

- 项目根目录：<absolute project root>
- 当前版本：<active version>（<candidate/current>）
- 当前阶段：<S0-S7>
- 状态权威：PROJECT_STATE.md
- 当前 PRD：<project-relative active PRD path>
- UI 合同：<project-relative active UI contract path>

## 不可违反的边界

- 修改当前版本、阶段或项目根时同步更新本文件、README、PROJECT_STATE、活动 PRD/UI 合同和会话登记。
- 项目移动后旧绝对路径立即失效；重绑定并通过 status gate 前不创建下游任务。
- 用户授权不能替代验证、独立验收、固定点或证据文件。
- 相应 `validate_project_state.py` gate 未通过时，不交接、不批准、不归档。
- 不创建远程、上传、发布、部署、访问生产数据库、删除或移入 Trash，除非另一个专用流程取得对应授权；本 Skill 本身不执行这些动作。
