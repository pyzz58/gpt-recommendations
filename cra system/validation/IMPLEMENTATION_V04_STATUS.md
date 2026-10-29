# v0.4完整实施路径与工程验证

日期：2026-10-29。实现/测试对象：`70a09ea1898ac1f6cb3cdde7ce3cf26b4300b18f`，复核业务基准：`cd3d36ecbdf57ae2f011c2b04e1174321624472b`。

[GitHub Actions证据](https://github.com/pyzz58/gpt-recommendations/actions/runs/40856683422)，job 123389302472，completed/success。

## 已实际完成

- 原最高说明只读复核、45条固定理论和最新八点决定对照；未修改临床理论。
- 八阶段、七个可观察里程碑和16份任务卡，增加技术输入、进入条件、交接及专属CI要求；22份生成视图同步通过。
- 统一输出/最低输入/版本与异步执行、检验自动化完整路径、验证/发布的技术设计。
- 实际工程工具：源码/规范/样本绑定完成证据、GitHub专属run/job/steps校验、阶段/引用/profile检查。
- 40项工程单元测试通过，含子目录源码绑定的正向合成Git案例及错误证据反例；既有合成监查示例通过。
- 原空文件加自报完成的诊断由accepted变为rejected_by_current_guard；硬依赖倒置边为空。
- 下一项仍CRA-W01/ready，业务任务没有被改成完成。

## 证据的限制

当前没有verified业务任务，运行中的权威证据检查记录task_evidence_checked=0；真实GitHub业务任务正向证据将在W01完成后验证。本轮GitHub API边界测试使用模拟响应，不能把模拟正向案例称真实W01通过。历史W00只保留工程bootstrap身份。

实际OCR/模型、真实格式性能、数据库/API/完整UI、40个完整业务场景、总时间和获授权试用均待相应任务实现。原10个审查项仍open；AUD-001已有负向修补证据，首个真实W01正向案例待补，不伪造关闭。

## 当前交付入口

[第一性原理复核](../audit/FIRST_PRINCIPLES_REVIEW_V04.md) → [完整实施路径](../plan/IMPLEMENTATION_PATH.md) → [Codex入口](../CODEX_START_HERE.md) → W01任务卡。后续从实际代码逐项推进。
