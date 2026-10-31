# M12 模型、OCR与检索接入

版本：7；状态：W03统一端口/OCR探测、W04确定性规则提取、W08检验读取与W09受限安全解释provider已实现；尚未完成真实资料与临床用途验证。代码位置：`backend/cra_app/providers/`。

## 对应理论和任务

理论：CRA-R035、CRA-R036、CRA-R038。完整内容及出处见[理论清单](../../theory/REQUIREMENTS.md)与[对照表](../../traceability/INDEX.md)。

工作包：CRA-W03、CRA-W04、CRA-W08、CRA-W09、CRA-W14。验收场景：CRA-S02、CRA-S22、CRA-S30、CRA-S39。依赖模块：M01、M02。

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

## 2026-10-29用户决定对应修订

RecognizeLab在W08即有实际适配实现与明确支持范围；W14增强格式。DisabledProvider仅支持内部演示/临时辅助，不满足核心自动能力完成。高低可信策略由结构/来源/实测决定，不能只信模型自报置信度。

详细输入、状态、边界与开发阶段按[WORKFLOW_CONTRACTS](../WORKFLOW_CONTRACTS.md)。本节与旧实现方法不一致时采用本节；设计更新不等于功能已经完成。

## v0.4技术实施补齐

W03先探测兼容与资源，必要时隔离识别环境，W04/W08/W09实际provider评估。 实现契约见[LAB_AUTOMATION.md](../LAB_AUTOMATION.md)，当前任务的进入条件/交接见[完整实施路径](../../plan/IMPLEMENTATION_PATH.md)。理论和任务编号保持；本轮文档不是业务功能完成证据。

## v0.5成熟组件复用

现成OCR/结构候选通过统一端口隔离，不绑定供应商业务结构；核对代码/模型/引擎许可和Python/资源兼容，不能把文档能力当临床验证。 具体上游、许可、替代范围和任务接法见[复用评估](../REUSE_ASSESSMENT.md)及[目录](../reuse-catalog.json)。本轮仅选型和来源核对，尚未安装/集成验证。

## W03实现记录

已建立ParseDocument/ExtractRules/RecognizeLab/AnalyzeCase端口和显式DisabledProvider。同一合成检验图片在隔离Python3.12环境实际试装PaddleOCR 3.7.0/PaddlePaddle 3.3.1与Docling 2.145.0：macOS上两者均输出预期token和坐标，PaddleOCR更快；但GitHub Ubuntu上PaddlePaddle在oneDNN执行路径失败，Docling通过。因此当前固定Linux CI路径选择Docling作为W08候选，PaddleOCR保留为需修正推理配置的隔离替代。主应用未安装OCR候选；单图探测不构成格式覆盖、字段准确率或临床验证，详见validation/PROVIDER_FEASIBILITY.md。

## W04实现记录

新增`AnchoredRuleExtractor`，实际消费W03解析锚点并只支持已声明的结构化规则语句子集。provider不读取评估预期，输出规则树与覆盖；域服务逐条校验锚点、引文归属、数字来源和条件完整性。独立评估组比较且/或、边界、例外、三值unknown，并用同引文反例检查漏前提、丢例外、否定颠倒和且改或。该实现不是通用LLM，也未在真实方案/IB上验证；自由文本保持analysis_required。

## W08实现记录

`RoutedLabProvider`把文字PDF和图像路由到可替换adapter：文字PDF由pdfplumber直接读取表格与cell bbox；清晰PNG/JPEG由Docling 2.145.0在隔离Python 3.12子进程读取，主应用不导入其依赖。每次报告识别创建持久`lab_recognition_jobs`记录，并保存provider/model版本、SupportProfile、源定位、失败和候选数量。独立合成PNG评估实际恢复5/5行、关键字段零错误且坐标齐全；文字PDF同样5/5。两格式比较均为3条自动一致、2条集中复核。该证据不覆盖真实版式、中文、模糊图像、生产资源/模型镜像或临床用途；详见`validation/LAB_AUTOMATION_SCOPE.md`。

## W09实现记录

`LocalTransformersCaseAnalysisProvider`固定Qwen2.5-0.5B-Instruct模型提交，在隔离Python 3.12环境运行transformers 4.57.1、torch 2.7.1和safetensors 0.5.3。模型只选择服务端允许的解释模板和输入证据ID，不决定安全维度或输出处置。主服务验证JSON形状、允许代码、引用ID及医学/数值边界；任何失败均记录provider rejected并保留程序候选、未知和问题。

独立评测只把合成事实、规则证据和确定性维度送入模型，不传正确预期。3/3案例维度与问题主题正确，模型输出3/3通过grounding；伪造引用、越界医学结论、无依据数字/日期和“分级等同严重性”控制均被阻止。评估不是临床质量或节时验证，模型/依赖来源与限制见`validation/W09_DEPENDENCIES.md`和`validation/W09_STATUS.md`。
