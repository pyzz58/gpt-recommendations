# 技术关联与变更检查

本文件从最高说明唯一原文机械生成，请勿手工修改。理论、模块/路线正文与逻辑标注都只在最高说明维护。

**CURRENT_BINDING仅表示本次关联版本一致；不证明方案正确、程序已实现、内容已审或获准运行。**
理论或设计/依赖改变会变为REVIEW_REQUIRED；重新生成只刷新事实，不自动改写技术正文或批准新基线。

当前规范SHA-256：`5b6e5f86c85ba193edeb99f8e7c578dd5432245a5ce1f6cd7cd9d2dab851b5f6`。

需复核节点：无；仅限关联新鲜度检查。

| 节点 | 设计原文 | 关联状态 | 责任/阶段 | 实现范围 |
|---|---|---|---|---|
| [R01](#r01) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r01) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | C01—C05共用主题闭环，六单元适配尚未实现；理论职责与真实成刊仍待验 |
| [R02](#r02) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r02) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | 共用C02 Theme/版本与C03/C04跨周接续；实际成熟/入刊未实现验收 |
| [R03](#r03) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r03) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | 共用C01/C02/C04/C05处理不同稿型，不为短稿另建流水线；业务路线未实现 |
| [R04](#r04) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r04) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | C04发定向缺口，C03路由C01/C02与编辑复选；条件研究适配须实测，路线未实现 |
| [R05](#r05) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r05) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | C02同一版本/依赖/限制+C03受控恢复；当前复用与历史回放分别验，业务路线未实现 |
| [R06](#r06) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r06) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | T12组织双输入并共用C01—C05，无年度存储/研究/渲染分叉；年度业务未实现 |
| [R07](#r07) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r07) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | 已有文档关联维护继续；研究任务原文装载/分段与C03持久恢复仍待实现，不由摘要恢复 |
| [R08](#r08) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-r08) | CURRENT_BINDING | 对应流程中注明的L层/技术模块责任；沿§19.2原四阶段；文档关联现可检查 | C06 Actions只设周开始+C03长任务续跑+C02期号/回执+C05文件；生产/已授权交付待实现 |
| [T01](#t01) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t01) | CURRENT_BINDING | 执行者组织；未来执行层维护决定；人工定位先行；第二阶段控制器 | C02提交/Review/AdoptionDecision追加版本与W15分离决定接口已离线实现；身份认证、完整研究图、LangGraph持久恢复和端到端采用仍未实现 |
| [T02](#t02) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t02) | CURRENT_BINDING | L1发现职责；第一阶段人工取样；第四阶段生产增量 | W20已离线实现feedparser/Trafilatura/JSON API受控字节入口、CandidateIndex、取得元信息、字段/时间缺口和失败记录，并持久到C02；W21已实现强键事件归并提案、来源血缘/独立根、编辑歧义和探索队列；W22已实现预固定独立参照、范围限定的覆盖比较与七类缺口；W23已消费候选/事件簇/覆盖审计，保存S0—S8取舍。真实来源运行与T03真实内容复核仍待后续 |
| [T03](#t03) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t03) | CURRENT_BINDING | L2编辑决定；第一阶段人工；第二阶段记录和接口 | C04编辑任务+C02决定+C03 S依赖；W22提供独立参照与覆盖缺口接口，W23已离线实现S0—S8前后决定、S8前置包的实对象绑定、研究准入与刊登准入分离及显式期次建议；分值不自动产生准入或拼刊，真实编辑取舍和W24—W26闭环待验 |
| [T04](#t04) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t04) | CURRENT_BINDING | L3取证/中文核对；第一阶段实际回源；第二阶段适配 | C01已离线复用Trafilatura解析获准HTML字节，并支持纯文本定位；W24持久SOURCE_MATERIAL、SOURCE_STRUCTURE、SOURCE_INTAKE及RIGHTS_RECORD，正文保存、机器处理和后续翻译分别核权。PDF/Docling/OCR尚未接入，复杂原件只保留与显式缺口；提取不代内容核真 |
| [T05](#t05) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t05) | CURRENT_BINDING | L4联合研究组织；B1/B2从早期参与；第一阶段分步研究；第二阶段可重跑组织 | W16同一Theme修订/输出链接/组合提交与CAS冲突边界已离线实现；C03完整M图、C04研究函数及真实模型内容仍待实现 |
| [T06](#t06) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t06) | CURRENT_BINDING | L4顾问职责；第一阶段真实研判；后续按任务验证 | C04 B1任务共用C02/C03和模型接口；实际顾问贡献待内容验收 |
| [T07](#t07) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t07) | CURRENT_BINDING | L4帝师职责；从M02参与；第一阶段真实教学；后续按任务验证 | C04 B2任务共用C02/C03和模型接口；主动知识研究/自足教学仍待独立验收 |
| [T08](#t08) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t08) | CURRENT_BINDING | L4的C与M12准备；当期保存条件；真实结果后来再核 | C04条件任务+C02 ThesisVersion/Theme；无独立预测平台，真实成果待验 |
| [T09](#t09) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t09) | CURRENT_BINDING | L5独立核查；不自签；第一阶段实际核查；第二阶段能力配置验证 | C04独立核查+C01回源+C02版本+C03返工；W19已离线实现模型/任务配置身份、给定材料/检索/约束增益验证记录和有限使用准入，作者与审稿决定分离。真实审稿能力、模型调用与业务闭环未实现 |
| [T10](#t10) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t10) | CURRENT_BINDING | L6主编/呈现；新命题回L4/L5；第一阶段实际格式；第四阶段正式渲染/交付 | C05 Jinja+第四阶段WeasyPrint，复用年度呈现；内容/实际文件对应未实现验收 |
| [T11](#t11) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t11) | CURRENT_BINDING | 六层共享档案职责；第一篇保存；第二阶段跨周；第四阶段持久恢复 | C02 Pydantic/SQLAlchemy+私有版本文件；共享依赖/双as-of/纠错待实现，图检查点不是事实库 |
| [T12](#t12) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t12) | CURRENT_BINDING | 年度A01—A12组织；复用六层；第四阶段缩区间演练；全年另验 | 年度双输入/A工序只组织C01—C05现有能力；无第二套引擎，年度成果待实现验收 |
| [T13](#t13) | [原文](CANONICAL_SYSTEM_SPEC_V5.md#tech-t13) | CURRENT_BINDING | 实际工具执行与配置记录；不替内容裁决；受控使用先行；二/三/四阶段逐步验证 | W17 OperationRequest/Receipt、Adapter返回校验、UNKNOWN对账与逻辑操作累计已离线实现；W18调用前能力/材料/外发/重试门禁、共享预算预留结算与未知保留已离线实现。真实第三方认证/适配、生产预算恢复和Actions周运行未实现 |

## R01

设计目的：当周深度主题到周刊

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：C01—C05共用主题闭环，六单元适配尚未实现；理论职责与真实成刊仍待验。

理论出处：[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T02、T03、T04、T05、T06、T07、T08、T09、T10、T11、T13；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R01.F01 / T02 发现与初筛 | 原始来源和时期；条件：有合法真实线索 | 候选/血缘交T03 | 成功：T03；失败：T02 | [§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)；池外抽查另有范围 |
| R01.F02 / T03 初选、取证与S8 | S7计划与T04实际包；条件：四硬门和有边界研究输入成立 | 研究准入与稿型 | 成功：T04/T05；失败：T04/T03 | [§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)；不在S8前要求已完成原因解释 |
| R01.F03 / T05 联合研究与中文接续 | 入选原作/中文和同一案卷；条件：M依赖、实际专业条件与未知明确 | B1/B2及C和复查准备 | 成功：T06/T07/T08；失败：T04/T05 | [§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)；帝师从问题期参与，不只接终稿 |
| R01.F04 / T09 核实际读者稿 | 真实全文、证据/方法和版本；条件：独立检查和问题处理完成 | 注明范围的Review | 成功：T10；失败：T04/T05/T07 | [§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；绑定版本；不从字段齐全自签PASS |
| R01.F05 / T10 核整刊与实际文件 | 专题、卷首、S6取舍和更新；条件：新综合已审、呈现对应 | 完整刊物或明确未达门 | 成功：T11；失败：T03/T09 | [§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；单篇通过不等于完整样刊通过 |

验收：按§25.5原路线与理论定义作真实流程/正反验收；当前检查不代替内容或运行通过。

## R02

设计目的：跨周研究与长期专题

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：共用C02 Theme/版本与C03/C04跨周接续；实际成熟/入刊未实现验收。

理论出处：[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§16.5](CANONICAL_SYSTEM_SPEC_V5.md#th-16-5)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T03、T04、T05、T06、T07、T08、T09、T10、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R02.F01 / T03 给予研究准入 | 长期问题和关键取证；条件：仍重要且足以开始有边界研究 | Theme问题及S8研究决定 | 成功：T05；失败：T04/T03 | [§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)；研究准入不占本期名额 |
| R02.F02 / T11 保存未决与接续 | 有效中间产物、限制和下一动作；条件：真实进展/触发可核 | 背景版本与合理重开条件 | 成功：T05；失败：T11 | [§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§16.5](CANONICAL_SYSTEM_SPEC_V5.md#th-16-5)；不每周重跑全部历史题 |
| R02.F03 / T05 新材料下继续或收口 | 具体新观察或到期问题；条件：下一动作有辨别价值且获准 | 成熟研究、有限成果或有据暂停 | 成功：T03；失败：T04/T05 | [§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)；停止不冒称原问题解决 |
| R02.F04 / T03 重新核本期资格 | 实际贡献、当前重要性和新鲜度；条件：当周新增或合格长期DEEP_THEME | 本期取舍与类型 | 成功：T09/T10；失败：T05/T11 | [§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)；长期失去深度且无新增，不自动改精选发出 |

验收：按§25.5原路线与理论定义作真实流程/正反验收；当前检查不代替内容或运行通过。

## R03

设计目的：精选/首次事实/进展/更正分支

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：共用C01/C02/C04/C05处理不同稿型，不为短稿另建流水线；业务路线未实现。

理论出处：[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T03、T04、T09、T10、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R03.F01 / T03 确定具体稿型 | 原作价值、事实和旧文关系；条件：publication_basis及update_kind准确 | 当前要交的内容责任 | 成功：T04；失败：T03 | [§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)；首次事实无旧文如实说明 |
| R03.F02 / T04 查证、S8后制作中文 | 实际原件、权利及阅读范围；条件：相应事实和中文方案可核 | 精选/事实稿及局限 | 成功：T09；失败：T04/T03 | [§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)；不强配完整课程 |
| R03.F03 / T09 按真实职责审核 | 该稿全文和必要依据；条件：事实/权限/表达责任达到 | 有效审核或具体返工 | 成功：T10；失败：T04 | [§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)；不因缺不相关历史而误拒 |
| R03.F04 / T10 与整刊深度一起核 | 合格短稿及其他当期稿件；条件：全刊仍达到使命且更正依赖已处理 | 入刊/暂缓及原稿归档 | 成功：T11；失败：T03/T05 | [§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)；更正转R05；不能全刊短讯化绕过深度 |

验收：按§25.5原路线与理论定义作真实流程/正反验收；当前检查不代替内容或运行通过。

## R04

设计目的：定向补证与复选

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：C04发定向缺口，C03路由C01/C02与编辑复选；条件研究适配须实测，路线未实现。

理论出处：[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T03、T04、T05、T06、T07、T09、T11、T13；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R04.F01 / T05 定位具体缺环 | 主张、专业条件或审稿疑点；条件：必要性和预期辨别作用明确 | 带版本的补证问题 | 成功：T04；失败：T05 | [§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)；不只说多找来源 |
| R04.F02 / T04 取得并核新依据 | 原件/方法/比较材料路径；条件：相应用途允许且实际核对 | 实际补证/限制及支持范围 | 成功：T05；失败：T04 | [§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)；补到材料不自动升置信度 |
| R04.F03 / T05 对照原解释与依赖 | 旧/新材料和问题版本；条件：支持、反对或仍不可区分已说明 | 维持/收窄/修订及采用限制 | 成功：T03/T06/T07；失败：T04/T05 | [§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)；只重核实际受影响部分 |
| R04.F04 / T03 必要时回S8 | 对象/价值/范围/类型变化；条件：相应刊登依据与投入已重核 | 继续、改型或暂停接续 | 成功：T05/T09；失败：T11 | [§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)；冻结评测不禁止真实补证；比较条件变化另记 |

验收：按§25.5原路线与理论定义作真实流程/正反验收；当前检查不代替内容或运行通过。

## R05

设计目的：更正、复用与历史隔离

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：C02同一版本/依赖/限制+C03受控恢复；当前复用与历史回放分别验，业务路线未实现。

理论出处：[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T04、T05、T06、T07、T08、T09、T10、T11、T12；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R05.F01 / T11 先限制已知关键用途 | 旧新版本、变化和实际用途；条件：有证据说明相关支持可能失效 | 受限范围及未确定事项 | 成功：T04/T05；失败：T11 | [§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)；不等全链查完才限制；疑点不直接判全假 |
| R05.F02 / T11 追直接与传递依赖 | 真实引用用途和剩余支持；条件：限定检索范围和不相关对照明确 | 实际影响/漏检/误限清单 | 成功：T04/T05；失败：T11 | [§16.6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-2)、[§16.6.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-3)；图关系不全时如实留未覆盖 |
| R05.F03 / T09 核修复及恢复范围 | 新依据、修订和受影响上下文；条件：事实/解释/教学及呈现责任达到 | 新审核、维持/缩小/撤回/未决 | 成功：T10/T11；失败：T04/T05 | [§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16.6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-2)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；不能只改状态或旧Review哈希 |
| R05.F04 / T11 区分当前采用与历史请求 | 具体用途及as-of模式；条件：新稿核现时限制，旧文返回当时版本 | 有效指向与另列的更正 | 成功：T05/T12；失败：T11 | [§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)；后补资料不得进入旧判断实际依据 |

验收：按§25.5原路线与理论定义作真实流程/正反验收；当前检查不代替内容或运行通过。

## R06

设计目的：年报双输入

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：T12组织双输入并共用C01—C05，无年度存储/研究/渲染分叉；年度业务未实现。

理论出处：[§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T02、T03、T04、T05、T06、T07、T08、T09、T10、T11、T12、T13；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R06.F01 / T12 固定两路年度材料 | 实际周刊/缺期与独立原件；条件：报告年、资料截点和覆盖明确 | A01—A03输入及旧原话 | 成功：T12；失败：T04/T11 | [§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)；只读周刊不合格 |
| R06.F02 / T12 核时间线、指标和旧判断 | 可比口径、新结果和原先条件；条件：后见信息与当时依据隔离 | A04—A07补漏/纠错/未决 | 成功：T05；失败：T04/T11 | [§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)；不按结果倒填当时知识 |
| R06.F03 / T05 年度新研究与教学 | 年度事实、边界和有效旧知识；条件：当前支持及跨题连接可核 | A08—A11顾问/帝师及条件路径 | 成功：T09；失败：T04/T05 | [§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)；旧周刊批准不覆盖新综合 |
| R06.F04 / T10 审核后制作年报 | 新Review、重收权限与实际文件；条件：A12版本和呈现对应 | 年报、索引和归档 | 成功：T11；失败：T09/T04 | [§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；缩区间演练不冒称全年能力 |

验收：按§25.5原路线与理论定义作真实流程/正反验收；当前检查不代替内容或运行通过。

## R07

设计目的：规范变更与中断重接

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：已有文档关联维护继续；研究任务原文装载/分段与C03持久恢复仍待实现，不由摘要恢复。

理论出处：[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T04、T05、T09、T10、T11、T13；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R07.F01 / T01 核最新规则与技术关联 | 最新最高说明和任务ID；条件：关联/派生无缺失且本节点未过期 | 当前原文与影响/待复核节点 | 成功：T11；失败：T01 | [§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)；机械关联不是语义重设计；待复核不能自清 |
| R07.F02 / T11 取回实际有效产物 | 前步原稿、证据、决定和限制；条件：版本及采用范围能重建 | 本次可接续输入及缺口 | 成功：T01；失败：T04/T05 | [§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)；聊天摘要不是已完成证明 |
| R07.F03 / T13 组织必要分段和实际提供 | 当前全局/局部原文和关键证据；条件：必要定义、注释和跨段依赖齐备 | 真实提供范围与中间产物 | 成功：T05；失败：T01 | [§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)；不能用字符统计证明已装载或理解 |
| R07.F04 / T09 核重接后的相关连接 | 跨段原句/证据及最终稿；条件：影响范围、语义与必要讲解已核 | 恢复后的有限有效版本 | 成功：T10/T11；失败：T05/T04 | [§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)；生产故障恢复仍需第四阶段验证 |

验收：按§25.5原路线与理论定义作真实流程/正反验收；当前检查不代替内容或运行通过。

## R08

设计目的：GitHub每周自动启动、完整运行与授权交付

责任：对应流程中注明的L层/技术模块责任；阶段：沿§19.2原四阶段；文档关联现可检查；实现：C06 Actions只设周开始+C03长任务续跑+C02期号/回执+C05文件；生产/已授权交付待实现。

理论出处：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T03、T04、T05、T09、T10、T11、T13；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| R08.F01 / T01 核阶段与运行授权 | 已验范围、GitHub周启动/资料期次、具体参数和运行/交付分开开关；条件：前三阶段门与本次运行权限具备 | 可启动范围或停止原因 | 成功：T13；失败：T01 | [§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)；当前只实现文档关联，不启生产任务 |
| R08.F02 / T13 周开始认领期号并持续/续跑完整内容链 | 计划期号、schedule/dispatch/续跑事件、实际Run、已有有效产物和当前规范；条件：认领/输入/能力/权限/资源有效；健康前期不抢占，新期持久排队，已完成期不重复执行 | 真实开始/进展/跨job续跑/合格内容文件与归档；积压/漏跑/受阻及恢复事实 | 成功：T10；失败：T13 | [§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)；只设周开始，无固定完成/停止/发送时刻；跨job/跨周同一期恢复；图退出/维护绿灯不证明成品或送达 |
| R08.F03 / T10 锁定经过核对的交付文件 | Edition、有效审核和真实文件；条件：实际内容/文件检查合格且已有交付授权，完成事件后立即接交付 | 目标刊次/文件版本/幂等标识 | 成功：T13；失败：T09/T10 | [§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)；不另等待发送钟点；未获交付授权仍可归档，版本变更不自动授予再次外发 |
| R08.F04 / T13 查真实回执并归档 | 实际交付尝试和服务商结果；条件：状态有可核依据 | ACCEPTED/CONFIRMED/FAILED/UNKNOWN | 成功：T11；失败：T13 | [§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)；UNKNOWN不盲目重发；送达与服务商接受不同 |

验收：按§25.13/W47/W48/W55核自然schedule、无Run漏跑、重复/跨周/夏令时/中断/平台故障与完整成果；手动/维护成功不代验周运行。

## T01

设计目的：规范与交接控制

责任：执行者组织；未来执行层维护决定；阶段：人工定位先行；第二阶段控制器；实现：C02提交/Review/AdoptionDecision追加版本与W15分离决定接口已离线实现；身份认证、完整研究图、LangGraph持久恢复和端到端采用仍未实现。

理论出处：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：无；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T01.L01 / T01 准备当前任务 | 问题/M步骤、规范与实际材料；条件：本次职责和采用用途明确 | 实际提供范围与缺口 | 成功：T01；失败：T05 | [§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)、[§8.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-1)；不以准备清单或模型自称已读代替实际输入 |
| T01.L02 / T01 核对采用资格 | 前步产物、版本、真实核对与当前限制；条件：实际依赖匹配且未过期 | 允许性质/用途及相应步骤决定 | 成功：T01；失败：T04/T05 | [§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)；候选可以按候选性质交接；不得升格为已证事实 |
| T01.L03 / T01 记录决定并交接 | 检查依据、缺口与本步产物；条件：相应责任核查已完成 | 绑定版本的采用记录或退回对象 | 成功：T03/T05/T09/T10；失败：T01 | [§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)；本模块的文档关联检查不替代研究放行程序 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T02

设计目的：全球发现与候选归并

责任：L1发现职责；阶段：第一阶段人工取样；第四阶段生产增量；实现：W20已离线实现feedparser/Trafilatura/JSON API受控字节入口、CandidateIndex、取得元信息、字段/时间缺口和失败记录，并持久到C02；W21已实现强键事件归并提案、来源血缘/独立根、编辑歧义和探索队列；W22已实现预固定独立参照、范围限定的覆盖比较与七类缺口；W23已消费候选/事件簇/覆盖审计，保存S0—S8取舍。真实来源运行与T03真实内容复核仍待后续。

理论出处：[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T13；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T02.L01 / T02 取得合法轻量线索 | 获准来源、时期与待查问题；条件：实际访问和本用途允许 | 候选、原始日期及取得状态 | 成功：T02；失败：T13 | [§4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-4-1)、[§4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-4-2)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)；候选来源登记不等于生产许可；不恢复全库探测 |
| T02.L02 / T02 归并并保留探索 | 线索及原发/转引血缘；条件：同事件、同源或不确定分别可核 | 归并建议、探索候选与缺口 | 成功：T03；失败：T02 | [§4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-4-2)、[§4.3](CANONICAL_SYSTEM_SPEC_V5.md#th-4-3)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)；不同网址/语言不是独立证据；模糊归并须人工核 |
| T02.L03 / T02 作池外参照检查 | 独立于入选清单的原始入口；条件：抽查范围和截点明确 | 发现/筛选/合理舍弃的区分及处理 | 成功：T03；失败：T02 | [§4.4](CANONICAL_SYSTEM_SPEC_V5.md#th-4-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)；小样本不能宣称全球召回率或零遗漏 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T03

设计目的：选题、复选与整刊计划

责任：L2编辑决定；阶段：第一阶段人工；第二阶段记录和接口；实现：C04编辑任务+C02决定+C03 S依赖；W22提供独立参照与覆盖缺口接口，W23已离线实现S0—S8前后决定、S8前置包的实对象绑定、研究准入与刊登准入分离及显式期次建议；分值不自动产生准入或拼刊，真实编辑取舍和W24—W26闭环待验。

理论出处：[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T02、T04、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T03.L01 / T03 初选并给取证计划 | 候选、价值依据和旧背景；条件：真实日期及基本价值成立 | S0—S7问题、类型及材料需求 | 成功：T04；失败：T02 | [§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.4](CANONICAL_SYSTEM_SPEC_V5.md#th-5-4)、[§8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5)；重要性、当前可知程度和本期呈现分别决定 |
| T03.L02 / T03 查证后S8复选 | T04实际证据/权利/A方案；条件：足以开展注明范围的工作 | COVER/REVISE/WATCH/DROP及理由 | 成功：T05/T04；失败：T04 | [§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)；不要求先完成原因研究才准许开始研究；COVER不等于PASS |
| T03.L03 / T03 复核成熟稿的本期价值 | 实际成稿贡献、当周重要事项；条件：CURRENT_WEEK或合格长期专题依据成立 | 当期组合取舍或跨周接续 | 成功：T09/T10；失败：T05 | [§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)；长期题失去深度且无当周新增，不自动降为精选刊登 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T04

设计目的：原作、证据与中文材料

责任：L3取证/中文核对；阶段：第一阶段实际回源；第二阶段适配；实现：C01已离线复用Trafilatura解析获准HTML字节，并支持纯文本定位；W24持久SOURCE_MATERIAL、SOURCE_STRUCTURE、SOURCE_INTAKE及RIGHTS_RECORD，正文保存、机器处理和后续翻译分别核权。PDF/Docling/OCR尚未接入，复杂原件只保留与显式缺口；提取不代内容核真。

理论出处：[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T13、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T04.L01 / T04 核用途并取具体版本 | S7/补证请求与具体作品；条件：访问、处理、保存和拟用范围有依据 | 取得回执、版本、范围和许可记录 | 成功：T04；失败：T03 | [§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)；只有链接或HTTP成功时不得填已核正文/全文 |
| T04.L02 / T04 核主张和支持范围 | 原段/原表、主张与计算输入；条件：相关上下文和专业条件实际可核 | Evidence/Claim支持、反证及缺口 | 成功：T03/T05/T09；失败：T04 | [§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)；计算须核实际输入与执行；同源材料不算多证 |
| T04.L03 / T04 制作入选中文并核更新 | S8选用范围与当前原作版本；条件：入选且相应用途允许 | 节选译文/独立导引及定稿更新结果 | 成功：T05/T09；失败：T04/T03 | [§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；S8后制作；影响结论的截点后材料须更新截点重审或调整安排 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T05

设计目的：问题界定与联合研究组织

责任：L4联合研究组织；B1/B2从早期参与；阶段：第一阶段分步研究；第二阶段可重跑组织；实现：W16同一Theme修订/输出链接/组合提交与CAS冲突边界已离线实现；C03完整M图、C04研究函数及真实模型内容仍待实现。

理论出处：[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T03、T04、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T05.L01 / T05 固定事实、问题和边界 | 已核材料、主/子问题及基线；条件：核心事实可支持开展本题 | M01—M03与问题完成标准 | 成功：T06/T07；失败：T04/T03 | [§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5)；研究准入不等于本题原因已经证明 |
| T05.L02 / T05 共同查条件与竞争解释 | B1事件问题、B2知识问题和专业资料；条件：方法前提与本题条件相称 | M04—M09过程/数量/反证及支持范围 | 成功：T06/T07/T08；失败：T04/T05 | [§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)；新材料可迫使改题；形成和检验材料分开 |
| T05.L03 / T05 决定有限交付或补研 | 实际支持、未知及必要未做工作；条件：对应问题的完成标准与停止理由可核 | 有范围的研究成果和下一取证/停止决定 | 成功：T06/T07/T09；失败：T04/T03 | [§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)；合格未知允许；不会、缺证、超预算不叫不适用 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T06

设计目的：顾问B1本案研判

责任：L4顾问职责；阶段：第一阶段真实研判；后续按任务验证；实现：C04 B1任务共用C02/C03和模型接口；实际顾问贡献待内容验收。

理论出处：[§1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T05；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T06.L01 / T06 核主体与现实处境 | 同一问题/截点的事实和解释；条件：权限、资源、行动和范围可核 | 有据的处境/约束地图 | 成功：T06；失败：T04/T05 | [§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§8.7](CANONICAL_SYSTEM_SPEC_V5.md#th-8-7)；公开表态、执行、结果和未知动机分开 |
| T06.L02 / T06 形成有限判断 | 机制比较、中间过程与最强反证；条件：判断强度与实际支持相称 | M10本案结论及相关含义 | 成功：T07/T08；失败：T05 | [§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)；无实际机会或决策问题不强配投资/创业建议 |
| T06.L03 / T06 交可审阅研判 | 实际段落、主张及未知；条件：相应前提和限制随文保留 | B1贡献与可改变判断的材料 | 成功：T09；失败：T05 | [§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)；不以新观点数量或通用建议代替本案理解 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T07

设计目的：帝师B2知识研究与教学

责任：L4帝师职责；从M02参与；阶段：第一阶段真实教学；后续按任务验证；实现：C04 B2任务共用C02/C03和模型接口；主动知识研究/自足教学仍待独立验收。

理论出处：[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T05、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T07.L01 / T07 提出材料中的知识问题 | 真实材料和共享解释/疑问；条件：知识对理解本题有明确作用 | 必要概念、专业/历史资料需求 | 成功：T05/T04；失败：T07 | [§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1)；不只接顾问定好的结论；不诊断读者掌握状态 |
| T07.L02 / T07 由具体到过程再到认识 | 已核知识、事实、案例和边界；条件：命题性质与依据对应 | M11连续讲解、必要基础与反例 | 成功：T07；失败：T05/T04 | [§10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1)、[§10.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-2-1)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)；认识未形成回研究，解释已有依据但不清楚回教学 |
| T07.L03 / T07 核迁移并形成读者稿 | 实际讲解和旧卡具体版本；条件：当前用途、条件和不同场景可核 | 知识贡献、迁移查证步骤及必要回顾 | 成功：T09/T08；失败：T07/T05 | [§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)；教学复用不算独立验证；去掉术语仍须有清楚过程 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T08

设计目的：条件推演与事前检验准备

责任：L4的C与M12准备；阶段：当期保存条件；真实结果后来再核；实现：C04条件任务+C02 ThesisVersion/Theme；无独立预测平台，真实成果待验。

理论出处：[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T05、T06、T07、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T08.L01 / T08 判断可推演到哪里 | B1/B2的有效成果和未知；条件：路径连接和条件有相称依据 | 情景适用范围或缺失区分材料 | 成功：T08；失败：T05 | [§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)；不凑路径、概率或固定题数 |
| T08.L02 / T08 写条件和中间传导 | 真实起点、主体、条件及时滞；条件：各路径有实质可辨的过程 | C条件路径与开放问题 | 成功：T09；失败：T05 | [§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)；未来路径不补成当前事实；不向读者索取答案 |
| T08.L03 / T08 保存事前复查条件 | 原判断、原证据与观察窗口；条件：时间/版本及可反驳条件明确 | M12当期记录及后续重开触发 | 成功：T11；失败：T08 | [§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)；不等未来发生才出刊；后来结果须另核机制 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T09

设计目的：独立审稿与具体内容放行

责任：L5独立核查；不自签；阶段：第一阶段实际核查；第二阶段能力配置验证；实现：C04独立核查+C01回源+C02版本+C03返工；W19已离线实现模型/任务配置身份、给定材料/检索/约束增益验证记录和有限使用准入，作者与审稿决定分离。真实审稿能力、模型调用与业务闭环未实现。

理论出处：[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T04、T05、T06、T07、T08；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T09.L01 / T09 固定被审对象并独立查验 | 实际读者稿、原件、方法和版本；条件：核查所需资料实际取得 | 独立疑点、支持核对和未核范围 | 成功：T09；失败：T04 | [§15.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-1)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；不能只审案卷；作者自评/预定PASS不是答案 |
| T09.L02 / T09 核判断、教学及修订 | 具体意见、反证、作者回应和改稿；条件：对应职责/适用性及支持关系可核 | 实际修订处理、合理争议及剩余限制 | 成功：T09；失败：T05/T07/T04 | [§15.2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-2)、[§15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)；既验漏检也验误拒；不以多数投票判真伪 |
| T09.L03 / T09 对实际版本作决定 | 核查依据和意见闭环；条件：硬门和相应稿型责任达到 | Review的决定、版本与允许范围 | 成功：T10；失败：T05/T04 | [§15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)；缺资源如实待审；CURRENT_BINDING不等于内容PASS |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T10

设计目的：成稿、整刊与实际阅读文件

责任：L6主编/呈现；新命题回L4/L5；阶段：第一阶段实际格式；第四阶段正式渲染/交付；实现：C05 Jinja+第四阶段WeasyPrint，复用年度呈现；内容/实际文件对应未实现验收。

理论出处：[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T03、T04、T09、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T10.L01 / T10 核当期取舍和重要更新 | 实际稿件、当期选择和截点；条件：足以影响结论的更新已处理 | 整刊顺序与选题/更新决定 | 成功：T10；失败：T03/T04 | [§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)；不能把初选或单篇通过当整刊已合格 |
| T10.L02 / T10 组织连续稿及卷首 | 已核主题、标题、图表和教学；条件：重要新概括有研究/审核支持 | 整刊源和审后变更承接 | 成功：T09/T10；失败：T05/T07 | [§13.5](CANONICAL_SYSTEM_SPEC_V5.md#th-13-5)、[§13.6](CANONICAL_SYSTEM_SPEC_V5.md#th-13-6)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；即使一字改意也按影响返审；纯呈现改版不重做无关研究 |
| T10.L03 / T10 核实际文件与冻结归档 | 有效Review、整刊源和真实文件；条件：呈现完整且版本对应 | Edition、文件检查与出版决定 | 成功：T11；失败：T10/T09 | [§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)；文件生成不等于内容已审、获准交付或确认到达 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T11

设计目的：共享档案、历史查询与纠错

责任：六层共享档案职责；阶段：第一篇保存；第二阶段跨周；第四阶段持久恢复；实现：C02 Pydantic/SQLAlchemy+私有版本文件；共享依赖/双as-of/纠错待实现，图检查点不是事实库。

理论出处：[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01、T13；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T11.L01 / T11 保存版本与引用用途 | 真实原稿、材料范围、审核和权限；条件：可留内容、时间与版本明确 | 不可无痕覆盖的原文及关联 | 成功：T11；失败：T04 | [§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)；保存权不足保留允许定位；不得借不可变性保留无权全文 |
| T11.L02 / T11 区分当前采用与历史回放 | 具体对象/版本和检索用途；条件：当前限制已核或as-of模式明确 | 可用范围或当时原话及后来说明 | 成功：T05/T12；失败：T11 | [§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)；索引命中不等于可正式采用；后来补录不能污染旧截点 |
| T11.L03 / T11 追更正并按范围恢复 | 变化、实际依赖和剩余支持；条件：先限制已知关键用途，再完成相关复核 | 影响/漏依赖/误限、重审及当前指向 | 成功：T09/T10；失败：T04/T05 | [§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§16.6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-2)、[§16.6.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-3)；不一改全撤或全过；测试副本不冒称自然更正 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T12

设计目的：年报双输入组织

责任：年度A01—A12组织；复用六层；阶段：第四阶段缩区间演练；全年另验；实现：年度双输入/A工序只组织C01—C05现有能力；无第二套引擎，年度成果待实现验收。

理论出处：[§2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-2-3)、[§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T02、T03、T04、T05、T06、T07、T08、T09、T10、T11；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T12.L01 / T12 固定双输入与年度范围 | 真实周刊、缺期和独立年度材料；条件：两路来源和知识截点可核 | A01—A07时间线、旧判断/修订及漏题审计 | 成功：T12；失败：T04/T11 | [§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)；不能伪造52期或以合订代独立回查 |
| T12.L02 / T12 作年度新研究和知识综合 | 年度过程、旧解释与新检验证据；条件：新旧依据和现时用途分别核过 | A08—A11年度顾问/帝师/未来条件稿 | 成功：T09；失败：T05/T04 | [§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)；年末新资料不回写成年初已知；旧周刊PASS不批准新综合 |
| T12.L03 / T12 核年报成品及许可 | 新Review、年度源及重收材料用途；条件：当次权限和实际文件对应 | A12年报版本、索引与归档 | 成功：T10/T11；失败：T09/T04 | [§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)；短期演练不证明全年质量、覆盖或费用 |

验收：按本模块§25.4原文及所指理论作真实正反验收；本次仅核关联/标注，不授予内容、模型或生产资格。

## T13

设计目的：模型、工具、投入及GitHub每周自动运行支撑

责任：实际工具执行与配置记录；不替内容裁决；阶段：受控使用先行；二/三/四阶段逐步验证；实现：W17 OperationRequest/Receipt、Adapter返回校验、UNKNOWN对账与逻辑操作累计已离线实现；W18调用前能力/材料/外发/重试门禁、共享预算预留结算与未知保留已离线实现。真实第三方认证/适配、生产预算恢复和Actions周运行未实现。

理论出处：[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)。另继承全局约束，完整哈希及依赖见technical_trace.json。

设计影响依赖：T01；这些不是任务启动前必须全部PASS的状态条件。

关联状态：CURRENT_BINDING；理论变化：无；设计变化：False；共用设计变化：无；上游变化：无。

| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |
|---|---|---|---|---|
| T13.L01 / T13 核调用边界 | 实际任务、配置、材料用途和资源；条件：获准且范围相称，或明确受控试用 | 本次可调用范围及限制 | 成功：T13；失败：T01 | [§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)；未知预算不当无限授权；能力可用不等于可付费/外发 |
| T13.L02 / T13 执行并记录真实结果 | 允许的操作、输入与工具；条件：实际请求与操作可确认 | 真实输出/错误、用量/估计及失败记录 | 成功：T04/T05/T09；失败：T13 | [§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§17.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-1)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)；不由模型补造版本、费用、页码、成功回执 |
| T13.L03 / T13 核健康进展、同一期续跑或有界故障恢复 | 预登记期次/积压、Run/真实进展或未知、持久检查点/有效产物和剩余允许资源；条件：区分健康长任务/排队与真实故障/受阻；同一期thread及认领/版本有效，故障恢复次数和预算有据 | 健康持续/跨job续跑、真实积压/漏跑/受阻及有限恢复/告警记录 | 成功：T01/T11；失败：T13 | [§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)；只设开始，不以总耗时或钟点无成品强停/重启；原生检查点/副作用须验；重试一处主控，不重复费用/交付 |

验收：按§25.13及原§19核每周真实触发、完整内容执行、独立漏跑/进展检查、有界补跑/恢复与权限/费用；当前均未实现，不以维护CI代验。

## 共用设计来源

以下共用架构、接口、阶段及维护边界由所有节点继承；变更会列出具体共用来源并要求复核。

| 稳定设计ID / 当前节号 | 当前标题 |
|---|---|
| [tech-shared-25-1 / §25.1](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-1) | 本章的设计范围、依据与效力 |
| [tech-shared-25-10 / §25.10](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-10) | 理论修订怎样自动传到模块、路线与逻辑 |
| [tech-shared-25-13 / §25.13](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-13) | GitHub Actions每周自动启动、完整运行与漏跑恢复 |
| [tech-shared-25-14 / §25.14](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-14) | 成熟项目优先的复用、整合与精简方案 |
| [tech-shared-25-2 / §25.2](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-2) | 理论要求怎样导出总体技术路线 |
| [tech-shared-25-3 / §25.3](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-3) | 总体架构与应用形态 |
| [tech-shared-25-6 / §25.6](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-6) | 共享数据、模块接口与控制边界 |
| [tech-shared-25-7 / §25.7](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-7) | 原有四阶段怎样落实到这套框架 |
| [tech-shared-25-8 / §25.8](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-8) | 通用技术复用路线与尚待确定的实施参数 |
| [tech-shared-25-9 / §25.9](CANONICAL_SYSTEM_SPEC_V5.md#tech-shared-25-9) | 本章的设计核对与后续实现验收边界 |

## 理论到技术的反向索引

包含全局约束的保守影响范围，不宣称自然语言依赖已经穷尽。问题台账中的未采纳方案及历史记录不升级为规范。

| 稳定理论ID/当前节号 | 直接绑定 | 设计依赖传播范围 |
|---|---|---|
| [th-0 / §0](CANONICAL_SYSTEM_SPEC_V5.md#th-0) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-1 / §1](CANONICAL_SYSTEM_SPEC_V5.md#th-1) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-1-3 / §1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3) | T06 | R01,R02,R03,R04,R05,R06,R07,R08,T06,T08,T09,T10,T12 |
| [th-10 / §10](CANONICAL_SYSTEM_SPEC_V5.md#th-10) | R01,T07 | R01,R02,R03,R04,R05,R06,R07,R08,T07,T08,T09,T10,T12 |
| [th-10-1 / §10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1) | T07 | R01,R02,R03,R04,R05,R06,R07,R08,T07,T08,T09,T10,T12 |
| [th-10-2-1 / §10.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-2-1) | T07 | R01,R02,R03,R04,R05,R06,R07,R08,T07,T08,T09,T10,T12 |
| [th-10-5 / §10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5) | T07,T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-10-6 / §10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6) | R05,T07,T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-10-7 / §10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7) | T07,T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-11 / §11](CANONICAL_SYSTEM_SPEC_V5.md#th-11) | R01,T08 | R01,R02,R03,R04,R05,R06,R07,R08,T08,T09,T10,T12 |
| [th-12 / §12](CANONICAL_SYSTEM_SPEC_V5.md#th-12) | T05 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-13 / §13](CANONICAL_SYSTEM_SPEC_V5.md#th-13) | R01,T10 | R01,R02,R03,R05,R06,R07,R08,T10,T12 |
| [th-13-1 / §13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1) | R02,R03,R04,T03 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-13-5 / §13.5](CANONICAL_SYSTEM_SPEC_V5.md#th-13-5) | T10 | R01,R02,R03,R05,R06,R07,R08,T10,T12 |
| [th-13-6 / §13.6](CANONICAL_SYSTEM_SPEC_V5.md#th-13-6) | T10 | R01,R02,R03,R05,R06,R07,R08,T10,T12 |
| [th-13-7 / §13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7) | R01,R05,R06,R07,R08,T04,T09,T10,T12 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T12 |
| [th-14 / §14](CANONICAL_SYSTEM_SPEC_V5.md#th-14) | R06,T12 | R05,R06,T12 |
| [th-14-1 / §14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1) | R06,T12 | R05,R06,T12 |
| [th-15 / §15](CANONICAL_SYSTEM_SPEC_V5.md#th-15) | T09 | R01,R02,R03,R04,R05,R06,R07,R08,T09,T10,T12 |
| [th-15-2 / §15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2) | R01,R03,R05 | R01,R03,R05 |
| [th-15-2-1 / §15.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-1) | T09 | R01,R02,R03,R04,R05,R06,R07,R08,T09,T10,T12 |
| [th-15-2-2 / §15.2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-2) | T09 | R01,R02,R03,R04,R05,R06,R07,R08,T09,T10,T12 |
| [th-15-2-3 / §15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3) | T09 | R01,R02,R03,R04,R05,R06,R07,R08,T09,T10,T12 |
| [th-16 / §16](CANONICAL_SYSTEM_SPEC_V5.md#th-16) | T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-16-1 / §16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1) | T05,T06 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-16-2 / §16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2) | T05,T06 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-16-3 / §16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3) | R05,R06,T08,T11,T12 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-16-4 / §16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4) | R02,R06,T08 | R01,R02,R03,R04,R05,R06,R07,R08,T08,T09,T10,T12 |
| [th-16-5 / §16.5](CANONICAL_SYSTEM_SPEC_V5.md#th-16-5) | R02 | R02 |
| [th-16-6 / §16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6) | R03,R05,R06,T11,T12 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-16-6-1 / §16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1) | R05,R06,R07,T01,T11,T12 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-16-6-2 / §16.6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-2) | R05,T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-16-6-3 / §16.6.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-3) | R05,T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-17 / §17](CANONICAL_SYSTEM_SPEC_V5.md#th-17) | T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-17-2 / §17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2) | R07,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-17-2-1 / §17.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-1) | T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-17-2-4 / §17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4) | R07,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-18 / §18](CANONICAL_SYSTEM_SPEC_V5.md#th-18) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-18-1 / §18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1) | R03,T09 | R01,R02,R03,R04,R05,R06,R07,R08,T09,T10,T12 |
| [th-19 / §19](CANONICAL_SYSTEM_SPEC_V5.md#th-19) | T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-19-1 / §19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1) | R08,T10 | R01,R02,R03,R05,R06,R07,R08,T10,T12 |
| [th-19-2 / §19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-19-5-1 / §19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1) | T06,T07,T09 | R01,R02,R03,R04,R05,R06,R07,R08,T06,T07,T08,T09,T10,T12 |
| [th-19-7 / §19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7) | R04,R08,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-2 / §2](CANONICAL_SYSTEM_SPEC_V5.md#th-2) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-2-1 / §2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1) | R01,R02,R03,T03,T04,T10 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T12 |
| [th-2-2 / §2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2) | R02,T03 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-2-3 / §2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-2-3) | T12 | R05,R06,T12 |
| [th-20 / §20](CANONICAL_SYSTEM_SPEC_V5.md#th-20) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-20-3 / §20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3) | R07 | R07 |
| [th-21 / §21](CANONICAL_SYSTEM_SPEC_V5.md#th-21) | T01 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-22 / §22](CANONICAL_SYSTEM_SPEC_V5.md#th-22) | T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-22-4 / §22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4) | R08,T01,T10 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-23 / §23](CANONICAL_SYSTEM_SPEC_V5.md#th-23) | T01 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-23-1 / §23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1) | T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-23-3 / §23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3) | T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-24 / §24](CANONICAL_SYSTEM_SPEC_V5.md#th-24) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-24-5 / §24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5) | T11 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 |
| [th-24-6-1 / §24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1) | R07,T01,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-3 / §3](CANONICAL_SYSTEM_SPEC_V5.md#th-3) | T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-4 / §4](CANONICAL_SYSTEM_SPEC_V5.md#th-4) | R01,T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-4-1 / §4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-4-1) | T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-4-2 / §4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-4-2) | T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-4-3 / §4.3](CANONICAL_SYSTEM_SPEC_V5.md#th-4-3) | T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-4-4 / §4.4](CANONICAL_SYSTEM_SPEC_V5.md#th-4-4) | T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-5 / §5](CANONICAL_SYSTEM_SPEC_V5.md#th-5) | T03 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-5-2 / §5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2) | R01,R02,T03 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-5-4 / §5.4](CANONICAL_SYSTEM_SPEC_V5.md#th-5-4) | T03 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-5-5 / §5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5) | R01,R03,T03,T10 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-6 / §6](CANONICAL_SYSTEM_SPEC_V5.md#th-6) | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-6-1 / §6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1) | T02 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-6-2 / §6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2) | R03,R04,T04,T09,T13 | R01,R02,R03,R04,R05,R06,R07,R08,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-7 / §7](CANONICAL_SYSTEM_SPEC_V5.md#th-7) | T04 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T12 |
| [th-7-3 / §7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3) | R03,T04 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T12 |
| [th-7-4 / §7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4) | R01,R04,T03,T04 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T12 |
| [th-8 / §8](CANONICAL_SYSTEM_SPEC_V5.md#th-8) | T05 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-8-2 / §8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2) | R01,T05 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-8-2-1 / §8.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-1) | T01 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-8-2-3 / §8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3) | T01 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-8-2-4 / §8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4) | R07,T01,T09 | R01,R02,R03,R04,R05,R06,R07,R08,T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13 |
| [th-8-3-4 / §8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4) | R04,T04,T05 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T04,T05,T06,T07,T08,T09,T10,T12 |
| [th-8-4-1 / §8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1) | T05,T06,T07 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-8-4-2 / §8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2) | R02,R04,T05,T08 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-8-5 / §8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5) | T03,T05 | R01,R02,R03,R04,R05,R06,R07,R08,T03,T05,T06,T07,T08,T09,T10,T12 |
| [th-8-7 / §8.7](CANONICAL_SYSTEM_SPEC_V5.md#th-8-7) | T06 | R01,R02,R03,R04,R05,R06,R07,R08,T06,T08,T09,T10,T12 |
| [th-8-8 / §8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8) | T05,T06,T08 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
| [th-8-8-3 / §8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3) | T08,T12 | R01,R02,R03,R04,R05,R06,R07,R08,T08,T09,T10,T12 |
| [th-9 / §9](CANONICAL_SYSTEM_SPEC_V5.md#th-9) | T06 | R01,R02,R03,R04,R05,R06,R07,R08,T06,T08,T09,T10,T12 |
| [th-9-1 / §9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1) | R01,T05,T06,T07 | R01,R02,R03,R04,R05,R06,R07,R08,T05,T06,T07,T08,T09,T10,T12 |
