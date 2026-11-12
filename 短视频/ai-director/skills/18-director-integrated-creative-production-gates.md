# 第18号导演专业规范｜QO-D10 × QO-D06 × QO-D12 总导演唯一创作闭环

**身份及范围：** 一位总导演，原十专业岗位；三个模块是同一个导演必须兼备的判断能力，不创建第二个导演Agent、不架设第二套编剧权威或任务数据库。

**本轮进度：** 源码和规范的静态融合阶段。用户要求先不测试，故不主动运行单元/CI/模型/媒体/人类盲评，不向主分支合并尚未验证的代码。GitHub既有自动工作流可能触发，不能将其视为新代码已审核完成。

## 1. 避免三种误用

- **QO-D10整片艺术自评**不替代编剧，不执行拍摄也不产生“世界一流”评定。它判断导演的方案为何真正服务主题、人物、观众认知与情绪；明确哪些独特镜头必须保留、哪些导演错误需要自己改、哪些事实/对白必须交给编剧、哪些尚需真实媒体才能评价。
- **QO-D06动作可拍性**不是纯物理动作检测或编剧改稿权。它在保持观众可见人物选择/行为结果的条件下，为同一镜头设计不同执行路径，锁定出演员、道具、手部、空间轴线和声画衔接；现有 `director_shootability.review` 只用于已有实际岗位交付的风险重算，结果不能冒称模型真拍成功。
- **QO-D12版本治理**不是又一个创作岗位。它根据导演或各部门反馈执行变更**权限边界**：未改原正式剧本的专业修改走原 `agent_team.request_revision` 定点返工；故事、人物决定、真实事实、原对白或正式分集结构发生变化时，只能向编剧发审核请求，新文本必须另建干净的十岗位团队与全新导演锁，旧媒体仅成为需人类重新审查的候选。

## 2. 单一导演的有序创作流程

```text
原稿（用户私有）→ 原剧本编剧改编/逐场说明/作者审阅
                         ↓
        已绑定版本的权威完整剧本、总导演开题与锁稿
                         ↓
        现有QO-D17艺术手法选择 + QO-D15制作会
                         ↓
        现有QO-D03逐镜具体视听语言
                         ↓
                【制作前导演创作门槛】
        QO-D10 preproduction_plan  ← 跨镜、整片艺术自审
        QO-D06 before_specialist_design ← 每镜动作/摄影/剪辑备选
                ↓ 检验完全相同的来源、导演锁、会议、
                   视听稿、艺术方法和镜头ID
        ├─ 必须改事实/人物/原台词：STOP→ QO-D12 编剧
        ├─ 必须改镜头、节奏、视觉母题：STOP→ 同一导演重审
        ├─ 动作方案存在结构阻断：STOP→ QO-D06重新设计
        └─ 已充分说明方案、仅剩真正媒体问题：允许
           【只是艺术指导/专业方案计划】的下游部门工作
                         ↓
           原十岗位模型请求中的七个下游专业角色
           演员/摄影/声音/剪辑/AI技术/QA/导演终审
                         ↓
                【部门交稿后的整片再审】
        QO-D10 post_department_design ← 对已提交设计批评
        QO-D06 after_specialist_design ← 实际动作表与技术路径
              ↓ 重新运行原 shootability 离线风控、
                 锁定实际部门revision与交付摘要
        QO-D16原同导演逐镜逐部门验收（可选接入）
                         ↓
             具体、无自动执行的修订建议单
                         ↓
         QO-D12 版本化修改提案→编剧 / 原DAG专业返工
                         ↓
        真实视频生成、真人专业审片、版权、出版授权
                  【仍是后续独立门禁】
```

## 3. 共同权威和版本失效

`director_creative_integration.preproduction_receipt()` 实际调用已有完整合约：
- `director_department_command.validate_command(base,state,meeting)`
- `director_visual_language.validate(base,state,meeting,av_plan,...)`
- `director_whole_film_critique.validate(...,holistic)`
- `director_action_rescue.validate(...,rescue)`

强制比较两套导演结论中的 `source_digest`、`base_digest`、`director_lock_digest`、`department_command_digest`、`audiovisual_language_digest`、`artistic_methods_digest`、`shot_ids`。任何差异拒绝，不允许一份来自旧人物关系、另一份来自新镜头。

**发现并修复的融合缺陷：** QO-D10原草稿制作前快照把尚未完成的专业部门状态也绑定；正常的演员/摄影交付后，制作前导演美学决定会被错误判“过时”。融合版明确：`preproduction_plan`只绑定已锁源剧本、导演锁、专业会议、视听与艺术方法，不依赖未来正常交稿；`post_department_design`才绑定专业部门状态、版本和实际提交摘要。QO-D06此前已有相同的“制作前独立于后续部门变化、制作后绑定实交付”边界，融合后两者一致。

