# 完整技术实施路径

技术执行版0.5。本页由plan/implementation.json与plan/tasks.json生成，任务卡是各项代码交付入口。设计完成不等于应用已实现。

先读[第一性原理复核](../audit/FIRST_PRINCIPLES_REVIEW_V04.md)、[总技术路线](../architecture/IMPLEMENTATION_ROUTE.md)和[Codex入口](../CODEX_START_HERE.md)。

## 按阶段推进

| 阶段 | 工作包 | CRA实际能得到什么 |
| --- | --- | --- |
| P0 工程基线与完成证据 | CRA-W00 | 设计可追溯，未实现任务不能凭状态标记放行。 |
| P1 可靠保存与工作台外壳 | CRA-W01、CRA-W02 | 进入正确项目/中心，操作可保存和恢复。 |
| P2 资料、条件清单与患者上下文 | CRA-W03、CRA-W04、CRA-W05 | 规则可读、可展开、有版本，缺资料可局部跳过。 |
| P3 遗留与自动检验核对 | CRA-W06、CRA-W07、CRA-W08 | 旧问题接续与点击确认；检验源文件和Excel自动对照。 |
| P4 异常支持、目录和材料 | CRA-W09、CRA-W10、CRA-W11 | 具体异常问题、简单目录、四阶段清单和可用报告。 |
| P5 全流程与独立验收 | CRA-W12、CRA-W13 | 两次监查连续操作，明确错误、人工负担和总耗时。 |
| P6 复杂检验格式增强 | CRA-W14 | 扩大已有自动读取范围，不重建比对和历史。 |
| P7 获授权环境和实际反馈 | CRA-W15 | 在明确用途和资料范围内试用，记录反馈与暂停恢复。 |

P6为复杂格式增强，P7需实际授权环境。默认继续沿V1A按W01—W13推进，不自动增加付费服务、实际部署或非检验OCR。

## 每项的进入条件和交接

### [CRA-W00 建立技术基线与同步检查](work_packages/CRA-W00.md)

状态：verified；前置：无。

进入条件：原工程基线有实际云端证据。

交接产物：同步工具和完成证据门槛；不代表业务完成。

技术输入：[task_evidence.py](../tools/task_evidence.py)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)

专属CI：CRA-W00。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W01 建立数据、权限和历史记录底座](work_packages/CRA-W01.md)

状态：in_progress；前置：CRA-W00。

进入条件：W00已有证据，完成声明使用新的任务专属CI门槛。

交接产物：数据迁移、授权/事务API、可重现依赖及cra-w01真实数据库CI。

技术输入：[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W01。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W02 建立云上API和界面框架](work_packages/CRA-W02.md)

状态：in_progress；前置：CRA-W01。

进入条件：W01迁移与隔离测试实际通过。

交接产物：可登录的合成工作台、真实API、能力状态、OpenAPI和前端类型。

技术输入：[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W02。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W03 实现资料接收、解析和来源定位](work_packages/CRA-W03.md)

状态：in_progress；前置：CRA-W02。

进入条件：API、私有文件接口和持久事务可用。

交接产物：文件/锚点/作业接口，合成资料集和OCR依赖/资源可行性探测记录。

