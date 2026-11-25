# W10 项目界面与知识库接手说明

对应：RQ-007、RQ-008、RQ-029、RQ-034及TR-11/TR-18的页面读取子项；TR-17、
TR-10.2、TR-20、TR-25；W10；AT-007、AT-029、AT-034的主要界面和API子项。

状态：IMPLEMENTED，未VERIFIED。真实PostgreSQL上的项目页面API、知识上传/处理/
检索、机会选择和SSE已测试；完整计划派工、任务审核、容器、删除恢复及现实协作
仍属于后续工作包。

## 已交付

- 本地开发会话使用随机opaque token、数据库SHA-256摘要和HttpOnly cookie；
  跨Origin写请求默认拒绝，页面请求不信任客户端指定的workspace或actor。
- `/projects`支持项目列表、创建和进入；项目页提供概览、Agent工作区、任务、
  机会和知识资料库入口，`/settings`展示真实依赖与限制。
- 项目概览从数据库读取对象计数、当前方向和事件。SSE按`project_seq`连接并
  自动重连；空状态明确表示没有任务，不显示虚构Agent活动。
- Agent页面加载A01—A26配置及本项目AgentInstance/AgentRun/Task；无任务岗位
  显示“未分配”，mock、provider、任务状态和更新时间来自实际记录。
- 任务页面区分工作队列、待验收/重做、等待与最终状态，并展示input refs、
  交付schema、验收政策和依赖。
- 机会页面分列科学、注册、专利、制造与商业缺口；主观/unknown概率和未知金额
  不转成精确总分。选择对话框记录理由和范围，不授权外部动作。
- 知识页面支持多文件选择/拖入、浏览器SHA-256、服务端分片校验、实际字节进度、
  commit、提取、词法索引、资料列表、详情、定位原文和hash校验原件下载。
- 知识检索要求选择真实任务，调用W08检索服务并保存RetrievalSnapshot；目录标题
  筛选与Agent证据检索明确分开。
- 页面切换使用AbortController取消旧查询，项目SSE在离开页面时关闭；桌面和
  390px窄屏完成浏览器联调。

## 主要路径

- 会话和认证：`services/core/src/medical_one_person/api/session.py`
- 项目/任务/Agent/机会API：`services/core/src/medical_one_person/api/workspace.py`
- 知识上传/详情/下载/检索API：`services/core/src/medical_one_person/api/knowledge.py`
- 页面只读查询：`services/core/src/medical_one_person/application/project_views.py`、
  `application/knowledge_browser.py`
- Web客户端：`apps/web/src/lib/api.ts`、`components/project-shell.tsx`、
  `apps/web/src/app/projects/`
- 集成测试：`services/core/tests/integration/test_w10_ui_api.py`

## 验收

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
PATH="/Users/zz/Library/pnpm/bin:$PATH" make test
PATH="/Users/zz/Library/pnpm/bin:$PATH" make lint
PATH="/Users/zz/Library/pnpm/bin:$PATH" make build
```

本轮结果：

```text
53 core tests passed (`make test`)
15 traceability self-tests passed
Project session/API and cross-Origin write rejection passed
Knowledge chunk upload, extraction, index, detail, search snapshot and download passed
Project SSE connected in browser
Next.js routes: projects, overview, agents, tasks, opportunities, knowledge, settings
Desktop and 390px responsive browser checks passed
Ruff and mypy passed
Next.js lint, typecheck and production build passed
```

## 尚未完成

- W11才实现线索到有界DAG、自动计划、派工、提交/退回/重做、暂停与停止命令。
- 上传暂停/继续/取消、完成/失败重试按钮、内嵌PDF/Office预览、版本比较、
  ACL共享/撤销、回收站、删除和备份恢复未完成。
- 当前解析和索引由API进程的BackgroundTasks触发；数据库job保留，但进程崩溃后
  自动恢复与worker接管仍须W18/W20验证。
- 机会页不能编辑候选卡，选择暂不附加知识证据版本；真实专业意见、询价、
  联系和实验均未发生。
- 没有浏览器自动化视觉回归；人工检查不能标为AT-007/029/034完全VERIFIED。
