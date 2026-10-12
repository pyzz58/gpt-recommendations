# AI 短视频导演系统

**输入文案，完成导演设计，通过第三方视频 API 制作镜头，经审片、逐镜返工和剪辑合成交付短视频。** 手动导出制作包保留为备用路径。

这是产品目标，当前尚未完成真实成片闭环。现有专业导演编译能力已保留，本轮纠正了旧文档只停在图纸的目标，并补上 Seedance 单镜接口。

## 质量优化阶段（当前最高优先级）

**目标：国际优秀编剧与导演职业标准 × AI 短视频实际生成特点。** 先完整审计和提高前置编剧、总导演的质量；未来其他部门同样审计，但不得因现有测试通过而自称达标。优先修复真实问题，不新增无用 Agent。

- [质量优化总纲：目标、岗位边界、AI 视频约束、完成门槛](quality-optimization/QUALITY_CHARTER.md)
- [QO-W01：职业编剧一手资料全文深读与既有模块逐项审计](quality-optimization/QO-W01_PROFESSIONAL_PRIMARY_SOURCE_AUDIT.md)：解释优秀改编与机械保留的区别，先审计方法、再设计创作流程；结构代码 PR #24 暂缓合并。
- [QO-W01：编剧创作开发能力实际升级](quality-optimization/QO-W01_CREATIVE_DEVELOPMENT_IMPLEMENTATION.md)：读稿诊断 → 不同影视化 take → 独立选案比较 → treatment → 剧本及独立适配审核，核心实现 [screenplay_development.py](screenplay_development.py)；未完成专业真人盲评。
- [独立问题清单：32 项逐条根因、解决方案、验收、状态和修复历史](quality-optimization/QUALITY_ISSUES.md)
- [逐批解决路线：先编剧、再总导演，其他部门持续登记](quality-optimization/EXECUTION_PLAN.md)
- [机器可读问题总账](quality-optimization/QUALITY_ISSUES.json)：改动一个问题就更新一条，CI 拦截无证据假完成、漏问题和状态表不同步。
- [质量阶段 GitHub 总入口 Issue #22](https://github.com/pyzz58/gpt-recommendations/issues/22)：讨论与跨任务导航；真实状态以 JSON 为准。
- 原有 [技术/安全审计](AUDIT_FINDINGS.json) 继续独立生效；媒体未实测、账号未授权均不能被本轮优化消除。


## 国际编剧质量与导演分工

- [国际编剧与导演职责审计](SCREENWRITER_INTERNATIONAL_AUDIT_2026-10-13.md)：对照 Nicholl、Sundance、BBC、Scriptnotes、BAFTA、DGA 的创作标准和职责，并公开现有流程的专业缺陷、已修与待修项。
- [原创编剧工作 Skill](skills/07-professional-screenwriter.md)：小说/纪录片/科普观点分别改编，完整场次与视听动作、独立剧本审阅、定点返修、给导演的清晰权限边界；不保证自动达到一流质量。

## 编剧到导演的独立交接

- [编剧直接交付既有总导演](SCREENWRITER_DIRECTOR_HANDOFF.md)：将经过逐项审阅的完整剧本作为导演岗位的正式 source 文本，保留台词、旁白、场次、剧情动作和来源；不增加导演或视频 Agent。完整小说被旧入口截断时禁止冒充已完成全稿改编。身份可信审核和实际创作质量仍未实测。

## 本轮可检查的结果

- [单镜制作操作流程](SINGLE_SHOT_WORKFLOW.md)：已接入现有程序，串联准备、提交、查询、下载与审片记录，并提供只读审阅页。尚未部署，不是已完成网页控制台。

- [API 路线审查](SEEDANCE_API_AUDIT.md)：已修问题、接口范围、剩余缺口和实际验证证据。
- [S02 的 8 秒 API 请求候选](examples/dinner-dialogue-review/seedance_s02_request.json)：精确对白、生成参数和后期交接可审阅；未授权费用、未发请求、无参考图或真实视频。
- [《先吃饭》48 秒对白导演稿](examples/dinner-dialogue-review/director_workbook.md) 与 [《门后的信》60 秒导演稿](examples/door-letter-review/director_workbook.md)：公开虚构候选，当前会话创作并离线编译，不是十岗位自动创作质量证明。

## 已有与未完成

现有程序能保留故事、表演、摄影美术、剪辑、对白/旁白/音效、字幕和后期安排，导出模型请求候选。新增 seedance_adapter 可在未来授权私人环境显式执行单镜提交、查询和下载；现已接入统一命令行入口和只读审阅页；未部署网页控制台或自动执行器。制作包和后期工作单现完整保存 speech，时间线明确出镜/画外对白。

**仍需完成：真实账号和私人运行环境、参考素材上传/绑定、单镜与跨镜视听验收、局部返工版本选择、实际解码和整片合成。** 当前无真实生成，不以测试通过宣称影片好看。

隔离 Linux/Python 3.12 全量609项通过，本轮新增17项流程回归（上一轮接口新增19项）；GitHub CI 以对应提交 Actions 为准。问题主账29项：15项回归修复、5项确认开放、6项待调查、3项待真实媒体验证；AUD-002/Issue #1 保持P0。

| 入口 | 用途 |
| --- | --- |
| [产品目标](PRODUCT_NORTH_STAR.md) | 从文案到成片的完整边界 |
| [当前计划](PRODUCT_REVIEW_PLAN.md) | 从 S02 单镜验证到跨镜、返工和合成 |
| [问题主账](AUDIT_FINDINGS.json) | 已修和未完成的可核查状态 |
| [开发边界](GITHUB_ONLY_DEVELOPMENT.md) | 当前仅源码研发，未部署到 Mac |
| [开发指令](AGENTS.md) | 当前决定优先于历史阶段排期 |
| [历史 README](HISTORY_README.md) | 历史说明，不作为当前运行授权 |
