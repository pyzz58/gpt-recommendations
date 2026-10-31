# W19 策略基线、运行绑定与迁移接手说明

对应：RQ-001、RQ-030、RQ-032；TR-02、TR-19、TR-22、TR-25；W19；
AT-001、AT-027、AT-030、AT-032。

状态：IMPLEMENTED，未将整体AT标为VERIFIED。W19已形成不可变策略基线、
项目/计划/任务/run绑定、影响传播和配置迁移账本；数据库迁移工具只验证
schema门与配置切换，不代替生产环境DDL变更、真实备份或现实外部动作。

## 已交付

- PolicyBundle保存思想/技术正文、RQ映射、26岗合同、技能、三领域工作流、
  来源政策、输出schema与全部配置文件的规范化和可重建JSON快照。
- bundle ID由workspace与规范化内容hash共同确定；同一workspace相同内容
  重复发布返回原记录，任一有效配置变化形成新bundle，旧bundle保持可读。
- bundle快照扫描secret-like字段；错误配置、缺失bundle或数据库未到
  `d9a7e3f1b420`时不启动worker。
- 新项目自动绑定当前不可变bundle；Plan、Task、TaskVersion、AgentRun和
  SkillRun分别保存实际运行/历史基线。
- AgentRunner从Task固定bundle重建角色合同和理论hash，不因全局配置升级
  半途替换旧Task方法；当前角色撤销的工具权限与旧权限求交集。
- SkillRunner要求固定bundle中的skill版本与当前实现一致，否则fail-closed；
  SkillRun保存bundle ID。
- 项目升级bundle时记录old/new、changed components、受影响RQ与任务。
  仅失效受影响角色或workflow的未完成历史；无关角色继续，accepted历史
  和已完成AgentRun不变。
- 受影响running/waiting任务暂停并标记`under_review`；其他未完成受影响
  任务标记`needs_input/stale`。新TaskVersion保留old bundle，修订输入后
  绑定新bundle恢复。
- 配置迁移提供dry-run、apply、失败和rollback账本；记录expected revision、
  schema revision、backup ref、实际结果和错误码。重复apply幂等，回滚只
  恢复配置基线，不删除历史证据或现实外部事实。
- API提供项目策略视图、配置发布、项目激活、迁移dry-run/apply/rollback。
  项目概览显示项目固定基线、workspace当前bundle、影响与迁移数量。
- 新增`policy_bundles`、`policy_states`、`policy_impacts`、
  `policy_migration_operations`四张FORCE RLS表；全库当前83条策略。

## C01收口

`_start_run`现在在同一事务先锁定job并核对state/owner/fence/lease，再按
`run_key`锁定并重读AgentRun。若接管者已保存成功结果，则直接复用该交付；
旧worker不能被过时的`ExistingRunView`重置成功记录。真实PostgreSQL时序
回归覆盖：

- 旧worker先创建running记录；
- 租约过期后新worker接管、执行并成功；
- 旧worker恢复后再次进入`_start_run`被拒绝；
- 成功output、input_snapshot、started_at和ended_at保持不变。

## 主要路径

- 领域视图：`services/core/src/medical_one_person/domain/policy_bundles.py`
- 构建与迁移服务：`services/core/src/medical_one_person/application/policy_bundles.py`
- API：`services/core/src/medical_one_person/api/policies.py`
- 数据模型：`services/core/src/medical_one_person/infrastructure/db/models.py`
- 迁移：`services/core/migrations/versions/d9a7e3f1b420_w19_policy_bundles.py`
- 核心测试：`services/core/tests/integration/test_w19_policy_bundles.py`
- API测试：`services/core/tests/integration/test_w19_policy_api.py`
- C01回归：`services/core/tests/integration/test_w04_scheduling.py`
- 页面：`apps/web/src/app/projects/[id]/overview/page.tsx`

## 验收范围

- mock provider与真实PostgreSQL 17.6；
- bundle发布去重、固定运行依据、精确影响范围、TaskVersion恢复；
- 配置迁移dry-run/apply幂等/失败门/rollback；
- 数据库迁移`c8f1a6d3e720 → d9a7e3f1b420 → c8f1a6d3e720 → d9a7e3f1b420`；
- 83条RLS策略和策略表FORCE RLS；
- Ruff、mypy、Next.js lint/typecheck/build。

未覆盖：

- 任意历史schema的无损自动回退；
- 活动生产库DDL执行、真实异地备份、主机故障和partial migration恢复；
- live模型、真实专家、真实外包、邮件、合同、付款或实验；
- 配置升级后人工研究决策质量，不由hash一致或测试通过自动证明。

## 下一包

W20继续成本上界、全链审计、性能、隔离和外部副作用故障回归。W19实现
不改变W01—W18整体AT未VERIFIED和W24 PREPARED的状态。
