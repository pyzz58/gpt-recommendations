# 医疗一人项目

思想与用户决定：[最高思想](最高思想.md)。

软件设计、开发顺序及验收：[技术路线与实施路径](技术路线与实施路径.md)。

逐项追踪：[需求映射](traceability/manifest.json)。

本文件只作入口。思想维护规则见《最高思想》第14节，技术同步操作见技术主文件TR-02、TR-22。当前W01—W20基础已实现，W21 mock/local双项目端到端已验收，科学反馈回流与A02首席整合已通过独立合成回归，W23本地部署/运维包已实现；W22模型与SMTP适配器及离线transport测试已实现，真实模型/邮箱仍未连接；整体live/现实AT仍未VERIFIED。W23提供统一`doctor/bootstrap/start/status/smoke/stop`入口、同一仓库外配置源、数据库/存储/队列/worker健康状态和恢复边界；Compose已静态结构化但本机无Docker。W17规则审计仍不是真人专家或非mock独立Agent审查；W24仍为PREPARED且没有现实联系或执行。准确状态见[W19接手说明](docs/w19-handoff.md)、[W20可靠性报告](docs/w20-reliability-report.md)、[W21验收报告](docs/w21-end-to-end-report.md)、[科学反馈交接](docs/scientific-feedback-handoff.md)、[W22适配交接](docs/w22-handoff.md)与[W23接手说明](docs/w23-handoff.md)。完成证据与源码提交绑定在`traceability/acceptance-records.json`。

