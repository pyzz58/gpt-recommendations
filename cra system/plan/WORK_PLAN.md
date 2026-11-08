# 第一版开发工作计划

状态以实际代码和证据为准：planned=待实现，prepared=基线已备待云端验证，verified=所列工作包验收已完成。W00通过不等于整个系统完成。

执行顺序按依赖逐项推进；不承诺未经测量的工期。W08包含支持格式的核心自动检验读取；W14仅增强复杂格式，W15需获准部署环境。

| 工作包 | 内容 | 前置 | 模块 | 状态 |
| --- | --- | --- | --- | --- |
| CRA-W00 | 建立技术基线与同步检查 | 无 | M13、M14 | verified |
| CRA-W01 | 建立数据、权限和历史记录底座 | CRA-W00 | M01、M14 | verified |
| CRA-W02 | 建立云上API和界面框架 | CRA-W01 | M01、M14 | verified |
| CRA-W03 | 实现资料接收、解析和来源定位 | CRA-W02 | M02、M12 | verified |
| CRA-W04 | 实现规则候选提取及分层list | CRA-W03 | M03、M12 | verified |
| CRA-W05 | 实现患者事实、锚点与核查断点 | CRA-W04 | M04 | verified |
| CRA-W06 | 实现遗留整理、提醒与点击确认整改 | CRA-W05 | M05、M06 | verified |
| CRA-W07 | 实现EDC Excel检验快照导入 | CRA-W05 | M07 | verified |
| CRA-W08 | 实现检验源文件自动读取与EDC核对 | CRA-W06、CRA-W07 | M08、M12 | verified |
| CRA-W09 | 实现有依据的AE及PD分析 | CRA-W04、CRA-W06、CRA-W08 | M09、M12 | verified |
| CRA-W10 | 实现中心文件目录和其他阶段清单 | CRA-W04、CRA-W06 | M05、M10 | verified |
| CRA-W11 | 实现访视信、报告和Excel导出 | CRA-W06、CRA-W09、CRA-W10 | M11 | verified |
| CRA-W12 | 串联四阶段界面与一次完整监查 | CRA-W08、CRA-W09、CRA-W10、CRA-W11 | M05 | verified |
| CRA-W13 | 完成自动检验主线验收与试用准备 | CRA-W12 | M14 | verified |
| CRA-W14 | 增强复杂检验格式与识别效果 | CRA-W08 | M08、M12 | verified |
| CRA-W15 | 配置受控云部署并开展授权试用 | CRA-W13 | M01、M14 | blocked |

## CRA-W00 建立技术基线与同步检查

验收：45条理论、14个模块、任务与验收关联；基础检查及反例测试在GitHub Actions运行。

对应理论：CRA-R039、CRA-R040、CRA-R044

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/40803113112；验证提交 67290ee4ea6e8d235fe38dd9f654b26dec243dcd；同步检查、22项单元测试和合成监查示例均通过。仅代表本工作包工程基线。

## CRA-W01 建立数据、权限和历史记录底座

验收：PostgreSQL迁移、研究/中心授权、幂等写入、并发版本和审计事务通过跨范围及重复提交测试。本轮还须满足 UX-A01；UX-A02；UX-A03 的正常产品验收。

对应理论：CRA-R002、CRA-R036、CRA-R040

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323；cra-w01 的真实 PostgreSQL 18.6 migrate/test 在 2026-11-01 复核迁移和共享授权/事务依赖后通过。 被测提交 5148684064a57e50077dd32d02e76b57b2221fc4。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w01 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w01 在 W10 集成和 CI 日志绑定源码上重新通过；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w01 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w01 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w01 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w01在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w01 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W02 建立云上API和界面框架

验收：在Codespaces启动React界面和FastAPI；私有端口，登录/选择项目/健康检查可用，生成依赖锁与软件清单。本轮还须满足 UX-A01；UX-A04；UX-A05 的正常产品验收。

