# W01—W17 工具链与环境兼容矩阵

记录日期：2026-10-31（Pacific/Auckland）。本表只记录本机实测和在官方注册表
核对的版本，不表示其他操作系统或架构已经通过。

| 项目 | 固定版本/状态 | 来源 | 当前验证 |
| --- | --- | --- | --- |
| 主机 | macOS 27.2，Darwin 27.2.0，arm64 | 本机 `uname` / `sw_vers` | 已识别 |
| CPU/内存/磁盘可用量 | 10 核 / 16 GiB / 约 234 GiB | 本机系统命令 | 已识别 |
| Python | CPython 3.12.14 | uv 管理的官方 CPython | 原生 mock 运行 |
| Node.js | 22.23.4 | pnpm runtime 下载的官方构建 | 网页安装、检查、构建 |
| pnpm | 11.25.0 | 当前环境已有 | 锁文件生成与安装 |
| Next.js | 16.4.3 | npm registry | 网页构建 |
| React | 19.3.1 | npm registry | 网页构建 |
| TypeScript | 6.0.3 | npm registry | 类型检查；避免尚未被 Next lint 链支持的 7.x |
| ESLint | 9.39.5 | npm registry | Next 插件兼容范围内固定 |
| PostgreSQL | 17.6 native（Theseus构建17.6.1） | 官方发布归档；SHA-256 `876c0255…2f3e` | 已运行迁移、事务和重启恢复 |
| PostgreSQL 容器 | 17.6-alpine，镜像摘要 `sha256:ef257d85…ee94` | Docker Registry | 仅固定版本，未启动 |
| PostgreSQL 应用角色 | `medical_one_app` | W03迁移 | 非superuser、无BYPASSRLS、9条RLS策略 |
| PostgreSQL任务/预算队列 | PostgreSQL 17.6 locking/JSONB/Numeric | W04迁移 | 18条RLS策略；SKIP LOCKED、fence和预算并发实测 |
| Agent配置/运行 | PyYAML 6.0.3；Pydantic 2.14.2 | W05目录与schema | 26岗加载、派发、mock结构化输出和20条RLS策略 |
| 技能注册/执行 | 本项目builtin runner；12项skill合同 | W06目录 | 2项ready、10项明确不可用、21条RLS策略 |
| 文件解析 | pypdf 6.21.4 / python-docx 1.2.0 / openpyxl 3.1.5 / Pillow 13.0.0 | PyPI | TXT/MD、CSV、PDF、DOCX、XLSX、图片、EML |
| Schema验证 | jsonschema 4.26.0 | PyPI | knowledge合同15个合成正反例 |
| 本地词法索引 | PostgreSQL文本/JSONB + ILIKE | W08应用服务 | 中英文原文定位、快照、citation、claims/version影响 |
| 机会比较与选择 | Pydantic 2.14.2 + PostgreSQL JSONB/RLS | W09应用服务 | 三领域合成候选、版本、概率/成本约束、owner选择、幂等与45条RLS策略 |
| 项目/知识界面 | Next.js 16.4.3 / React 19.3.1 / EventSource | W10 Web与API | 项目、26岗、任务、机会、上传、检索、下载与SSE；桌面/390px人工联调 |
| 本地页面会话 | HttpOnly cookie + PostgreSQL SHA-256 session摘要 | W10 API | development/mock本地owner会话、401重试与非allowlist写Origin拒绝 |
| 计划/审核状态机 | Pydantic 2.14.2 + PostgreSQL行锁/JSONB/RLS | W11应用服务和页面 | 有界DAG、派工、mock执行、TaskVersion审核、返工上限、暂停恢复与48条策略 |
| 三领域专业流程 | YAML + Pydantic 2.14.2 + workflow SHA-256 | W12配置/API/页面 | 3领域×4阶段、岗位/输出/判据、阶段门、外部阻塞与50条策略 |
| 数据与统计 | CSV/Python标准库、openpyxl 3.1.5、Python statistics | W13服务/API/页面 | 不可变raw/清理版本、三种确定性统计、hash/图表/复核；W13时56条策略 |
| Office/PDF生成 | python-docx 1.2.0、python-pptx 1.0.2、openpyxl 3.1.5、reportlab 5.1.0、pypdf 6.21.4 | PyPI | DOCX/PPTX/XLSX/PDF真实文件、结构重开、文本与hash检查 |
| Office渲染/重算 | LibreOfficeDev 26.8.0 alpha；前端包装固定指向本机headless应用 | Codex primary runtime | DOCX/PPTX/XLSX→PDF、XLSX实际重算、逐页页图；不是生产固定容器镜像 |
| PDF页图 | Poppler `pdftoppm`（Codex primary runtime） | 外部可执行文件 | 96/72dpi页面渲染、空页检查与首页PNG |
| CJK字体 | macOS系统Arial Unicode（`/Library/Fonts/Arial Unicode.ttf`） | 系统字体，不提交仓库 | Office fontconfig转换与PDF嵌入；Linux需配置Noto/WQY等CJK字体 |
| 导出数据/API | PostgreSQL 17.6 RLS、artifact_exports JSONB/唯一键 | W14迁移/服务/API | 57条策略、真实文件hash、幂等、跨项目下载拒绝 |
| 导出页面 | Next.js 16.4.3、React 19.3.1、Blob/PDF preview | W14 Web与API | 四格式生成、首页PNG、PDF预览、下载、校验和hash |
| 模拟邮件 | Python 3.12标准库、进程内`MockMailAdapter`、PostgreSQL JSONB/RLS | W15领域/服务/API/页面 | 收件线程、草稿、附件hash、授权、幂等发送、result unknown核对与64条策略；无真实网络 |
| 外部合作记录 | Pydantic 2.14.2、PostgreSQL JSONB/NUMERIC/RLS、项目内知识版本 | W16领域/服务/API/页面 | 机构/专家、scope hash、报价/合同、原始交付、专业事实台账与73条策略；无真实联系/签署/付款/执行 |
| 独立审计/评测 | Pydantic 2.14.2、PostgreSQL JSONB/SHA-256/RLS、Next.js | W17领域/服务/API/页面 | 三类目标快照、A25/A26规则、阻断/处置、7案合成评测、迁移往返与76条策略；非真人/非mock独立审查 |
| Docker / Compose | 未安装 | 本机命令检查 | BLOCKED；容器和隔离未验收 |
| 真实模型 | 未配置 | 无 | 不可用，不调用 |
| 邮箱/外部机构 | 未配置/无授权 | 无 | 禁用，不发送 |

## 隔离结论

本机当前无法执行 Docker Compose 或容器技能隔离。W02—W17已使用独立原生
PostgreSQL 17.6 验证迁移、真实事务、重启恢复、应用角色RLS、工具审计、队列
租约、预算并发、26岗派发、技能授权、上传原件、解析定位、本地词法检索、
Citation、claims、版本影响、机会选择、未知概率/成本、项目证据边界、页面API、
分片上传、SSE、计划派生、审核退回、三领域阶段判据、现实阻塞、不可变数据版本、
统计计算、图表、真实Office/PDF文件和预览、模拟邮件草稿/授权/发送账本、外部
合作、专业事实台账和确定性审计；不得据此声称容器路径、通用容器Office/mail技能、
真实邮箱、真实机构接触/报价/签约/付款/执行、语义检索、真人/非mock独立审查、
科学判断、完整医学漏检率、复杂统计/研究设计、Microsoft Office/WPS像素一致性、
完整进程kill压力回归或后续
工作包已通过。安装Docker Desktop或兼容运行时后，仍需重新执行Compose、容器
策略、健康检查和构建验证。
