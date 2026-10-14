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

## 2026-10-14 GitHub runner 候选实测与首批准入

[首轮运行 #38530216374](https://github.com/pyzz58/gpt-recommendations/actions/runs/38530216374) 检查了 9 个来源，其中 8 个可以成功解析 RSS，91 条 RSS 记录具备当期 24 小时内的发布时间。注意 RSS 文章标题相关性初筛出现误判，故不能将 6 条初筛相关结果称为 6 篇可刊登新闻。

[第二轮运行 #38530823404](https://github.com/pyzz58/gpt-recommendations/actions/runs/38530823404) 扩充到 12 个入口：11 个可解析 RSS、130 条当期新稿、9 条通过**修复荐股判定之前**的美股标题线索初筛，后续仍须通过本地选稿评分、同事件去重、正文抓取。主要结果：

| 来源 | 当期新稿 | 美股线索初筛 | 准入决定 |
|---|---:|---:|---|
| CNBC Earnings | 5 | 2 | **拟启用**；其中一条实际是刊方自主荐股，另有 UnitedHealth 业绩报道，应只保留事实稿 |
| CNBC Finance | 4 | 1 | **拟启用**；美联储政策交流新闻 |
| CNBC Top News | 30 | 3 | **拟启用**；与其他 CNBC 频道重复，统一按 URL/事件去重 |
| FT Markets / FT US | 18 / 25 | 1 / 2 | 保留观察，尚未证明付费墙下全文可提取 |
| MarketWatch Top Stories / Bulletins | 10 / 10 | 0 / 0 | 暂不启用；没有证明稳定提供额外高质量美股事实稿 |
| Investing.com Stock Market / Company | 10 / 10 | 0 / 0 | 暂不启用；欧洲股市只提美国 CPI 的误分类已修正 |
| Seeking Alpha Breaking | 7 | 0 | 暂不启用；还需核查来源使用权与可读性 |
| NVIDIA Press Release | 1 | 0 | 暂不启用，公告源正常，但无当期符合目标的实质性美股新闻 |
| Nasdaq Financial Release | 0 | 0 | **不能启用**：GitHub runner 返回 HTTP 错误 |

**准入不是 P1 完整验收**：当前 PR 已拟将 3 个官方 CNBC 频道写入 `feeds.json`；仍需本 PR 最新提交的完整 CI，通过新的真实来源 PDF 集成测试，复核最终刊登篇数和内容质量。特别注意，滚动 24 小时的 PR 样刊不同于北京时间 00:00 截稿的正式日报。
