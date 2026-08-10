# AI Project Delivery Suite

一个安装入口，同时安装两个职责独立、可协同工作的 Codex Skills：

- `ai-project-delivery-orchestrator`：项目预备、启动、会话编排、阶段门禁和交付总控。
- `consolidate-project-versions`：跨版本 PRD、Issue、完整代码候选和历史版本目录治理。

主控 Skill 在发现多个完整版本、PRD 冲突或待归档前序版本时，显式调用版本治理 Skill。两者不是 Git 分支关系，也不会并发写入同一候选目录。

## 安装

推荐通过 Codex 插件市场安装：

```bash
codex plugin marketplace add https://github.com/ianyu1201/ai-project-delivery-suite
codex plugin add ai-project-delivery-suite@ai-project-delivery-suite
```

也可以运行仓库内的安装脚本：

```bash
./install.sh
```

安装或升级后，请新建一个 Codex 任务，使两个 Skill 被重新加载。

## 源码与同步

组合包内的两个 Skill 是可安装快照，权威源码仍位于各自仓库：

- <https://github.com/ianyu1201/ai-project-delivery-orchestrator>
- <https://github.com/ianyu1201/consolidate-project-versions>

维护者使用 `scripts/sync_from_upstreams.py` 从本地权威仓库生成快照，并通过 `UPSTREAMS.json` 记录来源提交。不要直接在组合包副本中开发功能后忘记同步回权威仓库。

## License

MIT