对应理论：CRA-R035、CRA-R036、CRA-R040

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323；cra-w02 的 PostgreSQL API、13 个前端测试、typecheck、build、OpenAPI contract、runtime smoke 和 devcontainer smoke 全部通过。 被测提交 5148684064a57e50077dd32d02e76b57b2221fc4。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w02 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w02 在 W10 集成和 CI 日志绑定源码上重新通过；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w02 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w02 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w02 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w02在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w02在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w02在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w02 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w02 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w02 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W03 实现资料接收、解析和来源定位

验收：DOCX/PDF/文字解析保留章节、表格、脚注、格式和处理覆盖；异步作业可重试，缺件可登记。本轮还须满足 UX-A06 的正常产品验收。

对应理论：CRA-R003、CRA-R004、CRA-R009、CRA-R024、CRA-R036、CRA-R038

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323；cra-w03 的真实 PostgreSQL/S3 文档工作流、provider probe、contract 和前端检查全部通过。 被测提交 5148684064a57e50077dd32d02e76b57b2221fc4。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w03 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w03 在 W10 集成和 CI 日志绑定源码上重新通过；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w03 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w03 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w03 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w03在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w03在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w03在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w03 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w03 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w03 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W04 实现规则候选提取及分层list

验收：从模拟方案自动形成有出处的候选规则；用户确认增删；例外、且或、版本、冲突和修改轨迹可查看。本轮还须满足 UX-A07 的正常产品验收。

对应理论：CRA-R002、CRA-R004、CRA-R005、CRA-R006、CRA-R007、CRA-R008、CRA-R009、CRA-R011、CRA-R019、CRA-R034、CRA-R035、CRA-R036、CRA-R038、CRA-R041

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41248250769；17项review-unit/规则PostgreSQL测试、规则provider评估、契约和前端通过；同源中心采用日与独立中心同编号规则并存验证完成。 被测提交 f66750c9fac58dbf2e03189582a3544fc039bfd4。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w04 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w04 在 W10 集成和 CI 日志绑定源码上重新通过；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w04 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w04 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w04 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w04在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w04在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w04在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w04 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w04 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w04 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W05 实现患者事实、锚点与核查断点

验收：EDC/源信息或人工事实导入后可复用；按适用规则计算访视要求；不同资料类别断点分别恢复。本轮还须满足 UX-A08；UX-A09 的正常产品验收。

对应理论：CRA-R010、CRA-R011、CRA-R012、CRA-R028、CRA-R034、CRA-R041、CRA-R045

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001；15项PostgreSQL/API分支目标测试和4项review-gate自测通过；直接/容器目标、false/unknown/true、真实超窗、兄弟路径和多入口OR语义验证完成。 被测提交 12a7b38d577066424cb7cec9e29378923eeef406。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w05 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w05 在确切 CI 日志绑定校验器源码上通过；W10 功能、迁移和前端依赖链重新核验；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w05 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w05 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w05 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w05在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w05在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w05在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w05 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w05 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w05 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W06 实现遗留整理、提醒与点击确认整改

验收：上次报告/track/文字整理为可展开遗留，本次开始提醒；CRA点击确认即可完成所选整改，保留历史和其他待办；Query期限有依据。本轮还须满足 UX-A05；UX-A09；UX-A10 的正常产品验收。

对应理论：CRA-R001、CRA-R009、CRA-R012、CRA-R020、CRA-R021、CRA-R022、CRA-R023、CRA-R025、CRA-R026、CRA-R027、CRA-R028、CRA-R031、CRA-R041、CRA-R043、CRA-R045

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001；W05依赖链重新验证后，遗留复核、一次确认整改和分项状态真实PostgreSQL回归通过。 被测提交 12a7b38d577066424cb7cec9e29378923eeef406。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w06 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w06 在确切 CI 日志绑定校验器源码上通过；W10 功能、迁移和前端依赖链重新核验；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w06 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w06 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w06 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w06在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w06在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w06在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w06 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w06 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w06 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W07 实现EDC Excel检验快照导入

验收：预览、列映射、实例和导出范围确认后导入；复导不复制；导出缺项不直接判漏录。本轮还须满足 UX-A08 的正常产品验收。

