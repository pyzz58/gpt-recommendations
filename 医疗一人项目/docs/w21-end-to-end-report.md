# W21 双项目端到端验收报告

对应：RQ-007、RQ-008、RQ-010、RQ-014、RQ-029；TR-03、TR-05、TR-07、
TR-10、TR-12、TR-14、TR-16、TR-17、TR-21；W21；AT-007、AT-008、
AT-010、AT-014、AT-029。

状态：IMPLEMENTED；mock/local 软件的完整双项目链已形成可重复验收。
live模型、真实邮箱、真实机构、真实外包执行和浏览器视觉全集仍未验证。

## 双项目链路

同一workspace下创建项目A和项目B：

1. 两个项目分别选择机会方向；
2. 项目A创建 research→audit 有界DAG，项目B创建独立单节点计划；
3. 两项目分别激活、派工和mock执行，任务只进入`submitted`；
4. 项目A的research被A25以major finding退回；
5. 重新派工后run key变化，返工上下文包含finding和上一轮output；
6. research重做并接受，下游audit自动排队和执行；
7. audit接受后项目A计划完成；
8. 项目B任务保持原状态，不因项目A返工和完成而改变；
9. 用项目B路径读取项目A计划返回404。

## 外部模拟

项目A完成：

- 合成CRO机构与工作范围；
- accepted合成报价；
- signed合成合同状态；
- active金额/范围/时间授权；
- executing工作包；
- 原始CSV交付接收、manifest和A25验收。

所有对象明确标记为合成；没有联系机构、付款、签署现实合同或取得真实实验数据。

## 重启与停止

- 原客户端关闭后重新创建FastAPI app和本地session；
- 项目A计划、项目B任务、选择决定和外部交付均从PostgreSQL恢复；
- 项目A计划仍为completed，项目B仍为submitted；
- 新停止计划激活并派工后执行stop；
- 节点进入cancelled，计划进入stopped；
- 对已停止计划再次执行返回冲突，不产生新动作。

## 真实文件

本机验收使用LibreOffice/Poppler：

- CSV原件→raw/清理数据版本→统计计划→确定性分析→A14复核；
- 生成真实XLSX、公式重算和校验；
- 下载文件hash固定；
- 重启应用后再次下载，文件hash一致。

无Office/Poppler的CI会明确skip该真实文件项，不把skip当作通过。

## 链路发现的调度修正

重复派工/返工会留下已完成任务对应的queued job。原`JobQueue.claim`遇到
第一个不可领取job即返回空，可能使同批随后的下游任务饥饿。W21修正为：

- 在一次短事务内按优先级检查最多100个候选job；
- 陈旧job标记cancelled并继续寻找下一个；
- plan inactive、task不存在、input stale和审计阻断仍按原policy拒绝；
- 找到真正可领取任务后才递增fence、创建attempt并返回claim。

双项目链回归验证了A项目已完成任务留下的陈旧job不会阻塞A下游任务，
也不会消费B项目任务。

## 路径

- 双项目测试：`services/core/tests/integration/test_w21_end_to_end.py`
- 调度：`services/core/src/medical_one_person/application/scheduling.py`
- 计划执行：`services/core/src/medical_one_person/application/plan_execution.py`
- 外部合作：`services/core/src/medical_one_person/application/external.py`
- 真实文件：`services/core/src/medical_one_person/application/exports.py`
- 页面：`apps/web/src/app/projects/[id]`

## 未覆盖

- 自动浏览器Playwright视觉与可访问性回归；
- 真实模型/邮箱/专家/机构/合同/付款/实验；
- 生产规模并发、长稳和真实主机故障；
- Microsoft Office/WPS对任意模板的像素一致性。

## 下一包

W22只有在用户配置真实provider、小额明确额度并授权有限连接后才执行；
当前没有live授权，不得用mock链路替代。