技术输入：[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[LAB_AUTOMATION.md](../architecture/LAB_AUTOMATION.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W03。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W04 实现规则候选提取及分层list](work_packages/CRA-W04.md)

状态：in_progress；前置：CRA-W03。

进入条件：已解析原文、处理覆盖及授权提取端口可用。

交接产物：候选规则树、用户修正、版本启用解析及独立条件反例结果。

技术输入：[WORKFLOW_CONTRACTS.md](../architecture/WORKFLOW_CONTRACTS.md)、[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W04。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W05 实现患者事实、锚点与核查断点](work_packages/CRA-W05.md)

状态：in_progress；前置：CRA-W04。

进入条件：规则版本和三值逻辑可用，准备患者上下文合成表。

交接产物：患者/锚点/分类断点及缺口拒绝/恢复契约，日期精度和来源保留。

技术输入：[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[WORKFLOW_CONTRACTS.md](../architecture/WORKFLOW_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W05。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W06 实现遗留整理、提醒与点击确认整改](work_packages/CRA-W06.md)

状态：in_progress；前置：CRA-W05。

进入条件：事实、来源与规则接口可用，完整M10非前置。

交接产物：历史文件整理→遗留提醒/展开→点击确认→下次接续，正式Query与草稿区分。

技术输入：[WORKFLOW_CONTRACTS.md](../architecture/WORKFLOW_CONTRACTS.md)、[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W06。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W07 实现EDC Excel检验快照导入](work_packages/CRA-W07.md)

状态：in_progress；前置：CRA-W05。

进入条件：患者映射及快照范围契约可用。

交接产物：真实Excel输入、可复用列映射和不可变标准检验快照。

技术输入：[LAB_AUTOMATION.md](../architecture/LAB_AUTOMATION.md)、[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W07。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W08 实现检验源文件自动读取与EDC核对](work_packages/CRA-W08.md)

状态：planned；前置：CRA-W06、CRA-W07。

进入条件：W06/W07通过；W03探测已给出可安装、可运行的识别候选，支持格式和代表性评估输入已确定。

交接产物：自动源文件读取→匹配→比较→差异/未知与待办、实际provider证据、人工负担和支持范围。

技术输入：[LAB_AUTOMATION.md](../architecture/LAB_AUTOMATION.md)、[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W08。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W09 实现有依据的AE及PD分析](work_packages/CRA-W09.md)

状态：planned；前置：CRA-W04、CRA-W06、CRA-W08。

进入条件：自动比较结果、规则依据与已有安全上下文可用；缺项允许明确保留未知。

交接产物：按项目标准区分医学维度的候选分析、具体问题及必要及时线索，不自动作最终医学结论。

技术输入：[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W09。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W10 实现中心文件目录和其他阶段清单](work_packages/CRA-W10.md)

状态：planned；前置：CRA-W04、CRA-W06。

进入条件：原目录文件与M06问题服务可用。

交接产物：原目录直接对照及简单缺件状态，启动/关闭/交接复用已有资料和问题。

技术输入：[WORKFLOW_CONTRACTS.md](../architecture/WORKFLOW_CONTRACTS.md)、[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W10。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W11 实现访视信、报告和Excel导出](work_packages/CRA-W11.md)

状态：planned；前置：CRA-W06、CRA-W09、CRA-W10。

进入条件：问题/覆盖/分析事实接口可用，合成DOCX模板与Excel字段映射明确。

交接产物：可打开的模板信件、监查报告、track及不可变快照，多份输出同一事实。

技术输入：[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W11。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W12 串联四阶段界面与一次完整监查](work_packages/CRA-W12.md)

状态：planned；前置：CRA-W08、CRA-W09、CRA-W10、CRA-W11。

进入条件：既有各模块服务及页面实际可用，完整场景使用真实API和临时PostgreSQL。

交接产物：两次监查浏览器流程、刷新/重登/切中心/重试不丢状态，缺口和异常不混同。

技术输入：[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W12。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W13 完成自动检验主线验收与试用准备](work_packages/CRA-W13.md)

状态：planned；前置：CRA-W12。

进入条件：W12端到端通过，开发样例与独立评估已分离。

交接产物：40场景实证、逐用途能力/风险记录、自动覆盖和总耗时、明确可试用范围与未达标结论。

技术输入：[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[LAB_AUTOMATION.md](../architecture/LAB_AUTOMATION.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W13。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W14 增强复杂检验格式与识别效果](work_packages/CRA-W14.md)

状态：planned；前置：CRA-W08。

进入条件：W08已有自动读取，当前范围的错误及负担记录可复用。

交接产物：复杂格式新增SupportProfile和独立回归；既有业务数据不变。

技术输入：[LAB_AUTOMATION.md](../architecture/LAB_AUTOMATION.md)、[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W14。具体代码目标、步骤、命令和完成标准见上方任务卡。

### [CRA-W15 配置受控云部署并开展授权试用](work_packages/CRA-W15.md)

状态：planned；前置：CRA-W13。

进入条件：W13工程验收已汇总，实际服务和资料范围获授权；试用范围要求的provider证据有效。

交接产物：受控环境、恢复演练、实际试用、总时间和反馈及能力暂停恢复记录。

技术输入：[VALIDATION_AND_RELEASE.md](../architecture/VALIDATION_AND_RELEASE.md)、[EXECUTION_CONTRACTS.md](../architecture/EXECUTION_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../architecture/REUSE_ASSESSMENT.md)

专属CI：CRA-W15。具体代码目标、步骤、命令和完成标准见上方任务卡。

## 可观察里程碑

| 里程碑 | 前置工作包 | 必须看到的实际证据 |
| --- | --- | --- |
| CRA-MS01 可靠工作台 | CRA-W01、CRA-W02 | 合成两中心数据的API保存/重登/隔离及事务测试 |
| CRA-MS02 资料能成为可用list | CRA-W03、CRA-W04、CRA-W05 | 文件→真实来源→条件分支list/版本启用→患者阶段和缺口选择；包含实际提取模型和OCR环境探测 |
| CRA-MS03 遗留工作可接续 | CRA-W06 | 旧报告/track→遗留提醒/展开→直接确认→未完事项保留，重复导入不复制 |
| CRA-MS04 核心自动核对 | CRA-W07、CRA-W08 | 检验文件+Excel→实际自动识别/匹配/比较→差异待办，自动覆盖和人工负担实测 |
| CRA-MS05 监查结果可交付 | CRA-W09、CRA-W10、CRA-W11 | 异常依据/目录对照/阶段清单→模板DOCX报告及XLSX，历史快照不变 |
| CRA-MS06 第一版工程验收 | CRA-W12、CRA-W13 | 真实API浏览器连续两次监查、40场景/独立样本/全部耗时，给出限定范围结论 |
| CRA-MS07 实际试用 | CRA-W15 | 获准环境、恢复演练、实际CRA操作与反馈，达到已声明用途的试用条件 |

## 完成证据和能力边界

W00保留历史工程基线证据。W01以后verified必须绑定实际源码/任务规范指纹、精确测试提交、GitHub run及任务专属job/步骤；基础CI或自报文字不能代替。详见[验证与发布](../architecture/VALIDATION_AND_RELEASE.md)。

工程完成、合成/provider评估和获授权临床试用分别记录。开发任务通过不代表所有格式、所有项目或医学结论可靠，支持范围以实测SupportProfile和能力清单为准。

## 仍需实测

- 代表性检验格式的关键字段/身份/日期错误及人工负担尚未验证。
- 规则前提/分支/例外提取的完整性尚未验证。
- 整体节时、授权环境和临床用途可靠性尚未验证。
