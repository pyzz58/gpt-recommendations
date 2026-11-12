# 第24号总导演专业规范｜QO-D04 模型能力按接入渠道核证 × QO-D08 台词/嘴型/字幕对应

**版本**：2026-10-22。**模块**：`director_provider_capabilities.py` 与 `director_voice_picture_sync.py`。**生产入口**：现有 `agent_role_contracts.build_role_messages / validate_role_output / submit_role_output`，未增加第二导演、第二技术岗或新的付费API执行器。仍按照用户此前要求 **暂不测试**，不运行CI、付费模型、生成真实媒体或修改Seedance真实网络接口，不合并Draft PR #67。

## 一、第一性原则：电影意图优先于模型能力

总导演先确定观众必须看到的动作、表演、视觉含义与声音时刻，然后由原 `ai_technical` 在**特定模型版本＋特定API渠道**的真实可用能力内选生产方案。绝不能把“Seedance某适配器当前只接4–15秒”误称为所有AI模型同一上限，更不能因为某模型价格便宜、默认时长短，就先删掉编剧不可改动的人物动机、论点、原对白。无法直接生成的镜头可以提出**保留意义的专业替代方案**：源锁镜头拆解、后期合成、真实演员素材、画外声、静态图像动画，但必须明示原导演的艺术代价与待审返工工单，不得自动缩短原shot.duration。

### 已登记的渠道化证据（不是一个万能视频API）

