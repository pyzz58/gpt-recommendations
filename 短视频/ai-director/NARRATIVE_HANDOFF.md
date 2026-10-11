# 相邻镜头的专业叙事、节奏与视觉风格交接

> **产品定位**：这是 AI 短视频导演中间层的核心创作能力之一。用户给出文案，导演必须讲清楚**为何在这时剪、下一镜如何推进故事、声音/动作/动画如何衔接、不同制作方式如何看起来属于同一部片子**。该模块不是视频生成器或自动审美评分器。

## 本次真正新增的交付内容

`director_narrative_bridges.py` 读取 `plan.json` 和 `direction_v02.json`，从 **S01→S02、S02→S03 …**逐个形成相邻镜头导演合同；最后一镜无需凭空制造下一镜。

`director_workbook.py` 新增：

- `narrative_bridges[]`：每对镜头的切点秒数、两镜制作方式、剧情问答、情绪转变、构图/视线衔接、后期风格统一具体措施。
- `director_review.narrative_handoff_ready`：每个边界的合同字段完整，且没有明显类型和时长错误（**不代表艺术审查完成**）。
- `director_review.narrative_handoff_pending`：列出尚未进行的创作决策。
- `director_review.production_blueprint_ready`：此前的 `editor_handoff_ready` **且**跨镜头导演合同齐备；`--strict` 现在要求两方面都齐备，仍保留 `human_approved=false`。
- Markdown 导演交付书在每镜末尾附“下一镜的叙事、节奏与混合制作风格衔接”表。旧导演文件缺少该字段会得到明示的缺项提示，**依然可以编译旧稿草稿**。

## 新增：切点必须绑定真实动作节拍，拒绝模板化导演理由

本轮修复了一个重要的“填字段就算完成”的漏洞。过去只要某次剪辑写了 `why_cut_here="动作完成后自然切入下一镜"`，就可能被误认为已有专业切点设计；现在**每个相邻镜头交接必须明确绑定实际分镜中的动作节拍**。

在每个非末镜的 `editing.narrative_bridge` 里新增：

```json
{
  "beat_link": {
    "outgoing_beat_index": 2,
    "incoming_beat_index": 0,
    "cut_on_visible_event": "右手松开香烟，手指离开桌面，视线移向窗外的那个瞬间"
  }
}
```

索引均从 0 开始，分别定位前镜头 `direction.shots[].beats` 的末节拍和后镜头的首节拍。审核器核对索引有效、末节拍确实到达切镜时刻、下一节拍确实从 0 秒开始；在交付书的 `cut_beat_evidence` 中直接引用当事两镜真实的 `visible_change`。它**不臆造摄影画面**，只呈现已写入导演稿的具体动作。若末节拍编号不对、节拍没有落在切点，则按阻断处理；旧稿没写 `beat_link` 仍可读为草稿，但跨镜头交接不能标就绪。

同时，当同一段具体 `viewer_question`、`why_cut_here`、`answer_or_reframe`、`motion_or_prop_link` 或 `style_handoff.implementation` 在**三个或更多**相邻镜头之间逐字重复时，发出 `BOILERPLATE_DIRECTOR_REASON` 人工复核提示，并暂停把整份工作单宣称为“制作蓝图已齐备”。这是一条**保守的文本重复检测**，不是识别所有套话的 AI，也不是艺术质量评分；统一字体规范或统一色调可以合理重复，不纳入该检测。特殊叙事手法如果确实需要重复，应由导演保留真实说明，并由人工审阅，不应绕过检查伪装成不同内容。

注意：`narrative_handoff_ready` 仅代表所有切镜证据和合同格式齐全；`editorial_specificity_review_required` 标记复制套话情况；`production_blueprint_ready` 还需要通过该复核。即使所有布尔项为真，仍需人审故事表达、转场视觉效果和音频可听性。

## 相邻镜头必须由导演明确设计的四部分

| 字段 | 需要做的创作决策 | 不能省略的内容 |
|---|---|---|
| `cut_intention` | **为什么在这一刻切？**上一镜留给观众什么问题，下一镜解决或重构什么认知 | `viewer_question / answer_or_reframe / why_cut_here / information_change / cut_type` |
| `emotion_pacing` | 情绪由何变何，节奏何以加快、放慢或保持，上一镜应停多久，下一镜给观众多久理解 | `emotion_before / emotion_after / audience_effect / tempo_change / tempo_reason / hold_before_s / settle_after_s` |
| `visual_handoff` | 上一镜出画时哪里是视觉注意点，下一镜从哪里接住，人物视线/画面轴线/动作/道具或轮廓怎么连接 | `outgoing_frame_anchor / incoming_frame_anchor / axis_or_gaze_rule / motion_or_prop_link / relation` |
| `style_handoff` | AI 视频与静态图、动画、图形、实拍之间，如何统一色彩、灯光逻辑、构图、颗粒/锐度、字体与安全区 | `strategy / palette_target / lighting_logic / composition_rule / texture_rule / typography_rule / implementation` |

