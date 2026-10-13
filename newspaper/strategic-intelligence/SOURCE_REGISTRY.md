# 全球权威信息源登记表 V1.7

> 核查日期：2026-10-13。**公开网页/部分JSON接口的实际读取审计，不是生产采集通过验收。** 机器可读原件见 [SOURCE_REGISTRY.json](SOURCE_REGISTRY.json)。

## 本轮进展与解释
- 候选从原有68扩容至现在 **130**（A=76，B=7，C=47）。
- **A：免费公开页面内容或官方API/RSS文档已确认存在**；不是已完成定时接口采集，更不意味着可以合法重新分发全文。
- **B：机构有合法可免费阅读的栏目、节选或单篇，但客户独家研报/整套全文未授权。只把免费部分纳入候选。**
- **C：源有潜在价值但当前不能确认能够实际自动获取，有的因robots/403、动态渲染、跳转、解析XML限制；不计作可上线生产的白名单。**
- D/付费来源已从活动候选剔除并写入 [SOURCE_ACCESS_BLOCKLIST.md](SOURCE_ACCESS_BLOCKLIST.md)。
- 运行状态 **production_test=NOT_RUN 对所有来源均成立**。只有在实际宿主机按 [SOURCE_VERIFICATION_PLAYBOOK.md](SOURCE_VERIFICATION_PLAYBOOK.md) 连续通过测试才标生产有效。
- 当前真正经浏览器工具取得 HTML/JSON/RSS目录/API文档示例的来源有 32 个条目；其余大多是上一轮确认的公开入口或本轮未能测试，见具体 `content_test_result` 字段。特别要区分 **能读元信息、能读新闻正文、允许自动获取、允许 AI 处理、允许重发** 五种不同状态。

## 核心媒体补充
- 中国：人民日报海外版、海外网、人民网、新华网（中文）、央视、证券时报、21世纪经济报道、上海证券报、中国证券报、界面新闻等已出现可读的公开页面。新华社英文站另保留C类路径待验证。
- 国际：Reuters公开栏目及某一篇2026-10-12文章正文可读取；BBC世界新闻RSS返回XML内容类型，但本次浏览器工具不支持解析XML，**不可以算接口已完成成功拉取**；CNA、Al Jazeera、ABC、CBS、VOA等有公开可读目录。NPR/France24/DW英文主站当前抓取机器人受限，不能因此认定普通浏览器访问也失败。
- 重点风险：Guardian Open Platform当前条款包含禁止用其内容进行AI/文本数据分析的约束，因此在缺少相应授权前应排除自动AI摄取；NewsAPI.org免费开发者计划也不能未经许可作为生产源。

## 分领域全量登记

