# 从机械分镜到专业创作：总导演与剧本编辑衔接（离线验收版）

**状态：GitHub-only 研发，合成模型回复模拟，尚未调用真正 DeepSeek。** 这一步将已有“用户上传完整文章→单集分镜占位”的结果，接到**已有**总导演 `director_brief` 与剧本编辑 `script_edit` 两个正式岗位，允许专业岗位给每一镜提出真正不同的可拍摄构想，并生成一份可对比的**候选**分镜。原始文案、不经审定的数字和旁白仍受到保护。

源码：[editorial_storyboard.py](editorial_storyboard.py)  
测试：[tests/test_editorial_storyboard.py](tests/test_editorial_storyboard.py)

## 这一步解决的真问题

上一版 `article_intake.py` 只做机械分集、抽取“说人话”原文、分配时间，初稿镜头均是 `text_card` / `data_graphic`。这份草案可用于溯源，但还不是专业影视语言。现在剧本编辑的增强输出必须加入 `storyboard_pitch`，做到：

- **全片创意角度**：`creative_angle`、`hook_strategy`、`audience_question`、`ending_payoff`；
- **逐镜视觉构想**：每镜都有不同的 `visual_intention`，不能整片重复“电影感”；
- **逐镜动作**：完整 `start/action/micro_action/reaction/end`，让后续动作导演有具体素材；
- **摄影与光照意图**：`camera_intention`、`light_intention`；
- **镜间衔接**：`transition_intention` 和 `reason`；
- **正确生产路线**：按 `ai_video`、`data_graphic`、`text_card` 等分类，确保数字类内容不会直接交给视频模型生成准确汉字；
- **原文引述**：`evidence_quote` 必须逐字匹配权威单集分镜的当前旁白；新增的字幕数字必须至少在当前集原文出现，未做外部医学/法律核查则始终不能宣称已证实。

系统本身不会凭这些字段推断专业摄影、动作、音频、剪辑工作已经完成。后续部门需要按自己的岗位合同真正生成并复核。

## 操作接口（仅在未来获许可的私有环境中使用，不在公开 GitHub 执行真人素材）

```python
import article_intake
import editorial_storyboard
import agent_role_contracts

# 只是函数说明，不是一段会直接联网执行的脚本。
source = "### 1. 虚构小故事\n- 说人话：桌面上有一封信。"
intake = article_intake.prepare_episode(source, "EP01")
episode_source = article_intake.episode_source_for_team(source, "EP01")

# 1. 总导演：准备现有岗位规范的 system/user JSON 消息
director_request = editorial_storyboard.build_director_brief_request(
    intake, episode_source)
# 需要独立、明确获授权的模型通信层，才能真正返回角色创作内容。
# 2. 系统对外部提供的原始角色 JSON 用原 agent_role_contracts 提交，
#    验证来源、字段、任务依赖与版本；不信任任意结构化文本。
# 3. 总导演提交后再准备剧本编辑强化创作任务：
# script_request = editorial_storyboard.build_script_editor_request(
#    intake, state_after_director, episode_source)
# 4. 双岗位合格之后：
# proposal = editorial_storyboard.propose_directed_storyboard(
#    intake, state_after_editor, episode_source)
# 5. 原文不改，作者仍要审阅 proposal["candidate_plan"]。
```

测试中使用 `agent_model_gateway.OfflineMockTransport` 提供预写的**虚构创作回复**，通过现有 `roles.submit_role_output` 逐岗位验收、归入同一十阶段团队的前两阶段。**模拟 JSON 的质量和 CI 通过次数不能等价于实际模型已产出优秀导演方案。**

## 人工审批与强保护

1. `build_director_brief_request` 和 `build_script_editor_request` 只在内存中产生含单集私密原文、完整分镜、上游成果的 Prompt；**严禁**提交公有仓库、公共日志或未经用户许可的供应商。
2. 增强 Script Editor Schema 增加 `storyboard_pitch` 结构化验证，保留已有 `story_treatment.beat_map` / `source_change_proposals`；两者仍属于剧本编辑岗位，而不是创建重复的独立编剧项目。
3. 改写文案/删除原句/调换数字必须只能出现在 `source_change_proposals`，并具有 `requires_user_approval=true`、`approved=false`。**不能偷偷把这些文字写进原计划**。
4. `propose_directed_storyboard` 在新的独立副本中替换画面类型、视觉构想、动作、摄影、光照、字幕后期图层、镜间连续性策略与 hook，但**原旁白、镜头时码和 claims 不变**；原始 base 与 team 状态只读未改。
5. 新的分镜草案哈希不同，不能偷用旧 `agent_team` 的执行状态。 `stage_new_team` 会重新建立待审状态下的新任务账本，标注 `pending_author_editorial_review`，**不代表作者批准或团队创作完成**；实际模型执行必须设置更外层的真人许可门禁。
6. 场景、演员资料、准确镜头提示词、动作分镜时间节拍、音乐版权、实际视频生成、财务批准均尚未完成，必须由后续岗位与人工验收。系统始终 `human_approved=false`，`paid_api_authorized=false`，`media_generated=false`。

## 后续真正达到可用 MVP 的条件

现在已有从普通文章到**导演意图和剧本编辑创意方案的程序验收接口**。真正闭环至少还要：

- 获授权的**真实** AI 模型分别填入 `director_brief` 与 `script_edit.storyboard_pitch`，对用户允许传输的素材制作样例并人工看实际叙事质量；
- 人工审核并锁定所采用的候选分镜/旁白（未来要提供逐条批准及修改的界面/接口）；这一阶段内已考虑保留候选版本和无自动改稿；
- 由 `director_lock`、表演、摄影美术、声音、剪辑动画、技术导演、独立 QA 和终审依赖相同版本继续生产，输出经质量检查的逐镜视频提示词、参考资产和后期交付书；
- 在指定 AI 视频模型做小样验证，让“技术通过”转化为“可实际制作”。

**不能说已经生成了影片，也不能说 10 个 AI 已真的联网独立创作。**
