"""Derived development checklist; freshness is separate from actual acceptance."""
from __future__ import annotations

import hashlib
import json
import re

OUTPUTS = ('work_plan.json', 'WORK_PLAN.md')
SPEC = 'CANONICAL_SYSTEM_SPEC_V5.md'
STATES = {'NOT_STARTED', 'IN_PROGRESS', 'AWAITING_REVIEW', 'ACCEPTED',
          'RETURNED', 'BLOCKED', 'NOT_APPLICABLE'}
LABELS = dict(NOT_STARTED='待开始', IN_PROGRESS='进行中', AWAITING_REVIEW='待验收',
              ACCEPTED='验收通过', RETURNED='需返工', BLOCKED='受阻', NOT_APPLICABLE='有据不适用')


def sha(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing work-plan field: ' + field)


def unique_strings(value, field, allow_empty=False):
    if (not isinstance(value, list) or (not value and not allow_empty)
            or any(not isinstance(v, str) or not v.strip() for v in value)
            or len(set(value)) != len(value)):
        raise ValueError('Invalid work-plan list: ' + field)
    return value


def build(text, spec_sha256, trace, trace_module):
    config = trace_module.fenced_block(text, 'WORK_PLAN')
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported work-plan schema')
    catalog, _ = trace_module.units(text)
    context_refs = unique_strings(config.get('context_refs'), 'context_refs')
    if any(ref not in catalog or not ref.startswith('tech-work-') for ref in context_refs):
        raise ValueError('Missing work-plan context source')
    required_context = {ref for ref in catalog if ref.startswith('tech-work-') and ref != 'tech-work-26'}
    if set(context_refs) != required_context:
        raise ValueError('Unbound work-plan context source')
    context = {ref: catalog[ref]['sha256'] for ref in sorted(context_refs)}
    technical = {n['id']: n for n in trace['nodes']}
    logic = {s['id']: (n['id'], s) for n in trace['nodes'] for s in n['logic']}
    phases = config.get('phases')
    if (not isinstance(phases, list) or len(phases) != 4
            or [p.get('id') for p in phases] != [1, 2, 3, 4]):
        raise ValueError('Work plan must preserve the four canonical phases')
    for p in phases:
        require_text(p.get('name'), 'phase.name')
        require_text(p.get('gate'), 'phase.gate')
    items = config.get('items')
    if not isinstance(items, list) or not items:
        raise ValueError('Missing work-plan items')
    ids = [w.get('id') for w in items]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate work-plan ID')
    if [w.get('order') for w in items] != list(range(1, len(items) + 1)):
        raise ValueError('Work-plan orders must be continuous and unique')
    by_id = {w['id']: w for w in items}
    used_nodes, used_logic = set(), set()
    for w in items:
        wid = w['id']
        if not re.fullmatch(r'(?:W|G)\d{2}', wid):
            raise ValueError('Invalid work-plan ID: ' + str(wid))
        if w.get('kind') not in ('WORK', 'GATE') or (w['kind'] == 'GATE') != wid.startswith('G'):
            raise ValueError('Invalid work-plan kind: ' + wid)
        if type(w.get('phase')) is not int or w['phase'] not in (1, 2, 3, 4):
            raise ValueError('Invalid work-plan phase: ' + wid)
        for field in ('title', 'inputs', 'failure_action', 'work_type'):
            require_text(w.get(field), wid + '.' + field)
        for field in ('deliverables', 'acceptance', 'technical_nodes', 'logic_ids', 'depends_on'):
            unique_strings(w.get(field), wid + '.' + field, allow_empty=field in ('logic_ids', 'depends_on'))
        if len(w['acceptance']) < 3:
            raise ValueError('Missing positive/negative/integration acceptance: ' + wid)
        if any(n not in technical for n in w['technical_nodes']):
            raise ValueError('Unknown technical node in work plan: ' + wid)
        for lid in w['logic_ids']:
            if lid not in logic or logic[lid][0] not in w['technical_nodes']:
                raise ValueError('Unknown or unbound logic in work plan: ' + wid + ': ' + lid)
        used_nodes.update(w['technical_nodes'])
        used_logic.update(w['logic_ids'])
        deps = w['depends_on']
        if any(d not in by_id or d == wid for d in deps):
            raise ValueError('Unknown/self work-plan dependency: ' + wid)
        if any(by_id[d]['order'] >= w['order'] or by_id[d]['phase'] > w['phase'] for d in deps):
            raise ValueError('Cyclic/forward work-plan dependency: ' + wid)
        conditional = w.get('conditional')
        if conditional is not None:
            require_text(conditional, wid + '.conditional')
            if w['kind'] != 'WORK':
                raise ValueError('Stage gate cannot be conditional: ' + wid)
        state = w.get('progress')
        if state not in STATES or (state == 'NOT_APPLICABLE' and not conditional):
            raise ValueError('Invalid work-plan progress: ' + wid)
        evidence = w.get('evidence')
        if not isinstance(evidence, list):
            raise ValueError('Invalid work-plan evidence: ' + wid)
        for record in evidence:
            if not isinstance(record, dict):
                raise ValueError('Invalid work-plan evidence record: ' + wid)
            for field in ('record_id', 'reviewer', 'result', 'scope'):
                require_text(record.get(field), wid + '.evidence.' + field)
            for field in ('artifact_refs', 'validation_refs'):
                unique_strings(record.get(field), wid + '.evidence.' + field)
        if state in ('ACCEPTED', 'NOT_APPLICABLE') and not evidence:
            raise ValueError('Completed work plan requires actual evidence references: ' + wid)
        if not isinstance(w.get('reviewed_basis_sha256'), str) or not re.fullmatch('[0-9a-f]{64}', w['reviewed_basis_sha256']):
            raise ValueError('Missing reviewed work-plan basis: ' + wid)
    if used_nodes != set(technical):
        raise ValueError('Uncovered technical nodes in work plan: ' + repr(sorted(set(technical) - used_nodes)))
    if used_logic != set(logic):
        raise ValueError('Uncovered logic items in work plan: ' + repr(sorted(set(logic) - used_logic)))
    phase_gates = {}
    for p in phases:
        pid, gid = p['id'], p['gate']
        phase_items = [w for w in items if w['phase'] == pid]
        gate = by_id.get(gid)
        if (not gate or gate['kind'] != 'GATE' or gate['phase'] != pid
                or sum(w['kind'] == 'GATE' for w in phase_items) != 1
                or phase_items[-1]['id'] != gid):
            raise ValueError('Missing/misplaced phase gate: ' + str(pid))
        work_ids = {w['id'] for w in phase_items if w['kind'] == 'WORK'}
        if not work_ids or set(gate['depends_on']) != work_ids:
            raise ValueError('Phase gate must cover every work package: ' + gid)
        phase_gates[pid] = gid
    if [w['phase'] for w in items] != sorted(w['phase'] for w in items):
        raise ValueError('Work-plan phases must not interleave')

    def ancestors(wid):
        found = set()
        pending = list(by_id[wid]['depends_on'])
        while pending:
            dep = pending.pop()
            if dep not in found:
                found.add(dep)
                pending.extend(by_id[dep]['depends_on'])
        return found

    for w in items:
        if w['phase'] > 1 and phase_gates[w['phase'] - 1] not in ancestors(w['id']):
            raise ValueError('Work package bypasses previous phase gate: ' + w['id'])
        if w['progress'] == 'ACCEPTED' and any(by_id[d]['progress'] not in ('ACCEPTED', 'NOT_APPLICABLE') for d in w['depends_on']):
            raise ValueError('Cannot accept work before its dependencies: ' + w['id'])
    counts = dict(functional_modules=sum(n.startswith('T') for n in technical),
                  routes=sum(n.startswith('R') for n in technical), logic_items=len(logic),
                  work_packages=sum(w['kind'] == 'WORK' for w in items),
                  gates=sum(w['kind'] == 'GATE' for w in items), steps=len(items))
    if counts != config.get('expected_counts'):
        raise ValueError('Work-plan counts differ from declared inventory')
    computed = {}
    for w in items:
        wid = w['id']
        definition = {k: v for k, v in w.items() if k not in ('progress', 'evidence', 'reviewed_basis_sha256')}
        basis = dict(definition=sha(definition), context=context,
                     technical={n: technical[n]['basis_sha256'] for n in sorted(w['technical_nodes'])},
                     dependencies={d: computed[d]['basis_sha256'] for d in sorted(w['depends_on'])})
        digest = sha(basis)
        pending_nodes = sorted(n for n in w['technical_nodes'] if technical[n]['binding_status'] != 'CURRENT_BINDING')
        pending_deps = sorted(d for d in w['depends_on'] if computed[d]['binding_status'] != 'CURRENT_BINDING')
        pending_completion = sorted(d for d in w['depends_on'] if by_id[d]['progress'] not in ('ACCEPTED', 'NOT_APPLICABLE'))
        refs = set(trace['global_refs'])
        for node in w['technical_nodes']:
            refs.update(technical[node]['theory_refs'])
        for lid in w['logic_ids']:
            refs.update(logic[lid][1]['theory_refs'])
        computed[wid] = {**w, 'basis_sha256': digest, 'current_basis': basis,
                         'binding_status': 'CURRENT_BINDING' if digest == w['reviewed_basis_sha256'] and not pending_nodes and not pending_deps else 'REVIEW_REQUIRED',
                         'plan_basis_changed': digest != w['reviewed_basis_sha256'],
                         'pending_technical_nodes': pending_nodes, 'pending_binding_dependencies': pending_deps,
                         'pending_completion_dependencies': pending_completion,
                         'theory_refs': sorted(refs, key=lambda r: tuple(int(v) for v in trace['theory_to_technical'][r]['section'].split('.')))}
    return dict(schema_version=1, spec_sha256=spec_sha256, counts=counts, phases=phases,
                meaning='Planning correspondence only; no implementation acceptance, stage approval or execution permission.',
                review_required=[w for w, data in computed.items() if data['binding_status'] != 'CURRENT_BINDING'],
                items=list(computed.values()), context_sources={r: {k: catalog[r][k] for k in ('section', 'title', 'sha256')} for r in context_refs},
                technical_coverage={nid: [w['id'] for w in items if nid in w['technical_nodes']] for nid in sorted(technical)},
                logic_coverage={lid: [w['id'] for w in items if lid in w['logic_ids']] for lid in sorted(logic)},
                module_checklists={nid: dict(title=n['intent'], logic=n['logic'],
                                            works_by_phase={str(p): [w['id'] for w in items if w['kind'] == 'WORK' and w['phase'] == p and nid in w['technical_nodes']] for p in range(1, 5)})
                                   for nid, n in technical.items() if nid.startswith('T')},
                source_catalog=trace['theory_to_technical'])


def report(plan):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')

    def links(values):
        return '、'.join('[' + v + '](#' + v.lower() + ')' for v in values) or '无'

    counts = plan['counts']
    lines = ['# 内参系统开发工作清单', '',
             '本文件从[最高说明§26](' + SPEC + '#tech-work-26)机械生成；任务、验收条件及进度只改唯一原文。', '',
             '**' + str(counts['functional_modules']) + '个功能模块，' + str(counts['routes']) + '条跨模块路线，' + str(counts['logic_items']) + '项既有逻辑；拆为' + str(counts['work_packages']) + '个小工作包，加' + str(counts['gates']) + '个阶段验收门，共' + str(counts['steps']) + '步。**', '',
             '工作包不是新增服务、模型或Agent。顺序号用于对照；按明确前置依赖推进，同阶段独立项可并行，仍须原阶段质量门。', '',
             'CURRENT_BINDING只表示清单与当前理论/技术设计关联一致，**不表示已写代码、能力通过、阶段通过或获准运行**。', '',
             '当前规范SHA-256：' + chr(96) + plan['spec_sha256'] + chr(96) + '。', '',
             '清单需复核：' + ('、'.join(plan['review_required']) or '无；仅限清单关联新鲜度。'), '',
             '验收通过：' + str(sum(w['progress'] == 'ACCEPTED' for w in plan['items'])) + '；有据不适用：' + str(sum(w['progress'] == 'NOT_APPLICABLE' for w in plan['items'])) + '；其余按下表实际状态。', '',
             '**交付类型分开统计**：第一阶段人工准备/内容验证已验收' + str(sum(w['phase'] == 1 and w['kind'] == 'WORK' and w['progress'] == 'ACCEPTED' for w in plan['items'])) + '包；代码与接口工作包已验收' + str(sum(w['work_type'] == '代码与接口工作包' and w['progress'] == 'ACCEPTED' for w in plan['items'])) + '包、进行中/待验收' + str(sum(w['work_type'] == '代码与接口工作包' and w['progress'] in ('IN_PROGRESS', 'AWAITING_REVIEW') for w in plan['items'])) + '包。人工验收数量不表示业务模块已编码；模块完成须另核相应代码、接口、测试和适用阶段门。', '',
             '## 四阶段与数量', '', '| 阶段 | 小工作包 | 阶段门 | 对照步骤数 | 主要交付 |', '|---|---:|---|---:|---|']
    summaries = {1: '人工真实专题→完整同周样刊；内容验证先行', 2: '最小研究代码→真实跨周/纠错→六例',
                 3: '按题专业能力与有据增益，必要时比较分工', 4: '生产离线预演、恢复/交付及年度双输入回放'}
    for p in plan['phases']:
        ws = [w for w in plan['items'] if w['phase'] == p['id']]
        lines.append('| ' + str(p['id']) + ' ' + p['name'] + ' | ' + str(sum(w['kind'] == 'WORK' for w in ws)) + ' | ' + links([p['gate']]) + ' | ' + str(len(ws)) + ' | ' + summaries[p['id']] + ' |')
    lines += ['', '## 每包共同验收Q01—Q07', '',
              '各包同时满足[§26.2](' + SPEC + '#tech-work-26-2)的Q01—Q07：依据新鲜、输入/前置有效、实际交付物、正反及衔接结果、失败/限制、相称复核、主要投入与权限。', '',
              '结果记录复用RunLog/Review/Git与私有成果指针。模板：[§26.3](' + SPEC + '#tech-work-26-3)。验收清单存在或复选框被勾选，不构成实际证据。', '',
              '## 按步骤对照', '',
              '| 顺序 | 工作包/阶段门 | 类型 | T/R | 前置工作包 | 实际进度 / 关联 |', '|---:|---|---|---|---|---|']
    for w in plan['items']:
        lines.append('| ' + str(w['order']) + ' | [' + w['id'] + ' ' + cell(w['title']) + '](#' + w['id'].lower() + ') | ' + cell(w['work_type']) + ' | ' + '/'.join(w['technical_nodes']) + ' | ' + links(w['depends_on']) + ' | ' + LABELS[w['progress']] + ' / ' + w['binding_status'] + ' |')
    for w in plan['items']:
        lines += ['', '<a id="' + w['id'].lower() + '"></a>', '## ' + w['id'] + '｜' + w['title'], '',
                  '顺序：' + str(w['order']) + '/' + str(counts['steps']) + '；阶段：' + str(w['phase']) + '；类型：' + w['work_type'] + '。', '',
                  '进度：**' + LABELS[w['progress']] + '**；关联：' + w['binding_status'] + '；前置：' + links(w['depends_on']) + '。', '',
                  '前置尚未验收：' + links(w['pending_completion_dependencies']) + '。仅供执行者核对，生成器不代为验收阶段。', '',
                  '责任模块/路线：' + '、'.join('[' + n + '](TECHNICAL_TRACE.md#' + n.lower() + ')' for n in w['technical_nodes']) + '。', '',
                  '逐项逻辑：' + ('、'.join(w['logic_ids']) or '本项为综合验收，按所列T/R及本卡检查。') + '。', '',
                  '理论依据：' + '、'.join('[§' + plan['source_catalog'][r]['section'] + '](' + SPEC + '#' + r + ')' for r in w['theory_refs']) + '。原定义/例外仍须回原文读取。', '',
                  '**输入**：' + w['inputs'], '', '**交付物**：', '']
        lines += ['- ' + d for d in w['deliverables']]
        if w['conditional']:
            lines += ['', '**条件项**：' + w['conditional']]
        lines += ['', '**验收清单**（另核Q01—Q07）：', '']
        marks = ['正向', '反向', '衔接'] if w['kind'] == 'WORK' else ['内容与证据', '范围与质量', '禁止的捷径']
        for i, check in enumerate(w['acceptance']):
            lines.append('- [ ] ' + (marks[i] + '：' if i < len(marks) else '') + check)
        lines += ['- [ ] 填写实际产物/版本、验证结果、复核者及通过范围；未执行保持待验，不能填预期结果冒充实测。', '',
                  '**不通过时**：' + w['failure_action'], '',
                  '关联变化：本卡依据变化=' + str(w['plan_basis_changed']) + '；待复核T/R=' + ('/'.join(w['pending_technical_nodes']) or '无') + '；上游清单待复核=' + ('/'.join(w['pending_binding_dependencies']) or '无') + '。', '',
                  '实际证据：' + (json.dumps(w['evidence'], ensure_ascii=False) if w['evidence'] else '尚无；本轮只制定清单，未据此宣布开发或能力完成。')]
    lines += ['', '## 13个功能模块的验收清单', '',
              '以下逐项取自§25既有逻辑的启用条件、输出和限制，不另写一套模块规则。按本次阶段/稿型/允许用途验收，相关工作包提交实际证据；不要求先完成未来全部增强才能制作第一份样刊。', '']
    for nid, module in plan['module_checklists'].items():
        lines += ['<a id="module-' + nid.lower() + '"></a>', '### ' + nid + '｜' + module['title'], '',
                  '设计及完整逻辑：[技术关联](TECHNICAL_TRACE.md#' + nid.lower() + ')。', '']
        for phase, work_ids in module['works_by_phase'].items():
            if work_ids:
                lines.append('- 第' + phase + '阶段承接：' + links(work_ids) + '。')
        lines.append('')
        for step in module['logic']:
            lines.append('- [ ] ' + step['id'] + ' ' + step['action'] + '：条件=' + step['condition'] + '；实际输出=' + step['output'] + '；限制=' + step['limit'] + '。')
        lines += ['- [ ] 所列适用工作包的实际证据与本次模块版本一致；记录已实现/未实现、通过/失败/未验范围，按原逻辑去向返工。', '']
    lines += ['', '## 功能模块及路线反向索引', '', '| T/R | 工作包/阶段门 |', '|---|---|']
    for nid, work_ids in plan['technical_coverage'].items():
        lines.append('| [' + nid + '](TECHNICAL_TRACE.md#' + nid.lower() + ') | ' + links(work_ids) + ' |')
    lines += ['', '## 72项逻辑覆盖索引', '', '| 逻辑ID | 对应工作包 |', '|---|---|']
    for lid, work_ids in plan['logic_coverage'].items():
        lines.append('| ' + lid + ' | ' + links(work_ids) + ' |')
    return '\n'.join(lines) + '\n'


def project(text, digest, trace, trace_module):
    plan = build(text, digest, trace, trace_module)
    return {'work_plan.json': (json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'),
            'WORK_PLAN.md': report(plan).encode('utf-8')}


def pending_errors(plan, work_ids=None):
    by_id = {w['id']: w for w in plan['items']}
    selected = sorted(set(work_ids)) if work_ids is not None else sorted(by_id)
    errors = []
    for wid in selected:
        if wid not in by_id:
            errors.append('Unknown work-plan ID: ' + wid)
        elif by_id[wid]['binding_status'] != 'CURRENT_BINDING':
            errors.append('Work plan requires review: ' + wid)
    return errors
