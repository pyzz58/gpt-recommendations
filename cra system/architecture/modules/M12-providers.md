# M12 模型、OCR与检索接入

版本：1；状态：已设计，完整实现待工作包完成。计划代码位置：`backend/cra_app/providers/`。

## 对应理论和任务

理论：CRA-R035、CRA-R036、CRA-R038。完整内容及出处见[理论清单](../../theory/REQUIREMENTS.md)与[对照表](../../traceability/INDEX.md)。

工作包：CRA-W03、CRA-W04、CRA-W09、CRA-W14。验收场景：CRA-S02、CRA-S22、CRA-S30。依赖模块：M01、M02。

## 输入、输出和负责的数据

- 输入：带授权范围、用途、版本和预算的解析/识别/分析请求。
- 输出：统一结构候选、来源锚点、错误/不可用状态和必要运行元数据。
- 负责的数据：ProviderConfig、ProviderRun、Job输入输出摘要。

## 实现方法

定义ParseDocument、ExtractRules、RecognizeLab、AnalyzeCase四个端口；provider只提供能力，业务校验在调用方。最小必要数据、输出结构验证、有限重试、超时、幂等和费用限制。未配置使用显式DisabledProvider与人工路径。

具体服务路径和字段共同遵守[接口](../API_CONTRACTS.md)及[数据模型](../DATA_MODEL.md)。实现时本模块通过公开服务调用依赖，不直接改对方数据表。异步处理、幂等、权限、版本及历史适用共同约定。

## 工作边界

供应商不能直接改业务库、发送邮件、提交Query或关闭任务。不把整个项目上传换取方便，不把材料里的文字当工具指令。未经许可不启用新的外部服务。

## 验收与变更

本模块验收采用场景：CRA-S02、CRA-S22、CRA-S30。场景期望见[质量验收](../QUALITY.md)，实现证据在完成任务后追加；本文件存在不等于功能实现。

添加供应商实现只改adapter及配置测试；输出契约变化才影响业务消费者。选择供应商和数据处理条件在实际接入前核实。

理论变更先从固定编号定位到本文件，再确认是否改变配置、服务策略、供应商adapter或数据/API契约，按[同步规则](../../traceability/SYNC_POLICY.md)留下记录。
