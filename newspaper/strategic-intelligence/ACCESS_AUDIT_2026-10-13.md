> **V5 历史资料效力（2026-10-14）**：本文件保留当时的细化、模板或审计证据，不能独立改变[唯一现行 V5 主规格](CANONICAL_SYSTEM_SPEC_V5.md)。旧九栏固定百分比、独立连续情报/雷达、旧版“最高”与读者版“继续观察”等如有冲突，以 V5 为准；未冲突的专业方法和案例可按题参考。

# 2026-10-13 公共网络实际访问审计（来源扩容 V1.7）

> 这是一份**可重复核对的浏览器访问抽检**，不是运行中的GitHub Actions采集作业。本地容器对外DNS受限，尝试连接 BBC RSS 地址出现NameResolutionError；因此无法从当前容器对130个来源做同一环境的HTTP全量烟测。使用外部浏览检索器访问真实HTML/JSON；所有SOURCE_REGISTRY.json行仍保留production_test=NOT_RUN。无故障状态被夸称为成功生产运行。

## 真正取得新闻或研究HTML内容的例子
| 源 | 目标URL | 结果 |
|---|---|---|
| 人民日报海外版 | https://paper.people.com.cn/rmrbhwb/pc/layout/202610/13/node_01.html | 2026-10-13电子版新闻目录可读 |
| 海外网 | https://www.haiwainet.cn/ | 首页公开文章链接可读 |
| 人民网 | https://www.people.com.cn/ | 报系导航、时政财经及新闻目录可读 |
| 新华网中文 | https://www.news.cn/ | 文章入口和中文新闻页面可读；同站单条链接测试成功 |
| Reuters世界版 | https://www.reuters.com/world/ | 栏目可读，部分正文另看单篇 |
| Reuters单篇 | https://www.reuters.com/business/energy/us-hopes-diesel-deal-can-soften-moscow-peace-talks-sources-say-2026-10-12/ | 2026-10-12新闻标题、时间、作者、多个正文段落可读。此样本不保证全站免费。版权转载未授权 |
| 证券时报 | https://www.stcn.com/ | 公开首页 |
| 21世纪经济报道 | https://www.21jingji.com/ | 公开首页 |
| 上海证券报 | https://www.cnstock.com/ | 公开首页 |
| 中国证券报 | https://www.cs.com.cn/ | 公开首页 |
| 界面新闻 | https://www.jiemian.com/ | 公开首页 |
| 央视网 | https://www.cctv.com/ | 公开首页 |
| CNA | https://www.channelnewsasia.com/world | 世界新闻栏目 |
| Al Jazeera | https://www.aljazeera.com/ | 公开多地区报道、日期 |
| ABC Australia | https://www.abc.net.au/news | 跳转ABC主站，页面可读 |
| RNZ | https://www.rnz.co.nz/news | 公开新闻页面可读；网页缓存时间可能有滞后 |
| CBS News | https://www.cbsnews.com/world/ | 世界新闻列表可读 |
| VOA | https://www.voanews.com/ | 公开新闻入口可读 |
| Pew | https://www.pewresearch.org/ | 最新研究日期、标题和摘要可读 |
| CBO | https://www.cbo.gov/ | 官方预算研究页可读 |
| GAO | https://www.gao.gov/ | 官方审计页可读 |
| IAEA | https://www.iaea.org/newscenter | 官方新闻页面重定向并可读 |
| CDC | https://www.cdc.gov/ | 官方页面可读 |
| NIH | https://www.nih.gov/news-events/news-releases | 官方研究新闻目录可读 |
| Stanford HAI | https://hai.stanford.edu/research | 研究目录可读 |
| Microsoft Research | https://www.microsoft.com/en-us/research/publications/ | 论文目录可读 |
| SEC | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | 官方无Key JSON API文档（**不是提交真实数据请求**） |
| Fed RSS目录 | https://www.federalreserve.gov/feeds/feeds.htm | 官方RSS列表网页可读 |
| BIS RSS目录 | https://www.bis.org/rss | 官方RSS目录可读 |
| SIPRI | https://www.sipri.org/databases/milex | 军费数据库网页可读 |
| WHO | https://www.who.int/data/gho/info/athena-api/GHO | 官方API文档可读 |
| 伯克希尔股东信 | https://www.berkshirehathaway.com/letters/letters.html | 股东信历史目录可读 |
| 贝莱德周评 | https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary | 公开周评可读 |
| 摩根大通市场指南 | https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/ | 官方指南页面可读 |
| 高盛公开研究 | https://www.goldmansachs.com/insights/goldman-sachs-research/ | 公开精选研究页面可读 |
| YC RFS | https://www.ycombinator.com/rfs | 创业需求专题可读 |

