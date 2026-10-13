> **V5 历史资料效力（2026-10-14）**：本文件保留当时的细化、模板或审计证据，不能独立改变[唯一现行 V5 主规格](CANONICAL_SYSTEM_SPEC_V5.md)。旧九栏固定百分比、独立连续情报/雷达、旧版“最高”与读者版“继续观察”等如有冲突，以 V5 为准；未冲突的专业方法和案例可按题参考。

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


## V1.7 免费路线清理（2026-10-13）
**从活动免费候选清单移出的“完整免费获取未经证实/付费内容”**：
- Financial Times 全站/付费正文：https://www.ft.com/ 。公开标题与搜索结果可能存在，但**不纳入保证可免费取全文的渠道**。
- Bloomberg 全站/终端/付费报道：https://www.bloomberg.com/ 。需要订阅的资讯不列入免费全文采集。
- Le Monde 付费频道：https://www.lemonde.fr/ 。暂移出自动免费候选；未来只有合法开放的单篇经实测和许可核查后才可加入。
- WSJ完整订阅、The Economist完整订阅、Nikkei Asia订阅栏目、CB Insights和PitchBook付费完整商业数据库均不作为免费依赖；未经实际公开验证不得伪装成无成本API。
- Reuters/LSEG专业商业内容及Reuters新闻再分发许可：公开Reuters.com可读新闻不等于获得专业全文库与批量再分发许可。保留Reuters公开网页候选B，付费专有产品排除。
- 高盛/美银的机构客户专有研究库：保留公开精选栏目B；移除完整客户报告的免费获取假设。
- **The Guardian Open Platform 的AI使用限制**：Developer虽然对符合条件的非商业用途免费，但条款明确涉及AI/文本挖掘限制。出处：https://www.theguardian.com/open-platform/terms-and-conditions 。故不得未经授权将文章正文送入自动LLM内参流程。另查询 https://open-platform.theguardian.com/access/ ；这是**用途许可排除**，不是收费问题。
- **NewsAPI.org Developer**：https://newsapi.org/pricing 免费套餐面向开发/测试，不能将其当成不受限制的正式免费生产新闻渠道。

### 黑名单处理原则
1. 一家机构允许有A（免费公开页面）与D（受限专有数据库）两个不同具体产品，不封杀全部机构。
2. 付费研究产品永久保留“为何移除”的审计记录，但从自动采集启用白名单**排除**。
3. 对403/robots/XML解析器不支持/动态页面空白的来源保持C待验证，不得虚假声称“没有免费的信息”。
4. GitHub开源程序不能改变源站访问许可。无论工具是否能技术上获取，不可绕过订阅或明确AI使用禁令。

## 2026-10-13 用户决定放弃的技术访问来源（与付费D类别不同）
Congress.gov、欧盟委员会Press Corner、NHK WORLD-JAPAN、欧洲议会、中国国家药监局、中国国家卫健委六条从活跃采集白名单中移出，不继续排查；历史错误见[SOURCE_ABANDONED_2026-10-13.json](SOURCE_ABANDONED_2026-10-13.json)。此项是用户作出的成本/范围取舍，不表示这6家机构本身不权威、必然付费或者永远无法合法公开获取。