对应理论：CRA-R013、CRA-R014、CRA-R015、CRA-R034

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001；W05依赖链重新验证后，真实XLSX导入、不可变快照、契约和前端回归通过。 被测提交 12a7b38d577066424cb7cec9e29378923eeef406。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w07 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w07 在确切 CI 日志绑定校验器源码上通过；W10 功能、迁移和前端依赖链重新核验；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w07 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w07 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w07 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w07在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w07在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w07在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w07 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w07 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w07 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W08 实现检验源文件自动读取与EDC核对

验收：支持格式的检验源文件自动提取/定位后，与EDC Excel先匹配再核对；集中复核低可信、歧义和异常，少量失败才补录或跳过。本轮还须满足 UX-A08；UX-A09 的正常产品验收。

对应理论：CRA-R013、CRA-R015、CRA-R016、CRA-R017、CRA-R034、CRA-R035、CRA-R038

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001；7项复核、13项检验和4项识别测试通过；真实Docling评估及既有关闭的复投/租约修正回归通过。 被测提交 12a7b38d577066424cb7cec9e29378923eeef406。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w08 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w08 在确切 CI 日志绑定校验器源码上通过；W10 功能、迁移和前端依赖链重新核验；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w08 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w08 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w08 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w08在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w08在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w08在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w08 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w08 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w08 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W09 实现有依据的AE及PD分析

验收：基于事实和规则形成候选结论、缺口、针对性问题及证据；医学维度分开，紧急提示不被报告流程延误。本轮还须满足 UX-A09；UX-A10 的正常产品验收。

对应理论：CRA-R007、CRA-R016、CRA-R018、CRA-R019、CRA-R020、CRA-R035、CRA-R036、CRA-R038、CRA-R042

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001；65项受影响PostgreSQL/API测试、真实Qwen与Docling评估、契约和前端通过；W05分支目标修正已继承验证。 被测提交 12a7b38d577066424cb7cec9e29378923eeef406。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w09 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w09 在确切 CI 日志绑定校验器源码上通过；W10 功能、迁移和前端依赖链重新核验；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w09 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w09 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w09 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w09在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w09在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w09在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w09 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w09 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w09 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W10 实现中心文件目录和其他阶段清单

验收：原ISF/TMF目录可直接作为对照，附简要缺件与进展；结构化逐步建立，阶段和简洁交接复用原记录。本轮还须在模板驱动监查工作区中保持原有目录/复杂检验功能，并完成回归。

对应理论：CRA-R001、CRA-R003、CRA-R006、CRA-R024、CRA-R028、CRA-R032、CRA-R033、CRA-R045

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718；cra-w10 的真实 PostgreSQL 18.6、迁移/回归、契约和前端步骤通过；W10目录/阶段清单集成后重新绑定源码；被测提交 8c733e97ac35496ca463b171dd1cecfce73246a8。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286；cra-w10 在确切 CI 日志绑定校验器源码上通过；W10 功能、迁移和前端依赖链重新核验；被测提交 79ee1a1743946dcab4125acc9c6250d67b8f3ede。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w10 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w10 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w10 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w10在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w10在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w10在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w10 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w10 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w10 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W11 实现访视信、报告和Excel导出

验收：模板映射、旧问题与新发现分栏、选取式访视信、报告快照和track一致；草稿和实际提交分开。本轮还须满足 UX-A06；UX-A09；UX-A10 的正常产品验收。

对应理论：CRA-R009、CRA-R022、CRA-R025、CRA-R027、CRA-R029、CRA-R030、CRA-R031、CRA-R043

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41257509611；cra-w11 在 W11 集成及报告迁移后重新通过；被测提交 874450d033fbfcda01f9c191e3a76fbfa7caf8c2。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w11 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w11 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w11在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w11在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w11在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w11 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w11 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w11 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W12 串联四阶段界面与一次完整监查

验收：模拟前次报告→访前信→到中心复核→新受试者核查→报告→下一次接续全部完成；用户只需临床操作。本轮还须满足 UX-A01；UX-A02；UX-A03；UX-A04；UX-A05；UX-A06；UX-A07；UX-A08；UX-A09；UX-A10 的正常产品验收。

