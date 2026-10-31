# CRA系统综合开发审查｜2026-11-01

## 结论

整体产品方向和主技术框架保留，不需要推倒重建。Codex已经交付真实的数据库、接口、前端和实际provider调用，检验自动核对仍在W08主线，范围没有扩展到用药/样本。

**但当前不能接受“W01—W09的业务要求已全面满足”。** 本轮登记13项开放发现（10项P1、3项P2，含代码错误、核心能力范围缺口及近期需求追踪），其中8项通过14个独立合成组件反例得到复现，另5项为源码/任务审查。它们的关闭标准分别列在下文。P1表示应优先纠正的开发问题，不表示已经发生真实受试者伤害；本轮没有真实临床数据或临床使用。

尤其需要修复：人工更正回退、未知被判定、窗口条件丢失、中心启用日受阻，以及检验一致但异常的安全线索丢失。原先任务卡对“支持子集/模拟方案”的代表性要求仍不够具体，允许高度定制格式通过，审核也需要补充这些验收边界。

## 审查快照与事实

- 仓库：`pyzz58/gpt-recommendations`，项目：`cra system`。
- 主分支：`12dfeb8eb0172857533e607746dce6c34fce7933`；CRA仍是此前设计/工程基线。
- 实际开发分支：`codex/cra-w01-governance-20261031`。不能仅看main判断未开发。
- 先检查W01—W08交付快照`1ff52eb1c91ccc312cc03aab9700d00fb378b217`；审核期间新增W09源码`df6f04b4c321f133f80dff07afa24c0974266927`，一并审查。
- W09记录快照`137786b3088ce57a1d660b6a47e2ce070dfc2796`已把W01—W09记为verified，下一项为W10。df6→137只改文档/任务证据，所审W09运行代码未变；1ff→df6未修改本轮核心反例涉及的旧业务函数。
- 最高说明：Notion主文v0.14（最后编辑2026-10-29），结合Git的最新八点决定及本对话后续澄清。旧文中增加整改证明的内容不优先于用户后续“CRA点击确认即可”。
- 45条固定理论源文件在本轮Codex开发前后保持同一Git blob。任务核心目标/完成标准没有被整体删减，但实现和验收仍可能不足。
- 原始方案、IB和真实病历没有提交或用于本轮探针。