### 新闻

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-001 | AP News | A 公开入口 | PUBLIC SITE DOCUMENTED NOT RETESTED | [打开](https://apnews.com/) |
| SRC-002 | Reuters World | B 免费部分 | WEB TOOL ARTICLE FULL HTML SAMPLE OK | [打开](https://www.reuters.com/world/) |
| SRC-003 | Al Jazeera | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.aljazeera.com/) |
| SRC-004 | Deutsche Welle | A 公开入口 | WEB TOOL MAIN ROBOTS DENIED | [打开](https://amp.dw.com/en/the-day-with-brent-goff/video-19049331) |
| SRC-005 | BBC News | C 待验证 | RSS ENDPOINT RESPONDED TEXT XML BUT BROWSER PARSER UNSUPPORTED | [打开](https://www.bbc.com/news) |
| SRC-006 | 新华社英文站 | C 待验证 | ENGLISH SITE FAIL  CHINESE NEWS CN WORKS | [打开](https://english.news.cn/) |
| SRC-007 | GDELT | A 公开入口 | PRIOR PUBLIC INDEX DOCUMENTED | [打开](https://gdeltproject.org/) |
| SRC-008 | Media Cloud | B 免费部分 | PREVIOUS API DOC REVIEW | [打开](https://www.mediacloud.org/documentation/search-api-guide) |
| SRC-069 | 人民日报海外版 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://paper.people.com.cn/rmrbhwb/pc/layout/202610/13/node_01.html) |
| SRC-070 | 海外网 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.haiwainet.cn/) |
| SRC-071 | 人民网 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.people.com.cn/) |
| SRC-072 | 新华网（中文） | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.news.cn/) |
| SRC-073 | 央视网 CCTV | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.cctv.com/) |
| SRC-074 | CNA 亚洲新闻台 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.channelnewsasia.com/world) |
| SRC-075 | ABC Australia | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.abc.net.au/news) |
| SRC-076 | RNZ 新西兰广播电台 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.rnz.co.nz/news) |
| SRC-077 | 证券时报 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.stcn.com/) |
| SRC-078 | 21世纪经济报道 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.21jingji.com/) |
| SRC-079 | 上海证券报 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.cnstock.com/) |
| SRC-080 | 中国证券报 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.cs.com.cn/) |
| SRC-081 | 界面新闻 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.jiemian.com/) |
| SRC-082 | CBS News World | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.cbsnews.com/world/) |
| SRC-083 | VOA 美国之音 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.voanews.com/) |
| SRC-084 | NPR | C 待验证 | UNCONFIRMED | [打开](https://www.npr.org/) |
| SRC-085 | France 24 | C 待验证 | UNCONFIRMED | [打开](https://www.france24.com/en/) |
| SRC-086 | NHK World Japan | C 待验证 | UNCONFIRMED | [打开](https://www3.nhk.or.jp/nhkworld/en/news/) |
| SRC-087 | 澎湃新闻 | C 待验证 | UNCONFIRMED | [打开](https://www.thepaper.cn/) |
| SRC-088 | 第一财经 | C 待验证 | UNCONFIRMED | [打开](https://www.yicai.com/) |
| SRC-089 | 德国之声 DW英文主站 | C 待验证 | UNCONFIRMED | [打开](https://www.dw.com/en/top-stories/s-9097) |
| SRC-092 | The Hindu公开新闻 | C 待验证 | UNCONFIRMED | [打开](https://www.thehindu.com/) |
| SRC-093 | Dawn 巴基斯坦 | C 待验证 | UNCONFIRMED | [打开](https://www.dawn.com/) |
| SRC-094 | Hindustan Times | C 待验证 | UNCONFIRMED | [打开](https://www.hindustantimes.com/) |
| SRC-095 | Arab News | C 待验证 | UNCONFIRMED | [打开](https://www.arabnews.com/) |
| SRC-096 | Africanews | C 待验证 | UNCONFIRMED | [打开](https://www.africanews.com/) |

### 金融

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-009 | SEC EDGAR | A 公开入口 | WEB TOOL API DOCUMENTATION OK | [打开](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) |
| SRC-010 | Federal Reserve | A 公开入口 | WEB TOOL RSS DIRECTORY OK | [打开](https://www.federalreserve.gov/feeds/feeds.htm) |
| SRC-011 | BIS | A 公开入口 | WEB TOOL RSS DIRECTORY OK | [打开](https://www.bis.org/rss) |
| SRC-012 | 摩根大通 Guide to the Markets | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/) |
| SRC-013 | 贝莱德 Investment Institute | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary) |
| SRC-014 | 先锋 Vanguard Outlook | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vanguard-economic-market-outlook.html) |
| SRC-015 | 道富 State Street | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.ssga.com/us/en/individual/insights/featured-insights) |
| SRC-016 | 高盛 Goldman Sachs Research | B 免费部分 | NO DIRECT TEST THIS ROUND | [打开](https://www.goldmansachs.com/insights/goldman-sachs-research/) |
| SRC-017 | 花旗 Citi Institute | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.citigroup.com/global/insights/citi-institute) |
| SRC-018 | 美国银行 BofA Securities | B 免费部分 | NO DIRECT TEST THIS ROUND | [打开](https://business.bofa.com/en-us/content/market-strategies-insights.html) |
| SRC-019 | 摩根士丹利 Insights | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.morganstanley.com/insights/) |
| SRC-020 | 伯克希尔股东信 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.berkshirehathaway.com/letters/letters.html) |
| SRC-021 | Oaktree/Howard Marks | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.oaktreecapital.com/insights) |

### 宏观

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-022 | IMF Data | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://data.imf.org/en/Resource-Pages/IMF-API) |
| SRC-023 | 世界银行 World Bank | A 公开入口 | WEB TOOL JSON RESPONSE OK 2026 10 13 | [打开](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) |
| SRC-024 | OECD | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html) |
| SRC-025 | 国际能源署 IEA | B 免费部分 | NO DIRECT TEST THIS ROUND | [打开](https://www.iea.org/reports) |

### 产业

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-026 | PwC全球CEO调查 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.pwc.com/gx/en/issues/c-suite-insights/ceo-survey.html) |
| SRC-027 | Deloitte Tech Trends | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.deloitte.com/global/en/insights/topics/technology-management/tech-trends.html) |
| SRC-028 | EY CEO Outlook | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.ey.com/en_gl/ceo/ceo-outlook-global-report) |
| SRC-029 | KPMG Insights | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://kpmg.com/xx/en/our-insights.html) |
| SRC-030 | McKinsey Global Institute | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.mckinsey.com/mgi/overview) |
| SRC-031 | BCG | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.bcg.com/publications) |
| SRC-032 | Bain | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.bain.com/insights/) |

### 政治

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-033 | 美国白宫 Presidential Actions | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.whitehouse.gov/presidential-actions/) |
| SRC-034 | Congress.gov | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://api.congress.gov/) |
| SRC-035 | 英国议会 UK Parliament | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.parliament.uk/site-information/rss-feeds/) |
| SRC-036 | 中国国务院政策库 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.gov.cn/zhengce/zhengceku/bmwj/home.htm) |
| SRC-037 | 中国外交部 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.mfa.gov.cn/) |
| SRC-038 | 联合国 UN News | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.un.org/en/events-and-news/) |
| SRC-039 | 欧盟委员会 Press Corner | C 待验证 | NO DIRECT TEST THIS ROUND | [打开](https://ec.europa.eu/commission/presscorner/home/en) |
| SRC-040 | EUISS欧洲安全研究所 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.iss.europa.eu/publications) |
| SRC-098 | CBO美国国会预算办公室 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.cbo.gov/) |
| SRC-099 | GAO美国政府问责局 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.gao.gov/) |
| SRC-100 | Pew Research Center | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.pewresearch.org/) |
| SRC-101 | IAEA国际原子能机构 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.iaea.org/newscenter) |
| SRC-102 | CFR Council on Foreign Relations | C 待验证 | UNCONFIRMED | [打开](https://www.cfr.org/) |
| SRC-103 | Brookings Institution | C 待验证 | UNCONFIRMED | [打开](https://www.brookings.edu/) |
| SRC-104 | Carnegie Endowment | C 待验证 | UNCONFIRMED | [打开](https://carnegieendowment.org/) |
| SRC-105 | Chatham House | C 待验证 | UNCONFIRMED | [打开](https://www.chathamhouse.org/) |
| SRC-106 | European Parliament | C 待验证 | UNCONFIRMED | [打开](https://www.europarl.europa.eu/news/en) |
| SRC-107 | 美国财政部 Treasury | C 待验证 | UNCONFIRMED | [打开](https://home.treasury.gov/news/press-releases) |
| SRC-108 | 英国政府 GOV.UK | C 待验证 | UNCONFIRMED | [打开](https://www.gov.uk/search/news-and-communications) |
| SRC-109 | 中国商务部 MOFCOM | C 待验证 | UNCONFIRMED | [打开](https://www.mofcom.gov.cn/) |
| SRC-110 | 美国联邦公报 Federal Register | C 待验证 | UNCONFIRMED | [打开](https://www.federalregister.gov/) |

### 军事

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-041 | SIPRI军费数据库 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.sipri.org/databases/milex) |
| SRC-042 | NATO | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.nato.int/cps/en/natohq/RSS.htm) |
| SRC-043 | CSIS国防研究 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.csis.org/topics/defense-and-security) |
| SRC-044 | RAND兰德 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.rand.org/pubs/research_reports.html) |
| SRC-045 | IISS公开文章 | B 免费部分 | NO DIRECT TEST THIS ROUND | [打开](https://www.iiss.org/publications/the-military-balance/2026/the-military-balance-2026/global-defence-spending/) |
| SRC-046 | 美国国防部 News | C 待验证 | NO DIRECT TEST THIS ROUND | [打开](https://www.defense.gov/News/) |
| SRC-111 | RUSI | C 待验证 | UNCONFIRMED | [打开](https://www.rusi.org/explore-our-research) |
| SRC-112 | FAS Federation of American Scientists | C 待验证 | UNCONFIRMED | [打开](https://fas.org/) |
| SRC-113 | IISS免费公开Insights | C 待验证 | UNCONFIRMED | [打开](https://www.iiss.org/) |

### AI/科技

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-047 | Google Research | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://research.google/pubs/) |
| SRC-048 | Google DeepMind | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://deepmind.google/research/) |
| SRC-049 | OpenAI Research | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://openai.com/research/) |
| SRC-050 | Anthropic Research | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.anthropic.com/research) |
| SRC-051 | Meta AI Research | C 待验证 | NO DIRECT TEST THIS ROUND | [打开](https://ai.meta.com/research/) |
| SRC-052 | Hugging Face Papers | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://huggingface.co/papers) |
| SRC-053 | arXiv API文档 | C 待验证 | NO DIRECT TEST THIS ROUND | [打开](https://arxiv.org/help/api) |
| SRC-054 | Semantic Scholar API | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://webflow.semanticscholar.org/product/api) |
| SRC-055 | NIST AI Risk Framework | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.nist.gov/itl/ai-risk-management-framework) |
| SRC-056 | NASA News | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.nasa.gov/news/) |
| SRC-119 | Stanford HAI | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://hai.stanford.edu/research) |
| SRC-120 | Microsoft Research | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.microsoft.com/en-us/research/publications/) |
| SRC-121 | NVIDIA技术博客 | C 待验证 | UNCONFIRMED | [打开](https://developer.nvidia.com/blog/) |
| SRC-122 | NeurIPS Proceedings | C 待验证 | UNCONFIRMED | [打开](https://proceedings.neurips.cc/) |
| SRC-123 | CISA美国网络安全与基础设施安全局 | C 待验证 | UNCONFIRMED | [打开](https://www.cisa.gov/news-events) |

### 医疗

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-057 | WHO全球卫生数据库 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.who.int/data/gho/info/athena-api/GHO) |
| SRC-058 | FDA openFDA | A 公开入口 | WEB TOOL JSON RESPONSE OK 2026 10 13 | [打开](https://open.fda.gov/apis/authentication/) |
| SRC-059 | EMA欧洲药品管理局 | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.ema.europa.eu/en/news-events) |
| SRC-060 | ClinicalTrials.gov | A 公开入口 | WEB TOOL API DOCUMENTATION OK ENDPOINT NOT FETCHED | [打开](https://clinicaltrials.gov/data-api/api) |
| SRC-061 | Europe PMC | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://europepmc.org/RestfulWebService) |
| SRC-062 | NCBI/PubMed | C 待验证 | PRIOR BOT CHALLENGE | [打开](https://www.ncbi.nlm.nih.gov/books/NBK25501/) |
| SRC-063 | Nature期刊 | B 免费部分 | NO DIRECT TEST THIS ROUND | [打开](https://www.nature.com/nature/articles) |
| SRC-114 | CDC美国疾病控制中心 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.cdc.gov/) |
| SRC-115 | NIH新闻公告 | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.nih.gov/news-events/news-releases) |
| SRC-116 | medRxiv预印本 | C 待验证 | UNCONFIRMED | [打开](https://www.medrxiv.org/) |
| SRC-117 | 国家药监局 NMPA | C 待验证 | UNCONFIRMED | [打开](https://www.nmpa.gov.cn/) |
| SRC-118 | 国家卫健委 NHC | C 待验证 | UNCONFIRMED | [打开](https://www.nhc.gov.cn/) |

### 社会

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-064 | Our World in Data | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://ourworldindata.org/search) |
| SRC-130 | Our World in Data（社会指标） | C 待验证 | UNCONFIRMED | [打开](https://ourworldindata.org/) |
| SRC-131 | UNDP人类发展报告 | C 待验证 | UNCONFIRMED | [打开](https://hdr.undp.org/) |
| SRC-132 | UN DESA人口 | C 待验证 | UNCONFIRMED | [打开](https://population.un.org/wpp/) |
| SRC-133 | Gallup公开研究 | C 待验证 | UNCONFIRMED | [打开](https://news.gallup.com/) |

### 创业

| ID | 来源 | 状态 | 获取观察 | 官方入口 |
|---|---|---|---|---|
| SRC-065 | Y Combinator RFS | A 公开入口 | WEB TOOL HTML CONTENT OK | [打开](https://www.ycombinator.com/rfs) |
| SRC-066 | Y Combinator Library | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://www.ycombinator.com/library?categories=Diversity+++Inclusion) |
| SRC-067 | a16z | A 公开入口 | NO DIRECT TEST THIS ROUND | [打开](https://a16z.com/) |
| SRC-068 | Sequoia文章 | C 待验证 | NO DIRECT TEST THIS ROUND | [打开](https://www.sequoiacap.com/article/) |
| SRC-124 | First Round Review | C 待验证 | UNCONFIRMED | [打开](https://review.firstround.com/) |
| SRC-125 | Stripe Atlas创业指南 | C 待验证 | UNCONFIRMED | [打开](https://stripe.com/atlas/guides) |
| SRC-126 | Hacker News | C 待验证 | UNCONFIRMED | [打开](https://news.ycombinator.com/) |
| SRC-127 | Product Hunt | C 待验证 | UNCONFIRMED | [打开](https://www.producthunt.com/) |
| SRC-128 | GitHub Trending | C 待验证 | UNCONFIRMED | [打开](https://github.com/trending) |
| SRC-129 | Indie Hackers | C 待验证 | UNCONFIRMED | [打开](https://www.indiehackers.com/) |

## 停用/排除原则
- B只使用真正公开的文章/摘要；**所有需要付费的全文、客户数据库、商业许可证要求的获取方式不进入免费自动采集计划**。
- C先找机构原生RSS/API、免费网页，再评估RSSHub、Trafilatura等合法工具，然后搜索公开渠道；无法确认就保持C，并记下失败原因。不可用黑客手段绕过反爬及收费。
- 定期维护失败状态，发现许可变化时及时停用；严禁把“官网主页打开”冒充“深度研报已完整获得”。
