# 0.8.0 交付副本只读审计

核对提交：`6b0d7962652452b3d274c37da7948ba7fd672aaa`、`40e20d45b5d8e03983bf2500e56141b584954f17`。仅核对指定副本与 Git 对象；未删除或修改副本，未修改原有 branding avatar。

ZIP 共 52 个文件，全部与 HEAD 同路径 Git blob 完全一致：True。HEAD 中未包含于 ZIP 的路径：0。

## 逐文件哈希与来源

| ZIP 相对路径 | SHA-256 | Git blob（HEAD 同路径） |
|---|---|---|
| `.agents/plugins/marketplace.json` | `a41d22e7dfe661d5688f7a6a75a8d5a593703e0277ad8c21f987d34793d88da0` | `9973f6bb70f67f89599118374db4762f31525ffd` |
| `.github/workflows/ci.yml` | `cc4543ea5b9b3982642a997fb3239ad7d5c439a8e02b18beffad248dd77ebe0e` | `b298be8e960a25dc898a772633d7a420be27cc57` |
| `.gitignore` | `60c9bdd905fcf45ac485c680d32e9773962cf061b6f041dcddd033911558a672` | `b908d4cbe37ccea3388a2f308595ae63a255755d` |
| `LICENSE` | `4f267d5337f2e26d215b61f4759e76d5f53a732534669c70dbc8cb3451c19611` | `cc2a06fecb29096083c2d6415c12ca6f0915b068` |
| `README.md` | `af34b77526a4eb1033f5336fab060a1b19a3540d7c5862af339b62bf0212f904` | `fbabf2b879482a25fee42f9cd82c3a410abbe569` |
| `VERSION` | `a66780da23103beaf12432b418508966b31a2a3a787f9468a5b6cdaa8667c1ef` | `a3df0a6959e154733da89a5d6063742ce6d5b851` |
| `install.sh` | `f3b813ae6b6ccb9518ac587eb095c748a5af567daddcfc06c03285187adf350f` | `bfa833e3239223e36cf0df2e16a9350108d23b60` |
| `plugins/project-delivery-suite/.codex-plugin/plugin.json` | `1c578a620adae9a31a732b37aac44ea799cc8ae1fa67528dfc4e4a9561733b02` | `b9634b25edc8ea05982b7e11627ccd78d92d60f3` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/.gitignore` | `997d3b4df2681c5f1200aa84407aa89b45e6a7cf691a99e8b3cef6f9c77246b5` | `269fbc1d94668a265d0a6cbcd9bb7b533b3d641e` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/LICENSE` | `ef6fdff085828682eed07c44271cdc62dd16b9df2b760bc5356f08f3d60eba82` | `088facc70019a0f815dc30a33e9b3c78bfc745c4` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/SKILL.md` | `d36badd35302fea058b7d3239c6fedb7063b89469fbf8da7c45b59cac164578a` | `cdb3d0d0d41e2fa7ba43830a5a3b356c6e3b2fe9` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/VERSION` | `a66780da23103beaf12432b418508966b31a2a3a787f9468a5b6cdaa8667c1ef` | `a3df0a6959e154733da89a5d6063742ce6d5b851` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/agents/openai.yaml` | `1bc55075d1c9d734b764ec3e29769996f4b5b49e9ebd6bc71be40fadda19663a` | `a72ffbda020d5dd66155db5ae7f54fbe71b6f502` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/ACCEPTANCE_REPORT.md` | `07a20b2e4df39ccefa3de504f7425c3b4e4c6968a793b52eed0e3bb082171245` | `667b128ee67f3ed563c87d1fade57caf47c97bfb` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/DEVELOPMENT_HANDOFF.md` | `7c424ca11479efaa2d36b7977a083f3e68e728c816b667c9a15002f25e2ad393` | `9cda0da5d8a4270ea36d3f2b77b333b9cc19e9f9` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/EVIDENCE_MANIFEST.md` | `8d9421785acc6619018aeda146f9460f258df433c03c7b434710139dd7cfa65f` | `a5d984da26e0cc45e231262098cf861c23f1a881` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/MINIMUM_PRD.md` | `596aff906e98ec4c19433f311fb288b0b6ecd4402f9be52d5b385b096c24221b` | `ca491e92324fce989ad59ae427a3e10e99c1a981` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/PROJECT_BRIEF.md` | `e7f6d6e25185cc529f47705ac8401ae921ba5b72633dcc547e268aadab17cfd0` | `4b10fc40e35ea2a49e7da630b46a3627c42594cf` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/PROJECT_STATE.md` | `2e9b0d7e09271a561f6832bbce6feaee46ec478818029bed3c134ef5227fc87e` | `dcc3e42514c84f7f8b02f774044fb4c1aad59cc3` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/RELEASE_CHARTER.md` | `af3eb9f6ef1ef3271d98dde8ce8d779f002648104e9b9792e3e367b92bd7a778` | `834761933c141e291d0c4f8c3bd3d26899d9cc10` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/THREAD_REGISTRY.md` | `ef9174f9f2bdddf336e5d7b6321eadf7ef26fc7e5685dec3d4ea512bf6d1910e` | `94002c302c9dcf8782e4a6ee929d810944360c86` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/UI_IMPLEMENTATION_AND_RUNTIME_ACCEPTANCE_CONTRACT.md` | `7a20ffbffaf1dd44eb75d102a765e3fc12e057cf6c494516b9f0ba3d0dcf0f6c` | `c35b66ca916365d3a76918ece70cd7411d8b3c31` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/assets/current-version-docs-template.md` | `5772a7c3025228591c44146ce98426821293e01b8ac43488742f5b2415616493` | `6bbf51153570b4e9e98fabf4b9b481cd940663a6` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/evals/behavior-cases.json` | `f2a0c25cdce5a2955015f515aabcbea1c855ceecfbc654e2506e1b85bdcdb53c` | `2c2f3fab64aeb66a53ea9892f5eae1b465f0ed76` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/evals/scenarios.json` | `5d4eb52edd2508c9762e6351c2c4adde16db61c5882de3ab26fd395390fbb30a` | `d5f3f38df80fe615d0fb2255400c2b2860993ddb` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/evals/trigger-cases.json` | `7b7c8ed5944f1ed9273fbb3983372cc8b50eda58a88c775fdd6eeeee60e33439` | `8abe09a50b82ec7bbca843c76c886dcc3a9a0786` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/evals/version-scenarios.json` | `c57a7d2c73cd2bb2c1b48a576c1058086b2e02bac8d4eacd8ff257673c64286e` | `53de9546257e5b981f6af2a6a62a831e3291ff60` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/evals/version-trigger-cases.json` | `7a8904efe79b6f6ebe1a21faa6006b80665a485cf92f8632e7d5ae6388f5e402` | `16946edd3d51f9efef1b988efa594bc05834abbd` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/artifact-and-folder-governance.md` | `01d5fae9b1f0ab427200ce536cf1b2513870d3fc24ce399faca5528316eb26a5` | `616bdb58c051d8134b40a0f17dee5e5958b636ad` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/behavior-evaluation.md` | `4f93a095b9e359f86857c0d370b73f334626663d198d74d3b9252f730de20cc1` | `bddf7cef16ab987a244cadb7b2ae628cdeac2a89` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/conversation-orchestration.md` | `37d195072a6f6a685935905dc3b33866986b7f82f60f5835265e431b9985466d` | `3b63016cb0472fbe8b44c38fa068592fdd698c50` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/git-and-release-control.md` | `9498969e159b133b117855317447858090b9845ab08057ebb146c7f49a4ab0fe` | `d49c49c03a2fee8a49b565240bf29ebdf1e9899b` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/governance-model.md` | `3e6147b97ee151a84c5a738bc4f04ded997fc2bf38fd7fcd9a8b51b5d4d4bb3e` | `a0b8bdd39167a33183257d27d7c24e00e20daab3` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/lifecycle-and-scaling.md` | `4cc45def40977b0b34feed7b13d6f4980886c14fbced2f137b424a576a6ca296` | `8992b594fd0d00dbe01ce8915c4be88b2b37a08c` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/novice-intake-and-scope-control.md` | `cdf3aff9f7cc3923c991b1ccc51a8b02c0077cd87fc45e2d5ee99f226a64c9f3` | `90924d18b1d00368acbd7a64f61e1c908504d358` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/project-profiles.md` | `abf34ff1544dee0639b8235c78d34a7b28bc9e3dfbefc8a3ebdd1659cb85ee90` | `ba8ad66b6b7eb2c5c8afa0ca6eb63ccbf98b6f32` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/quality-and-evidence.md` | `05f059fcf0de426cb417bff414f05014c209b5fa0018926c0ad717b34833870b` | `56ed11c9cad9c8ff454868ca7d92398bf7aa3a13` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/semantic-constraint-preservation.md` | `493dbe403737b26eb2ba37507e735b7c2f6a276799ec96aa29ad4a8d1d0fcc2d` | `1049bc67f3912c856b5465939ebd243afdf1a453` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/ui-implementation-and-runtime-acceptance.md` | `ca3a8b1cf8cd761b9adb7b9f6fdfba9d367dada316497a394503ff90e65e1d96` | `91ddec1a458f424dacfd6bf025353654ce51295e` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/references/version-governance-coordination.md` | `25de85e88777c48a8b7315256fed071465c769e227fc16ea1c7ef80f3bec0530` | `b4a8eb4c32e256aa6537bf9d02ffbdeb417f82cc` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/audit_versions.py` | `ee5fd92e02d10b4e0558dc7001d31e2618e16b4c07969a3704a91498157af061` | `e093651e5600596d02d2760fecb58c32cb860ca7` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/evaluate_behavior.py` | `d59093cf1a62bf802f9b52976b7a1933f05b681661289032fb7c8683e9491f44` | `e39f121db6c2fc58e2b956f1e189725549b5a50a` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/project_snapshot.py` | `70472262146292078a706108c2a776481d7dac594f421baee9ac2161b033a5e0` | `b9f353645fb5d3a9705eba1a31f65f9451a46eaa` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/scaffold_delivery.py` | `fd5bc8bca365cc31fa8808543c30ef228f1907b016d8326ea3ab63c5c4064683` | `345825c8cc1f450b28888e25aa93e4555defb529` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/test_audit_versions.py` | `568f0be6cbe346a1bebf36db4b038015dfde60833b5e026d7c32b9b8f0603793` | `5286e9e6fa79bff837c49b752d5770c54882f1c5` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/test_behavior_evaluation.py` | `4f83efe3172bf61cc23f1cea35deb573d04c747701d142bdab5605322c2405de` | `b9a9874c32a8abc5b2044c11f0914471f0198fcc` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/test_orchestrator_scripts.py` | `bf386e40e8ba25e4eba7f83fa13ef0eb067f2906a7fe01de9d383578b918c1f9` | `bdeb13ce3aef079f6d23ff483b3ab6e48fe2c565` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/test_semantic_coverage.py` | `0700611de83604fb7b78e74a62951b77826a1eba88321a06863ba6fcd060ec2e` | `504b7def12a0a1896419a5643917ab546dd7eb48` |
| `plugins/project-delivery-suite/skills/project-delivery-suite/scripts/validate_semantic_coverage.py` | `c0947294f5904543b095edc75a4d452ed7881bf09e6cea7eba52163a21f9826a` | `c7b0c6a6327c84586d8e95e50bbfa14afeef23d5` |
| `scripts/validate_bundle.py` | `6161a5533f0158d2d69254a941ccd7b7327840dd837400ddbc970bef4e052259` | `1cb9a45c6dd3fdc436fe4c6d162c57ef1d7e1bfb` |
| `scripts/validate_codex_release.py` | `2c36cfa4b21c4aface3a575f72471a256ecee7984f7ad727d3fa5b9c59c07f8d` | `95abfe45d85771e6ad6925c632b5ddee2e8f4399` |
| `scripts/validate_local_codex_sync.py` | `9a2ec219c1ce6045d5b6b1257f013af44f25d1834d79ee6816db8674e989edcc` | `bdad97d5598e36585600294262e6eb685a9460e4` |

