# 全球权威信息源白名单｜V1.6

> 调查日期：2026-10-13。**规划与公开来源侦察，未实现真实自动采集。**

## 状态语义（不可混用）
- **A**：官网存在可公开阅读内容，或者公开列明RSS/API；这不代表已经成功调用接口或获准转载全文。
- **B**：有部分公开内容，但完整商业研究/非OA全文未获免费访问确认。
- **C**：本轮路径出现访问/动态渲染问题，仍需官方替代路径、合法搜索、GitHub工具和真实运行环境测试。**不等于绝对不存在信息。**
- **D**：特定的付费/客户专属产品，目前不存在已确认合法免费全文路径；详见 SOURCE_ACCESS_BLOCKLIST.md。

查询门户/官方API文档验证 ≠ 端点真实返回成功 ≠ 长期稳定采集 ≠ 已获版权二次分发权。未来逐源必须执行真实HTTP、解析、时效、权限和复测验收。

## 九大栏目跨领域初始来源表

| 类别 | 机构与专题 | 状态 | 官方地址 | 已知获取形式 | 候选回退 |
|---|---|---|---|---|---|
| 新闻 | AP News | **A** | [官网](https://apnews.com/) | 公开新闻网页 | 原文引用、Newsletter |
| 新闻 | Reuters World | **B** | [官网](https://www.reuters.com/world/) | 公开栏目；部分正文/商业授权有限 | GDELT与公开合法检索 |
| 新闻 | Al Jazeera | **A** | [官网](https://www.aljazeera.com/) | 公开新闻页 | 官网栏目与RSS核验 |
| 新闻 | Deutsche Welle | **A** | [官网](https://amp.dw.com/en/the-day-with-brent-goff/video-19049331) | 主站报错，AMP官方内容可读 | 官方RSS/AMP |
| 新闻 | BBC News | **C** | [官网](https://www.bbc.com/news) | 本轮访问失败 | RSS/合法搜索，技术烟测 |
| 新闻 | 新华社英文站 | **C** | [官网](https://english.news.cn/) | 本轮直接访问失败 | 新华中文官网/搜索 |
| 新闻 | GDELT | **A** | [官网](https://gdeltproject.org/) | 公开全球新闻发现索引，不是原始事实源 | 原发媒体核实 |
| 新闻 | Media Cloud | **B** | [官网](https://www.mediacloud.org/documentation/search-api-guide) | 搜索/API文档可见；权限与调用未测 | GDELT/媒体原生源 |
| 金融 | SEC EDGAR | **A** | [官网](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | 官方无Key API文档 | sec-edgar-downloader |
| 金融 | Federal Reserve | **A** | [官网](https://www.federalreserve.gov/feeds/feeds.htm) | 官方RSS | 官方公告页 |
| 金融 | BIS | **A** | [官网](https://www.bis.org/rss) | 官方研究与讲话RSS | 官方研究页 |
| 金融 | 摩根大通 Guide to the Markets | **A** | [官网](https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/) | 官方说明免费完整指南 | 官网更新监测 |
| 金融 | 贝莱德 Investment Institute | **A** | [官网](https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary) | 免费公开周评 | 官网更新监测 |
| 金融 | 先锋 Vanguard Outlook | **A** | [官网](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vanguard-economic-market-outlook.html) | 公开经济展望 | 官网公开研究 |
| 金融 | 道富 State Street | **A** | [官网](https://www.ssga.com/us/en/individual/insights/featured-insights) | 公开精选洞察 | 栏目更新 |
| 金融 | 高盛 Goldman Sachs Research | **B** | [官网](https://www.goldmansachs.com/insights/goldman-sachs-research/) | 公开精选，不等于所有专有研报 | 公开文章/一手数据 |
| 金融 | 花旗 Citi Institute | **A** | [官网](https://www.citigroup.com/global/insights/citi-institute) | 公开研究专题 | 官网发布页 |
| 金融 | 美国银行 BofA Securities | **B** | [官网](https://business.bofa.com/en-us/content/market-strategies-insights.html) | 公开精选；客户研究不保证 | 公开市场洞察 |
| 金融 | 摩根士丹利 Insights | **A** | [官网](https://www.morganstanley.com/insights/) | 公开市场与科技精选 | 官网更新 |
| 金融 | 伯克希尔股东信 | **A** | [官网](https://www.berkshirehathaway.com/letters/letters.html) | 历史股东信目录 | SEC年报/官网报告 |
| 金融 | Oaktree/Howard Marks | **A** | [官网](https://www.oaktreecapital.com/insights) | 公开投资备忘录目录 | 公开newsletter |
| 宏观 | IMF Data | **A** | [官网](https://data.imf.org/en/Resource-Pages/IMF-API) | 官方SDMX API文档，真实调用未测 | 公开报告 |
| 宏观 | 世界银行 World Bank | **A** | [官网](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) | 官方无需密钥的API | 指标页面 |
| 宏观 | OECD | **A** | [官网](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html) | 免费SDMX API文档、有频限 | 数据浏览器 |
| 宏观 | 国际能源署 IEA | **B** | [官网](https://www.iea.org/reports) | 研究目录公开，全文逐篇判许可 | 免费概要/网页 |
| 产业 | PwC全球CEO调查 | **A** | [官网](https://www.pwc.com/gx/en/issues/c-suite-insights/ceo-survey.html) | 公开报告正文 | 研究页面监测 |
| 产业 | Deloitte Tech Trends | **A** | [官网](https://www.deloitte.com/global/en/insights/topics/technology-management/tech-trends.html) | 公开专题报告 | 网站更新 |
| 产业 | EY CEO Outlook | **A** | [官网](https://www.ey.com/en_gl/ceo/ceo-outlook-global-report) | 公开报告正文 | 网站更新 |
| 产业 | KPMG Insights | **A** | [官网](https://kpmg.com/xx/en/our-insights.html) | 公开研究页面 | 具体系列逐篇检验 |
| 产业 | McKinsey Global Institute | **A** | [官网](https://www.mckinsey.com/mgi/overview) | 公开研究目录 | 公开报告原文 |
| 产业 | BCG | **A** | [官网](https://www.bcg.com/publications) | 公开文章与研究 | 网站监控 |
| 产业 | Bain | **A** | [官网](https://www.bain.com/insights/) | 公开商业洞察 | 研究文章 |
| 政治 | 美国白宫 Presidential Actions | **A** | [官网](https://www.whitehouse.gov/presidential-actions/) | 2026政策/政令可读 | 联邦公报 |
| 政治 | Congress.gov | **A** | [官网](https://api.congress.gov/) | 公开API文档，需申请免费Key | 国会网站搜索 |
| 政治 | 英国议会 UK Parliament | **A** | [官网](https://www.parliament.uk/site-information/rss-feeds/) | 法案/研究简报官方RSS | 议会官网 |
| 政治 | 中国国务院政策库 | **A** | [官网](https://www.gov.cn/zhengce/zhengceku/bmwj/home.htm) | 中文政策原文索引可读 | 中国政府网搜索 |
| 政治 | 中国外交部 | **A** | [官网](https://www.mfa.gov.cn/) | 官方声明/问答网页 | 公告频道 |
| 政治 | 联合国 UN News | **A** | [官网](https://www.un.org/en/events-and-news/) | 官方多语新闻页面；原press路径403 | docs.un.org/press/releases/ |
| 政治 | 欧盟委员会 Press Corner | **C** | [官网](https://ec.europa.eu/commission/presscorner/home/en) | 动态栏目内容为空，未确认自动读取 | EU单篇公告/公开检索 |
| 政治 | EUISS欧洲安全研究所 | **A** | [官网](https://www.iss.europa.eu/publications) | 公开完整研究PDF | 官网研究目录 |
| 军事 | SIPRI军费数据库 | **A** | [官网](https://www.sipri.org/databases/milex) | 公开数据下载，商业许可另议 | OWID衍生数据 |
| 军事 | NATO | **A** | [官网](https://www.nato.int/cps/en/natohq/RSS.htm) | 官方新闻RSS | 官网声明 |
| 军事 | CSIS国防研究 | **A** | [官网](https://www.csis.org/topics/defense-and-security) | 公开研究文章 | CSIS分析 |
| 军事 | RAND兰德 | **A** | [官网](https://www.rand.org/pubs/research_reports.html) | 公开研究目录和部分PDF | 公开研究单页 |
| 军事 | IISS公开文章 | **B** | [官网](https://www.iiss.org/publications/the-military-balance/2026/the-military-balance-2026/global-defence-spending/) | 部分国防研究免费；完整版商业产品另列D | SIPRI/CSIS/RAND |
| 军事 | 美国国防部 News | **C** | [官网](https://www.defense.gov/News/) | 本轮自动读取失败 | 合法公开搜索/官方单页 |
| AI/科技 | Google Research | **A** | [官网](https://research.google/pubs/) | 官方研究论文目录 | 论文原始网址 |
| AI/科技 | Google DeepMind | **A** | [官网](https://deepmind.google/research/) | 官方研究成果 | 公开论文 |
| AI/科技 | OpenAI Research | **A** | [官网](https://openai.com/research/) | 官方研究页面 | 论文及发布原文 |
| AI/科技 | Anthropic Research | **A** | [官网](https://www.anthropic.com/research) | 官方研究成果 | 公开研究资料 |
| AI/科技 | Meta AI Research | **C** | [官网](https://ai.meta.com/research/) | 本轮页面为空 | 论文索引及公开文章搜索 |
| AI/科技 | Hugging Face Papers | **A** | [官网](https://huggingface.co/papers) | 论文发现索引 | 论文原始链接 |
| AI/科技 | arXiv API文档 | **C** | [官网](https://arxiv.org/help/api) | 跳转地址本轮无法访问 | Semantic Scholar/公开作者页 |
| AI/科技 | Semantic Scholar API | **A** | [官网](https://webflow.semanticscholar.org/product/api) | 公开论文API文档、有访问限额 | Europe PMC/原论文 |
| AI/科技 | NIST AI Risk Framework | **A** | [官网](https://www.nist.gov/itl/ai-risk-management-framework) | 美国标准与研究页 | NIST官网 |
| AI/科技 | NASA News | **A** | [官网](https://www.nasa.gov/news/) | 官方航天新闻页面 | NASA项目网页 |
| 医疗 | WHO全球卫生数据库 | **A** | [官网](https://www.who.int/data/gho/info/athena-api/GHO) | 官方API文档 | 卫生数据门户 |
| 医疗 | FDA openFDA | **A** | [官网](https://open.fda.gov/apis/authentication/) | 免费API及调用限额官方文档 | 药监公告 |
| 医疗 | EMA欧洲药品管理局 | **A** | [官网](https://www.ema.europa.eu/en/news-events) | 新闻与RSS明确列出 | 药品审批信息 |
| 医疗 | ClinicalTrials.gov | **A** | [官网](https://clinicaltrials.gov/data-api/api) | 官方API入口可读，JSON端点未烟测 | 临床试验网站 |
| 医疗 | Europe PMC | **A** | [官网](https://europepmc.org/RestfulWebService) | 医学文献公开API文档 | 开放全文子集 |
| 医疗 | NCBI/PubMed | **C** | [官网](https://www.ncbi.nlm.nih.gov/books/NBK25501/) | 本轮反机器人验证页 | Europe PMC API |
| 医疗 | Nature期刊 | **B** | [官网](https://www.nature.com/nature/articles) | 可看目录和OA子集，非OA全文需订阅 | 开放获取论文/作者合法版本 |
| 社会 | Our World in Data | **A** | [官网](https://ourworldindata.org/search) | 公开图表、RSS、部分开放数据 | 原始统计机构 |
| 创业 | Y Combinator RFS | **A** | [官网](https://www.ycombinator.com/rfs) | 公开创业需求主题 | YC官方库 |
| 创业 | Y Combinator Library | **A** | [官网](https://www.ycombinator.com/library?categories=Diversity+++Inclusion) | 可查公开教程和访谈 | YC Startup School |
| 创业 | a16z | **A** | [官网](https://a16z.com/) | 公开投资与科技文章 | 合法newsletter |
| 创业 | Sequoia文章 | **C** | [官网](https://www.sequoiacap.com/article/) | 本轮栏目读取报错 | 官网单篇/索引搜索 |

## 规则
1. 媒体与研究机构、政策原文、公开财报、医学文献均独立发现，绝不只从日报精选中二次筛选。
2. A状态仅针对公开页面与官方接口文档的可发现性，不是生产连接成功报告。所有实际技术运行状态保持NOT_RUN，直到Codex真实验证。
3. 任何受限研究不因RSSHub、Trafilatura或搜索引擎存在就被视为开放；不可绕过付费墙或盗用会话。
4. 每个来源未来补充频率、语言、地区、所有权、许可证、上次成功、失败代码、错误原因与下次复检；重要来源以多个相互独立的原始资料交叉核查。
5. A/B/C动态转移，D只针对具体受限系列不封禁整个机构。

本轮来源数量：**68**；A=53，B=7，C=8；D产品另见限制清单。
