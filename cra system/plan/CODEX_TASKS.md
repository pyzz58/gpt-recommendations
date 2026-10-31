# Codex逐项开发入口

本页与16份任务卡均由plan/tasks.json生成，编号和状态沿用原计划。先读根目录CODEX_START_HERE.md。

当前V1A默认下一项：CRA-W02；状态：ready。

默认按V1A编号顺序推进，遇阻塞先说明，不自动跳项。V1A/W08必须包含支持格式的自动读取；V1B复杂格式增强和获准部署分别选择，不混进普通下一项。

| 工作包 | 具体执行说明 | 前置 | 路线 | 状态 |
| --- | --- | --- | --- | --- |
| CRA-W00 | [建立技术基线与同步检查](work_packages/CRA-W00.md) | 无 | baseline | verified |
| CRA-W01 | [建立数据、权限和历史记录底座](work_packages/CRA-W01.md) | CRA-W00 | v1a | verified |
| CRA-W02 | [建立云上API和界面框架](work_packages/CRA-W02.md) | CRA-W01 | v1a | planned |
| CRA-W03 | [实现资料接收、解析和来源定位](work_packages/CRA-W03.md) | CRA-W02 | v1a | planned |
| CRA-W04 | [实现规则候选提取及分层list](work_packages/CRA-W04.md) | CRA-W03 | v1a | planned |
| CRA-W05 | [实现患者事实、锚点与核查断点](work_packages/CRA-W05.md) | CRA-W04 | v1a | planned |
| CRA-W06 | [实现遗留整理、提醒与点击确认整改](work_packages/CRA-W06.md) | CRA-W05 | v1a | planned |
| CRA-W07 | [实现EDC Excel检验快照导入](work_packages/CRA-W07.md) | CRA-W05 | v1a | planned |
| CRA-W08 | [实现检验源文件自动读取与EDC核对](work_packages/CRA-W08.md) | CRA-W06、CRA-W07 | v1a | planned |
| CRA-W09 | [实现有依据的AE及PD分析](work_packages/CRA-W09.md) | CRA-W04、CRA-W06、CRA-W08 | v1a | planned |
| CRA-W10 | [实现中心文件目录和其他阶段清单](work_packages/CRA-W10.md) | CRA-W04、CRA-W06 | v1a | planned |
| CRA-W11 | [实现访视信、报告和Excel导出](work_packages/CRA-W11.md) | CRA-W06、CRA-W09、CRA-W10 | v1a | planned |
| CRA-W12 | [串联四阶段界面与一次完整监查](work_packages/CRA-W12.md) | CRA-W08、CRA-W09、CRA-W10、CRA-W11 | v1a | planned |
| CRA-W13 | [完成自动检验主线验收与试用准备](work_packages/CRA-W13.md) | CRA-W12 | v1a | planned |
| CRA-W14 | [增强复杂检验格式与识别效果](work_packages/CRA-W14.md) | CRA-W08 | v1b | planned |
| CRA-W15 | [配置受控云部署并开展授权试用](work_packages/CRA-W15.md) | CRA-W13 | deployment | planned |

每张卡都列出临床目标、对应理论/模块、目标文件、接口、实现步骤、命令、完成标准和不包含范围。
目标文件在未实现前可不存在；verified须有实际交付、可执行命令及绑定源码和任务专属CI的completion_evidence。完整阶段和交接见IMPLEMENTATION_PATH.md。

当前选择命令：`python3 tools/next_task.py`。该工具只读计划，不运行开发、部署或外部操作。
