# W01—W18 可审核交付状态

被测源码提交：由最终`traceability/acceptance-records.json`绑定

状态口径：下列工作包均为IMPLEMENTED，不等于整体VERIFIED。成功的mock和
真实PostgreSQL测试只能支持对应技术行为；live模型、真人专家、真实邮箱和现实
外包未通过。W24仅PREPARED。

| W | 真实状态 | RQ | AT | 主要实现 | 本轮证据 | 未覆盖 |
| --- | --- | --- | --- | --- | --- | --- |
| W01 | IMPLEMENTED | RQ-025、RQ-032 | AT-025、AT-032 | `apps/web`、`services/core`、`deploy`、依赖锁 | web build、Ruff、mypy、系统测试 | Compose/Docker |
| W02 | IMPLEMENTED | RQ-007、RQ-012、RQ-029 | AT-007、AT-012、AT-029 | 项目、版本、会话、事件、artifact store | PostgreSQL W02测试 | 完整AT |
| W03 | IMPLEMENTED | RQ-005、RQ-013 | AT-005、AT-013 | RLS、授权交集、ToolGateway、运行目录 | 隔离/越权测试、83 RLS | 强容器隔离 |
| W04 | IMPLEMENTED | RQ-002、RQ-009、RQ-027 | AT-002、AT-009、AT-027 | 任务、outbox、租约、预算、输入有效性、worker异常隔离 | 调度/并发/陈旧输入/租约恢复测试 | 大规模故障回归 |
| W05 | IMPLEMENTED | RQ-004、RQ-005、RQ-006 | AT-004、AT-006 | 26岗合同、AgentRunner、fake/live合同 | 26岗配置与运行测试 | live模型 |
| W06 | IMPLEMENTED | RQ-013、RQ-025 | AT-013、AT-025 | 技能目录、授权、审计、容器策略 | 技能授权/输入输出测试 | 真实容器 |
| W07 | IMPLEMENTED | RQ-011、RQ-026、RQ-034 | AT-011、AT-026、AT-034 | 上传、原件、解析、来源政策 | 7类格式和来源测试 | 真实专业渠道 |
| W08 | IMPLEMENTED | RQ-012、RQ-023、RQ-034 | AT-012、AT-023、AT-034 | 词法索引、Citation、Claim、版本影响 | PostgreSQL检索/版本测试 | 向量检索 |
| W09 | IMPLEMENTED | RQ-008、RQ-021、RQ-028、RQ-031 | AT-008、AT-021、AT-028、AT-031 | 机会卡、简报、概率/成本、用户选择 | 合成候选与合同测试 | 真实需求/报价 |
| W10 | IMPLEMENTED | RQ-007、RQ-029、RQ-034 | AT-007、AT-029、AT-034 | 项目/知识/任务/机会页面、SSE | API、页面与生产构建 | 自动浏览器回归 |
| W11 | IMPLEMENTED | RQ-008、RQ-009、RQ-010、RQ-022 | AT-008、AT-009、AT-010、AT-022 | 有界DAG、派工、mock执行、审核/返工 | PostgreSQL与页面测试 | 独立Agent审核 |
| W12 | IMPLEMENTED | RQ-003、RQ-018、RQ-031 | AT-003、AT-018、AT-031 | 宠物药/IVD/器械流程、阶段门 | 配置、服务与页面测试 | 现实适用性 |
| W13 | IMPLEMENTED | RQ-017 | AT-017 | raw/清理数据、统计计划、图表、复核 | 数据/API/页面测试 | 复杂统计 |
| W14 | IMPLEMENTED | RQ-014、RQ-023 | AT-014、AT-023 | DOCX/PPTX/XLSX/PDF、重算和预览 | 真实文件与渲染测试 | Office/WPS像素全集 |
| W15 | IMPLEMENTED | RQ-015、RQ-029 | AT-015、AT-029 | 模拟邮箱、草稿、授权发送、不确定态 | 邮件/API/页面测试 | 真实邮箱 |
| W16 | IMPLEMENTED | RQ-016、RQ-018—RQ-021 | AT-016、AT-018—AT-021 | 机构、专家、报价、合同、交付、专业台账 | 合成外部记录测试 | 真实接触/签署/付款/执行 |
| W17 | IMPLEMENTED | RQ-006、RQ-011、RQ-022、RQ-024、RQ-031 | AT-006、AT-011、AT-022、AT-024、AT-031 | A25/A26确定性审计、输入/依赖范围阻断、处置、合成评测 | PostgreSQL/API/页面测试 | 真人/非mock独立审查 |
| W18 | IMPLEMENTED | RQ-012、RQ-026、RQ-027、RQ-034 | AT-012、AT-026、AT-027、AT-034 | 离线门、回收站、索引重建、加密备份、输入失效 | PostgreSQL/API/页面/迁移测试 | 活动DB重放、异地、主机故障 |
| W19 | IMPLEMENTED | RQ-001、RQ-030 | AT-001、AT-030 | 不可变PolicyBundle、运行绑定、影响传播、迁移账本 | PostgreSQL/API/页面/迁移测试 | 生产DDL、异地灾备、现实模式 |

## 当前后续工作

- W20—W23：PLANNED。全链故障回归、跨项目端到端、live连接和部署发布尚未完成。
- W24：PREPARED。没有现实联系、授权、执行、原始交付或验收；见
  [W24试点档案](w24-pilot-charter.md)。
- 当前分支不合并`main`。任何后续代码变化都要重新运行受影响验收并形成新证据；
  旧证据继续保留为历史。
