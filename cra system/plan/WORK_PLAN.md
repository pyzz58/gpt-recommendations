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
| CRA-W08 | 实现检验源文件自动读取与EDC核对 | CRA-W06、CRA-W07 | M08、M12 | planned |
| CRA-W09 | 实现有依据的AE及PD分析 | CRA-W04、CRA-W06、CRA-W08 | M09、M12 | planned |
| CRA-W10 | 实现中心文件目录和其他阶段清单 | CRA-W04、CRA-W06 | M05、M10 | planned |
| CRA-W11 | 实现访视信、报告和Excel导出 | CRA-W06、CRA-W09、CRA-W10 | M11 | planned |
| CRA-W12 | 串联四阶段界面与一次完整监查 | CRA-W08、CRA-W09、CRA-W10、CRA-W11 | M05 | planned |
| CRA-W13 | 完成自动检验主线验收与试用准备 | CRA-W12 | M14 | planned |
| CRA-W14 | 增强复杂检验格式与识别效果 | CRA-W08 | M08、M12 | planned |
| CRA-W15 | 配置受控云部署并开展授权试用 | CRA-W13 | M01、M14 | planned |

## CRA-W00 建立技术基线与同步检查

验收：45条理论、14个模块、任务与验收关联；基础检查及反例测试在GitHub Actions运行。

对应理论：CRA-R039、CRA-R040、CRA-R044

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/40803113112；验证提交 67290ee4ea6e8d235fe38dd9f654b26dec243dcd；同步检查、22项单元测试和合成监查示例均通过。仅代表本工作包工程基线。

## CRA-W01 建立数据、权限和历史记录底座

验收：PostgreSQL迁移、研究/中心授权、幂等写入、并发版本和审计事务通过跨范围及重复提交测试。

对应理论：CRA-R002、CRA-R036、CRA-R040

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787；W07新增EDC快照迁移、共享API和前端依赖后，cra-w01专属job的migrate/test在PostgreSQL 18.6再次通过；被测提交9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59。

## CRA-W02 建立云上API和界面框架

验收：在Codespaces启动React界面和FastAPI；私有端口，登录/选择项目/健康检查可用，生成依赖锁与软件清单。

对应理论：CRA-R035、CRA-R036、CRA-R040

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787；W07接入EDC上传与AG Grid预览后，cra-w02的6项API测试、10项前端测试、类型、构建、OpenAPI、运行时和devcontainer smoke全部通过；被测提交9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59。

## CRA-W03 实现资料接收、解析和来源定位

验收：DOCX/PDF/文字解析保留章节、表格、脚注、格式和处理覆盖；异步作业可重试，缺件可登记。

对应理论：CRA-R003、CRA-R004、CRA-R009、CRA-R024、CRA-R036、CRA-R038

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787；W07扩展共享依赖、API与前端后，cra-w03专属job的8项PostgreSQL/S3测试、provider探测、OpenAPI契约和前端全部再次通过；被测提交9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59。

## CRA-W04 实现规则候选提取及分层list

验收：从模拟方案自动形成有出处的候选规则；用户确认增删；例外、且或、版本、冲突和修改轨迹可查看。

对应理论：CRA-R002、CRA-R004、CRA-R005、CRA-R006、CRA-R007、CRA-R008、CRA-R009、CRA-R011、CRA-R019、CRA-R034、CRA-R035、CRA-R036、CRA-R038、CRA-R041

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787；W07扩展共享API与前端后，cra-w04专属job的PostgreSQL测试、真实DOCX规则provider独立评估、OpenAPI契约和前端全部再次通过；被测提交9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59。

## CRA-W05 实现患者事实、锚点与核查断点

验收：EDC/源信息或人工事实导入后可复用；按适用规则计算访视要求；不同资料类别断点分别恢复。

对应理论：CRA-R010、CRA-R011、CRA-R012、CRA-R028、CRA-R034、CRA-R041、CRA-R045

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787；W07扩展共享迁移、入口和前端后，cra-w05专属job的7项PostgreSQL 18.6测试、OpenAPI契约、前端测试、类型检查和构建全部再次通过；被测提交9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59。

