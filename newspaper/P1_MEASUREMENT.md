# 新闻日报 P1 — 选题质量测量：第一批可运行交付

> 范围：新闻日报 `newspaper/`，与内参系统完全独立。不会改变北京时间凌晨 01:00 正式发送规则。
> 时间政策唯一权威：`production_policy.json`。

## 1. 本次已实现（需要通过 CI 才能判为通过）

- `benchmarks/p1_headline_v1.json`：**50 条冻结的人工标记样例**。**其中仅 5 条是真实历史事件、且有经过核实的官方原始来源链接**；其他 **45 条明确标注为模拟测试**（包含 20 条应关注候选、15 条低价值噪声和 10 条同事件重复稿）。
- `editorial_benchmark.py`：以真实的 `newsroom.prepare_pool()` + `select_readable()` 选稿路径离线回放；选稿器只接收标题、概述、来源和 URL，标签字段不进入算法。
- `selection_audit.py`：正式采集流程产生每期**实际观察到**的原始候选条数、候选去向、淘汰理由和高分未入选预警；保留选稿得分解释，所有依据只是元数据而不是转载全文。
- GitHub PR 回归与固定样本测量每次运行，正式日报和 PR 的审核结果作为 Actions Artifact 保存 14 天（不可视为永久历史数据库）。
- 诊断失败不阻断已经正常生成的新闻日报，PR/预览不获取正式发送凭据，也不额外调用付费模型。

## 2. 指标的精确定义

- **事件召回率**：固定数据集中被成功选入的应关注**不同事件数** / 固定数据集中全部应关注**不同事件数**，不是相关新闻篇数之比。
- **选稿精确率**：被选入的应关注**不同事件数** / 实际被选入的**文章槽位数**。重复同一事件会降低此项精确率。
- **重复槽位率**：同一个人工事件 ID 被多次入选的冗余槽位数 / 全部入选槽位数。
- **误选项**：被选中但人工标签认为不是应关注事件的素材。
- “没有从预设 RSS 抓到该事件”不能被这套固定标题夹具测量出来；必须使用**历史快照/独立权威参考清单**衡量新闻发现的覆盖缺口。

固定样本中的 5 条可追溯历史原始资料：

1. [美联储 2024-09-18 联邦基金利率调整](https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm)
2. [SEC 2024-01-10 现货比特币 ETP 上市交易批准](https://www.sec.gov/newsroom/speeches-statements/gensler-statement-spot-bitcoin-011023)
3. [WHO 2020-03-11 新冠疫情定性](https://www.who.int/news-room/speeches/item/who-director-general-s-opening-remarks-at-the-media-briefing-on-covid-19---11-march-2020)
4. [欧盟理事会 2024-05-21 通过 AI Act](https://www.consilium.europa.eu/en/press/press-releases/2024/05/21/artificial-intelligence-ai-act-council-gives-final-green-light-to-the-first-worldwide-rules-on-ai/)
5. [FDA 2023-12-08 首项 CRISPR 疗法审批](https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapies-treat-patients-sickle-cell-disease)

**特别禁止：** 上述 50 条模拟混合集的数值不能被报告为“真实历史重大新闻召回率”，也不能被报告为“全球新闻覆盖率”。它只用于揭示当前选择器的显著回归、误选和重复风险。

## 3. 还未完成的 P1 验收

| 验收 | 当前状态 |
|---|---|
| 单一 feed 配置入口 | 已有 `feeds.json`，但来源身份证明/长时间健康趋势尚需加强 |
| 事件聚类、分板块、价值启发式 | 已有生产实现，尚需独立人工标注验证 |
| 50 条固定标题夹具与可复算指标 | 本次交付（待 CI） |
| 50 个真实历史重大事件金标准（独立来源、真实历史 as-of 候选集） | **未完成；目前仅 5 条有官方历史出处** |
| 真实历史漏选率、误选率、重复率 | **未测得；不可替换为模拟指标** |
| 每期观测 RSS 候选高分遗漏审计 | 本次接入（待首次真实运行） |
| 独立于所订阅 RSS 的覆盖缺口检查 | **未完成** |
| 选题质量人工盲审和基线提升 | **未完成** |

## 4. 下一批工作应如何客观验收

1. 扩充到至少 50 个**来源、日期真实可核验**的历史重大事件，区分报道当天能否获取原始资料；保留冷启动/不同主题/中文事件。
2. 对各历史日期保存当时可获取的候选池（或明确指出无法重现）；事件金标准需要独立核验，不能从最终入选结果倒推出标签。
3. 用同一固定快照同时运行旧版与新版，报告真实变化的召回、误选和重复指标（还需按领域/国家分别统计）。
4. 增加来自**独立原始机构源/机构日历**的漏选比较；仅比较已入库新闻不能证明系统没有漏掉重大新闻。
5. 选取真实日报由人抽检入选与遗漏理由；看重大政策、监管、财报、AI、外交在不同新闻源之间是否存在结构性盲区。

## 5. 运行和数据文件

```bash
python newspaper/editorial_benchmark.py
python -m unittest discover -s newspaper -p 'test_p1_benchmark.py' -v
```

- GitHub PR 的 Artifact：`newspaper-p1-benchmark`，含可计算的 JSON 明细。
- GitHub 新闻日报/PR 的 Artifact：`newspaper-p1-selection-audit`，含 `newspaper-selection-audit.json`；仅当真实素材采集、筛选已执行才产生文件。
- 运行日志：`NEWSROOM_P1_BENCHMARK` 和 `NEWSROOM_P1_SELECTION_AUDIT`，供后续趋势采集。
