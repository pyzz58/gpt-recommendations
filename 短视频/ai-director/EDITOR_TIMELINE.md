# 导演交付书的剪辑时间线（GitHub-only）

**定位**：该模块不是视频生成器，而是“用户文案 → 导演创作决策 → 可交接给 AI 视频工具及剪辑师的工作单”中间层的一部分。用户不需要先学剪辑、分镜或动画。

## 实现进度

本轮 `director_timeline.py` 与 `director_workbook.py` 结合 `plan.json`、`direction_v02.json`，把原本散落的摄影、表演、声音、剪辑、动画指令放进统一的**绝对时间线（单位秒）**，并附带质量提示。

| 轨道 | 导演要填写的内容 | 机器可核验 |
|---|---|---|
| Picture Beats | 0–1.2 秒做什么、演员肢体/表情、机位与镜头运动、每节拍音效 | 相对时间→绝对时间、越界 |
| Voiceover | 完整旁白原文、语气、每句开始/结束时间、是否需要停顿 | timecoded cue 可选；未填写不能假装已对齐 |
| Dialogue | 谁说、确切台词、从第几秒到第几秒、口型和演法 | speaker 与时段 |
| Sound Effects | 画面动作对应的拟音、绝对 cue 时间 | 越界检测 |
| Animation | 图层名称、运动方式、时间、关键帧 | from_s/to_s 若有则核验；只有说明文字就留待后期 |
| Editing | 入出转场、切点动机、音频跨镜头连接、拼接要求 | 与基础分镜转场一致性检查 |
| Production | 哪些动作交给 AI 视频、哪些用剪辑合成、静态图、实拍 | 按既有混合路线编译 |

**备注**：此处只导出时间线工作表，不导出可以直接载入剪辑软件的工程文件。当前所有来源素材都还不存在，不能说已剪出视频、已生成配音或做了音频混音。

## 可复用的成熟开源思路

- [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO)：成熟影视剪辑时间线交换框架。借鉴它把 timeline、clip、tracks、transitions、time ranges 分开的方法；**本轮不移植其源码、不安装它的 Python/原生依赖，也不冒充 OTIO 文件格式**。未来如果真要导出剪映/达芬奇/FCP 工程，需先核对实际支持的格式和引用的媒体，届时再评估原生 OTIO 适配。
- [AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline)：其公开 shot-list-template 将 action、dialogue、voiceover、audio、镜头运动分别列出；我们的导演输出继续区分配音与出镜对白。
- [CineCrew](https://github.com/Ironieser/CineCrew)：继承 FilmDSL 中分镜/角色/道具/导演约束分层的设计，但并未集成多模型视频执行器。

## 创作与校验的边界

每个镜头都必须是导演亲自作出的**具体视听决定**。代码只是防止：
- 同一镜头内某个音效安排在镜头结束之后；
- 出镜对白与旁白都发生时，没安排好声音层级；
- 旁白没有逐句时间码，却被错误标记为“已同步”；
- 时间码里的旁白文字偏离原始文案；
- 动画有“让时钟转动”的描述，却没有可供后期执行的具体起止秒数；
- 超过节奏参考阈值的中文旁白未留待人审。当前阈值仅是**提醒**，不是配音演员真实速度的判定；
- 剧情剪辑入出点与基础稿冲突。

`director_timeline.assemble()` 返回逐镜头的编辑决策轨道与检查发现。当前 `director_workbook.compile_workbook()` 已将其整合为 `editor_decision_list`、`director_review.timing_review_findings`；严重时间错误影响 `creative_design_complete`，一般节奏提示不自动驳回导演稿。

## 人工审核

即使所有字段具备时间码，也不能通过程序判断“观众看不看得懂”“转场是否漂亮”“这一刻的音乐是否感人”。这些必须由用户/真正的导演在预演中审核。

**现阶段所有内容仅 GitHub 远程开发。** 用户 Mac 的旧代码、私人分镜和费用设置不更改。无付费 API、无下载模型、无渲染。

## 开发验证状态

已把 `tests/test_director_timeline.py` 11 个新回归用例提交 GitHub，覆盖时间线、配音文本偏移、对白及声音冲突、动画时段和与总工作单的集成。**最新整仓未在统一隔离环境执行测试；测试文件已经提交不代表测试通过。** 在下次正式部署批准前，必须完成一次完整无付费回归。
