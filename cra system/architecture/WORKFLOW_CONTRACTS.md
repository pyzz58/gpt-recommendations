# 本轮监查决定的实现契约

版本1；2026-10-29。这是CRA-R005—R045相关决定的技术实现约定，不建立第二份业务规范。所有字段均为计划；实际实现与证据以tasks.json为准。

## 1. 遗留提醒与简单确认

W06通过M02解析结果接收历史DOCX报告、XLSX track或问题文字，生成CarryoverCandidate；已有系统问题直接复用。候选含原编号（如有）、问题、位置、整改建议/来源、已知进展和原文件定位。缺字段保持unknown，不能为了形成完整底稿编造法规出处或修改历史。用户可在列表修正后一次确认导入；来源哈希、原条目键与已有Issue映射保证幂等，无法确定重复时只核实该项。

本次开始GET carryover取未完事项并可展开历史。确认按钮调用confirm-corrected(action_ids, expected_revision, idempotency_key)，身份与时间由服务器记录。选择整条问题时明确列出将完成的现有动作；未选动作不变。正常确认不需要修改位置、附件、说明或单独CRC回复。reply只表示可选沟通记录，不能作为确认前置。

状态保存completion_basis=user_confirmation、actor_id、confirmed_at，optional_note可空。UI和报告写“CRA确认已整改”，不能写“AI独立验证”。用户发现仍未改或需重开可更新相应动作并保留历史。PD上报继续使用confirm-reported，不因普通整改确认而伪造已上报。

## 2. 缺数据与不核查相关路径

ContextRequirement按用途列needed_fact_keys、来源范围、affected_rule_ids及可继续事项。例如时间窗需要实际锚点；数值一致性只用该比较所需身份/字段，不能被缺少锚点一并禁用。匹配身份不明时仍可提取和保存，但不运行该对照。

用户选择“不补充，本范围不核查相关事项”后保存CheckDecision：study/site/subject、check_scope（检查类型/规则/资料期间或快照）、reason=declined_missing_data或unreadable_skip、missing_keys、affected_paths、actor、time、state=active。显示具体影响后一次选择，不增加二次审批。只抑制对应追问与依赖判断，不屏蔽其他已知差异/紧急发现，不把跳过当normal或待整改Issue。

依赖该数据的判断返回not_checked_by_user；其余可计算部分继续。后台不得根据拒绝再自动猜测该缺失数据。补数据或切换相关输入时保留选择并提示该路径可恢复，只有用户恢复才重新运行；恢复不重新录入已有资料。选择跨次在明确范围内保留，不能默认扩大为未来所有患者。

## 3. 条件分支list

RuleNode包含summary、preconditions、trigger、branches、exceptions、follow_up、completion、required_facts、children、source_refs。Branch含condition、target_node_ids、actions、source_refs。优先显示当前路径，所有未触发分支仍可展开，不丢原文。

可计算AST最小语法：all/any/not、present、eq/ne/gt/ge/lt/le、in、date_interval；值为带类型的fact_ref或literal。数值用Decimal，单位显式，时间保留date/date-time和区间开闭。未知按三值逻辑：not unknown=unknown；all含false为false，否则含unknown为unknown；any含true为true，否则含unknown为unknown。未知不当false，不默认走另一分支。

无法转换为上述有限表达式的医学或复杂条款保存analysis_required及完整条件/原文，不执行模型生成代码。来源存在、数值一致只是必要检查；独立样例还要识别漏前提、否定颠倒、且或错换和丢例外。资料未提供的路径保留未覆盖；第一版不宣称穷尽所有临床可能。

用户增删修正产生RuleVersion与变更范围；保留原提取，未在新版出现不能自动当撤销。后续事实变化只影响关联路径和草稿。

## 4. 版本开始使用日期

DocumentVersion保留published_on和uploaded_at；M03的VersionActivation单独保存document_version_id、study/site_scope、starts_on、ends_before、actor、recorded_at、revision及可选范围例外。starts_on含当天，ends_before不含；按同范围后续启用日衔接，范围重叠不静默决策。用户录入的是实际开始使用日，不能被上传日覆盖。

规则核查以相关clinical_event_date解析，不能用报告生成时间代替事件时间。报告生成同时保存当次输出规则版本与每项历史Assessment使用的rule_version/activation_revision。以后新报告可包含旧事件和旧依据，签发快照不重写。启用日更正有影响预览与修订记录，不自动批量判PD。

## 5. 简单目录与阶段能力

DirectoryReference绑定M02原目录的document_version_id；用户可直接打开目录，在相关位置增加简要状态或缺件，锚点可为原页/行/用户标注。无可自动解析条目时reference_only仍是可用对照模式，不要求先全量录目录。W10再渐进提取可识别条目和目录变化；未识别范围不能称全部检查通过。

M05在W06硬依赖M01/M03/M04/M06。M10为W10才启用的可选集成，W06先通过M02公开读取已有对照文件或显示未提供；不能伪装M10已经实现。W10用公开端口补充状态，沿用原Issue和资料引用，不迁移成另一份问题库。

## 6. 首版核心自动核对

W08必须提供RecognizeLab的实际适配实现、文件输入、作业、字段提取与定位，进入既有M07/M08匹配和确定性比较。支持格式写入SupportProfile，含文件类型/版式、图像条件、验证范围、provider/model版本及已知限制。先交付约定支持格式；W14只增强困难版式和更多格式。

字段区分auto_extracted、user_corrected、unreadable、user_skipped；对象匹配区分unique_validated、ambiguous、unmatched。来源定位、结构校验及经评估的字段规则通过后，可自动产生带scope/unknowns的比较候选，保留未人工核实状态；模型自报置信度不能单独证明可用。低可信/歧义/异常集中查看，正常记录可按范围确认，不要求每字段机械点击。用户改值或改匹配后使对应结果待重算，不改源文件。

比较一致性和可计算逻辑；安全问题由M09按适用规则及已有上下文提出线索/待核实问题，不输出全局clinical_safe。少量失败可补录，用户也可跳过相应路径。自动读取全部不可用时可保存工作、看list与跟进问题，但不能宣称核心自动检验功能通过验收。

## 7. 验证与能力等级

code_complete、synthetic_validated、provider_validated、authorized_trial_ready分别记录。W08实现并用忠实合成文件及可获准provider验证支持范围；没有服务条件时实现可以记录，provider状态保持未验证。W13可汇总离线或合成证据，但核心自动能力未验证时必须给出未达标结论，不能将人工版本宣布为完整首版。W15配置获准实际环境与真实操作；可在既有缺口未完时安排必要环境准备，不假称用户实际试用已完成。

从开发开始保留独立评估样本及预期，分别记录身份/日期错配、数值/单位/比较符错误、条件遗漏、误报和漏检。统计原流程与新流程总时间、自动可用比例、需人工更正/补录比例和重做量；阈值在明确用途和代表性数据下制定，不凭空给百分比。

上线维护按用途保存风险、验证、能力/版本、反馈和暂停/恢复方法；这些是开发发布职责，不在每次监查增加审批或在确认整改前加材料门槛。现有AUD-001任务完成证据校验缺口仍开放，本契约本身不构成其修复证据。
