# 医疗一人项目

思想与用户决定：[最高思想](最高思想.md)。

软件设计、开发顺序及验收：[技术路线与实施路径](技术路线与实施路径.md)。

逐项追踪：[需求映射](traceability/manifest.json)。

本文件只作入口。思想维护规则见《最高思想》第14节，技术同步操作见技术主文件TR-02、TR-22。当前W01—W19已实现但仍未整体VERIFIED；W18提供默认离线门、回收站/恢复、索引重建、AES-256-GCM项目备份、独立PostgreSQL回放和后台mock worker；W19提供不可变策略bundle、运行绑定、影响传播和配置迁移账本。PR#81复核后的返工缓存、审计门槛、类型化输入、直接Citation失效链与迟到worker执行所有权已修复。W17规则审计仍不是真人专家或非mock独立Agent审查；W19未验证生产DDL或异地灾备。准确状态见[W18接手说明](docs/w18-handoff.md)与[W19接手说明](docs/w19-handoff.md)，现实试点准备见[W24试点档案](docs/w24-pilot-charter.md)。完成证据与源码提交绑定在`traceability/acceptance-records.json`。

