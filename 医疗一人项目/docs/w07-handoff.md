# W07 资料原件与来源接手说明

对应：RQ-011、RQ-026、RQ-034；TR-03、TR-04、TR-09、TR-10、TR-13、TR-16、
TR-18、TR-20、TR-25；W07；AT-011、AT-026、AT-034的主要基础子项。

状态：IMPLEMENTED，未VERIFIED。上传、原件、解析和来源政策已有真实PostgreSQL
及格式测试；词法索引、检索快照、引用影响属于W08，上传界面属于W10，删除和
备份恢复属于W18，完整CRO数据闭环属于W21/W24。

## 已交付

- 四类专业来源政策：生物医学原始、监管官方、专利官方和项目私有。
- PubMed缓存XML元数据适配器；普通网页搜索强制关闭，预印本保留单独标记。
- Knowledge合同在运行时用Draft 2020-12完整验证，全部15个合成正反例通过。
- 项目私有库、分片upload session、part range/hash与断点状态。
- 8MiB工程分片、100MiB单文件、500MiB批次默认边界可配置。
- 上传重叠/改内容冲突、错误hash、缺片、过期、路径伪装和格式签名不匹配拒绝。
- commit幂等：重试返回原version/job；内容按SHA-256复用blob但文档ACL独立。
- 原件使用内容寻址不可变存储；上传staging成功后清理，失败保留可恢复状态。
- 文档、版本、解析、段落和表格分开；同内容跨逻辑文件不覆盖原记录。
- 四维状态分别存储：ingest/evidence/version/access。
- TXT/Markdown、CSV、PDF、DOCX、XLSX、PNG/JPEG、EML解析及定位。
- PDF页、DOCX段/表、XLSX sheet/cell、CSV表、文本行/字符、邮件body/headers均有locator。
- 无文本PDF和图片保留原件并进入partial，明确OCR未配置；PPTX保留原件并标部分解析。
- 解析完成但未建索引时版本进入indexing，不冒充ready；证据状态保持unreviewed。
- W07新增11张表受RLS保护；累计32条策略。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
make schema
```

本轮结果：

```text
43 passed
Formats: TXT/MD, CSV, PDF, DOCX, XLSX, PNG, EML
Upload: resume, replay, overlap, checksum, incomplete and duplicate content tested
Ruff: all checks passed
mypy: no issues found in 65 source files
Alembic: W07 rollback and W02-W07 reapply passed
PostgreSQL: 32 RLS policies
Next.js: lint, TypeScript and production build passed
```

## 尚未完成

- 没有外部PubMed实时请求、付费全文或跨出版商下载；只验证缓存XML适配器。
- OCR/Tesseract、OCR置信度和扫描PDF全文尚未配置。
- W08才实现词法索引、检索、Citation、retrieval snapshot、版本影响和claims。
- W10才实现拖拽/文件队列/资料详情界面；当前只有服务层，不是完整HTTP上传/UI。
- W18才实现回收站、引用保护、加密备份和恢复演练。
- 页面“专业来源”显示not_checked，因为政策已加载但活体渠道未连接。
