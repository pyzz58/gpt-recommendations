# 全部130个来源逐项访问记录｜2026-10-13

本报告基于**对130条登记网址逐条执行的网页浏览访问**，另抽查官方替代路径，以及世界银行和openFDA实际JSON响应。浏览器代理不等于生产采集环境；130条记录全部仍为 production_test=NOT_RUN。并未逐家取得商业AI处理/转载授权，也未执行跨日稳定性测试。

## 当前候选入口结论

- A（94）：取得公开网页内容、公告/报告目录或API/RSS官方文档，**只说明存在免费公开路径，并非完整正文或定时抓取均可用**。
- B（5）：只有合法公开部分，付费客户报告或封闭全文排除。
- C（31）：访问失败、动态空白、403、反爬、认证页、路径错误或仅有过薄入口；**不得启用生产自动采集**。
- 实际JSON响应：世界银行 https://api.worldbank.org/v2/country/US/indicator/NY.GDP.MKTP.CD?format=json 与 openFDA https://api.fda.gov/drug/label.json?limit=1，均通过网页代理获得而非未来部署主机。

## 逐条访问矩阵

| ID | 机构/来源 | 领域 | 当前状态 | 实测结果 | 原始登记地址 |
|---|---|---|---|---|---|
| SRC-001 | AP News | 新闻 | A | HTML_CONTENT_OK | [入口](https://apnews.com/) |
| SRC-002 | Reuters World | 新闻 | B | HTML_CONTENT_OK | [入口](https://www.reuters.com/world/) |
| SRC-003 | Al Jazeera | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.aljazeera.com/) |
| SRC-004 | Deutsche Welle | 新闻 | C | WRONG_SCOPE_PAGE_IS_SINGLE_VIDEO | [入口](https://amp.dw.com/en/the-day-with-brent-goff/video-19049331) |
| SRC-005 | BBC News | 新闻 | C | BBC_HTML_AND_XML_UNREADABLE_IN_TEST_BROWSER；备用:XML_UNPARSABLE_IN_CURRENT_BROWSER; third-party feed index exists, host parser test pending | [入口](https://www.bbc.com/news) |
| SRC-006 | 新华社英文站 | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://english.news.cn/) |
| SRC-007 | GDELT | 新闻 | A | HTML_CONTENT_OK | [入口](https://gdeltproject.org/) |
| SRC-008 | Media Cloud | 新闻 | B | DOCUMENTED_SEARCH_API_WITH_AUTH_NOT_TESTED | [入口](https://www.mediacloud.org/documentation/search-api-guide) |
| SRC-009 | SEC EDGAR | 金融 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) |
| SRC-010 | Federal Reserve | 金融 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://www.federalreserve.gov/feeds/feeds.htm) |
| SRC-011 | BIS | 金融 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://www.bis.org/rss) |
| SRC-012 | 摩根大通 Guide to the Markets | 金融 | A | HTML_CONTENT_OK | [入口](https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/) |
| SRC-013 | 贝莱德 Investment Institute | 金融 | A | HTML_CONTENT_OK | [入口](https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary) |
| SRC-014 | 先锋 Vanguard Outlook | 金融 | A | HTML_CONTENT_OK | [入口](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vanguard-economic-market-outlook.html) |
| SRC-015 | 道富 State Street | 金融 | A | HTML_CONTENT_OK | [入口](https://www.ssga.com/us/en/individual/insights/featured-insights) |
| SRC-016 | 高盛 Goldman Sachs Research | 金融 | B | HTML_CONTENT_OK | [入口](https://www.goldmansachs.com/insights/goldman-sachs-research/) |
| SRC-017 | 花旗 Citi Institute | 金融 | A | HTML_CONTENT_OK | [入口](https://www.citigroup.com/global/insights/citi-institute) |
| SRC-018 | 美国银行 BofA Securities | 金融 | B | HTML_CONTENT_OK | [入口](https://business.bofa.com/en-us/content/market-strategies-insights.html) |
| SRC-019 | 摩根士丹利 Insights | 金融 | A | HTML_CONTENT_OK | [入口](https://www.morganstanley.com/insights/) |
| SRC-020 | 伯克希尔股东信 | 金融 | A | HTML_CONTENT_OK | [入口](https://www.berkshirehathaway.com/letters/letters.html) |
| SRC-021 | Oaktree/Howard Marks | 金融 | A | HTML_CONTENT_OK | [入口](https://www.oaktreecapital.com/insights) |
| SRC-022 | IMF Data | 宏观 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://data.imf.org/en/Resource-Pages/IMF-API) |
| SRC-023 | 世界银行 World Bank | 宏观 | A | LIVE_JSON_API_SAMPLE_AND_DOC_PAGE_OK | [入口](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) |
| SRC-024 | OECD | 宏观 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html) |
| SRC-025 | 国际能源署 IEA | 宏观 | B | HTML_CONTENT_OK | [入口](https://www.iea.org/reports) |
| SRC-026 | PwC全球CEO调查 | 产业 | A | HTML_CONTENT_OK | [入口](https://www.pwc.com/gx/en/issues/c-suite-insights/ceo-survey.html) |
| SRC-027 | Deloitte Tech Trends | 产业 | A | HTML_CONTENT_OK | [入口](https://www.deloitte.com/global/en/insights/topics/technology-management/tech-trends.html) |
| SRC-028 | EY CEO Outlook | 产业 | A | HTML_CONTENT_OK | [入口](https://www.ey.com/en_gl/ceo/ceo-outlook-global-report) |
| SRC-029 | KPMG Insights | 产业 | A | HTML_CONTENT_OK | [入口](https://kpmg.com/xx/en/our-insights.html) |
| SRC-030 | McKinsey Global Institute | 产业 | A | HTML_CONTENT_OK | [入口](https://www.mckinsey.com/mgi/overview) |
| SRC-031 | BCG | 产业 | A | HTML_CONTENT_OK | [入口](https://www.bcg.com/publications) |
| SRC-032 | Bain | 产业 | A | HTML_CONTENT_OK | [入口](https://www.bain.com/insights/) |
| SRC-033 | 美国白宫 Presidential Actions | 政治 | A | HTML_CONTENT_OK | [入口](https://www.whitehouse.gov/presidential-actions/) |
| SRC-034 | Congress.gov | 政治 | C | API_LANDING_SHELL_ONLY_API_KEY_REQUIRED | [入口](https://api.congress.gov/) |
| SRC-035 | 英国议会 UK Parliament | 政治 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://www.parliament.uk/site-information/rss-feeds/) |
| SRC-036 | 中国国务院政策库 | 政治 | A | GOV_CN_POLICY_URL_403_AND_ALTERNATE_REDIRECT_LOOP | [入口](https://www.gov.cn/zhengce/zhengceku/bmwj/home.htm) |
| SRC-037 | 中国外交部 | 政治 | A | HTML_CONTENT_OK | [入口](https://www.mfa.gov.cn/) |
| SRC-038 | 联合国 UN News | 政治 | C | UN_PAGE_AND_NEWS_UNREADABLE_BROWSER | [入口](https://www.un.org/en/events-and-news/) |
| SRC-039 | 欧盟委员会 Press Corner | 政治 | C | EU_PRESS_CORNER_DYNAMIC_EMPTY | [入口](https://ec.europa.eu/commission/presscorner/home/en) |
| SRC-040 | EUISS欧洲安全研究所 | 政治 | A | HTML_CONTENT_OK | [入口](https://www.iss.europa.eu/publications) |
| SRC-041 | SIPRI军费数据库 | 军事 | A | HTML_CONTENT_OK | [入口](https://www.sipri.org/databases/milex) |
| SRC-042 | NATO | 军事 | A | ALTERNATIVE_OFFICIAL_NEWS_HTML_OK_ORIGINAL_URL_FAIL；备用:PUBLIC_HTML_OK | [入口](https://www.nato.int/cps/en/natohq/RSS.htm) |
| SRC-043 | CSIS国防研究 | 军事 | A | HTML_CONTENT_OK | [入口](https://www.csis.org/topics/defense-and-security) |
| SRC-044 | RAND兰德 | 军事 | A | HTML_CONTENT_OK | [入口](https://www.rand.org/pubs/research_reports.html) |
| SRC-045 | IISS公开文章 | 军事 | C | IISS_PAGE_TITLE_OR_LOGIN_ONLY | [入口](https://www.iiss.org/publications/the-military-balance/2026/the-military-balance-2026/global-defence-spending/) |
| SRC-046 | 美国国防部 News | 军事 | C | PAGE_NOT_RETRIEVED | [入口](https://www.defense.gov/News/) |
| SRC-047 | Google Research | AI/科技 | A | HTML_CONTENT_OK | [入口](https://research.google/pubs/) |
| SRC-048 | Google DeepMind | AI/科技 | A | HTML_CONTENT_OK | [入口](https://deepmind.google/research/) |
| SRC-049 | OpenAI Research | AI/科技 | A | HTML_CONTENT_OK | [入口](https://openai.com/research/) |
| SRC-050 | Anthropic Research | AI/科技 | A | HTML_CONTENT_OK | [入口](https://www.anthropic.com/research) |
| SRC-051 | Meta AI Research | AI/科技 | C | META_AI_DYNAMIC_EMPTY | [入口](https://ai.meta.com/research/) |
| SRC-052 | Hugging Face Papers | AI/科技 | A | HTML_CONTENT_OK | [入口](https://huggingface.co/papers) |
| SRC-053 | arXiv API文档 | AI/科技 | C | ARXIV_API_DOCUMENTATION_BLOCKED_AT_CURRENT_PATH | [入口](https://arxiv.org/help/api) |
| SRC-054 | Semantic Scholar API | AI/科技 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://webflow.semanticscholar.org/product/api) |
| SRC-055 | NIST AI Risk Framework | AI/科技 | A | HTML_CONTENT_OK | [入口](https://www.nist.gov/itl/ai-risk-management-framework) |
| SRC-056 | NASA News | AI/科技 | A | HTML_CONTENT_OK | [入口](https://www.nasa.gov/news/) |
| SRC-057 | WHO全球卫生数据库 | 医疗 | A | API_OR_RSS_DOCUMENTATION_PAGE | [入口](https://www.who.int/data/gho/info/athena-api/GHO) |
| SRC-058 | FDA openFDA | 医疗 | A | LIVE_JSON_API_SAMPLE_AND_DOC_PAGE_OK | [入口](https://open.fda.gov/apis/authentication/) |
| SRC-059 | EMA欧洲药品管理局 | 医疗 | A | HTML_CONTENT_OK | [入口](https://www.ema.europa.eu/en/news-events) |
| SRC-060 | ClinicalTrials.gov | 医疗 | C | API_DOC_SHELL_ENDPOINT_UNTESTED | [入口](https://clinicaltrials.gov/data-api/api) |
| SRC-061 | Europe PMC | 医疗 | C | EUROPE_PMC_API_DOCUMENTATION_BLOCKED | [入口](https://europepmc.org/RestfulWebService) |
| SRC-062 | NCBI/PubMed | 医疗 | C | NCBI_RECAPTCHA_BLOCKED | [入口](https://www.ncbi.nlm.nih.gov/books/NBK25501/) |
| SRC-063 | Nature期刊 | 医疗 | C | COOKIE_ERROR_WITH_PARTIAL_LISTING | [入口](https://www.nature.com/nature/articles) |
| SRC-064 | Our World in Data | 社会 | C | SEARCH_SHELL_PAGE_ONLY | [入口](https://ourworldindata.org/search) |
| SRC-065 | Y Combinator RFS | 创业 | A | HTML_CONTENT_OK | [入口](https://www.ycombinator.com/rfs) |
| SRC-066 | Y Combinator Library | 创业 | A | YC_LIBRARY_PAGE_OVER_4MB_TOOL_LIMIT | [入口](https://www.ycombinator.com/library?categories=Diversity+++Inclusion) |
| SRC-067 | a16z | 创业 | A | HTML_CONTENT_OK | [入口](https://a16z.com/) |
| SRC-068 | Sequoia文章 | 创业 | C | PAGE_NOT_RETRIEVED | [入口](https://www.sequoiacap.com/article/) |
| SRC-069 | 人民日报海外版 | 新闻 | A | HTML_CONTENT_OK | [入口](https://paper.people.com.cn/rmrbhwb/pc/layout/202610/13/node_01.html) |
| SRC-070 | 海外网 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.haiwainet.cn/) |
| SRC-071 | 人民网 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.people.com.cn/) |
| SRC-072 | 新华网（中文） | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.news.cn/) |
| SRC-073 | 央视网 CCTV | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.cctv.com/) |
| SRC-074 | CNA 亚洲新闻台 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.channelnewsasia.com/world) |
| SRC-075 | ABC Australia | 新闻 | A | HTML_CONTENT_OK_BUT_REDIRECTED_TO_SITE_ROOT | [入口](https://www.abc.net.au/news) |
| SRC-076 | RNZ 新西兰广播电台 | 新闻 | A | HTML_CONTENT_OK_BUT_CACHED_6_MONTHS | [入口](https://www.rnz.co.nz/news) |
| SRC-077 | 证券时报 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.stcn.com/) |
| SRC-078 | 21世纪经济报道 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.21jingji.com/) |
| SRC-079 | 上海证券报 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.cnstock.com/) |
| SRC-080 | 中国证券报 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.cs.com.cn/) |
| SRC-081 | 界面新闻 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.jiemian.com/) |
| SRC-082 | CBS News World | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.cbsnews.com/world/) |
| SRC-083 | VOA 美国之音 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.voanews.com/) |
| SRC-084 | NPR | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://www.npr.org/) |
| SRC-085 | France 24 | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://www.france24.com/en/) |
| SRC-086 | NHK World Japan | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://www3.nhk.or.jp/nhkworld/en/news/) |
| SRC-087 | 澎湃新闻 | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://www.thepaper.cn/) |
| SRC-088 | 第一财经 | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://www.yicai.com/) |
| SRC-089 | 德国之声 DW英文主站 | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://www.dw.com/en/top-stories/s-9097) |
| SRC-092 | The Hindu公开新闻 | 新闻 | C | PAGE_NOT_RETRIEVED | [入口](https://www.thehindu.com/) |
| SRC-093 | Dawn 巴基斯坦 | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.dawn.com/) |
| SRC-094 | Hindustan Times | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.hindustantimes.com/) |
| SRC-095 | Arab News | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.arabnews.com/) |
| SRC-096 | Africanews | 新闻 | A | HTML_CONTENT_OK | [入口](https://www.africanews.com/) |
| SRC-098 | CBO美国国会预算办公室 | 政治 | A | HTML_CONTENT_OK | [入口](https://www.cbo.gov/) |
| SRC-099 | GAO美国政府问责局 | 政治 | C | GAO_MAIN_PAGE_UNREADABLE_BROWSER | [入口](https://www.gao.gov/) |
| SRC-100 | Pew Research Center | 政治 | A | HTML_CONTENT_OK | [入口](https://www.pewresearch.org/) |
| SRC-101 | IAEA国际原子能机构 | 政治 | A | HTML_CONTENT_OK | [入口](https://www.iaea.org/newscenter) |
| SRC-102 | CFR Council on Foreign Relations | 政治 | A | HTML_CONTENT_OK | [入口](https://www.cfr.org/) |
| SRC-103 | Brookings Institution | 政治 | A | HTML_CONTENT_OK | [入口](https://www.brookings.edu/) |
| SRC-104 | Carnegie Endowment | 政治 | A | HTML_CONTENT_OK | [入口](https://carnegieendowment.org/) |
| SRC-105 | Chatham House | 政治 | A | HTML_CONTENT_OK | [入口](https://www.chathamhouse.org/) |
| SRC-106 | European Parliament | 政治 | C | EUROPEAN_PARLIAMENT_MINIMAL_SHELL | [入口](https://www.europarl.europa.eu/news/en) |
| SRC-107 | 美国财政部 Treasury | 政治 | A | HTML_CONTENT_OK_METADATA_MINIMAL | [入口](https://home.treasury.gov/news/press-releases) |
| SRC-108 | 英国政府 GOV.UK | 政治 | A | HTML_CONTENT_OK | [入口](https://www.gov.uk/search/news-and-communications) |
| SRC-109 | 中国商务部 MOFCOM | 政治 | A | HTML_CONTENT_OK | [入口](https://www.mofcom.gov.cn/) |
| SRC-110 | 美国联邦公报 Federal Register | 政治 | A | HTML_CONTENT_OK | [入口](https://www.federalregister.gov/) |
| SRC-111 | RUSI | 军事 | A | HTML_CONTENT_OK | [入口](https://www.rusi.org/explore-our-research) |
| SRC-112 | FAS Federation of American Scientists | 军事 | A | HTML_CONTENT_OK | [入口](https://fas.org/) |
| SRC-113 | IISS免费公开Insights | 军事 | C | IISS_PAGE_TITLE_OR_LOGIN_ONLY | [入口](https://www.iiss.org/) |
| SRC-114 | CDC美国疾病控制中心 | 医疗 | A | HTML_CONTENT_OK | [入口](https://www.cdc.gov/) |
| SRC-115 | NIH新闻公告 | 医疗 | A | HTML_CONTENT_OK | [入口](https://www.nih.gov/news-events/news-releases) |
| SRC-116 | medRxiv预印本 | 医疗 | C | PAGE_NOT_RETRIEVED | [入口](https://www.medrxiv.org/) |
| SRC-117 | 国家药监局 NMPA | 医疗 | C | PAGE_NOT_RETRIEVED | [入口](https://www.nmpa.gov.cn/) |
| SRC-118 | 国家卫健委 NHC | 医疗 | C | PAGE_NOT_RETRIEVED | [入口](https://www.nhc.gov.cn/) |
| SRC-119 | Stanford HAI | AI/科技 | A | HTML_CONTENT_OK | [入口](https://hai.stanford.edu/research) |
| SRC-120 | Microsoft Research | AI/科技 | A | HTML_CONTENT_OK | [入口](https://www.microsoft.com/en-us/research/publications/) |
| SRC-121 | NVIDIA技术博客 | AI/科技 | A | HTML_CONTENT_OK | [入口](https://developer.nvidia.com/blog/) |
| SRC-122 | NeurIPS Proceedings | AI/科技 | A | HTML_CONTENT_OK | [入口](https://proceedings.neurips.cc/) |
| SRC-123 | CISA美国网络安全与基础设施安全局 | AI/科技 | C | CISA_MAIN_PAGE_UNREADABLE_BROWSER | [入口](https://www.cisa.gov/news-events) |
| SRC-124 | First Round Review | 创业 | A | HTML_CONTENT_OK | [入口](https://review.firstround.com/) |
| SRC-125 | Stripe Atlas创业指南 | 创业 | A | HTML_CONTENT_OK | [入口](https://stripe.com/atlas/guides) |
| SRC-126 | Hacker News | 创业 | A | HTML_CONTENT_OK | [入口](https://news.ycombinator.com/) |
| SRC-127 | Product Hunt | 创业 | A | HTML_CONTENT_OK | [入口](https://www.producthunt.com/) |
| SRC-128 | GitHub Trending | 创业 | A | HTML_CONTENT_OK | [入口](https://github.com/trending) |
| SRC-129 | Indie Hackers | 创业 | A | HTML_CONTENT_OK_BUT_CACHED_WEEK | [入口](https://www.indiehackers.com/) |
| SRC-130 | Our World in Data（社会指标） | 社会 | A | HTML_CONTENT_OK | [入口](https://ourworldindata.org/) |
| SRC-131 | UNDP人类发展报告 | 社会 | A | HTML_CONTENT_OK | [入口](https://hdr.undp.org/) |
| SRC-132 | UN DESA人口 | 社会 | C | UN_POPULATION_DYNAMIC_EMPTY | [入口](https://population.un.org/wpp/) |
| SRC-133 | Gallup公开研究 | 社会 | A | HTML_CONTENT_OK | [入口](https://news.gallup.com/) |

## 重点限制与待修复的真实障碍

1. BBC原站与RSS XML无法被本次网页解析器提取；需从有外网权限主机用XML客户端验证。不是BBC确定失效。
2. 人民日报海外版、新华网中文、Reuters/AP部分公开文章、国际地区媒体可以读取，但源站许可、批量处理及人工可见性是三件事。
3. NATO旧RSS页不可读，官方新闻替代入口 https://www.nato.int/cps/en/natohq/news.htm 已经可读。
4. 中国国务院政策库页面在此工具403，联合国及美国国防部部分页面失败，不能冒称成功。国务院政策其他版本检索存在，但当前浏览器也遭403/跳转循环。
5. Sequoia和YC Library在本工具中未成功（后者页面体积大于4MB），仍保留C等待寻找单篇/合规订阅入口。
6. RNZ查询来自约6个月前缓存，不足以证明实时更新；其它媒体需实际核查文章来源发布时间。
7. 部分机构只是索引：SEC/IMF/OECD/WHO/ClinicalTrials等存在官方API文档，但并未都执行实际数据提取。World Bank和FDA是两项取得JSON结果的独立示例。
8. 付费完整研究、AI用途禁止或新闻转载商业许可证另见SOURCE_ACCESS_BLOCKLIST.md；RSSHub/Trafilatura不是授权工具。

## 网络环境与后续门禁

当前容器对任意公网域名做requests实测时返回DNS NameResolutionError。网页代理能验证一定数量的HTML/JSON，但不能当作真实宿主机端到端测试。下一阶段按SOURCE_VERIFICATION_PLAYBOOK.md通过合法HTTP/RSS/API在测试主机逐源请求、解析至少1个新条目，记录状态码、content-type、文章日期、正文覆盖范围和实际许可，再连续跨日测试。不得自动部署或推送日报邮件。
