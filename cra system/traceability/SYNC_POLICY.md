# 理论、技术和实现同步规则

## 1. 一条可以追到代码的链

业务讨论来源 → CRA-R固定理论条目 → M模块设计 → 数据/API约定 → 计划或实际代码路径 → CRA-W工作包 → CRA-S验收场景 → 实际运行证据。

theory/requirements.json是Git开发基线的规范源。REQUIREMENTS.md、INDEX.md、WORK_PLAN.md和QUALITY.md由脚本生成，不能只改生成页面制造“已同步”。每条理论有永久编号和revision；模块可以多对多对应，编号不随章节移动而改变。

## 2. 什么时候更新哪一层

| 变化 | 需要复核的区域 | 通常不必做的事 |
| --- | --- | --- |
| 项目某条具体规则/模板/目录内容更新 | 运行时RuleVersion/Template/Directory及依赖判断，必要测试 | 不必每次都修改全套技术架构 |
| 业务理论变化，如先复核遗留或PD任务完成方式 | 对应CRA-R、M05/M06等设计、流程、测试及实际实现 | 不复制一份新的问题库 |
| 识别或模型供应商改变 | M12 adapter、配置、识别/分析验证及相关输出复核 | 不重做患者、报告和历史 |
| 数据或API结构改变 | 数据迁移、契约、调用方、版本与回归 | 不静默抹去旧版本 |
| 表述润色而业务含义不变 | 关联模块复核并说明no_technical_change理由 | 不强行编造代码重构 |

## 3. 一次理论更新的具体步骤

1. 将新讨论导入Git对应CRA-R，保留编号、提高revision；不再适用也保留retired条目和原因，不能删除后复用编号。
2. 运行 `python3 tools/impact.py CRA-R021`，得到直接对应模块和依赖模块候选；按实际影响判断，不机械重写所有依赖。
3. 更新受影响模块设计、数据/API、实现、任务和案例。确实无需技术改变时记录明确理由。
4. 新建changes/CR-xxxx.json，填新理论内容指纹以及每个直接模块的review。旧变更记录不可改写。
5. 更新bindings中各对应模块的reviewed_revision与reviewed_digest；指纹可从impact命令输出取得。
6. 执行 `python3 tools/render_views.py --write` 生成可读视图，再执行同步检查及对应测试，提交同一个PR/变更集。
7. 检查通过后按真实完成情况更新任务状态和证据；设计更新不是代码实现完成。

CR记录至少包含id、date、kind、requirement_fingerprints、module_reviews、validation和status。module_reviews每项含decision（updated或no_technical_change）、具体reason和所复核/修改路径。纯业务基线说明润色且没有理论条目变化时，新增documentation_only_reason解释原因。

## 4. 自动检查能拦截什么

检查固定编号唯一、模块反向关系、依赖、任务和场景覆盖、设计文件存在、内容SHA-256指纹、全部关联模块复核、匹配的新变更记录及生成视图。与基准提交比较时，还检查变更revision递增、理论ID不删除、旧CR不改写、声称updated确有技术文件变化。

因此只改理论、不复核技术会失败。只改revision不更新模块绑定也失败。一条理论对应两个模块而只复核其中一个会失败。沿用旧指纹的CR不能覆盖新条文。

这些检查**不证明语义正确或临床功能有效**，有人仍需根据具体改动审查内容。允许no_technical_change是为了避免无意义重构，不是免除复核。

## 5. Notion与Git

Notion v0.14为本轮来源，Git中整理后的条目是后续开发基线。当前没有配置Notion自动持续导入或写回；GitHub检查只能验证已导入Git的内容。不能声称修改Notion就会自动生成并验证新代码。

后续若增加只读Notion差异导入，只应创建待审变更，保持来源版本、权限和原文范围；不自动覆盖已发布理论、项目规则或报告。现有Notion法规维护任务也不能被当作已经完成Git代码同步。

## 6. 任务执行说明的同步

plan/tasks.json同时保存目标文件、步骤、接口、验证命令及完成标准；16份work_packages任务卡和CODEX_TASKS索引由同一渲染器生成并受CI检查。技术细化使用TECH记录，不伪造业务理论修订；真正改变业务含义仍按CRA-R的revision和CR机制处理。

任务完成前允许计划路径不存在，但标verified时必须有实际交付文件、已可执行命令和已完成前置，并保留evidence。此检查不证明证据内容或实现语义一定正确，仍需按任务验收审查。下一项选择器只读计划，默认不跳过阻塞项，不自动启用OCR增强或部署。
