# W01—W18 直接依赖、来源与许可

本表记录直接依赖。`pnpm-lock.yaml` 和 `services/core/uv.lock` 固定完整解析结果；
`services/core/requirements.lock` 是容器安装使用的带哈希导出。没有复制第三方的
技能、模板或论文全文。

| 组件 | 版本来源 | 许可 | 用途 | 验证状态 |
| --- | --- | --- | --- | --- |
| Next.js | npm registry `16.4.3` | MIT | 本地网页 | 构建 |
| React / React DOM | npm registry `19.3.1` | MIT | 网页组件 | 构建 |
| TypeScript | npm registry `6.0.3` | Apache-2.0 | 类型检查 | 类型检查；兼容 Next lint 链 |
| ESLint / eslint-config-next | npm registry `9.39.5` / `16.4.3` | MIT | 静态检查 | lint |
| FastAPI | PyPI `0.162.0` | MIT | HTTP API | pytest |
| Pydantic / settings | PyPI `2.14.2` / `2.16.2` | MIT | 合同与配置 | pytest |
| jsonschema | PyPI `4.26.0` | MIT | Knowledge合同完整验证 | 15个正反例 |
| pypdf | PyPI `6.21.4` | BSD-3-Clause | PDF文本提取 | 合成PDF |
| python-docx | PyPI `1.2.0` | MIT | DOCX段落/表格 | 合成DOCX |
| python-pptx | PyPI `1.0.2` | MIT | PPTX可编辑摘要与形状 | 6页合成演示、重开与边界检查 |
| openpyxl | PyPI `3.1.5` | MIT/Expat | XLSX公式与缓存值分离 | 合成XLSX |
| Pillow | PyPI `13.0.0` | HPND | 图片校验与尺寸 | 合成PNG |
| reportlab | PyPI `5.1.0` | BSD-3-Clause | 真实PDF报告生成、CJK嵌入 | 合成PDF重开/预览 |
| LibreOffice headless | 本机LibreOfficeDev `26.8.0.0.alpha0` | MPL-2.0/LGPL-3.0（组件许可需按发布物复核） | Office→PDF与XLSX实际重算 | 原生命令已运行；固定生产镜像未验收 |
| Poppler `pdftoppm` | Codex primary runtime | GPL-2.0-or-later（单独可执行程序） | PDF逐页PNG渲染 | 原生命令已运行；分发方式需复核 |
| Arial Unicode系统字体 | macOS系统字体 | 未随仓库分发；使用/嵌入许可需在发布环境复核 | Office CJK fontconfig与PDF字体 | 本机合成预览；可由`MEDICAL_ONE_OFFICE_PDF_FONT_PATH`替换 |
| 本地词法索引 | PostgreSQL文本/JSONB、应用层分词 | PostgreSQL License / 本项目 | W08检索与快照 | 合成中英文资料实测 |
| 机会/简报合同 | Pydantic `2.14.2`、JSON Schema 2020-12 | MIT / 本项目 | W09候选、概率、成本和科学简报 | 4个导出Schema、3类合成候选及边界测试 |
| 项目/知识页面 | Next.js `16.4.3`、React `19.3.1`、Server-Sent Events | MIT / WHATWG标准 | W10项目、岗位、任务、机会和知识界面 | lint/typecheck/build；桌面与390px人工联调 |
| 本地页面会话 | Web Cookie、PostgreSQL session摘要 | 本项目/PostgreSQL License | W10 development/mock owner会话 | HttpOnly、401/重试、跨Origin写拒绝测试 |
| DAG与审核 | Pydantic `2.14.2`、PostgreSQL行锁/JSONB | MIT / PostgreSQL License | W11计划、派工、审核、暂停与返工上限 | 真实PostgreSQL工作流、迁移往返和48条RLS策略 |
| 三领域流程配置 | PyYAML `6.0.3`、Pydantic `2.14.2` | MIT | W12宠物药/IVD/器械阶段与判据 | 3份严格配置、角色/依赖校验、SHA-256固定 |
| 数据与统计 | Python `statistics`、openpyxl `3.1.5` | PSF / MIT-Expat | W13 CSV/XLSX、描述/均值差/Wilson区间 | 合成数据、清理版本、hash、API与页面测试 |
| Office/PDF导出 | python-docx `1.2.0`、python-pptx `1.0.2`、openpyxl `3.1.5`、reportlab `5.1.0`、pypdf `6.21.4` | MIT / MIT-Expat / BSD-3-Clause | W14结构化报告、公式重算、预览和不可变导出版本 | 四种真实文件重开、57条策略、API与页面；Microsoft Office/WPS未测 |
| 模拟邮件/授权 | Python `3.12`标准库、Pydantic `2.14.2`、PostgreSQL JSONB/RLS | PSF / MIT / PostgreSQL License | W15 owner inbox、草稿、附件hash、发送授权、幂等账本和不确定核对 | 合成收件、64条策略、API/页面与浏览器；无真实邮箱或网络 |
| 外部合作/专业记录 | Pydantic `2.14.2`、PostgreSQL JSONB/NUMERIC/RLS | MIT / PostgreSQL License | W16机构、专家、工作范围、报价、合同、交付、注册/专利/财务/商业台账 | 合成外部记录、73条策略、API/页面；无真实机构事实 |
| 独立审计/合成评测 | Pydantic `2.14.2`、PostgreSQL JSONB/SHA-256/RLS、JSON Schema 2020-12 | MIT / PostgreSQL License / 本项目 | W17三类审计快照、A25/A26确定性规则、阻断/处置、7案合成回归与两个导出Schema | 98项核心测试、迁移往返、76条策略、API/页面；不证明科学能力 |
| 离线/恢复 | cryptography `46.0.3`、cffi `2.1.1`、pycparser `3.12`、PostgreSQL 17.6 | Apache-2.0 OR BSD-3-Clause / MIT / BSD-3-Clause / PostgreSQL License | W18 AES-256-GCM备份、scrypt密钥派生、回收站、索引重建和输入失效 | mock/本地真实PostgreSQL、加密/篡改/错误口令与隔离恢复测试；活动DB重放和异地恢复未测 |
| PyYAML / type stubs | PyPI `6.0.3` / `6.0.12.20261030` | MIT | 26岗YAML配置与类型检查 | 26岗加载 |
| Uvicorn | PyPI `0.54.0` | BSD-3-Clause | ASGI 服务 | 服务启动 |
| SQLAlchemy | PyPI `2.1.6` | MIT | PostgreSQL ORM、事务与行锁 | W02—W09真实数据库测试 |
| Alembic | PyPI `1.20.1` | MIT | 版本迁移与回滚 | W02—W09迁移上/下及重应用 |
| psycopg | PyPI `3.3.6` | LGPL-3.0 | PostgreSQL 驱动 | W02—W09真实数据库测试 |
| python-multipart | PyPI `0.0.32` | Apache-2.0 | 后续上传表单 | 仅安装 |
| pytest / httpx | PyPI `9.2.0` / `0.28.1` | MIT / BSD-3-Clause | API 测试 | 已运行 |
| Ruff / mypy | PyPI `0.17.3` / `2.4.1` | MIT | 检查 | 已运行 |
| PostgreSQL 17.6（测试运行时） | Theseus release `17.6.1`，macOS arm64 | PostgreSQL License / Theseus 发布许可 | W02真实数据库验收 | 临时目录运行，不提交 |
| PostgreSQL RLS/应用角色 | PostgreSQL 17.6内置能力 | PostgreSQL License | W03项目隔离 | 原生PostgreSQL实测 |
| PostgreSQL队列/预算 | PostgreSQL行锁、SKIP LOCKED、JSONB、NUMERIC | PostgreSQL License | W04可靠调度和并发预算 | 原生PostgreSQL实测 |
| Agent运行 | 本项目自建Runner + fake provider | 本项目；不复制第三方技能 | W05独立上下文与结构化交付 | 26岗mock合同测试 |
| 内置技能执行 | 本项目自建numeric summary/artifact hash | 本项目；未复制第三方技能目录 | W06技能合同、授权与输出验收 | 2项ready并实测 |
| 容器沙箱策略 | OCI/Docker CLI参数合同 | 不打包第三方镜像 | W06资源与挂载策略 | 仅参数单测；Docker未安装 |

官方来源：

- Next.js：https://nextjs.org/docs
- React：https://react.dev/
- FastAPI：https://fastapi.tiangolo.com/
- Pydantic：https://docs.pydantic.dev/
- SQLAlchemy：https://docs.sqlalchemy.org/
- Alembic：https://alembic.sqlalchemy.org/
- PostgreSQL：https://www.postgresql.org/
- PostgreSQL portable binary：https://github.com/theseus-rs/postgresql-binaries/releases/tag/17.6.1
- Python：https://www.python.org/
- Node.js：https://nodejs.org/
- python-pptx：https://python-pptx.readthedocs.io/
- LibreOffice：https://www.libreoffice.org/
- Poppler：https://poppler.freedesktop.org/

依赖存在和锁文件固定不证明它们已适合完整医疗研发业务；医疗、权限、文件、
调度和科学验证仍需对应工作包的实际测试。

本机Arial Unicode字体来自macOS系统安装，未提交仓库。当前合成输出的PDF会嵌入
所选字体；对外分发前必须按实际字体许可和目标机器单独复核，并可通过环境变量换成
已获准使用的CJK字体。LibreOffice和Poppler作为外部程序调用，不因本项目MIT代码
许可而改变其自身许可与分发义务。
