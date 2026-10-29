# 理论—技术—开发—验收对照

每条理论可对应多个模块。模块文件是具体技术入口，任务和场景编号可在相应工作计划及质量页找到。此表只表示设计覆盖，不表示功能已经实现。

| 理论 | 对应技术模块 | 开发任务 | 验收场景 |
| --- | --- | --- | --- |
| [CRA-R001 四个工作模块](../theory/REQUIREMENTS.md#cra-r001) | [M05](../architecture/modules/M05-monitoring.md) | CRA-W06、CRA-W10、CRA-W12 | CRA-S10、CRA-S12 |
| [CRA-R002 三层适用约束](../theory/REQUIREMENTS.md#cra-r002) | [M01](../architecture/modules/M01-governance.md)、[M03](../architecture/modules/M03-rules.md) | CRA-W01、CRA-W04 | CRA-S01、CRA-S06 |
| [CRA-R003 全部适用项目资料](../theory/REQUIREMENTS.md#cra-r003) | [M02](../architecture/modules/M02-documents.md)、[M10](../architecture/modules/M10-site_files.md) | CRA-W03、CRA-W10 | CRA-S03、CRA-S26 |
| [CRA-R004 规则用途文字直接纳入](../theory/REQUIREMENTS.md#cra-r004) | [M02](../architecture/modules/M02-documents.md)、[M03](../architecture/modules/M03-rules.md) | CRA-W03、CRA-W04 | CRA-S04 |
| [CRA-R005 条目级变更识别](../theory/REQUIREMENTS.md#cra-r005) | [M03](../architecture/modules/M03-rules.md) | CRA-W04 | CRA-S04 |
| [CRA-R006 所有list统一分层](../theory/REQUIREMENTS.md#cra-r006) | [M03](../architecture/modules/M03-rules.md)、[M05](../architecture/modules/M05-monitoring.md) | CRA-W04、CRA-W10、CRA-W12 | CRA-S05 |
| [CRA-R007 精确保留判定条件](../theory/REQUIREMENTS.md#cra-r007) | [M03](../architecture/modules/M03-rules.md)、[M09](../architecture/modules/M09-safety.md) | CRA-W04、CRA-W09 | CRA-S05、CRA-S25 |
| [CRA-R008 提取后用户确认增删](../theory/REQUIREMENTS.md#cra-r008) | [M03](../architecture/modules/M03-rules.md) | CRA-W04 | CRA-S05 |
| [CRA-R009 事实与建议附来源](../theory/REQUIREMENTS.md#cra-r009) | [M02](../architecture/modules/M02-documents.md)、[M03](../architecture/modules/M03-rules.md)、[M06](../architecture/modules/M06-issues.md)、[M11](../architecture/modules/M11-reports.md) | CRA-W03、CRA-W04、CRA-W06、CRA-W11 | CRA-S04、CRA-S15、CRA-S25 |
| [CRA-R010 患者事实自动复用](../theory/REQUIREMENTS.md#cra-r010) | [M04](../architecture/modules/M04-subjects.md) | CRA-W05 | CRA-S08 |
| [CRA-R011 访视锚点和时间窗](../theory/REQUIREMENTS.md#cra-r011) | [M03](../architecture/modules/M03-rules.md)、[M04](../architecture/modules/M04-subjects.md) | CRA-W04、CRA-W05 | CRA-S08 |
| [CRA-R012 按受试者实际顺序工作](../theory/REQUIREMENTS.md#cra-r012) | [M04](../architecture/modules/M04-subjects.md)、[M05](../architecture/modules/M05-monitoring.md) | CRA-W05、CRA-W06、CRA-W12 | CRA-S08、CRA-S10 |
| [CRA-R013 自动核对仅限检验报告](../theory/REQUIREMENTS.md#cra-r013) | [M07](../architecture/modules/M07-edc_import.md)、[M08](../architecture/modules/M08-laboratory.md) | CRA-W07、CRA-W08、CRA-W14 | CRA-S13 |
| [CRA-R014 EDC导出快照](../theory/REQUIREMENTS.md#cra-r014) | [M07](../architecture/modules/M07-edc_import.md) | CRA-W07 | CRA-S18 |
| [CRA-R015 先匹配再比对](../theory/REQUIREMENTS.md#cra-r015) | [M07](../architecture/modules/M07-edc_import.md)、[M08](../architecture/modules/M08-laboratory.md) | CRA-W07、CRA-W08、CRA-W14 | CRA-S19 |
| [CRA-R016 检验一致性和逻辑](../theory/REQUIREMENTS.md#cra-r016) | [M08](../architecture/modules/M08-laboratory.md)、[M09](../architecture/modules/M09-safety.md) | CRA-W08、CRA-W09、CRA-W14 | CRA-S19、CRA-S20 |
| [CRA-R017 无法识别可补录或跳过](../theory/REQUIREMENTS.md#cra-r017) | [M05](../architecture/modules/M05-monitoring.md)、[M08](../architecture/modules/M08-laboratory.md) | CRA-W08、CRA-W12、CRA-W14 | CRA-S21 |
| [CRA-R018 CRA基本分析支持](../theory/REQUIREMENTS.md#cra-r018) | [M09](../architecture/modules/M09-safety.md) | CRA-W09 | CRA-S23 |
| [CRA-R019 安全规则分别展开](../theory/REQUIREMENTS.md#cra-r019) | [M03](../architecture/modules/M03-rules.md)、[M09](../architecture/modules/M09-safety.md) | CRA-W04、CRA-W09 | CRA-S07、CRA-S23 |
| [CRA-R020 紧急事项及时提示](../theory/REQUIREMENTS.md#cra-r020) | [M06](../architecture/modules/M06-issues.md)、[M09](../architecture/modules/M09-safety.md) | CRA-W06、CRA-W09 | CRA-S11、CRA-S24 |
| [CRA-R021 PD上报按用户确认完成](../theory/REQUIREMENTS.md#cra-r021) | [M06](../architecture/modules/M06-issues.md) | CRA-W06 | CRA-S14 |
| [CRA-R022 系统问题和正式Query区分](../theory/REQUIREMENTS.md#cra-r022) | [M06](../architecture/modules/M06-issues.md)、[M11](../architecture/modules/M11-reports.md) | CRA-W06、CRA-W11 | CRA-S16 |
| [CRA-R023 Query超期有真实依据](../theory/REQUIREMENTS.md#cra-r023) | [M06](../architecture/modules/M06-issues.md) | CRA-W06 | CRA-S16 |
| [CRA-R024 ISF和TMF目录驱动](../theory/REQUIREMENTS.md#cra-r024) | [M02](../architecture/modules/M02-documents.md)、[M10](../architecture/modules/M10-site_files.md) | CRA-W03、CRA-W10 | CRA-S03、CRA-S26 |
| [CRA-R025 访前信只选几项](../theory/REQUIREMENTS.md#cra-r025) | [M06](../architecture/modules/M06-issues.md)、[M11](../architecture/modules/M11-reports.md) | CRA-W06、CRA-W11 | CRA-S27 |
| [CRA-R026 现场先复核遗留](../theory/REQUIREMENTS.md#cra-r026) | [M05](../architecture/modules/M05-monitoring.md)、[M06](../architecture/modules/M06-issues.md) | CRA-W06、CRA-W12 | CRA-S10、CRA-S11、CRA-S15 |
| [CRA-R027 遗留问题底稿写清过程](../theory/REQUIREMENTS.md#cra-r027) | [M06](../architecture/modules/M06-issues.md)、[M11](../architecture/modules/M11-reports.md) | CRA-W06、CRA-W11 | CRA-S14、CRA-S15 |
| [CRA-R028 正常范围简记异常详记](../theory/REQUIREMENTS.md#cra-r028) | [M04](../architecture/modules/M04-subjects.md)、[M05](../architecture/modules/M05-monitoring.md) | CRA-W05、CRA-W06、CRA-W10、CRA-W12 | CRA-S09、CRA-S17、CRA-S21、CRA-S29 |
| [CRA-R029 一次记录多份输出](../theory/REQUIREMENTS.md#cra-r029) | [M11](../architecture/modules/M11-reports.md) | CRA-W11 | CRA-S27、CRA-S28 |
| [CRA-R030 报告供上级确认保留快照](../theory/REQUIREMENTS.md#cra-r030) | [M11](../architecture/modules/M11-reports.md) | CRA-W11 | CRA-S28、CRA-S29 |
| [CRA-R031 跨次监查持续跟进](../theory/REQUIREMENTS.md#cra-r031) | [M06](../architecture/modules/M06-issues.md)、[M11](../architecture/modules/M11-reports.md) | CRA-W06、CRA-W11 | CRA-S14、CRA-S17、CRA-S26 |
| [CRA-R032 中心关闭依项目资料](../theory/REQUIREMENTS.md#cra-r032) | [M05](../architecture/modules/M05-monitoring.md) | CRA-W10、CRA-W12 | CRA-S12 |
| [CRA-R033 交接保持简洁](../theory/REQUIREMENTS.md#cra-r033) | [M05](../architecture/modules/M05-monitoring.md)、[M06](../architecture/modules/M06-issues.md) | CRA-W10、CRA-W12 | CRA-S12 |
| [CRA-R034 未知和冲突如实表达](../theory/REQUIREMENTS.md#cra-r034) | [M03](../architecture/modules/M03-rules.md)、[M04](../architecture/modules/M04-subjects.md)、[M07](../architecture/modules/M07-edc_import.md)、[M08](../architecture/modules/M08-laboratory.md) | CRA-W04、CRA-W05、CRA-W07、CRA-W08、CRA-W14 | CRA-S06、CRA-S18、CRA-S20、CRA-S25、CRA-S29 |
| [CRA-R035 检验自动化可以分期](../theory/REQUIREMENTS.md#cra-r035) | [M08](../architecture/modules/M08-laboratory.md)、[M12](../architecture/modules/M12-providers.md)、[M14](../architecture/modules/M14-platform.md) | CRA-W02、CRA-W04、CRA-W08、CRA-W09、CRA-W13、CRA-W14、CRA-W15 | CRA-S22、CRA-S30 |
| [CRA-R036 权限来源及历史约束](../theory/REQUIREMENTS.md#cra-r036) | [M01](../architecture/modules/M01-governance.md)、[M12](../architecture/modules/M12-providers.md) | CRA-W01、CRA-W02、CRA-W03、CRA-W04、CRA-W09、CRA-W14、CRA-W15 | CRA-S01、CRA-S02、CRA-S30 |
| [CRA-R037 第一版聚焦已确认业务](../theory/REQUIREMENTS.md#cra-r037) | [M05](../architecture/modules/M05-monitoring.md)、[M14](../architecture/modules/M14-platform.md) | CRA-W12、CRA-W13、CRA-W15 | CRA-S13、CRA-S33 |
| [CRA-R038 模型和OCR可替换](../theory/REQUIREMENTS.md#cra-r038) | [M08](../architecture/modules/M08-laboratory.md)、[M12](../architecture/modules/M12-providers.md) | CRA-W03、CRA-W04、CRA-W08、CRA-W09、CRA-W14 | CRA-S02、CRA-S22、CRA-S30 |
| [CRA-R039 理论与技术可追踪同步](../theory/REQUIREMENTS.md#cra-r039) | [M13](../architecture/modules/M13-traceability.md) | CRA-W00 | CRA-S31、CRA-S32 |
| [CRA-R040 GitHub云上开发](../theory/REQUIREMENTS.md#cra-r040) | [M14](../architecture/modules/M14-platform.md) | CRA-W00、CRA-W01、CRA-W02、CRA-W13、CRA-W15 | CRA-S33 |
| [CRA-R041 规则更新定位受影响事项](../theory/REQUIREMENTS.md#cra-r041) | [M03](../architecture/modules/M03-rules.md)、[M04](../architecture/modules/M04-subjects.md)、[M06](../architecture/modules/M06-issues.md) | CRA-W04、CRA-W05、CRA-W06 | CRA-S04、CRA-S07 |
| [CRA-R042 医学最终判断有职责边界](../theory/REQUIREMENTS.md#cra-r042) | [M09](../architecture/modules/M09-safety.md) | CRA-W09 | CRA-S23、CRA-S24 |
| [CRA-R043 生成与发送提交区分](../theory/REQUIREMENTS.md#cra-r043) | [M06](../architecture/modules/M06-issues.md)、[M11](../architecture/modules/M11-reports.md) | CRA-W06、CRA-W11 | CRA-S27 |
| [CRA-R044 用真实工作结果验收](../theory/REQUIREMENTS.md#cra-r044) | [M14](../architecture/modules/M14-platform.md) | CRA-W00、CRA-W13、CRA-W15 | CRA-S34 |
| [CRA-R045 少录入少重复打断](../theory/REQUIREMENTS.md#cra-r045) | [M04](../architecture/modules/M04-subjects.md)、[M05](../architecture/modules/M05-monitoring.md) | CRA-W05、CRA-W06、CRA-W10、CRA-W12 | CRA-S09、CRA-S34 |
