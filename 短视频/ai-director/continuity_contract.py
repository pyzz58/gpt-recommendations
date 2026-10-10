"""Replay an explicit, offline, per-shot continuity contract.

JSON Schema shape mirrors python-jsonschema's documented Draft 2020-12 support.
No runtime dependencies; semantic transitions are purpose-built because FSM
libraries do not infer object motion from the script.
"""
from __future__ import annotations
import re

PROP_LOCATION = re.compile(r'^(?:LOC[A-Za-z0-9_]+:[A-Za-z0-9_]+|CH[A-Za-z0-9_]+:hand)$')
ACTOR_LOCATION = re.compile(r'^LOC[A-Za-z0-9_]+(?::[A-Za-z0-9_]+)?$')


def audit_contract(plan):
    contract = plan.get('continuity_contract')
    if contract is None:
        return []
    findings = []
    def add(code, ids, reason, suggestion='核对分镜及物品位置后补足合法的状态转移。', severity='blocker'):
        findings.append({'code': code, 'severity': severity, 'shot_ids': ids, 'reason': reason, 'suggestion': suggestion})
    if not isinstance(contract, dict) or contract.get('version') != 1 or contract.get('coverage') != 'complete':
        add('CONTRACT_INVALID', [], 'continuity_contract 必须声明 version=1、coverage=complete。')
        return findings
    props = contract.get('props')
    actors = contract.get('actors')
    if not isinstance(props, dict) or not isinstance(actors, dict):
        add('CONTRACT_INVALID', [], 'props、actors 必须是以稳定 ID 为键的字典。')
        return findings
    prop_ids, actor_ids = set(props), set(actors)
    state_p, state_a = {}, {}
    for kind, entries, target, pattern in [('道具', props, state_p, PROP_LOCATION), ('人物', actors, state_a, ACTOR_LOCATION)]:
        for ident, item in entries.items():
            if not isinstance(ident, str) or not ident or not isinstance(item, dict) or not isinstance(item.get('initial'), str) or not pattern.fullmatch(item['initial']):
                add('ASSET_INVALID', [], f'{kind} {ident!r} 缺少合法的 initial 位置。')
                continue
            target[ident] = item['initial']
    if len(state_p) != len(props) or len(state_a) != len(actors):
        return findings
    character_ids = {x.get('id') for x in plan.get('characters', []) if isinstance(x, dict)}
    if actor_ids - character_ids:
        add('ACTOR_ID_UNDECLARED', [], f'连续性资产的人物没有全部出现在 characters：{sorted(actor_ids - character_ids)}')
    for shot in plan.get('shots', []):
        sid = shot.get('id', '?')
        st = shot.get('continuity_state')
        if not isinstance(st, dict):
            add('SHOT_STATE_MISSING', [sid], '完整追踪模式要求每一镜都填写 continuity_state（包括不出镜的道具）。')
            continue
        if not all(isinstance(st.get(k), dict) for k in ('props_before', 'props_after', 'actors_before', 'actors_after')) or not all(isinstance(st.get(k), list) for k in ('prop_moves', 'actor_moves')):
            add('SHOT_STATE_INVALID', [sid], '缺少 props_before/after、actors_before/after 或 prop_moves/actor_moves。')
            continue
        def compare(stage, actual, expected, ids, kind):
            if set(actual) != ids:
                add('STATE_COVERAGE_GAP', [sid], f'{kind} {stage} 覆盖不完整：缺少{sorted(ids-set(actual))}，多出{sorted(set(actual)-ids)}。')
            for ident in sorted(set(actual) & ids):
                if actual[ident] != expected[ident]:
                    add('STATE_MISMATCH', [sid], f'{kind} {ident} 的{stage}是 {actual[ident]}，实际应为 {expected[ident]}。')
        compare('before', st['props_before'], state_p, prop_ids, '道具')
        compare('before', st['actors_before'], state_a, actor_ids, '人物')
        # Keep a single deterministic event timeline so a person may walk to
        # another room before picking up or putting down an object. All events
        # must have a strict integer order within the shot.
        events = []
        for kind, key in [('actor', 'actor_moves'), ('prop', 'prop_moves')]:
            for m in st[key]:
                if not isinstance(m, dict) or not isinstance(m.get('order'), int) or isinstance(m.get('order'), bool):
                    add('MOVE_INVALID', [sid], f'{key} 事件必须是对象，带整数 order。')
                    continue
                events.append((m['order'], kind, m))
        if len(events) != len({v[0] for v in events}):
            add('EVENT_ORDER_DUPLICATED', [sid], '演员与道具移动事件 order 必须在该镜头内唯一。')
        for _, kind, m in sorted(events, key=lambda x: x[0]):
            ident = m.get('actor') if kind == 'actor' else m.get('prop')
            src, dst, action = m.get('from'), m.get('to'), m.get('kind')
            state, known, regex = (state_a, actor_ids, ACTOR_LOCATION) if kind == 'actor' else (state_p, prop_ids, PROP_LOCATION)
            if ident not in known or not isinstance(src, str) or not isinstance(dst, str) or not regex.fullmatch(src) or not regex.fullmatch(dst):
                add('MOVE_INVALID', [sid], f'{kind}事件引用未知资产或不合法位置：{m!r}。')
                continue
            if state[ident] != src:
                add('MOVE_FROM_MISMATCH', [sid], f'{ident} 从 {src} 移动，但此前位置为 {state[ident]}。')
                continue
            if not isinstance(m.get('visible'), bool):
                add('MOVE_INVALID', [sid], f'{ident} 移动未明确 visible=true/false。')
                continue
            if not m['visible']:
                if not isinstance(m.get('note'), str) or not m['note'].strip():
                    add('ELLIPSIS_UNJUSTIFIED', [sid], f'{ident} 场外移动没有说明为何允许省略。')
                    continue
                add('ELLIPSIS_REVIEW', [sid], f'{ident} 的场外移动需人工确认：{m["note"]}', severity='review')
            if kind == 'actor':
                if action not in ('walk', 'cut', 'reposition') or src == dst:
                    add('ACTOR_MOVE_INVALID', [sid], f'{ident} 人物移动类型或位置无效：{action}, {src} → {dst}。')
                    continue
            else:
                src_hand, dst_hand = src.endswith(':hand'), dst.endswith(':hand')
                allowed = ((not src_hand and dst_hand and action == 'pickup') or
                           (src_hand and not dst_hand and action == 'place') or
                           (src_hand and dst_hand and src != dst and action == 'handoff') or
                           (not src_hand and not dst_hand and src.split(':')[0] == dst.split(':')[0]
                            and src != dst and action == 'slide'))
                if not allowed:
                    add('ILLEGAL_PROP_TRANSITION', [sid], f'{ident} 不允许 {src} → {dst} ({action})：跨场景必须经过手持或有明确动作。')
                    continue
                actor = dst.split(':')[0] if dst_hand else (src.split(':')[0] if src_hand else None)
                actor_place = src if not src_hand else dst
                if actor and (actor not in state_a or state_a[actor].split(':')[0] != actor_place.split(':')[0]):
                    add('ACTOR_PROP_SCENE_MISMATCH', [sid], f'{ident} 操作发生在 {actor_place}，但 {actor} 人物不在该场景。')
                    continue
            state[ident] = dst
        compare('after', st['props_after'], state_p, prop_ids, '道具')
        compare('after', st['actors_after'], state_a, actor_ids, '人物')
    return findings
