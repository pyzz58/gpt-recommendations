# 免费新闻获取工具研究与选型 V1.7

> 调查时间2026-10-13。**项目源码可公开使用不代表目标媒体的数据取得与AI处理已经获授权。工具代码已核对公开仓库说明，但尚未在本新闻项目生产环境安装/调用。**

## 最小采集组合（建议）
1. 原生RSS/API + 轻量Python标准网络客户端与Feed解析：首选，最稳定、最少依赖。
2. **Trafilatura**：https://github.com/adbar/trafilatura （Apache-2.0）— 公开且允许获取的HTML正文、作者、日期提取；可处理Sitemap/RSS入口。优先正文提取器。
3. **RSSHub**：https://github.com/DIYgod/RSSHub — 若合法公开内容没有原生RSS，且存在支持具体站点的路由，作为备选订阅转换。已经找到 BBC 路由 https://github.com/DIYgod/RSSHub/blob/master/lib/routes/bbc/index.ts ；但BBC已有原生RSS，无需为它优先部署RSSHub。
4. **Miniflux**：https://github.com/miniflux/v2 或 **FreshRSS**：https://github.com/FreshRSS/FreshRSS — 二者选一个作统一订阅平台，不能因为两个都开源就都部署。
5. **news-please**：https://github.com/fhamborg/news-please （Apache-2.0）— 具备RSS、站点地图、新闻归档与元信息抽取，适合合法公开媒体源的离线基准与特定规模化采集；侵入性大，需限制速率与许可审核。
6. **newspaper4k**：https://github.com/AndyTheFactory/newspaper4k （MIT等）— newspaper3k的后续维护分支，支持多语言网页提取。与Trafilatura作为竞品测试，不同时放进首版生产；上游有2026年7月的版本更新记录。
7. **NewsNow**：https://github.com/ourongxing/newsnow 或 https://github.com/newsnext/newsnow — 免费开源热点聚合/来源配置参考，适合发现线索，不把榜单热度当专业权威事实。源站个别接口可随时失效，项目也正处版本变迁。
8. **GDELT/Media Cloud**：公开新闻索引作为跨语言/跨国家线索渠道，必须回到原发媒体或官方资料核验；不是开放新闻全文的授权。
9. **SEC EDGAR downloader**：https://github.com/jadchaar/sec-edgar-downloader — 美股原始财报下载专用；依SEC官方访问政策/速率。

## 免费商业News API（不列为核心依赖）
- NewsAPI.org Developer Free https://newsapi.org/pricing — 主要供开发与测试，文章延迟、限制生产；**排除正式免费生产接入**。
- GNews Free https://gnews.io/pricing — 免费100次请求/日、12小时延迟、内容截断；官方仅允许个人/非商业用途，需注册密钥，正式使用条款必须另审。本轮**未注册/未调用**，仅备选。
- NewsData.io Free https://newsdata.io/documentation — 有200 credit/day免费计划，需要密钥，正文能力与条款另审；本轮**未调用**。
- The Guardian Open Platform https://www.theguardian.com/open-platform/terms-and-conditions — 虽有免费开发者API，现行条款第6(g)禁止使用其内容进行AI相关处理和文本挖掘。**在未取得相应许可前不纳入自动LLM研究正文管道**，不能因为免费就接入。

## 真实能力和失败边界
- 这些开源工具是**下载/解析工具而非媒体内容授权渠道**，没有一款能保证免费获取Reuters/Bloomberg/FT付费文章。
- 新闻RSS只给标题、时间、摘要时，应在数据库记录为metadata_only/summary_only。无法合法取得全文就停止深入阅读或寻找同事件开放一手材料。
- 官方机构报告可能免费阅读但不允许再分发原始内容，内参只写原创研究、合规短摘与原文指针。
- 机器人校验、JS渲染、地区限制是**技术/许可待判断**，不是默认许可用代理突破。
- 低成本选择：日报与周刊可共用技术库，但独立全球发现池；首版不同时引入三套大型爬虫、知识图谱与复杂自建代理池。

## 实施建议顺序
阶段0：原生API/RSS + 目前直读成功的开放网页，积累失败基线。
阶段1：只补Trafilatura解析和事件去重。
阶段2：对没有RSS的合法来源按站点单测RSSHub。
阶段3：只有当大量站点出现无法覆盖才测试news-please/newspaper4k并比较质量与成本。
上线前逐个检查协议、使用条款、robots、请求节奏和版权；不做未授权访问或网页全文批量转载。
