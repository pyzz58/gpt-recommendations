# 专门内容限制清单与待确认队列｜2026-10-13

> 此处黑名单的单位是**具体研究产品/全文权限**，不是整家机构。只对已经有收费/客户限定证据的内容标 D；一次网络失败一律记 C，不应误拉黑。禁用绕过付费墙/账号/反爬的方法。

## D：明确无法作为“免费完整内容”承诺的产品

| 特定研究产品 | 公开内容可做什么 | 免费全文状态 | 证据 | 合法替代 |
|---|---|---|---|---|
| IISS Military Balance+ 专业军事数据库 | 官方公开文章与部分军费摘要仍保留白名单B | **D：需商业访问/试用/订阅** | https://www.iiss.org/the-military-balance-plus/ | SIPRI军费数据库、NATO公开信息、CSIS、RAND |
| Gartner 客户专属完整分析/多数Magic Quadrant及AskGartner | 部分公开摘要可以分析、引用 | **D：客户登录或订阅** | https://www.gartner.com/en/documents/3957010 和 https://www.gartner.com/en/products/ask-gartner-faqs | NIST标准、IDC以外的公开调查、McKinsey/BCG/Bain公开报告 |
| Nature 非开放获取文章的完整正式出版PDF | 摘要、开放获取版本、公开的部分新闻 | **D：该单篇若非OA则需订阅/购买** | https://www.nature.com/nature/our-publishing-models | Europe PMC OA子集、作者允许的公开版本、Semantic Scholar提供的合法链接 |

## B：机构有公开精选，但全部商业研报尚无免费全文证明
- Goldman Sachs institutional research：公开的Goldman Sachs Research栏目可读，**不能把机构客户完整研究库列为可免费获取**。官方公开入口：https://www.goldmansachs.com/insights/goldman-sachs-research/
- Bank of America Securities proprietary reports：公开Market Insights已证实，客户专属的完整股票/行业研报**尚未确认免费完整取得**。保留B，不武断标整个机构D。https://business.bofa.com/en-us/content/market-strategies-insights.html
- Reuters机器化商业新闻分发与多机构转载权：Reuters.com公开文章和付费/许可的专业内容是不同产品。新闻页面公开不等于可以批量再分发全文。
- Nature开放获取与非开放获取文章应按单篇DOI分别标记A/D。

## C：本轮访问异常，不能宣称不可获得
| 来源/接口 | 本轮症状 | 后续核验 |
|---|---|---|
| BBC News | 浏览工具打开失败 | 查官方RSS、合法搜索、实际主机网络权限 |
| 新华社英文主站 | 本轮直接打开失败 | 逐篇官方来源、中文站、搜索引擎 |
| European Commission Press Corner | 动态页面正文为空 | 官方文档/RSS/单篇公告及网页渲染 |
| 美国国防部News | 栏目读取失败 | 官网新闻单篇、公开索引 |
| Meta AI Research | 本轮内容提取为空 | 官方博客、论文页、公开论文DOI |
| arXiv API文档 | 跳转info.arxiv.org未被本轮浏览器获取 | 真正API查询、Semantic Scholar备用 |
| NCBI/PubMed | 触发浏览器验证页 | 真实合法E-utilities访问、Europe PMC API |
| Sequoia文章目录 | 自动读取报错 | 官方可读单篇/公开搜索 |

**规则**：C只有在完成原生API/RSS、合法开源采集器、公开网络检索三层验证且仍无法获取时，才可迁移为D-ACCESS-UNVERIFIED；如有权限限制则D-RESTRICTED。要记录HTTP错误、时间、请求方式、地区、试过的工具和替代路径，不作绝对性声称。

## 专题提醒
- 网站公开本身不等于版权允许全文存档；引用、短摘与自写研究遵循许可证。
- 没有授权不能通过GitHub开源代码绕过专业订阅。
- 每季度重新检查D内容是否有合法OA版本或官方免费公开变动；黑名单可逆。