## 返回真实JSON数据的测试（高于纯文档证明）
1. World Bank: https://api.worldbank.org/v2/country/US/indicator/NY.GDP.MKTP.CD?format=json 。响应application/json，含美国GDP指标值、data sourceid及更新时间，属于**真实数据接口返回**。
2. openFDA: https://api.fda.gov/drug/label.json?limit=1 。响应application/json，meta.last_updated为2026-10-12，至少1条药品标注记录，属于**真实数据接口返回**。
说明：两个结果通过外部Web代理取得，仍未在未来实际部署主机和定时调度中复现。

## 已发现但当前浏览器工具无法真正解析/读取（**保留C**）
- BBC RSS https://feeds.bbci.co.uk/news/world/rss.xml : 取得 text/xml 的响应类型，但Web文档解析器拒绝XML；这不能证明RSS端点坏了，须由标准feedparser在服务器实测。
- Guardian RSS https://www.theguardian.com/world/rss : XML类型不被浏览工具支持，更有独立的AI用途许可限制。
- Al Jazeera RSS https://www.aljazeera.com/xml/rss/all.xml : application/rss+xml 不被当前网页浏览工具解析；其HTML首页已实际可读。
- NPR https://www.npr.org/ : Web机器人收到 robots.txt denied；另有公开RSS候选，需确认内容与许可。
- DW 英文主站 https://www.dw.com/en/top-stories/s-9097 : robots限制；官方部分AMP页面在前轮可搜索。
- France24 https://www.france24.com/en/ : 当前403；不等于一般浏览器完全无权。
- BBC https://www.bbc.com/news : 浏览工具未成功读HTML；RSS待标准XML客户端确认。
- NHK、澎湃、第一财经、部分国内及国际网站：本轮读取失败或未验证，统一保持C。
- ClinicalTrials.gov 的API页面可读，但调用特定 JSON 端点时Web工具拒绝该URL，不得误记“API坏了”或“真实数据已返回”。

## 对“能用”的五级验收
V0：只找到机构网站/搜索结果；V1：确实读到一个可合法使用的页面或数据；V2：正式宿主机发起请求成功、解析出结构化条目并核验时间；V3：连续三次以上跨日成功，支持增量去重与错误恢复；V4：正式监控、权限审查及交付反馈正常。
**本次最多只是Web工具V1/部分JSON示例，不能假称130个源全部真实运行通过。**

## 明确不能标免费全文的商业内容
- IISS Military Balance+、Gartner客户专有研报、Nature非OA论文、FT/Bloomberg/Le Monde无法验证免费完整正文的频道、Reuters/LSEG专业授权数据、Bank of America/Goldman客户专属研究库；从免费全文生产白名单中排除。
- The Guardian 开发者API条款对AI与文本数据挖掘设限，在未获得适用授权前从自动LLM正文使用名单排除。
- 以上“剔除付费”不阻止从其他合法公开来源报道同一主题。

## 本次网络限制和未来补验
当前没有可直接从本容器连接任意外部媒体网址的DNS网络通道，不能在这里完成130路同环境的requests/urlopen实时测试；外部Web解析器也不能处理RSS/XML。未来可在隔离、授权的云测试环境跑脚本进行HTTP、Feed解析、许可和连续性测试。每一个失败要记录时间、HTTP代码、原始URL、备用入口和是否源端限制；不要把工具受限自动写成来源不可用。
