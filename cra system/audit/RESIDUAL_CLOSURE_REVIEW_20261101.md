# 三项残留修复关闭复核｜2026-11-01

## 结论

**原04、08可以按本轮工程范围关闭；原03的祖先前提/例外修复有效，但分支指向子清单的路径仍未完整修复。** 不建议现在将三项全部关闭并直接进入W10。只补这一处，不重做04/08，也不扩大到其他临床功能。

此次读到的两次开发者CI均成功，源码绑定也真实有效。独立增加的正向验收在相同产品源码上得到**8 passed、3 failed**，进一步确认测试覆盖缺口。失败来自正确行为断言，不是依赖安装、迁移或API设置错误。

## 审核版本与证据

- 修复源码：`f66750c9fac58dbf2e03189582a3544fc039bfd4`。
- 完成状态：`fa8cd479b0913a2241b3a6ab5145af462c8153d9`；相对源码只改文档/任务证据，产品运行代码不变。
- [源码CI 41248250769](https://github.com/pyzz58/gpt-recommendations/actions/runs/41248250769)：10个job成功。
- [状态CI 41248689830](https://github.com/pyzz58/gpt-recommendations/actions/runs/41248689830)：10个job成功。
- 直接读取源码job日志：W04为17项、W05为10项、W08为7+13+4项、W09为60项；实际规则/Docling/Qwen评估按声明子集通过。状态baseline日志为task_evidence_checked=9、authoritative_verification=true，下一项W10。
- 本地122项为开发者记录，本复核不冒称自己执行了本地完整回归。
- [独立正向验收 41249314958](https://github.com/pyzz58/gpt-recommendations/actions/runs/41249314958)，job `124679301464`，执行提交`8345b2d6ec81969fd977cc411222b59a2febe6e2`。只增加审核测试和专属workflow，运行产品与f66750c相同。
- 独立环境：临时PostgreSQL18.6，迁移至0009，Python3.13.15和已有锁定依赖；没有模型推理或真实临床资料。

与上次“5 passed表示错误复现成功”不同，本次测试明确断言**正确行为**。所以三个失败就是尚未通过验收，不能转写成成功。

## 各项判断

| 原项 | 判断 | 直接依据 |
| --- | --- | --- |
| 03 | 部分有效，仍开放一处 | 原祖先条件及兄弟同窗两项API回归独立重跑通过；新增分支目标结构中三项失败 |
| 04 | 关闭针对性工程问题 | 采用选择改为同一Rule身份；同源中心启用与独立同编号项目/中心规则并存两项PostgreSQL回归均通过 |
| 08 | 关闭针对性工程问题 | 成功复投提前返回、公开过期重试/活跃保护、旧attempt不能覆盖CRA更正三项回归均独立通过 |

七项既有修复回归全部通过，新增四项中一个真条件控制用例通过，总计8通过、3失败。这些关闭只涉及已明确工程问题，不代表所有临床用途、队列场景或规则形式已穷尽验证。

## 原03的唯一剩余范围：分支选择没有稳定传到目标子清单

临床示例采用纯合成要求：**只有条件A成立，才进入子清单，核查某项检查是否在锚点前后2天完成。**

同样的要求可以表示为“分支直接指向带日期窗口的子项”，也可以表示为“分支指向一个子清单，日期窗口在其下一层”。当前RuleBranch有target_node_ids，RuleNode可有独立trigger/children；公开确认接口接受这些结构并保存为complete。本测试通过上传、规则确认、事实导入和访视要求API执行，没有直接篡改业务表或预制API返回值。

| 结构/事实 | 正确预期 | 实际结果 |
| --- | --- | --- |
| 分支直接指向日期子项，A=true，实际超窗 | 保留该检查并显示out_of_window | 对应要求数量为0，窗口消失 |
| 分支指向容器，日期项在下一层，A=false | not_applicable | out_of_window |
| 同上，A未提供 | unknown_applicability | out_of_window |
| 同上，A=true，实际超窗 | out_of_window | out_of_window，控制用例通过 |

源码位置：

- [calendar.py:164](https://github.com/pyzz58/gpt-recommendations/blob/f66750c9fac58dbf2e03189582a3544fc039bfd4/cra%20system/backend/cra_app/subjects/calendar.py#L164)收集全部branch_targets。
- [calendar.py:174](https://github.com/pyzz58/gpt-recommendations/blob/f66750c9fac58dbf2e03189582a3544fc039bfd4/cra%20system/backend/cra_app/subjects/calendar.py#L174)仅因子项被某分支指向就suppress_trigger，未核对该日期trigger是否只是分支的重复表达，导致独立子项窗口也被删掉。
- [calendar.py:172](https://github.com/pyzz58/gpt-recommendations/blob/f66750c9fac58dbf2e03189582a3544fc039bfd4/cra%20system/backend/cra_app/subjects/calendar.py#L172)传下branch_gates，但该变量只有祖先门槛、当前前提/例外及当前非日期trigger，没有按target_node_ids加入实际选择该目标的branch.condition。
- 默认提取器常把branch.condition复制为子项trigger，因此部分标准生成树可以绕过缺口；现有API契约并不要求所有确认树都重复表达同一条件。依赖这种巧合不能称为分支条件完整继承。

本轮修复应按实际分支到目标的关系保留选择条件，并保留目标自身日期义务。只有已证明同一日期条件的重复表达才可消重；不能一律删掉被指向子项的trigger。多条路径指向同一目标时按明确的规则树语义组合，不误作全部条件同时成立，也不凭空添加分支。

如果某种结构确实不在当前支持范围，应在确认/执行处明确拒绝或analysis_required，不能接受为complete后静默遗漏。这里不要求任意中文文本自动解析或扩展条件语言，只要求已有有限AST与公开接口正确使用。

关闭需要本次四项正向API用例全部通过，同时保留原七项回归通过，并按既有机制重新绑定受影响源码证据。当前正确行为测试可直接复用：[closure_branch_20261101.py](probes/closure_branch_20261101.py)。

## 防复发要求的接入情况

之前已交付[40c8d2f文档提交](https://github.com/pyzz58/gpt-recommendations/commit/40c8d2f2dfb200afe6975656c3c315f9986fbc14)和[防复发规范](https://github.com/pyzz58/gpt-recommendations/blob/40c8d2f2dfb200afe6975656c3c315f9986fbc14/cra%20system/architecture/REGRESSION_PREVENTION.md)，分支audit/cra-regression-prevention-20261101。

截至本次读取fa8cd47，开发分支尚无REGRESSION_PREVENTION.md；AGENTS仍为旧入口，next_task和task_evidence未增加该文档规定的审核连接。因此本次确实增加了针对性回归，却尚未完成此前要求的整体防复发规范接入。它属于已有后续工程要求，**不否定本次04/08的修复，也不作为新临床缺陷重新编号**。

后续选择性带入规范与接手要求，保留最新修复/任务证据，避免机械覆盖新状态；再将实际测试和工程检查绑定。不要把“文档已经在GitHub另一个分支”说成“开发流程已自动执行”。

## 保留范围与下一步

普通中文analysis_required、清晰文字/合成检验图像、设备/弱网/跨设备在W12/W15、临床性能及总工作量尚未验证，继续按用户已经认可的范围记录，不作为新增阻断项。

只继续原03的分支目标残留；04/08保持关闭及持续回归。同步原防复发要求，完成这一处的正确行为与源码绑定复核后，再按原计划进入W10。此次审阅没有修改产品、开发分支、main或tasks.json，也没有启动W10。

机器记录：[RESIDUAL_CLOSURE_REVIEW_20261101.json](RESIDUAL_CLOSURE_REVIEW_20261101.json)。
给Codex：[CODEX_BRANCH_GATE_FOLLOWUP_20261101.md](CODEX_BRANCH_GATE_FOLLOWUP_20261101.md)。
