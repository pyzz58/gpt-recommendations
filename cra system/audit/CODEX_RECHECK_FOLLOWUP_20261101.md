# 给Codex：只补完本次独立复核确认的三项残留

先读取最新HEAD及cra system/AGENTS.md、最高业务基线和既有任务/证据规则。

独立复核分支：audit/cra-remediation-recheck-20261101。
读取：
- cra system/audit/REMEDIATION_RECHECK_20261101.md
- cra system/audit/REMEDIATION_RECHECK_20261101.json

被审修复源码5148684064a57e50077dd32d02e76b57b2221fc4，完成记录6b2fa75fcc55d0738bbf6b97372db89b22a58dd5。原两次CI成功已确认；此次五个独立边界用例在GitHub run 41247079903复现三项原发现的残留。

只处理以下范围，保留其他已有效修正及明确限制：
1. 原03：子清单递归必须继承父级适用前提、豁免及相关分支；同窗口不同条件路径不能被去重合并。父级false/例外true/unknown分别验证，真正适用而超窗仍应保留。
2. 原04：同一共享方案按中心不同启用日继续支持；独立中心SOP不能只因rule_key相同就默默删掉项目规定。仅在明确同源版本采用关系中选择默认/中心版本，真实冲突展示双方来源。
3. 原08：succeeded识别job重复投递须在provider之前直接返回原结果；不得重复识别或插候选。公开retry接口须能安全恢复过期running租约，保护活跃租约并防止旧attempt迟到写入，保留CRA更正。

按原机制重开受影响任务及必要依赖链，保存completion_history，写正向API/PostgreSQL/worker回归并运行专属CI，重新绑定源码证据后再确认完成。独立诊断5 passed只表示复现了缺陷，各结果acceptance_passed=false，不可把它冒充产品验收通过。

不扩展任意中文方案完整AST、复杂照片或设备验收的本轮范围；这些继续按已声明限制和后续任务执行。先修完三项，再进入W10；不重写架构、不修改其他项目或自动部署/外发/写回EDC。
