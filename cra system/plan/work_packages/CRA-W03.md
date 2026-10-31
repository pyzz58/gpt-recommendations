# CRA-W03 实现资料接收、解析和来源定位

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：verified；分支路线：v1a。
前置：CRA-W02。必须按实际verified状态核实。

## 临床工作目标

资料上传后能定位原文，知道哪些内容已读取、哪些仍缺失。

## 对应理论和模块

理论：[CRA-R003](../../theory/REQUIREMENTS.md#cra-r003)、[CRA-R004](../../theory/REQUIREMENTS.md#cra-r004)、[CRA-R009](../../theory/REQUIREMENTS.md#cra-r009)、[CRA-R024](../../theory/REQUIREMENTS.md#cra-r024)、[CRA-R036](../../theory/REQUIREMENTS.md#cra-r036)、[CRA-R038](../../theory/REQUIREMENTS.md#cra-r038)

模块：[M02](../../architecture/modules/M02-documents.md)、[M12](../../architecture/modules/M12-providers.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/documents/models.py` | code | 文档版本、锚点和覆盖 |
| `backend/cra_app/documents/service.py` | code | 用途、上传和版本 |
| `backend/cra_app/documents/parsers/docx.py` | code | 完整OOXML解析 |
| `backend/cra_app/documents/parsers/pdf.py` | code | 文字PDF定位 |
| `backend/cra_app/documents/api.py` | code | 资料及原文接口 |
| `backend/cra_app/providers/ports.py` | code | 解析/提取/识别/分析端口 |
| `backend/cra_app/providers/disabled.py` | code | 未配置能力返回 |
| `backend/cra_app/platform/jobs.py` | code | 持久作业与重试 |
| `web/src/features/documents/DocumentWorkspace.tsx` | code | 资料与原文界面 |
| `tests/integration/test_documents.py` | test | 解析、覆盖、版本和作业 |
| `validation/PROVIDER_FEASIBILITY.md` | document | OCR/模型适配安装与资源探测、授权范围和待验证项 |
| `tests/fixtures/manifest.json` | config | 合成资料及开发/独立评估分组和正确预期定位 |
| `backend/cra_app/providers/probe.py` | code | 仅合成资料的依赖/资源与候选输出探测入口 |
| `backend/cra_app/documents/storage.py` | code | boto3私有文件薄适配，不暴露永久公开链接 |
| `web/src/components/SourcePdfViewer.tsx` | code | React-PDF源文件展示及授权/定位边界 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 上传返回job_id；SourceAnchor包含文档版本及章节、节点、表格/脚注或坐标。
- 原文件私有，DocumentVersion不可覆盖；不把上传时间当业务生效日期。
- DocumentVersion分别保存发布时间、上传时间和用户手动的开始使用信息；实际适用区间由M03管理。目录可仅作原文件对照。
- QueueAdapter封装Procrastinate，业务Job/授权/版本/Outbox不交给队列决定；S3 SDK不替代范围/保留/版本策略。

## 进入条件与交接

阶段：P2；CI profile：CRA-W03

- 进入：API、私有文件接口和持久事务可用。
- 交接：文件/锚点/作业接口，合成资料集和OCR依赖/资源可行性探测记录。

技术输入：[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[LAB_AUTOMATION.md](../../architecture/LAB_AUTOMATION.md)、[REUSE_ASSESSMENT.md](../../architecture/REUSE_ASSESSMENT.md)


## 实现步骤

1. 增量迁移来源、锚点、覆盖、业务Job/Outbox；私有文件经boto3薄适配，通用队列/worker/锁/重试优先Procrastinate，不从头写队列引擎。
2. 分别记录规则/事实用途和适用范围；文件哈希发现重复但不裁定替代关系。
3. 遍历DOCX的w:sdt、合并单元格、脚注和字符格式；PDF保留坐标，失败页如实显示。
4. 实现有限重试、幂等、资源预算及worker重新鉴权，不执行宏或文档内指令。
5. 界面展示版本、缺口和可回查原文，供规则提取复用。
6. 保留历史监查报告/track的来源定位，供W06整理遗留；目录无需先全量结构化也能查看。
7. 及早用纯合成检验文件探测OCR的Python/运行库/CPU内存与定位输出，不在此实现完整核对；依赖冲突时隔离OCR适配运行环境，保留原业务接口。
8. 建立docs/Excel/图片/模板的合成样本清单与预期，保留独立评估分组；不得把开发结果当独立验证。
9. 核对Procrastinate所选发布版/驱动的入队事务能力；未经共享事务验证时使用业务写入+Outbox同事务，再relay入队并幂等处理。队列只传内部ID，worker重查授权和版本。
10. 以相同少量纯合成样本比较PaddleOCR结构管道与Docling候选；记录精确定位/表格/条件覆盖、模型许可、运行兼容和负担，选合适的一个，不默认双装。
11. 源PDF查看复用React-PDF并本地打包worker/字库，保留SourceRef页和坐标；不是用PDF查看器替代OCR或完整DOCX解析。

## 验证命令

available表示当前已有入口；to_implement表示本任务必须先实现该入口，不能现在就声称已经运行。进入后续阶段使用合成数据和临时服务。

- [available] 理论/技术/任务卡同步

```bash
python3 tools/check_traceability.py
```

- [available] 现有基础与反例检查

```bash
python3 -m unittest discover -s tests -v
```

- [available] 合成文档及作业

```bash
uv run --frozen pytest -q tests/integration/test_documents.py
```

- [available] 可安装、可运行的识别候选探测，不代表全格式准确性

```bash
uv run --frozen python -m cra_app.providers.probe --synthetic
```

- [available] 资料接口、前端类型及PDF查看器契约

```bash
npm --prefix web run api:check
```

- [available] 资料界面测试、类型和构建

```bash
npm --prefix web test && npm --prefix web run typecheck && npm --prefix web run build
```

## 完成标准

原工作包验收：DOCX/PDF/文字解析保留章节、表格、脚注、格式和处理覆盖；异步作业可重试，缺件可登记。

- 脚注和加粗等有意义格式不丢失。
- 解析失败、背景、未处理分别记录，不以条目多表示提取完整。
- 重试不重复建版本，越权资料不可读取。

关联完整场景：CRA-S02、CRA-S03、CRA-S04。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不把所有临床源文件纳入逐字段自动OCR。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
