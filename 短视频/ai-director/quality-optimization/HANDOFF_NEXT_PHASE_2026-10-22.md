# AI导演系统｜2026-10-22 静态交接审核与下一阶段工作基线

> 本文件为阶段性交接记录，不是运行测试报告，不是片子质量证明。
> 用户明确：当前先完成导演模块，不运行单元/CI/实际媒体/付费模型，不合并未经验证的PR。不得因一个新的对话框而重置此禁令。

## 0. 单一事实来源与当前开发分支

- 仓库：https://github.com/pyzz58/gpt-recommendations
- 范围：`短视频/ai-director/`（与新闻日报、战略内参完全分开）
- 统一未合并 Draft PR：https://github.com/pyzz58/gpt-recommendations/pull/67
- 开发分支：`ai-director-integrated-creative-gates-v1`；目标 `main`
- 主审计/开发事项：https://github.com/pyzz58/gpt-recommendations/issues/61
- 唯一质量事项主账：`quality-optimization/QUALITY_ISSUES.json`；Markdown：`quality-optimization/QUALITY_ISSUES.md`
- 总指南：`AGENTS.md`；新增详细专业规范为 `skills/15-...md` 至 `skills/24-...md`
- 截至本轮 compare：PR相对main领先74个提交、落后141个提交，变更27个文件且本PR变更均在 `短视频/ai-director/` 内。主分支相对PR的新增变更集合主要在新闻/内参等其他路径；仍须在正式同步前重新比较确切SHAs并审查CI/依赖交叉影响。GitHub主分支可能继续推进，数字不是永久锁定。
- 质量主账40项：20 in_progress / 5 partially_addressed / 4 confirmed_open / 1 blocked_external / 10 audit_pending。导演项QO-D01至D19共19项：18 in_progress、D11 blocked_external。没有任一项在本轮因仅写代码而标为已通过人工艺术/真实媒体验收。

## 1. 已完成的是「第一版能力编码」，不是正式成片验收

PR#67新增的导演模块与专业规范：
1. `director_whole_film_critique.py`（D10）／`skills/15...`
2. `director_action_rescue.py`（D06）／`skills/16...`
3. `director_revision_lineage.py`（D12）／`skills/17...`
4. `director_creative_integration.py`（QO-D10/D06/D12整合）／`skills/18...`
5. `director_conflict_arbitration.py`（D16）／`skills/19...`
6. `director_visual_continuity.py`（D05/D07）／`skills/20...`
7. `director_episode_rhythm.py`（D03/D09）／`skills/21...`
8. `director_cut_series_handoff.py`（D13/D14）／`skills/22...`
9. `director_screenplay_authority.py`（D01）＋现有 `director_shot_coverage.py` 修正（D02）／`skills/23...`
10. `director_provider_capabilities.py`（D04）与`director_voice_picture_sync.py`（D08）／`skills/24...`

原有完整系统已含 `screenplay_adaptation`、`screenplay_director_handoff`、`screenplay_series_delivery`、`director_shot_coverage`、`director_visual_language`、`film_continuity`、`director_speech_cues`、`director_delivery_review`、`director_montage_editor_conform`、`director_media_otio_export`、`agent_team`、`agent_role_contracts`、`agent_live_crew`、`seedance_adapter` 等。不得再制造第二套编剧、总导演、剪辑调度器或后期引擎。

## 2. 静态审核得出的可核实阻断与约束

### P0-01 真实授权执行入口仍未接入新增专业门禁（已核实）

`agent_live_crew.run_one_locked_role(...)`已经接收并传递较早的三个 `department_command`、`audiovisual_plan`、`artistic_method_plan` 到 `roles.build_role_messages`、`roles.validate_role_output`、`roles.submit_role_output`。因此质量项D18中“这三项均未接通”的旧文字不再准确，需修订，不能照搬。

但当前该**实际真实运行入口**缺本PR新增加的 `holistic_critique`、`action_rescue_plan`、`holistic_post_critique`、`action_rescue_post_plan`、`department_delivery_review`、`artistic_arbitration_plan`、`visual_continuity_review`、`rhythm_pre_plan`、`rhythm_post_plan`、`provider_capability_plan`、`speech_picture_plan` 参数传递。显式严格模式开启时，离线角色构造和结果校验可能阻止专业工单，因此不能宣称真实模型全链路已经接通。必须以**一份版本锁定的私有导演创作快照**跨三处共同传递，不允许单靠禁用gate规避。

### P0-02 PR分叉与配置收敛

开发分支与main明显分叉，但本轮两个方向比较显示PR修改限定导演目录、main一方新增变更未出现在导演目录的清单中。**尚未完成真正的合并/重放/冲突验收**。下一聊天应冻结主分支/PR头SHA，先比较其他CI/依赖改动，再决定新分支或重放策略，禁止无审计直接强推main。

### P0-03 多个导演门禁共同版本与合同须静态逐字段审核

新模块之间现已出现制作前/专业交付后两阶段，以及 `base`、`state`、导演锁稿、制作会、视听语言、影片节奏、角色提交 `revision`、音频cue、AI能力目录等多种digest。只在GitHub静态看到了这些实现；**没有执行解释器编译、Schema验证或反例运行**。

需逐模块列生产者/消费者/具体输入字段/产出字段/缺省/生效阶段/重算条件；尤其审核`director_creative_integration`→`agent_role_contracts`→`agent_live_crew`、`director_conflict_arbitration`→QO-D12修订、`director_voice_picture_sync`→已有QO-D19表、`director_cut_series_handoff`→新编剧稿及series原工作包、`director_provider_capabilities`→AI技术岗实际route。任何字段可能不一致，必须以源码引用定位，不可假设因为有模块文件就已经正确运行。