| 唯一渠道ID | 证据类型 | 当前离线约束 | 不可误称 |
|---|---|---|---|
| `seedance-2.5-volcengine-existing-adapter` | 仓库原`seedance_adapter.py`内部已设定的保守支持子集 | 仅该适配器：竖屏、720p、4–15整数秒、单镜、最多3张参考图；需另行明确是否候选原生音频 | 不是「所有Seedance模型官方最长15秒」，不是新账号已可调用 |
| `seedance-2.5-byteplus-existing-adapter` | 同一原仓库另一个渠道与型号标识 | 同上，但渠道和model版本不同 | 不能用火山引擎凭据假装BytePlus已授权 |
| `veo-3.1-gemini-api-preview` | [Google Gemini API官方文档](https://ai.google.dev/gemini-api/docs/veo) | 按该API：4/6/8秒；9:16/16:9；720p/1080p/4k，高清或参考图输入等需要8秒；原生音频可用但内容质量未知 | 不能当作Veo其他平台、全部模型版本、音频内容或人脸真实性认证 |
| `runway-gen4.5-cloudflare-workers-ai` | [Cloudflare的Runway Gen-4.5渠道参数](https://developers.cloudflare.com/ai/models/runwayml/gen-4.5/) | 该渠道2–10整数秒，具体画幅枚举、720p、一个图像输入参数 | **不是Runway直连官方API**；不借Cloudflare的字段证明直连权限、价格或原生对白支持 |
| Kling 3、Seedance 2.0、Runway直连等尚未核实渠道 | UNKNOWN | **不产生可执行provider工单**，先补真正的官方渠道版本资料 | 不依据社媒、推广页面或跨渠道宣传直接下发 |

**2026-10-22核对时点**只是登记时间，不代表这些宣传、API价格、可用区域与功能在以后不会变化。能力表必须绑定`registry_digest`；文档或渠道能力发生调整时，旧导演选型不能静默复用。视频价格、地区、配额、账号状态、图像版权、付费权皆必须现场由可信操作者另行验证，注册表不把未知值填成真。

### 能力表实际机制

`catalogue()`只返回原接入渠道来源、API能力约束和明确未知状态，不联网。由总导演提供的`provider_capability_plan`逐镜列`shot_id`、原`duration_s`、不可牺牲的故事/表演、期望route、型号和渠道、画幅、分辨率、参考图需求、头尾帧需求、是否一片内多镜、音频路由、替代手法与艺术损失。

`validate(base,state,plan)`强制原`director_lock`已经存在且完成、base/source/registry digest未变化、原镜头时长完全相同；只允许有据的`ai_video`配置或既有`static_post/edit_composite/live_action_insert/post_production`路线。超出当前选择渠道的片长、错误画幅/高清条件、未知模型能力、多镜假支持、头尾帧未支持等均拒绝。不提供所谓“自动拆15秒成任意N段成功”的承诺。只有导演明确重新设计分镜、回原QO-D02源锁重建专业计划才能真正拆镜。

`validate_technical_delivery`会将原 `ai_technical` 实际提交的每镜`generation.route`与总导演选定route逐项对照，拒绝技术岗偷换production路线。此处**没有跨供应商派发工具**：原`seedance_adapter.prepare_shot/submit_once`与真实网络API仍是独立的、需要另行授权的具体适配器。

## 二、声画关系必须由权威台词确定，不能让生成模型先改嘴型再改剧本

原`director_speech_cues.py`（QO-D19）已提供：编剧官方每句对白speaker、每字text_exact、原场次节拍相对秒数、字幕cue与导演分镜下的跨镜头音轨绑定；`director_montage_editor_conform`和`director_media_otio_export`拥有帧级编辑计划与实际媒体本地来源校验。新模块并不重造TTS/ASR、配音或字幕引擎，而是**把真实声轨、人物嘴型、画面镜头、字幕与导演要求联系起来**。

新`director_voice_picture_sync.py`的`validate`只有在base已存原QO-D19`director_editor_cue_sheet`且剧本SHA、base摘要一致时允许审查；任何缺原audio/subtitle cue、额外台词、改字、偷改speaker、扩大或挪用秒数都会拒绝。每条音轨需完整绑定原剪辑器的`picture_segments`，并逐小段写：
- **on_camera_speaking**：现在画面内真实哪名角色开口，`lip_target_character_id`必须与权威编剧的speaker→character_id相同且人物ID属于这一物理镜头；
- **off_camera_audio**：对白可延伸到另一人的反应镜头，但**不得驱动反应者的嘴巴说话**，`lip_target_character_id=None`；
- **narration_no_visible_speaker**：旁白不是某个镜内演员的嘴型目标；
- 每个镜头交稿明确`other_visible_characters_must_not_mouth_this_dialogue=true`：两人对话特写尤其必须保证另一个人不被AI同时生成开口动作；此规则是**导演的目标要求，不是实片已被核验**。

原生语音只属于 `native_dialogue_candidate`，必须同时与QO-D04真实选定的`ai_video`模型音频路由一致；不能选择技术上不支持或不确定的原生音频能力。其它使用`post_dubbing`或`post_voiceover`，原视频沉默处理后在剪辑阶段建立音轨，并在最终实片逐句审听。无论原生生成或后配，字幕只允许使用源`text_exact`，具体画面可读性、颜色、对齐和口型必须后期核查，不让视频模型生成精确文字。

## 三、实际角色请求和回执入口

`agent_role_contracts`增加两个向后兼容的可选参数：`provider_capability_plan`、`speech_picture_plan`，仅在base**显式**声明以下新生产要求后才会强制：

```json
{
  "director_provider_capability_mode": {
    "kind": "director_model_channel_capability_required",
    "before_ai_technical": true
  },
  "director_speech_picture_mode": {
    "kind": "director_source_exact_speech_picture_required",
    "before_sound_and_edit": true
  }
}
```

- AI技术岗与最终导演收到同一版本的`provider_capability_plan`，没有不能进入严模式；若技术岗最后交稿route与选中方案不同，拒绝交稿或终审。
- 声音、剪辑、AI技术、最终导演收到`speech_picture_plan`，须先完成原QO-D19逐字逐句信息与跨镜时间核验。
- 任何要求原生对白的画面必须在能力路由中也选`native_dialogue_candidate`，不能拿“技术上可能有音频”当成已经听懂原台词。
- 没开启相应base模式的老项目继续旧路径，不强制为历史视频加新字段，不改原`seedance_adapter`、现有`video_workflow`或`production_delivery`的真实媒体逻辑。

## 四、真实声音、嘴型、字幕的最后验收尚未完成

真正媒体落地后，应当由**可信私有媒体工具**对所有视频/音频实际字节做hash与时码探测、ASR/人工审听逐句文本、分析/人工核验声画口型与上下嘴部动作、核对真实渲染字幕的每个汉字和时码；两人同镜一人发声另一人必须无不当嘴型。若出现“张三嘴动、其实李四说话”“台词改成语义相近却不是原句”“AI自动加一句话”“字幕错字”“后期音轨重复播放”，定位具体`cue_id`和`subtitle_id`后只做局部声音/字幕/编辑修订，必要时回导演决定重生成该小段，不能改剧本掩盖错误。

`audit_real_media_review_record()`**只验证操作者填写的逐句核查表结构、原文与其填报的观察结果**，不能自己读取媒体、认证此人真实身份或声称独立ASR验证；即使所有字段标通过，仍返回`can_publish_or_autoapprove=False`。这与原`video_workflow`的真人候选审查与真实媒体哈希校验是分开的独立步骤。只有未来真正的本地音视频分析及人工独立审稿完成后才能称为“音画已验收”。

## 五、未来集中测试/真人艺术评估（本轮不执行）

- 公开双人对话：A开口时镜内B不能开口；反打到B的反应镜仍播放A音轨，则嘴型目标为空、源文本不增不减；
- 编剧对白跨3个物理镜头，首句源cue只出现一次，字幕随剪口不断裂、不抢话、不复制；
- 无准确QO-D19逐句source时间，不得从字数推算并伪装为已同步；
- Veo 3.1要求4秒而输入参考图/1080p、Runway当前Cloudflare渠道要求11秒、Seedance现有adapter要求多shot，应拒绝；
- 同一模型名由Cloudflare换成Runway直连，不得复用Cloudflare的API配置；
- 真实AI视频/声音经私人ASR和人工核验错字、口型、声道重复后正确定位工单及可追踪真实素材hash；
- 无新的真人鉴权、实际声视频和独立电影艺术评价，始终不能宣称发布或付费授权。

**质量状态：** QO-D04、QO-D08仅应登记为`in_progress`，不能因为源锁JSON、现有媒体下载成功或操作者自行填表就标`completed`。
