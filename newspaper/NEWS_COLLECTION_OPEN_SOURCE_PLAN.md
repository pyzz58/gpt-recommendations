# Newspaper — Open-source news collection candidates (reviewed 2026-10-13)

This is a design decision record, NOT a statement that all adapters are installed or usable.
Keep upstream source attribution, original publication timestamps, and legal access limitations.

## Adopt-by-layer, not replace-everything

| Layer | Candidate | Repository | Proposed use | Current status / caveat |
| --- | --- | --- | --- | --- |
| Route-based discovery | RSSHub | https://github.com/DIYgod/RSSHub | 36Kr categories `/36kr/newsflashes`, `/36kr/news`; consider Xueqiu `/xueqiu/user/:id` | NOT deployed; Xueqiu route marks antiCrawler=true; do not bypass access controls; RSSHub AGPL-3.0 applies |
| Original RSS | Existing feedparser | https://github.com/kurtmckee/feedparser | Prefer verified 36Kr official WWW RSS, Xinhua official RSS, SEC/Fed feeds | Already in production; retain first priority |
| HTML extraction | Trafilatura | https://github.com/adbar/trafilatura | Article content from public pages | Already primary extractor; continue |
| Secondary extraction | Newspaper4k | https://github.com/AndyTheFactory/newspaper4k | Readable article fallback only, same publicly obtained HTML | Already integrated |
| Dynamic HTML | Crawl4AI | https://github.com/unclecode/crawl4ai | On-demand extraction for publicly readable Javascript-rendered article pages | NOT installed; browser-heavy; optional separate job only after measured quality gain |
| Financial indices/data | AKShare | https://github.com/akfamily/akshare | Test documented, dated US index / macro providers as candidate | NOT installed or verified in Actions; interfaces may disappear, provider terms apply |
| Complex site traversal | Scrapy | https://github.com/scrapy/scrapy | Build dated People's Daily Overseas edition catalog crawl if needed | NOT installed; our existing lightweight edition parser may be sufficient |

## Specific sources

- **36Kr**: first-party `https://www.36kr.com/feed` is configured. RSSHub 36Kr route code reads site fields such as `itemList`; useful as reference but might break when layout changes. Only prefer additional feed if GitHub runner shows higher actual valid-item yield.
- **Xinhua**: retain the three official RSS channels already configured; use article extraction only after verified dated feed discovery.
- **People's Daily Overseas**: dated daily-issue URLs and article links can be monitored; an issue date IS NOT a precise publication timestamp. Never silently admit issue-dated items into strict 24-hour feed without article-level date evidence or an explicitly separately labeled issue-date policy.
- **Xueqiu Journal**: official public monitor currently cannot identify journal issue from page; an RSSHub user stream would not by itself prove the journal's exact article provenance or date. Source is editorial opinion, not an official market quote.
- **US markets**: prefer regulator/exchange/FRED/official Treasury published metrics. For major indices only, a public Google Finance HTML adapter is experimental and must show quote timestamp, provider, intraday/post-session state, and refuse stale/challenge pages. Do not mislabel web quotes as certified closes.
- **Research institutions**: direct Fed, SEC, official institutional publication feeds and publicly readable primary releases are superior to unsupported analyst second-hand claims. Store publisher and release timestamp.

## Required benchmark before enabling an additional route

1. Can obtain valid RSS or article HTML in GitHub Actions without cookies or secret browser sessions.
2. Every item exposes credible title, URL, source, publication timestamp and stable canonical ID.
3. At least several days of observed successful fetches; count valid timestamped items, not HTTP 200 only.
4. Compare incremental *unique event* yield after deduplication, not number of endpoints.
5. Preserve origin and avoid paywalls, login bypass, anti-bot evasions, or full-text unlicensed republication.
6. Fail closed and record `source_failed`, `no_new_items`, `blocked`, `bad_timestamp`, `article_too_short` separately.
7. Keep scheduled Beijing 01:00 mail unchanged and use non-email PR previews for acceptance.

## Priority

1. Finish reliable and accurately attributed US-index numbers; check structured `.market.json` in actual CI.
2. Harden 36Kr/Xinhua RSS validation and observe per-source valid in-window counts.
3. Optional RSSHub evaluation in a separate non-production integration job, with explicit uptime and legal/attribution checks.
4. Optional Crawl4AI only for specific high-impact missing public articles and after runtime/cost measurements.