## CRA-W06 实现遗留整理、提醒与点击确认整改

验收：上次报告/track/文字整理为可展开遗留，本次开始提醒；CRA点击确认即可完成所选整改，保留历史和其他待办；Query期限有依据。

对应理论：CRA-R001、CRA-R009、CRA-R012、CRA-R020、CRA-R021、CRA-R022、CRA-R023、CRA-R025、CRA-R026、CRA-R027、CRA-R028、CRA-R031、CRA-R041、CRA-R043、CRA-R045

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787；W07扩展共享迁移、API和前端后，cra-w06专属job的test步骤运行test_issues.py 5项和test_carryover_import.py 3项，全部通过PostgreSQL 18.6；contracts与10项frontend测试、类型和生产构建全部成功；被测提交9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59。

## CRA-W07 实现EDC Excel检验快照导入

验收：预览、列映射、实例和导出范围确认后导入；复导不复制；导出缺项不直接判漏录。

对应理论：CRA-R013、CRA-R014、CRA-R015、CRA-R034

实际证据：GitHub Actions https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787；cra-w07专属job的5项PostgreSQL 18.6 EDC集成测试、OpenAPI契约、10项frontend测试、类型检查和生产构建全部成功；被测提交9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59。浏览器实测多sheet公式/缓存预览、映射确认、同日初检/复查分离及未命中范围语义；详见validation/W07_STATUS.md。

## CRA-W08 实现检验源文件自动读取与EDC核对

验收：支持格式的检验源文件自动提取/定位后，与EDC Excel先匹配再核对；集中复核低可信、歧义和异常，少量失败才补录或跳过。

对应理论：CRA-R013、CRA-R015、CRA-R016、CRA-R017、CRA-R034、CRA-R035、CRA-R038

## CRA-W09 实现有依据的AE及PD分析

验收：基于事实和规则形成候选结论、缺口、针对性问题及证据；医学维度分开，紧急提示不被报告流程延误。

对应理论：CRA-R007、CRA-R016、CRA-R018、CRA-R019、CRA-R020、CRA-R035、CRA-R036、CRA-R038、CRA-R042

## CRA-W10 实现中心文件目录和其他阶段清单

验收：原ISF/TMF目录可直接作为对照，附简要缺件与进展；结构化逐步建立，阶段和简洁交接复用原记录。

对应理论：CRA-R001、CRA-R003、CRA-R006、CRA-R024、CRA-R028、CRA-R032、CRA-R033、CRA-R045

## CRA-W11 实现访视信、报告和Excel导出

验收：模板映射、旧问题与新发现分栏、选取式访视信、报告快照和track一致；草稿和实际提交分开。

对应理论：CRA-R009、CRA-R022、CRA-R025、CRA-R027、CRA-R029、CRA-R030、CRA-R031、CRA-R043

## CRA-W12 串联四阶段界面与一次完整监查

验收：模拟前次报告→访前信→到中心复核→新受试者核查→报告→下一次接续全部完成；用户只需临床操作。

对应理论：CRA-R001、CRA-R006、CRA-R012、CRA-R017、CRA-R026、CRA-R028、CRA-R032、CRA-R033、CRA-R037、CRA-R045

## CRA-W13 完成自动检验主线验收与试用准备

验收：逐能力给出40场景、独立样本/实际provider证据、关键错误、自动覆盖及人工负担和总耗时；未验证核心自动能力必须记录未达标，不能以人工版替代。

对应理论：CRA-R035、CRA-R037、CRA-R040、CRA-R044

## CRA-W14 增强复杂检验格式与识别效果

验收：V1B在W08已有自动读取基础上扩展难版式/图像，沿用同一字段、匹配和比较；按关键错误与总负担实测决定支持范围。

对应理论：CRA-R013、CRA-R015、CRA-R016、CRA-R017、CRA-R034、CRA-R035、CRA-R036、CRA-R038

## CRA-W15 配置受控云部署并开展授权试用

验收：在获准环境配置身份、私有数据库/文件服务、备份恢复和模型；确认权限后以真实操作评价，记录风险与反馈。

对应理论：CRA-R035、CRA-R036、CRA-R037、CRA-R040、CRA-R044