对应理论：CRA-R001、CRA-R006、CRA-R012、CRA-R017、CRA-R026、CRA-R028、CRA-R032、CRA-R033、CRA-R037、CRA-R045

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41272918165；cra-w12 在 W12 四阶段串联后重新通过；被测提交 8b85aa2c8a0d26d6ef56d359d691206794199563。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562；cra-w12 在证据摘要排除 ignored 运行产物的最终源码上通过；被测提交 7c369da552db7f11d8b794bd9edc19174f8aa6e9。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w12在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w12在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w12在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w12 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w12 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w12 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W13 完成自动检验主线验收与试用准备

验收：逐能力给出40场景、独立样本/实际provider证据、关键错误、自动覆盖及人工负担和总耗时；未验证核心自动能力必须记录未达标，不能以人工版替代。本轮还须满足 UX-A01；UX-A02；UX-A03；UX-A04；UX-A05；UX-A06；UX-A07；UX-A08；UX-A09；UX-A10 的正常产品验收。

对应理论：CRA-R035、CRA-R037、CRA-R040、CRA-R044

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42356972071；cra-w13在真实PostgreSQL 18.6上通过W12恢复、13项验收反例、1项Chromium两轮监查及能力报告结构检查；40场景中33项合成验证、3项工程验证、3项未评估、CRA-S34未达标；总人工时间和授权试用明确保留为W15工作；被测提交72fb8dc4853fbf68ccadfc1a0c0f4d2c8726e11b。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w13在W14复杂格式增强后的绑定源码上通过专属job；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w13在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w13在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w13 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w13 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w13 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W14 增强复杂检验格式与识别效果

验收：V1B在W08已有自动读取基础上扩展难版式/图像，沿用同一字段、匹配和比较；按关键错误与总负担实测决定支持范围。本轮还须在模板驱动监查工作区中保持原有目录/复杂检验功能，并完成回归。

对应理论：CRA-R013、CRA-R015、CRA-R016、CRA-R017、CRA-R034、CRA-R035、CRA-R036、CRA-R038

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42358464585；cra-w14在真实PostgreSQL下通过23项实验室/识别测试、既有PDF/PNG回归、两页扫描4/4与0.5度JPEG 2/2实际Docling评估（6/6行、关键字段零错误、5行可自动使用、1行逗号小数集中复核）、19项前端测试和1项完整Chromium流程；被测提交261b1d0844a68f56e9b3835f6a32e62c22d15dbc。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w14在W15部署候选及运行时Authlib传输依赖修正后的绑定源码上通过专属job；被测提交5002880736888e69035d0d62bf62fbb6415b113d。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456；cra-w14在本机合成体验和W12浏览器稳定性修复后的绑定源码上通过专属job；被测提交cae99eda0f2b771f5092c698d69ee304aa41ae29。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396；cra-w14 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例和W12阶段竞态修复后的绑定源码上通过专属job；被测提交0107bff1782649033b1d8125a25c04ec4798241f。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132；cra-w14 在本机合成核查工作台、EDC快照默认展示、Docling清晰图像OCR、安全规则示例、W12阶段竞态修复和证据步骤索引重试后的绑定源码上通过专属job；被测提交6967ecf41fb10f199dbc4401ca48c5f1d53d0c98。

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42462436237；cra-w14 在本机空白合成项目、项目/中心浏览器创建、模板章节问句集中配置与复用、逐项核查、EDC/检验核对、问题关联、报告回填和两次监查接续后的绑定源码上通过专属job；被测提交bbcb96440fb94e7eb7b9f7f94a93f1ea2a77e549。

## CRA-W15 配置受控云部署并开展授权试用

验收：在获准环境配置身份、私有数据库/文件服务、备份恢复和模型；确认权限后以真实操作评价，记录风险与反馈。

对应理论：CRA-R035、CRA-R036、CRA-R037、CRA-R040、CRA-R044

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/42359819771；cra-w15的deployment-check通过API/Web镜像构建、PostgreSQL迁移、API/worker/Nginx启动和健康检查；trial-record明确输出authorized_trial_ready=false、状态BLOCKED。缺少获准OIDC租户、私有生产服务、真实恢复、物理设备和授权CRA试用，因此W15未verified；被测部署候选提交5002880736888e69035d0d62bf62fbb6415b113d。
