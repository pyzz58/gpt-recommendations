# P0：2026-10-15 北京时间 01:00 日报未发送——定时触发根因审计

> 范围仅 `newspaper/` 日报，与独立内参无关。  
> 这是**已证据确认的未触发事件**，尚不能据此断言 GitHub 后端或 workflow 状态的最终根因。**绝不将 Gmail 作为 QQ 收件箱证据。**

## 后续核查结果与原始记录更正（2026-10-15）

**本节为最新证据，下文 §1—5 保留当时调查截面，不能再作为最终系统状态。** 当时查询到“仅一次 schedule”是早期查询时点的真实结果，但此后 GitHub 又创建了多次严重迟到的 `schedule` 运行；因此今天不是永远没有触发，而是**准点窗口内没有运行 + 到达过晚 + 旧版时限拒绝恢复**：

| 北京时间，2026-10-15 | run | 实际 GitHub 结论 |
| --- | --- | --- |
| 04:09 | [38629642981](https://github.com/pyzz58/gpt-recommendations/actions/runs/38629642981) | `event=schedule`；备稿因超出原 00:00–02:00 窗口失败 |
| 04:13 | [38630279581](https://github.com/pyzz58/gpt-recommendations/actions/runs/38630279581) | `event=schedule`；相同备稿期限失败 |
| 04:34 | [38633203909](https://github.com/pyzz58/gpt-recommendations/actions/runs/38633203909) | `event=schedule`；标记过期/失败 |
| 04:41 | [38634172442](https://github.com/pyzz58/gpt-recommendations/actions/runs/38634172442) | `event=schedule`；`EXPIRED_NO_SEND` |
| 07:23 | [38653814094](https://github.com/pyzz58/gpt-recommendations/actions/runs/38653814094) | 独立只读 `schedule` 探针真实成功；日志 `NEWSPAPER_CRON_REAL_EVENT=true` 且主工作流 `state=active` |
| 约 07:26 | [38653377545](https://github.com/pyzz58/gpt-recommendations/actions/runs/38653377545) | 一次**专门的 push**（非 schedule）生成当天 PDF；`NEWSPAPER_SMTP_ACCEPTED edition=2026-10-15`；`newspaper-sent-2026-10-15` 回执缓存保存 |

最后一行仅证明 QQ SMTP 交接，用户 QQ 收件箱是否到达仍未核实。不能与日报每日凌晨 01:00 定时发送成功混淆。

**已实施但尚待下一次真实准点验证的 P0 保护**：[PR #74](https://github.com/pyzz58/gpt-recommendations/pull/74) 于 2026-10-15 合并，固定 00:00 截稿，00:xx 只能备稿、`01:00` 前 SMTP 禁发；过 01:00 后至北京当天结束可恢复。同步修复每日回执读取/凭据检查顺序及旧版冲突测试；[CI 38657988185](https://github.com/pyzz58/gpt-recommendations/actions/runs/38657988185) **187 项回归+真实新闻 PDF 集成通过**。以上验证生产程序的行为，**不是 GitHub 计划调度的准点 SLA**。

**剩余关键未完成**：配置真实独立于 GitHub cron 的外部触发器，以 `workflow_dispatch(ref=main,inputs.dry_run=false)` 发起同日定时兜底，外部服务须由所有者专门授权且不公开 token；当前未部署。外部触发完成后，至少验证一次真实定时执行和 QQ SMTP 回执，再连续多日复查。

---
## 1. 从 GitHub 生产系统取得的证据

- 默认分支 `main`，审计时 HEAD `10d7a8dc1d2ebee3072273648568f1ed6f9b0bc7`，`.github/workflows/newspaper.yml` 位于此分支。
- 仓库公开、未归档，前 24 小时内存在大量提交：排除因仓库 **60 天无活动**而自动禁用定时任务这一常见原因。
- 主工作流包含 `schedule`、`pull_request`、`workflow_dispatch`；最近 PR 的 `pull_request` 工作流确实能运行并通过 CI。
- GitHub API：`GET /repos/pyzz58/gpt-recommendations/actions/runs?event=schedule&per_page=100` 返回 **1 次**历史定时事件（run `38341435043`，2026-10-13 03:22:55 UTC）。**2026-10-15 北京时间 00:05–01:55** 无任何 `schedule` 工作流。
- 专门查询 `2026-10-14T16:00:00Z..2026-10-14T18:30:00Z` 的 **所有事件**，运行总数为零，非 UI 过滤/错误分页导致。
- 因 **Github 没有创建对应 job**，无法推断当天运行过采集、SMTP、成功投递或 QQ 邮箱收信。
- 定时配置校验完整：`production_policy.json`、`verify_schedule.py` 与当前工作流包含同样七条 UTC cron。2026-10-14 UTC 16:05、16:20、17:03、17:16、17:29、17:42、17:55 分别映射 2026-10-15 北京时间 00:05、00:20、01:03、01:16、01:29、01:42、01:55。
- 当天最新生产代码早于该时段已合并到 `main`，与“定时任务仍在错误分支或定时前尚未创建文件”的解释不一致。

## 2. 不能当作根因的推断

1. 工作流 `active / disabled` 状态：**未能通过当前 GitHub 连接获取**。必须在 GitHub Actions 工作流页面或者 `gh api repos/pyzz58/gpt-recommendations/actions/workflows/newspaper.yml --jq .state` 核实。
2. GitHub 后台是否接受七条 cron 的调度注册、是否丢弃预定事件、对应计划任务的 actor 是否能参与调度：**仅 GitHub 后台或额外调度实验可进一步说明**。
3. QQ SMTP 是否配置正确、收件箱是否最终收到：这属于下游问题。**本次失败首先发生在触发层**。连接到其他邮箱不构成 QQ 收信证据。
4. 历史唯一一次 `schedule` 发生于 2026-10-13 03:22 UTC，时间并非最新配置的 16–17 UTC 段，也不能据此声称目前新 cron 曾成功触发。

## 3. 独立、最小化故障隔离探针

`.github/workflows/newspaper-schedule-probe.yml`：

- **每小时 UTC 第 37 分钟**执行只读 job，耗时和权限非常有限；不安装新闻依赖、不请求 QQ、不读取 Secrets，不会生成日报或发邮件。
- 支持工作流手动触发 `workflow_dispatch` 及在指定 marker 推送时用 `push` 触发，用于与 `schedule` 事件对照；只有出现日志 `NEWSPAPER_CRON_REAL_EVENT=true` 才算证实自动 cron 触发，手动/推送运行一律标注 `false`。
- 如果该新工作流能出现 `schedule` 事件而日报没有，重点转向日报原工作流的启用状态、schedule actor 与 cron 注册；如果两个都没有 schedule 事件，应升级为仓库/平台调度事件缺失排障。
- 此探针**只是隔离诊断，不是备用邮件发送器**，不证明正式发送恢复。证据足够后应及时删除每小时探针，避免无意义长期运行。
- 手动对照 URL：`https://github.com/pyzz58/gpt-recommendations/actions/workflows/newspaper.yml`，核实该工作流是否显示 `Enable workflow`。如显示则按官方步骤启用。若需核实状态，可在本地 `gh api repos/pyzz58/gpt-recommendations/actions/workflows/newspaper.yml --jq .state`。

本探针还使用 `github.token` 的 **Actions: read / Contents: read** 内置只读权限调用官方工作流详情接口，生成 `NEWSPAPER_MAIN_WORKFLOW_STATE`（含状态 `active`、`disabled_*` 或明确无法读取的状态），不披露 token、不进行启用、写入或发送操作。通过有意的普通 `push` 探针可立刻查询登记状态；**`push` 成功依然不等于 cron 成功**。

## 4. 生产事故验收门槛

- P0-Trigger：GitHub 已创建真实 `schedule` 运行（不是 PR、手动或标记推送），且运行开始时间属于当前北京时间稿期。
- P0-Prepare：有效稿期的完整备稿缓存与哈希清单成功保存。
- P0-Send：北京时间 01:00–02:00 的真实生产 job 读取备稿并得到 QQ SMTP `NEWSPAPER_SMTP_ACCEPTED`。
- P0-Receipt：SMTP 成功后存储当日发送回执；回执不代表实际收件成功。
- P0-Inbox：用户在 **QQ 邮箱**确认收件（含垃圾邮件和拦截规则检查）。
- 连续多日记录上述五层成功与失败。**PR 预览绿灯和 182 项单测不证明 P0-Trigger/P0-Send 已通过**。

## 5. 防止继续误报已修复

本次探针并不“修复 GitHub schedule 漏触发”。若得到已启用且 probe 同样长时间无运行的证据，应向 GitHub Support 反馈包括仓库、工作流文件、最近 commit、cron UTC 列表、历史唯一定时 run ID 与连续漏触发时段，并配置真正**不依赖 GitHub 自身 cron 的外部备援触发器**；只有经过明确授权、配置及真实投递回执验证后才可声称自动发送恢复。

官方依据：
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
