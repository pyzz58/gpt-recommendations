# 医疗一人项目

思想与用户决定：[最高思想](最高思想.md)。

软件设计、开发顺序及验收：[技术路线与实施路径](技术路线与实施路径.md)。

逐项追踪：[需求映射](traceability/manifest.json)。

本文件只作入口。思想维护规则见《最高思想》第14节，技术同步操作见技术主文件TR-02、TR-22。当前W01—W20已实现，W21 mock/local双项目端到端已验收，但整体live/现实AT仍未VERIFIED；W18提供默认离线门、回收站/恢复、索引重建、AES-256-GCM项目备份、独立PostgreSQL回放和后台mock worker；W19提供不可变策略bundle、运行绑定、影响传播和配置迁移账本；W20提供task/job预算关联、工具审计correlation、全链可靠性门及性能/故障回归；W21覆盖双项目选择、派工、退回、外部模拟、真实文件、重启和停止。PR#81复核后的返工缓存、审计门槛、类型化输入、直接Citation失效链与迟到worker执行所有权已修复。W17规则审计仍不是真人专家或非mock独立Agent审查；W19/W20未验证生产DDL、真实DB重启或异地灾备。准确状态见[W18接手说明](docs/w18-handoff.md)、[W19接手说明](docs/w19-handoff.md)、[W20可靠性报告](docs/w20-reliability-report.md)与[W21验收报告](docs/w21-end-to-end-report.md)，现实试点准备见[W24试点档案](docs/w24-pilot-charter.md)。完成证据与源码提交绑定在`traceability/acceptance-records.json`。

