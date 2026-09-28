# Project Delivery Suite 0.8.0 两批改进交付

状态：两批本地实现与确定性检查完成；真实模型行为评测待运行。GitHub 尚未推送，未安装到当前 Codex，未启动子代理。

## 版本与交付

- 基线：576e04aeddcfdd98b0365f67645fc9214c74def9（上游 main，0.7.0）。
- 工作分支：improve/delivery-governance。
- 第一批：6b0d796，路径边界、授权继承与分层证据检查。
- 第二批：40e20d45b5d8e03983bf2500e56141b584954f17，轻量流程、证据继承、行为评分与 0.8.0 版本同步。
- 独立工作副本：`work/project-delivery-suite-review`；工作区干净。
- 完整源码包：[project-delivery-suite-v0.8.0.zip](project-delivery-suite-v0.8.0.zip)。
- 顺序补丁：[第一批](project-delivery-suite-v0.8.0/0001-fix-enforce-path-boundaries-and-distinguish-evidence.patch)、[第二批](project-delivery-suite-v0.8.0/0002-feat-add-local-delivery-and-auditable-behavior-evalu.patch)。

源码包不含 .git。补丁可在基线仓库的独立分支上依序使用 git am 应用；不要向已经含这些提交的工作副本重复应用。包内 install.sh 仍是 GitHub 安装入口，在上游发布前运行它会取得上游现有版本，不是本地 0.8.0 候选。

## 第一批

1. scaffold_delivery.py：完整计划预检、拒绝中间符号链接/普通文件冲突/越界路径；写入采用 dir_fd 与 O_NOFOLLOW 逐层打开。平台不支持安全原语时拒绝 apply，保留只读预览。预检后 I/O 失败可能留下已创建的空目录，明确报错，不自动删除或假称原子回滚。
2. validate_semantic_coverage.py：输出 schema v2，区分结构 valid/limited/invalid 与引用 not_checked/verified/failed；不再输出自动语义通过、防漂移保障或 archive_allowed。
3. --root 检查已固定约束清单、来源与目标文件哈希、来源原文及目标摘录；清单与覆盖记录的 ID 集合必须一致，不能整条遗漏或追加来源不明的约束。
4. 语义等价、清单自身完整性和批准真实性仍需来源复核；返回码 0 不能用作业务批准。文档说明旧字段兼容迁移。
5. 明确执行请求与既有授权连续有效，仅实质范围/权限/风险变化补充确认；只读请求保持只读。

## 第二批

1. SKILL.md 从 147 行收敛为 57 行。入口保留共享边界，按目标加载版本、UI、证据和会话规则。
2. 增加当前会话内的局部交付；按需文档和独立验收。无 UI 不生成 UI 合同，无新任务不生成登记表；正式批准仍由授权责任人决定。
3. 跨提交视觉证据复用要求可核查的输入与环境不变，保留原 capture commit/build、目标提交、比较依据和复核记录；不明影响必须重采。
4. PATCH 按恢复既有合同判断，不因修复改变错误的可观察行为就强制 MINOR。
5. 七个行为场景：只读审阅、授权实现、局部交付、整条约束遗漏、伪造批准、恢复既有候选、无影响截图继承。
6. 新评分器核对原始日志哈希/摘录、观察事件与预期及允许写入范围，报告确认次数、文档数量和可用成本。按模型/Skill 提交/配置分组；合成轨迹不计入真实模型成功率，拒绝重复运行 ID。
7. 包校验新增相对资源链接和用例夹具路径检查，去掉对特定指令句子的机械匹配；修正 install.sh 的双 Skill 遗留文案。

## 硬约束保留核对

| 原约束 | 处置 | 现役位置 |
|---|---|---|
| 最新代码/目录/绿色测试不是批准 | 保留 | SKILL.md 边界 2；governance-model.md |
| 单一现役 PRD；what/why 与工程合同分开 | 保留 | SKILL.md 边界 3；semantic-constraint-preservation.md |
| 专有技术、平台兼容、最低系统等硬约束不得泛化丢失 | 保留 | semantic-constraint-preservation.md；原语义测试夹具 |
| 四类约束处置及稳定 ID | 保留并增强引用核验 | SKILL.md 边界 4；语义文档与校验器 |
| 独立验收与版本批准分开，开发者不得自批 | 保留；局部任务未执行独立验收须标明 | SKILL.md 边界 2；quality-and-evidence.md |
| 当前批准版/候选版分开；失败不增版、不覆盖历史 | 保留 | SKILL.md 边界 5；版本治理与交接 |
| 候选必须完整；保留代码/配置/迁移/测试/必要资产；排除秘密和运行数据 | 保留 | governance-model.md 第 4、6 节 |
| Git 元数据不随文件复制；沿用 Git/worktree 拓扑 | 保留并明确 | governance-model.md 第 4、7 节 |
| 视觉探索不改变导航、入口数/顺序、几何、图标语义、文案、业务与批准技术 | 移至专项全文，入口保留路由 | ui-implementation-and-runtime-acceptance.md 第 3 节 |
| 无专业 PRD Skill 时使用内置回退 | 保留 | SKILL.md 边界 3 |
| 无授权不外传；不在 Skill 内做生产/共享数据库/删除/Trash | 保留 | SKILL.md 边界 1、6；governance-model.md |
| 归档须批准、路径授权及语义通过，同盘不释放空间 | 保留 | SKILL.md 边界 6；版本与语义文档 |
| 不承诺绝对零 Bug；证据对应具体结论 | 保留 | SKILL.md 边界 7；quality-and-evidence.md |
| 每次写入前重新确认 | 按本次批准建议调整为授权继承 | SKILL.md 边界 1；agents/openai.yaml |
| 小任务强制多会话/全套文档 | 按本次批准建议调整为按风险裁剪 | lifecycle-and-scaling.md |
| 最终提交改变即强制重拍 | 按本次批准建议调整为有证据的影响分析 | quality-and-evidence.md；证据模板 |

## 验证证据与限制

本机 macOS / Python 3.9.6：

- 第一批回归 65 项通过；第二批最终代码回归 74 项通过。
- validate_bundle.py、validate_codex_release.py、Skill quick_validate.py 通过。
- 全部 Python 文件内存编译、5 个 CLI --help、bash -n install.sh、git diff --check 通过。
- 最后的文档约束补齐后重做资源链接、Skill 结构和差异检查；没有代码变化，未重复整套测试。
- 仓库 CI 的 Python 3.11/3.13 矩阵尚未在远端运行。
- 没有执行真实模型行为评测，也没有声称新模型或 0.8.0 的真实成功率提升。当前侧会话禁止子代理；已经交付可用于主任务后续执行的用例、记录协议和评分器。
- 固定哈希不能证明批准者身份，评分器不能认证采集日志或观察分类；这些仍需可信来源及独立复核。
- 不将编译/单元测试当作产品独立验收或正式版本批准；本包为可评审候选。
