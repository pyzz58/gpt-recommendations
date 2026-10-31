# CRA-W01—W09修复独立复核｜2026-11-01

## 结论

本轮修复有实质进展，云端证据真实对应源码，声明的合成样本/能力限制也基本准确。**但不能将原13项全部关闭：03、04、08仍有残留问题。** 独立补充的5个边界案例全部复现，涉及3项原审核发现，没有扩大到W10或新业务。

建议仅补完这三项，再继续W10。保留已正确实现的更正链、未知状态、独立中心采用、报告上下文、异步底座、检验安全入口、事件归属及有限能力声明。

## 快照与已核实证据

- 权威修复源码：`5148684064a57e50077dd32d02e76b57b2221fc4`。
- 完成状态提交：`6b2fa75fcc55d0738bbf6b97372db89b22a58dd5`；与源码提交相比只更新文档/任务证据，运行代码不变。
- [源码CI 41245438323](https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323)及[状态CI 41245900472](https://github.com/pyzz58/gpt-recommendations/actions/runs/41245900472)：各10个job成功。
- 直接读取日志确认：W09 test步骤54 passed；W08分别7/10/4项通过；实际Qwen、Docling/PDF评估通过；最终`task_evidence_checked=9`、`authoritative_verification=true`，选择器下一项W10。
- 源码提交中W01—W09为in_progress，后续状态提交重新绑定证据为verified；保留completion_history，符合重新验证约定。当前W10仍planned。
- 本轮不将本地115/116项数量作为独立核验依据；云端数据是上述直接读取结果。
- 独立诊断：[run 41247079903](https://github.com/pyzz58/gpt-recommendations/actions/runs/41247079903)，job `124672626722`，执行提交`e257602a5445b352c301958a057cce3ac1d36c0f`，临时PostgreSQL 18.6并完成迁移至0009。
- 独立诊断只增加审核探针和专属workflow，产品源码与被审5148684一致；没有修改活动分支、main、任务状态或真实资料。

**该诊断5 passed表示预期残留行为被观测到；各结果明确`acceptance_passed=false`。不能把绿色诊断当作修复完成。** 两个层级不同：子树条件是实际组件与调用路径检查；规则作用域、重复任务及过期重试涉及真实数据库/服务，重试还通过公开API复现。

原始审核：[13项发现及关闭标准](https://github.com/pyzz58/gpt-recommendations/blob/ec5ba1e4ed54ca3745d1681a47970981225bc16d/cra%20system/audit/DEVELOPMENT_REVIEW_20261101.md)。

## 原13项复核状态

| 原编号 | 本轮判定 | 依据与限制 |
| --- | --- | --- |
| 01 | 针对性修复有源码/既有CI支持 | 有效值按完整更正链折叠；单项确认、连续局部更正与批量确认有真实API回归。 |
| 02 | 针对性修复有源码/既有CI支持 | 未知例外和带单位的数值比较缺单位时保留unknown；原问题的针对性修复有效。 |
| 03 | 仍开放，独立反例复现 | 同层门槛和未知日期已修；父级前提/例外仍不传给更深子清单，独立组件反例复现。 |
| 04 | 仍开放，独立反例复现 | 共享方案可以按中心采用；但按相同rule_key一律删除项目默认，独立中心文件可静默遮掉项目要求，真实PostgreSQL复现。 |
| 05 | 按已声明范围改善 | 普通中文要求进入有来源的analysis_required候选及中英用途标签；这部分修复有效，不等于自动生成完整可执行条件，保持用户本轮明确限制。 |
| 06 | 针对性修复有源码/既有CI支持 | 参考上下限、报告日期和修订号增加独立比较，原本同标志漏范围差异的问题已修；等价值格式等减负表现仍需代表性验收。 |
| 07 | 上下文修复有效，格式有限 | 页眉上下文及行/页眉冲突保留，清晰中文合成文字PDF有实测；真实照片/复杂版式及总人工负担不在本轮已验证范围。 |
| 08 | 仍开放，独立反例复现 | Job/Outbox/队列及独立模型run有实质实现；完成任务复投仍再次识别触发IntegrityError，已过期running的公共重试入口仍409。 |
| 09 | 工程改进落实，保留发布核查 | 隔离环境完整哈希锁和Qwen权重校验已落实；Docling记录模型清单摘要。固定获准模型清单、镜像/冷启动和恢复等仍应在发布门槛逐项核实，不能将运行后摘要当运行前白名单。 |
| 10 | 已登记后续，未验设备 | iPad/电脑/弱网/跨设备已纳入W12/W15等任务；这是追踪闭环，当前没有真实设备验收。 |
| 11 | 针对性修复有源码/既有CI支持 | 一致但异常继续进入安全核查；跳过/陈旧比较区分处理，有针对性集成回归；仍非临床准确性验证。 |
| 12 | 针对性修复有源码/既有CI支持 | 可信研究法域、上游unknown继承、服务端数据分类及limited/validated=false已落实。 |
| 13 | 针对性修复有源码/既有CI支持 | 事件事实/重复实例与显式相关历史分开，有多事件、历史相关事实和空实例的回归。 |

这里没有把保留限制当成新失败。普通中文资料进入analysis_required、清晰文字PDF替代复杂照片、iPad/弱网暂未实机验收，均按用户本轮明确范围如实记录。它们不能被扩写为完整方案语义理解、医院照片普适识别或临床节时已经验证。

## 03仍开放：父级条件和例外没有传入更深子清单

实际场景：只有A成立才需做其下检查；或者上层条款已有适用豁免。父级判断已经是not_applicable或exception，子条目仍被当作独立窗口核查，产生out_of_window。

本轮已修同层gate_conditions，但递归children时仅复制子项自身的gate_conditions，没有带下父级适用上下文。独立案例分别得到：

- 父级前提不成立：parent=not_applicable，child_gate_count=0，child=out_of_window。
- 父级例外成立：parent=exception，child_gate_count=0，child=out_of_window。

源码：[calendar.py:96](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/subjects/calendar.py#L96)、[calendar.py:127](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/subjects/calendar.py#L127)、[去重:141](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/subjects/calendar.py#L141)；消费者仍将抽出的spec交给_requirement_status计算。

修复应把明确的适用前提/例外/分支上下文沿树传递。去重还须保留条件路径身份：相同窗口但属于不同分支时，不能仅按锚点和天数合并。区分“是否适用”和“待检查的窗口断言”，确保真正适用但超窗的事项仍能被发现。关闭需要实际API验证父级false、例外true、祖先unknown及兄弟分支。

## 04仍开放：中心独立文件可以静默遮掉项目要求

本轮正确放开了共享项目文件的中心采用日期。但applicable_rules构造site_rule_keys后，把所有相同rule_key的项目默认记录删除，未限定为同一项目文件/规则沿革的采用关系。

真实PostgreSQL流程中：上传并启用项目要求，再上传独立中心SOP，故意使用相同条目编号但不同要求。结果只剩site层规则，原项目rule ID消失，conflicts为空。

源码：[rules/service.py:1822](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/rules/service.py#L1822)。

应保留共享方案各中心不同启用日；将版本采用选择限定在明确同源的项目版本关系中。独立中心要求应参与三层约束，或展示真实冲突与两处原文，不能仅按相同编号默默替代项目规定。关闭须同时验证合法中心采用与独立中心规则冲突，避免修一边又恢复原限制。

## 08仍开放：完成任务复投与过期任务重试没有闭环

### 完成任务重复投递

_claim_job在succeeded时返回report.id，但process_recognition_job随后仍继续读取、调用provider和保存候选。再次写相同报告/ordinal，触发唯一约束。

在临时PostgreSQL上先完成一次，再投递相同job：provider再次调用1次，出现IntegrityError（uq_lab_observations_ordinal）。本次事务回滚后原5条候选仍在，但任务不是可安全重放的幂等操作，可能造成队列失败或额外识别成本。

源码：[状态返回:731](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/laboratory/service.py#L731)、[继续识别:780](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/laboratory/service.py#L780)、[追加候选:941](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/laboratory/service.py#L941)。

完成任务应在再次识别前返回原结果，provider调用、候选、revision和完成审计均不应增加。

### running租约已过期，公开重试仍拒绝

重试函数只看status==running，无论lease_expires_at是否过去，都返回409。独立API案例把合成任务置为过期running，POST retry-recognition得到laboratory_conflict，retryable=false。

源码：[retry_recognition:828](https://github.com/pyzz58/gpt-recommendations/blob/5148684064a57e50077dd32d02e76b57b2221fc4/cra%20system/backend/cra_app/laboratory/service.py#L828)。

需区分有效租约和失效租约，过期后通过受控重试安全重排，并隔离旧attempt的迟到结果；仍在有效租约内的任务保持并发保护。关闭需要公开API及worker投递路径的重复执行/中断恢复回归，保留原候选和CRA更正。

## 保留的能力边界

- 05：自然中文要求现在不会静默消失，也有中英用途标签。完整条件AST提取和真正减少整理负担仍需独立样本衡量，不把当前候选保留误称全面理解。
- 07：清晰中文合成文字PDF实际通过。页眉/行冲突与引用有代码；照片、旋转、模糊和复杂模板继续按声明范围推进，不要求本轮突然覆盖所有医院版式。
- 09：完整依赖哈希锁与Qwen权重运行前校验已读到。Docling当前在convert之后生成缓存模型清单摘要；在W15固定获准模型/镜像时须区分“记录本次模型”与“运行前校验获准模型”。不能用摘要代替生产模型选择/冷启动验证。
- 10：iPad、弱网及跨设备已写入后续任务；实际设备验收仍待W12/W15。没有要求扩展用药/样本OCR，也不增添不必要的离线承诺。
- 11—13：一致异常、安全维度、跳过/stale、法域/unknown继承、有限能力及事件事实选择都有实质修复。现有工程结果不等于临床准确性或总时间收益已经被证明。

## 给Codex的下一步

仅继续原03/04/08残留修复，保留已经有效的修正与用户认可的限制。按现有源码绑定机制重开受影响任务及必要依赖链、保留旧证据，新增正向API/数据库回归；修复后目标应是本诊断中的缺陷不再出现。诊断脚本断言的是“复现到了错误”，不可直接当产品通过测试复制使用。

完成这三项并给出新证据后，再进入原W10，不重新搭架构、不扩大本轮业务或临床OCR范围。当前产品分支仍保留原状态；本审查分支只是独立记录与证据。

机器可读复核表、原始观察及关闭标准：[REMEDIATION_RECHECK_20261101.json](REMEDIATION_RECHECK_20261101.json)。简短指令：[CODEX_RECHECK_FOLLOWUP_20261101.md](CODEX_RECHECK_FOLLOWUP_20261101.md)。
