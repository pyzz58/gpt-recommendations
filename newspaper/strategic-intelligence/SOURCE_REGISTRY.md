# 内参系统｜全球权威信息来源登记表 V1.9

> 最后核查：2026-10-13。规范名称：**内参系统**（GSI）。机器可读主账本：[SOURCE_REGISTRY.json](SOURCE_REGISTRY.json)。
>
> **状态表示公开入口可获证据的水平，不表示已经获得批量全文下载、AI处理许可或生产定时抓取。**

当前共 **130** 条：**A 102（公开网页/官方文档）**、**B 7（仅公开部分）**、**C 21（待实际解析或仍受访问限制）**。全部生产环境自动采集测试 **0/130**。

## 来源分类和判定规则
- **A**：通过公网浏览器取得实质公开文章/栏目，或取得官方RSS/API说明。准确到“正文 / 标题 / 元信息 / API文档”细粒度级别请看单条记录；A绝不自动等于全文采集成功。
- **B**：仅免费公开文章/部分报告可用。任何专有付费部分始终排除，见 [SOURCE_ACCESS_BLOCKLIST.md](SOURCE_ACCESS_BLOCKLIST.md)。
- **C**：需要密钥、标准XML解析、合法页面替代、处理403/412/robots/JS，或者当前只找到索引而没有可取正文。此类不能默认进入生产。
- 不使用盗取、绕过付费墙、冒充受限用户或违反站点授权的方法。
- 新补救详见 [SOURCE_RECOVERY_AUDIT_2026-10-13.md](SOURCE_RECOVERY_AUDIT_2026-10-13.md)；此前逐项URL访问见 [ACCESS_AUDIT_2026-10-13_FULL.md](ACCESS_AUDIT_2026-10-13_FULL.md)。

## 全部来源