### P1-01 原剧本源权、人物道具与音画现实差距

`director_shot_coverage`已增加合镜道具、speaker和来源记录，但未执行公开样例回归；D01对白逐字检查仍不能识别自由文字里隐含的事实或人物动机改变。D05/D07跨镜一致、D08嘴型/字幕和D19计划中的准确cue也不能证明真人实片。必须拆分「静态可证事实」「模型交付方案」「真实媒体/真人审片」三档证据，禁止跨档冒用。

### P1-02 模型能力证据有条件、不是账号通行证

D04能力注册表明确每个型号、渠道及自身 `registry_digest`；现有Seedance4–15秒只代表旧adapter自限，Veo和Runway字段属于各自特定API渠道。正式接入前再核官方当前版本、区域、配额、价格及真实可用性；不在GitHub公共CI传真实用户脚本、密钥、授权或媒体资产。D11维持blocked_external。

### P1-03 避免重复扩建与假闭环

已有十岗位、导演制作会、编剧原稿、编辑工单、OTIO等较完整。下一阶段**优先集成和修错，禁止新增新的导演Agent、大型工作流、重复时间线或无效schema**。D16的艺术仲裁报告不是部门已返工证据；D10文本批评不是电影好看；任何“自填真人审片表”不等于完成真人身份/媒体哈希验证。

## 3. 下一阶段路线（分阶段执行且逐项有可复查证据）

| 序号 | 优先级 | 子任务及允许操作 | 验收产物（未到此阶段不可提前宣称完成） |
|---|---|---|---|
| N00 | P0 | 冻结仓库两分支SHA，核对PR#67、Issue#61、AGENTS和质量主账；检查主分支CI与交叉依赖 | `BASELINE_SNAPSHOT.md`，SHA及全部版本源列 |
| N01 | P0 | 列全模块producer→consumer，静态字段/枚举/phase/权限对照；登记高危错误 | `CONTRACT_MATRIX.md` 与逐项风险ID/修复建议，不运行测试 |
| N02 | P0 | 修复`agent_live_crew`旧真实十岗入口缺新版导演快照/门禁参数的三处调用，严格只接受私有版号一致的批准数据 | 实际真实运行入口源码三处对齐，缺任一必需字段离线安全报错；不得真实发送 |
| N03 | P0 | 静态核对D01/02/13/14/19的编剧/导演/新镜头/时间线源权及字幕cue接口，做确定性代码修复 | 不丢角色/道具/事实/对白的引用与源beat映射，旧剧本改稿强制新版本；人工语义仍待验证 |
| N04 | P0 | 核对D10/D06/D12/D16与D03/D05/D07/D08的复审、返工、失效边界，修复假放行或死锁 | 导演pre/post门禁矩阵+fail-closed规则，仲裁≠返工通过 |
| N05 | P1 | 对D04能力注册表按官方渠道文档复核，分开未知与本仓库适配器已实现能力；审核无密钥/媒体泄漏 | 能力证据表含版本/URL/日期/未知/过期行为；不实际调用 |
| N06 | P1 | 识别重复schema/重复source校验和重复角色指令，合并/删除冗余而不破坏原结构；同步AGENTS/两个质量账 | 统一架构图与废弃项清单，无重复导演/编剧/剪辑引擎 |
| N07 | P1 | 生成**不执行**的公开合成回归设计，覆盖正常、失败、旧版本、跨镜、时长、质量、人声/字幕、权限 | `TEST_MATRIX.md`：例子、输入、预期错误码、通过标准；保持pending |
| N08 | 需用户解除“先不测试” | 先解释器/Schema/单元，再CI、模拟HTTPS十岗及公开虚构端到端、故障恢复 | 每项真实测试命令、run ID、结果及失败修复记录；不能只写PASS |
| N09 | 需另行授权 | 公共虚构电影/论述/荒诞喜剧各至少一组，人类独立评价与实片生成试验 | 编剧/导演两种创意方案艺术对照、真实媒体哈希、成本、跨镜复核；D11仍blocked直到完成 |
| N10 | 需上述验收 | 清理旧Draft，确认所有阻断已解除、主分支变更安全同步及用户同意，审议合并 | 可审查的最终PR与版本化验收总报告，仍不自动发布或扣费 |

## 4. 原则与交付要求

- 先静态P0，不跑本地Python、pytest、CI、不自动触发GitHub Actions；即使新对话开启，禁令持续，只有用户明确解除某一层才执行该层。
- 每完成N00–N07一项，**做出实际GitHub文件/代码/issue记录，再描述完成**；不把拟办当完成。
- 原始用户文案/小说、脚本、私人资产、凭据、媒体及完整私人提示词不能提交到公开仓库。
- 不碰新闻日报/内参；不绕过版权、真实用户支付及人工鉴权。
- 验收证据要具体到文件、关键字段、commit、PR、run ID（如已授权测试）；必须区分`planned`、`in_progress`、`static_checked`、`tested`、`human_media_verified`。
- 质量主账是单一事实来源，但**如果账本与当前实际源码不符，应先以源码审计纠正过时问题描述**，如QO-D18早期描述“3项未接入”已经被旧PR解决，当前新增11项仍未传真实入口。

## 5. 新聊天第一句话建议

“阅读仓库`pyzz58/gpt-recommendations`的Draft PR#67以及`短视频/ai-director/quality-optimization/HANDOFF_NEXT_PHASE_2026-10-22.md`，同时核对`AGENTS.md`与`QUALITY_ISSUES.json`。先执行N00和N01：取主分支/PR SHA，输出逐模块实际接口合同表与真实阻断清单；不运行任何测试、不调用付费API、不合并主分支、不新增专业Agent。然后按N02起逐项修复，每项附真实GitHub证据。”
