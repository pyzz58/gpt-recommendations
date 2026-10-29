# 可直接发给Codex的第一段指令

本指令对应技术修订v0.5。用于启动实际编程；开源组件选择见architecture/REUSE_ASSESSMENT.md，任务状态以实际分支为准。

```text
仓库：pyzz58/gpt-recommendations
项目目录：cra system

请先读取最新main和本目录AGENTS.md、CODEX_START_HERE.md，再按入口读取
theory/BASELINE.md、theory/REQUIREMENTS.md、architecture/IMPLEMENTATION_ROUTE.md、
architecture/REUSE_ASSESSMENT.md、plan/IMPLEMENTATION_PATH.md和plan/tasks.json。
运行python3 tools/next_task.py，核实当前实际进度，不把设计文档当已实现。

本轮只实现CRA-W01，严格按plan/work_packages/CRA-W01.md交付实际代码。
目标是可靠保存项目/中心授权、操作历史、幂等和并发版本，使用真实临时PostgreSQL
完成迁移、隔离、事务回滚和重试验证；不能用SQLite或纯mock代替。

优先使用已经选定的SQLAlchemy、Alembic、Pydantic等成熟组件，核对兼容和许可证，
生成可重现锁文件；不重写ORM/数据库迁移/身份密码系统。
其他现成组件在对应后续任务才接入，不提前做OCR、报告界面或整套身份服务器。
不要整仓复制FastAPI模板覆盖本项目，也不要重新写一套计划代替编程。

仅修改cra system及其专属工作流/Codespaces配置，保留其他项目。
在GitHub云端编写并验证，仅用合成数据，不上传真实项目/受试者资料，
不创建收费资源，不外发邮件，不写回EDC。

按plan/implementation.json的W01 profile真正建立cra-w01 CI job和migrate/test步骤。
源码提交实际通过后，按architecture/VALIDATION_AND_RELEASE.md记录
tested_commit、run_id、subject_digest等completion_evidence，再更新完成状态和生成视图。
自报完成、空文件、基础CI绿色或跳过测试都不能记为verified。
如改到已验证任务的源码/依赖，保留旧证据并按约定重新验证，不绕过证据检查。

保留固定CRA-R/M/CRA-W编号和最高说明。用户需求包括：
遗留开始提醒并可展开；CRA点击确认整改即可；缺数据可拒绝并跳过相关路径；
list含完整条件/分支/例外和出处；版本可手动开始使用日；
目录先直接作对照；支持格式的检验自动读取和EDC Excel核对是W08核心，
手工仅少量失败兜底；医学最终判断、发送/上报/签发状态按实际职责记录。

完成W01后报告实际代码/迁移、执行命令与CI链接、证据和限制及下一项；
只在确实达到任务验收后标完成。若有实质阻塞，写明缺口并完成本任务中
不依赖该缺口的工作，不跳过当前项冒充完成。本轮完成W01后停止，不自行进入W02。
```