源故事、导演锁稿、导演会议、视听方案或选中艺术方法**任何一个变化**，都必须重做相应导演判断。制作后如专业交付被修改，旧制作后评审作废。不允许只因为导演给新方案换了个“最新版本”文件名就继续发送旧指令。

## 4. 向实际岗位消息和岗位交稿作成对验证

实际适配位置：`agent_role_contracts.build_role_messages`（真实 role-facing 私有消息构造）及 `validate_role_output`、`submit_role_output`（接收已有专业结果前的强制复验）。新增可选 `holistic_critique` 配合已有 `action_rescue_plan`。

**严格新项目**显式在**建立新ledger前**给 `base` 设置：

```json
{
  "director_integrated_creative_mode": {
    "kind": "director_integrated_creative_review_required",
    "before_specialists": true
  }
}
```

将该base与相同已锁专业会议、视听稿、艺术方法和两份制作前导演审查分别传给专业岗位消息生成器及回执校验器。在 `director_command.DEPARTMENTS` 的七个下游角色：任一缺少holistic或rescue会拒绝，任一源版本/镜头不同会拒绝；即使两者各自格式合法，若QO-D10仍有待编剧/导演实质修改或QO-D06动作仍需重新设计，也不允许拿未解决问题继续派发。**这是创作过程一致性，不是影片完成或导演艺术水平认证。**

旧base完全没有此mode时兼容原有十岗位路线；已有只声明`director_action_rescue_mode`的项目按原QO-D06可选路径继续，不会被新门槛强迫补填全片艺术审查。

在每个现有专业角色的 model-facing 消息里，通过 `director_creative_integration.departmental_context` 发送：
- 总导演整片思想与预期的观众经历；
- 每镜哪些独特视听创意不可被机械改成通用B-roll；
- 为什么人物关键动作必须让观众看见、删掉会损失什么；
- 源锁定的 QO-D06 动作方案digest与QO-D10整片意见digest；
- 本角色的专业关注点、尚未通过真人视频验证的客观限制。
详细动作时刻、手与道具、摄影、声轨等完整制作路线仍由既有 `director_action_rescue.departmental_context` 提供；编剧修改仍只能走原审稿流程，不得把它变成部门自行修改原文的许可。

若已有QO-D10问题尚未解决，`preproduction_receipt`拒绝专业部门下发，只有“已充分说明、暂时等待真实媒体验证”的艺术不确定性可以以**未完成**状态继续专业设计；绝不可把它写成已经看过成片。

## 5. 制作后评审与具体修订权

`postproduction_assessment` 不执行拍摄，不生成新导演Agent，它同时校验 QO-D10 `post_department_design` 和QO-D06 `after_specialist_design`，后者从已提交的演员与AI技术设计运行原离线 `director_shootability.review`。结果只输出尚待解决的逐镜问题、导演艺术问题、已知动作风险及源/导演锁版本，不将文字稿评审冒充真实AI视频成片审看。

如QO-D10提出具体问题，由 `make_lineage_change_from_finding(...)` 转为 QO-D12 **未派发**修改请求：
- `return_to_screenwriter` 只能显式分类为剧本/事实/结构更改：编剧完成新稿及必要审核，不能导入旧部门已完工状态。
- `director_revise` 发起现有 `director_lock` 文档级返工提案，不能私自改变权威剧本。
- `department_refine` 对演员、摄影、声音、剪辑、AI技术中的具体负责人提出定点修订。
- `defer_until_media_review` 不可虚构有问题的专业交付，也不应为了完成评分强迫改视频。

特别注意 `make_lineage_change_from_finding` 仍**不会调用** `agent_team.request_revision`，不会批准故事改写。使用者必须另外明确选择同版专业返工；将真实编剧改变交给可靠私有的审核流程。总导演不能以“拍起来更容易”作为无授权改变编剧内容的借口。

## 6. 未完成项目清单

- 综合代码/专业规范已形成，**不等于**代码经过单元测试、真实模型联动或媒体审片。当前不启动这些验证。
- 独立QO-D10/06/12三项原草稿分别在 PR #62 / #65 / #66；本统一开发分支把其源代码、三份原技能规范和接口协调集中，避免将来互相独立并入main导致冲突。
- 若要启用严格模式，调用方须持有实际的`holistic_critique`与`action_rescue_plan`。设计新模式字段并不意味着旧项目的base会被自动重写。
- 版本号、结构校验与trace链可以阻断确定的违规，但无法自行评价动机是否深刻、反转是否成立、演员是否动人、真实模型是否拍得出来、或是否存在版权/隐私问题。独立审片与作者审批仍不可替代。
- QO-D10、QO-D06、QO-D12继续标记`in_progress`，原合成媒体已证明的部分不受改变，未进行实拍的QO-D11仍是`blocked_external`。