| 编号 | 领域 | 来源 | 状态 | 推荐公开入口 | 验证提示 |
|---|---|---|---|---|---|
| SRC-001 | 新闻 | AP News | **A** | [官方/说明](https://apnews.com/) | HTML_CONTENT_OK |
| SRC-002 | 新闻 | Reuters World | **B** | [官方/说明](https://www.reuters.com/world/) | HTML_CONTENT_OK |
| SRC-003 | 新闻 | Al Jazeera | **A** | [官方/说明](https://www.aljazeera.com/) | HTML_CONTENT_OK |
| SRC-004 | 新闻 | Deutsche Welle | **A** | [官方/说明](https://rss.dw.com/syndication/feeds/vam_volltextfeedconfirmado.20605-copypaste.html) | PUBLIC_HTML_ALTERNATE；DW官方西班牙语公开供稿HTML含2026-10-12日期、标题及正文；并非英文版，版权和二次使用另审。 |
| SRC-005 | 新闻 | BBC News | **C** | [官方/说明](https://feeds.bbci.co.uk/news/world/rss.xml) | FREE_RSS_XML_BROWSER_UNSUPPORTED；BBC World RSS存在2026年9月第三方逐项更新检验；本轮web.open返回text/xml，浏览器无法解析，须联网Python解析并核验BBC使用条款。 |
| SRC-006 | 新闻 | 新华社英文站 | **A** | [官方/说明](https://english.news.cn/xinhuanews/index.htm) | PUBLIC_HTML_ALTERNATE；官方英文栏目直读，2026-10-13新闻标题、时间与文章链接均出现。 |
| SRC-007 | 新闻 | GDELT | **A** | [官方/说明](https://gdeltproject.org/) | HTML_CONTENT_OK |
| SRC-008 | 新闻 | Media Cloud | **B** | [官方/说明](https://www.mediacloud.org/documentation/search-api-guide) | DOCUMENTED_SEARCH_API_WITH_AUTH_NOT_TESTED |
| SRC-009 | 金融 | SEC EDGAR | **A** | [官方/说明](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-010 | 金融 | Federal Reserve | **A** | [官方/说明](https://www.federalreserve.gov/feeds/feeds.htm) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-011 | 金融 | BIS | **A** | [官方/说明](https://www.bis.org/rss) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-012 | 金融 | 摩根大通 Guide to the Markets | **A** | [官方/说明](https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/) | HTML_CONTENT_OK |
| SRC-013 | 金融 | 贝莱德 Investment Institute | **A** | [官方/说明](https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary) | HTML_CONTENT_OK |
| SRC-014 | 金融 | 先锋 Vanguard Outlook | **A** | [官方/说明](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vanguard-economic-market-outlook.html) | HTML_CONTENT_OK |
| SRC-015 | 金融 | 道富 State Street | **A** | [官方/说明](https://www.ssga.com/us/en/individual/insights/featured-insights) | HTML_CONTENT_OK |
| SRC-016 | 金融 | 高盛 Goldman Sachs Research | **B** | [官方/说明](https://www.goldmansachs.com/insights/goldman-sachs-research/) | HTML_CONTENT_OK |
| SRC-017 | 金融 | 花旗 Citi Institute | **A** | [官方/说明](https://www.citigroup.com/global/insights/citi-institute) | HTML_CONTENT_OK |
| SRC-018 | 金融 | 美国银行 BofA Securities | **B** | [官方/说明](https://business.bofa.com/en-us/content/market-strategies-insights.html) | HTML_CONTENT_OK |
| SRC-019 | 金融 | 摩根士丹利 Insights | **A** | [官方/说明](https://www.morganstanley.com/insights/) | HTML_CONTENT_OK |
| SRC-020 | 金融 | 伯克希尔股东信 | **A** | [官方/说明](https://www.berkshirehathaway.com/letters/letters.html) | HTML_CONTENT_OK |
| SRC-021 | 金融 | Oaktree/Howard Marks | **A** | [官方/说明](https://www.oaktreecapital.com/insights) | HTML_CONTENT_OK |
| SRC-022 | 宏观 | IMF Data | **A** | [官方/说明](https://data.imf.org/en/Resource-Pages/IMF-API) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-023 | 宏观 | 世界银行 World Bank | **A** | [官方/说明](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) | LIVE_JSON_API_SAMPLE_AND_DOC_PAGE_OK |
| SRC-024 | 宏观 | OECD | **A** | [官方/说明](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-025 | 宏观 | 国际能源署 IEA | **B** | [官方/说明](https://www.iea.org/reports) | HTML_CONTENT_OK |
| SRC-026 | 产业 | PwC全球CEO调查 | **A** | [官方/说明](https://www.pwc.com/gx/en/issues/c-suite-insights/ceo-survey.html) | HTML_CONTENT_OK |
| SRC-027 | 产业 | Deloitte Tech Trends | **A** | [官方/说明](https://www.deloitte.com/global/en/insights/topics/technology-management/tech-trends.html) | HTML_CONTENT_OK |
| SRC-028 | 产业 | EY CEO Outlook | **A** | [官方/说明](https://www.ey.com/en_gl/ceo/ceo-outlook-global-report) | HTML_CONTENT_OK |
| SRC-029 | 产业 | KPMG Insights | **A** | [官方/说明](https://kpmg.com/xx/en/our-insights.html) | HTML_CONTENT_OK |
| SRC-030 | 产业 | McKinsey Global Institute | **A** | [官方/说明](https://www.mckinsey.com/mgi/overview) | HTML_CONTENT_OK |
| SRC-031 | 产业 | BCG | **A** | [官方/说明](https://www.bcg.com/publications) | HTML_CONTENT_OK |
| SRC-032 | 产业 | Bain | **A** | [官方/说明](https://www.bain.com/insights/) | HTML_CONTENT_OK |
| SRC-033 | 政治 | 美国白宫 Presidential Actions | **A** | [官方/说明](https://www.whitehouse.gov/presidential-actions/) | HTML_CONTENT_OK |
| SRC-034 | 政治 | Congress.gov | **C** | [官方/说明](https://api.congress.gov/) | FREE_ACCOUNT_KEY_REQUIRED；美国国会公开v3 API确实存在，但需免费api.data.gov密钥；未取得密钥也未请求真实法案JSON。可先用国会公开网页。 |
| SRC-035 | 政治 | 英国议会 UK Parliament | **A** | [官方/说明](https://www.parliament.uk/site-information/rss-feeds/) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-036 | 政治 | 中国国务院政策库 | **A** | [官方/说明](https://www.gov.cn/zhengce/zhengceku/bmwj/home.htm) | GOV_CN_POLICY_URL_403_AND_ALTERNATE_REDIRECT_LOOP |
| SRC-037 | 政治 | 中国外交部 | **A** | [官方/说明](https://www.mfa.gov.cn/) | HTML_CONTENT_OK |
| SRC-038 | 政治 | 联合国 UN News | **A** | [官方/说明](https://www.ungeneva.org/en/news-media/rss) | OFFICIAL_RSS_DIRECTORY_HTML；联合国日内瓦办事处官方RSS目录可读，链接新闻稿、会议记录、总部按主题订阅；RSS条目尚待XML实际解析。 |
| SRC-039 | 政治 | 欧盟委员会 Press Corner | **C** | [官方/说明](https://commission.europa.eu/about/contact/press-services/press-releases-and-notifications_en) | OFFICIAL_EMAIL_SUBSCRIPTION_DOCUMENTED；欧委会官方明确支持按主题订阅Press Corner新闻邮件，网页内容可读；尚未取得可无需登录直接采集的发布列表。 |
| SRC-040 | 政治 | EUISS欧洲安全研究所 | **A** | [官方/说明](https://www.iss.europa.eu/publications) | HTML_CONTENT_OK |
| SRC-041 | 军事 | SIPRI军费数据库 | **A** | [官方/说明](https://www.sipri.org/databases/milex) | HTML_CONTENT_OK |
| SRC-042 | 军事 | NATO | **A** | [官方/说明](https://www.nato.int/cps/en/natohq/RSS.htm) | ALTERNATIVE_OFFICIAL_NEWS_HTML_OK_ORIGINAL_URL_FAIL |
| SRC-043 | 军事 | CSIS国防研究 | **A** | [官方/说明](https://www.csis.org/topics/defense-and-security) | HTML_CONTENT_OK |
| SRC-044 | 军事 | RAND兰德 | **A** | [官方/说明](https://www.rand.org/pubs/research_reports.html) | HTML_CONTENT_OK |
| SRC-045 | 军事 | IISS公开文章 | **B** | [官方/说明](https://www.iiss.org/research/defence-and-military-analysis) | FREE_TAGGED_ANALYSIS_SUBSET；IISS官方公开研究频道与明确标为Free to Read的部分文章可找到，完整Military Balance+继续付费排除；具体免费全文按篇核验。 |
| SRC-046 | 军事 | 美国国防部 News | **C** | [官方/说明](https://www.war.gov/News/Releases/News/) | OFFICIAL_ALTERNATIVE_INDEXED_BROWSER_403；官方新域名war.gov新闻发布列表已被搜索索引收录，但直接web.open本轮403；不能标机器接口可用，需合法联网宿主机或订阅验证。 |
| SRC-047 | AI/科技 | Google Research | **A** | [官方/说明](https://research.google/pubs/) | HTML_CONTENT_OK |
| SRC-048 | AI/科技 | Google DeepMind | **A** | [官方/说明](https://deepmind.google/research/) | HTML_CONTENT_OK |
| SRC-049 | AI/科技 | OpenAI Research | **A** | [官方/说明](https://openai.com/research/) | HTML_CONTENT_OK |
| SRC-050 | AI/科技 | Anthropic Research | **A** | [官方/说明](https://www.anthropic.com/research) | HTML_CONTENT_OK |
| SRC-051 | AI/科技 | Meta AI Research | **A** | [官方/说明](https://research.meta.ai/) | PUBLIC_HTML_ALTERNATE；Meta AI独立官方研究站点直接返回2026-10-12研究更新及文章链接。 |
| SRC-052 | AI/科技 | Hugging Face Papers | **A** | [官方/说明](https://huggingface.co/papers) | HTML_CONTENT_OK |
| SRC-053 | AI/科技 | arXiv API文档 | **C** | [官方/说明](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/api/user-manual.md) | OFFICIAL_GITHUB_API_DOC_READABLE_ATOM_UNTESTED；arXiv官方GitHub API手册可读，说明开放Atom搜索接口；实际API XML数据在本环境未能解析或确认。 |
| SRC-054 | AI/科技 | Semantic Scholar API | **A** | [官方/说明](https://webflow.semanticscholar.org/product/api) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-055 | AI/科技 | NIST AI Risk Framework | **A** | [官方/说明](https://www.nist.gov/itl/ai-risk-management-framework) | HTML_CONTENT_OK |
| SRC-056 | AI/科技 | NASA News | **A** | [官方/说明](https://www.nasa.gov/news/) | HTML_CONTENT_OK |
| SRC-057 | 医疗 | WHO全球卫生数据库 | **A** | [官方/说明](https://www.who.int/data/gho/info/athena-api/GHO) | API_OR_RSS_DOCUMENTATION_PAGE |
| SRC-058 | 医疗 | FDA openFDA | **A** | [官方/说明](https://open.fda.gov/apis/authentication/) | LIVE_JSON_API_SAMPLE_AND_DOC_PAGE_OK |
| SRC-059 | 医疗 | EMA欧洲药品管理局 | **A** | [官方/说明](https://www.ema.europa.eu/en/news-events) | HTML_CONTENT_OK |
| SRC-060 | 医疗 | ClinicalTrials.gov | **C** | [官方/说明](https://clinicaltrials.gov/api/v2/studies) | OFFICIAL_JSON_API_DOC_ENDPOINT_UNTESTED；ClinicalTrials.gov公开v2接口有规范，但当前网页工具对实际JSON请求无法返回可解析数据；仍待联网运行环境确认。 |
| SRC-061 | 医疗 | Europe PMC | **C** | [官方/说明](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=p53&format=json) | OFFICIAL_REST_DOC_SEARCH_INDEXED_ENDPOINT_UNTESTED；Europe PMC文档明确公开JSON/XML REST检索；直接API请求在当前Web工具无法解析，不能报成功。 |
| SRC-062 | 医疗 | NCBI/PubMed | **A** | [官方/说明](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html) | OFFICIAL_API_DOCUMENTATION_HTML_ONLY；NLM官方E-Utilities文档可读并说明PubMed ESearch等；实际文献数据接口尚未进行运行宿主机烟测。 |
| SRC-063 | 医疗 | Nature期刊 | **C** | [官方/说明](https://www.nature.com/nature/articles) | OA_SUBSET_UNVERIFIED_BROWSER_COOKIE；Nature非OA全文依旧需订阅；公开目录和OA子集待逐篇检测，不使用付费正文。 |
| SRC-064 | 社会 | Our World in Data | **A** | [官方/说明](https://ourworldindata.org/) | PUBLIC_HTML_AND_DOCUMENTED_CSV_API；OWID主站可直接读取公开数据研究文章；官方文档列出Grapher CSV数据端点，端点逐项授权另审。 |
| SRC-065 | 创业 | Y Combinator RFS | **A** | [官方/说明](https://www.ycombinator.com/rfs) | HTML_CONTENT_OK |
| SRC-066 | 创业 | Y Combinator Library | **A** | [官方/说明](https://www.ycombinator.com/library?categories=Diversity+++Inclusion) | YC_LIBRARY_PAGE_OVER_4MB_TOOL_LIMIT |
| SRC-067 | 创业 | a16z | **A** | [官方/说明](https://a16z.com/) | HTML_CONTENT_OK |
| SRC-068 | 创业 | Sequoia文章 | **A** | [官方/说明](https://sequoiacap.com/stories) | PUBLIC_HTML_ALTERNATE；红杉官方新版Stories目录及创业案例链接可直接读取，原/sequoiacap.com/article/为404应退役。 |
| SRC-069 | 新闻 | 人民日报海外版 | **A** | [官方/说明](https://paper.people.com.cn/rmrbhwb/pc/layout/202610/13/node_01.html) | HTML_CONTENT_OK |
| SRC-070 | 新闻 | 海外网 | **A** | [官方/说明](https://www.haiwainet.cn/) | HTML_CONTENT_OK |
| SRC-071 | 新闻 | 人民网 | **A** | [官方/说明](https://www.people.com.cn/) | HTML_CONTENT_OK |
| SRC-072 | 新闻 | 新华网（中文） | **A** | [官方/说明](https://www.news.cn/) | HTML_CONTENT_OK |
| SRC-073 | 新闻 | 央视网 CCTV | **A** | [官方/说明](https://www.cctv.com/) | HTML_CONTENT_OK |
| SRC-074 | 新闻 | CNA 亚洲新闻台 | **A** | [官方/说明](https://www.channelnewsasia.com/world) | HTML_CONTENT_OK |
| SRC-075 | 新闻 | ABC Australia | **A** | [官方/说明](https://www.abc.net.au/news) | HTML_CONTENT_OK_BUT_REDIRECTED_TO_SITE_ROOT |
| SRC-076 | 新闻 | RNZ 新西兰广播电台 | **A** | [官方/说明](https://www.rnz.co.nz/news) | HTML_CONTENT_OK_BUT_CACHED_6_MONTHS |
| SRC-077 | 新闻 | 证券时报 | **A** | [官方/说明](https://www.stcn.com/) | HTML_CONTENT_OK |
| SRC-078 | 新闻 | 21世纪经济报道 | **A** | [官方/说明](https://www.21jingji.com/) | HTML_CONTENT_OK |
| SRC-079 | 新闻 | 上海证券报 | **A** | [官方/说明](https://www.cnstock.com/) | HTML_CONTENT_OK |
| SRC-080 | 新闻 | 中国证券报 | **A** | [官方/说明](https://www.cs.com.cn/) | HTML_CONTENT_OK |
| SRC-081 | 新闻 | 界面新闻 | **A** | [官方/说明](https://www.jiemian.com/) | HTML_CONTENT_OK |
| SRC-082 | 新闻 | CBS News World | **A** | [官方/说明](https://www.cbsnews.com/world/) | HTML_CONTENT_OK |
| SRC-083 | 新闻 | VOA 美国之音 | **A** | [官方/说明](https://www.voanews.com/) | HTML_CONTENT_OK |
| SRC-084 | 新闻 | NPR | **C** | [官方/说明](https://www.npr.org/rss/) | PUBLIC_RSS_CANDIDATE_WEB_ROBOTS_DENIED；NPR主站在本浏览器环境被robots拒绝；无法声明RSS运行成功。 |
| SRC-085 | 新闻 | France 24 | **C** | [官方/说明](https://www.france24.com/en/rss) | BROWSER_403_FREE_FEED_UNVERIFIED；France24当前网页浏览请求403；免费RSS候选路径本轮同样403，仍需合规RSS测试。 |
| SRC-086 | 新闻 | NHK World Japan | **C** | [官方/说明](https://www3.nhk.or.jp/nhkworld/en/news/) | OFFICIAL_NEWS_BROWSER_FAIL；NHK官方新闻目录尚未被本工具取得正文或有效XML；需网络隔离环境和官方RSS回退。 |
| SRC-087 | 新闻 | 澎湃新闻 | **C** | [官方/说明](https://github.com/DIYgod/RSSHub/blob/master/lib/routes/thepaper/sidebar.ts) | RSSHUB_ROUTE_FOUND_API_JSON_CONTENT_UNDECODED；RSSHub存在澎湃sidebar公开路由，cache.thepaper.cn接口返回application/json但本工具未显示具体可解析记录；自建RSSHub/合规客户端实测待做。 |
| SRC-088 | 新闻 | 第一财经 | **C** | [官方/说明](https://github.com/DIYgod/RSSHub/blob/master/lib/routes/yicai/latest.ts) | RSSHUB_ROUTE_FOUND_ENDPOINT_TEST_FAILED；RSSHub具有第一财经latest、brief与news等源码路由，但源接口及rsshub.app演示本轮访问失败；存在2023年的路由失效Issue。代码存在不等于路线可用。 |
| SRC-089 | 新闻 | 德国之声 DW英文主站 | **C** | [官方/说明](https://www.dw.com/en/top-stories/s-9097) | DW_ENGLISH_NEWS_NOT_RETRIEVED_SPANISH_ALTERNATE_AVAILABLE；DW的西班牙语可读供稿归属于SRC-004，不自动认定英文站抓取已解决；英文版仍需合法直读或RSS解析。 |
| SRC-092 | 新闻 | The Hindu公开新闻 | **C** | [官方/说明](https://www.thehindu.com/) | THE_HINDU_ROBOTS_BLOCKED；本工具对thehindu.com受robots限制；没有证据可持续无障碍取得免费文章，继续待验证。 |
| SRC-093 | 新闻 | Dawn 巴基斯坦 | **A** | [官方/说明](https://www.dawn.com/) | HTML_CONTENT_OK |
| SRC-094 | 新闻 | Hindustan Times | **A** | [官方/说明](https://www.hindustantimes.com/) | HTML_CONTENT_OK |
| SRC-095 | 新闻 | Arab News | **A** | [官方/说明](https://www.arabnews.com/) | HTML_CONTENT_OK |
| SRC-096 | 新闻 | Africanews | **A** | [官方/说明](https://www.africanews.com/) | HTML_CONTENT_OK |
| SRC-098 | 政治 | CBO美国国会预算办公室 | **A** | [官方/说明](https://www.cbo.gov/) | HTML_CONTENT_OK |
| SRC-099 | 政治 | GAO美国政府问责局 | **A** | [官方/说明](https://www.gao.gov/topics/government-operations?page=1) | OFFICIAL_REPORTS_HTML_ALTERNATE；GAO政府运作专题页直接返回发布日期、报告摘要和报告链接，具备实际公开研究内容。 |
| SRC-100 | 政治 | Pew Research Center | **A** | [官方/说明](https://www.pewresearch.org/) | HTML_CONTENT_OK |
| SRC-101 | 政治 | IAEA国际原子能机构 | **A** | [官方/说明](https://www.iaea.org/newscenter) | HTML_CONTENT_OK |
| SRC-102 | 政治 | CFR Council on Foreign Relations | **A** | [官方/说明](https://www.cfr.org/) | HTML_CONTENT_OK |
| SRC-103 | 政治 | Brookings Institution | **A** | [官方/说明](https://www.brookings.edu/) | HTML_CONTENT_OK |
| SRC-104 | 政治 | Carnegie Endowment | **A** | [官方/说明](https://carnegieendowment.org/) | HTML_CONTENT_OK |
| SRC-105 | 政治 | Chatham House | **A** | [官方/说明](https://www.chathamhouse.org/) | HTML_CONTENT_OK |
| SRC-106 | 政治 | European Parliament | **C** | [官方/说明](https://www.europarl.europa.eu/news/en/press-room/20260708IPR46377/) | SINGLE_RELEASE_INDEXED_DIRECT_ROBOT_CHALLENGE；欧洲议会官方单篇新闻及其正文被搜索索引收录；web.open返回JS机器人验证，浏览器直读未解决。 |
| SRC-107 | 政治 | 美国财政部 Treasury | **A** | [官方/说明](https://home.treasury.gov/news/press-releases) | HTML_CONTENT_OK_METADATA_MINIMAL |
| SRC-108 | 政治 | 英国政府 GOV.UK | **A** | [官方/说明](https://www.gov.uk/search/news-and-communications) | HTML_CONTENT_OK |
| SRC-109 | 政治 | 中国商务部 MOFCOM | **A** | [官方/说明](https://www.mofcom.gov.cn/) | HTML_CONTENT_OK |
| SRC-110 | 政治 | 美国联邦公报 Federal Register | **A** | [官方/说明](https://www.federalregister.gov/) | HTML_CONTENT_OK |
| SRC-111 | 军事 | RUSI | **A** | [官方/说明](https://www.rusi.org/explore-our-research) | HTML_CONTENT_OK |
| SRC-112 | 军事 | FAS Federation of American Scientists | **A** | [官方/说明](https://fas.org/) | HTML_CONTENT_OK |
| SRC-113 | 军事 | IISS免费公开Insights | **B** | [官方/说明](https://www.iiss.org/latest/) | IISS_FREE_PUBLIC_SUBSET_DUPLICATE_045；与SRC-045同一机构免费研究系列，宜在未来规范化为一源多栏目，公开免费文章存在而付费数据库排除。 |
| SRC-114 | 医疗 | CDC美国疾病控制中心 | **A** | [官方/说明](https://www.cdc.gov/) | HTML_CONTENT_OK |
| SRC-115 | 医疗 | NIH新闻公告 | **A** | [官方/说明](https://www.nih.gov/news-events/news-releases) | HTML_CONTENT_OK |
| SRC-116 | 医疗 | medRxiv预印本 | **C** | [官方/说明](https://www.medrxiv.org/content/early/recent) | PREPRINT_SEARCH_INDEXED_BROWSER_403；搜索索引可确认2026-10-09最新预印本列表，但本工具直接打开403，待官方RSS/合法镜像/网络主机实测；不得把预印本当同行评审证据。 |
| SRC-117 | 医疗 | 国家药监局 NMPA | **C** | [官方/说明](https://www.nmpa.gov.cn/directory/web/nmpa/ylqx/ylqxjgdt/index.html) | NMPA_OFFICIAL_REPORTS_INDEXED_BROWSER_412；2026-10-09官方医疗器械审核目录有搜索索引可读；web.open仍412，不满足直接自动抓取验收。 |
| SRC-118 | 医疗 | 国家卫健委 NHC | **C** | [官方/说明](https://www.nhc.gov.cn/) | NHC_OFFICIAL_REPORTS_INDEXED_BROWSER_412；国家卫健委公开2026政策与新闻搜索索引可读；当前网页工具直接打开412，继续待验证。 |
| SRC-119 | AI/科技 | Stanford HAI | **A** | [官方/说明](https://hai.stanford.edu/research) | HTML_CONTENT_OK |
| SRC-120 | AI/科技 | Microsoft Research | **A** | [官方/说明](https://www.microsoft.com/en-us/research/publications/) | HTML_CONTENT_OK |
| SRC-121 | AI/科技 | NVIDIA技术博客 | **A** | [官方/说明](https://developer.nvidia.com/blog/) | HTML_CONTENT_OK |
| SRC-122 | AI/科技 | NeurIPS Proceedings | **A** | [官方/说明](https://proceedings.neurips.cc/) | HTML_CONTENT_OK |
| SRC-123 | AI/科技 | CISA美国网络安全与基础设施安全局 | **C** | [官方/说明](https://www.cisa.gov/news-events/cybersecurity-advisories) | CISA_ADVISORIES_INDEXED_BROWSER_403；官方安全通告目录通过搜索可取得旧版记录；web.open403，未证明实时可采集。 |
| SRC-124 | 创业 | First Round Review | **A** | [官方/说明](https://review.firstround.com/) | HTML_CONTENT_OK |
| SRC-125 | 创业 | Stripe Atlas创业指南 | **A** | [官方/说明](https://stripe.com/atlas/guides) | HTML_CONTENT_OK |
| SRC-126 | 创业 | Hacker News | **A** | [官方/说明](https://news.ycombinator.com/) | HTML_CONTENT_OK |
| SRC-127 | 创业 | Product Hunt | **A** | [官方/说明](https://www.producthunt.com/) | HTML_CONTENT_OK |
| SRC-128 | 创业 | GitHub Trending | **A** | [官方/说明](https://github.com/trending) | HTML_CONTENT_OK |
| SRC-129 | 创业 | Indie Hackers | **A** | [官方/说明](https://www.indiehackers.com/) | HTML_CONTENT_OK_BUT_CACHED_WEEK |
| SRC-130 | 社会 | Our World in Data（社会指标） | **A** | [官方/说明](https://ourworldindata.org/) | HTML_CONTENT_OK |
| SRC-131 | 社会 | UNDP人类发展报告 | **A** | [官方/说明](https://hdr.undp.org/) | HTML_CONTENT_OK |
| SRC-132 | 社会 | UN DESA人口 | **C** | [官方/说明](https://population.un.org/wpp/) | UN_DESA_POPULATION_DYNAMIC_UNREADABLE；UN人口数据库门户动态内容不可读；需要UN静态数据下载与授权核验，未确认真实数据。 |
| SRC-133 | 社会 | Gallup公开研究 | **A** | [官方/说明](https://news.gallup.com/) | HTML_CONTENT_OK |

## 审核和维护
本项目采用动态来源注册，优先免费权威一手公开来源及多地区新闻，单条源报错不影响其他来源；付费具体产品移到限制名单而不是一律拉黑机构。需要严格区分发布时间、观察时间、收集时间；重要政治/市场观点应交叉验证机构利益立场。

## 下一步技术验收（尚未执行）
使用 [tools/source_probe.py](tools/source_probe.py) 在经许可、可正常访问互联网的测试主机进行低频手动探测；先处理21条C及需API密钥的来源，记录真实内容数量、时间、许可与连续性。再决定是否用于自动研究，不得把浏览器索引当成部署成功。