## 补丁

- `$OUTPUTS/project-delivery-suite-v0.8.0/0001-fix-enforce-path-boundaries-and-distinguish-evidence.patch`：SHA-256 `987d1174743454e44bb03b671206117c40895a2d717c87d6c6c74e92b8299d71`；来源提交 `6b0d7962652452b3d274c37da7948ba7fd672aaa`；提交头匹配 True；stable patch-id `1d9c1698bcbeaf5450cd216d97d7360accc728b8` 与提交一致 True。单条 format-patch 字节一致 False（批量序号可造成邮件头差异）。
- `$OUTPUTS/project-delivery-suite-v0.8.0/0002-feat-add-local-delivery-and-auditable-behavior-evalu.patch`：SHA-256 `d1684d1c1cce6b891d355ef39c9dd3fa97d8041704a8274789d4bee15ae63e27`；来源提交 `40e20d45b5d8e03983bf2500e56141b584954f17`；提交头匹配 True；stable patch-id `e0300923c89dd3ea688e52213f86a74091a23959` 与提交一致 True。单条 format-patch 字节一致 False（批量序号可造成邮件头差异）。

## 未覆盖内容与留存

改进报告 SHA-256：`237a9dbb041099ae2fca37da6c05ab48dce9fd02bf3955005b989e1dc6ab4d19`。两个提交中无相同 Git blob。其两批摘要、约束映射、历史检查声明和交付使用说明是独有的交付叙述；本次未验证其中测试通过、环境、历史工作区状态等声明。建议将原文原样留存至仓库 evidence 下并注明历史说明、来源与哈希，再决定是否清理原报告；本次按要求没有复制报告。

ZIP 和两份补丁均可由上述 Git 提交恢复代码内容。技术上可清理的精确范围：
- `$OUTPUTS/project-delivery-suite-v0.8.0.zip`
- `$OUTPUTS/project-delivery-suite-v0.8.0`（仅所列两份补丁）

在报告原文留存前不得将其视为冗余副本。审计 JSON 保留 ZIP 容器哈希、逐文件 Git 对应和补丁 patch-id。清理授权仍由主任务确认。

补充字节验证：两份补丁按顺序、以一个换行连接，与 `git format-patch --stdout 6b0d796^..40e20d4` 完全一致：True。上文单提交差异仅为系列编号和邮件主题折行。
