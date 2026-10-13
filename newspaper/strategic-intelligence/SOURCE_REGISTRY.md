# 内参系统｜全球权威信息源登记（V2.0：云端真实解析校验后）

> 核查日期：2026-10-13。正式名称：**内参系统**。机器主账本 [SOURCE_REGISTRY.json](SOURCE_REGISTRY.json)。

当前130个来源：**A 116**（开放网页、报告或接口有证据）、**B 8**（只使用免费公开部分）、**C 6**（需免费Key、源站合法替代或进一步技术验证）。A不是全文转载许可，也不是已经持续运行。

**新增实测证据：**使用隔离GitHub Actions联网主机进行四轮实际HTTP/XML/JSON测试，部分来源已获取新鲜RSS新闻、研究和API记录，详见 [SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)。**正式连续采集及版权授权仍未验收，production_test在130条中全部为NOT_RUN。**

## 全部来源当前表

| 编号 | 类别 | 来源 | 等级 | 可追踪入口 | 联网实测摘要 |
|---|---|---|---|---|---|
| SRC-001 | 新闻 | AP News | A | [官方/公开入口](https://apnews.com/) | HTML_CONTENT_OK |
| SRC-002 | 新闻 | Reuters World | B | [官方/公开入口](https://www.reuters.com/world/) | HTML_CONTENT_OK |
| SRC-003 | 新闻 | Al Jazeera | A | [官方/公开入口](https://www.aljazeera.com/) | HTML_CONTENT_OK |
| SRC-004 | 新闻 | Deutsche Welle | A | [官方/公开入口](https://rss.dw.com/syndication/feeds/vam_volltextfeedconfirmado.20605-copypaste.html) | No usable content proven; refer to round results |
| SRC-005 | 新闻 | BBC News | A | [官方/公开入口](https://feeds.bbci.co.uk/news/world/rss.xml) | BBC World RSS: HTTP200; 30 entries; 2026-10-12 |
| SRC-006 | 新闻 | 新华社英文站 | A | [官方/公开入口](https://english.news.cn/xinhuanews/index.htm) | No usable content proven; refer to round results |
| SRC-007 | 新闻 | GDELT | A | [官方/公开入口](https://gdeltproject.org/) | HTML_CONTENT_OK |
| SRC-008 | 新闻 | Media Cloud | B | [官方/公开入口](https://www.mediacloud.org/documentation/search-api-guide) | DOCUMENTED_SEARCH_API_WITH_AUTH_NOT_TESTED |
| SRC-009 | 金融 | SEC EDGAR | A | [官方/公开入口](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-010 | 金融 | Federal Reserve | A | [官方/公开入口](https://www.federalreserve.gov/feeds/feeds.htm) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-011 | 金融 | BIS | A | [官方/公开入口](https://www.bis.org/rss) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-012 | 金融 | 摩根大通 Guide to the Markets | A | [官方/公开入口](https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/) | HTML_CONTENT_OK |
| SRC-013 | 金融 | 贝莱德 Investment Institute | A | [官方/公开入口](https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary) | HTML_CONTENT_OK |
| SRC-014 | 金融 | 先锋 Vanguard Outlook | A | [官方/公开入口](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vanguard-economic-market-outlook.html) | HTML_CONTENT_OK |
| SRC-015 | 金融 | 道富 State Street | A | [官方/公开入口](https://www.ssga.com/us/en/individual/insights/featured-insights) | HTML_CONTENT_OK |
| SRC-016 | 金融 | 高盛 Goldman Sachs Research | B | [官方/公开入口](https://www.goldmansachs.com/insights/goldman-sachs-research/) | HTML_CONTENT_OK |
| SRC-017 | 金融 | 花旗 Citi Institute | A | [官方/公开入口](https://www.citigroup.com/global/insights/citi-institute) | HTML_CONTENT_OK |
| SRC-018 | 金融 | 美国银行 BofA Securities | B | [官方/公开入口](https://business.bofa.com/en-us/content/market-strategies-insights.html) | HTML_CONTENT_OK |
| SRC-019 | 金融 | 摩根士丹利 Insights | A | [官方/公开入口](https://www.morganstanley.com/insights/) | HTML_CONTENT_OK |
| SRC-020 | 金融 | 伯克希尔股东信 | A | [官方/公开入口](https://www.berkshirehathaway.com/letters/letters.html) | HTML_CONTENT_OK |
| SRC-021 | 金融 | Oaktree/Howard Marks | A | [官方/公开入口](https://www.oaktreecapital.com/insights) | HTML_CONTENT_OK |
| SRC-022 | 宏观 | IMF Data | A | [官方/公开入口](https://data.imf.org/en/Resource-Pages/IMF-API) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-023 | 宏观 | 世界银行 World Bank | A | [官方/公开入口](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) | LIVE_JSON_API_SAMPLE_AND_DOC_PAGE_OK |
| SRC-024 | 宏观 | OECD | A | [官方/公开入口](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-025 | 宏观 | 国际能源署 IEA | B | [官方/公开入口](https://www.iea.org/reports) | HTML_CONTENT_OK |
| SRC-026 | 产业 | PwC全球CEO调查 | A | [官方/公开入口](https://www.pwc.com/gx/en/issues/c-suite-insights/ceo-survey.html) | HTML_CONTENT_OK |
| SRC-027 | 产业 | Deloitte Tech Trends | A | [官方/公开入口](https://www.deloitte.com/global/en/insights/topics/technology-management/tech-trends.html) | HTML_CONTENT_OK |
| SRC-028 | 产业 | EY CEO Outlook | A | [官方/公开入口](https://www.ey.com/en_gl/ceo/ceo-outlook-global-report) | HTML_CONTENT_OK |
| SRC-029 | 产业 | KPMG Insights | A | [官方/公开入口](https://kpmg.com/xx/en/our-insights.html) | HTML_CONTENT_OK |
| SRC-030 | 产业 | McKinsey Global Institute | A | [官方/公开入口](https://www.mckinsey.com/mgi/overview) | HTML_CONTENT_OK |
| SRC-031 | 产业 | BCG | A | [官方/公开入口](https://www.bcg.com/publications) | HTML_CONTENT_OK |
| SRC-032 | 产业 | Bain | A | [官方/公开入口](https://www.bain.com/insights/) | HTML_CONTENT_OK |
| SRC-033 | 政治 | 美国白宫 Presidential Actions | A | [官方/公开入口](https://www.whitehouse.gov/presidential-actions/) | HTML_CONTENT_OK |
| SRC-034 | 政治 | Congress.gov | C | [官方/公开入口](https://api.congress.gov/) | No usable content proven; refer to round results |
| SRC-035 | 政治 | 英国议会 UK Parliament | A | [官方/公开入口](https://www.parliament.uk/site-information/rss-feeds/) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-036 | 政治 | 中国国务院政策库 | A | [官方/公开入口](https://www.gov.cn/zhengce/zhengceku/bmwj/home.htm) | GOV_CN_POLICY_URL_403_AND_ALTERNATE_REDIRECT_LOOP |
| SRC-037 | 政治 | 中国外交部 | A | [官方/公开入口](https://www.mfa.gov.cn/) | HTML_CONTENT_OK |
| SRC-038 | 政治 | 联合国 UN News | A | [官方/公开入口](https://www.ungeneva.org/en/news-media/rss) | No usable content proven; refer to round results |
| SRC-039 | 政治 | 欧盟委员会 Press Corner | C | [官方/公开入口](https://commission.europa.eu/about/contact/press-services/press-releases-and-notifications_en) | No usable content proven; refer to round results |
| SRC-040 | 政治 | EUISS欧洲安全研究所 | A | [官方/公开入口](https://www.iss.europa.eu/publications) | HTML_CONTENT_OK |
| SRC-041 | 军事 | SIPRI军费数据库 | A | [官方/公开入口](https://www.sipri.org/databases/milex) | HTML_CONTENT_OK |
| SRC-042 | 军事 | NATO | A | [官方/公开入口](https://www.nato.int/cps/en/natohq/RSS.htm) | ALTERNATIVE_OFFICIAL_NEWS_HTML_OK_ORIGINAL_URL_FAIL |
| SRC-043 | 军事 | CSIS国防研究 | A | [官方/公开入口](https://www.csis.org/topics/defense-and-security) | HTML_CONTENT_OK |
| SRC-044 | 军事 | RAND兰德 | A | [官方/公开入口](https://www.rand.org/pubs/research_reports.html) | HTML_CONTENT_OK |
| SRC-045 | 军事 | IISS公开文章 | B | [官方/公开入口](https://www.iiss.org/research/defence-and-military-analysis) | No usable content proven; refer to round results |
| SRC-046 | 军事 | 美国国防部 News | A | [官方/公开入口](https://www.war.gov/News/Releases/News/) | Official defense releases listing: HTTP200 readable HTML; continuous updates not tested |
| SRC-047 | AI/科技 | Google Research | A | [官方/公开入口](https://research.google/pubs/) | HTML_CONTENT_OK |
| SRC-048 | AI/科技 | Google DeepMind | A | [官方/公开入口](https://deepmind.google/research/) | HTML_CONTENT_OK |
| SRC-049 | AI/科技 | OpenAI Research | A | [官方/公开入口](https://openai.com/research/) | HTML_CONTENT_OK |
| SRC-050 | AI/科技 | Anthropic Research | A | [官方/公开入口](https://www.anthropic.com/research) | HTML_CONTENT_OK |
| SRC-051 | AI/科技 | Meta AI Research | A | [官方/公开入口](https://research.meta.ai/) | No usable content proven; refer to round results |
| SRC-052 | AI/科技 | Hugging Face Papers | A | [官方/公开入口](https://huggingface.co/papers) | HTML_CONTENT_OK |
| SRC-053 | AI/科技 | arXiv API文档 | A | [官方/公开入口](https://export.arxiv.org/api/query?search_query=cat%3Acs.AI&sortBy=submittedDate&sortOrder=descending&max_results=1) | arXiv Atom: HTTP200; one result latest 2026-10-09 after sortBy submittedDate |
| SRC-054 | AI/科技 | Semantic Scholar API | A | [官方/公开入口](https://webflow.semanticscholar.org/product/api) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-055 | AI/科技 | NIST AI Risk Framework | A | [官方/公开入口](https://www.nist.gov/itl/ai-risk-management-framework) | HTML_CONTENT_OK |
| SRC-056 | AI/科技 | NASA News | A | [官方/公开入口](https://www.nasa.gov/news/) | HTML_CONTENT_OK |
| SRC-057 | 医疗 | WHO全球卫生数据库 | A | [官方/公开入口](https://www.who.int/data/gho/info/athena-api/GHO) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-058 | 医疗 | FDA openFDA | A | [官方/公开入口](https://open.fda.gov/apis/authentication/) | LIVE_JSON_API_SAMPLE_AND_DOC_PAGE_OK |
| SRC-059 | 医疗 | EMA欧洲药品管理局 | A | [官方/公开入口](https://www.ema.europa.eu/en/news-events) | HTML_CONTENT_OK |
| SRC-060 | 医疗 | ClinicalTrials.gov | A | [官方/公开入口](https://clinicaltrials.gov/api/v2/studies?pageSize=1) | ClinicalTrials API: HTTP200; JSON studies includes NCT00711035 |
| SRC-061 | 医疗 | Europe PMC | A | [官方/公开入口](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=malaria&format=json&pageSize=1) | Europe PMC: HTTP200; JSON resultList contains one real publication |
| SRC-062 | 医疗 | NCBI/PubMed | A | [官方/公开入口](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html) | No usable content proven; refer to round results |
| SRC-063 | 医疗 | Nature期刊 | B | [官方/公开入口](https://www.nature.com/nature/articles) | Nature index HTTP200; OA articles only, paid full text excluded |
| SRC-064 | 社会 | Our World in Data | A | [官方/公开入口](https://ourworldindata.org/) | No usable content proven; refer to round results |
| SRC-065 | 创业 | Y Combinator RFS | A | [官方/公开入口](https://www.ycombinator.com/rfs) | HTML_CONTENT_OK |
| SRC-066 | 创业 | Y Combinator Library | A | [官方/公开入口](https://www.ycombinator.com/library?categories=Diversity+++Inclusion) | YC_LIBRARY_PAGE_OVER_4MB_TOOL_LIMIT |
| SRC-067 | 创业 | a16z | A | [官方/公开入口](https://a16z.com/) | HTML_CONTENT_OK |
| SRC-068 | 创业 | Sequoia文章 | A | [官方/公开入口](https://sequoiacap.com/stories) | No usable content proven; refer to round results |
| SRC-069 | 新闻 | 人民日报海外版 | A | [官方/公开入口](https://paper.people.com.cn/rmrbhwb/pc/layout/202610/13/node_01.html) | HTML_CONTENT_OK |
| SRC-070 | 新闻 | 海外网 | A | [官方/公开入口](https://www.haiwainet.cn/) | HTML_CONTENT_OK |
| SRC-071 | 新闻 | 人民网 | A | [官方/公开入口](https://www.people.com.cn/) | HTML_CONTENT_OK |
| SRC-072 | 新闻 | 新华网（中文） | A | [官方/公开入口](https://www.news.cn/) | HTML_CONTENT_OK |
| SRC-073 | 新闻 | 央视网 CCTV | A | [官方/公开入口](https://www.cctv.com/) | HTML_CONTENT_OK |
| SRC-074 | 新闻 | CNA 亚洲新闻台 | A | [官方/公开入口](https://www.channelnewsasia.com/world) | HTML_CONTENT_OK |
| SRC-075 | 新闻 | ABC Australia | A | [官方/公开入口](https://www.abc.net.au/news) | HTML_CONTENT_OK_BUT_REDIRECTED_TO_SITE_ROOT |
| SRC-076 | 新闻 | RNZ 新西兰广播电台 | A | [官方/公开入口](https://www.rnz.co.nz/news) | HTML_CONTENT_OK_BUT_CACHED_6_MONTHS |
| SRC-077 | 新闻 | 证券时报 | A | [官方/公开入口](https://www.stcn.com/) | HTML_CONTENT_OK |
| SRC-078 | 新闻 | 21世纪经济报道 | A | [官方/公开入口](https://www.21jingji.com/) | HTML_CONTENT_OK |
| SRC-079 | 新闻 | 上海证券报 | A | [官方/公开入口](https://www.cnstock.com/) | HTML_CONTENT_OK |
| SRC-080 | 新闻 | 中国证券报 | A | [官方/公开入口](https://www.cs.com.cn/) | HTML_CONTENT_OK |
| SRC-081 | 新闻 | 界面新闻 | A | [官方/公开入口](https://www.jiemian.com/) | HTML_CONTENT_OK |
| SRC-082 | 新闻 | CBS News World | A | [官方/公开入口](https://www.cbsnews.com/world/) | HTML_CONTENT_OK |
| SRC-083 | 新闻 | VOA 美国之音 | A | [官方/公开入口](https://www.voanews.com/) | HTML_CONTENT_OK |
| SRC-084 | 新闻 | NPR | A | [官方/公开入口](https://feeds.npr.org/1001/rss.xml) | NPR RSS: HTTP200; 10 entries 2026-10-12 |
| SRC-085 | 新闻 | France 24 | A | [官方/公开入口](https://www.france24.com/en/rss) | France24 RSS: HTTP200; 24 entries 2026-10-13 |
| SRC-086 | 新闻 | NHK World Japan | C | [官方/公开入口](https://www3.nhk.or.jp/nhkworld/en/news/) | No usable content proven; refer to round results |
| SRC-087 | 新闻 | 澎湃新闻 | A | [官方/公开入口](https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar) | 澎湃 official public endpoint: HTTP200; JSON data with 45 records |
| SRC-088 | 新闻 | 第一财经 | A | [官方/公开入口](https://www.yicai.com/api/ajax/getlatest?page=1&pagesize=10) | 第一财经 public AJAX: HTTP200; JSON list with 10 records, 2026-10-13 date |
| SRC-089 | 新闻 | 德国之声 DW英文主站 | A | [官方/公开入口](https://rss.dw.com/xml/rss-en-all) | DW English RSS: HTTP200; 137 items dated 2026-10-13 |
| SRC-092 | 新闻 | The Hindu公开新闻 | A | [官方/公开入口](https://www.thehindu.com/) | The Hindu public website: HTTP200 readable HTML |
| SRC-093 | 新闻 | Dawn 巴基斯坦 | A | [官方/公开入口](https://www.dawn.com/) | HTML_CONTENT_OK |
| SRC-094 | 新闻 | Hindustan Times | A | [官方/公开入口](https://www.hindustantimes.com/) | HTML_CONTENT_OK |
| SRC-095 | 新闻 | Arab News | A | [官方/公开入口](https://www.arabnews.com/) | HTML_CONTENT_OK |
| SRC-096 | 新闻 | Africanews | A | [官方/公开入口](https://www.africanews.com/) | HTML_CONTENT_OK |
| SRC-098 | 政治 | CBO美国国会预算办公室 | A | [官方/公开入口](https://www.cbo.gov/) | HTML_CONTENT_OK |
| SRC-099 | 政治 | GAO美国政府问责局 | A | [官方/公开入口](https://www.gao.gov/topics/government-operations?page=1) | No usable content proven; refer to round results |
| SRC-100 | 政治 | Pew Research Center | A | [官方/公开入口](https://www.pewresearch.org/) | HTML_CONTENT_OK |
| SRC-101 | 政治 | IAEA国际原子能机构 | A | [官方/公开入口](https://www.iaea.org/newscenter) | HTML_CONTENT_OK |
| SRC-102 | 政治 | CFR Council on Foreign Relations | A | [官方/公开入口](https://www.cfr.org/) | HTML_CONTENT_OK |
| SRC-103 | 政治 | Brookings Institution | A | [官方/公开入口](https://www.brookings.edu/) | HTML_CONTENT_OK |
| SRC-104 | 政治 | Carnegie Endowment | A | [官方/公开入口](https://carnegieendowment.org/) | HTML_CONTENT_OK |
| SRC-105 | 政治 | Chatham House | A | [官方/公开入口](https://www.chathamhouse.org/) | HTML_CONTENT_OK |
| SRC-106 | 政治 | European Parliament | C | [官方/公开入口](https://www.europarl.europa.eu/news/en/press-room/20260708IPR46377/) | No usable content proven; refer to round results |
| SRC-107 | 政治 | 美国财政部 Treasury | A | [官方/公开入口](https://home.treasury.gov/news/press-releases) | HTML_CONTENT_OK_METADATA_MINIMAL |
| SRC-108 | 政治 | 英国政府 GOV.UK | A | [官方/公开入口](https://www.gov.uk/search/news-and-communications) | HTML_CONTENT_OK |
| SRC-109 | 政治 | 中国商务部 MOFCOM | A | [官方/公开入口](https://www.mofcom.gov.cn/) | HTML_CONTENT_OK |
| SRC-110 | 政治 | 美国联邦公报 Federal Register | A | [官方/公开入口](https://www.federalregister.gov/) | HTML_CONTENT_OK |
| SRC-111 | 军事 | RUSI | A | [官方/公开入口](https://www.rusi.org/explore-our-research) | HTML_CONTENT_OK |
| SRC-112 | 军事 | FAS Federation of American Scientists | A | [官方/公开入口](https://fas.org/) | HTML_CONTENT_OK |
| SRC-113 | 军事 | IISS免费公开Insights | B | [官方/公开入口](https://www.iiss.org/latest/) | No usable content proven; refer to round results |
| SRC-114 | 医疗 | CDC美国疾病控制中心 | A | [官方/公开入口](https://www.cdc.gov/) | HTML_CONTENT_OK |
| SRC-115 | 医疗 | NIH新闻公告 | A | [官方/公开入口](https://www.nih.gov/news-events/news-releases) | HTML_CONTENT_OK |
| SRC-116 | 医疗 | medRxiv预印本 | A | [官方/公开入口](https://connect.medrxiv.org/medrxiv_xml.php?subject=Epidemiology) | medRxiv RSS1.0/RDF: HTTP200; 30 epidemiology items dated 2026-10-12; preprints not peer-reviewed |
| SRC-117 | 医疗 | 国家药监局 NMPA | C | [官方/公开入口](https://www.nmpa.gov.cn/directory/web/nmpa/ylqx/ylqxjgdt/index.html) | No usable content proven; refer to round results |
| SRC-118 | 医疗 | 国家卫健委 NHC | C | [官方/公开入口](https://www.nhc.gov.cn/) | No usable content proven; refer to round results |
| SRC-119 | AI/科技 | Stanford HAI | A | [官方/公开入口](https://hai.stanford.edu/research) | HTML_CONTENT_OK |
| SRC-120 | AI/科技 | Microsoft Research | A | [官方/公开入口](https://www.microsoft.com/en-us/research/publications/) | HTML_CONTENT_OK |
| SRC-121 | AI/科技 | NVIDIA技术博客 | A | [官方/公开入口](https://developer.nvidia.com/blog/) | HTML_CONTENT_OK |
| SRC-122 | AI/科技 | NeurIPS Proceedings | A | [官方/公开入口](https://proceedings.neurips.cc/) | HTML_CONTENT_OK |
| SRC-123 | AI/科技 | CISA美国网络安全与基础设施安全局 | A | [官方/公开入口](https://www.cisa.gov/news-events/cybersecurity-advisories) | CISA alerts listing: HTTP200 readable HTML |
| SRC-124 | 创业 | First Round Review | A | [官方/公开入口](https://review.firstround.com/) | HTML_CONTENT_OK |
| SRC-125 | 创业 | Stripe Atlas创业指南 | A | [官方/公开入口](https://stripe.com/atlas/guides) | HTML_CONTENT_OK |
| SRC-126 | 创业 | Hacker News | A | [官方/公开入口](https://news.ycombinator.com/) | HTML_CONTENT_OK |
| SRC-127 | 创业 | Product Hunt | A | [官方/公开入口](https://www.producthunt.com/) | HTML_CONTENT_OK |
| SRC-128 | 创业 | GitHub Trending | A | [官方/公开入口](https://github.com/trending) | HTML_CONTENT_OK |
| SRC-129 | 创业 | Indie Hackers | A | [官方/公开入口](https://www.indiehackers.com/) | HTML_CONTENT_OK_BUT_CACHED_WEEK |
| SRC-130 | 社会 | Our World in Data（社会指标） | A | [官方/公开入口](https://ourworldindata.org/) | HTML_CONTENT_OK |
| SRC-131 | 社会 | UNDP人类发展报告 | A | [官方/公开入口](https://hdr.undp.org/) | HTML_CONTENT_OK |
| SRC-132 | 社会 | UN DESA人口 | A | [官方/公开入口](https://www.un.org/development/desa/pd/content/world-population-prospects-2024) | UN DESA population research static page: HTTP200; dynamic dataset API not validated |
| SRC-133 | 社会 | Gallup公开研究 | A | [官方/公开入口](https://news.gallup.com/) | HTML_CONTENT_OK |

## 尚未解决的C类来源
- **SRC-034 Congress.gov**：见 [云端测试审计](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)；生产禁用。
- **SRC-039 欧盟委员会 Press Corner**：见 [云端测试审计](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)；生产禁用。
- **SRC-086 NHK World Japan**：见 [云端测试审计](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)；生产禁用。
- **SRC-106 European Parliament**：见 [云端测试审计](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)；生产禁用。
- **SRC-117 国家药监局 NMPA**：见 [云端测试审计](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)；生产禁用。
- **SRC-118 国家卫健委 NHC**：见 [云端测试审计](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)；生产禁用。

## 运行和授权判定
- 获得过一次可用HTML/JSON/RSS结果，不代表多日稳定，也不自动拥有再分发/大规模挖掘许可。
- 机构商业客户专属数据、期刊订阅非OA全文和其它有明确限制的API不纳入免费自动采集；按单份产品记录限制，不封禁整个机构。
- 正式服务引入任何一条来源之前，必须做跨日持续测试、来源独立性与转载去重、发布时间、版权与模型处理条款审核。
