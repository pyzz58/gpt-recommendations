# M02 项目资料与原文定位

版本：5；状态：W03私有文件、不可变版本、DOCX/PDF来源定位、覆盖和异步Task已实现；provider/真实格式用途验证仍属于后续任务。代码位置：`backend/cra_app/documents/`。

## 对应理论和任务

理论：CRA-R003、CRA-R004、CRA-R009、CRA-R024。完整内容及出处见[理论清单](../../theory/REQUIREMENTS.md)与[对照表](../../traceability/INDEX.md)。

工作包：CRA-W03。验收场景：CRA-S03、CRA-S04。依赖模块：M01。

## 输入、输出和负责的数据

- 输入：规则或事实用途的文件/文字、文件类型、业务版本、已知适用范围。
- 输出：不可变文档版本、私有存储引用、结构化原文锚点、处理覆盖和资料缺口。
- 负责的数据：SourceDocument、DocumentVersion、SourceAnchor、ParseCoverage、Job。

## 实现方法

上传限大小、类型及解析预算，异步隔离解析，不执行宏或嵌入代码。DOCX遍历OOXML含内容控件/表格/脚注/格式，PDF保留坐标，文字保持段落位置。文件哈希发现重复但不自行裁定业务替代。

具体服务路径和字段共同遵守[接口](../API_CONTRACTS.md)及[数据模型](../DATA_MODEL.md)。实现时本模块通过公开服务调用依赖，不直接改对方数据表。异步处理、幂等、权限、版本及历史适用共同约定。

## 工作边界

收到文件不代表已经理解或已生效。逻辑章节定位和渲染页码分开；无法定位如实说明。源图片临床自动核对仅由M08接入。

## 验收与变更

本模块验收采用场景：CRA-S03、CRA-S04。场景期望见[质量验收](../QUALITY.md)，实现证据在完成任务后追加；本文件存在不等于功能实现。

新增文件格式只增加解析adapter和覆盖测试；源锚点契约改变才需更新M03/M11等消费者。

理论变更先从固定编号定位到本文件，再确认是否改变配置、服务策略、供应商adapter或数据/API契约，按[同步规则](../../traceability/SYNC_POLICY.md)留下记录。

## 2026-10-29用户决定对应修订

允许记录用户手动开始使用信息并交M03管理区间，不能以上传日替代。上次报告/track作为W06遗留整理的来源；ISF/TMF可直接展示原目录作对照，不要求先全量结构化。

详细输入、状态、边界与开发阶段按[WORKFLOW_CONTRACTS](../WORKFLOW_CONTRACTS.md)。本节与旧实现方法不一致时采用本节；设计更新不等于功能已经完成。

## v0.4技术实施补齐

来源覆盖、私有文件与异步job、历史文件及原目录接口。 实现契约见[EXECUTION_CONTRACTS.md](../EXECUTION_CONTRACTS.md)，当前任务的进入条件/交接见[完整实施路径](../../plan/IMPLEMENTATION_PATH.md)。理论和任务编号保持；本轮文档不是业务功能完成证据。

## v0.5成熟组件复用

boto3封装私有文件；React-PDF显示源PDF；Procrastinate经薄队列adapter处理通用任务。Docling仅样本验证后替换合适的解析层，保留OOXML精确来源。 具体上游、许可、替代范围和任务接法见[复用评估](../REUSE_ASSESSMENT.md)及[目录](../reuse-catalog.json)。本轮仅选型和来源核对，尚未安装/集成验证。

## W03实现记录

已接入受控OOXML DOCX解析、pdfplumber文字PDF坐标/表格、纯文本、私有本地/S3存储、Procrastinate Job/Outbox、幂等上传、不可变源版本及React-PDF源页查看。W03测试真实经过PostgreSQL和S3 HTTP接口，合成DOCX覆盖w:sdt背景标记、合并单元格、脚注和run级加粗；嵌入媒体保留为明确unsupported，不冒称已解析。XLSX/图片在W03仅作原文件保存，结构化读取分别属于W07与W08。业务生效区间、规则树、历史问题整理和报告仍未实现。
