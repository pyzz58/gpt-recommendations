# 模块目录

14个模块构成一套系统，不是14个独立服务。业务入口为启动、访视、关闭和交接；下表是支撑这些工作的技术边界。

| 编号 | 模块 | 负责什么代码区域 | 主要工作包 |
| --- | --- | --- | --- |
| M01 | [权限、研究范围与操作历史](modules/M01-governance.md) | `backend/cra_app/governance/` | CRA-W01 |
| M02 | [项目资料与原文定位](modules/M02-documents.md) | `backend/cra_app/documents/` | CRA-W03 |
| M03 | [适用规则与分层list](modules/M03-rules.md) | `backend/cra_app/rules/` | CRA-W04 |
| M04 | [受试者事实与访视时间线](modules/M04-subjects.md) | `backend/cra_app/subjects/` | CRA-W05 |
| M05 | [四阶段监查工作台](modules/M05-monitoring.md) | `backend/cra_app/monitoring/` | CRA-W06、CRA-W10、CRA-W12 |
| M06 | [遗留问题、整改、Query与PD跟进](modules/M06-issues.md) | `backend/cra_app/issues/` | CRA-W06 |
| M07 | [EDC检验数据导入与范围](modules/M07-edc_import.md) | `backend/cra_app/edc_import/` | CRA-W07 |
| M08 | [检验报告识别与一致性核对](modules/M08-laboratory.md) | `backend/cra_app/laboratory/` | CRA-W08、CRA-W14 |
| M09 | [AE、安全及方案偏离分析支持](modules/M09-safety.md) | `backend/cra_app/safety/` | CRA-W09 |
| M10 | [ISF/TMF目录和中心资料](modules/M10-site_files.md) | `backend/cra_app/site_files/` | CRA-W10 |
| M11 | [访视信、监查报告与Excel输出](modules/M11-reports.md) | `backend/cra_app/reports/` | CRA-W11 |
| M12 | [模型、OCR与检索接入](modules/M12-providers.md) | `backend/cra_app/providers/` | CRA-W03、CRA-W04、CRA-W09、CRA-W14 |
| M13 | [理论、技术与任务同步](modules/M13-traceability.md) | `tools/` | CRA-W00 |
| M14 | [云上开发、部署和质量验证](modules/M14-platform.md) | `deploy/` | CRA-W00、CRA-W01、CRA-W02、CRA-W13、CRA-W15 |

固定理论与各模块的多对多关系以[对照表](../traceability/INDEX.md)为准。目录下的实现路径属于计划，当前只有backend/cra_core中的小范围示例和tools同步检查真正有代码。