原始最高说明：[Notion主文](https://app.notion.com/p/4070782f004581ea84f4e6ef46e5fc68)。本次核对其产品控制要求，未重新进行所有外部法规的现行性核验，不能将本文作为法规认证或法律适用结论。

## 已证实的工程进度与保留项

| 区域 | 读到的实现/证据 | 审查判断 |
| --- | --- | --- |
| W01/W02底座 | PostgreSQL迁移、租户/中心授权、并发revision、幂等、审计、Authlib、真实API和React壳 | 有实质实现，抽查路径和既有CI支持；没有作完整生产安全认证 |
| W03资料与原文 | 私有文件、来源锚点、DOCX/PDF解析、Job/Outbox及Procrastinate、S3测试 | 主线合理，可作为知识库基础；OCR新路径不应绕过队列 |
| W04规则 | 不可变规则版本、来源、用户增删、有限AST、启用区间 | 底层有用；自然资料入口、三值逻辑和中心采用仍有缺陷 |
| W05患者/窗口 | 结构化事实、身份映射、分类断点、局部跳过 | 有实质实现；条件、未知和确认语义须修复 |
| W06遗留 | 历史导入预览、稳定Issue/Action、一次点击整改、PD上报独立、Query期限依据、访前选择 | 保留了用户简化流程；未增加CRC证明附件或审批门槛 |
| W07 EDC | 实际XLSX读取、多sheet/公式缓存、映射、范围、不可变快照 | 有实质实现；未见把本次导出未见直接作为EDC漏录的比较判定 |
| W08自动检验 | 文字PDF实际读取、Docling实际图像识别、字段/实例匹配、Decimal比较、复核和M06关联 | 自动路径真实存在；仅有限合成格式，存在更正/范围/上下文/异步问题 |
| W09安全 | 九个维度、程序规则、受限Qwen调用、证据校验、CRA/医学答复分开、M06关联 | 已有代码；输入衔接、上下文和能力等级有实质缺口 |
| W10—W15 | 仍planned：目录/阶段、报告、整体验收、格式增强、授权部署试用 | 当前缺少它们属于正常开发进度，不单独判作跑偏；不得宣称已完成完整第一版 |

本次看到的开源复用符合主路线：Authlib、boto3、Procrastinate、AG Grid Community、React-PDF、openpyxl等。Paddle在Linux探测失败后改用实际通过的Docling，有保留失败证据，属于合理适配。W11的docxtpl尚未进入实际交付，不据此指责没有使用。

## 最高思想逐项检查

| 最高说明要求 | 当前判断 | 相关发现/后续 |
| --- | --- | --- |
| 以人为中心、医学职责清楚 | CRA/医学/程序分开保存的方向正确；窗口结果被写成CRA已确认需改 | 03、11、12 |
| 按具体用途和风险管理 | 发布/授权试用仍保留后续门槛；响应格式通过不等于能力验证 | 12；W13/W15 |
| 按法域、事件日及三层依据适用 | 版本/范围有底层对象；中心采用与下游继承未完整实现 | 03、04、12 |
| 用途及允许范围清楚 | 文档如实写有限子集，但过窄子集不能代表实际核心功能满足 | 05、07、11 |
| 多学科职责、人工最终判断 | 未看到系统自动作最终医学签署或自动关闭行动；应保留 | W09现有职责边界 |
| 数据来源、权限和版本 | 私有来源及审计有实质实现；有效更正和事件归属需要修复 | 01、13 |
| 可复核数值/逻辑、稳健设计 | Decimal/有限AST合理；关键分支存在可复现错误 | 02、03、06、08 |
| 独立验证和真实减负 | 实际provider评估存在；样本代表性与整个人机总耗时未验证 | 05、07；W13/W15 |
| 生命周期、变更与恢复 | 源码绑定CI及重新验证机制有改进；provider环境/任务恢复需补 | 08、09 |
| 清晰透明的依据、状态和局限 | 多数交付文档坦承限度；部分运行时标签与实际语义不一致 | 03、12 |

## 云端证据：绿色CI与业务正确性分别判断

- 原W01—W08交付快照：[run 41193688723](https://github.com/pyzz58/gpt-recommendations/actions/runs/41193688723)，9个job成功。日志确认43项基础测试、8项源码绑定完成证据，下一项W09。
- W09实现快照：[run 41196248119](https://github.com/pyzz58/gpt-recommendations/actions/runs/41196248119)，10个job成功；W09/平台API测试10项通过，实际模型评估3个合成案例通过。模型实际只选服务端允许的解释模板与证据ID，不能把这一结果解释为独立临床推理已验证。
- W09证据记录提交：[run 41196595963](https://github.com/pyzz58/gpt-recommendations/actions/runs/41196595963)，成功。
- 本轮独立反例：[run 41196720274](https://github.com/pyzz58/gpt-recommendations/actions/runs/41196720274)，执行提交`6f4b4810de3c41cb980c09b07c2f20f1a89fbcfa`；10个W04—W08反例及4个W09边界反例均复现。两段各自固定被审源码；W09通过云端detached worktree读取df6，不修改活动开发分支。
- 审查分支原有工程回归：[run 41196720321](https://github.com/pyzz58/gpt-recommendations/actions/runs/41196720321)，成功。此处基于1ff旧底座；不能冒称它是整个最新W09的又一次完整回归，W09完整工程证据是上述df6工作流。

**反例工作流成功表示诊断执行成功，并不表示功能通过。** 输出明确`acceptance_passed=false`，所有发现仍open。原测试绿色与反例发现错误可以同时成立：源码绑定证明了相应代码实际被测过，并不证明测试覆盖了全部业务含义。

首轮诊断因审核脚本漏填必需的authentication_source而中断，随后补齐并重跑成功。该次审核夹具错误不记为产品缺陷；完整运行史见[结构化记录](REVIEW_20261101_FINDINGS.json)。

14个反例调用实际业务组件；部分命令以合成授权来源或服务端口替身隔离数据库。它们不是完整API/浏览器/真实OCR/临床验收。具体证据种类和正确关闭所需的真实API回归分别记录，不能用这些组件诊断代替修复后的集成验证。

## 发现与逐项关闭要求

### CRA-REV-20261101-01｜P1｜确认和后续局部更正会丢失先前人工更正

状态：open；证据：源码与合成组件反例。对应CRA-W08；理论CRA-R016、CRA-R034、CRA-R038、CRA-R041。

实际场景：CRA把识别值121改成119，之后点击确认或批量确认，有效值回到原来的121；再次只改单位也可能丢掉数值更正。

源码：[backend/cra_app/laboratory/service.py:176](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/service.py#L176)；[backend/cra_app/laboratory/service.py:225](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/service.py#L225)；[backend/cra_app/laboratory/service.py:988](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/service.py#L988)；[web/src/features/laboratory/RecognitionReview.tsx:169](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/web/src/features/laboratory/RecognitionReview.tsx#L169)。

修正要求：把有效值修订与核实/跳过状态分开，或者按有序事件折叠完整更正链；确认不能恢复原OCR值，补丁应作用于当前有效版本。

关闭标准：

- 真实API和PostgreSQL验证：更正→单项确认、更正→批量确认、连续两次局部更正，值始终保留。
- 刷新、重登、重新比较及源输入修订后仍一致；原识别值和审计历史保留。

### CRA-REV-20261101-02｜P1｜未知例外和缺失单位仍能产生确定性规则结果

状态：open；证据：源码与合成组件反例。对应CRA-W04、CRA-W09；理论CRA-R007、CRA-R034。

实际场景：例外是否适用还没取得资料，规则已显示适用；一侧没有单位，也可以与带单位阈值直接判真。

源码：[backend/cra_app/rules/evaluator.py:63](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/rules/evaluator.py#L63)；[backend/cra_app/rules/evaluator.py:251](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/rules/evaluator.py#L251)。

修正要求：明确前提、触发、例外及分支的三值合成次序；依赖的例外未知时保留不确定性，所需单位缺失时禁止直接数值判定。

关闭标准：

- 否则适用+例外未知→unknown；确定不适用的前提不被例外覆盖。
- 带单位比较覆盖两侧单位一致、缺失、冲突；合法无量纲比较仍可运行。

### CRA-REV-20261101-03｜P1｜访视窗口丢失适用条件、未知状态和真实确认语义

状态：open；证据：源码与合成组件反例。对应CRA-W05、CRA-W09；理论CRA-R002、CRA-R007、CRA-R011、CRA-R034。

实际场景：只有条件A成立才需检查，A不成立仍生成窗口任务；实际日期是未知文字时可能显示超窗；程序算出的窗口结果被标为CRA已确认。

源码：[backend/cra_app/subjects/service.py:1596](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/subjects/service.py#L1596)；[backend/cra_app/subjects/service.py:1690](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/subjects/service.py#L1690)；[backend/cra_app/subjects/service.py:1844](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/subjects/service.py#L1844)；[backend/cra_app/subjects/calendar.py:71](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/subjects/calendar.py#L71)。

修正要求：区分适用门槛和待核查的窗口断言，保存分支/例外上下文；未知实际日期保留unknown，自动计算与CRA确认分开，继承上游规则未知/冲突。

关闭标准：

- 有/无前提、C→B/D→F、例外、嵌套且或/否定的窗口在实际API上验证。
- 不能简单过滤所有not_applicable：窗口超界可能是待发现的偏离，须区分适用条件与被检验条件。
- 未知实际日期不成超窗；未点击核实不写cra_confirmed；共性资料未知不在下游消失。

### CRA-REV-20261101-04｜P1｜共享项目方案不能设置某中心的实际启用日

状态：open；证据：源码与合成组件反例。对应CRA-W04、CRA-W05；理论CRA-R002、CRA-R005、CRA-R011、CRA-R041。

实际场景：方案属于整个项目，A中心1月开始用，B中心2月开始用；当前命令直接拒绝给项目级文件设置某个中心启用日。

源码：[backend/cra_app/rules/service.py:1513](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/rules/service.py#L1513)。

修正要求：分开文件/规则的归属与版本的实际采用范围；项目方案仍是项目规则，共享原件可以有各中心采用区间，避免要求逐中心复制或改称中心规定。

关闭标准：

- 同一文档版本在两个中心不同日期采用，按事件日准确选择，起始日含当天。
- 项目默认、中心采用、真实冲突、更正影响和历史输出边界均有测试，不能一律取最新或更严。

### CRA-REV-20261101-05｜P1｜规则语义入口仍依赖专门编写的格式和英文标识

状态：open；证据：源码与合成组件反例。对应CRA-W04、CRA-W09；理论CRA-R003、CRA-R004、CRA-R006、CRA-R007、CRA-R008、CRA-R018、CRA-R045。

实际场景：正常中文方案/邮件尚不能直接形成有用list；当前识别器要求Rule/规则编号、前提、触发、分支等格式。新增安全模块还依赖SAE/GRADE等英文标题或编号片段识别用途。

源码：[backend/cra_app/providers/rule_extraction.py:32](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/providers/rule_extraction.py#L32)；[backend/cra_app/providers/rule_extraction.py:506](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/providers/rule_extraction.py#L506)；[backend/cra_app/rules/service.py:694](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/rules/service.py#L694)；[backend/cra_app/safety/service.py:114](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L114)；[backend/cra_app/safety/service.py:219](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L219)；[backend/cra_app/providers/case_worker.py:24](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/providers/case_worker.py#L24)。

修正要求：保留有限AST作为执行器，增加直接消费普通资料的语义提取入口并记录覆盖；用明确、可确认的规则用途元数据路由安全维度。无须为使用AI而使用AI，但必须证明实际资料能减少整理工作。

关闭标准：

- 用普通中文段落、访视表格、脚注及自然语言Q&A构成独立合成集，不能先人工改写成专用DSL再验收。
- 原句含应/需/不得等要求时，不能因不合语法就静默标成非规则。
- 中文规则不靠英文编号仍进入正确维度；实际规则和事实能生成具体判断理由/问题，四句通用解释模板不能单独代表该能力完成。

### CRA-REV-20261101-06｜P2｜参考范围只比异常标志，漏掉范围本身不一致

状态：open；证据：源码与合成组件反例。对应CRA-W08；理论CRA-R016、CRA-R034。

实际场景：结果都为10，源参考上限20、EDC上限30，两侧都在范围内，当前总结果仍显示一致。

源码：[backend/cra_app/laboratory/comparison.py:418](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/comparison.py#L418)。

修正要求：把上下限、比较符、单位及缺失状态作为独立比较字段；范围标志作为额外逻辑检查。补清已解析报告日期等字段的比较范围。

关闭标准：

- 上下限不同但标志相同、只有一侧有范围、单侧边界、不可读边界均不能丢失。
- 数值/单位一致与其他字段差异分开显示，输出措辞与本次实际覆盖一致。

### CRA-REV-20261101-07｜P1｜检验报告页眉上下文不能复用到结果行

状态：open；证据：源码与合成组件反例。对应CRA-W08、CRA-W13；理论CRA-R010、CRA-R013、CRA-R015、CRA-R035、CRA-R044、CRA-R045。

实际场景：识别结果已取得页眉里的受试者和采样日，但逐行提取只找表格列；结果每行不重复身份/日期时，都会变成待手填。

源码：[backend/cra_app/laboratory/recognition.py:249](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/recognition.py#L249)；[backend/cra_app/laboratory/recognition.py:354](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/recognition.py#L354)；[validation/LAB_AUTOMATION_SCOPE.md:1](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/validation/LAB_AUTOMATION_SCOPE.md#L1)。

修正要求：增加报告级身份/日期上下文及一次性绑定确认，经来源和范围校验后供各结果行复用；不能直接凭当前打开患者把无身份文件强行归属。

关闭标准：

- 支持至少一种接近实际工作的清晰中文合成报告：身份在页眉、结果在表格；保留原件/字段区域和歧义。
- 加入同日复查、修订、缺少显式初复检标签等代表性情形；测量每份报告的总确认和补录负担。
- 现有英文定制PDF和单张PNG确有实际识别结果，应保留；它们不单独证明实际拍照流程可用。

### CRA-REV-20261101-08｜P1｜检验OCR绕过既有异步队列，阻塞上传请求且无法可靠续跑

状态：open；证据：源码/任务审查，未独立做运行时复现。对应CRA-W03、CRA-W08；理论CRA-R035、CRA-R036、CRA-R045。

实际场景：上传后页面要等OCR全部完成；进程中断后，同一请求重试找到已有pending/running报告就返回，当前没有接续识别路径。

源码：[backend/cra_app/laboratory/api.py:276](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/api.py#L276)；[backend/cra_app/laboratory/service.py:576](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/service.py#L576)；[backend/cra_app/laboratory/service.py:609](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/laboratory/service.py#L609)；[backend/cra_app/providers/lab_ocr.py:252](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/providers/lab_ocr.py#L252)。

修正要求：复用持久Job/Outbox和Procrastinate，将识别移到worker，API尽快返回作业引用，页面查询状态；补授权复查、租约、幂等、异常恢复和输出版本检查。

关闭标准：

- 上传期间其他请求可服务；杀worker、超时、断网重试后同一任务可恢复且无重复候选。
- 保存来源版本和作业尝试，撤权后禁止继续读取/输出；失败/停机不永久卡在running。
- W09如有耗时模型推理，也采用同一约定。

### CRA-REV-20261101-09｜P2｜隔离provider仅固定顶层包，完整依赖和OCR模型未锁定

状态：open；证据：源码/任务审查，未独立做运行时复现。对应CRA-W03、CRA-W08、CRA-W09；理论CRA-R038、CRA-R044。

实际场景：同样的应用代码以后重新运行，OCR底层依赖或默认模型可能变化，之前的评估不能直接证明新环境表现。

源码：[backend/cra_app/providers/lab_ocr.py:230](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/providers/lab_ocr.py#L230)；[backend/cra_app/providers/lab_worker.py:98](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/backend/cra_app/providers/lab_worker.py#L98)；[backend/cra_app/providers/case_analysis.py:98](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/providers/case_analysis.py#L98)；[validation/PROVIDER_FEASIBILITY.md:1](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/validation/PROVIDER_FEASIBILITY.md#L1)。

修正要求：为隔离环境提供完整锁文件/固定镜像与模型标识或哈希，把这些版本纳入provider输出及评估证据；保留W09已固定的Qwen模型revision。

关闭标准：

- 缓存清空后可重建相同依赖/模型，记录引擎、模型、资源限制和许可范围。
- 不是要求现在部署生产；W15部署前仍需真实环境许可、恢复和运行验证。

### CRA-REV-20261101-10｜P2｜iPad/电脑与资料知识库的近期讨论尚未完整进入CRA任务验收

状态：open；证据：源码/任务审查，未独立做运行时复现。对应CRA-W02、CRA-W03、CRA-W04、CRA-W12、CRA-W15；理论CRA-R003、CRA-R039、CRA-R045。

实际场景：已有资料库底层；但iPad拍照/触控、换设备接续、资料搜索和有效版本展示等没有作为明确整体验收。

源码：[plan/tasks.json:1](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/plan/tasks.json#L1)；[architecture/SYSTEM.md:1](https://github.com/pyzz58/gpt-recommendations/blob/1ff52eb1c91ccc312cc03aab9700d00fb378b217/cra%20system/architecture/SYSTEM.md#L1)。

修正要求：登记本对话中明确的设备场景；将知识库建议区分为已确认需求与待确认设计，落实到原有模块和任务，不另建不相连的大平台。

关闭标准：

- 形成讨论→理论/设计→任务/测试的对应关系；支持范围与离线边界明确。
- 至少验证iPad上传/查看/确认、电脑Excel核对、两端同一记录接续和弱网中断恢复。
- 本项是近期需求追踪，不追认此前已经验收，也不要求现在扩展临床OCR到其他资料。

### CRA-REV-20261101-11｜P1｜W09把数据差异作为安全入口，遗漏一致但异常的结果，并重提已跳过或陈旧字段

状态：open；证据：源码与合成组件反例。对应CRA-W08、CRA-W09；理论CRA-R016、CRA-R017、CRA-R018、CRA-R019、CRA-R034、CRA-R041、CRA-R045。

实际场景：源与EDC都记录同一个超参考范围结果时，检验安全入口直接跳过；用户局部不核查仍会重新产生AE问题；已因更正失效的旧对照也被继续消费。

源码：[backend/cra_app/safety/service.py:1007](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L1007)；[backend/cra_app/safety/service.py:1046](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L1046)。

修正要求：将数据一致性、异常/趋势线索、医学所需上下文和用户核查决定分开；一致的异常也保留为安全事实，跳过仅停止对应路径，陈旧字段需重算或显式标为旧依据。

关闭标准：

- 一致且正常、一致但异常、不一致、无法比较、用户跳过、来源更正导致stale，逐项做真实API联调。
- AE未提供不写无AE；医学规则按项目实际版本；数据质量差异本身不直接当AE。局部跳过不屏蔽其他独立已知安全事实或紧急提示，只停止依赖被跳过输入的对应路径。
- 从检验事实到规则判断和具体提问的路径有独立代表性案例，不仅依赖人工预填grade_criteria_met等结果性标志。

### CRA-REV-20261101-12｜P1｜W09未完整继承适用上下文，并将一次模型输出通过当作能力已验证

状态：open；证据：源码/任务审查，未独立做运行时复现。对应CRA-W04、CRA-W09、CRA-W13；理论CRA-R002、CRA-R034、CRA-R036、CRA-R044。

实际场景：安全查询未提供法域而落到synthetic默认；共性资料未知没有并入下游unknowns；模型回复符合格式就把能力写为validated；请求来源固定写pure_synthetic。

源码：[backend/cra_app/safety/service.py:1217](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L1217)；[backend/cra_app/safety/service.py:1139](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L1139)；[backend/cra_app/safety/service.py:1302](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L1302)；[backend/cra_app/safety/service.py:1452](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L1452)。

修正要求：使用可信研究配置确定法域/范围，继承上游未知和冲突及状态；分开单次响应结构校验、能力验证记录与临床用途；数据来源由真实元数据/环境控制决定。

关闭标准：

- 共性资料缺失/草案/不适用、规则冲突、法域配置有反例且在最终页面/输出可见。
- 响应accepted不能自行升级能力验证等级；实际用途证据与模型/规则/输入版本绑定。
- 非合成请求不会被代码虚标为pure_synthetic；生产接入仍受W15授权环境限制。

### CRA-REV-20261101-13｜P1｜W09事实集合未绑定具体事件和访视

状态：open；证据：源码/任务审查，未独立做运行时复现。对应CRA-W05、CRA-W09；理论CRA-R010、CRA-R011、CRA-R015、CRA-R018、CRA-R034。

实际场景：安全分析读取受试者所有当前事实，再按fact_key合并；多个AE或访视可混在一起，重复键全变歧义，单个其他事件的事实也可能进入本次判断。

源码：[backend/cra_app/safety/contracts.py:34](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/contracts.py#L34)；[backend/cra_app/safety/service.py:574](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L574)；[backend/cra_app/safety/service.py:606](https://github.com/pyzz58/gpt-recommendations/blob/df6f04b4c321f133f80dff07afa24c0974266927/cra%20system/backend/cra_app/safety/service.py#L606)。

修正要求：增加明确的事件/访视及事实用途范围，区分当前事件事实、纵向相关历史、后来取得的补充结论；按来源和时序选择，无法归属则明确待核实。

关闭标准：

- 同一患者两个AE、同一指标跨访视、同日复查以及历史事件后补医学意见均有独立测试。
- 不能简单丢弃所有后来记录：事件发生、观察、录入和后补确认时间分别保留，并建立具体归属。

## 给Codex的修正顺序

1. 先处理01/02/03/04/06及11的确定性业务错误，同时补13的事件归属；修复后用真实API、临时PostgreSQL和必要前端流程验证，不能只改文案或增加mock。
2. 对08恢复队列与中断重试，09固定实际provider依赖/模型。W09耗时调用也复用既有作业约定。
3. 05/07补接近实际工作输入的语义提取和报告上下文。无需承诺任意文档，但不能要求用户大规模改写方案或重录检验。开发集和独立评估集分开，记录漏条件、错值、错配及总复核负担。
4. 修正12的共同约束继承、来源与能力等级；把10中的明确设备场景及知识库待确认设计登记到正确位置。
5. 按原证据约定，将受影响的verified任务及其依赖链置in_progress、保留completion_history，再做源码绑定的实际专属CI和独立反例。关闭发现要附新源码、运行及覆盖范围，不直接用“基础检查通过”关闭。
6. 然后继续原W10→W11→W12→W13。报告未实现、真实iPad与全流程未验收、实际节时未知，不能因为W09已有代码而提前宣布完整第一版可用。W14增强格式、W15授权部署/试用仍按既定边界。
7. 不增加整改附件/二次审批，不扩展用药/样本OCR，不为了知识库另搭一套与患者/规则/问题分离的平台，不替用户作最终医学判断。共性/项目/中心要求仍按实际适用关系处理。

审查记录与活动分支分离，本文没有修复产品代码、修改任务完成状态或合并main。Codex处理前应先读取其最新HEAD，核对本轮固定源码是否已经被后续修正；已经修好的项提供新证据即可，不重复实现。

## 历史审查与覆盖限制

2026-10-29登记的10项CRA-AUD开放记录仍保留历史。此轮没有逐项执行其全部关闭标准，不能将本文13项与旧10项简单相加或声称旧项全部解决。源码绑定、M10可选依赖和自动核心W08确实有进展；语义正确性、输出约束、代表性与总工作负担仍须实际验证。

本轮覆盖最高说明、最新已确认业务、完整任务/模块关系、W01—W09关键调用路径、接口/存储边界、测试/独立provider日志及上述合成反例。没有执行真实试验核查、外部发送、EDC写回、生产部署、完整浏览器/iPad验收或全量临床法规核查。公开仓库继续只存代码与合成资料。

机器可读发现及原始诊断输出见[REVIEW_20261101_FINDINGS.json](REVIEW_20261101_FINDINGS.json)；可交给Codex的简短接续指令见[CODEX_REMEDIATION_20261101.md](CODEX_REMEDIATION_20261101.md)。
