# P1 市场新闻来源增补——来源实测治理（2026-10-14）

## 背景
上一轮 [PR #63 集成测试](https://github.com/pyzz58/gpt-recommendations/actions/runs/38525707755) 采集到 527 条新闻记录，但财经栏目 4 篇目标仅正式选入 3 篇；某些原有财经 RSS 入口 HTTP 200 却在 24 小时内没有可核实的新稿。重要：首次启动于北京时间 01:00 的发送时刻不调整，内参系统完全独立。

## 规则
1. 候选必须先进入 `market_source_candidates.json`，保留原始官方页或第三方核验出处及用途；**登记不代表启用**。
2. `probe_market_sources.py` 在 GitHub Actions runner 实际检查：HTTP、可解析 RSS/Atom、真实发布时间、最近 24 小时与 7 天更新数、标题美股相关性以及反垃圾过滤。HTTP 200 但 HTML 验证页不能算可用。
3. 通过候选探测后，再单独确认 **正文可访问性**、编辑质量、来源版权及原始站点是否允许使用。只有通过所有必要条件的源才加入 `feeds.json` 的 active 列表；失败源仍可作为候选观察，不伪称可用。
4. 对财报和官方公告，某日无新稿是正常情况，因此 24 小时为零不等于源故障；必须区分“RSS 正常但当日无公告”和“RSS 无法使用”。
5. 避免把公司宣传稿当作优质美股报道。公司官方公告可作为事实来源，经过 `market_headline.py` 和 `newsroom.py` 现有重要性和去重校验后才有机会入选。
6. 不制造新闻条数，也不启用无出处的二次抓取。所有测试只走公开数据，PR 不发正式邮件、不触发 DeepSeek 费用。

## 本轮可验收产物
- `market_source_candidates.json`：带公开出处、用途和风险备注的候选清单。
- `probe_market_sources.py`：真实 GitHub Linux runner 的单次源验收，不依赖本机网络或用户电脑。
- `test_market_source_probe.py`：测试 RSS 有效性、日期窗口、HTML 伪源和异常状态。
- 每个 PR 保留 `newspaper-p1-market-source-probe` JSON 运行附件 14 天，日志以 `NEWSPAPER_MARKET_PROBE_FEED=` 为行级报告。

## 留待完成
- 根据真实运行报告启用经过审核的新来源，再分别对新增的财经来源验证有多少被成功提取正文/最终入选 PDF。
- 建立 50 个真实历史重大事件（已独立引用）+ 当时确实可获取的历史候选池；当前模拟测试结果不能称为真实全球新闻召回率。
