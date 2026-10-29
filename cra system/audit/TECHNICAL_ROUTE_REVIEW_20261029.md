# CRA技术路线复核

日期：2026-10-29；审查基线：60be8e67f4fa941a4663541351253296e5ee06a4，技术执行版v0.2。审查对象仅为cra system及专属工程入口。

## 结论

总体技术选择和模块化单体可以保留。四阶段共享资料与问题、规则与事实分开、检验自动核对边界、PD分项完成、报告快照及可替换provider等方向符合已确认目标。

当前路线还不是可以不加判断照单实施的冻结规范。发现5项P1和5项P2：它们主要涉及真实数据入口、最高控制的落地、完成证据及阶段契约，而不是需要更换整套框架。W01的数据/权限/事务底座可以继续；相关问题要在对应工作包前补清，不能把开放项当已解决。

本轮是审查和诊断，**没有重排用户已确认的四模块范围、修改45条理论或把任何业务工作包标为完成**。开放项见[机器清单](findings.json)，并给出建议和关闭标准；报告写完、诊断运行成功均不代表这些问题已经修复。

## 第一性原理：什么才算系统达到目标

| 必须成立的条件 | 当前已有基础 | 尚需补清或验证 |
| --- | --- | --- |
| 能取得本次工作的实际输入 | 资料解析、EDC快照、患者事实模型 | 历史报告/track导入及判断所需最低事实；不能只预置JSON演示 |
| 同一个对象与正确依据相对应 | 身份范围、规则版本、匹配和来源 | 完整条件/例外及统一输出控制；真实引文不等于解释正确 |
| 每个临床工作动作有清楚状态 | 分项Action、PD口径、覆盖和报告分开 | 人工演示、自动能力、发布试用与任务verified的边界 |
| 软件行为能够被独立证明 | 30项工程测试和34个场景描述 | 实际任务命令、真实格式、独立评估及具体用途风险门槛 |
| 对CRA产生净收益 | 简记、同源输出和接续方向合理 | 手工补录、匹配确认、复核和返工是否抵消收益 |
| 理论改变能定位增量修改 | 固定编号、指纹和生成视图 | 原最高说明的覆盖遗漏、未导入外部变更及语义判断仍需明确维护责任 |

## 复核依据和范围

开发基线为[业务基线](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/theory/BASELINE.md)、[45条理论](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/theory/requirements.json)、[开发约定](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/AGENTS.md)及当前用户指示。原Notion v0.14第1.1—1.4节用于核对最高共同要求，不能只检查自己整理的45条是否彼此有链接。详见[最高说明覆盖核对](HIGHEST_REQUIREMENTS_COVERAGE.md)。

本轮读取当前架构、数据/API约定、解析方案、16任务及映射、相关模块、同步工具和测试；没有把未实现模块当作已存在功能审查，也未取得IQVIA/ICON内部SOP或对真实项目做合规结论。