可选择的切点/视觉联系 `cut_type/relation`：`cut`、`match_action`、`match_gaze`、`match_shape`、`contrast`、`reveal`、`establish`、`intentional_jump`。

节奏 `tempo_change`：`accelerate`、`decelerate`、`hold`、`contrast`。风格处理 `strategy`：`preserve`、`grade_to_match`、`graphic_match`、`motivated_contrast`。**不能因程序支持某个术语就机械使用它**，需要独立创作理由。

### 合成公开示例：人物举烟犹豫 → 日常花费图表

例子对应 GitHub 原有的演示内容，不使用用户私人短视频：

```json
{
  "cut_intention": {
    "viewer_question": "观众看到他放下香烟之后，会想知道为什么值得这样做",
    "answer_or_reframe": "用日常花费的图形让抽象决定变得具体",
    "why_cut_here": "上一镜右手松开香烟、视线停留之后切入日常花费",
    "information_change": "从行为动机进入可感知的经济代价",
    "cut_type": "match_shape"
  },
  "emotion_pacing": {
    "emotion_before": "迟疑",
    "emotion_after": "理解",
    "audience_effect": "让观众在短暂停顿后获得第一个具体理由",
    "tempo_change": "accelerate",
    "tempo_reason": "情绪已经成立，下一镜尽快交代钱的意义",
    "hold_before_s": 0.5,
    "settle_after_s": 0.3
  },
  "visual_handoff": {
    "outgoing_frame_anchor": "画面右下方桌面上的香烟和刚收回的手",
    "incoming_frame_anchor": "图形左侧的烟盒符号，以相似横向形状入画",
    "axis_or_gaze_rule": "由右下视觉重点进入下一镜左侧的图形符号，保留竖屏主信息安全区",
    "motion_or_prop_link": "真实桌面香烟转化为图表的扁平图标，靠遮罩衔接而不是强求模型变形",
    "relation": "match_shape"
  },
  "style_handoff": {
    "strategy": "graphic_match",
    "palette_target": "延续低饱和冷灰蓝色，费用数字只用有限暖黄强调",
    "lighting_logic": "真人的左侧窗光在二维图里改成左侧浅色梯度，而不是伪装真实照明",
    "composition_rule": "9:16中轴与底部字幕安全区维持一致",
    "texture_rule": "二维图形边缘清晰，不额外叠加浮夸电影颗粒",
    "typography_rule": "同一套中文字体、字重、字号和平台安全区",
    "implementation": "在后期将人物镜末帧冻结一瞬，以香烟轮廓做匹配剪辑，再展示独立矢量层"
  }
}
```

以上仅示范一个**可能**的导演设计，并不是系统自动生成的最优方案，也不是已审片的真实剪辑；拍摄/效果还需人审。

## 何时是阻断、何时只是提醒

- 未设计合同 / 未填写部分栏位：标记 `pending`，旧片仍可以看不完整草稿；严格交付不能通过。
- 不认识的转场语义、非法节奏、相邻镜头停留时间超出时长：`blocker`。
- 相邻镜头制作路线变化，而导演写 `strategy=preserve`：提示 `MIXED_MEDIA_STYLE_REVIEW`，要求人审对色、画面锐度和排版；不是自动认定不一致。
- 即使全部字段填写，程序也**无法证明**电影语言合理、观众真的感动、画面真的一致。不能输出 AI“艺术评分100分”或未经试片的完成承诺。

## 采用哪些成熟开源方案

- [CineCrew](https://github.com/Ironieser/CineCrew)：FilmDSL 的分镜、人物、统一约束与镜头间关联理念。这里只复用**数据建模思路**，未复制或安装其研究型大模型链。
- [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO)：专业剪辑中时间线、轨道与剪辑对象的分层思想。现阶段无需源媒体/特定软件文件，因此未集成完整库或宣称可导出 OTIO。
- [AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline)：公开 shot-list 中对镜头、动作、对白、旁白、声音、角色与场景分列的交接理念，用于避免“只有漂亮 Prompt”。

## 仍然遵守 GitHub-only

只在公开 GitHub 编写程序、合成测试与演示文档；**没有**在 Mac 安装、下载、同步、运行任何程序，也没有上传用户真实分镜、参考图和 API Key。没有调用收费 DeepSeek/视频 API。真实 13 镜私人导演档仍在用户 Mac，当前无法核验或修改它。

当前只提交代码与新增测试，尚未获得最新完整仓库同一版本的全部测试结果；必须将“代码提交”与“测试通过”区分。
