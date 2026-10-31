# 内参系统开发工作清单

本文件从[最高说明§26](CANONICAL_SYSTEM_SPEC_V5.md#tech-work-26)机械生成；任务、验收条件及进度只改唯一原文。

**13个功能模块，8条跨模块路线，72项既有逻辑；拆为55个小工作包，加4个阶段验收门，共59步。**

工作包不是新增服务、模型或Agent。顺序号用于对照；按明确前置依赖推进，同阶段独立项可并行，仍须原阶段质量门。

CURRENT_BINDING只表示清单与当前理论/技术设计关联一致，**不表示已写代码、能力通过、阶段通过或获准运行**。

当前规范SHA-256：`98814ddf580992c27cd255c4f5a008353124c582653568a936087c67acf659f6`。

清单需复核：无；仅限清单关联新鲜度。

验收通过：11；有据不适用：1；其余按下表实际状态。

**交付类型分开统计**：第一阶段人工准备/内容验证已验收11包；代码与接口工作包已验收0包、进行中/待验收22包。人工验收数量不表示业务模块已编码；模块完成须另核相应代码、接口、测试和适用阶段门。

## 四阶段与数量

| 阶段 | 小工作包 | 阶段门 | 对照步骤数 | 主要交付 |
|---|---:|---|---:|---|
| 1 编辑体系 | 12 | [G01](#g01) | 13 | 人工真实专题→完整同周样刊；内容验证先行 |
| 2 研究体系 | 29 | [G02](#g02) | 30 | 最小研究代码→真实跨周/纠错→六例 |
| 3 专业能力 | 4 | [G03](#g03) | 5 | 按题专业能力与有据增益，必要时比较分工 |
| 4 生产体系 | 10 | [G04](#g04) | 11 | 生产离线预演、恢复/交付及年度双输入回放 |

## 每包共同验收Q01—Q07

各包同时满足[§26.2](CANONICAL_SYSTEM_SPEC_V5.md#tech-work-26-2)的Q01—Q07：依据新鲜、输入/前置有效、实际交付物、正反及衔接结果、失败/限制、相称复核、主要投入与权限。

结果记录复用RunLog/Review/Git与私有成果指针。模板：[§26.3](CANONICAL_SYSTEM_SPEC_V5.md#tech-work-26-3)。验收清单存在或复选框被勾选，不构成实际证据。

## 按步骤对照

| 顺序 | 工作包/阶段门 | 类型 | T/R | 前置工作包 | 实际进度 / 关联 |
|---:|---|---|---|---|---|
| 1 | [W01 固定样刊任务与第一篇档案](#w01) | 人工内容验证 | T01/T11/T13/R07 | 无 | 验收通过 / CURRENT_BINDING |
| 2 | [W02 人工发现、归并与池外参照](#w02) | 人工内容验证 | T02/T03/R01 | [W01](#w01) | 验收通过 / CURRENT_BINDING |
| 3 | [W03 初选与有边界的取证计划](#w03) | 人工内容验证 | T03/R01 | [W02](#w02) | 验收通过 / CURRENT_BINDING |
| 4 | [W04 真实原件、许可与主张支持核对](#w04) | 人工内容验证 | T04/R04 | [W03](#w03) | 验收通过 / CURRENT_BINDING |
| 5 | [W05 S8复选与入选中文材料](#w05) | 人工内容验证 | T03/T04/R03 | [W04](#w04) | 验收通过 / CURRENT_BINDING |
| 6 | [W06 联合界定事实、问题与完成边界](#w06) | 人工内容验证 | T05/T07/R01 | [W05](#w05) | 验收通过 / CURRENT_BINDING |
| 7 | [W07 竞争解释、专业前提与真实方法应用](#w07) | 人工内容验证 | T05/T04/R04 | [W06](#w06) | 验收通过 / CURRENT_BINDING |
| 8 | [W08 顾问B1真实成稿与增益对照](#w08) | 人工内容验证 | T06 | [W07](#w07) | 验收通过 / CURRENT_BINDING |
| 9 | [W09 帝师B2主动研究与自足讲解](#w09) | 人工内容验证 | T07 | [W07](#w07) | 验收通过 / CURRENT_BINDING |
| 10 | [W10 条件推演与事前复查准备](#w10) | 人工内容验证 | T08 | [W08](#w08)、[W09](#w09) | 验收通过 / CURRENT_BINDING |
| 11 | [W11 独立审稿、改稿与真实版本放行](#w11) | 人工内容验证 | T09/R01/R03 | [W08](#w08)、[W09](#w09)、[W10](#w10) | 验收通过 / CURRENT_BINDING |
| 12 | [W12 完整同周样刊与实际阅读验收](#w12) | 人工内容验证 | T03/T10/T11/R01/R03 | [W11](#w11) | 待验收 / CURRENT_BINDING |
| 13 | [G01 第一阶段门：真实专题及完整同周样刊](#g01) | 阶段门 | R01/R03/R04/R07/T01/T02/T03/T04/T05/T06/T07/T08/T09/T10/T11/T13 | [W01](#w01)、[W02](#w02)、[W03](#w03)、[W04](#w04)、[W05](#w05)、[W06](#w06)、[W07](#w07)、[W08](#w08)、[W09](#w09)、[W10](#w10)、[W11](#w11)、[W12](#w12) | 待开始 / CURRENT_BINDING |
| 14 | [W13 共享对象、版本与档案基础接口](#w13) | 代码与接口工作包 | T11/T01/T04 | [G01](#g01) | 进行中 / CURRENT_BINDING |
| 15 | [W14 当前规范与任务输入准备接口](#w14) | 代码与接口工作包 | T01/R07 | [W13](#w13) | 进行中 / CURRENT_BINDING |
| 16 | [W15 采用检查与权威决定接口](#w15) | 代码与接口工作包 | T01 | [W14](#w14) | 进行中 / CURRENT_BINDING |
| 17 | [W16 共享研究修订与并发提交边界](#w16) | 代码与接口工作包 | T05/T01/T11 | [W13](#w13)、[W15](#w15) | 进行中 / CURRENT_BINDING |
| 18 | [W17 工具适配器与真实操作身份](#w17) | 代码与接口工作包 | T13/T11 | [W13](#w13)、[W15](#w15) | 进行中 / CURRENT_BINDING |
| 19 | [W18 调用前权限、预算与能力核验](#w18) | 代码与接口工作包 | T13/T01 | [W17](#w17)、[W15](#w15) | 进行中 / CURRENT_BINDING |
| 20 | [W19 模型任务配置与有限准入证据](#w19) | 代码与接口工作包 | T13/T09 | [W18](#w18) | 进行中 / CURRENT_BINDING |
| 21 | [W20 少量来源适配与候选输入](#w20) | 代码与接口工作包 | T02 | [W17](#w17)、[W18](#w18) | 进行中 / CURRENT_BINDING |
| 22 | [W21 事件归并、血缘与探索队列](#w21) | 代码与接口工作包 | T02 | [W20](#w20)、[W13](#w13) | 进行中 / CURRENT_BINDING |
| 23 | [W22 独立参照与覆盖缺口接口](#w22) | 代码与接口工作包 | T02/T03 | [W20](#w20)、[W21](#w21) | 进行中 / CURRENT_BINDING |
| 24 | [W23 初选、S8与当期取舍记录](#w23) | 代码与接口工作包 | T03 | [W15](#w15)、[W21](#w21) | 进行中 / CURRENT_BINDING |
| 25 | [W24 原件取得、结构提取与用途控制](#w24) | 代码与接口工作包 | T04 | [W13](#w13)、[W17](#w17)、[W18](#w18)、[W23](#w23) | 进行中 / CURRENT_BINDING |
| 26 | [W25 主张支持、计算与定向补证接口](#w25) | 代码与接口工作包 | T04/T05/R04 | [W24](#w24)、[W16](#w16) | 进行中 / CURRENT_BINDING |
| 27 | [W26 入选中文、节选边界与重要更新](#w26) | 代码与接口工作包 | T04/T03 | [W24](#w24)、[W25](#w25)、[W23](#w23) | 进行中 / CURRENT_BINDING |
| 28 | [W27 M工序、共同研究与有限收口接口](#w27) | 代码与接口工作包 | T05/T07/R04 | [W16](#w16)、[W25](#w25)、[W19](#w19) | 进行中 / CURRENT_BINDING |
| 29 | [W28 顾问任务、判断与增益提交](#w28) | 代码与接口工作包 | T06 | [W27](#w27) | 进行中 / CURRENT_BINDING |
| 30 | [W29 帝师研究、连续教学与迁移提交](#w29) | 代码与接口工作包 | T07 | [W27](#w27) | 进行中 / CURRENT_BINDING |
| 31 | [W30 条件路径与原判断检验条件](#w30) | 代码与接口工作包 | T08 | [W28](#w28)、[W29](#w29) | 进行中 / CURRENT_BINDING |
| 32 | [W31 独立核查、意见闭环与审核决定](#w31) | 代码与接口工作包 | T09/T01 | [W28](#w28)、[W29](#w29)、[W30](#w30)、[W19](#w19)、[W15](#w15) | 进行中 / CURRENT_BINDING |
| 33 | [W32 连续文章、卷首与审后变更承接](#w32) | 代码与接口工作包 | T10/T03 | [W31](#w31)、[W23](#w23)、[W26](#w26) | 进行中 / CURRENT_BINDING |
| 34 | [W33 原文档案、双模式查询与知识复用](#w33) | 代码与接口工作包 | T11 | [W13](#w13)、[W16](#w16)、[W32](#w32) | 进行中 / CURRENT_BINDING |
| 35 | [W34 更正影响、限制采用与有限恢复](#w34) | 代码与接口工作包 | T11/T01 | [W33](#w33)、[W25](#w25)、[W31](#w31)、[W15](#w15) | 进行中 / CURRENT_BINDING |
| 36 | [W35 必要时的原文任务视图与分段装载](#w35) | 条件能力 | T01/T13/R07 | [W14](#w14)、[W17](#w17) | 有据不适用 / CURRENT_BINDING |
| 37 | [W36 最小深度主题闭环与中断重接](#w36) | 路线集成验收 | R01/R07/T01/T09/T11/T13 | [W22](#w22)、[W32](#w32)、[W33](#w33)、[W18](#w18) | 进行中 / CURRENT_BINDING |
| 38 | [W37 精选、首次事实、进展及更正分支](#w37) | 路线集成验收 | R03/T03/T04/T09/T10 | [W23](#w23)、[W26](#w26)、[W31](#w31)、[W32](#w32)、[W34](#w34) | 待开始 / CURRENT_BINDING |
| 39 | [W38 定向补证、解释变化与回S8](#w38) | 路线集成验收 | R04/T03/T04/T05 | [W25](#w25)、[W27](#w27)、[W23](#w23)、[W31](#w31) | 待开始 / CURRENT_BINDING |
| 40 | [W39 真实跨周接续与长期专题入刊](#w39) | 路线集成验收 | R02/T03/T05/T11 | [W33](#w33)、[W27](#w27)、[W23](#w23)、[W36](#w36) | 待开始 / CURRENT_BINDING |
| 41 | [W40 更正、当前采用与历史回放集成](#w40) | 路线集成验收 | R05/T11/T09/T10 | [W34](#w34)、[W39](#w39)、[W31](#w31)、[W32](#w32) | 待开始 / CURRENT_BINDING |
| 42 | [W41 六份真实跨领域案例与投入联合验收](#w41) | 真实案例与能力验收 | R01/R02/R03/R04/R05/R07/T09/T13 | [W36](#w36)、[W37](#w37)、[W38](#w38)、[W39](#w39)、[W40](#w40) | 待开始 / CURRENT_BINDING |
| 43 | [G02 第二阶段门：研究闭环、跨周与六例](#g02) | 阶段门 | R01/R02/R03/R04/R05/R07/T01/T02/T03/T04/T05/T06/T07/T08/T09/T10/T11/T13 | [W13](#w13)、[W14](#w14)、[W15](#w15)、[W16](#w16)、[W17](#w17)、[W18](#w18)、[W19](#w19)、[W20](#w20)、[W21](#w21)、[W22](#w22)、[W23](#w23)、[W24](#w24)、[W25](#w25)、[W26](#w26)、[W27](#w27)、[W28](#w28)、[W29](#w29)、[W30](#w30)、[W31](#w31)、[W32](#w32)、[W33](#w33)、[W34](#w34)、[W35](#w35)、[W36](#w36)、[W37](#w37)、[W38](#w38)、[W39](#w39)、[W40](#w40)、[W41](#w41) | 待开始 / CURRENT_BINDING |
| 44 | [W42 按题接入必要专业原始资料](#w42) | 代码与接口工作包 | T04/T05/T13 | [G02](#g02) | 待开始 / CURRENT_BINDING |
| 45 | [W43 专业深度专题与方法实际增益](#w43) | 真实案例与能力验收 | T05/T06/T07/T08/T09 | [W42](#w42) | 待开始 / CURRENT_BINDING |
| 46 | [W44 必要时的专业分工比较](#w44) | 条件能力 | T09/T13 | [W43](#w43) | 待开始 / CURRENT_BINDING |
| 47 | [W45 新例复核与有限能力范围更新](#w45) | 真实案例与能力验收 | T09/T13/T01 | [W43](#w43) | 待开始 / CURRENT_BINDING |
| 48 | [G03 第三阶段门：专业增益与有限能力](#g03) | 阶段门 | T01/T04/T05/T06/T07/T08/T09/T13 | [W42](#w42)、[W43](#w43)、[W44](#w44)、[W45](#w45) | 待开始 / CURRENT_BINDING |
| 49 | [W46 GitHub周运行参数与私有持久环境落实](#w46) | 代码与接口工作包 | T01/T11/T13/R08 | [G03](#g03) | 待开始 / CURRENT_BINDING |
| 50 | [W47 每周schedule入口、期号认领与完整运行](#w47) | 代码与接口工作包 | T13/T01/T02/R08 | [W46](#w46)、[W20](#w20)、[W21](#w21)、[W18](#w18) | 待开始 / CURRENT_BINDING |
| 51 | [W48 独立漏跑检查、有界补跑与运行恢复](#w48) | 代码与接口工作包 | T13/T01/T11/R07/R08 | [W47](#w47)、[W18](#w18)、[W17](#w17)、[W33](#w33) | 待开始 / CURRENT_BINDING |
| 52 | [W49 正式阅读格式、审后锁定与出版身份](#w49) | 代码与接口工作包 | T10/T09/T11/R08 | [W46](#w46)、[W32](#w32)、[W48](#w48) | 待开始 / CURRENT_BINDING |
| 53 | [W50 授权交付、回执与重复投递防护](#w50) | 代码与接口工作包 | T13/T10/T11/R08 | [W49](#w49)、[W48](#w48) | 待开始 / CURRENT_BINDING |
| 54 | [W51 私有归档、备份与真实恢复](#w51) | 代码与接口工作包 | T11/T13 | [W46](#w46)、[W48](#w48)、[W49](#w49) | 待开始 / CURRENT_BINDING |
| 55 | [W52 年度双输入与旧判断审计](#w52) | 代码与接口工作包 | T12/R06/T11/T04 | [W51](#w51)、[W39](#w39)、[W40](#w40) | 待开始 / CURRENT_BINDING |
| 56 | [W53 年度新综合、教学与重新独审](#w53) | 代码与接口工作包 | T12/R06/T05/T09/T10 | [W52](#w52)、[W43](#w43)、[W49](#w49) | 待开始 / CURRENT_BINDING |
| 57 | [W54 R06年度缩区间完整回放](#w54) | 路线集成验收 | R06/T12/T11/T09/T10 | [W52](#w52)、[W53](#w53) | 待开始 / CURRENT_BINDING |
| 58 | [W55 每周自然触发、连续周刊与漏跑故障验收](#w55) | 路线集成验收 | R08/R01/R03/R05/R07/T01/T10/T11/T13 | [W47](#w47)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W54](#w54) | 待开始 / CURRENT_BINDING |
| 59 | [G04 第四阶段门：生产离线验收与年度回放](#g04) | 阶段门 | R01/R03/R05/R06/R07/R08/T01/T02/T04/T05/T09/T10/T11/T12/T13 | [W46](#w46)、[W47](#w47)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W52](#w52)、[W53](#w53)、[W54](#w54)、[W55](#w55) | 待开始 / CURRENT_BINDING |

<a id="w01"></a>
## W01｜固定样刊任务与第一篇档案

顺序：1/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：无。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T01](TECHNICAL_TRACE.md#t01)、[T11](TECHNICAL_TRACE.md#t11)、[T13](TECHNICAL_TRACE.md#t13)、[R07](TECHNICAL_TRACE.md#r07)。

逐项逻辑：T01.L01、T11.L01、R07.F01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-1)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：当前最高说明、一个真实周的候选区间；尚未确定的持久宿主与资源明确列缺口。

**交付物**：

- 任务卡：区间/截点、当期范围、规范版本、获准工具和材料用途。
- 第一篇即保存的材料/原话/完整稿/审核目录及三时间记录；持久位置落实记录。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：逐项打开任务卡和实际档案，能找到规范版本、事件/公开/记录时间、材料版本与后续稿件位置。
- [ ] 反向：用后来补录、无持久位置及仅聊天摘要的对照，分别识别时点差异、临时草稿和缺失原文；不宣称长期保存通过。
- [ ] 衔接：把同一任务ID交给W02—W12；后续每次修稿追加版本而非覆盖旧判断。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：缺宿主时先保留临时草稿并标限制；缺必要权限停止相应用途，不创建生产调度。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W01-ACCEPTANCE-20261020-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W01-v01.zip#00-task/task-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W01-v01.zip#02-article/ART-SI-WEEKLY-2026-W42-001/archive-index-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W01-v01.zip#05-handoff/W02-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W01-v01.zip#04-validation/W01-content-check-v001.md", "private:/新闻/SI-WEEKLY-2026-W42-W01-v01.zip#04-validation/negative-cases-v001.json", "CANONICAL_SYSTEM_SPEC_V5.md#run-w01-20261020 (RV-W01-PERSISTENCE-20261020；独立私有回读/15文件哈希相符)"], "reviewer": "Codex：实际文件/原话定位/三时间/人工正反与私有保存回读核对；非L5内容审稿", "result": "ACCEPTED：W01首份样刊任务与初始人工私有档案已逐项核对", "scope": "仅任务SI-WEEKLY-2026-W42及首篇档案准备；输入规范f793d407/110e3c821eda，私有包SHA-256 d0feedf3f468ac7b139765f91d73d4005327236cb1e7fb72774268c0ab246f44；正文/Review/全球覆盖/生产和长期恢复均未验，不代G01或W02以后工作"}]

<a id="w02"></a>
## W02｜人工发现、归并与池外参照

顺序：2/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W01](#w01)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T02](TECHNICAL_TRACE.md#t02)、[T03](TECHNICAL_TRACE.md#t03)、[R01](TECHNICAL_TRACE.md#r01)。

逐项逻辑：T02.L01、T02.L02、T02.L03、R01.F01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-4-1)、[§4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-4-2)、[§4.3](CANONICAL_SYSTEM_SPEC_V5.md#th-4-3)、[§4.4](CANONICAL_SYSTEM_SPEC_V5.md#th-4-4)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：获准且本轮实际使用的来源、区间和旧题；独立参照的预定范围。

**交付物**：

- 轻量候选索引、原发/转引血缘、事件归并建议。
- 池外参照与候选/入选的差异、覆盖缺口及原因。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：实际来源能回查，可靠冷门和正面事项有被比较的机会；不同时间含义分别记。
- [ ] 反向：同源转载不作多重独立支持；不同事件不因相似标题强并；旧数据报告不改写成本周发生。
- [ ] 衔接：由T03独立取舍；移除日报输入仍能完成本次发现，参照不是从入选稿倒推。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：断源留SOURCE_UNAVAILABLE和覆盖缺口，转其他获准来源；不声称全球零漏题。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W02-ACCEPTANCE-20261020-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#W02-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#01-discovery/CandidateIndex-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#01-discovery/CandidateIndex-v002.json", "private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#02-lineage/SourceLineage-v002.json", "private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#02-lineage/EventClusterProposal-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#03-reference/ReferenceComparison-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#03-reference/CoverageGap-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#05-handoff/W03-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W02-v01.zip#04-validation/W02-content-check-v001.md (RV-W02-CONTENT-20261020/M01—M10)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w02-20261020 (W02-ACCEPTANCE-20261020-001；原三项实际人工正反核对)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w02-20261020 (RV-W02-PERSISTENCE-20261020；独立私有回读22文件/21清单/冻结主池一致)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w02-20261020 (RV-W02-PERSISTENCE-20261020-002；修正两处工作卡链接/保存版本1再次回读；研究JSON原字节不变)"], "reviewer": "Codex本轮实际执行者/档案核对；不是L5独立审稿或用户读后认可", "result": "ACCEPTED", "scope": "仅SI-WEEKLY-2026-W42的W02手工L1交付；输入df660635/951b7953a2aa，主池18条先冻结后查10参照，最终26候选（19比较/7待核）、35来源/12关系、7类缺口；私有包当前保存版本1 SHA-256 60fdf68840fd41b7965293c8d8a485651b53a279948ca9688355542a8524955c，回读相符；回溯同人路径独立检查，不是盲测/全球覆盖/原件事实PASS/自动采集；W03尚无入选/筛选差异，G01/生产均未验"}]

<a id="w03"></a>
## W03｜初选与有边界的取证计划

顺序：3/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W02](#w02)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T03](TECHNICAL_TRACE.md#t03)、[R01](TECHNICAL_TRACE.md#r01)。

逐项逻辑：T03.L01、R01.F02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.4](CANONICAL_SYSTEM_SPEC_V5.md#th-5-4)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：候选、真实日期/血缘、主题背景和已知资源。

**交付物**：

- S0—S7决定及理由、具体问题、拟用稿型。
- S7阅读/取证计划：关键主张、区分材料、可得性与限制。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：价值、可知程度、投入和整刊互补分别有依据，重要难题有下一动作而非因易写性淘汰。
- [ ] 反向：热度、领域配额、最高分和COVER均不能直接变成内容PASS或本期刊登承诺。
- [ ] 衔接：W04按计划取得关键材料，W05依据真实结果重新选择，不沿用初选自证。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：无价值则DROP/降优先；重要但未熟则WATCH并留下具体接续条件。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W03-ACCEPTANCE-20261020-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#W03-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#01-editorial/TopicDecisions-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#01-editorial/AccessObservations-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#01-editorial/整刊比较与投入决定.md", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#02-research/ResearchPlans-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#02-research/W04-priority-and-return-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#03-coverage/ReferenceEditorialComparison-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#03-coverage/CoverageGap-v002.json", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#05-handoff/W04-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#04-validation/W03-content-check-v001.md (RV-W03-CONTENT-20261020/M01—M12)", "private:/新闻/SI-WEEKLY-2026-W42-W03-v01.zip#04-validation/W03-structure-check-v001.json (实际ID/状态/计划字段与输入字节检查)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w03-20261020 (W03-ACCEPTANCE-20261020-001；原三项验收与Q01—Q07)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w03-20261020 (RV-W03-PERSISTENCE-20261020；实际保存及28文件/27项清单回读)"], "reviewer": "Codex同一实际执行者人工编辑/本包检查，已见W02与草稿；不是独立L5、盲审或用户认可", "result": "ACCEPTED", "scope": "仅SI-WEEKLY-2026-W42的W03人工初选与S7计划；26卡/3拟取证/16WATCH/7待核，3计划10取证动作，10参照与7类缺口；私有保存版本0/113611字节/SHA-256 5916f2834267bc2cca90a6d028e0efc886fc0785817ea2e81abf3fc58f440c3e，28文件/27清单回读相符；全部晚取得/历史正文未证；无S8/COVER/Review、正文、G01或生产实现，W04尚未开始"}]

<a id="w04"></a>
## W04｜真实原件、许可与主张支持核对

顺序：4/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W03](#w03)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T04](TECHNICAL_TRACE.md#t04)、[R04](TECHNICAL_TRACE.md#r04)。

逐项逻辑：T04.L01、T04.L02、R04.F01、R04.F02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：S7计划、具体作品/版本及允许访问、处理、保存、翻译和收录范围。

**交付物**：

- 实际取得记录、原段/原表定位、RightsRecord、支持与未知清单。
- 必要计算的真实输入/运行结果；定向补证及取得限制。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：关键主张能定位实际版本与核对范围，数量/单位/口径及来源独立性可复核。
- [ ] 反向：HTTP成功却无正文、真实但无关引用、局部支持整句、未执行代码均不能当已核结论。
- [ ] 衔接：向W05交S8前关键证据包；研究发现专业缺环时可带具体问题回本步追加材料。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按缺口补证、收窄或暂停；权限不足改允许定位/导引，不伪造原文或日志。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W04-ACCEPTANCE-20261020-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#W04-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#02-sources/SelectedSourcePacket-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#03-rights/RightsRecord-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#04-evidence/EvidencePacket-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#04-evidence/ClaimRegister-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#04-evidence/Calculations-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#05-scope/ReadingScopePlan-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#05-scope/FactLimitations-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#07-handoff/W05-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#06-validation/W04-manual-check-v001.md (RV-W04-CONTENT-20261020；原三项及Q01—Q07/衔接)", "private:/新闻/SI-WEEKLY-2026-W42-W04-v01.zip#06-validation/W04-structure-check-v001.json (实际ID/引用/10动作覆盖与计算)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w04-20261020 (RV-W04-PERSISTENCE-20261020；26文件/25清单实际保存回读)"], "reviewer": "Codex同一执行者实际回源/运算/L3检查；不是盲审、独立L5或用户认可", "result": "ACCEPTED", "scope": "仅W04手工S8前证据包：19文档/指针、21支持关系、9权限、3真实计算及10限制，IEA关键页实际核；不是19原件全齐，正式收费表/MoU/国家原通告等未取，历史正文未证；私有版本0/81521字节/1887d65c97b563230f409dfb878c1758375f3226fdc0dd11a62a7ad4efbdb0b5、26文件25清单回读一致。无S8/COVER/读者正文/Review/G01或生产验收，W05尚未开始"}]

<a id="w05"></a>
## W05｜S8复选与入选中文材料

顺序：5/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W04](#w04)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T03](TECHNICAL_TRACE.md#t03)、[T04](TECHNICAL_TRACE.md#t04)、[R03](TECHNICAL_TRACE.md#r03)。

逐项逻辑：T03.L02、T04.L03、R03.F01、R03.F02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：实际证据包、拟用稿型、许可及原作重点的必要上下文。

**交付物**：

- S8后决定、稿型/刊登依据及未完成研究责任。
- 仅对确定入选范围制作的中文材料/导引、节选标识与原文对应。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：查证结果确实改变或支持选择；中文保留关键否定、限定、表注与单位。
- [ ] 反向：未经许可不收录/翻译全文；节选不冒称全译；无旧稿的INITIAL_FACT不伪造前文。
- [ ] 衔接：深度题进入W06；精选/首次事实/进展/更正按R03保留对应责任，之后同受W11—W12检查。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：材料、价值或类型实变回S8；无许可则合法导引；不得靠改型逃避整刊深度。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W05-ACCEPTANCE-20261020-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#W05-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#01-selection/S8Decisions-v002.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#01-selection/CandidateDisposition-v002.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#03-reader/ReaderMaterialIndex-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#04-source-map/SourceMap-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#04-source-map/ActualUseRights-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#05-coverage/ReferenceEditorialComparison-v002.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#05-coverage/CoverageGap-v003.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#07-handoff/W06-input-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#07-handoff/R03-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#06-validation/W05-manual-check-v001.md (RV-W05-CONTENT-20261020；本卡三项/Q01—Q07，8正向/10显著过强句/3衔接)", "private:/新闻/SI-WEEKLY-2026-W42-W05-v01.zip#06-validation/W05-structure-check-v001.json (实际SHA/锚点/引用/去向及算术)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w05-20261020 (RV-W05-PERSISTENCE-20261020；41文件40清单实际保存回读)"], "reviewer": "同一Codex实际S8/制作/回源检查；非独立L5、盲审、专家或用户认可", "result": "ACCEPTED", "scope": "仅W05人工S8及入选中文A：7实质复选5COVER2WATCH、19仅接续，1深度研究/3首次事实/1公开部分精选导引，5真实中文与19段原文对应、10局部观察、9实际用途权利，10参照/7开放覆盖缺口；回溯材料历史正文未证，正式收费表/独立效果/合同履约/国家原通告等缺口保留。私有版本0/121892字节/dfef666078dc8e5c46c2c3cba4e53cb7a141080005a49fbd4b01e3be51f95f0f、41文件40清单实际回读一致；未通过L5/整刊/G01或生产验收，W06尚未开始。"}]

<a id="w06"></a>
## W06｜联合界定事实、问题与完成边界

顺序：6/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W05](#w05)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T05](TECHNICAL_TRACE.md#t05)、[T07](TECHNICAL_TRACE.md#t07)、[R01](TECHNICAL_TRACE.md#r01)。

逐项逻辑：T05.L01、T07.L01、R01.F03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：同一已核事实包、S8范围、旧背景/知识的具体版本与当前限制。

**交付物**：

- M01—M03真实产物、主/子问题、事实与未知边界。
- 顾问和帝师从问题形成期共同提出的研究与知识问题。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：问题对应真实差异，完成标准说明要查清什么、什么仍可合理未决；B2从M02参与。
- [ ] 反向：不以固定角色话术或方法名称代替问题；不同截点/问题版本不拼成同一案卷。
- [ ] 衔接：W07—W10共享同一案卷版本，解释不足、取证不足与教学不足有不同返工去向。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：事实缺口回W04，选题实变回W03/W05；保留不依赖缺口的探索性质。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W06-ACCEPTANCE-20261021-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#W06-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#M01-M03-联合事实与问题案卷.md", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#01-facts/M01-FactBoundary-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#02-problem/M02-JointQuestions-v003.json", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#03-boundary/M03-ScopeConcepts-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#04-completion/CompletionAndReturns-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#07-handoff/W07-W10-input-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#07-handoff/SharedDossierIndex-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#06-validation/W06-manual-check-v001.md (RV-W06-CONTENT-20261021；8正向/10显著模拟反向/4衔接，本卡三项及Q01—Q07)", "private:/新闻/SI-WEEKLY-2026-W42-W06-v01.zip#06-validation/W06-structure-check-v001.json (31项结构/字节/引用/状态/算术)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w06-20261021 (RV-W06-PERSISTENCE-20261021；30文件29清单实际保存回读)"], "reviewer": "同一Codex实际顾问/帝师问题研究与回原作核查；非第二模型、独立L5、专家、盲审或用户认可", "result": "ACCEPTED", "scope": "仅W06人工M01—M03：同案卷D06-v001/P01-Q-v003，8事实、7子问完成标准、4顾问/5帝师早期问题，5层结果/6知识用途，关键原件及机制/结果缺口与不同返工去向保留。回溯历史正文未证，阶段联系为公司报告非独立因果；READY不是子问全解/L5或B1/B2/C完成。私有版本0/85952字节/59f1f24d7e5325023ab425f85f3dbb69db19465a903f83b6b8a5c3536f83188c、30文件29清单实际回读一致；W07—W10仍未开始。"}]

<a id="w07"></a>
## W07｜竞争解释、专业前提与真实方法应用

顺序：7/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W06](#w06)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T05](TECHNICAL_TRACE.md#t05)、[T04](TECHNICAL_TRACE.md#t04)、[R04](TECHNICAL_TRACE.md#r04)。

逐项逻辑：T05.L02、T05.L03、R04.F03、R04.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：共同问题、原作解释、必要专业资料、实际适用方法原文与反证。

**交付物**：

- M04—M09：条件/行动/过程、竞争解释、区分证据、反例与时滞。
- MethodUse、前提核对、补证及有限收口/停止依据。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：指出哪条材料区分哪些解释；方法的前提、必要中间过程及对判断的实际作用可查。
- [ ] 反向：前提失配撤销应用；同源重复和事后换标签不算验证；无法区分时不强编唯一原因。
- [ ] 衔接：专业缺环回W04；对象/价值/类型改变回W05；向W08/W09交可采用的有限结果。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按有价值新动作补研；无新增信息或获准资源受限时记录未完成与下一触发，不无限检索。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W07-ACCEPTANCE-20261022-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#W07-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#M04-M09-竞争解释与风险机制研究.md", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#01-sources/SourcePacket-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#01-sources/VersionAndLineage-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#02-research/MethodUse-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#02-research/M07-CompetingExplanations-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#02-research/M08-M09-ProcessCounterevidence-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#04-completion/RevisionAndReturns-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#05-handoff/W08-W09-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#06-validation/W07-content-check-v001.json (RV-W07-CONTENT-20261022；8正向/12显著模拟反向/4衔接)", "private:/新闻/SI-WEEKLY-2026-W42-W07-v01.zip#06-validation/W07-structure-check-v001.json (RV-W07-STRUCTURE-20261022；122项结构/身份/输入/来源字节/引用/算术)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w07-20261022 (RV-W07-PERSISTENCE-20261022；55文件54清单实际保存回读)"], "reviewer": "同一Codex人工专业取证/页图与方法核对/内容正反和衔接检查；非独立L5、专家、盲审或用户认可", "result": "ACCEPTED", "scope": "仅W07 M04—M09有限研究：D07-v001/P01-Q-v003，原版及修订DCT/说明函等8文书身份、12主张、3竞争解释/6观察、4方法、5风险链/5计算。前提失配的强信号应用撤销，项目原因/实际费用保护未决；历史正文仍未证。私有版本0/144798字节/784cff6707c1c2c6d5721f15a40a4168c819e7fb81ba378b62a8432d9e8a4d99、55文件/54清单实际回读。W08/W09实稿、独审、G01及生产未完成。"}]

<a id="w08"></a>
## W08｜顾问B1真实成稿与增益对照

顺序：8/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W07](#w07)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T06](TECHNICAL_TRACE.md#t06)。

逐项逻辑：T06.L01、T06.L02、T06.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.7](CANONICAL_SYSTEM_SPEC_V5.md#th-8-7)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：共同研究、主体处境/制度资源/行动和原作已有解释。

**交付物**：

- M10顾问稿、关键判断与支持、条件/反证/未知。
- 与原作及既有写法的具体段落对照，必要时才比较行动与机会。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：删去B1会失去的本案理解能具体指出；判断强度、主体约束与证据相称。
- [ ] 反向：通用建议、强造新观点、宣传当动机、融资当营收均不能借顾问身份通过。
- [ ] 衔接：与W09同一问题/截点互校；重要新判断回W07核证，再交W11。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：无理解增益先回研究；确应改型则由W05重新核本期依据和整刊责任。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W08-ACCEPTANCE-20261022-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W08-B1-v002.md", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#W08-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#01-reader/B1-数据中心承诺与风险-v001.md", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#02-analysis/JudgmentRegister-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#02-analysis/ActorsAndChoices-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#02-analysis/DossierRevision-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#03-comparison/顾问增益与实际改稿对照.md", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#04-handoff/W09-W11-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#05-validation/W08-content-review-v001.json (RV-W08-CONTENT-20261022；6正向/8显著模拟反向/4衔接)", "private:/新闻/SI-WEEKLY-2026-W42-W08-v01.zip#05-validation/W08-structure-check-v001.json (RV-W08-STRUCTURE-20261022；182项结构/字节/引用/算术)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w08-20261022 (RV-W08-PERSISTENCE-20261022；正文及71文件70清单实际保存回读)"], "reviewer": "同一Codex作者实际原件核对/全文阅读/改稿/正反及衔接检查；非独立L5、盲审、领域专家或用户认可", "result": "ACCEPTED", "scope": "仅W08 M10人工成稿及增益对照：B1-v002/D08-v001/P01-Q-v003，16段实稿/8判断/6主体/6对照，真实v001保留及4段修订。期限表述差异与来源路径定向回核；具体适用期限/项目原因/实际费用效果未决。私有包版本0/193067字节/c1fc86eab5e9d2d6c6f1393ab22fc367d371b5de707cfcd01bcf1dbc4787672c及单独正文实际回读。W09双向成稿互校、独立审稿、G01和生产未完成。"}]

<a id="w09"></a>
## W09｜帝师B2主动研究与自足讲解

顺序：9/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W07](#w07)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T07](TECHNICAL_TRACE.md#t07)。

逐项逻辑：T07.L02、T07.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1)、[§10.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-2-1)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：材料中的知识问题、实际知识来源、必要概念/专业前提及W08可用成果。

**交付物**：

- M11连续读者稿：具体事实—中间过程—认识—边界/反例—迁移重查。
- 知识依据、必要算例/图示及应登记概念，按实际需要留卡。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：不用术语仍能讲清关键连接，成熟知识可充分教学；迁移说明哪些条件需重新核。
- [ ] 反向：格言、加书名、改写B1、缺关键连接及无依据的跨情境套用须分别识别。
- [ ] 衔接：与W08双向纠偏；认识未形成回W07/原件，有据却未讲清只返教学；交W11审实际段落。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按原因补知识研究或重写连接；不靠字数、卡数或用户已掌握的宣称验收。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W09-ACCEPTANCE-20261022-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W09-B2-v002.md", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#W09-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#01-reader/B1-数据中心承诺与风险-v003.md", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#02-knowledge/KnowledgeQuestions-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#02-knowledge/KnowledgeClaims-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#02-knowledge/Calculations-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#02-knowledge/ConceptRegister-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#03-comparison/教学贡献与双向互校.md", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#03-comparison/MutualReview-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#04-handoff/W10-W11-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#05-validation/W09-content-review-v001.json (RV-W09-CONTENT-20261022；6正向/8显著模拟反向/4衔接)", "private:/新闻/SI-WEEKLY-2026-W42-W09-v01.zip#05-validation/W09-structure-check-v001.json (RV-W09-STRUCTURE-20261022；245项结构/字节/引用/算术)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w09-20261022 (RV-W09-PERSISTENCE-20261022；正文及91文件90清单实际保存回读)"], "reviewer": "同一Codex实际知识原文/全文/计算与顾问帝师互校、正反及衔接；非独立L5、盲审、专家或用户认可", "result": "ACCEPTED", "scope": "仅W09 M11人工教学及互校：B2-v002/B1-v003/D09/P01-Q-v003，22段/9知识主张/5计算/3人工概念登记/4对照，B1两段澄清和B2三段真实修订；所有假设非真实案例/独立验证/学习测量。项目原因/个案责任/净回收与账单未决。私有包版本0/255422字节/2c6c06c704443286f082da46858d47e8ce945bef2f5127a2fa7876edebfeb072和单独正文实际回读；W10、独审、整刊/G01和生产未完成。"}]

<a id="w10"></a>
## W10｜条件推演与事前复查准备

顺序：10/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W08](#w08)、[W09](#w09)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T08](TECHNICAL_TRACE.md#t08)。

逐项逻辑：T08.L01、T08.L02、T08.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：有据的B1/B2起点、合理未知和可观察条件。

**交付物**：

- 适用时的C：条件、行动、传导、时滞及可区分结果。
- M12事前原话/条件/观察窗口或无法确定原因、开放问题。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：每条路径的中间连接和可证伪条件可查；当期先保存准备，不等未来结果才出刊。
- [ ] 反向：仅好坏终点、凑概率/题数、未证原因当事实不得通过；确不适用须有据说明而非填零。
- [ ] 衔接：原判断进入W01档案，W11核条件表述，未来结果走R02/R05重新研究。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：传导缺环回W07，区分材料不足保留可辨别条件，不强造确定预测。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W10-ACCEPTANCE-20261022-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W10-C-v001.md", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#W10-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#02-scenarios/ConditionalPaths-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#03-theses/FormationEvidence-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#03-theses/M12-Preparation-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#04-archive/SI-WEEKLY-2026-W42/02-article/ART-SI-WEEKLY-2026-W42-001/archive-index-W10-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#04-archive/SI-WEEKLY-2026-W42/02-article/ART-SI-WEEKLY-2026-W42-001/theses/TH-SI-W42-POWER-C10-ENGINEERING-001-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#04-archive/SI-WEEKLY-2026-W42/02-article/ART-SI-WEEKLY-2026-W42-001/theses/TH-SI-W42-POWER-C10-RECOVERY-001-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#05-handoff/W11-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#06-validation/W10-content-review-v001.json (RV-W10-CONTENT-20261022；6正向/8显著模拟反向/6时间分类/4衔接)", "private:/新闻/SI-WEEKLY-2026-W42-W10-v01.zip#06-validation/W10-structure-check-v001.json (RV-W10-STRUCTURE-20261022；267项字节/身份/引用/原话/时间/档案)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w10-20261022 (RV-W10-PERSISTENCE-20261022；正文及113文件112清单实际保存回读)"], "reviewer": "同一Codex实际原文/正文/原档案与时间边界、正反/衔接检查；非独立L5、盲审、专家或用户认可", "result": "ACCEPTED", "scope": "仅W10人工C/M12准备：C-v001/D10/P01，2条件路径/2Thesis及原W01同任务槽位的实际追加；原话形成10月22日非18日预测，窗口为有理由事件触发，无新未来结果/点预测命中率/自动查询。113文件包版本0/310331字节/dacafff28e5f1be7855a5934008991b3eeedf99bf277aa154bdaf2e531eab100及单独正文真实回读。个案原因/责任/工程/净回收和账单未决，独立W11、整刊/G01及生产未完成。"}]

<a id="w11"></a>
## W11｜独立审稿、改稿与真实版本放行

顺序：11/59；阶段：1；类型：人工内容验证。

进度：**验收通过**；关联：CURRENT_BINDING；前置：[W08](#w08)、[W09](#w09)、[W10](#w10)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T09](TECHNICAL_TRACE.md#t09)、[R01](TECHNICAL_TRACE.md#r01)、[R03](TECHNICAL_TRACE.md#r03)。

逐项逻辑：T09.L01、T09.L02、T09.L03、R01.F04、R03.F03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§15.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-1)、[§15.2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-2)、[§15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：实际全文、原作/方法/计算、材料版本、限制与作者产物；检查任务与写作分开。

**交付物**：

- 先独立形成的具体疑点、回源核查、作者回应和修订差异。
- 绑定实际稿件版本/范围的Review及PASS/REVISE/BLOCK或待审。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：每个重要意见可定位原句和证据，改稿后核受影响内容；合理未知和合格成熟知识能正确接受。
- [ ] 反向：作者自评、预定PASS、投票或全拒稿不当能力证据；错审意见也须回原件修正。
- [ ] 衔接：事实退W04、问题/研究退W06/W07、教学退W09；实际通过版本交W12，不能只审案卷。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：关键未核保留待审/阻止相应用途；分歧回材料，不因流程走完提前盖章。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W11-ACCEPTANCE-20261023-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W11-专题全文-v001.md", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#W11-交付与验收.md", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#01-review/InitialInquiry-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#01-review/SourceVerificationAndFindings-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#03-revision/AuthorResponse-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#04-recheck/RevisionRecheck-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#05-decision/Review-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#06-handoff/W12-input-v001.json"], "validation_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#05-decision/Review-v001.json (RV-W11-CONTENT-20261023-001；首轮REVISE后修订/回源复核，PASS仅本专题单篇内容)", "private:/新闻/SI-WEEKLY-2026-W42-W11-v01.zip#09-validation/StructureCheck-v001.json (RV-W11-STRUCTURE-20261023；138项身份/时序/版本/结构)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w11-20261023 (RV-W11-PERSISTENCE-20261023；139文件138清单及独立全文实际回读)"], "reviewer": "本次Codex同一执行者参与前序写作，明确非盲；另行固定疑点并回原件/方法/实际演算/全文及diff核查。无第二人/模型/专家，无盲测或通用准入。", "result": "ACCEPTED", "scope": "仅W11第一阶段人工内容核查：8初始疑点/8实际意见、2修订要求、11来源范围与8算术；A02/B1-v004/B2-v003/C-v002及真实全文绑定RV-W11-CONTENT-20261023-001。139文件包版本0/415640字节/97611a22175d0bfa2d09f578a4bc9bb5f6e6690052815903d9fe9cc3b94b459e与全文回读相符。PASS只交W12内容使用，个案/原因/工程/净回收未知、原M12时间保留；视觉/完整样刊/G01、通用能力及生产未验。"}]

<a id="w12"></a>
## W12｜完整同周样刊与实际阅读验收

顺序：12/59；阶段：1；类型：人工内容验证。

进度：**待验收**；关联：CURRENT_BINDING；前置：[W11](#w11)。

前置尚未验收：无。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T03](TECHNICAL_TRACE.md#t03)、[T10](TECHNICAL_TRACE.md#t10)、[T11](TECHNICAL_TRACE.md#t11)、[R01](TECHNICAL_TRACE.md#r01)、[R03](TECHNICAL_TRACE.md#r03)。

逐项逻辑：T03.L03、T10.L01、T10.L02、T10.L03、R01.F05、R03.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.5](CANONICAL_SYSTEM_SPEC_V5.md#th-13-5)、[§13.6](CANONICAL_SYSTEM_SPEC_V5.md#th-13-6)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：真实同周专题及必要短稿、当前重要更新、有效Review和允许格式。

**交付物**：

- 封面/范围/截点、目录、卷首、深度主题及按需精选/更正的完整可读样刊。
- 原作重点与中文、来源/方法/权利索引、整刊漏题/解释审计及投入/失败记录。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：实际文件逐页/逐段查看，连续中文阅读清楚；B1/B2贡献和整刊互补有具体依据。
- [ ] 反向：标题删限定、卷首新增因果、单字改意、脚注/单位漏失须处理；单篇或PDF生成不代替整刊通过。
- [ ] 衔接：语义变动回W11及相应研究；纯呈现保留差异与审核承接。保存用户实际审阅读体验记录后交G01。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：未达内容或阅读要求继续修订，明确未验格式；本步不自动发信或转入生产。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W12-SAMPLE-20261023-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W12-v01.pdf", "private:/新闻/SI-WEEKLY-2026-W42-W12-v01.zip#04-edition/Edition-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W12-v01.zip#05-audit/Review-v001.json", "private:/新闻/SI-WEEKLY-2026-W42-W12-v01.zip#08-handoff/UserReading-v001.json"], "validation_refs": ["audits/w12-sample-20261023.json", "CANONICAL_SYSTEM_SPEC_V5.md#run-w12-sample-20261023"], "reviewer": "当前执行者实际原站/算术/稿件与21页呈现核查；同一执行者非盲，用户实际阅读意见未取得", "result": "AWAITING_REVIEW", "scope": "仅第一阶段W12完整回溯样刊制作与有限内容/呈现检查，21页/86块/55链接/5计算、四个明确边界副本及一合格呈现对照；214文件包和PDF已保存。用户实际阅读及第一阶段门待验；不等于全球完整覆盖、当前行情/疫情、业务模块或生产完成。"}, {"record_id": "W12-SAVED-READBACK-20261023-001", "artifact_refs": ["private:/新闻/SI-WEEKLY-2026-W42-W12-v01.pdf (actual stored SHA-256 1297b17353ba7c411b92b0ff8302e1ea0606639f143950b6f496680f59f52047)", "private:/新闻/SI-WEEKLY-2026-W42-W12-v01.zip#02-reader/完整样刊-v001.pdf (original render SHA-256 393f7c58eb6f7ab1656819a0fd78386b6aa133d65816f52ee4ce98e79fba801e)"], "validation_refs": ["audits/w12-saved-readback-20261023.json", "CANONICAL_SYSTEM_SPEC_V5.md#run-w12-saved-readback-20261023"], "reviewer": "当前执行者实际取回已保存版本，逐页文本/像素/链接核对；非用户阅读意见或阶段批准", "result": "AWAITING_REVIEW", "scope": "原PDF与独立存储PDF字节不相同，分别保留身份；21页文本、像素和55链接及8项目录一致，承接原有限内容/呈现检查。保存ZIP与原包逐字节相同，214文件/213项清单核过；用户实际阅读仍待，W12/G01未过，不继续W13/W14。"}]

<a id="g01"></a>
## G01｜第一阶段门：真实专题及完整同周样刊

顺序：13/59；阶段：1；类型：阶段门。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W01](#w01)、[W02](#w02)、[W03](#w03)、[W04](#w04)、[W05](#w05)、[W06](#w06)、[W07](#w07)、[W08](#w08)、[W09](#w09)、[W10](#w10)、[W11](#w11)、[W12](#w12)。

前置尚未验收：[W12](#w12)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R01](TECHNICAL_TRACE.md#r01)、[R03](TECHNICAL_TRACE.md#r03)、[R04](TECHNICAL_TRACE.md#r04)、[R07](TECHNICAL_TRACE.md#r07)、[T01](TECHNICAL_TRACE.md#t01)、[T02](TECHNICAL_TRACE.md#t02)、[T03](TECHNICAL_TRACE.md#t03)、[T04](TECHNICAL_TRACE.md#t04)、[T05](TECHNICAL_TRACE.md#t05)、[T06](TECHNICAL_TRACE.md#t06)、[T07](TECHNICAL_TRACE.md#t07)、[T08](TECHNICAL_TRACE.md#t08)、[T09](TECHNICAL_TRACE.md#t09)、[T10](TECHNICAL_TRACE.md#t10)、[T11](TECHNICAL_TRACE.md#t11)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：本项为综合验收，按所列T/R及本卡检查。。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：W01—W12真实产物；实际用户审阅读体验记录与独立内容核查。

**交付物**：

- 第一阶段适用§19.4/19.5.1/19.6/19.7的逐项证据和未解决问题。
- 明确是否进入第二阶段，实际通过范围及阻碍。

**验收清单**（另核Q01—Q07）：

- [ ] 内容与证据：真实专题具备适用A/B1/B2/C、主张支持/条件、双方实际增益及独立Review。
- [ ] 范围与质量：同一真实周完整可读样刊及重要更新/漏题/解释审计、权利和实际阅读检查通过；用户意见如实记录。
- [ ] 禁止的捷径：模板齐全、单篇、分数、维护测试或文件生成不能替代内容验收；不启自动发信。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：保留实际证据与未过项，退回相应工作包修订；不能以后阶段工具或维护检查替代本阶段质量门。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w13"></a>
## W13｜共享对象、版本与档案基础接口

顺序：14/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[G01](#g01)。

前置尚未验收：[G01](#g01)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T11](TECHNICAL_TRACE.md#t11)、[T01](TECHNICAL_TRACE.md#t01)、[T04](TECHNICAL_TRACE.md#t04)。

逐项逻辑：T11.L01、T01.L01、T04.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§8.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-1)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：第一阶段真实案卷、对象/时间/权限定义与已确定的开发环境。

**交付物**：

- 单应用内的对象ID、追加式版本、三时间/事件区间/数据期和引用用途接口。
- 原稿/允许材料/定位与可重建索引的存取；按用途执行的权利、期限、地域、供应商、内容例外、条件、署名及部分撤权接口。
- 仓库外私有输出边界、部分授权的独立MaterialSelection、最小接口说明及旧JSON/旧数据库兼容迁移样例。
- C02优先Pydantic字段合同与SQLAlchemy Core事务/查询，私有版本正文接口只实现一次；C06用uv锁最小兼容组合，重型可选依赖分开。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：同一材料被多题引用仍只有一个权威版本；可完整取回原稿、审核及原判断。
- [ ] 反向：重复ID、悬空版本、无权全文写入或索引冒充事实原件均被识别；到期、未生效、地域/供应商/内容范围不匹配和未知条件均停止对应用途。
- [ ] 衔接：新正文写入前须有当前有效、条件已满足且覆盖完整内容的STORE_BODY结构化许可；失败不留下正文文件。后续读取同时核目标用途与当前保存许可。
- [ ] 部分内容或第三方排除权限不得返回原完整正文；只能返回引用原版本、具有独立有效全内容许可且字节哈希不同的MaterialSelection。
- [ ] 不同用途可有不同期限和撤权；未知或旧合同缺项不扩成通配授权，部分撤权保留无关用途及历史，STORE_BODY撤回使正文不可继续读取。
- [ ] 事件区间保留端点精度/语义、时区、出处与不确定性；旧JSON可读且不推定未知时区、午夜或更广许可。
- [ ] 档案、正文导出和准备包均拒绝整个Git工作树及符号链接别名，仓库外私有目录可用且不覆盖已有文件。
- [ ] T01/T04/T05/T09/T10通过同一接口引用真实版本，接口测试使用明示合法副本。
- [ ] 用同一真实对象跨模块读写验严格类型/枚举/引用与事务；结构合格不代事实/权利，锁定组合有实际安装/迁移/读取证据。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：缺宿主/权限则停止依赖操作；开发先小型持久关系库/版本文件，复用成熟接口，不另造事实库或高级索引。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W13-CODE-20261023-001", "artifact_refs": ["intelligence/contracts.py", "intelligence/archive.py", "intelligence/__main__.py", "pyproject.toml", "uv.lock", ".github/workflows/strategic-intelligence-runtime.yml (repository root)"], "validation_refs": ["tests_runtime/test_archive.py (30 actual passing runtime tests)", "audits/w13-archive-20261023.json (6 owned originals, pointer/shared references, restart readback and explicit migration copy)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w13-code-20261023"], "reviewer": "当前执行者实际编码、安装和离线测试；非内容/用户/阶段门批准", "result": "AWAITING_REVIEW", "scope": "W13代码已实现并离线测试；Pydantic/SQLAlchemy单应用共享合同、SQLite事务/私有版本文件、正文取回/索引重建/撤权/迁移和CLI。W12/G01未完成，故不记整包ACCEPTED；相邻业务消费者、完整研究/生产恢复及其他模块尚未验。"}, {"record_id": "W13-ORDER-CORRECTION-20261023-001", "artifact_refs": ["intelligence/contracts.py", "intelligence/archive.py", "intelligence/__main__.py"], "validation_refs": ["CANONICAL_SYSTEM_SPEC_V5.md#run-w12-sample-20261023", "audits/w12-sample-20261023.json"], "reviewer": "用户当前澄清及执行者实际依赖核对；不是阶段批准", "result": "BLOCKED", "scope": "纠正把咨询误读成优先编码授权；提前代码及原测试历史保留，W13后续暂停。W12/G01未过，先回W12与G01，过门再按原W13卡复核；未更改G01依赖，不启动W14。"}, {"record_id": "W13-REFERENCE-READ-20261023-001", "artifact_refs": ["intelligence/contracts.py", "intelligence/archive.py", "intelligence/__main__.py"], "validation_refs": ["tests_runtime/test_archive.py (41 actual passing runtime tests; 11 added)", "audits/w13-reference-read-20261023.json (explicit private test copy, 5 actual owned-file consumers, shared original bytes, CLI and withdrawal)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w13-reference-read-20261023"], "reviewer": "当前用户明确样刊后置与继续指令；执行者实际编码/离线接口检查，非用户阅读、内容或阶段批准", "result": "AWAITING_REVIEW", "scope": "按用户本次明确指令恢复W13小范围代码准备；补已提交引用归属、固定版本/类型/正文哈希、独立用途与撤权检查，共用唯一正文后端。41项运行测试和五类既有自有文件在明示副本的真实接口衔接通过；原私有档案7文件保持。样刊阅读后置但W12/G01未过，G01依赖保留，整包不记ACCEPTED；相邻业务模块/现行规范输入/权威采用/生产仍另包验。"}, {"record_id": "W13-REMEDIATION-20261025-001", "artifact_refs": ["intelligence/contracts.py", "intelligence/archive.py", "intelligence/__main__.py", "tests_runtime/test_archive.py", "audits/w13-w15-remediation-20261025.json"], "validation_refs": ["tests_runtime/test_archive.py (52 actual passing archive/contract/CLI tests)", "audits/w13-w15-remediation-20261025.json"], "reviewer": "当前执行者实际代码、正反、兼容读取和Git工作树边界检查；非法律审查、独立L5、用户阅读或阶段批准", "result": "IN_PROGRESS", "scope": "修复七项审核缺口中W13所属私有输出边界、逐用途权利/期限/地域/供应商/内容例外/条件/署名、部分撤权、事件区间及旧JSON兼容。schema升级到3但旧v1记录可读且不扩权；52项W13运行测试通过。W12/G01前置未过，整包不ACCEPTED；真实许可判断、跨周as-of、生产恢复及W17/W18身份/调用上下文仍待。"}, {"record_id": "W13-PR76-STORAGE-SELECTION-20261026-001", "artifact_refs": ["intelligence/contracts.py", "intelligence/archive.py", "tests_runtime/test_archive.py", "audits/pr76-review-remediation-step1-20261026.json"], "validation_refs": ["tests_runtime/test_archive.py (56 archive/contract/CLI tests passing after storage and selection regressions)", "audits/pr76-review-remediation-step1-20261026.json"], "reviewer": "当前执行者实际复现PR #76 F01/F02/F10、核对修复后正反与兼容读取；非真实许可判断或阶段批准", "result": "IN_PROGRESS", "scope": "F01/F02已修复离线共享边界：新正文仅在显式、当时有效、条件确认且全内容覆盖的STORE_BODY许可下写入；后续读取复核保存许可；部分授权只能返回独立MaterialSelection的精确字节，原完整正文或字节相同重贴均拒绝。旧schema1正文保留本地恢复读取，但新写入不能用旧缺项绕过。G01未过，W13仍非ACCEPTED。"}]

<a id="w14"></a>
## W14｜当前规范与任务输入准备接口

顺序：15/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W13](#w13)。

前置尚未验收：[W13](#w13)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T01](TECHNICAL_TRACE.md#t01)、[R07](TECHNICAL_TRACE.md#r07)。

逐项逻辑：T01.L01、R07.F01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-1)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：当前最高说明、T/R关联、实际任务/M步骤及材料依赖。

**交付物**：

- 任务准备入口：规范版本、适用原文定位、实际输入清单与缺口。
- 已有文档同步/关联检查接入研究任务的调用边界。
- C03 LangGraph任务节点统一调用已有维护检查与原文输入准备，不另造通用任务/状态框架；共用C02版本。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：真实任务正式采用前检查所用T/R关联，规范原文、材料和任务指令明确分开。
- [ ] 反向：过期视图、漏关键否定/例外、材料注入命令及伪造已读范围不能升级为有效输入。
- [ ] 衔接：向W15交实际提供的输入版本与性质；现有维护程序复用，但研究入口须另验。
- [ ] 图节点实际消费当前规范/证据版本，缺依赖进入既有返工分支；底座能运行不证明规范正确装载。
- [ ] 材料读取携带真实用途及可用的供应商/地域/内容上下文；权利未知、范围不符或旧合同缺项时进入缺口而非补成许可。
- [ ] 本地环境和缓存存在时维护检查无假失败，但未登记规则、缺失源码、过期视图和真实关联漂移仍阻断；所有私有输出遵守仓库外边界。
- [ ] get、read-reference与准备包均以O_EXCL/NOFOLLOW直接创建0600新文件；宽松umask、已存在文件、符号链接和仓库内路径均不得产生或覆盖私有输出。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：补原文/实际材料或停止受影响部分；不依赖缺口的修复/探索可继续。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W14-PREPARATION-20261024-001", "artifact_refs": ["intelligence/preparation.py", "intelligence/__main__.py", "pyproject.toml (optional workflow)", "uv.lock", ".github/workflows/strategic-intelligence-runtime.yml (repository root)"], "validation_refs": ["tests_runtime/test_preparation.py (14 actual passing W14 tests; 55 total runtime tests)", "audits/w14-preparation-20261024.json (actual private test copy: 4 owned files, 1 pointer, full current source, graph and CLI recheck)", "CANONICAL_SYSTEM_SPEC_V5.md#run-w14-preparation-20261024"], "reviewer": "当前执行者实际代码/接口正反与真实文件检查；非模型接收/理解、内容批准、用户阅读或阶段门验收", "result": "AWAITING_REVIEW", "scope": "W13提交及CI通过后，按用户样刊后置/继续指令逐包准备W14；LangGraph原生节点共用既有维护/W13，完整当前原文基线与任务/实际材料分隔，缺口/过期/漏条款/伪回执/撤权重核和私有CLI已验。55项运行测试及实际四份自有文件/一来源定位接口衔接通过；未做选择性精简或模型容量/质量验证。W12/G01及W13正式前置未通过，整包不记ACCEPTED；W15采用决定尚未开始。"}, {"record_id": "W14-TECHNICAL-REVIEW-20261025-001", "artifact_refs": ["intelligence/preparation.py", "intelligence/__main__.py", "tests_runtime/test_preparation.py"], "validation_refs": ["audits/w14-technical-review-20261025.json", "CANONICAL_SYSTEM_SPEC_V5.md#run-w14-technical-review-20261025"], "reviewer": "本次执行者Codex实际逐项技术复核；不冒称独立内容L5、用户阅读或阶段批准", "result": "AWAITING_REVIEW", "scope": "W14本卡及Q01—Q07逐项检查已执行：离线输入准备、正反/返工、实际仓库文件测试包装、W13共用和W15生产端合同检查通过；补两项回归，命令/结果及限制见审计。Q02正式前置W13及W12/G01未过，故整包仍待验，不记ACCEPTED；未运行W15消费者、模型或生产。"}, {"record_id": "W14-REMEDIATION-20261025-002", "artifact_refs": ["intelligence/preparation.py", "intelligence/__main__.py", "tests_runtime/test_preparation.py", "audits/w13-w15-remediation-20261025.json"], "validation_refs": ["tests_runtime/test_preparation.py (16 actual passing W14 tests; 74 total runtime)", "audits/w13-w15-remediation-20261025.json"], "reviewer": "当前执行者实际接口、输入合法性、权利上下文和仓库外输出检查；非模型接收/理解、独立内容或阶段批准", "result": "IN_PROGRESS", "scope": "W14继承PR #75两项回归，改用仓库外统一私有输出边界及可执行权利上下文；旧规范/漏条款/伪回执/撤权仍阻断。W13/W12/G01正式前置未过，不ACCEPTED；完整规范容纳与模型质量未验。"}, {"record_id": "W14-PR76-PRIVATE-EXPORT-20261026-001", "artifact_refs": ["intelligence/archive.py", "intelligence/__main__.py", "tests_runtime/test_archive.py", "audits/pr76-review-remediation-step1-20261026.json"], "validation_refs": ["tests_runtime/test_archive.py (get/read-reference/prepare direct 0600 creation under umask 022)", "audits/pr76-review-remediation-step1-20261026.json"], "reviewer": "当前执行者实际宽松umask、拒覆盖/路径/权限和仓库外成功对照；非用户或阶段批准", "result": "IN_PROGRESS", "scope": "F10已修复：get、read-reference和准备包统一调用O_EXCL/NOFOLLOW直接创建0600文件，不再先按umask创建后chmod；宽松umask下正文和准备包均为0600，既有文件不覆盖、仓库内路径与符号链接仍拒绝。W13/W12/G01正式前置未过，整包不ACCEPTED。"}]

<a id="w15"></a>
## W15｜采用检查与权威决定接口

顺序：16/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W14](#w14)。

前置尚未验收：[W14](#w14)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T01](TECHNICAL_TRACE.md#t01)。

逐项逻辑：T01.L02、T01.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：任务输入、实际前步产物、当前限制及相应内容核查记录。

**交付物**：

- 产物提交与决定写入分离的最小控制器及追加式StepSubmission/AdoptionDecision记录。
- 按精确Task/主体/Review/输入/依赖版本、状态、用途、范围和期限的采用检查与交接记录。
- submit-step、decide-step及current-decision离线CLI；调用者身份和完整研究图另包验。
- C03原生条件边/中断承载执行，C02权威决定与严格合同承载本刊采用范围；只加领域规则，不自研检查点引擎。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：PENDING/READY/RETURN/NOT_APPLICABLE/BLOCKED沿原定义；单独提交本身不产生当前权威决定，候选可交接但不升级为已证因果。
- [ ] 反向：写作职责自签READY/PASS、同一生产者署名、过期决定、跳步、缺Review或必输版本时无法正式采用；补齐后可按原版本继续。
- [ ] 衔接：决定绑定精确Task/主体/Review/输入/依赖版本与采用范围；上游版本或依赖变化不再满足当前采用，有据合格产物仍在范围内可继续。
- [ ] NOT_APPLICABLE须有实际Review与理由；CHECKER角色、READY范围、期限和依赖分别核，不以字段合法或全部拒稿代替。
- [ ] Review须以结构化引用实际覆盖当前主体/任务/用途；合法多主体Review显式列明覆盖，另一主体或版本不可授权当前决定。
- [ ] 权威决定链以稳定Task执行身份、步骤和必要作用域隔离；两个并行主题/期号不得互相覆盖同一work/step状态。
- [ ] 当前授权递归核必要依赖链：任一必要上游失效即不得采用下游历史READY；独立无关分支保留。主体/必输版本按用途撤回时也阻止采用，补核恢复后重新有效。
- [ ] 同一提交/采用接口覆盖M步骤和Review；任何图结束/next为空、字段合法、作者输出不得自变内容PASS或出版授权。
- [ ] 结构采用不认证调用者身份、不核内容真伪；W17身份/权限及W31内容审稿仍须实际验收，阶段门与真实研究图未通过。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按具体原因退责任模块或待核，保留允许的探索和未受影响产物。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W15-ADOPTION-20261025-001", "artifact_refs": ["intelligence/adoption.py", "intelligence/contracts.py", "intelligence/__main__.py", "tests_runtime/test_adoption.py", "audits/w13-w15-remediation-20261025.json"], "validation_refs": ["tests_runtime/test_adoption.py (6 actual passing W15 tests)", "audits/w13-w15-remediation-20261025.json"], "reviewer": "当前执行者实际离线接口与正反/衔接检查；非独立L5、身份认证、真实模型或阶段批准", "result": "IN_PROGRESS", "scope": "实现并持久追加StepSubmission/AdoptionDecision；单独提交不改变当前决定，README范围、精确Task/主体/Review/输入/依赖绑定、生产者自签拒绝、依赖过期、PENDING/READY/RETURN/BLOCKED/NOT_APPLICABLE与CLI已离线验证。checker身份、内容真伪、完整M图、模型执行和出版/交付未验；W14正式前置未过，整包不ACCEPTED。"}, {"record_id": "W15-PR76-REVIEW-RETURN-20261026-001", "artifact_refs": ["intelligence/adoption.py", "tests_runtime/test_adoption.py", "audits/pr76-review-remediation-step1-20261026.json"], "validation_refs": ["Codex-PR76-Review-20261025: F03/F04/F05 reproduced", "audits/pr76-review-remediation-step1-20261026.json"], "reviewer": "独立PR #76审查与当前执行者复现；非用户或阶段批准", "result": "RETURNED", "scope": "Review未绑定被审主体、不同Task共用决定键、传递依赖及主体撤回未传播均实际复现。原有限接口保留为历史，不得继续依赖；须先修复NC-056—058并补两任务/三层依赖/独立分支/恢复用例。"}, {"record_id": "W15-PR76-REMEDIATION-20261026-001", "artifact_refs": ["intelligence/contracts.py", "intelligence/adoption.py", "intelligence/archive.py", "intelligence/__main__.py", "tests_runtime/test_adoption.py", "audits/pr76-review-remediation-w15-20261026.json"], "validation_refs": ["tests_runtime/test_adoption.py (12 actual passing W15 tests)", "audits/pr76-review-remediation-w15-20261026.json"], "reviewer": "当前执行者实际离线合同、SQLite记录、正反/衔接与旧记录兼容检查；非独立L5、调用者身份、内容真伪或阶段批准", "result": "IN_PROGRESS", "scope": "F03—F05已修复离线范围：ReviewCoverage结构化绑定精确Task/主体/用途并支持多主体；决定与提交按稳定Task对象隔离，CLI显式按Task查询且旧共享槽只读筛选；当前采用递归核必要依赖、状态、期限、Task/主体最新版本及主体/Review/必输版本撤回。A→B→C、独立分支、两Task、主体撤回、新Task版本和检查后恢复均通过。W14/G01正式前置未过，调用者身份、真实L5、内容真伪、完整M图和生产仍未验，W15整包不ACCEPTED。"}]

<a id="w16"></a>
## W16｜共享研究修订与并发提交边界

顺序：17/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W13](#w13)、[W15](#w15)。

前置尚未验收：[W13](#w13)、[W15](#w15)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T05](TECHNICAL_TRACE.md#t05)、[T01](TECHNICAL_TRACE.md#t01)、[T11](TECHNICAL_TRACE.md#t11)。

逐项逻辑：T05.L01、T05.L02、T01.L02、T11.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：同一问题/证据/截点/限制修订及B1/B2/C/Review所基于的版本。

**交付物**：

- 研究修订身份与输入兼容性检查；输出链接及单条ResearchCommit组合提交接口。
- NC-041实现/验证证据、冲突与重核记录。
- C02复用SQLAlchemy事务/约束，显式expected revision/CAS及冲突/受影响行数检查，不另建并发存储框架。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：B1/B2共用同一有效研究截面，更新能定位失效输出；顺序执行也记录明确基线。
- [ ] 反向：以B1新版本拼B2旧版本、审核期间换证据及两个写入丢失更新均被拒绝或明确重核。
- [ ] 衔接：ArtifactLink/Commit须核作品原有依据、问题、证据版本/知识截点/限制与当前修订兼容；只换revision标签无效，无影响变化可留显式兼容复核继续。
- [ ] 期望当前ResearchRevision与期望上一Commit须在同一受控事务/CAS边界内核验并写入；检查后revision变化时提交冲突，不返回看似成功的最新旧组合。
- [ ] W27—W32提交均带所基于修订；受影响作品回责任模块，历史稿不覆盖。
- [ ] 实际数据库验顺序/并发/批量路径；ORM版本计数不自动覆盖批量写入，旧持有者不能覆盖新修订。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：冲突保留两版并补核；未实现并发能力时禁用并发写入，不能静默最后写入者获胜。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W16-REVISION-20261025-001", "artifact_refs": ["intelligence/research.py", "intelligence/contracts.py", "tests_runtime/test_research.py", "audits/w16-revision-20261025.json"], "validation_refs": ["tests_runtime/test_research.py (5 actual passing W16 tests)", "audits/w16-revision-20261025.json"], "reviewer": "当前执行者实际SQLite并发、版本绑定和正反检查；非独立L5、模型或阶段批准", "result": "IN_PROGRESS", "scope": "同一Theme修订追加、ArtifactLink精确修订绑定、单条ResearchCommit组合同步；B1新/B2旧、跨规范、旧持有者并发修订/提交及新修订使旧组合失效均验证。未接通W27—W32真实任务、Review换证据、模型内容或阶段门；W13/W15正式前置未过，不ACCEPTED。"}, {"record_id": "W16-PR76-REVIEW-RETURN-20261026-001", "artifact_refs": ["intelligence/research.py", "tests_runtime/test_research.py", "audits/pr76-review-remediation-step1-20261026.json"], "validation_refs": ["Codex-PR76-Review-20261025: F06/F09 reproduced", "audits/pr76-review-remediation-step1-20261026.json"], "reviewer": "独立PR #76审查与当前执行者复现；非用户或阶段批准", "result": "RETURNED", "scope": "旧作品仅重贴新revision可被认作当前成果，且revision检查与commit写入存在确定并发窗口，均已复现。原组合接口不得继续依赖；须先修复NC-059/062并验证关键/无关变化与revision/commit交错。"}, {"record_id": "W16-PR76-REMEDIATION-20261026-001", "artifact_refs": ["intelligence/research.py", "intelligence/archive.py", "intelligence/contracts.py", "tests_runtime/test_research.py", "audits/pr76-review-remediation-w16-20261026.json"], "validation_refs": ["tests_runtime/test_research.py (9 actual passing W16 tests)", "audits/pr76-review-remediation-w16-20261026.json"], "reviewer": "当前执行者实际离线研究修订、作品引用、兼容Review、SQLite条件写和并发交错检查；非独立L5、真实研究内容或阶段批准", "result": "IN_PROGRESS", "scope": "F06/F09已修复离线范围：修订结构化区分问题/证据/截点/限制，非critical以外默认关键；ArtifactLink保存并核对作品实际basis，旧作品仅在完整列举非关键增删并经精确Review兼容后沿用，关键变化须重建；Archive写事务同时核期望revision和上一commit，检查后换修订返回Conflict。重建、关键拒绝、无关通过、revision/commit交错及并发提交均有回归。W13/W15正式前置未过，真实W27—W32、模型内容与生产恢复未验，W16整包不ACCEPTED。"}]

<a id="w17"></a>
## W17｜工具适配器与真实操作身份

顺序：18/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W13](#w13)、[W15](#w15)。

前置尚未验收：[W13](#w13)、[W15](#w15)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T13](TECHNICAL_TRACE.md#t13)、[T11](TECHNICAL_TRACE.md#t11)。

逐项逻辑：T13.L02、T13.L03、T11.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-1)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：获准操作、实际配置、允许材料、任务和操作身份。

**交付物**：

- 最小可替换ToolAdapter、真实请求哈希/响应或错误、运行及逐次操作ID。
- 操作级重复请求识别、UNKNOWN对账、失败重试绑定及原始用量/费用/耗时记录。
- 逻辑操作历史、累计实际/估计费用、未知费用次数及耗时汇总；增加operation-summary只读CLI。
- C03统一任务调用/官方checkpointer；C06锁依赖，库/搜索/模型内置请求接同一权限/预算/操作记录，不增第二重试编排。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：实际返回与模型声称分开；重试/恢复可追原操作，未知和估计分别标明。
- [ ] 反向：请求已受理但超时不直接当未执行；模型不能补造成功、版本、页码或费用；不重复计同次操作。
- [ ] 衔接：W18控制调用前许可和预算，W24—W31使用同一适配器，恢复交W48；当前仅验已实现范围。
- [ ] 同一操作恢复保留身份/回执/累计费用；图replay会重执行后续节点，不能冒充外部副作用安全恢复；SDK重试受总控。
- [ ] UNKNOWN对账须绑定原operation、已知provider_request_id及真实查询证据；不同供应商请求或证据身份不符时继续UNKNOWN并禁止重试。
- [ ] 对账的状态检查、预期回执版本和写入须为同一事务/CAS；旧UNKNOWN调用不得覆盖已SUCCEEDED终态，终态成功不得开放再次执行。
- [ ] Adapter违规时只停止采用其结果，仍保留已返回的provider ID、费用、用量、内部重试与违规原因；不得降为null/0/UNKNOWN或重复计费。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：先核可查询的真实结果，再决定有限重试/停止；保持未知，禁止无限自动换模型求PASS。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W17-OPERATIONS-20261025-001", "artifact_refs": ["intelligence/operations.py", "intelligence/archive.py", "intelligence/contracts.py", "intelligence/__main__.py", "tests_runtime/test_operations.py", "audits/w17-operations-20261025.json"], "validation_refs": ["tests_runtime/test_operations.py (6 actual passing W17 tests)", "audits/w17-operations-20261025.json"], "reviewer": "当前执行者实际离线适配器、SQLite回执、重试/UNKNOWN与累计费用检查；非真实供应商、独立L5或阶段批准", "result": "IN_PROGRESS", "scope": "OperationRequest/Receipt持久追加、Adapter描述及字节结果校验；重复成功不再调用，仅FAILED可按原上限绑定重试，UNKNOWN先对账，内建重试超限转UNKNOWN，逻辑操作累计可用。W18授权/预算、真实第三方适配、模型内容及生产恢复未验；W13/W15正式前置未过，不ACCEPTED。"}, {"record_id": "W17-PR76-REVIEW-RETURN-20261026-001", "artifact_refs": ["intelligence/operations.py", "tests_runtime/test_operations.py", "audits/pr76-review-remediation-step1-20261026.json"], "validation_refs": ["Codex-PR76-Review-20261025: F07/F08/F11 reproduced", "audits/pr76-review-remediation-step1-20261026.json"], "reviewer": "独立PR #76审查与当前执行者复现；非用户或阶段批准", "result": "RETURNED", "scope": "错误供应商请求可对账、旧对账可把成功改为失败并开放重试、Adapter违规时丢失已观测事实，均已复现。原接口不得继续依赖；须先修复NC-060/061/064并补回执CAS交错与观测保留。"}, {"record_id": "W17-PR76-REMEDIATION-20261026-001", "artifact_refs": ["intelligence/operations.py", "intelligence/archive.py", "intelligence/contracts.py", "tests_runtime/test_operations.py", "audits/pr76-review-remediation-w17-20261026.json"], "validation_refs": ["tests_runtime/test_operations.py (10 actual passing W17 tests)", "audits/pr76-review-remediation-w17-20261026.json"], "reviewer": "当前执行者实际离线供应商对账身份、回执CAS、Adapter违规观测和累计费用检查；非真实供应商、独立认证或阶段批准", "result": "IN_PROGRESS", "scope": "F07/F08/F11已修复离线范围：UNKNOWN对账绑定原operation、原回执版本、已知provider ID及引用operation的Evidence；不同查询ID须带同版本ProviderRequestMapping。对账以expected-current CAS写回，不覆盖并发成功，失败/失败只留一个当前回执。Adapter违规结果不采用但保留provider ID、实际费用、用量、内部重试、观察状态/结果哈希和违规原因，汇总继续计费。W18授权/预算、真实供应商认证与生产恢复未验，W17整包不ACCEPTED。"}]

<a id="w18"></a>
## W18｜调用前权限、预算与能力核验

顺序：19/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W17](#w17)、[W15](#w15)。

前置尚未验收：[W15](#w15)、[W17](#w17)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T13](TECHNICAL_TRACE.md#t13)、[T01](TECHNICAL_TRACE.md#t01)。

逐项逻辑：T13.L01、T13.L03、T01.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：实际操作、任务配置准入范围、材料处理权和已获准额度/重试限制。

**交付物**：

- 调用前校验、共享预算预留/结算/未知处理及可核拒绝原因。
- NC-044证据；未配置项和受控试用的有限范围记录。
- C02/C03共享唯一调用门/预算账，第三方内置搜索、翻译、下载和模型请求也逐项受控，未接入钩子的组件不进入正式链。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：有授权且能力/材料用途符合的调用可执行；费用实际值/估计/未知及币种分开，预留可核。
- [ ] 反向：并发抢占同一余额不能超用；未知额度不当无限授权；无外发权、越准入范围或重试不足不能偷偷调用。
- [ ] 衔接：每次实际调用均经本入口；可先串行实现并拒绝不支持的并发，W48再验生产多任务恢复/结算。
- [ ] 验图节点/SDK/研究适配的重试总量与未知结算，不出现多层相乘费用；无法控住的研究器只能不接或作获准线索。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：不足/未知按实际已授权范围停止或受控处理；无授权不新增收费；关内容任务不妨碍离线修复。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W18-PRECALL-GATE-20261026-001", "artifact_refs": ["intelligence/gating.py", "intelligence/operations.py", "intelligence/archive.py", "intelligence/contracts.py", "tests_runtime/test_gating.py", "audits/pr76-review-remediation-w18-20261026.json"], "validation_refs": ["tests_runtime/test_gating.py (8 actual passing W18 tests)", "audits/pr76-review-remediation-w18-20261026.json"], "reviewer": "当前执行者实际离线能力准入、材料用途、预算CAS、Adapter调用前拒绝和合成回执检查；非真实供应商、独立L5或阶段批准", "result": "IN_PROGRESS", "scope": "W18离线门禁：CapabilityAdmission精确绑定Task/步骤/供应商/工具/配置/操作/材料/地域/期限/Review和重试；BudgetEnvelope与追加预算事件在执行前预留、执行后按实际/估计结算，未知费用保留，默认并发预留1并由expected-current保护。材料用途/外发/配置/重试不足均在Adapter调用前拒绝；受控试用显式标记人工复核。真实供应商认证/账单、生产预算/W48恢复仍未验，整包不ACCEPTED。"}]

<a id="w19"></a>
## W19｜模型任务配置与有限准入证据

顺序：20/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W18](#w18)。

前置尚未验收：[W18](#w18)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T13](TECHNICAL_TRACE.md#t13)、[T09](TECHNICAL_TRACE.md#t09)。

逐项逻辑：T13.L01、T13.L02、T09.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-1)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§17.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：拟用实际模型/版本、提示、工具、材料、人工帮助与明确职责。

**交付物**：

- 配置身份、给定材料/真实检索/约束增益分别记录的验证结果。
- 职责及领域有限准入、失败/未验范围与配置变更复验规则。
- C04共用模型配置/样稿记录；promptfoo只在少量现有验证不足时条件接实际CLI，复用已有真实正反例。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：配置能复现，保留失败；给定材料、检索、写作和审稿分别判断，不以同一分数通用授权。
- [ ] 反向：人工改稿冒充模型独立成功、只报最好一轮、固定材料通过后直接扩大到未验检索均不获准。
- [ ] 衔接：W28/W29/W31采用对应配置范围，变化触发实际受影响用途复验。
- [ ] 评测不另建内容批准源；模型/提示变更仍核任务范围，第三方打分不代回原文/独审。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：未验任务明确限制；允许的受控尝试仍须核产物，不按便宜或角色名直接放行。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W19-MODEL-ADMISSION-20261026-001", "artifact_refs": ["intelligence/model_admission.py", "intelligence/contracts.py", "tests_runtime/test_model_admission.py", "audits/pr76-review-remediation-w19-20261026.json"], "validation_refs": ["tests_runtime/test_model_admission.py (7 actual passing W19 tests)", "audits/pr76-review-remediation-w19-20261026.json"], "reviewer": "当前执行者实际离线配置指纹、三类合成验证、全尝试/人工帮助、职责领域限定与复验映射检查；非真实模型能力、独立L5或阶段批准", "result": "IN_PROGRESS", "scope": "W19离线记录：配置精确绑定供应商/模型/任务/提示/上下文/生成/方法/工具/职责/领域/材料形式，未知项显式；给定材料、真实检索、约束增益分别验证并保留全部尝试/失败/人工帮助/未验范围；准入只授明确职责领域，固定材料不扩为检索，关键失败/人工帮助降为受限或受控试用，配置变化旧准入失效并按身份/范围影响列复验。未调用真实模型、未做内容质量或W28/29/31消费，整包不ACCEPTED。"}]

<a id="w20"></a>
## W20｜少量来源适配与候选输入

顺序：21/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W17](#w17)、[W18](#w18)。

前置尚未验收：[W17](#w17)、[W18](#w18)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T02](TECHNICAL_TRACE.md#t02)。

逐项逻辑：T02.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-4-1)、[§4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-4-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：本轮实际需要、已核许可的少量来源及区间；不预设具体项目版本。

**交付物**：

- 最小来源适配器与CandidateIndex、实际取得元信息和故障记录。
- C01首选feedparser解析已获准Feed字节、Trafilatura处理合法HTML；T02/T04共用入口，RSSHub仅具体路由需要时接。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：合法RSS/API/页面等按实际配置取得可回查线索，日期/摘要缺失如实标记。
- [ ] 反向：来源不可用保留缺口；标题不能补造正文事实，手动探测成功不当自动发现已验。
- [ ] 衔接：输出交W21/W23；关闭日报仍独立工作；W47才补生产增量/巡视频率。
- [ ] 在真实Feed/页面核日期/缺字段/血缘/覆盖时段/失败；第三方解析成功不是合法使用、实际支持或全球覆盖。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：保留故障并改其他获准来源；不一次接入全部候选工具/来源。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W20-SOURCE-ADAPTER-20261031-001", "artifact_refs": ["intelligence/sources.py", "intelligence/contracts.py", "tests_runtime/test_sources.py", "pyproject.toml", "uv.lock", "audits/pr76-review-remediation-w20-20261031.json"], "validation_refs": ["tests_runtime/test_sources.py (6 actual passing W20 tests)", "feedparser 6.0.14; trafilatura 2.3.1; lxml 6.1.3 locked", "audits/pr76-review-remediation-w20-20261031.json"], "reviewer": "当前执行者实际离线Feed/HTML/JSON字节、字段/时间缺口、失败索引、权限边界与Archive往返检查；非真实来源、内容或阶段批准", "result": "IN_PROGRESS", "scope": "W20离线来源入口：仅解析明确许可的既有字节，Feed使用feedparser、HTML使用Trafilatura、JSON API按显式items映射；CandidateIndex保存来源/取得方式/哈希/语言地区所有权、短摘或摘要、时间精度、血缘、缺字段、故障和人工探测性质，原始正文不随候选保存。真实网络来源、覆盖时段、事件归并和W21/W23消费未验，整包不ACCEPTED。"}]

<a id="w21"></a>
## W21｜事件归并、血缘与探索队列

顺序：22/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W20](#w20)、[W13](#w13)。

前置尚未验收：[W13](#w13)、[W20](#w20)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T02](TECHNICAL_TRACE.md#t02)。

逐项逻辑：T02.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-4-2)、[§4.3](CANONICAL_SYSTEM_SPEC_V5.md#th-4-3)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：真实候选、原发/转引链及可得事件事实。

**交付物**：

- 事件归并建议、来源血缘、未确定合并与探索队列。
- 共用W20/C01原始入口和C02血缘对象，只写本刊归并/探索规则，不另建采集/清洗服务。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：同一事件更新可关联、真实不同事件可拆开，保留原始候选与合并理由。
- [ ] 反向：十次同源转载不作十个独立立场，模糊相似不强并；冷门候选不因无热度自动丢弃。
- [ ] 衔接：T03可覆核合并且保留差异，后续证据支持独立性回到血缘而非URL数量。
- [ ] 同一批来源可共验解析与归并，但保留归并判断及同源/独立结果，不用同源数量证明证据充分。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：不确定则交编辑核；语义聚类确有必要才接入经过任务验证的模型。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W21-CLUSTER-PROPOSAL-20261031-001", "artifact_refs": ["intelligence/discovery.py", "intelligence/sources.py", "intelligence/contracts.py", "tests_runtime/test_discovery.py", "audits/pr76-review-remediation-w21-20261031.json"], "validation_refs": ["tests_runtime/test_discovery.py (5 actual passing W21 tests)", "audits/pr76-review-remediation-w21-20261031.json"], "reviewer": "当前执行者实际离线强键归并、同源/独立根、歧义编辑复核、探索队列和Archive往返检查；非真实来源、T03内容或编辑批准", "result": "IN_PROGRESS", "scope": "W21离线提案：只有显式事件键、已记录共同血缘根、canonical/duplicate候选关系或完全同URL才建立合并建议；标题相似和possible-related不强制合并且进探索队列。十次同源转载只计一个血缘根，独立来源按原始根而非URL数；差异、成员、来源和理由保留交T03复核，低热候选不丢弃。真实来源链、内容归并判断、W22覆盖及W23选择未验，整包不ACCEPTED。"}]

<a id="w22"></a>
## W22｜独立参照与覆盖缺口接口

顺序：23/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W20](#w20)、[W21](#w21)。

前置尚未验收：[W20](#w20)、[W21](#w21)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T02](TECHNICAL_TRACE.md#t02)、[T03](TECHNICAL_TRACE.md#t03)。

逐项逻辑：T02.L03、T03.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§4.4](CANONICAL_SYSTEM_SPEC_V5.md#th-4-4)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：事先固定范围的独立参照、候选/入选及实际取得限制。

**交付物**：

- CoverageGap及未发现/取得失败/主动舍弃/未成熟/重复覆盖的区分记录。
- C01/C02复用入口/时间/来源记录，池外参照独立固定范围；不为防漏另造常驻监测平台。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：能从参照回查具体遗漏及原因，非热门地区/正面事项有真实比较记录。
- [ ] 反向：用入选稿倒推参照、把断源当无重要事件、领域配额冒充覆盖均被指出。
- [ ] 衔接：缺口返回T02发现或T03重选，在W36/W41核整刊影响，不声称全球无遗漏。
- [ ] 共用取得代码仍须独立参照，不能从候选/入刊反推池外集合；覆盖缺口与取得失败分别记录。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：限定参照覆盖范围和剩余盲区，具体重要漏题优先处理。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W22-COVERAGE-AUDIT-20261031-001", "artifact_refs": ["intelligence/coverage.py", "intelligence/discovery.py", "intelligence/sources.py", "intelligence/contracts.py", "tests_runtime/test_coverage.py", "audits/pr76-review-remediation-w22-20261031.json"], "validation_refs": ["tests_runtime/test_coverage.py (5 actual passing W22 tests)", "audits/pr76-review-remediation-w22-20261031.json"], "reviewer": "当前执行者实际离线预固定参照、候选/入选比较、七类缺口和Archive往返检查；非真实来源、编辑决定或阶段批准", "result": "IN_PROGRESS", "scope": "W22离线比较：参照计划须在CandidateIndex/EventClusterProposal之前固定且不得由域配额、候选或入选结果倒推；独立通道失败单列SOURCE_UNAVAILABLE，参照与候选可按精确事件键或显式匹配比较。未发现、聚类/筛选漏失、编辑舍弃、材料不足、未成熟、他题覆盖和重复覆盖分别记录责任人/下一步；审计明确global_recall_claim=false，只覆盖声明窗口/通道。真实参照、W23选择、W36/W41整刊影响未验，整包不ACCEPTED。"}]

<a id="w23"></a>
## W23｜初选、S8与当期取舍记录

顺序：24/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W15](#w15)、[W21](#w21)。

前置尚未验收：[W15](#w15)、[W21](#w21)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T03](TECHNICAL_TRACE.md#t03)。

逐项逻辑：T03.L01、T03.L02、T03.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.4](CANONICAL_SYSTEM_SPEC_V5.md#th-5-4)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：候选/血缘、证据包接口、Theme及期号和刊登依据。

**交付物**：

- S0—S7/S8前后决定与理由、阅读计划、稿型及publication_basis。
- 长期研究准入与本期刊登分离的选题接口。
- C04编辑任务共用C02决定/版本、C03 S工序，不新增选题框架；S8与研究/刊登权限分别保存。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：同候选前后决定可比较，重要单次事项、长期题与困难题能按实际证据走不同分支。
- [ ] 反向：最高分拼刊、COVER=PASS、沉没投入强发和长期题自动降成当周精选均不能发生。
- [ ] 衔接：W24—W26提供证据/中文版本，R04改变对象/类型回S8，整刊最终再比较价值。
- [ ] 同一真实主题可连W25/W27验往返，但逐项留初选、取证后复选和本期取舍依据。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：WATCH留具体下一动作，改型重核适用责任与整刊深度；程序不替编辑作无据判断。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W23-EDITORIAL-AUDIT-20261031-001", "artifact_refs": ["intelligence/editorial.py", "intelligence/contracts.py", "intelligence/sources.py", "intelligence/discovery.py", "intelligence/coverage.py", "tests_runtime/test_editorial.py", "audits/pr76-review-remediation-w23-20261031.json"], "validation_refs": ["tests_runtime/test_editorial.py (10 actual passing W23 tests)", "audits/pr76-review-remediation-w23-20261031.json"], "reviewer": "当前执行者实际离线检查S0—S8历史、S8包对象身份、候选/事件簇/覆盖审计绑定、研究/刊登权限分离和并发旧证据反例；非真实编辑、内容、审稿或阶段批准", "result": "IN_PROGRESS", "scope": "W23离线记录：S0—S7/WATCH与S8/COVER前后决定保留；S8包必须绑定实际QuestionVersion、SourceMaterial、Evidence、RightsRecord、ReadingScopePlan、CandidateIndex、EventClusterProposal及可选CoverageAudit，依赖过期或错类型阻止COVER准入；研究准入只保留COVER稿型且hard-coded无出版权，期次建议必须由当前COVER、有效研究准入和显式位置组成，研究准入/期次建议均不授予刊登。十项回归覆盖高分不自动拼刊、外来候选/事件簇、错误类型、新证据失效、旧决定失效、长期题降型和校验后并发CAS。W24—W26真实证据/中文、W31审稿、W36/W39/W41闭环及用户阅读未验，整包不ACCEPTED。"}]

<a id="w24"></a>
## W24｜原件取得、结构提取与用途控制

顺序：25/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W13](#w13)、[W17](#w17)、[W18](#w18)、[W23](#w23)。

前置尚未验收：[W13](#w13)、[W17](#w17)、[W18](#w18)、[W23](#w23)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T04](TECHNICAL_TRACE.md#t04)。

逐项逻辑：T04.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：具体作品/版本、S7/补证请求与实际用途许可。

**交付物**：

- 原文/允许副本或定位、解析结果、真实取得/核对范围、RightsRecord。
- C01共用Trafilatura与合法字节入口，复杂PDF/表格/OCR确需再接Docling；C02共享Rights/Source与原版定位。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：能回原页/原段/原表，复杂表格或OCR关键数据核原件，存留内容符合相应用途。
- [ ] 反向：空正文、错版本、解析截断及无权保存/翻译必须显式处理，模型输出不能自写已核。
- [ ] 衔接：向W25/26交同一实际版本，许可或重要修订回W34限制已知用途。
- [ ] 用同一真实页面/报告回核截断、原表数值/单位/上下文和实际版本；轻文本不强装OCR，模型权重许可/投入另验。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：改合法定位/导引或报缺口，不用现网页伪造旧版，故障不误删其他有效材料。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W24-ORIGINAL-AUDIT-20261031-001", "artifact_refs": ["intelligence/original.py", "intelligence/contracts.py", "intelligence/editorial.py", "tests_runtime/test_original.py", "audits/pr76-review-remediation-w24-20261031.json"], "validation_refs": ["tests_runtime/test_original.py (15 actual passing W24 tests)", "audits/pr76-review-remediation-w24-20261031.json"], "reviewer": "当前执行者实际离线检查获准字节、原文/结构/权利/取得记录、用途门禁和并发反例；非真实来源取得、PDF/OCR、事实核对或阶段批准", "result": "IN_PROGRESS", "scope": "W24离线接口：从当前S7 WATCH/REVISE或S8 COVER及明确请求处理调用者提供的精确字节；错哈希/格式、空正文、陈旧或DROP决定被阻断。STORE_BODY决定是否保留原件，MODEL_PROCESS决定是否运行结构提取，TRANSLATE按精确源版本另行检查；HTML/纯文本生成不含正文的节点定位和哈希，表格/图像强制回原件，PDF只保存并标记解析器/OCR缺口。RIGHTS_RECORD、SOURCE_STRUCTURE与SOURCE_INTAKE均引用同一SOURCE_MATERIAL版本；首段部分取得、无保存权、无处理权、错误版本、空源、PDF未解析、重复取得和操作中决定变更均有反例。未用真实网页/PDF/扫描件、Docling、OCR、翻译、Claim支持或W25/W26闭环，整包不ACCEPTED。"}]

<a id="w25"></a>
## W25｜主张支持、计算与定向补证接口

顺序：26/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W24](#w24)、[W16](#w16)。

前置尚未验收：[W16](#w16)、[W24](#w24)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T04](TECHNICAL_TRACE.md#t04)、[T05](TECHNICAL_TRACE.md#t05)、[R04](TECHNICAL_TRACE.md#r04)。

逐项逻辑：T04.L02、R04.F01、R04.F02、R04.F03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：具体主张/缺环、原件和专业条件、计算输入及可区分证据。

**交付物**：

- Claim—Evidence支持范围/反证/未知、来源独立性及实际计算记录。
- 补证请求与真实结果、受影响判断的前后差异。
- C02共享Claim—Evidence和计算记录；C04定向补证复用C01/C03，GPT Researcher仅有据试用受控适配，不接默认报告/导出。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：主张强度对应实际支持；计算输入、口径/单位/时间与执行结果均可核。
- [ ] 反向：真实无关引用、局部支持、同源重复、公式正确但输入错及生成代码未执行均不通过。
- [ ] 衔接：发现条件失配回W27并按影响回W23，查剩余支持后再限制/恢复用途。
- [ ] 补证器必须留真实原件/版本/支持范围及内部调用/预算；无法控制或只给摘要链接时不算证据完成，回本刊取证。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：有区分价值才继续补证；无条件完成则收窄/待研，不能由日志齐全推断因果成立。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W25-EVIDENCE-AUDIT-20261031-001", "artifact_refs": ["intelligence/evidence.py", "intelligence/original.py", "intelligence/discovery.py", "intelligence/contracts.py", "tests_runtime/test_evidence.py", "audits/pr76-review-remediation-w25-20261031.json"], "validation_refs": ["tests_runtime/test_evidence.py (12 actual passing W25 tests)", "audits/pr76-review-remediation-w25-20261031.json"], "reviewer": "当前执行者实际离线检查精确节点、来源根、支持范围、十进制计算和补证结果；非真实语义支持、外部检索、专家、审稿或阶段批准", "result": "IN_PROGRESS", "scope": "W25离线接口：Claim与Evidence绑定W24的精确SourceIntake、结构节点和哈希；来源根从W21事件簇成员读取，同一根重复证据不增加独立根数。ClaimEvidenceAssessment显式记录支持/部分支持/反证/仅背景/无关/未决、适用范围、条件、不支持面、反证和未知，并只声明locator replay。CalculationRecord只运行受控Decimal加、减、乘、除和百分比变化，核节点值文本、单位文本、维度声明、源数据期、舍入和实际结果，不接受任意生成代码。SupplementRequest/Result可记录无新增证据、部分结果和实际新增SourceIntake/Evidence/Assessment，前后关系与影响分开；对象或范围变化强制S8复核。GPT Researcher试用适配未实现，当前明确拒绝而非伪造调用。十二项回归覆盖支持/部分/无关、同源重复、W16 Evidence交接、计算正反例、未执行代码、真实补证前后及S8标记。真实内容语义、W27条件失配、外部适配/预算和W38整链仍未验，整包不ACCEPTED。"}]

<a id="w26"></a>
## W26｜入选中文、节选边界与重要更新

顺序：27/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W24](#w24)、[W25](#w25)、[W23](#w23)。

前置尚未验收：[W23](#w23)、[W24](#w24)、[W25](#w25)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T04](TECHNICAL_TRACE.md#t04)、[T03](TECHNICAL_TRACE.md#t03)。

逐项逻辑：T04.L03、T03.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：S8确定范围、许可、原件/表注与实际译文配置。

**交付物**：

- 版本化中文/导引、原文范围对应和节选标识。
- 定稿前重要更新及截点变化的影响记录。
- 入选重点翻译共用已验模型/翻译接口；BabelDOC仅确需PDF版式时、Argos仅真实离线质量达标时条件采用，不装并行常驻翻译服务。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：普通中文准确保留限定/否定/单位，长报告重点包含理解本题所需语境。
- [ ] 反向：S8前批量全译、节选冒充全文、漏否定或无授权收录均被识别；后出材料不混入旧截点。
- [ ] 衔接：译文更正进入W34，重要更新回研究/审稿或明确保留原截点并调整刊登。
- [ ] 实际专业材料核否定/数字/表注/边界和语言包许可；开源/离线不代准确或零算力费用，不默认全篇翻译。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：回原作核对/改允许导引；材料不足报具体限制，不以更流畅掩盖错译。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W26-MATERIAL-AUDIT-20261031-001", "artifact_refs": ["intelligence/materials.py", "intelligence/original.py", "intelligence/evidence.py", "intelligence/editorial.py", "intelligence/contracts.py", "tests_runtime/test_materials.py", "audits/pr76-review-remediation-w26-20261031.json"], "validation_refs": ["tests_runtime/test_materials.py (7 actual passing W26 tests)", "audits/pr76-review-remediation-w26-20261031.json"], "reviewer": "当前执行者实际离线检查S8后范围、翻译权利、原文节点映射、全文/节选标签、版本链和截点更新；非真实翻译、双语校对、读者、审稿或阶段批准", "result": "IN_PROGRESS", "scope": "W26离线接口：中文材料只在当前S8 COVER及同一决定历史授权的SourceIntake上制作，必须引用W25 Evidence并映射精确原文节点。节选译文强制列明省略，全文译文要求完整取得、无缺口全节点结构及独立全文覆盖证明，独立导读只要求机器处理权而不冒充译文；否定、数字、单位/分母、条件、表注和归属可逐项登记源/中文位置，表格/图像必须有原视觉核对。ChineseMaterial与SourceMap按稳定material_id追加版本，旧版本历史保留。定稿前ImportantUpdateCheck独立记录后取得来源、核心影响、是否越出原截点及NO_UPDATE/更新截点/W23/W25/W34去向；后出核心材料不能被标成无更新或写回旧版本。七项回归覆盖节选、全文、独立导读、无翻译权、无省略/外来证据、版本修订、S8前阻断及截点更新隔离。真实语义翻译、否定/表注准确、BabelDOC/Argos、W31审稿和实际读者验收未完成，整包不ACCEPTED。"}]

<a id="w27"></a>
## W27｜M工序、共同研究与有限收口接口

顺序：28/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W16](#w16)、[W25](#w25)、[W19](#w19)。

前置尚未验收：[W16](#w16)、[W19](#w19)、[W25](#w25)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T05](TECHNICAL_TRACE.md#t05)、[T07](TECHNICAL_TRACE.md#t07)、[R04](TECHNICAL_TRACE.md#r04)。

逐项逻辑：T05.L01、T05.L02、T05.L03、T07.L01、R04.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§8.5](CANONICAL_SYSTEM_SPEC_V5.md#th-8-5)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：共同案卷修订、真实问题、专业资料/方法原文、前步可用产物。

**交付物**：

- M01—M12依赖组织及真实中间产物；B1/B2从问题期共同参与。
- 竞争解释/MethodUse/未知与补证、改题、暂停的有据路由。
- C03嵌入式LangGraph/官方checkpointer运行M依赖，C04同一组明确任务函数共享C02案卷；不另造研究编排器或接完整报告框架。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：方法前提被实际查验，研究按具体依赖推进；M07不是首次选方法，M12不等未来才开始。
- [ ] 反向：流程齐全但无解释、假设自动升级事实、未完成改称不适用和静态设计依赖当启动门均被阻止。
- [ ] 衔接：采用边界共用W15；事实回W25、对象/价值回W23、教学不足回W29，并保存检查点。
- [ ] 在同一真实题验问题/补证/改题/有限收口，B1/B2均从问题期贡献；节点齐全/原生恢复不代内容完成。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：说明已做/未做及下一动作价值，有据有限交付或暂停；不为PASS无限重写。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W27-WORKFLOW-AUDIT-20261031-001", "artifact_refs": ["intelligence/workflow.py", "intelligence/research.py", "intelligence/evidence.py", "intelligence/model_admission.py", "intelligence/operations.py", "intelligence/contracts.py", "tests_runtime/test_workflow.py", "audits/pr76-review-remediation-w27-20261031.json"], "validation_refs": ["tests_runtime/test_workflow.py (8 actual passing W27 tests)", "audits/pr76-review-remediation-w27-20261031.json"], "reviewer": "当前执行者实际离线检查M依赖、B1/B2早期问题、MethodUse、版本失效、LangGraph检查和案卷恢复；非真实研究、B1/B2内容、模型或阶段批准", "result": "IN_PROGRESS", "scope": "W27离线接口：同一W16当前修订启动ResearchDossier，Archive中的Dossier快照与ResearchStepRecord为权威，LangGraph官方InMemorySaver只保存可重建导航状态。M01—M12按显式依赖推进而非静态全链启动；M02强制B1/B2各提问题，MethodUse可从M02引入，M07必须汇总至少一个更早方法且不能成为首次选方法。步骤实际产物须引用精确revision；模型执行另需有效W19准入、具体配置、成功OperationReceipt及产物对操作的回指。重提M05只使其下游M07—M12失效，M01—M04/M06保留；M12当期保存有限收口、未知与触发，不等待未来结果。八项回归覆盖并行依赖、B1/B2缺失、方法时序、全周期收口、检查点恢复、下游递归失效、错误revision及未配置模型。真实研究内容、W28/W29产物、持久checkpointer、W31审稿及阶段验收未完成，整包不ACCEPTED。"}]

<a id="w28"></a>
## W28｜顾问任务、判断与增益提交

顺序：29/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W27](#w27)。

前置尚未验收：[W27](#w27)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T06](TECHNICAL_TRACE.md#t06)。

逐项逻辑：T06.L01、T06.L02、T06.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.7](CANONICAL_SYSTEM_SPEC_V5.md#th-8-7)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：同一研究截面、主体处境/行动、竞争解释和任务准入配置。

**交付物**：

- B1研究/写作入口、判断及支持/限制、原作与本刊贡献的区别。
- C04 B1函数共用C02案卷/C03流程和T13调用；只维护本刊顾问任务与成果，不另建顾问Agent服务。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：能指出具体本案理解增益；行动建议只在实际有决策问题时给出，证据变化能收窄判断。
- [ ] 反向：仅设置顶级顾问角色、通用建议、自评分、未经检验动机或强造机会不能成为合格研判。
- [ ] 衔接：共享修订检查拒绝旧基线，研究不足回W27，原件问题回W25，成稿交W31。
- [ ] 与W29共用材料/调用代码但分别指出本案研判贡献及证据，通用自动研究报告不算本刊B1。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：有限解释如实交；改型由W23重核而非由作者直接宣布完成。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W28-ADVISER-AUDIT-20261031-001", "artifact_refs": ["intelligence/advisor.py", "intelligence/contracts.py", "intelligence/research.py", "intelligence/evidence.py", "intelligence/model_admission.py", "intelligence/operations.py", "intelligence/workflow.py", "tests_runtime/test_advisor.py", "audits/pr76-review-remediation-w28-20261031.json"], "validation_refs": ["tests_runtime/test_advisor.py (13 actual passing W28 tests)", "audits/pr76-review-remediation-w28-20261031.json"], "reviewer": "当前执行者实际离线检查B1输入/判断/增益/决策选项/M10、W25关系、模型身份与回执、幂等和上游返工；非真实B1内容、独立审稿、读者或阶段批准", "result": "IN_PROGRESS", "scope": "W28离线接口：B1只能以当前W27案卷的活跃M09、当前W16修订及其实际输入中的当前基线原作/文档、W25 Claim、Evidence和ClaimEvidenceAssessment为依据；评估必须精确覆盖所选Claim并共同覆盖同一Evidence集合，撤权、跨theme/spec、旧version、陈修订和陈快照均拒绝。判断强制列明条件、未知、可改变判断的证据与支持范围；原作已有解释和本刊贡献分开，前后增益不得同文重标。只有声明具体行动决策时才要求真实决策者、比较基础和至少两个含行动理由、代价、受益者、其他行动者反应、调整/退出及可观察效果的选项；无行动决策不得夹带臆造选项。BOUNDED提交READY、CANDIDATE仅提交CANDIDATE、LIMITATION_OR_UNKNOWN提交LIMITED，均不是内容PASS；成果固定B1、facts_verified=false、causal_support=false、content_review_required=true、publication_authorized=false。人工成果拒绝模型身份；模型成果须有当前W19职责/领域准入、绑定全部判断输入的MODEL OperationRequest及成功OperationReceipt，并回指操作。重复调用幂等；Archive后M10失败时只保留未采用的确定性attempt，同一basis精确重试可恢复，否则须按变化后basis另立版本；并发不会产生两个活跃M10，上游重做会以旧M10为parent重建。十三项回归覆盖完整M01—M09/B1/M10、陈旧快照/修订/M09、错类型/错关系/撤权、贡献与增益重标、无据条件/未知/falsifier、两类决策上下文、READY/LIMITED/CANDIDATE、人工/模型身份、成功/缺失回执、失败恢复、并发及上游返工。真实B1研究文字、判断质量、决策真实性、独立Review/W31、持久运行和阶段门未完成，整包不ACCEPTED。"}]

<a id="w29"></a>
## W29｜帝师研究、连续教学与迁移提交

顺序：30/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W27](#w27)。

前置尚未验收：[W27](#w27)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T07](TECHNICAL_TRACE.md#t07)。

逐项逻辑：T07.L01、T07.L02、T07.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1)、[§10.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-2-1)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：共同问题、真实知识来源、必要基础和可采用的B1研究。

**交付物**：

- 从M02介入的知识研究入口和M11连续讲解稿。
- 过程/算例/反例/迁移条件与按需Concept关联。
- C04 B2函数共用C02/C03和模型接口，独立保留知识问题、过程与成稿；不把B1摘要包装为教学。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：普通语言把关键连接讲清，成熟知识与必要回顾可保留；每次迁移核本题条件。
- [ ] 反向：仅复述B1、跳关键连接、堆书名和把收到知识卡记为掌握均不合格。
- [ ] 衔接：与B1可交错研究而非固定末尾润色；认识不足回W27/25、讲解不足只返教学，交W31审实际稿。
- [ ] 可共用W28同题核实际增益，但B2的必要基础/过程/边界/迁移逐项仍有实际段落，知识卡不代讲解。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：补必要研究或连接；不预建课程、读者测评或每篇强制卡数。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W29-TEACHER-AUDIT-20261031-001", "artifact_refs": ["intelligence/teacher.py", "intelligence/advisor.py", "intelligence/contracts.py", "intelligence/research.py", "intelligence/evidence.py", "intelligence/model_admission.py", "intelligence/operations.py", "intelligence/workflow.py", "tests_runtime/test_teacher.py", "audits/pr76-review-remediation-w29-20261031.json"], "validation_refs": ["tests_runtime/test_teacher.py (17 actual passing W29 tests)", "audits/pr76-review-remediation-w29-20261031.json"], "reviewer": "当前执行者实际离线检查B2早期问题、知识依据、连续段落、过程连接、边界/反例、Concept版本、迁移、可选B1、模型身份与M11恢复；非真实教学内容、读者效果、独立审稿或阶段批准", "result": "IN_PROGRESS", "scope": "W29离线接口：B2只能从当前W27案卷的活跃M02 B2问题与M09、当前W16修订及其实际输入中的当前W25 Claim、Evidence和ClaimEvidenceAssessment出发；评估必须精确覆盖所教Claim并共同覆盖同一Evidence集合，撤权、跨theme/spec、旧version、陈快照/修订/M02/M09均拒绝。知识命题须明确类型、条件、范围、未知和反例；正文必须为具体情境、必要基础、至少两段相连中间过程、边界/反例、知识总结和迁移分别提供实际段落。过程步骤绑定真实Evidence且不得超出其PROCESS段落依据；迁移列明共享关系、改变条件、重查事实和不得假定项；专业术语先有日常说明再命名。算例若使用须有假设、步骤、结果、限制；计算还须列值和单位，假设情境须显著标注。MethodUse须在M07经确认并在当前案卷，Concept须为当前且属于精确修订；旧知识若标必要回顾必须有实际RECAP段落，知识卡不能替代讲解。B1可选，但若使用必须是当前M10绑定的精确B1版本，且B2知识贡献不得重标B1。BOUNDED交READY，PARTIAL/LIMITATION交LIMITED且不是内容PASS；成果固定B2、facts_verified=false、causal_support=false、reader_mastery_measured=false、content_review_required=true、publication_authorized=false。人工成果禁止模型身份；模型成果须有当前W19 TEACHER职责/领域准入、绑定全部教学输入的M11 MODEL OperationRequest及成功OperationReceipt，并回指操作。重复调用幂等；Archive后M11失败只保留未采用确定性attempt，同basis精确重试恢复，变化后须另立版本；并发不产生两个活跃M11，上游重做以旧M11为parent重建。十七项回归覆盖完整M01—M09/B2/M11、M02问题、旧快照/修订/M09、必备段落、过程连接与依据绑定、迁移条件、算例单位/假设/假设标识、术语顺序、Method/Concept版本、撤权、可选B1、LIMITED、W19与回执、失败恢复、并发和上游返工。真实B2研究文字、教学连贯性/准确性、读者实际阅读、独立Review/W31、持久运行及阶段门未完成，整包不ACCEPTED。"}]

<a id="w30"></a>
## W30｜条件路径与原判断检验条件

顺序：31/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W28](#w28)、[W29](#w29)。

前置尚未验收：[W28](#w28)、[W29](#w29)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T08](TECHNICAL_TRACE.md#t08)。

逐项逻辑：T08.L01、T08.L02、T08.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：有据起点、条件/传导、未知和共享案卷修订。

**交付物**：

- C与M12任务入口、条件路径、开放问题和事前检验条件。
- 原判断版本及观察窗口/无法区分原因。
- C04条件任务共用C02原判断/Theme和C03运行，不建预测/监测服务；后续观察沿T11现有档案。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：路径差别有实质依据，关键中间连接及反证/时滞可回查；未来结果按新版本另核。
- [ ] 反向：凑概率、只写好坏终点、将推演当事实、抹去旧预测或强迫短稿执行全套C不通过。
- [ ] 衔接：原判断交W33保存，W31核现实起点和表述，真实到期复查进入W39/W40。
- [ ] 同题共用依据仍单验可区分路径/事前条件，未来未发生不阻塞本期，不凑概率/路径数量。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：条件不足回W27/25；确不适用写具体理由，不等未来结果才完成当期准备。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W30-PROSPECTIVE-AUDIT-20261031-001", "artifact_refs": ["intelligence/prospective.py", "intelligence/advisor.py", "intelligence/teacher.py", "intelligence/contracts.py", "intelligence/research.py", "intelligence/evidence.py", "intelligence/model_admission.py", "intelligence/operations.py", "intelligence/workflow.py", "tests_runtime/test_prospective.py", "audits/pr76-review-remediation-w30-20261031.json"], "validation_refs": ["tests_runtime/test_prospective.py (14 actual passing W30 tests)", "audits/pr76-review-remediation-w30-20261031.json"], "reviewer": "当前执行者实际离线检查B1/B2成果接合、原判断原话、路径分支/传导/时滞、可观察检验、开放问题、M12有限收口、模型身份与恢复；非真实未来结果、内容审稿或阶段批准", "result": "IN_PROGRESS", "scope": "W30离线接口：C必须同时绑定当前W27案卷的活跃M10/M11及其精确AdvisorOutput/TeacherOutput和当前W16修订；条件Claim、Evidence及W25评估须精确并集当前B1/B2依据，MethodUse须在当前案卷。原B1核心判断与支持范围、B2知识命题与范围必须逐字保留，不能改写未来‘预测’。MULTI_PATH至少两条实质不同路径，各有不同分支条件和首个区分观察；每路径至少两段行动者/系统、权限资源、决定/传导、前置、结果、最小时滞、不确定性以及Claim/Evidence连接，并写受益、代价、反馈、失败/退出和‘仍是条件非事实’。SINGLE_LIMITED仅一条路径；NOT_APPLICABLE不得造路径；两类均须具体限制。所有模式均须列缺失信息、为何不能区分和下一区分观察，并保存观察窗口、支持/削弱/推翻条件、机制检查与替代解释检查。开放问题只供读者自行思考，不收答案。当期只保存ReviewWindow、W39/W40复查归属和M12 closure/重开触发，不等待未来；成果固定C、facts_verified=false、causal_support=false、forecast_is_fact=false、observed_outcome_claimed=false、reader_answers_collected=false、content_review_required=true、publication_authorized=false，并将W33标为ThesisVersion保存目标但不冒充已保存。人工成果拒绝模型身份；模型成果须有当前W19 EXPLANATION准入、绑定全部条件输入的M12 MODEL OperationRequest及成功OperationReceipt。重复调用幂等；Archive后M12失败只保留未采用确定性attempt，同basis精确重试恢复；并发不产生两个活跃M12，上游重做以旧M12为parent重建。十四项回归覆盖完整B1/B2/C/M12、原话重写、M10/M11/修订失效、路径数量/分支/两段传导、单一路径/不适用、观察窗口、来源精确、W19回执、失败恢复、并发、上游返工及概率/未来结果偷渡。真实路径质量、到期复查、W33实际保存、W31内容审、持久运行和G02未完成，整包不ACCEPTED。"}]

<a id="w31"></a>
## W31｜独立核查、意见闭环与审核决定

顺序：32/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W28](#w28)、[W29](#w29)、[W30](#w30)、[W19](#w19)、[W15](#w15)。

前置尚未验收：[W15](#w15)、[W19](#w19)、[W28](#w28)、[W29](#w29)、[W30](#w30)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T09](TECHNICAL_TRACE.md#t09)、[T01](TECHNICAL_TRACE.md#t01)。

逐项逻辑：T09.L01、T09.L02、T09.L03、T01.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-1)、[§15.2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-2)、[§15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：实际读者稿、原件/方法/计算、真实版本和限制；分开的审稿配置与输入。

**交付物**：

- 独立疑点/回源核查、意见处理、作者回应及实际改稿的Review接口。
- 版本/范围绑定的决定，写作方无权自行修改审核。
- C04写作/独审分任务装载和决定，C01回源、C02版本及C03返工共用；不另设自动投票/PASS平台。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：能识别关键事实/解释/教学错误，也能接受条件充分的合格稿和合理未决。
- [ ] 反向：预泄缺陷答案、作者自签、全拒稿、错审强迫造新结论及旧Review冒充新审不能通过。
- [ ] 衔接：改稿按实际影响回负责模块，W32消费有效Review，能力验证与本篇放行分别保存。
- [ ] 同一正反稿可核事实与教学，但核查者不能读取缺陷答案代查；库评语/分数和作者自评不能直接放行。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：关键未核保持待审/受限，分歧回原件与定义；内容能力另由真实例及新例验。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W31-EDITORIAL-REVIEW-AUDIT-20261031-001", "artifact_refs": ["intelligence/editorial_review.py", "intelligence/adoption.py", "intelligence/prospective.py", "intelligence/advisor.py", "intelligence/teacher.py", "intelligence/contracts.py", "intelligence/research.py", "intelligence/model_admission.py", "intelligence/operations.py", "intelligence/workflow.py", "tests_runtime/test_editorial_review.py", "audits/pr76-review-remediation-w31-20261031.json"], "validation_refs": ["tests_runtime/test_editorial_review.py (17 actual passing W31 tests)", "audits/pr76-review-remediation-w31-20261031.json"], "reviewer": "当前执行者实际离线检查实际Article正文、独立疑点、作者回应、逐项closure、PASS/REVISE/BLOCK、W15版本决定、模型身份与并发；非真实独立审阅、通用审稿能力、用户阅读或阶段批准", "result": "IN_PROGRESS", "scope": "W31离线接口：先固定当前W27案卷的M10/M11/M12、当前W16修订、B1/B2/C精确输出和实际Article读者稿。Article必须是当前保留全文版本，正文非空且引用精确revision、Task、M10/M11/M12及对应B1/B2/C输出；仅案卷或指针不能冒充读者稿。ReviewCase先记录审稿者独立疑点，再允许声明的作者逐项回应并提交可追到初稿的修订Article。疑点的quoted_text必须真实出现在初稿，类型/严重度、Claim/Evidence/MethodUse精确引用；reviewer不得是author或producer，draft-first不得同时声称看过作者自评/旧Review，缺陷答案键始终不得提供。最终固定reviewer逐项closure；PASS不得保留open/unverified，REVISE至少一项open/unverified，BLOCK至少一项critical未解决；合理accepted dispute可保留而不强迫新结论。最终Review绑定实际修订Article、Task与scope并写ReviewCoverage，再由W15以精确subject/review/scope形成决定：PASS→READY，REVISE→RETURN，BLOCK→BLOCKED；同一Task下不同Article使用独立W15 step槽，禁止后一篇覆盖前一篇当前采用。作者不能签审核，模型审稿须W19 REVIEW独立准入、与writer configuration分离、W31 OperationRequest及成功回执。上游W27修订、B1/B2/C最新版本、Article或case版本变化均使旧Review失效；同一final决定并发幂等且后续Article不能继承旧Review。成果固定author_self_approved=false、model_self_passed=false、publication_authorized=false、review_capability_certified=false。十七项回归覆盖正向PASS/W15、自签、真实正文/引文、问题来源、作者回应顺序、PASS未决拒绝、合理争议、REVISE/BLOCK、critical block、新Article、上游修订、exposure、模型W19/回执、并发、库评分/预定PASS偷渡及同Task多Article采用隔离。真实审稿文字、盲测/新例、跨领域漏检/误拒、完整样刊、W32消费及G02仍未完成，整包不ACCEPTED。"}]

<a id="w32"></a>
## W32｜连续文章、卷首与审后变更承接

顺序：33/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W31](#w31)、[W23](#w23)、[W26](#w26)。

前置尚未验收：[W23](#w23)、[W26](#w26)、[W31](#w31)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T10](TECHNICAL_TRACE.md#t10)、[T03](TECHNICAL_TRACE.md#t03)。

逐项逻辑：T10.L01、T10.L02、T10.L03、T03.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.5](CANONICAL_SYSTEM_SPEC_V5.md#th-13-5)、[§13.6](CANONICAL_SYSTEM_SPEC_V5.md#th-13-6)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：有效稿件/Review、当期取舍与重要更新、实际使用的可读格式。

**交付物**：

- Article/Edition源与实际读者稿、标题/图表/卷首/目录及来源索引。
- 审后差异、纯呈现承接或语义返审记录；当期文件冻结指针。
- C05编码优先Jinja，固定模板由最高说明派生；C04形成连续文章/卷首，模板只呈现已审数据，年度复用同一层。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：正文、标题、卷首和结尾强度一致，整刊互补/重要更新有据，实际使用文档可读。
- [ ] 反向：单字改意、漏限定、卷首新因果、脚注/单位丢失须返核；纯版式不强制全篇重研。
- [ ] 衔接：语义新增回W27/W31，纯呈现核实际文件后保留原Review承接；正式多格式渲染到W49。
- [ ] 实际稿件HTML转义、外部文字不能执行为模板；新命题返审，W49后续PDF只渲染该定稿，不从研究器导出第二正文。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：先修负责层的具体缺陷，不以文件生成当出版/交付；未验格式不标通过。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W32-PRESENTATION-AUDIT-20261031-001", "artifact_refs": ["intelligence/presentation.py", "intelligence/editorial_review.py", "intelligence/editorial.py", "intelligence/materials.py", "intelligence/adoption.py", "intelligence/contracts.py", "tests_runtime/test_presentation.py", "audits/pr76-review-remediation-w32-20261031.json", "pyproject.toml", "uv.lock"], "validation_refs": ["tests_runtime/test_presentation.py (10 actual passing W32 tests)", "audits/pr76-review-remediation-w32-20261031.json"], "reviewer": "当前执行者实际离线检查Edition组合、PASS Review/W15版本、W23 placement、W26更新、Jinja转义、私有文件、并发和错误路径；非真实整刊内容、用户阅读、视觉/PDF或阶段批准", "result": "IN_PROGRESS", "scope": "W32离线接口：Edition只接收当前W23 EditionPlacementProposal与当前W26 ImportantUpdateCheck；需研究/审稿/改型/更正的更新不能被版面层吞掉，文章Review须晚于该检查。封面与专题各绑定当前Article、PASS Review及当前W15 READY采用；Article必须保留全文且H1与被审版本一致，Review精确覆盖Article及用途，W15 subject/review/scope一致。Feature必须匹配W23 placement和slot；一个Edition不能把同一Article重复冒充多篇。模板只使用Jinja StrictUndefined/autoescape，不加载外部模板或资源；标题、正文、目录和来源标签均转义，来源URL仅允许HTTPS，正文HTML片段与脚本不执行。正文在Archive中保留为EditionRecord，实际读者文件为版本绑定HTML，按O_NOFOLLOW/O_EXCL创建0600私有文件并记录hash/bytes；重试、并发和陈旧版本不覆盖当前Edition。Edition固定content_review_required=true、full_edition_review_required=true、publication_authorized=false、delivery_authorized=false，生成文件不等于内容通过、正式PDF、出版或送达。十项回归覆盖PASS/W15组合、标题篡改、真实原文、W23 placement/slot、W26返回、HTTPS、新稿旧审、仓库内/外来文件、并发幂等、排序重复和HTML转义。真实整刊阅读、标题/图表/卷首审稿、字体分页、视觉呈现、PDF/W49、用户阅读及G01未完成，整包不ACCEPTED。"}, {"record_id": "W32-W36-CURRENT-S8-REVALIDATION-20261031-001", "artifact_refs": ["intelligence/editorial.py", "intelligence/presentation.py", "tests_runtime/test_presentation.py", "tests_runtime/test_route_integration.py", "audits/w36-route-integration-20261031.json"], "validation_refs": ["tests_runtime/test_presentation.py (11 actual passing W32 tests)", "tests_runtime/test_route_integration.py (3 actual passing W36 route tests)", "audits/w36-route-integration-20261031.json"], "reviewer": "当前执行者实际离线检查W36反向用例及W32当前依据重核；非真实跨模块内容、用户阅读或阶段批准", "result": "IN_PROGRESS", "scope": "W36接续修复W32在生成阅读文件前只核Edition方案自身版本、未重核其所依赖当前W23 S8决定/研究准入/S8包的问题。新增load_current_edition_proposal：先确认方案当前，再逐placement用W23同一依赖校验核当前TopicDecision、ResearchAdmission、S8包、候选、覆盖、问题、来源、权利和Evidence；任一变为旧版即退回相应编辑/取证责任，不生成HTML。W32夹具改为真实经过W23控制器的候选/覆盖/S8/准入/方案链，新增后出Evidence使旧S8失效的反例；十一项W32测试通过。真实整刊、用户阅读和G02仍未验，W32整包不ACCEPTED。"}]

<a id="w33"></a>
## W33｜原文档案、双模式查询与知识复用

顺序：34/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W13](#w13)、[W16](#w16)、[W32](#w32)。

前置尚未验收：[W13](#w13)、[W16](#w16)、[W32](#w32)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T11](TECHNICAL_TRACE.md#t11)。

逐项逻辑：T11.L01、T11.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：原稿/判断/知识/背景的实际版本、三时间、权限和当前限制。

**交付物**：

- 当前查询、KNOWN_TO_SYSTEM_AS_OF及PUBLICLY_AVAILABLE_AS_OF接口。
- 完整原稿取回、按需知识/背景/机构变化/TransmissionLink及可重建索引。
- C02同一SQLAlchemy/版本文件接口实现历史/当前查询；C03官方检查点另作执行恢复，不拿图状态充当新闻档案。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：两种历史语义给出各自正确结果，原话与后来说明分开；当前采用回权威版本核本题条件。
- [ ] 反向：后来公开/后来补录不得污染旧截面；摘要/缓存/命中不能代替原文或绕过当前限制。
- [ ] 衔接：同一档案支撑W39/W40/W52；机构前后变化和跨域每一环有实际材料，不独立建雷达产品。
- [ ] C02业务/原件版本与图检查点职责可查；同一权威原稿支撑跨周和年报，不复制第二知识库。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：历史取不回标范围不足，不用现稿补造；索引可重建但不是第二事实源。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W33-HISTORY-AUDIT-20261031-001", "artifact_refs": ["intelligence/history.py", "intelligence/archive.py", "intelligence/contracts.py", "intelligence/adoption.py", "tests_runtime/test_history.py", "audits/pr76-review-remediation-w33-20261031.json"], "validation_refs": ["tests_runtime/test_history.py (11 actual passing W33 tests)", "audits/pr76-review-remediation-w33-20261031.json"], "reviewer": "当前执行者实际离线检查双as-of、发布时间与recorded_at、正文权限、索引重建和知识复用；非真实跨周截面、完整纠错链、用户历史阅读或阶段批准", "result": "IN_PROGRESS", "scope": "W33离线接口：同一共享Archive提供CURRENT、KNOWN_TO_SYSTEM_AS_OF和PUBLICLY_AVAILABLE_AS_OF。KNOWN只选published_by(t)且真实DB recorded_at≤t的最新版本；PUBLIC可选published_by(t)但recorded_at>t的版本，并固定system_unknown_at_as_of=true，同时另报known_to_system_version_id，两者不混成一段依据。事件时间不代替发布时间；未知、仅部分区间或同日日期精度不能证明精确公开时点，日期型发布时间需原始时区且不推午夜。查询返回所选版本、当时已知版本、当前版本、后续版本列表和recorded/published元数据；正文仅在include_body且当前用途与STORAGE/撤权均通过时从原私有文件读取，INDEX、撤权、缺失或二进制分别如实返回，不拿导航/摘要替代原文。当前查询可核可选W15决定在查询时是否仍current及覆盖scope，但查询本身固定current_use_authorized=false，不授予采用。导航索引可从Archive重建，重建不产生第二事实源。Concept/Background/MethodUse/TransmissionLink共用同一版本查询；KnowledgeReuse追加记录精确旧来源、当前来源、目标Article、原/现条件差异、SUPPORTED/NARROWED/CONTRADICTED/UNRESOLVED、证据及does_not_prove，幂等且不记录读者掌握/学习状态。十一项回归覆盖KNOWN/PUBLIC隔离、后录修正、事件早于发布、日期午夜、未知发布、当前最新、撤权正文、索引重建、知识复用/当前版分离和TransmissionLink历史。真实两个不同周截面、自然更正传播、W39/W40/W52实际复用、长期宿主/备份恢复和阶段门未完成，整包不ACCEPTED。"}]

<a id="w34"></a>
## W34｜更正影响、限制采用与有限恢复

顺序：35/59；阶段：2；类型：代码与接口工作包。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W33](#w33)、[W25](#w25)、[W31](#w31)、[W15](#w15)。

前置尚未验收：[W15](#w15)、[W25](#w25)、[W31](#w31)、[W33](#w33)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T11](TECHNICAL_TRACE.md#t11)、[T01](TECHNICAL_TRACE.md#t01)。

逐项逻辑：T11.L03、T01.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§16.6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-2)、[§16.6.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-3)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：真实更正或明示测试副本、直接/传递用途及其他仍有效支持。

**交付物**：

- 先限制已知关键用途、依赖追查、漏依赖/误限制与补核记录。
- 维持/缩小/撤回/未决及按范围恢复的当前指向。
- C02同一显式依赖/剩余支持/版本限制与事务接口，C03只负责有条件返工，不另造纠错存储或全库重跑平台。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：受影响采用先失效再复核；有效剩余支持和无关稿件能保留，历史原稿仍可回放。
- [ ] 反向：仅改源数字却旧批准可用、一改全撤/全过、漏依赖和缓存绕过限制均须被检出。
- [ ] 衔接：W15/W31/W32/W33采用时核限制；恢复绑定真实补证/Review，W40验完整链。
- [ ] 更正副本可与W16/W33共用真实档案，逐项验遗漏依赖、误限制和恢复范围，不以事务成功代语义判断。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：关系不全执行限定查找并报告未覆盖，限制相关用途而非伪称完整影响图。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W34-CORRECTION-AUDIT-20261031-001", "artifact_refs": ["intelligence/correction.py", "intelligence/adoption.py", "intelligence/history.py", "intelligence/contracts.py", "tests_runtime/test_correction.py", "audits/pr76-review-remediation-w34-20261031.json"], "validation_refs": ["tests_runtime/test_correction.py (8 actual passing W34 tests)", "audits/pr76-review-remediation-w34-20261031.json"], "reviewer": "当前执行者实际离线检查显式反向依赖、先限制、W15/W33当前使用、无关分支、历史正文和Review绑定恢复；非真实自然更正、内容影响判断、完整依赖图或阶段批准", "result": "IN_PROGRESS", "scope": "W34离线接口：更正登记须指旧版及同对象后续修正版（撤回/权利变化除外），沿Archive全部显式反向引用逐层追到依赖版本，记录dependent/dependency/reference use/locator/depth，不按同Theme或文本相似推断。所有显式依赖版本先获得共享UseRestriction并记录受影响W15决定；旧READY采用及W33当前正文在活动限制下不可继续使用，无关分支不被限制，历史as-of正文仍可取回。每项显式依赖必须逐项分类MAINTAINED/NARROWED/RETRACTED/UNRESOLVED；维持/缩小须列其余支持，缩小须列保留scope，撤回/未决不得保留批准scope，并另报未检索范围。恢复必须引用目标版本和精确更正案卷的新Review，恢复scope不得超过原限制；允许的新W15决定必须subject/Review/scope匹配且不得复用被更正约束的旧决定。旧决定不会因恢复自动复活，W33无决定的历史正文/post-recovery current scope、未恢复依赖与无关稿件分别处理。更正案卷、限制和恢复均为同一Archive追加版本，不另造纠错库。八项回归覆盖直接/传递限制、无关采用保留、全依赖评估、旧Review拒绝、新Review/新决定按范围恢复、当前与历史正文隔离、错误修正身份、图外采用及retracted原地恢复拒绝。真实自然更正、语义剩余支持评估、W40完整链、长期宿主恢复及G02未完成，整包不ACCEPTED。"}]

<a id="w35"></a>
## W35｜必要时的原文任务视图与分段装载

顺序：36/59；阶段：2；类型：条件能力。

进度：**有据不适用**；关联：CURRENT_BINDING；前置：[W14](#w14)、[W17](#w17)。

前置尚未验收：[W14](#w14)、[W17](#w17)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T01](TECHNICAL_TRACE.md#t01)、[T13](TECHNICAL_TRACE.md#t13)、[R07](TECHNICAL_TRACE.md#r07)。

逐项逻辑：T01.L01、T13.L03、R07.F03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-1)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：来自RunLog或当前任务记录的实际受阻证据、任务所需原文/材料依赖及配置限制；W27失败尝试可作为触发，但不要求W27整包验收。

**交付物**：

- 确需时的早期解阻产物：当前原文单元、材料依赖清单/哈希、实际提供范围及返回原任务的接续点。
- 后续分段、恢复、W33真实中间产物、W15采用与W36/R07全稿连接的集成产物。
- 无瓶颈时的NOT_APPLICABLE依据和已验证人工定位办法。
- 有实际瓶颈才实现原文提取/分段，执行重接直接复用C03官方checkpointer和C02中间产物，不再引入Deep Agents/自动记忆层。

**条件项**：仅第二阶段出现经RunLog记录的真实上下文/装载受阻时启用；无受阻依据可有据不适用，不能跳过输入完整性，也不得因W27未完成本身自动启动。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：只有真实受阻记录触发早期分支；字符数/token估算不能单独证明过载，无触发依据时不建设W35。
- [ ] 反向：W27尚未完成时可以按受阻记录进入局部解阻并返回同一任务，但不产生READY/PASS或W35整包通过。
- [ ] 衔接：保留关键否定/例外/表注及跨段依赖；只传摘要、缺必需依赖、过期任务视图不能通过。
- [ ] 后续从W33取真实中间产物，用W15核采用，W36核R07全稿连接与中断重接；官方检查点/自动摘要不替必需原文。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：先人工定位或补原文/拆分，仍不足停止受影响任务；返回原任务后若仍有受阻，保留缺口而不以局部修复冒充完成。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W35-APPLICABILITY-20261031-001", "artifact_refs": ["audits/w35-applicability-20261031.json", "audits/w14-preparation-20261024.json", "audits/pr76-review-remediation-w27-20261031.json"], "validation_refs": ["audits/w35-applicability-20261031.json#manual_locator", "audits/w35-applicability-20261031.json#trigger_review", "tests/test_work_plan.py (conditional NOT_APPLICABLE and blocked-repair branch regressions)"], "reviewer": "当前执行者Codex实际检索现有任务/审计记录、核对实际提供状态并复跑人工定位/重接路径；非用户、独立L5或阶段批准", "result": "NOT_APPLICABLE", "scope": "本轮没有真实RunLog或任务记录显示上下文上限、截断、关键依赖未提供或输出不全，故不建设任务视图/分段器；已核§24.6.1唯一锚点、W35唯一机器条目及从当前规范/任务版本/依赖返回原任务的人工路径。源码探测字节截断、1.07 MB规范准备包和W27离线测试均不单独构成过载。W14/W17及G01—G04未过，未来出现具名真实受阻证据时须重开局部解阻；本记录不产生READY/PASS、W35能力通过、阶段门或生产能力。"}]

<a id="w36"></a>
## W36｜最小深度主题闭环与中断重接

顺序：37/59；阶段：2；类型：路线集成验收。

进度：**进行中**；关联：CURRENT_BINDING；前置：[W22](#w22)、[W32](#w32)、[W33](#w33)、[W18](#w18)。

前置尚未验收：[W18](#w18)、[W22](#w22)、[W32](#w32)、[W33](#w33)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R01](TECHNICAL_TRACE.md#r01)、[R07](TECHNICAL_TRACE.md#r07)、[T01](TECHNICAL_TRACE.md#t01)、[T09](TECHNICAL_TRACE.md#t09)、[T11](TECHNICAL_TRACE.md#t11)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：R01.F01、R01.F02、R01.F03、R01.F04、R01.F05、R07.F01、R07.F02、R07.F03、R07.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：冻结合法真实案例、当前实现、配置、有效原文/材料及实际中间产物。

**交付物**：

- R01最小可重跑内部闭环和R07规则变化/分段/中断重接的集成证据。
- 实际跨模块输入/输出/决定链与质量/主要投入。
- 复用C01—C04及实际内容呈现层在同一thread/版本链跑真实闭环；LangGraph官方检查点承担执行恢复。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：从独立发现到真实读者稿可回放；人工职责明确；恢复只重做实际失效部分。
- [ ] 反向：越步、自报通过、缺依赖、过期关联/视图、只用聊天摘要恢复均被拦在相应用途。
- [ ] 衔接：理论→T/R→工作包→代码/真实产物/检查可来回定位；W35有据不适用时仍验人工装载和重接。
- [ ] 实际中断后从最近有效节点继续，外部调用身份/累计投入不丢；强制历史replay引起的重执行必须可辨并受控。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：定位具体交接/内容缺陷后返责任包，不因维护测试通过就认研究能力合格。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：[{"record_id": "W36-ROUTE-INTEGRATION-20261031-001", "artifact_refs": ["intelligence/editorial.py", "intelligence/presentation.py", "tests_runtime/test_presentation.py", "tests_runtime/test_route_integration.py", "audits/w36-route-integration-20261031.json"], "validation_refs": ["tests_runtime/test_route_integration.py (3 actual passing W36 route tests)", "tests_runtime/test_presentation.py (11 actual passing W32 tests)", "audits/w36-route-integration-20261031.json"], "reviewer": "当前执行者实际搭建并回归同一Archive的R01/R07离线链；非真实冻结案例、独立内容审稿、用户阅读、持久生产恢复或阶段批准", "result": "IN_PROGRESS", "scope": "W36离线路线集成：在同一Archive以自有合成合法材料串起候选索引、独立参照/覆盖审计、S8包、COVER决定、研究准入、Edition方案、W27全集、B1/B2/C、W31 Review/W15、W32 HTML及W33 CURRENT版本回取；W32在成刊前重新核当前W23决定、准入和S8依赖。控制器丢失后从Archive dossier重建十二步检查点；新Dossier在M01后中断，恢复后只继续M02且M01记录未重建。聊天摘要字符串不能冒充快照。外部受控试用经W18后保留OperationRequest/Receipt与$0.03累计费用，控制器重建后重复请求在Adapter前因既有储备被拒。另验后出Evidence使W23 S8系旧时W32不生成页面。真实冻结案例、跨模块内容质量、独立L5、读者阅读、实际中断/C03持久后端、W37以后路线和G01—G04未完成；W35仍N/A，故整包IN_PROGRESS，不ACCEPTED。"}]

<a id="w37"></a>
## W37｜精选、首次事实、进展及更正分支

顺序：38/59；阶段：2；类型：路线集成验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W23](#w23)、[W26](#w26)、[W31](#w31)、[W32](#w32)、[W34](#w34)。

前置尚未验收：[W23](#w23)、[W26](#w26)、[W31](#w31)、[W32](#w32)、[W34](#w34)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R03](TECHNICAL_TRACE.md#r03)、[T03](TECHNICAL_TRACE.md#t03)、[T04](TECHNICAL_TRACE.md#t04)、[T09](TECHNICAL_TRACE.md#t09)、[T10](TECHNICAL_TRACE.md#t10)。

逐项逻辑：R03.F01、R03.F02、R03.F03、R03.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：真实对应稿型及实际旧稿/无旧稿依据、许可、适用责任和整刊。

**交付物**：

- R03四种分支路由、对应产物/审核与整刊责任的集成记录。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：各型完成实际适用职责；更正定位旧原句，新事实明确无旧文，必要背景和限制充分。
- [ ] 反向：短稿强套全部B1/B2/C、深稿仅改标签、全刊短讯化或借无旧稿伪造前刊均失败。
- [ ] 衔接：CORRECTION连W34/W40，研究改型回W23；有效短稿可入刊，不误等不适用工序。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按稿型/价值重新选择，未完成研究继续保留而非因路由成功标为完成。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w38"></a>
## W38｜定向补证、解释变化与回S8

顺序：39/59；阶段：2；类型：路线集成验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W25](#w25)、[W27](#w27)、[W23](#w23)、[W31](#w31)。

前置尚未验收：[W23](#w23)、[W25](#w25)、[W27](#w27)、[W31](#w31)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R04](TECHNICAL_TRACE.md#r04)、[T03](TECHNICAL_TRACE.md#t03)、[T04](TECHNICAL_TRACE.md#t04)、[T05](TECHNICAL_TRACE.md#t05)。

逐项逻辑：R04.F01、R04.F02、R04.F03、R04.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：实际缺环/反证、可区分新材料、原解释与原选择。

**交付物**：

- R04补证请求→真实取得→支持变化→相关交接复核→必要S8复选的完整链。
- 定向缺口仍走C01/C02/C03/C04同一入口，GPT Researcher只在受控真实增益可验时条件适配；不增第三条选题/报告链。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：新增材料可维持、削弱或无法区分解释，分别有实际依据和主要投入。
- [ ] 反向：同源堆叠算新验证、固定材料评测禁止真实补证、无新依据无限重试均失败。
- [ ] 衔接：问题/对象/价值/类型实变确实回T03，未变只重核相关推理；能有据继续、有限交付或暂停。
- [ ] 采用/不采用条件补证器均有依据，真实回S8与支持修订保留，不用更多搜索结果自动提高结论强度。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按缺陷回W25/W27/W23，停止无新增价值动作，不自动全篇重写。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w39"></a>
## W39｜真实跨周接续与长期专题入刊

顺序：40/59；阶段：2；类型：路线集成验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W33](#w33)、[W27](#w27)、[W23](#w23)、[W36](#w36)。

前置尚未验收：[W23](#w23)、[W27](#w27)、[W33](#w33)、[W36](#w36)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R02](TECHNICAL_TRACE.md#r02)、[T03](TECHNICAL_TRACE.md#t03)、[T05](TECHNICAL_TRACE.md#t05)、[T11](TECHNICAL_TRACE.md#t11)。

逐项逻辑：R02.F01、R02.F02、R02.F03、R02.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§16.5](CANONICAL_SYSTEM_SPEC_V5.md#th-16-5)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：同一主题至少两个真实不同周截面、旧原话/缺口及新公开材料。

**交付物**：

- R02跨周演变、背景/知识版本、暂停/重开与新的研究结果。
- CURRENT_WEEK或LONG_TERM_FEATURE逐项刊登依据及重新审核。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：Theme独立延续、旧刊原话可找回，新材料/复查确实改变或检验原判断。
- [ ] 反向：模拟两周、现稿回填历史、COVER占本期名额、沉没投入强发及未熟长期题自动短稿均不通过。
- [ ] 衔接：历史查询走W33，补证走W38，更正走W40，成熟后T03重核本期价值而非自动刊登。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：未到真实第二周保持待验；材料不足暂停并保留下一触发，不伪造自然时间。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w40"></a>
## W40｜更正、当前采用与历史回放集成

顺序：41/59；阶段：2；类型：路线集成验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W34](#w34)、[W39](#w39)、[W31](#w31)、[W32](#w32)。

前置尚未验收：[W31](#w31)、[W32](#w32)、[W34](#w34)、[W39](#w39)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R05](TECHNICAL_TRACE.md#r05)、[T11](TECHNICAL_TRACE.md#t11)、[T09](TECHNICAL_TRACE.md#t09)、[T10](TECHNICAL_TRACE.md#t10)。

逐项逻辑：R05.F01、R05.F02、R05.F03、R05.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§16.6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-2)、[§16.6.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-3)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：真实跨周档案、明示更正测试副本、具体依赖及有其他支持/无关稿对照。

**交付物**：

- R05完整影响链、采用前拒绝/恢复、历史原话与后来更正分离的证据。
- 找到/遗漏/误限制的实际结果及覆盖限制。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：先限制关键用途，再补核并按范围恢复；当前复用和两类as-of查询各得正确结果。
- [ ] 反向：旧缓存或旧PASS绕过限制、全恢复、漏依赖/误限及测试更正冒充自然更正均失败。
- [ ] 衔接：覆盖Evidence→Claim→B1/B2/C→Review→Article/Edition及实际查询用途；相关修改回对应内容审核。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：补依赖和真实核查；未覆盖范围保持限制，不以登记条目数当链路通过。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w41"></a>
## W41｜六份真实跨领域案例与投入联合验收

顺序：42/59；阶段：2；类型：真实案例与能力验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W36](#w36)、[W37](#w37)、[W38](#w38)、[W39](#w39)、[W40](#w40)。

前置尚未验收：[W36](#w36)、[W37](#w37)、[W38](#w38)、[W39](#w39)、[W40](#w40)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R01](TECHNICAL_TRACE.md#r01)、[R02](TECHNICAL_TRACE.md#r02)、[R03](TECHNICAL_TRACE.md#r03)、[R04](TECHNICAL_TRACE.md#r04)、[R05](TECHNICAL_TRACE.md#r05)、[R07](TECHNICAL_TRACE.md#r07)、[T09](TECHNICAL_TRACE.md#t09)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：本项为综合验收，按所列T/R及本卡检查。。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§16.5](CANONICAL_SYSTEM_SPEC_V5.md#th-16-5)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：至少六份真实、合法、跨领域完整深度案例，第一阶段合格案例可计入。

**交付物**：

- 逐例A/B1/B2/C适用产物、独立Review、权利/知识关系、配置/失败/返工与主要投入。
- 六案例覆盖清单及第二阶段全部实际缺口；不预填自然周和案例通过。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：包含非金融、非创业、非中美重大题；至少一例机构前后变化、一例逐环跨域传导，均有真实依据。
- [ ] 反向：模拟凑六例、只数来源/角色、只报最后成功费用、字符数冒充Token及跨币种直接相加均不通过。
- [ ] 衔接：与同题真实基线对照具体理解/教学增益；成本未知如实列缺口，阶段门按§19.2/19.7核实际范围。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：缺哪例/哪责任就补对应真实研究；不为数量挑无价值新闻，不以代码绿灯越过G02。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="g02"></a>
## G02｜第二阶段门：研究闭环、跨周与六例

顺序：43/59；阶段：2；类型：阶段门。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W13](#w13)、[W14](#w14)、[W15](#w15)、[W16](#w16)、[W17](#w17)、[W18](#w18)、[W19](#w19)、[W20](#w20)、[W21](#w21)、[W22](#w22)、[W23](#w23)、[W24](#w24)、[W25](#w25)、[W26](#w26)、[W27](#w27)、[W28](#w28)、[W29](#w29)、[W30](#w30)、[W31](#w31)、[W32](#w32)、[W33](#w33)、[W34](#w34)、[W35](#w35)、[W36](#w36)、[W37](#w37)、[W38](#w38)、[W39](#w39)、[W40](#w40)、[W41](#w41)。

前置尚未验收：[W13](#w13)、[W14](#w14)、[W15](#w15)、[W16](#w16)、[W17](#w17)、[W18](#w18)、[W19](#w19)、[W20](#w20)、[W21](#w21)、[W22](#w22)、[W23](#w23)、[W24](#w24)、[W25](#w25)、[W26](#w26)、[W27](#w27)、[W28](#w28)、[W29](#w29)、[W30](#w30)、[W31](#w31)、[W32](#w32)、[W33](#w33)、[W34](#w34)、[W36](#w36)、[W37](#w37)、[W38](#w38)、[W39](#w39)、[W40](#w40)、[W41](#w41)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R01](TECHNICAL_TRACE.md#r01)、[R02](TECHNICAL_TRACE.md#r02)、[R03](TECHNICAL_TRACE.md#r03)、[R04](TECHNICAL_TRACE.md#r04)、[R05](TECHNICAL_TRACE.md#r05)、[R07](TECHNICAL_TRACE.md#r07)、[T01](TECHNICAL_TRACE.md#t01)、[T02](TECHNICAL_TRACE.md#t02)、[T03](TECHNICAL_TRACE.md#t03)、[T04](TECHNICAL_TRACE.md#t04)、[T05](TECHNICAL_TRACE.md#t05)、[T06](TECHNICAL_TRACE.md#t06)、[T07](TECHNICAL_TRACE.md#t07)、[T08](TECHNICAL_TRACE.md#t08)、[T09](TECHNICAL_TRACE.md#t09)、[T10](TECHNICAL_TRACE.md#t10)、[T11](TECHNICAL_TRACE.md#t11)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：本项为综合验收，按所列T/R及本卡检查。。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-2-2)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§5](CANONICAL_SYSTEM_SPEC_V5.md#th-5)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-2)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§16.5](CANONICAL_SYSTEM_SPEC_V5.md#th-16-5)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：W13—W41实际实现和研究证据；W35仅在确有上下文需要时适用。

**交付物**：

- 最小可重跑L1—L6、配置有限准入、真实跨周/查询/复用/纠错与六案例证据。
- 实际能力范围、主要投入/失败/缺项和进入第三阶段的决定。

**验收清单**（另核Q01—Q07）：

- [ ] 内容与证据：至少两个真实不同周截面；两类as-of、背景/知识复用、来源/许可/译文变化及更正依赖按范围恢复均有证据。
- [ ] 范围与质量：至少六份真实合法跨领域深度案例，含原定领域/地区覆盖、机构变化与逐环跨域案例，逐例独立审稿。
- [ ] 禁止的捷径：模拟不能凑真实案例/周截面；控制器检查、内容质量、模型能力及成本证据分别报告，条件任务有据不适用。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：保留实际证据与未过项，退回相应工作包修订；不能以后阶段工具或维护检查替代本阶段质量门。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w42"></a>
## W42｜按题接入必要专业原始资料

顺序：44/59；阶段：3；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[G02](#g02)。

前置尚未验收：[G02](#g02)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T04](TECHNICAL_TRACE.md#t04)、[T05](TECHNICAL_TRACE.md#t05)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：T04.L01、T04.L02、T05.L02、T13.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：第二阶段真实案卷暴露的专业缺口、对应原始数据/披露/合同/政策/科技医学等材料。

**交付物**：

- 只针对实际需要的专业适配与资料版本/权限、单位/口径/数据期。
- 对旧解释遗漏条件或例外的真实核对及修订。
- 专业资料接C01/C02同一链：复杂报告按需Docling、SEC按需EdgarTools；广域OpenBB/RSSHub只有真实需求才加。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：资料确实补到某个决定性条件，来源、单位、方法、时点与使用权可回查。
- [ ] 反向：预印本当临床效果、机构措辞当权限改变、融资当收入、口径不兼容直接比较不得通过。
- [ ] 衔接：缺口经T05进入实际B1/B2/Review，仍用共享证据/采用接口，不另起专业事实库。
- [ ] 少量专用来源足够时不接整个平台；核实际分发物/模型/数据者许可、可得时点、专业单位和真实增益，失败可退回原接口。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：无材料或无权使用则收窄/待研，候选工具不因成熟或免费就直接成为内容结论。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w43"></a>
## W43｜专业深度专题与方法实际增益

顺序：45/59；阶段：3；类型：真实案例与能力验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W42](#w42)。

前置尚未验收：[W42](#w42)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T05](TECHNICAL_TRACE.md#t05)、[T06](TECHNICAL_TRACE.md#t06)、[T07](TECHNICAL_TRACE.md#t07)、[T08](TECHNICAL_TRACE.md#t08)、[T09](TECHNICAL_TRACE.md#t09)。

逐项逻辑：T05.L02、T06.L02、T07.L02、T08.L02、T09.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.8](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§10.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-1)、[§10.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-10-2-1)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-2)、[§15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：专业材料、必要方法、竞争解释及可比的既有案卷/基线。

**交付物**：

- 真实专业深度专题、前后判断/教学差异与独立核验。
- 专业条件/反例/传导使稿件具体改善的段落及投入。
- C04复用同一题任务/方法/证据接口验证专业实际增益，不按领域另建研究引擎；原典条件进入真实调查。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：解释与教学比普通摘要多出的必要过程可查；前提失配会撤销或修正方法。
- [ ] 反向：加术语/资料量却无实际作用、强求原创、忽略其他世界领域或把相关当收益传导均不合格。
- [ ] 衔接：仍走T01/T04/T09/T10当前版本链，重要新材料重新检查受影响内容及整刊。
- [ ] 同一真实题比较专业资料加入前后解释/教学与主要投入，不能用新增术语/角色/文长代增益。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：回真实材料/方法/讲解定位问题，必要时简化工具，不以新角色掩盖内容浅。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w44"></a>
## W44｜必要时的专业分工比较

顺序：46/59；阶段：3；类型：条件能力。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W43](#w43)。

前置尚未验收：[W43](#w43)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T09](TECHNICAL_TRACE.md#t09)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：T09.L01、T09.L02、T09.L03、T13.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-1)、[§15.2.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-2)、[§15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：明确的专业审核瓶颈、同一固定真实样本、原有独立审核基线与实际配置。

**交付物**：

- 确需时专业分角色/多Agent对照；漏检/误拒/争议/中文质量、时间与用量/费用。
- 无瓶颈或无增益时的简化/不适用依据，保留独立核查职责。
- 先复用C04单一独立审核；真实瓶颈才在同一接口条件比较专业分工，不默认Deep Agents/多Agent或第二编排。

**条件项**：只有真实专业瓶颈需要时比较；用户此轮仅授权工作清单，未授权现在启动多Agent。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：实际提升关键识错与正确放行能力才保留复杂编排；人工帮助和条件差异公开记。
- [ ] 反向：角色数/多数投票/分数上升不能代替回源；全拒稿、泄露缺陷答案、隐去失败轮次均不通过。
- [ ] 衔接：专业意见仍由T09按原件收口，写作模型无权自签PASS；不新增一组永久生产线。
- [ ] 代码/材料/参照可共用，比较仍分开记录漏检、误拒、耗时/费用；无增益简化或有据不适用，不删独审责任。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：无明确增益就用更简单的独立审稿，未验职责保持受限。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w45"></a>
## W45｜新例复核与有限能力范围更新

顺序：47/59；阶段：3；类型：真实案例与能力验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W43](#w43)。

前置尚未验收：[W43](#w43)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T09](TECHNICAL_TRACE.md#t09)、[T13](TECHNICAL_TRACE.md#t13)、[T01](TECHNICAL_TRACE.md#t01)。

逐项逻辑：T09.L01、T09.L03、T13.L01、T01.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-1)、[§15.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2-3)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：专业专题与另留未调试新例、实际配置和必要的新任务范围。

**交付物**：

- 新例的漏检/误拒/未核、配置变化复验、有限准入与简化决定。
- 本阶段质量/主要投入/返工及仍未覆盖的范围。
- 新例复核沿C02/C04现有记录和实际模型接口，promptfoo需要时才条件接固定正反回归，不再造评测平台。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：新条件能说明哪些知识可迁移、哪些须重查；范围更新有真实证据且绑定实际配置。
- [ ] 反向：把调试例最好一次或一次稿件PASS当跨领域通用能力、把旧模型记录套到新配置均失败。
- [ ] 衔接：W44如被触发必须先完成并核证；否则有据不适用；G03只放行本次实际证明范围。
- [ ] 另留新例核迁移/失败范围，共同参照可复用但不泄露答案；第三方CLI发行与评分范围明确，分数不直接准入。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：新例失败定位相应能力并限制用途，退内容/研究修订，不强求全领域能力声明。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="g03"></a>
## G03｜第三阶段门：专业增益与有限能力

顺序：48/59；阶段：3；类型：阶段门。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W42](#w42)、[W43](#w43)、[W44](#w44)、[W45](#w45)。

前置尚未验收：[W42](#w42)、[W43](#w43)、[W44](#w44)、[W45](#w45)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T01](TECHNICAL_TRACE.md#t01)、[T04](TECHNICAL_TRACE.md#t04)、[T05](TECHNICAL_TRACE.md#t05)、[T06](TECHNICAL_TRACE.md#t06)、[T07](TECHNICAL_TRACE.md#t07)、[T08](TECHNICAL_TRACE.md#t08)、[T09](TECHNICAL_TRACE.md#t09)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：本项为综合验收，按所列T/R及本卡检查。。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§1.3](CANONICAL_SYSTEM_SPEC_V5.md#th-1-3)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§8.4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-8-4-1)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§9](CANONICAL_SYSTEM_SPEC_V5.md#th-9)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10](CANONICAL_SYSTEM_SPEC_V5.md#th-10)、[§11](CANONICAL_SYSTEM_SPEC_V5.md#th-11)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：W42—W45实际专业专题、新例及需要时的分工比较。

**交付物**：

- 专业资料/方法带来实际质量增益及来源/单位/口径/时点/权限可追溯专题。
- 复杂分工保留/简化及配置有限准入决定。

**验收清单**（另核Q01—Q07）：

- [ ] 内容与证据：真实专题证明专业条件及商业/财务等适用传导，比普通摘要多出的解释/教学可核。
- [ ] 范围与质量：需要专业分工时同固定样本比较漏检/误报/中文质量/时间/Token和金额；无增益即简化，有据不适用保留独立审稿。
- [ ] 禁止的捷径：新例与失败/未验范围如实记录；专业专题不挤掉九领域价值标准，不凭角色数越过内容门。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：保留实际证据与未过项，退回相应工作包修订；不能以后阶段工具或维护检查替代本阶段质量门。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w46"></a>
## W46｜GitHub周运行参数与私有持久环境落实

顺序：49/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[G03](#g03)。

前置尚未验收：[G03](#g03)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T01](TECHNICAL_TRACE.md#t01)、[T11](TECHNICAL_TRACE.md#t11)、[T13](TECHNICAL_TRACE.md#t13)、[R08](TECHNICAL_TRACE.md#r08)。

逐项逻辑：R08.F01、T13.L01、T11.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：已过阶段门的内容链；用户确认GitHub Actions每周自动执行；具体周历、私有档案及独立观察/告警参数待落实。 仅落实每周开始；完成/停止/发送时刻不设置，已选C01—C06方向按实际兼容组合验证。

**交付物**：

- 周启动的周几/时刻/时区、资料周界/截点、服务/预算/渠道开关及变更；无固定结束/发送时刻。
- 私有持久存储、访问范围、版本迁移与真实可恢复数据边界。
- GitHub默认分支/运行入口/周历、时区与夏令时、期号/截点、延迟/无进展阈值、有限补跑及实际平台时限的明确配置。
- 主任务之外的独立漏跑/进展观察与告警位置/最低权限；未落实时标保障范围受限。
- C06 uv锁Python/实际依赖组合及工具/Actions版本；C03官方持久checkpointer与C02私有业务/文件存储、备份/观察接口落实，共用现有能力。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：明确GitHub每周运行目标与全部实际未定参数；研究档案/锁/检查点持久且私有，runner临时文件不作唯一原件，密钥不入档。
- [ ] 反向：自动套用日报时区、邮箱、密钥、预算或将未知参数当默认许可均失败。
- [ ] 衔接：W47—W55只消费本步明确配置；未获外发/付费授权仍可按允许范围离线预演。
- [ ] 核默认分支/工作流启用、实际权限/额度/时区及独立观察可达性；不把GitHub托管任务环境当永久服务器。
- [ ] 配置/界面只有启动日时，不把完成/发送钟点当必填；新环境按锁重建且不每周自动升级，官方检查点和正文档案均能跨runner取回。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：缺必需参数停止依赖它的操作，继续无依赖的离线修复；不擅自部署或购买。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w47"></a>
## W47｜每周schedule入口、期号认领与完整运行

顺序：50/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W46](#w46)、[W20](#w20)、[W21](#w21)、[W18](#w18)。

前置尚未验收：[W18](#w18)、[W20](#w20)、[W21](#w21)、[W46](#w46)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T13](TECHNICAL_TRACE.md#t13)、[T01](TECHNICAL_TRACE.md#t01)、[T02](TECHNICAL_TRACE.md#t02)、[R08](TECHNICAL_TRACE.md#r08)。

逐项逻辑：R08.F02、T13.L03、T01.L02、T02.L01。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§4.1](CANONICAL_SYSTEM_SPEC_V5.md#th-4-1)、[§4.2](CANONICAL_SYSTEM_SPEC_V5.md#th-4-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：已确认周历/区间/时区、获准来源、真实业务入口、持久应运行期次与最小预算门。

**交付物**：

- 拟建独立intelligence-weekly.yml生产入口的实际实现：schedule、受控workflow_dispatch/恢复均走同一业务入口；当前未创建。
- 预登记期次、原子认领/去重、Run关联、源增量游标及完整R01/R03实际运行结果。
- §25.13 T13.AUTO01/AUTO02/AUTO03与NC-043任务级重入证据；不与操作/出版/交付身份混用。
- C06只按开始时间认领，C03持续/跨job续跑到合格完成；C02登记下一周待办，健康前期不取消/覆盖，新期独立身份排队。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：无用户电脑/聊天/日报/人工dispatch参与也能从真实schedule自动启动并完成已验内容链或留下真实受阻原因；同一期号重复事件只登记空操作。
- [ ] 反向：无主Run、假入口/echo/只跑维护、忽略失败、错默认分支/禁用、延迟跨周重建期号、同一期多次费用/成品均失败。
- [ ] 衔接：与W48独立观察/恢复、W49成品、W51档案衔接；健康运行不被补跑取消，不同周不被并发队列静默挤掉。
- [ ] 业务期号取固定资料周界/时区而非Run ID或晚到实际日期；夏令时、只改触发时间/代码及重复dispatch对照通过。
- [ ] 长任务越过假定发送钟点仍健康推进；下周触发不杀前期、不清累计投入，故障/受阻可按依据暂挂；合格完成事件立即接W49/W50既有授权，不等固定时刻。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：先查任务事实/锁状态和有效检查点，不盲目重跑全部或修改日报启动器。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w48"></a>
## W48｜独立漏跑检查、有界补跑与运行恢复

顺序：51/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W47](#w47)、[W18](#w18)、[W17](#w17)、[W33](#w33)。

前置尚未验收：[W17](#w17)、[W18](#w18)、[W33](#w33)、[W47](#w47)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T13](TECHNICAL_TRACE.md#t13)、[T01](TECHNICAL_TRACE.md#t01)、[T11](TECHNICAL_TRACE.md#t11)、[R07](TECHNICAL_TRACE.md#r07)、[R08](TECHNICAL_TRACE.md#r08)。

逐项逻辑：T13.L01、T13.L02、T13.L03、R07.F02、R08.F02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2)、[§17.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-1)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：预登记应运行期次、真实Run/开始/进展/结束与成品、持久认领/检查点、操作/用量/额度和独立观察入口。

**交付物**：

- §25.13 T13.AUTO04/AUTO05/AUTO06：真实进展、持久检查点、独立漏跑/卡住观察、有界dispatch/恢复及已获准告警。
- 跨任务预算预留/结算/未知账单、重启对账、旧持有者迟到写入防护及操作幂等证据。
- 无主Run/被禁用/凭据失效/排队/进展停滞/runner结束/平台故障的区分诊断，实际保障范围与未完成记录。
- 直接复用C03官方检查点/持久模式与单一重试入口，长节点按真实中间产物拆段；观察区分健康长写作、排队、未知、无进展和资源/内容受阻。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：主任务根本未启动时仍能发现缺期；健康排队/运行与失效分别判断，已完成期不补跑，未完成期按相同业务身份及有效检查点有界恢复。
- [ ] 反向：仅依赖主任务内部自检、虚假更新时间、独立观察失联未发现、未知费用无限重试、旧运行迟到覆盖/重复提交/外发均失败。
- [ ] 衔接：W15核当前采用，W47核认领，W49/W50核成品/回执，W51核新runner取回与恢复；完整故障链交W55验。
- [ ] 当前runner/job时限前保存有效检查点并受控续跑；硬故障按最近持久版本恢复，仍服从质量/权限/预算，不能无限常驻。
- [ ] GitHub不可用/观察器缺权限时如实未补跑并从已获准独立通道告警；只有GitHub自身备用cron时不得冒称独立兜底通过。
- [ ] 总耗时长本身不触发强停/重启；技术片段时限前保存并同一期thread续跑，已有效节点/累计预算/外部回执不重做；SDK/图/观察重试不得相乘。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：未知先查询/对账，必要时保持受阻；保留已有有效产物，不自动扩大资源。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w49"></a>
## W49｜正式阅读格式、审后锁定与出版身份

顺序：52/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W46](#w46)、[W32](#w32)、[W48](#w48)。

前置尚未验收：[W32](#w32)、[W46](#w46)、[W48](#w48)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T10](TECHNICAL_TRACE.md#t10)、[T09](TECHNICAL_TRACE.md#t09)、[T11](TECHNICAL_TRACE.md#t11)、[R08](TECHNICAL_TRACE.md#r08)。

逐项逻辑：T10.L01、T10.L02、T10.L03、R08.F03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.5](CANONICAL_SYSTEM_SPEC_V5.md#th-13-5)、[§13.6](CANONICAL_SYSTEM_SPEC_V5.md#th-13-6)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：有效终稿/Review、已确定实际输出格式及出版版本。

**交付物**：

- 只消费定稿的正式渲染、实际文件检查、源/文件/Review对应和冻结身份。
- NC-043中出版版本与纯重渲染的区别，未审语义变化返审。
- C05 Jinja与按实际格式WeasyPrint共用周刊/年报呈现，中文字体及受控资源实际验；内容/文件合格事件触发归档与后续获准交付。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：每个实际使用格式查看实际文件，图文/单位/脚注/链接正确，能回冻结终稿。
- [ ] 反向：渲染擅自改写、仅凭哈希放行、换一个字改意及重渲染当新交付许可均失败。
- [ ] 衔接：新命题回研究/审核，纯版式可有据承接；交W50的是核过的具体文件和原授权范围。
- [ ] 不在渲染或发布配置中设置强制截止/固定发送时刻，只有有效实际文件可触发下一步；不因到钟点跳过内容/呈现复核。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：修具体格式/内容缺陷，未生成/未查看格式标未验；文件生成不推定已交付。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w50"></a>
## W50｜授权交付、回执与重复投递防护

顺序：53/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W49](#w49)、[W48](#w48)。

前置尚未验收：[W48](#w48)、[W49](#w49)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T13](TECHNICAL_TRACE.md#t13)、[T10](TECHNICAL_TRACE.md#t10)、[T11](TECHNICAL_TRACE.md#t11)、[R08](TECHNICAL_TRACE.md#r08)。

逐项逻辑：R08.F01、R08.F03、R08.F04、T13.L02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-6-2)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：具体刊物/文件版本、渠道/对象及明确交付授权；未授权用隔离测试端。

**交付物**：

- 独立交付身份、发送/查询适配与真实ACCEPTED/CONFIRMED/UNKNOWN记录。
- NC-043中接受后超时、重试/重渲染/换版本与重复投递的核查证据。
- C06共用已有操作/回执接口，在文件合格且已有交付授权时立即进入交付，无另一发送钟点；未授权可归档或隔离测试。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：回执指向实际定稿/渠道，服务商接受与确认到达分开；相同交付身份不重复发送。
- [ ] 反向：未知直接重发、ACCEPTED冒充已收到、重渲染重新授权或换渠道绕过许可均失败。
- [ ] 衔接：先查询/人工核真实服务结果再决定后续；与W47任务、W17操作、W49出版身份分别关联。
- [ ] 明示长任务完成前无投递、合格完成后不等钟点；接受后超时继续查同一交付身份，立即衔接不意味盲目重试或再次授权。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：未知保持UNKNOWN并查证；实际外发仍按明确授权，离线成功不冒充真实送达。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w51"></a>
## W51｜私有归档、备份与真实恢复

顺序：54/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W46](#w46)、[W48](#w48)、[W49](#w49)。

前置尚未验收：[W46](#w46)、[W48](#w48)、[W49](#w49)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T11](TECHNICAL_TRACE.md#t11)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：T11.L01、T11.L02、T11.L03、T13.L03。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§16.6.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-2)、[§16.6.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-3)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：允许保存的真实档案、引用关系、当前限制与备份/恢复目标。

**交付物**：

- 实际备份及隔离恢复结果、全文/索引/审核/判断/许可/限制的一致性核对。
- 密钥/受限原作排除规则的实际检查和已验恢复范围。
- C02业务/原件档案和C03官方checkpointer按各自真实后端备份/恢复；使用兼容锁版本，新runner共用同一thread/期号。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：恢复后可找回完整原稿/历史原话，当前限制仍生效，索引可从权威记录重建。
- [ ] 反向：仅有压缩包无恢复、恢复遗漏限制/版本关系、用无权材料证明完整性均失败。
- [ ] 衔接：恢复环境重跑当前/双as-of查询和采用检查，W55使用实际恢复记录。
- [ ] 隔离新环境取回实际正文、限制和检查点后可继续，不以临时SQLite/内存/单个checkpoint证明档案完整或外部无重复。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按缺项修备份/恢复链；无法取回范围如实报告，不把空壳索引当历史完整。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w52"></a>
## W52｜年度双输入与旧判断审计

顺序：55/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W51](#w51)、[W39](#w39)、[W40](#w40)。

前置尚未验收：[W39](#w39)、[W40](#w40)、[W51](#w51)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T12](TECHNICAL_TRACE.md#t12)、[R06](TECHNICAL_TRACE.md#r06)、[T11](TECHNICAL_TRACE.md#t11)、[T04](TECHNICAL_TRACE.md#t04)。

逐项逻辑：T12.L01、R06.F01、R06.F02。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-2-3)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：实际周刊/缺期/原判断、独立年度原件和后续结果；先明示缩区间。

**交付物**：

- A01—A07年度范围/双输入、时间线、可比指标、漏题和旧判断/数据修订表。
- C02读取真实周刊/原判断，C01复用同一独立年度取证入口；T12只组织年度双输入，不接另一档案/抓取系统。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：独立回查不复制周刊，历史当时所知、当时公开却漏用、事后信息分别保留。
- [ ] 反向：伪造52期、合订冒充年报、年末资料回写成年初已知及不可比数据直接对比均失败。
- [ ] 衔接：复用W33双模式历史和W40纠错，新增资料按当前用途许可交W53研究。
- [ ] 原历史截面与后来材料分明，复用取得代码仍须年度独立漏题检查，不能把周刊合订当双输入。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：缺期/缺资料明确缩范围，不能从短期材料推定全年能力或成本。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w53"></a>
## W53｜年度新综合、教学与重新独审

顺序：56/59；阶段：4；类型：代码与接口工作包。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W52](#w52)、[W43](#w43)、[W49](#w49)。

前置尚未验收：[W43](#w43)、[W49](#w49)、[W52](#w52)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[T12](TECHNICAL_TRACE.md#t12)、[R06](TECHNICAL_TRACE.md#r06)、[T05](TECHNICAL_TRACE.md#t05)、[T09](TECHNICAL_TRACE.md#t09)、[T10](TECHNICAL_TRACE.md#t10)。

逐项逻辑：T12.L02、T12.L03、R06.F03、R06.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-2-3)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.8.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-8-3)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)。原定义/例外仍须回原文读取。

**输入**：年度双输入、当前有效旧知识、补漏及新的跨题问题。

**交付物**：

- A08—A12年度新研判/知识综合/未来条件稿及全新Review。
- 允许年度用途的原作/中文材料、实际成品与归档指针。
- C04共用研究/B1/B2/独审任务和C02版本，C05复用成刊；只新增年度问题/范围/A工序配置。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：年度认识由新的可核连接产生，旧判断原话保留；独立审核和成品核对绑定当次新稿。
- [ ] 反向：旧周刊PASS直接批准新综合、重收材料不核许可或仅拼接旧文均不通过。
- [ ] 衔接：T12调用同一T03—T10，不建年报事实库；新证据回实际研究/审核，交W54集成验。
- [ ] 周刊旧PASS不批准年度新命题；年度新综合与教学分别有据，不为年报复制模型/翻译/排版框架。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：缺新研究退对应案卷/取证，缩区间成果明确标示，不宣称全年年报通过。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w54"></a>
## W54｜R06年度缩区间完整回放

顺序：57/59；阶段：4；类型：路线集成验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W52](#w52)、[W53](#w53)。

前置尚未验收：[W52](#w52)、[W53](#w53)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R06](TECHNICAL_TRACE.md#r06)、[T12](TECHNICAL_TRACE.md#t12)、[T11](TECHNICAL_TRACE.md#t11)、[T09](TECHNICAL_TRACE.md#t09)、[T10](TECHNICAL_TRACE.md#t10)。

逐项逻辑：R06.F01、R06.F02、R06.F03、R06.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-2-3)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§14.1](CANONICAL_SYSTEM_SPEC_V5.md#th-14-1)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.4](CANONICAL_SYSTEM_SPEC_V5.md#th-16-4)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§16.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6-1)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)。原定义/例外仍须回原文读取。

**输入**：实际可用周刊和独立原件、缩区间年报稿/Review/实际文件。

**交付物**：

- R06从双输入到漏题/旧判断审计、年度新综合/独审/成品归档的全链证据。
- 实际区间、未覆盖全年部分及许可/费用/质量限制。
- R06只调用C01—C05共享接口回放年度缩区间，周刊/年度使用同一格式/版本校核。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：任一重要年度结论能回两路材料与新研究，旧原话和事后修订可分别取回。
- [ ] 反向：只合订、无独立回查、遗漏旧错误/缺期、短演练冒称全年验证均失败。
- [ ] 衔接：与R05更正/当前复用链一致，实际年报文件也经W49核对；全年另凭全年真实资料验。
- [ ] 同一底座可复用验证，但新年度输入/综合/独审各有结果；未自然经过全年仍报告范围限制。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按缺口回W52/53，不为赶阶段门伪造年度范围。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="w55"></a>
## W55｜每周自然触发、连续周刊与漏跑故障验收

顺序：58/59；阶段：4；类型：路线集成验收。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W47](#w47)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W54](#w54)。

前置尚未验收：[W47](#w47)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W54](#w54)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R08](TECHNICAL_TRACE.md#r08)、[R01](TECHNICAL_TRACE.md#r01)、[R03](TECHNICAL_TRACE.md#r03)、[R05](TECHNICAL_TRACE.md#r05)、[R07](TECHNICAL_TRACE.md#r07)、[T01](TECHNICAL_TRACE.md#t01)、[T10](TECHNICAL_TRACE.md#t10)、[T11](TECHNICAL_TRACE.md#t11)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：R08.F01、R08.F02、R08.F03、R08.F04。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.7](CANONICAL_SYSTEM_SPEC_V5.md#th-19-7)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：获准来源、已验内容链、实际GitHub周历/生产入口、独立观察/持久档案及隔离故障/交付测试环境。

**交付物**：

- 连续多次完整离线周刊的质量/成本/失败记录和实际刊次清单。
- 断源、超预算、重复触发、模型故障、审后修改、接受后超时、重启/备份恢复的真实结果。
- 按§25.13逐项留真实schedule事件/Run与业务期号；临时试验有测试期号、到期失效和试后清理证据，真实每周自然触发另列。
- 无主Run、工作流被禁用/凭据失效、排队/无进展、跨周/夏令时、重复补跑、硬中断/续跑与GitHub/独立观察故障矩阵。
- 只设开始的长任务、跨多个job/run及下周触发时前期健康/受阻、待办持续积压、完成事件后获准交付的实际或明示模拟记录。

**验收清单**（另核Q01—Q07）：

- [ ] 正向：每个刊次内容/版本/出版文件可回查；故障后保持有限采用、预算和幂等边界。
- [ ] 反向：一次成功当连续稳定、离线当真实送达、恢复丢限制、重复操作/发送或未知当成功均失败。
- [ ] 衔接：R01/R03内容、R05当前限制、R07恢复和R08交付衔接共同通过；至少覆盖一个恢复后的完整刊次。
- [ ] 必须有真实schedule自然触发的完整链证据，区别临时schedule、workflow_dispatch、人工执行与规范CI；后者不能代验每周启动。
- [ ] 独立观察先发现漏跑再同一期号补跑，健康/已完成任务不重复执行；故障时如实告警/未完成，无重复主要调用费用或投递。
- [ ] 连续预演/真实周运行与实际成品/持久原稿一一对应，未自然经过的周/未覆盖平台故障明确待验，不用模拟充数。
- [ ] 长任务不因耗时或假定发送时刻强停/降质；续跑保留同一期身份/有效节点/累计预算/回执；新周不取消旧周，持续积压保留并告警，模拟时钟不冒充自然周稳定。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：按具体故障回相应包并重验受影响范围，正式外发/自动发行仍需实际明确授权。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

<a id="g04"></a>
## G04｜第四阶段门：生产离线验收与年度回放

顺序：59/59；阶段：4；类型：阶段门。

进度：**待开始**；关联：CURRENT_BINDING；前置：[W46](#w46)、[W47](#w47)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W52](#w52)、[W53](#w53)、[W54](#w54)、[W55](#w55)。

前置尚未验收：[W46](#w46)、[W47](#w47)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W52](#w52)、[W53](#w53)、[W54](#w54)、[W55](#w55)。仅供执行者核对，生成器不代为验收阶段。

责任模块/路线：[R01](TECHNICAL_TRACE.md#r01)、[R03](TECHNICAL_TRACE.md#r03)、[R05](TECHNICAL_TRACE.md#r05)、[R06](TECHNICAL_TRACE.md#r06)、[R07](TECHNICAL_TRACE.md#r07)、[R08](TECHNICAL_TRACE.md#r08)、[T01](TECHNICAL_TRACE.md#t01)、[T02](TECHNICAL_TRACE.md#t02)、[T04](TECHNICAL_TRACE.md#t04)、[T05](TECHNICAL_TRACE.md#t05)、[T09](TECHNICAL_TRACE.md#t09)、[T10](TECHNICAL_TRACE.md#t10)、[T11](TECHNICAL_TRACE.md#t11)、[T12](TECHNICAL_TRACE.md#t12)、[T13](TECHNICAL_TRACE.md#t13)。

逐项逻辑：本项为综合验收，按所列T/R及本卡检查。。

理论依据：[§0](CANONICAL_SYSTEM_SPEC_V5.md#th-0)、[§1](CANONICAL_SYSTEM_SPEC_V5.md#th-1)、[§2](CANONICAL_SYSTEM_SPEC_V5.md#th-2)、[§2.1](CANONICAL_SYSTEM_SPEC_V5.md#th-2-1)、[§2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-2-3)、[§3](CANONICAL_SYSTEM_SPEC_V5.md#th-3)、[§4](CANONICAL_SYSTEM_SPEC_V5.md#th-4)、[§5.2](CANONICAL_SYSTEM_SPEC_V5.md#th-5-2)、[§5.5](CANONICAL_SYSTEM_SPEC_V5.md#th-5-5)、[§6](CANONICAL_SYSTEM_SPEC_V5.md#th-6)、[§6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-6-1)、[§7](CANONICAL_SYSTEM_SPEC_V5.md#th-7)、[§7.3](CANONICAL_SYSTEM_SPEC_V5.md#th-7-3)、[§7.4](CANONICAL_SYSTEM_SPEC_V5.md#th-7-4)、[§8](CANONICAL_SYSTEM_SPEC_V5.md#th-8)、[§8.2](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2)、[§8.2.3](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-3)、[§8.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-2-4)、[§8.3.4](CANONICAL_SYSTEM_SPEC_V5.md#th-8-3-4)、[§9.1](CANONICAL_SYSTEM_SPEC_V5.md#th-9-1)、[§10.5](CANONICAL_SYSTEM_SPEC_V5.md#th-10-5)、[§10.6](CANONICAL_SYSTEM_SPEC_V5.md#th-10-6)、[§10.7](CANONICAL_SYSTEM_SPEC_V5.md#th-10-7)、[§12](CANONICAL_SYSTEM_SPEC_V5.md#th-12)、[§13](CANONICAL_SYSTEM_SPEC_V5.md#th-13)、[§13.1](CANONICAL_SYSTEM_SPEC_V5.md#th-13-1)、[§13.7](CANONICAL_SYSTEM_SPEC_V5.md#th-13-7)、[§14](CANONICAL_SYSTEM_SPEC_V5.md#th-14)、[§15](CANONICAL_SYSTEM_SPEC_V5.md#th-15)、[§15.2](CANONICAL_SYSTEM_SPEC_V5.md#th-15-2)、[§16](CANONICAL_SYSTEM_SPEC_V5.md#th-16)、[§16.1](CANONICAL_SYSTEM_SPEC_V5.md#th-16-1)、[§16.2](CANONICAL_SYSTEM_SPEC_V5.md#th-16-2)、[§16.3](CANONICAL_SYSTEM_SPEC_V5.md#th-16-3)、[§16.6](CANONICAL_SYSTEM_SPEC_V5.md#th-16-6)、[§17](CANONICAL_SYSTEM_SPEC_V5.md#th-17)、[§17.2.4](CANONICAL_SYSTEM_SPEC_V5.md#th-17-2-4)、[§18](CANONICAL_SYSTEM_SPEC_V5.md#th-18)、[§18.1](CANONICAL_SYSTEM_SPEC_V5.md#th-18-1)、[§19](CANONICAL_SYSTEM_SPEC_V5.md#th-19)、[§19.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-1)、[§19.2](CANONICAL_SYSTEM_SPEC_V5.md#th-19-2)、[§19.5.1](CANONICAL_SYSTEM_SPEC_V5.md#th-19-5-1)、[§20](CANONICAL_SYSTEM_SPEC_V5.md#th-20)、[§20.3](CANONICAL_SYSTEM_SPEC_V5.md#th-20-3)、[§21](CANONICAL_SYSTEM_SPEC_V5.md#th-21)、[§22](CANONICAL_SYSTEM_SPEC_V5.md#th-22)、[§22.4](CANONICAL_SYSTEM_SPEC_V5.md#th-22-4)、[§23](CANONICAL_SYSTEM_SPEC_V5.md#th-23)、[§23.1](CANONICAL_SYSTEM_SPEC_V5.md#th-23-1)、[§23.3](CANONICAL_SYSTEM_SPEC_V5.md#th-23-3)、[§24](CANONICAL_SYSTEM_SPEC_V5.md#th-24)、[§24.5](CANONICAL_SYSTEM_SPEC_V5.md#th-24-5)、[§24.6.1](CANONICAL_SYSTEM_SPEC_V5.md#th-24-6-1)。原定义/例外仍须回原文读取。

**输入**：W46—W55实际GitHub周运行、私有档案/独立观察、连续离线刊次、自然schedule/漏跑/恢复及年度缩区间证据。

**交付物**：

- 生产运行已验范围、实际质量/投入/故障/回执/备份恢复结论。
- 年度双输入回放与全年未验范围；自动发行/外发/费用的实际授权状态。
- 六个共享单元的生产适配、只设周开始/长任务续跑/完成后获准交付及真实吞吐/积压范围结论；未验条件和重型可选依赖明确列出。

**验收清单**（另核Q01—Q07）：

- [ ] 内容与证据：连续多次完整离线周刊及原定断源/超预算/重复/模型/审后改稿/未知回执/恢复场景均有实际结果。
- [ ] 范围与质量：年报双输入、漏报/纠错、旧判断时点与年度新综合成立；短演练明确不是全年验证。
- [ ] 禁止的捷径：阶段通过不自动打开外发、收费或自动发行；具体预算/渠道获另行明确授权且相应运行验收通过才启用。
- [ ] 每周schedule自动触发、完整业务链、无Run漏跑的独立检测/同一期补跑及平台失效告警均有实际结果；手动成功、维护CI或cron存在不代验。用户已确认周运行方向，实际启用仍按已落实配置和运行验收；外发/自动发行/费用沿原明确授权。
- [ ] 完成时刻不预设；健康跨job/跨周、受阻暂挂、待办不丢、旧回执/预算不重置及完成事件衔接有实据。关联维护/上游项目存在不抵任何业务验收。
- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。

**不通过时**：保留实际证据与未过项，退回相应工作包修订；不能以后阶段工具或维护检查替代本阶段质量门。

关联变化：本卡依据变化=False；待复核T/R=无；上游清单待复核=无。

实际证据：尚无；本轮只制定清单，未据此宣布开发或能力完成。

## 13个功能模块的验收清单

以下逐项取自§25既有逻辑的启用条件、输出和限制，不另写一套模块规则。按本次阶段/稿型/允许用途验收，相关工作包提交实际证据；不要求先完成未来全部增强才能制作第一份样刊。

<a id="module-t01"></a>
### T01｜规范与交接控制

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t01)。

- 第1阶段承接：[W01](#w01)。
- 第2阶段承接：[W13](#w13)、[W14](#w14)、[W15](#w15)、[W16](#w16)、[W18](#w18)、[W31](#w31)、[W34](#w34)、[W35](#w35)、[W36](#w36)。
- 第3阶段承接：[W45](#w45)。
- 第4阶段承接：[W46](#w46)、[W47](#w47)、[W48](#w48)、[W55](#w55)。

- [ ] T01.L01 准备当前任务：条件=本次职责和采用用途明确；实际输出=实际提供范围与缺口；限制=不以准备清单或模型自称已读代替实际输入。
- [ ] T01.L02 核对采用资格：条件=实际依赖匹配且未过期；实际输出=允许性质/用途及相应步骤决定；限制=候选可以按候选性质交接；不得升格为已证事实。
- [ ] T01.L03 记录决定并交接：条件=相应责任核查已完成；实际输出=绑定版本的采用记录或退回对象；限制=本模块的文档关联检查不替代研究放行程序。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t02"></a>
### T02｜全球发现与候选归并

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t02)。

- 第1阶段承接：[W02](#w02)。
- 第2阶段承接：[W20](#w20)、[W21](#w21)、[W22](#w22)。
- 第4阶段承接：[W47](#w47)。

- [ ] T02.L01 取得合法轻量线索：条件=实际访问和本用途允许；实际输出=候选、原始日期及取得状态；限制=候选来源登记不等于生产许可；不恢复全库探测。
- [ ] T02.L02 归并并保留探索：条件=同事件、同源或不确定分别可核；实际输出=归并建议、探索候选与缺口；限制=不同网址/语言不是独立证据；模糊归并须人工核。
- [ ] T02.L03 作池外参照检查：条件=抽查范围和截点明确；实际输出=发现/筛选/合理舍弃的区分及处理；限制=小样本不能宣称全球召回率或零遗漏。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t03"></a>
### T03｜选题、复选与整刊计划

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t03)。

- 第1阶段承接：[W02](#w02)、[W03](#w03)、[W05](#w05)、[W12](#w12)。
- 第2阶段承接：[W22](#w22)、[W23](#w23)、[W26](#w26)、[W32](#w32)、[W37](#w37)、[W38](#w38)、[W39](#w39)。

- [ ] T03.L01 初选并给取证计划：条件=真实日期及基本价值成立；实际输出=S0—S7问题、类型及材料需求；限制=重要性、当前可知程度和本期呈现分别决定。
- [ ] T03.L02 查证后S8复选：条件=足以开展注明范围的工作；实际输出=COVER/REVISE/WATCH/DROP及理由；限制=不要求先完成原因研究才准许开始研究；COVER不等于PASS。
- [ ] T03.L03 复核成熟稿的本期价值：条件=CURRENT_WEEK或合格长期专题依据成立；实际输出=当期组合取舍或跨周接续；限制=长期题失去深度且无当周新增，不自动降为精选刊登。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t04"></a>
### T04｜原作、证据与中文材料

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t04)。

- 第1阶段承接：[W04](#w04)、[W05](#w05)、[W07](#w07)。
- 第2阶段承接：[W13](#w13)、[W24](#w24)、[W25](#w25)、[W26](#w26)、[W37](#w37)、[W38](#w38)。
- 第3阶段承接：[W42](#w42)。
- 第4阶段承接：[W52](#w52)。

- [ ] T04.L01 核用途并取具体版本：条件=访问、处理、保存和拟用范围有依据；实际输出=取得回执、版本、范围和许可记录；限制=只有链接或HTTP成功时不得填已核正文/全文。
- [ ] T04.L02 核主张和支持范围：条件=相关上下文和专业条件实际可核；实际输出=Evidence/Claim支持、反证及缺口；限制=计算须核实际输入与执行；同源材料不算多证。
- [ ] T04.L03 制作入选中文并核更新：条件=入选且相应用途允许；实际输出=节选译文/独立导引及定稿更新结果；限制=S8后制作；影响结论的截点后材料须更新截点重审或调整安排。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t05"></a>
### T05｜问题界定与联合研究组织

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t05)。

- 第1阶段承接：[W06](#w06)、[W07](#w07)。
- 第2阶段承接：[W16](#w16)、[W25](#w25)、[W27](#w27)、[W38](#w38)、[W39](#w39)。
- 第3阶段承接：[W42](#w42)、[W43](#w43)。
- 第4阶段承接：[W53](#w53)。

- [ ] T05.L01 固定事实、问题和边界：条件=核心事实可支持开展本题；实际输出=M01—M03与问题完成标准；限制=研究准入不等于本题原因已经证明。
- [ ] T05.L02 共同查条件与竞争解释：条件=方法前提与本题条件相称；实际输出=M04—M09过程/数量/反证及支持范围；限制=新材料可迫使改题；形成和检验材料分开。
- [ ] T05.L03 决定有限交付或补研：条件=对应问题的完成标准与停止理由可核；实际输出=有范围的研究成果和下一取证/停止决定；限制=合格未知允许；不会、缺证、超预算不叫不适用。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t06"></a>
### T06｜顾问B1本案研判

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t06)。

- 第1阶段承接：[W08](#w08)。
- 第2阶段承接：[W28](#w28)。
- 第3阶段承接：[W43](#w43)。

- [ ] T06.L01 核主体与现实处境：条件=权限、资源、行动和范围可核；实际输出=有据的处境/约束地图；限制=公开表态、执行、结果和未知动机分开。
- [ ] T06.L02 形成有限判断：条件=判断强度与实际支持相称；实际输出=M10本案结论及相关含义；限制=无实际机会或决策问题不强配投资/创业建议。
- [ ] T06.L03 交可审阅研判：条件=相应前提和限制随文保留；实际输出=B1贡献与可改变判断的材料；限制=不以新观点数量或通用建议代替本案理解。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t07"></a>
### T07｜帝师B2知识研究与教学

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t07)。

- 第1阶段承接：[W06](#w06)、[W09](#w09)。
- 第2阶段承接：[W27](#w27)、[W29](#w29)。
- 第3阶段承接：[W43](#w43)。

- [ ] T07.L01 提出材料中的知识问题：条件=知识对理解本题有明确作用；实际输出=必要概念、专业/历史资料需求；限制=不只接顾问定好的结论；不诊断读者掌握状态。
- [ ] T07.L02 由具体到过程再到认识：条件=命题性质与依据对应；实际输出=M11连续讲解、必要基础与反例；限制=认识未形成回研究，解释已有依据但不清楚回教学。
- [ ] T07.L03 核迁移并形成读者稿：条件=当前用途、条件和不同场景可核；实际输出=知识贡献、迁移查证步骤及必要回顾；限制=教学复用不算独立验证；去掉术语仍须有清楚过程。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t08"></a>
### T08｜条件推演与事前检验准备

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t08)。

- 第1阶段承接：[W10](#w10)。
- 第2阶段承接：[W30](#w30)。
- 第3阶段承接：[W43](#w43)。

- [ ] T08.L01 判断可推演到哪里：条件=路径连接和条件有相称依据；实际输出=情景适用范围或缺失区分材料；限制=不凑路径、概率或固定题数。
- [ ] T08.L02 写条件和中间传导：条件=各路径有实质可辨的过程；实际输出=C条件路径与开放问题；限制=未来路径不补成当前事实；不向读者索取答案。
- [ ] T08.L03 保存事前复查条件：条件=时间/版本及可反驳条件明确；实际输出=M12当期记录及后续重开触发；限制=不等未来发生才出刊；后来结果须另核机制。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t09"></a>
### T09｜独立审稿与具体内容放行

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t09)。

- 第1阶段承接：[W11](#w11)。
- 第2阶段承接：[W19](#w19)、[W31](#w31)、[W36](#w36)、[W37](#w37)、[W40](#w40)、[W41](#w41)。
- 第3阶段承接：[W43](#w43)、[W44](#w44)、[W45](#w45)。
- 第4阶段承接：[W49](#w49)、[W53](#w53)、[W54](#w54)。

- [ ] T09.L01 固定被审对象并独立查验：条件=核查所需资料实际取得；实际输出=独立疑点、支持核对和未核范围；限制=不能只审案卷；作者自评/预定PASS不是答案。
- [ ] T09.L02 核判断、教学及修订：条件=对应职责/适用性及支持关系可核；实际输出=实际修订处理、合理争议及剩余限制；限制=既验漏检也验误拒；不以多数投票判真伪。
- [ ] T09.L03 对实际版本作决定：条件=硬门和相应稿型责任达到；实际输出=Review的决定、版本与允许范围；限制=缺资源如实待审；CURRENT_BINDING不等于内容PASS。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t10"></a>
### T10｜成稿、整刊与实际阅读文件

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t10)。

- 第1阶段承接：[W12](#w12)。
- 第2阶段承接：[W32](#w32)、[W37](#w37)、[W40](#w40)。
- 第4阶段承接：[W49](#w49)、[W50](#w50)、[W53](#w53)、[W54](#w54)、[W55](#w55)。

- [ ] T10.L01 核当期取舍和重要更新：条件=足以影响结论的更新已处理；实际输出=整刊顺序与选题/更新决定；限制=不能把初选或单篇通过当整刊已合格。
- [ ] T10.L02 组织连续稿及卷首：条件=重要新概括有研究/审核支持；实际输出=整刊源和审后变更承接；限制=即使一字改意也按影响返审；纯呈现改版不重做无关研究。
- [ ] T10.L03 核实际文件与冻结归档：条件=呈现完整且版本对应；实际输出=Edition、文件检查与出版决定；限制=文件生成不等于内容已审、获准交付或确认到达。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t11"></a>
### T11｜共享档案、历史查询与纠错

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t11)。

- 第1阶段承接：[W01](#w01)、[W12](#w12)。
- 第2阶段承接：[W13](#w13)、[W16](#w16)、[W17](#w17)、[W33](#w33)、[W34](#w34)、[W36](#w36)、[W39](#w39)、[W40](#w40)。
- 第4阶段承接：[W46](#w46)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W52](#w52)、[W54](#w54)、[W55](#w55)。

- [ ] T11.L01 保存版本与引用用途：条件=可留内容、时间与版本明确；实际输出=不可无痕覆盖的原文及关联；限制=保存权不足保留允许定位；不得借不可变性保留无权全文。
- [ ] T11.L02 区分当前采用与历史回放：条件=当前限制已核或as-of模式明确；实际输出=可用范围或当时原话及后来说明；限制=索引命中不等于可正式采用；后来补录不能污染旧截点。
- [ ] T11.L03 追更正并按范围恢复：条件=先限制已知关键用途，再完成相关复核；实际输出=影响/漏依赖/误限、重审及当前指向；限制=不一改全撤或全过；测试副本不冒称自然更正。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t12"></a>
### T12｜年报双输入组织

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t12)。

- 第4阶段承接：[W52](#w52)、[W53](#w53)、[W54](#w54)。

- [ ] T12.L01 固定双输入与年度范围：条件=两路来源和知识截点可核；实际输出=A01—A07时间线、旧判断/修订及漏题审计；限制=不能伪造52期或以合订代独立回查。
- [ ] T12.L02 作年度新研究和知识综合：条件=新旧依据和现时用途分别核过；实际输出=A08—A11年度顾问/帝师/未来条件稿；限制=年末新资料不回写成年初已知；旧周刊PASS不批准新综合。
- [ ] T12.L03 核年报成品及许可：条件=当次权限和实际文件对应；实际输出=A12年报版本、索引与归档；限制=短期演练不证明全年质量、覆盖或费用。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。

<a id="module-t13"></a>
### T13｜模型、工具、投入及GitHub每周自动运行支撑

设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#t13)。

- 第1阶段承接：[W01](#w01)。
- 第2阶段承接：[W17](#w17)、[W18](#w18)、[W19](#w19)、[W35](#w35)、[W36](#w36)、[W41](#w41)。
- 第3阶段承接：[W42](#w42)、[W44](#w44)、[W45](#w45)。
- 第4阶段承接：[W46](#w46)、[W47](#w47)、[W48](#w48)、[W50](#w50)、[W51](#w51)、[W55](#w55)。

- [ ] T13.L01 核调用边界：条件=获准且范围相称，或明确受控试用；实际输出=本次可调用范围及限制；限制=未知预算不当无限授权；能力可用不等于可付费/外发。
- [ ] T13.L02 执行并记录真实结果：条件=实际请求与操作可确认；实际输出=真实输出/错误、用量/估计及失败记录；限制=不由模型补造版本、费用、页码、成功回执。
- [ ] T13.L03 核健康进展、同一期续跑或有界故障恢复：条件=区分健康长任务/排队与真实故障/受阻；同一期thread及认领/版本有效，故障恢复次数和预算有据；实际输出=健康持续/跨job续跑、真实积压/漏跑/受阻及有限恢复/告警记录；限制=只设开始，不以总耗时或钟点无成品强停/重启；原生检查点/副作用须验；重试一处主控，不重复费用/交付。
- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。


## 功能模块及路线反向索引

| T/R | 工作包/阶段门 |
|---|---|
| [R01](TECHNICAL_TRACE.md#r01) | [W02](#w02)、[W03](#w03)、[W06](#w06)、[W11](#w11)、[W12](#w12)、[G01](#g01)、[W36](#w36)、[W41](#w41)、[G02](#g02)、[W55](#w55)、[G04](#g04) |
| [R02](TECHNICAL_TRACE.md#r02) | [W39](#w39)、[W41](#w41)、[G02](#g02) |
| [R03](TECHNICAL_TRACE.md#r03) | [W05](#w05)、[W11](#w11)、[W12](#w12)、[G01](#g01)、[W37](#w37)、[W41](#w41)、[G02](#g02)、[W55](#w55)、[G04](#g04) |
| [R04](TECHNICAL_TRACE.md#r04) | [W04](#w04)、[W07](#w07)、[G01](#g01)、[W25](#w25)、[W27](#w27)、[W38](#w38)、[W41](#w41)、[G02](#g02) |
| [R05](TECHNICAL_TRACE.md#r05) | [W40](#w40)、[W41](#w41)、[G02](#g02)、[W55](#w55)、[G04](#g04) |
| [R06](TECHNICAL_TRACE.md#r06) | [W52](#w52)、[W53](#w53)、[W54](#w54)、[G04](#g04) |
| [R07](TECHNICAL_TRACE.md#r07) | [W01](#w01)、[G01](#g01)、[W14](#w14)、[W35](#w35)、[W36](#w36)、[W41](#w41)、[G02](#g02)、[W48](#w48)、[W55](#w55)、[G04](#g04) |
| [R08](TECHNICAL_TRACE.md#r08) | [W46](#w46)、[W47](#w47)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W55](#w55)、[G04](#g04) |
| [T01](TECHNICAL_TRACE.md#t01) | [W01](#w01)、[G01](#g01)、[W13](#w13)、[W14](#w14)、[W15](#w15)、[W16](#w16)、[W18](#w18)、[W31](#w31)、[W34](#w34)、[W35](#w35)、[W36](#w36)、[G02](#g02)、[W45](#w45)、[G03](#g03)、[W46](#w46)、[W47](#w47)、[W48](#w48)、[W55](#w55)、[G04](#g04) |
| [T02](TECHNICAL_TRACE.md#t02) | [W02](#w02)、[G01](#g01)、[W20](#w20)、[W21](#w21)、[W22](#w22)、[G02](#g02)、[W47](#w47)、[G04](#g04) |
| [T03](TECHNICAL_TRACE.md#t03) | [W02](#w02)、[W03](#w03)、[W05](#w05)、[W12](#w12)、[G01](#g01)、[W22](#w22)、[W23](#w23)、[W26](#w26)、[W32](#w32)、[W37](#w37)、[W38](#w38)、[W39](#w39)、[G02](#g02) |
| [T04](TECHNICAL_TRACE.md#t04) | [W04](#w04)、[W05](#w05)、[W07](#w07)、[G01](#g01)、[W13](#w13)、[W24](#w24)、[W25](#w25)、[W26](#w26)、[W37](#w37)、[W38](#w38)、[G02](#g02)、[W42](#w42)、[G03](#g03)、[W52](#w52)、[G04](#g04) |
| [T05](TECHNICAL_TRACE.md#t05) | [W06](#w06)、[W07](#w07)、[G01](#g01)、[W16](#w16)、[W25](#w25)、[W27](#w27)、[W38](#w38)、[W39](#w39)、[G02](#g02)、[W42](#w42)、[W43](#w43)、[G03](#g03)、[W53](#w53)、[G04](#g04) |
| [T06](TECHNICAL_TRACE.md#t06) | [W08](#w08)、[G01](#g01)、[W28](#w28)、[G02](#g02)、[W43](#w43)、[G03](#g03) |
| [T07](TECHNICAL_TRACE.md#t07) | [W06](#w06)、[W09](#w09)、[G01](#g01)、[W27](#w27)、[W29](#w29)、[G02](#g02)、[W43](#w43)、[G03](#g03) |
| [T08](TECHNICAL_TRACE.md#t08) | [W10](#w10)、[G01](#g01)、[W30](#w30)、[G02](#g02)、[W43](#w43)、[G03](#g03) |
| [T09](TECHNICAL_TRACE.md#t09) | [W11](#w11)、[G01](#g01)、[W19](#w19)、[W31](#w31)、[W36](#w36)、[W37](#w37)、[W40](#w40)、[W41](#w41)、[G02](#g02)、[W43](#w43)、[W44](#w44)、[W45](#w45)、[G03](#g03)、[W49](#w49)、[W53](#w53)、[W54](#w54)、[G04](#g04) |
| [T10](TECHNICAL_TRACE.md#t10) | [W12](#w12)、[G01](#g01)、[W32](#w32)、[W37](#w37)、[W40](#w40)、[G02](#g02)、[W49](#w49)、[W50](#w50)、[W53](#w53)、[W54](#w54)、[W55](#w55)、[G04](#g04) |
| [T11](TECHNICAL_TRACE.md#t11) | [W01](#w01)、[W12](#w12)、[G01](#g01)、[W13](#w13)、[W16](#w16)、[W17](#w17)、[W33](#w33)、[W34](#w34)、[W36](#w36)、[W39](#w39)、[W40](#w40)、[G02](#g02)、[W46](#w46)、[W48](#w48)、[W49](#w49)、[W50](#w50)、[W51](#w51)、[W52](#w52)、[W54](#w54)、[W55](#w55)、[G04](#g04) |
| [T12](TECHNICAL_TRACE.md#t12) | [W52](#w52)、[W53](#w53)、[W54](#w54)、[G04](#g04) |
| [T13](TECHNICAL_TRACE.md#t13) | [W01](#w01)、[G01](#g01)、[W17](#w17)、[W18](#w18)、[W19](#w19)、[W35](#w35)、[W36](#w36)、[W41](#w41)、[G02](#g02)、[W42](#w42)、[W44](#w44)、[W45](#w45)、[G03](#g03)、[W46](#w46)、[W47](#w47)、[W48](#w48)、[W50](#w50)、[W51](#w51)、[W55](#w55)、[G04](#g04) |

## 72项逻辑覆盖索引

| 逻辑ID | 对应工作包 |
|---|---|
| R01.F01 | [W02](#w02)、[W36](#w36) |
| R01.F02 | [W03](#w03)、[W36](#w36) |
| R01.F03 | [W06](#w06)、[W36](#w36) |
| R01.F04 | [W11](#w11)、[W36](#w36) |
| R01.F05 | [W12](#w12)、[W36](#w36) |
| R02.F01 | [W39](#w39) |
| R02.F02 | [W39](#w39) |
| R02.F03 | [W39](#w39) |
| R02.F04 | [W39](#w39) |
| R03.F01 | [W05](#w05)、[W37](#w37) |
| R03.F02 | [W05](#w05)、[W37](#w37) |
| R03.F03 | [W11](#w11)、[W37](#w37) |
| R03.F04 | [W12](#w12)、[W37](#w37) |
| R04.F01 | [W04](#w04)、[W25](#w25)、[W38](#w38) |
| R04.F02 | [W04](#w04)、[W25](#w25)、[W38](#w38) |
| R04.F03 | [W07](#w07)、[W25](#w25)、[W38](#w38) |
| R04.F04 | [W07](#w07)、[W27](#w27)、[W38](#w38) |
| R05.F01 | [W40](#w40) |
| R05.F02 | [W40](#w40) |
| R05.F03 | [W40](#w40) |
| R05.F04 | [W40](#w40) |
| R06.F01 | [W52](#w52)、[W54](#w54) |
| R06.F02 | [W52](#w52)、[W54](#w54) |
| R06.F03 | [W53](#w53)、[W54](#w54) |
| R06.F04 | [W53](#w53)、[W54](#w54) |
| R07.F01 | [W01](#w01)、[W14](#w14)、[W36](#w36) |
| R07.F02 | [W36](#w36)、[W48](#w48) |
| R07.F03 | [W35](#w35)、[W36](#w36) |
| R07.F04 | [W36](#w36) |
| R08.F01 | [W46](#w46)、[W50](#w50)、[W55](#w55) |
| R08.F02 | [W47](#w47)、[W48](#w48)、[W55](#w55) |
| R08.F03 | [W49](#w49)、[W50](#w50)、[W55](#w55) |
| R08.F04 | [W50](#w50)、[W55](#w55) |
| T01.L01 | [W01](#w01)、[W13](#w13)、[W14](#w14)、[W35](#w35) |
| T01.L02 | [W15](#w15)、[W16](#w16)、[W18](#w18)、[W31](#w31)、[W34](#w34)、[W45](#w45)、[W47](#w47) |
| T01.L03 | [W15](#w15) |
| T02.L01 | [W02](#w02)、[W20](#w20)、[W47](#w47) |
| T02.L02 | [W02](#w02)、[W21](#w21) |
| T02.L03 | [W02](#w02)、[W22](#w22) |
| T03.L01 | [W03](#w03)、[W23](#w23) |
| T03.L02 | [W05](#w05)、[W23](#w23)、[W26](#w26) |
| T03.L03 | [W12](#w12)、[W22](#w22)、[W23](#w23)、[W32](#w32) |
| T04.L01 | [W04](#w04)、[W13](#w13)、[W24](#w24)、[W42](#w42) |
| T04.L02 | [W04](#w04)、[W25](#w25)、[W42](#w42) |
| T04.L03 | [W05](#w05)、[W26](#w26) |
| T05.L01 | [W06](#w06)、[W16](#w16)、[W27](#w27) |
| T05.L02 | [W07](#w07)、[W16](#w16)、[W27](#w27)、[W42](#w42)、[W43](#w43) |
| T05.L03 | [W07](#w07)、[W27](#w27) |
| T06.L01 | [W08](#w08)、[W28](#w28) |
| T06.L02 | [W08](#w08)、[W28](#w28)、[W43](#w43) |
| T06.L03 | [W08](#w08)、[W28](#w28) |
| T07.L01 | [W06](#w06)、[W27](#w27)、[W29](#w29) |
| T07.L02 | [W09](#w09)、[W29](#w29)、[W43](#w43) |
| T07.L03 | [W09](#w09)、[W29](#w29) |
| T08.L01 | [W10](#w10)、[W30](#w30) |
| T08.L02 | [W10](#w10)、[W30](#w30)、[W43](#w43) |
| T08.L03 | [W10](#w10)、[W30](#w30) |
| T09.L01 | [W11](#w11)、[W19](#w19)、[W31](#w31)、[W44](#w44)、[W45](#w45) |
| T09.L02 | [W11](#w11)、[W31](#w31)、[W43](#w43)、[W44](#w44) |
| T09.L03 | [W11](#w11)、[W31](#w31)、[W44](#w44)、[W45](#w45) |
| T10.L01 | [W12](#w12)、[W32](#w32)、[W49](#w49) |
| T10.L02 | [W12](#w12)、[W32](#w32)、[W49](#w49) |
| T10.L03 | [W12](#w12)、[W32](#w32)、[W49](#w49) |
| T11.L01 | [W01](#w01)、[W13](#w13)、[W16](#w16)、[W17](#w17)、[W33](#w33)、[W46](#w46)、[W51](#w51) |
| T11.L02 | [W33](#w33)、[W51](#w51) |
| T11.L03 | [W34](#w34)、[W51](#w51) |
| T12.L01 | [W52](#w52) |
| T12.L02 | [W53](#w53) |
| T12.L03 | [W53](#w53) |
| T13.L01 | [W18](#w18)、[W19](#w19)、[W42](#w42)、[W45](#w45)、[W46](#w46)、[W48](#w48) |
| T13.L02 | [W17](#w17)、[W19](#w19)、[W44](#w44)、[W48](#w48)、[W50](#w50) |
| T13.L03 | [W17](#w17)、[W18](#w18)、[W35](#w35)、[W47](#w47)、[W48](#w48)、[W51](#w51) |
