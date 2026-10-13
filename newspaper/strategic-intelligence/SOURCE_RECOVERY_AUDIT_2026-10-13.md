# 内参系统｜31个来源恢复审计（2026-10-13）

> **新名称：内参系统。** 继先前130/130 URL浏览器检查后，对31个C类来源逐项寻找合法公开替代。检查了官方网页/RSS/API、媒体的替代栏目、公开GitHub工具路线、公开搜索索引。所有结果是**线索恢复或公开页面验证**，不是已部署自动采集、也不是批量AI使用许可通过。

## 本次结果
- 原待核查：31。
- 找到公开可读页面或官方API文档并按登记规则重新归类：**10**，其中A=8，B=2。
- 仍待运行环境/接口/权限验证：**21**。
- 全部来源现在共130条，A=102、B=7、C=21。**生产宿主机真实连续采集0/130**，绝不宣称可用API数据已全部取到。
- A包括“公开研究网页可读”与“官方API文档可读”两种，必须看recovery_20261013.result，不能用A单独判断能否自动摄取。

## 逐源核查与处置

| ID | 来源 | 旧→新 | 结果层级 | 已找到的合法路径与判定理由 | 来源依据 |
|---|---|---|---|---|---|
| SRC-004 | Deutsche Welle | C→A | PUBLIC_HTML_ALTERNATE | DW官方西班牙语公开供稿HTML含2026-10-12日期、标题及正文；并非英文版，版权和二次使用另审。 | [查证](https://rss.dw.com/syndication/feeds/vam_volltextfeedconfirmado.20605-copypaste.html) |
| SRC-005 | BBC News | C→C | FREE_RSS_XML_BROWSER_UNSUPPORTED | BBC World RSS存在2026年9月第三方逐项更新检验；本轮web.open返回text/xml，浏览器无法解析，须联网Python解析并核验BBC使用条款。 | [查证](https://feeder.co/knowledge-base/rss-content/bbc-rss-feeds/) |
| SRC-006 | 新华社英文站 | C→A | PUBLIC_HTML_ALTERNATE | 官方英文栏目直读，2026-10-13新闻标题、时间与文章链接均出现。 | [查证](https://english.news.cn/xinhuanews/index.htm) |
| SRC-034 | Congress.gov | C→C | FREE_ACCOUNT_KEY_REQUIRED | 美国国会公开v3 API确实存在，但需免费api.data.gov密钥；未取得密钥也未请求真实法案JSON。可先用国会公开网页。 | [查证](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/README.md) |
| SRC-038 | 联合国 UN News | C→A | OFFICIAL_RSS_DIRECTORY_HTML | 联合国日内瓦办事处官方RSS目录可读，链接新闻稿、会议记录、总部按主题订阅；RSS条目尚待XML实际解析。 | [查证](https://www.ungeneva.org/en/news-media/rss) |
| SRC-039 | 欧盟委员会 Press Corner | C→C | OFFICIAL_EMAIL_SUBSCRIPTION_DOCUMENTED | 欧委会官方明确支持按主题订阅Press Corner新闻邮件，网页内容可读；尚未取得可无需登录直接采集的发布列表。 | [查证](https://commission.europa.eu/about/contact/press-services/press-releases-and-notifications_en) |
| SRC-045 | IISS公开文章 | C→B | FREE_TAGGED_ANALYSIS_SUBSET | IISS官方公开研究频道与明确标为Free to Read的部分文章可找到，完整Military Balance+继续付费排除；具体免费全文按篇核验。 | [查证](https://www.iiss.org/latest/) |
| SRC-046 | 美国国防部 News | C→C | OFFICIAL_ALTERNATIVE_INDEXED_BROWSER_403 | 官方新域名war.gov新闻发布列表已被搜索索引收录，但直接web.open本轮403；不能标机器接口可用，需合法联网宿主机或订阅验证。 | [查证](https://www.war.gov/News/Releases/News/) |
| SRC-051 | Meta AI Research | C→A | PUBLIC_HTML_ALTERNATE | Meta AI独立官方研究站点直接返回2026-10-12研究更新及文章链接。 | [查证](https://research.meta.ai/) |
| SRC-053 | arXiv API文档 | C→C | OFFICIAL_GITHUB_API_DOC_READABLE_ATOM_UNTESTED | arXiv官方GitHub API手册可读，说明开放Atom搜索接口；实际API XML数据在本环境未能解析或确认。 | [查证](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/api/user-manual.md) |
| SRC-060 | ClinicalTrials.gov | C→C | OFFICIAL_JSON_API_DOC_ENDPOINT_UNTESTED | ClinicalTrials.gov公开v2接口有规范，但当前网页工具对实际JSON请求无法返回可解析数据；仍待联网运行环境确认。 | [查证](https://clinicaltrials.gov/data-api/api) |
| SRC-061 | Europe PMC | C→C | OFFICIAL_REST_DOC_SEARCH_INDEXED_ENDPOINT_UNTESTED | Europe PMC文档明确公开JSON/XML REST检索；直接API请求在当前Web工具无法解析，不能报成功。 | [查证](https://europepmc.org/RestfulWebService) |
| SRC-062 | NCBI/PubMed | C→A | OFFICIAL_API_DOCUMENTATION_HTML_ONLY | NLM官方E-Utilities文档可读并说明PubMed ESearch等；实际文献数据接口尚未进行运行宿主机烟测。 | [查证](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html) |
| SRC-063 | Nature期刊 | C→C | OA_SUBSET_UNVERIFIED_BROWSER_COOKIE | Nature非OA全文依旧需订阅；公开目录和OA子集待逐篇检测，不使用付费正文。 | [查证](https://www.nature.com/nature/articles) |
| SRC-064 | Our World in Data | C→A | PUBLIC_HTML_AND_DOCUMENTED_CSV_API | OWID主站可直接读取公开数据研究文章；官方文档列出Grapher CSV数据端点，端点逐项授权另审。 | [查证](https://docs.owid.io/projects/etl/api/chart-api/) |
| SRC-068 | Sequoia文章 | C→A | PUBLIC_HTML_ALTERNATE | 红杉官方新版Stories目录及创业案例链接可直接读取，原/sequoiacap.com/article/为404应退役。 | [查证](https://sequoiacap.com/stories) |
| SRC-084 | NPR | C→C | PUBLIC_RSS_CANDIDATE_WEB_ROBOTS_DENIED | NPR主站在本浏览器环境被robots拒绝；无法声明RSS运行成功。 | [查证](https://www.npr.org/rss/) |
| SRC-085 | France 24 | C→C | BROWSER_403_FREE_FEED_UNVERIFIED | France24当前网页浏览请求403；免费RSS候选路径本轮同样403，仍需合规RSS测试。 | [查证](https://www.france24.com/en/rss) |
| SRC-086 | NHK World Japan | C→C | OFFICIAL_NEWS_BROWSER_FAIL | NHK官方新闻目录尚未被本工具取得正文或有效XML；需网络隔离环境和官方RSS回退。 | [查证](https://www3.nhk.or.jp/nhkworld/en/news/) |
| SRC-087 | 澎湃新闻 | C→C | RSSHUB_ROUTE_FOUND_API_JSON_CONTENT_UNDECODED | RSSHub存在澎湃sidebar公开路由，cache.thepaper.cn接口返回application/json但本工具未显示具体可解析记录；自建RSSHub/合规客户端实测待做。 | [查证](https://github.com/DIYgod/RSSHub/blob/master/lib/routes/thepaper/sidebar.ts) |
| SRC-088 | 第一财经 | C→C | RSSHUB_ROUTE_FOUND_ENDPOINT_TEST_FAILED | RSSHub具有第一财经latest、brief与news等源码路由，但源接口及rsshub.app演示本轮访问失败；存在2023年的路由失效Issue。代码存在不等于路线可用。 | [查证](https://github.com/DIYgod/RSSHub/blob/master/lib/routes/yicai/latest.ts) |
| SRC-089 | 德国之声 DW英文主站 | C→C | DW_ENGLISH_NEWS_NOT_RETRIEVED_SPANISH_ALTERNATE_AVAILABLE | DW的西班牙语可读供稿归属于SRC-004，不自动认定英文站抓取已解决；英文版仍需合法直读或RSS解析。 | [查证](https://rss.dw.com/syndication/feeds/vam_volltextfeedconfirmado.20605-copypaste.html) |
| SRC-092 | The Hindu公开新闻 | C→C | THE_HINDU_ROBOTS_BLOCKED | 本工具对thehindu.com受robots限制；没有证据可持续无障碍取得免费文章，继续待验证。 | [查证](https://www.thehindu.com/) |
| SRC-099 | GAO美国政府问责局 | C→A | OFFICIAL_REPORTS_HTML_ALTERNATE | GAO政府运作专题页直接返回发布日期、报告摘要和报告链接，具备实际公开研究内容。 | [查证](https://www.gao.gov/topics/government-operations?page=1) |
| SRC-106 | European Parliament | C→C | SINGLE_RELEASE_INDEXED_DIRECT_ROBOT_CHALLENGE | 欧洲议会官方单篇新闻及其正文被搜索索引收录；web.open返回JS机器人验证，浏览器直读未解决。 | [查证](https://www.europarl.europa.eu/news/en/press-room/20260708IPR46377/) |
| SRC-113 | IISS免费公开Insights | C→B | IISS_FREE_PUBLIC_SUBSET_DUPLICATE_045 | 与SRC-045同一机构免费研究系列，宜在未来规范化为一源多栏目，公开免费文章存在而付费数据库排除。 | [查证](https://www.iiss.org/latest/) |
| SRC-116 | medRxiv预印本 | C→C | PREPRINT_SEARCH_INDEXED_BROWSER_403 | 搜索索引可确认2026-10-09最新预印本列表，但本工具直接打开403，待官方RSS/合法镜像/网络主机实测；不得把预印本当同行评审证据。 | [查证](https://www.medrxiv.org/content/early/recent) |
| SRC-117 | 国家药监局 NMPA | C→C | NMPA_OFFICIAL_REPORTS_INDEXED_BROWSER_412 | 2026-10-09官方医疗器械审核目录有搜索索引可读；web.open仍412，不满足直接自动抓取验收。 | [查证](https://www.nmpa.gov.cn/directory/web/nmpa/ylqx/ylqxjgdt/index.html) |
| SRC-118 | 国家卫健委 NHC | C→C | NHC_OFFICIAL_REPORTS_INDEXED_BROWSER_412 | 国家卫健委公开2026政策与新闻搜索索引可读；当前网页工具直接打开412，继续待验证。 | [查证](https://www.nhc.gov.cn/) |
| SRC-123 | CISA美国网络安全与基础设施安全局 | C→C | CISA_ADVISORIES_INDEXED_BROWSER_403 | 官方安全通告目录通过搜索可取得旧版记录；web.open403，未证明实时可采集。 | [查证](https://www.cisa.gov/news-events/cybersecurity-advisories) |
| SRC-132 | UN DESA人口 | C→C | UN_DESA_POPULATION_DYNAMIC_UNREADABLE | UN人口数据库门户动态内容不可读；需要UN静态数据下载与授权核验，未确认真实数据。 | [查证](https://population.un.org/wpp/) |

## 尚未解决的21个：按真正障碍分组

### 1. 有免费Feed/API，但需要运行环境实际解析/密钥
- BBC（SRC-005）：标准RSS返回text/xml，当前网页工具不支持解析；Python标准XML解析/Feedparser的真实宿主机测试仍未执行。媒体文本版权和AI使用另查。
- Congress.gov（SRC-034）：API需免费注册api.data.gov密钥；在未通过用户授权的注册或提供密钥前，不做带密钥访问。可以人工使用公开法案网页。
- arXiv（SRC-053）、ClinicalTrials.gov（SRC-060）、Europe PMC（SRC-061）：官方API文档有证据，但实际Atom/JSON未在生产主机取得。切勿写为故障接口。
- 第一财经（SRC-088）和澎湃（SRC-087）：已找到RSSHub具体路由，分别 https://github.com/DIYgod/RSSHub/blob/master/lib/routes/yicai/latest.ts 和 https://github.com/DIYgod/RSSHub/blob/master/lib/routes/thepaper/sidebar.ts 。澎湃缓存接口取得JSON Content-Type，工具没有解析输出；第一财经路由存在历史失败问题，须实际调用与核对文章时间。**不建议绕开源站许可使用私有/受限接口。**

### 2. 来源存在公开目录，但当前工具受浏览器403/412/robots/JS挑战
- France24（SRC-085）、NHK（SRC-086）、NPR（SRC-084）、The Hindu（SRC-092）、DW英文站（SRC-089）、medRxiv（SRC-116）、国家药监局（SRC-117）、国家卫健委（SRC-118）、CISA（SRC-123）、欧洲议会（SRC-106）、美国官方国防新闻（SRC-046）：官方/索引线索存在，但并未完整取得可解析且可持续的页面；应先尝试原生RSS及官方可用的不同页面，合法的第三方元信息搜索只作为发现层，不代表授权全文。
- 美国官方国防新闻（SRC-046）：已找到 war.gov 官方发布目录的公开搜索索引，但在当前浏览器直接打开仍403，故保持C。注册表preferred_url保存备用。
- 国家药监局：2026-10-09医疗器械监管信息在官方索引可找到，但本浏览器访问具体目录412，不升级为自动可用。

### 3. 已确认公开通知渠道，但缺少无需登录的机器化数据
- 欧盟委员会（SRC-039）：官方Press Corner允许按搜索/主题订阅邮件；还没有完成自动内容采集与邮箱接入，故保持C。
- 其他受限制的外部页面要分别标记技术阻断与内容版权限制，禁止虚构成功。

### 4. 数据服务的具体静态获取仍待补验
- UN DESA人口（SRC-132）：动态数据门户本轮不可解析；寻找联合国官方公开CSV/Excel或静态报告，再测实际字节下载。

## 两项永久边界
1. **不是所有免费网页都能免费全文入库及通过LLM处理。** 页面可读、可自动下载、允许算法加工、允许邮件再发布是四个不同授权层次；后两者需遵循相应站点许可。
2. **不得因为GitHub上存在RSSHub路由就把来源标生产可用**；必须真正运行路由、解析至少一个新条目并经过多次跨日测试。

## 正式复测标准
- 官网直读或开放官方RSS/API优先；自建RSSHub等工具是补充，不能突破收费墙。
- 每次保存checked_at、original_url、preferred_url、HTTP状态、content_type、entries_count、latest_pub_at、source_license、AI_use_permission、independent_origin、last_failure_reason。
- `production_test`只有在有权限的隔离宿主机跑真实调用并保存结果后才能变更；当前130/130均为NOT_RUN。
- 先修主流高优先级BBC、第一财经、澎湃、Congress.gov、官方医疗/政治来源，其后再处理其他长尾来源，避免过度设计。
- 本次没有创建账号、购买服务、调用收费API或改动日报生产任务。