外部支持：本轮核对[FDA/EMA良好AI实践原则](https://www.fda.gov/media/189581/download)，其强调明确用途、相称风险控制、全系统及人机表现评价和生命周期管理。产品最高说明已采纳这些控制；这不等于本系统取得监管认证。FDA的[2025年AI可信度文件](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/considerations-use-artificial-intelligence-support-regulatory-decision-making-drug-and-biological)本轮官网仍为草案，未当作统一强制认证程序。

[ICH官方PDF](https://database.ich.org/sites/default/files/ICH_E6%28R3%29_Step4_FinalGuideline_2025_0106.pdf)本轮重新读取超时；本次未据此新增或确认具体法规条款。审查结论主要由项目实际文件、可复现代码行为和成功读取的官方资料支持。

## 风险与状态总览

P1表示在相关功能实现/宣称完成前须补实，不表示当前已发生患者安全事件。P2表示实施歧义或效果风险，应在对应工作包消除。全部为open。

| 编号 | 级别 | 问题 | 主要落点 |
| --- | --- | --- | --- |
| CRA-AUD-001 | P1 | 任务完成标记可以绕过实际功能验证 | CRA-W00、CRA-W01、CRA-W13 |
| CRA-AUD-002 | P1 | 上次报告和track如何成为遗留问题没有明确交付 | CRA-W03、CRA-W06、CRA-W12 |
| CRA-AUD-003 | P1 | 每一次输出的三层约束缺少统一可执行契约 | CRA-W02、CRA-W04、CRA-W09、CRA-W11 |
| CRA-AUD-004 | P1 | 用途风险与全生命周期要求没有完整任务化 | CRA-W04、CRA-W09、CRA-W13、CRA-W15 |
| CRA-AUD-005 | P1 | 人工演示、自动能力和获准试用的完成边界混用 | CRA-W04、CRA-W09、CRA-W13、CRA-W15 |
| CRA-AUD-006 | P2 | M05声明依赖M10，但实现早于M10 | CRA-W06、CRA-W10 |
| CRA-AUD-007 | P2 | 时间锚点、安全上下文与模板输入的最低要求未列清 | CRA-W05、CRA-W07、CRA-W09、CRA-W11 |
| CRA-AUD-008 | P2 | 真实引文和数字一致不足以证明规则提取正确 | CRA-W04、CRA-W09 |
| CRA-AUD-009 | P2 | 34个场景尚缺代表性样本、评判依据和风险门槛 | CRA-W03、CRA-W04、CRA-W08、CRA-W09、CRA-W13、CRA-W14 |
| CRA-AUD-010 | P2 | 人工版能跑通不等于检验核对真正省时 | CRA-W06、CRA-W08、CRA-W11、CRA-W12、CRA-W13、CRA-W14 |

## 云端诊断证据

已在[GitHub Actions](https://github.com/pyzz58/gpt-recommendations/actions/runs/40812829876)实际运行，诊断提交为005338880abd296ab4fede226c32b629494c92f9。现有30项工程测试继续通过；诊断同时复现**未实现任务被接受为完成**：application_commands_executed=false，validator_errors=[]。真实W01状态仍为planned，未修改任何业务任务。结果摘要见[diagnostic-results](diagnostic-results-20261029.json)。

诊断脚本位于[audit/probes/reproduce_review.py](probes/reproduce_review.py)。它只在临时合成仓库伪造W01完成：目标文件为空，命令没有执行，仅更改状态、availability和证据文字，再生成视图并调用当前完整检查。原项目任务和代码不被修改。

另一个静态诊断显示M05在W06开始，却把W10才实现的M10列为模块依赖。这不是已证实运行时有环，而是需要按阶段区分核心/可选能力。

如果未来修复后诊断返回rejected_by_current_guard，应另补关闭证据；不能为保持诊断现象而让错误成为测试要求。诊断退出0仅表示观察被记录，不代表缺陷消失。

## 哪些目标可能达到

以下是工程可行性判断，尚不是实际使用表现：

| 目标 | 当前判断 | 达成条件 |
| --- | --- | --- |
| 遗留问题复核、跨次接续、简单交接 | 可实现，主要为常规持久化及状态设计 | 补历史导入，保留原问题/位置/来源和分项完成 |
| 方案等资料形成分层list | 可实现候选提取与可回查展示；完整性未证明 | 明确输入范围、有限规则语义、独立条件标注、用户复核 |
| EDC与已确认源检验字段核对 | 可实现确定性比对 | 身份和实例正确、必要单位/时间/范围可得；未知不能猜 |
| 检验照片减少抄录 | 具备技术路径，实际格式效果未证明 | 真实格式/质量覆盖、OCR及人工复核评测；支持补录/跳过 |
| AE/PD的基本分析和具体追问 | 可提供有依据的辅助分析，临床用途表现待验证 | 足够事实和项目资料，维度分开、来源校验及适当人员判断 |
| 报告和Excel减少重复整理 | 可实现，需限定支持模板与映射方式 | 实际DOCX/XLSX产物、范围校验、快照与同源状态 |
| 监查总耗时下降 | 当前不能确认 | 比较同一任务的完整总时间和质量，计入导入、补录、复核及返工 |
| 理论变化后局部维护 | 结构定位机制已具备 | 仍需导入源变更、评估语义影响并验证；CI不能代替设计判断 |

OCR和文档解析不是同一种能力。[pdfplumber原项目](https://github.com/jsvine/pdfplumber)明确其优先适用于机器生成PDF；它不能单独证明拍照或扫描检验可稳定识别。选库和架构可行与具体用途可靠分开评价。

## 建议修订顺序

1. **先防止假完成（001）并定义用途/能力验收层级（004/005）。** 让工程检查与真正功能证据连接，保留现有30项反例。
2. **在W03/W04前补输入、规则语义及输出控制（003/007/008/009）。** 给出最小schema和样本，不让Codex各模块自行猜。
3. **在W06前补历史导入并理顺M05阶段依赖（002/006）。** 不需要新建一个大型模块，复用M02/M06服务。
4. **开发中增加小型可用里程碑（010）。** 保留四模块总范围，先让遗留→选信→复核→报告、一个检验实例的通路可操作；不必等所有高级功能后才首次验证价值。
5. W13汇总已持续积累的独立评估，W15核实实际环境及授权后进行限定试用。OCR增强继续按用户允许的方式分期。

净节时应比较：原有查找/核查/记录/报告/返工总时间，减去系统辅助后的导入/映射/识别或补录/匹配确认/复核/输出/返工总时间。手工版本可先验证规则查找、问题接续和报告收益，检验自动节时要另以证据证明。

## CRA-AUD-001 P1 任务完成标记可以绕过实际功能验证

类型：验收机制缺口；状态：open。关联理论：CRA-R039、CRA-R044；模块：M13、M14；工作包：CRA-W00、CRA-W01、CRA-W13。

**观察：** 当前检查验证文件存在、命令availability标记和非空evidence，但不核验该功能命令确实运行成功及其提交版本；空文件加自报证据可能通过。

**为什么影响目标：** Codex可把尚未实现的工作包标verified，下一项选择器随之推进，工程CI绿色不证明该功能完成。

**修订建议：** 保留现有结构检查，增加每任务必须通过的CI job/测试集合及绑定实现提交的机器证据。命令由受控CI运行，不能把tasks.json任意命令直接当可信脚本执行。仍保留人工语义审查。

**关闭标准：** 本轮诊断能被改进后的门槛拒绝；真实最小W01运行成功证据可接受，且不强迫无关任务重复测试。

证据位置：[tools/execution_plan.py:85-122](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/tools/execution_plan.py)；[tools/traceability_lib.py:210-211](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/tools/traceability_lib.py)；[.github/workflows/cra-system.yml](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/.github/workflows/cra-system.yml)。

## CRA-AUD-002 P1 上次报告和track如何成为遗留问题没有明确交付

类型：实际工作入口遗漏；状态：open。关联理论：CRA-R025、CRA-R026、CRA-R027、CRA-R031、CRA-R045；模块：M02、M06、M11；工作包：CRA-W03、CRA-W06、CRA-W12。

**观察：** 资料解析与结构化问题服务分别存在，但没有指定把既有监查报告/Excel track解析、映射、确认并导入原问题的服务、接口和验收。合成预置问题不能代替首次真实接手。

**为什么影响目标：** 用户首日可能仍要手工重建全部遗留，上次是什么、在哪里和怎么改难以可靠接续。

**修订建议：** 在W06增加历史问题导入：复用W03解析，提供报告/track字段映射及确认，保留来源位置、原编号、实际整改和未知；无编号由用户核实关联，不编造处理历史。

**关闭标准：** 从合成的前次DOCX报告和XLSX track进入本次访前信/现场复核，重复导入不重复建问题，旧记录缺项保留待补。

证据位置：[theory/BASELINE.md:目标和工作顺序](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/theory/BASELINE.md)；[plan/tasks.json:CRA-W06](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)；[architecture/modules/M06-issues.md](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/modules/M06-issues.md)。

## CRA-AUD-003 P1 每一次输出的三层约束缺少统一可执行契约

类型：最高约束未完整落地；状态：open。关联理论：CRA-R002、CRA-R009、CRA-R034、CRA-R036；模块：M01、M03、M09、M11、M12；工作包：CRA-W02、CRA-W04、CRA-W09、CRA-W11。

**观察：** 目前主要要求各调用方校验来源/数值/范围，没有统一定义适用共性/项目/中心规则版本、未知和冲突、事实/推断类别及可发布状态的输出结构与责任。

**为什么影响目标：** 模型分析、现场提示和报告可能分别采用不同检查，某一路径绕过共同底线而其他路径仍通过。

**修订建议：** 定义共享OutputEnvelope和按用途校验策略，明确M01范围、M03适用性、业务模块语义及M11覆盖责任；所有模型和确定性结论都走相应检查。允许真实差异、未知和澄清草稿保存，不以输出校验阻止记录问题。

**关闭标准：** 跨患者、过期/冲突依据、假引用、超覆盖措辞分别在所有适用输出路径被识别；合法缺口和真实偏离仍可记录。

证据位置：Notion v0.14:1.4 每一次输出必须受约束；[architecture/API_CONTRACTS.md:共同约定](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/API_CONTRACTS.md)；[architecture/modules/M12-providers.md](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/modules/M12-providers.md)。

## CRA-AUD-004 P1 用途风险与全生命周期要求没有完整任务化

类型：最高说明覆盖不足；状态：open。关联理论：CRA-R036、CRA-R039、CRA-R044；模块：M09、M12、M13、M14；工作包：CRA-W04、CRA-W09、CRA-W13、CRA-W15。

**观察：** 45条已登记需求的映射完整，不证明原最高说明均被提取。按用途的风险记录、独立评估样本、专业审阅、上线后性能/事故监测及暂停回退尚无完整可验收任务。

**为什么影响目标：** 可产出功能齐全的演示，但无法证明具体用途下的可靠性，也可能无法发现模型/规则更新后的退化。

**修订建议：** 建立原最高说明→理论/控制→模块/任务/证据的覆盖表；在M14/W13/W15加入轻量UseCase/Risk/Validation/Release/Monitoring记录，限定具体用途。放在发布验证层，不增加每次监查或PD上报的审批。

**关闭标准：** 关键用途均有错误后果、数据适用性、评估、相应职责和监测/暂停方法；覆盖遗漏明确标open，不能只以45/45自证。

证据位置：Notion v0.14:1.1 十项AI原则及原则落地规则；[theory/source-register.json](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/theory/source-register.json)；[plan/tasks.json:CRA-W13/CRA-W15](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)。

## CRA-AUD-005 P1 人工演示、自动能力和获准试用的完成边界混用

类型：阶段与验收语义不清；状态：open。关联理论：CRA-R035、CRA-R038、CRA-R040、CRA-R044；模块：M12、M14；工作包：CRA-W04、CRA-W09、CRA-W13、CRA-W15。

**观察：** V1A写为完整可试用且模型须配置验证；同时各任务允许DisabledProvider/合成演示，实际模型和环境配置又主要在W15，而W15依赖W13。未定义W13何种能力等级可完成。

**为什么影响目标：** 可能把人工演示当完整自动版，或在未部署与先验收之间形成流程性等待。不是已证明的运行时死锁，而是实施歧义。

**修订建议：** 拆开code-complete、synthetic-validated、provider-validated、authorized-trial-ready等能力状态。W13可以完成明确范围的离线/合成验收；真实provider配置测试必须有具体落点；获准环境及实际试用由W15确认，不互相替代。

**关闭标准：** 无模型时允许的功能、不能宣称的能力、W13和W15各自完成证据清楚，且无循环等待。

证据位置：[architecture/SYSTEM.md:62-64](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/SYSTEM.md)；[plan/tasks.json:CRA-W13/CRA-W15](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)。

## CRA-AUD-006 P2 M05声明依赖M10，但实现早于M10

类型：依赖描述歧义；状态：open。关联理论：CRA-R001、CRA-R026、CRA-R032、CRA-R033；模块：M05、M10；工作包：CRA-W06、CRA-W10。

**观察：** M05在W06开始，声明依赖M10；M10在W10才开始，而W10依赖W06。模块图与工作包图各自无环，但合在一起没有区分阶段可选依赖。

**为什么影响目标：** Codex可能提前做W10、用假服务冒充完成，或误认为无法开始W06。

**修订建议：** 区分核心硬依赖与W10启用的可选中心文件能力，按阶段列出公开端口及未启用状态；W06不需要已实现全部M10。

**关闭标准：** W06核心场景可独立运行，W10接入后不改已存问题/核查状态；依赖检查认识阶段能力。

证据位置：[traceability/modules.json:M05 depends_on](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/traceability/modules.json)；[plan/tasks.json:CRA-W06/CRA-W10](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)。

## CRA-AUD-007 P2 时间锚点、安全上下文与模板输入的最低要求未列清

类型：输入契约不够具体；状态：open。关联理论：CRA-R010、CRA-R011、CRA-R014、CRA-R018、CRA-R029、CRA-R034；模块：M02、M04、M07、M09、M11；工作包：CRA-W05、CRA-W07、CRA-W09、CRA-W11。

**观察：** 笼统写EDC/源记录或人工输入，未给各项判断必须具备的事实和导入字段契约。检验导出未必含输注/治疗锚点；AE相关判断还需要相应历史/评价。实际模板也没有支持范围和映射规格。

**为什么影响目标：** 模块有API仍可能缺少可用输入，只能反复追问，或无依据推断日期、范围和医学上下文。

**修订建议：** 逐用途列required/optional facts、允许来源、身份/时间精度、缺失结果与一次性人工补充入口；补充ContextImport及TemplateMapping的最小schema与支持格式。仍不扩大非检验源数据OCR。

**关闭标准：** 缺锚点/缺病史/缺模板字段的输入被明确处理；合成Excel、报告和模板能从文件进入完整流程，而非只预造JSON。

证据位置：[architecture/DATA_MODEL.md](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/DATA_MODEL.md)；[architecture/API_CONTRACTS.md](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/API_CONTRACTS.md)；[plan/tasks.json:CRA-W05/CRA-W07/CRA-W09/CRA-W11](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)。

## CRA-AUD-008 P2 真实引文和数字一致不足以证明规则提取正确

类型：推理和证据验证不足；状态：open。关联理论：CRA-R006、CRA-R007、CRA-R008、CRA-R009；模块：M03、M09、M12；工作包：CRA-W04、CRA-W09。

**观察：** 现有校验重点为锚点存在、片段归属、数字可追溯；一条含且/或和例外的原文即使漏掉前提，仍可能引用真实原文并保留同一个数字。规则AST的最小语法和unknown运算亦未明确。

**为什么影响目标：** 系统给出有出处但逻辑错误的清单；仅看摘要的用户不易发现漏条件。

**修订建议：** 先定义有限Rule AST、单位/区间/时间精度和三值逻辑；用独立标注的合成/获准规则比较完整条件和例外；无法稳定结构化的保留人工分析型规则，不强行自动判定。

**关闭标准：** 真实引文但漏前提、颠倒否定、丢例外、且改或等反例被识别；通过不只取决于引用存在。

证据位置：[architecture/AI_AND_PARSING.md:21-23](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/AI_AND_PARSING.md)；[plan/tasks.json:CRA-W04](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)。

## CRA-AUD-009 P2 34个场景尚缺代表性样本、评判依据和风险门槛

类型：验证设计待补；状态：open。关联理论：CRA-R007、CRA-R015、CRA-R019、CRA-R044；模块：M03、M08、M09、M14；工作包：CRA-W03、CRA-W04、CRA-W08、CRA-W09、CRA-W13、CRA-W14。

**观察：** 场景有描述但没有完整输入/预期/依据/样本来源/独立评估划分；本轮30项是工程反例，不含真实格式或临床用途性能证据。

**为什么影响目标：** 开发者可针对示例写对，换格式或项目后遗漏和误匹配仍未知；不能据此承诺可靠自动核查。

**修订建议：** 尽早建立去标识获准或忠实合成的文档/Excel/图片/模板样本，区分开发和独立评估；按用途明确关键错误与复核标准。W13汇总，而非最后才第一次测试数据适用性。

**关闭标准：** 样本和预期可复核，测试集分离，关键错误与总体表现分别记录，覆盖外用途清楚。

证据位置：[traceability/scenarios.json](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/traceability/scenarios.json)；[plan/tasks.json:CRA-W13/CRA-W14](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)；Notion v0.14:1.1 原则8。

## CRA-AUD-010 P2 人工版能跑通不等于检验核对真正省时

类型：价值与实施顺序风险；状态：open。关联理论：CRA-R028、CRA-R035、CRA-R037、CRA-R044、CRA-R045；模块：M05、M08、M11、M14；工作包：CRA-W06、CRA-W08、CRA-W11、CRA-W12、CRA-W13、CRA-W14。

**观察：** V1A先人工输入源字段，可能增加抄录和确认时间；完整价值串联主要在W12/W13。后置OCR是用户允许的分期，但不能因此认为最耗时的一致性核查目标已经达到。

**为什么影响目标：** 系统功能按计划完成，用户反而多录入；较晚才发现匹配、模板或使用路径不适合。

**修订建议：** 保留四模块范围与编号，增加早期可用里程碑和端到端小样；先验证遗留→选信→复核→报告及一个检验实例。测总时间，识别未就绪时如实将节时收益限定在规则查找、记录和报告。

**关闭标准：** 同一任务原流程与新流程总耗时可比，计入导入/补录/复核/返工，用户实际操作反馈决定迭代。

证据位置：[architecture/SYSTEM.md:62-64](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/architecture/SYSTEM.md)；[plan/tasks.json:CRA-W08/CRA-W12/CRA-W13/CRA-W14](https://github.com/pyzz58/gpt-recommendations/blob/60be8e67f4fa941a4663541351253296e5ee06a4/cra%20system/plan/tasks.json)。

