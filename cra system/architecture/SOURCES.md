# 技术依据与核对记录

核对日期：2026-10-29。以下是官方文档或项目原始仓库，用于支持技术选型；不是完整适用性验证，不引用未经取得的IQVIA/ICON内部SOP。

| 来源 | 支持的选择 | 使用边界 |
| --- | --- | --- |
| [GitHub Codespaces](https://docs.github.com/en/codespaces/overview) | 云开发环境及仓库配置 | 不据此宣称适合作为稳定临床生产托管 |
| [FastAPI SQL数据库教程](https://fastapi.tiangolo.com/tutorial/sql-databases/) | Python API与SQL持久化可组合 | 教程不是本系统数据模型或权限实现 |
| [SQLAlchemy版本计数](https://docs.sqlalchemy.org/en/20/orm/versioning.html) | 乐观版本检查和并发更新控制 | ORM版本计数不覆盖所有批量SQL路径，服务层仍需明确expected_revision |
| [PostgreSQL行级策略](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) | 行级权限及默认拒绝策略 | 超级用户/绕过角色及表拥有者例外需处理，不可只打开RLS就声称隔离完成 |
| [Vite官方指南](https://vite.dev/guide/) | React/TypeScript开发与构建候选 | 实现时核对Node兼容并生成锁文件 |
| [PaddleOCR原始仓库](https://github.com/PaddlePaddle/PaddleOCR) | OCR及文档结构识别候选，Apache-2.0 | 需实测中文检验及部署，不采用宣传准确率作为临床结果 |
| [pdfplumber原始仓库](https://github.com/jsvine/pdfplumber) | 字符/坐标/表格提取，MIT | 优先机器生成PDF；扫描文件仍需其他解析路径 |
| [官方Python开发容器](https://github.com/devcontainers/images/tree/main/src/python) | Python 3.13 bookworm开发镜像 | 开发容器版本在实际启动后核对，发布时进一步固定 |
| [python-docx官方文档](https://python-docx.readthedocs.io/) | DOCX适配候选 | 尚未完成本轮实现验证，必须覆盖OOXML控件与格式 |
| [openpyxl官方文档](https://openpyxl.readthedocs.io/) | Excel适配候选 | 尚未锁定版本；宏、公式及缓存值需单独检查 |

临床和法规依据应来自项目实际适用资料及原理论维护页。公开仓库不复制真实方案原件、整本标准或客户专有内容。项目实际标准版本由规则配置确定，不能因技术资料较新就替换研究采用版本。
