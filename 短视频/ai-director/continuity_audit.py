"""Offline conservative continuity checks for AI-director plans.

The machine checks only observable scripted movements and explicit state data.
It never silently rewrites human work or claims to understand every scene.
"""
from __future__ import annotations

import re

PROPS = {'手机': 'phone', '书': 'book'}
PICK = r'(?:拿起|捡起|拾起|取回|拿回|取出|抓起|拿走|拎起|拿着|握着|带上)'
LOCATIONS = {'沙发扶手': 'sofa_arm', '茶几': 'coffee_table', '抽屉': 'drawer', '书桌': 'desk'}


def _piece(shot):
    action = shot.get('action') or {}
    return '；'.join(str(action.get(k, '')) for k in ('start', 'action', 'micro_action', 'reaction', 'end'))


def _pickup(text, name):
    return bool(re.search(rf'{PICK}.{{0,9}}{name}|{name}.{{0,6}}{PICK}', text))


def _placed(text, name):
    # A placement needs an identifiable verb and destination. A limited
    # two-clause drawer case handles “拉开抽屉，把手机放进去”. Never infer moves
    # from an action.start state or from scenery inventory.
    clauses = re.split('[；，。]', text)
    for i, clause in enumerate(clauses):
        if name not in clause or not re.search(r'(放|扣|搁|摆|塞)', clause):
            continue
        for key, loc in LOCATIONS.items():
            if key in clause and re.search(rf'{name}.{{0,12}}(?:放|扣|搁|摆|塞).{{0,12}}{key}', clause):
                return loc
        if (i > 0 and '抽屉' in clauses[i - 1]
                and re.search(r'(拉开|打开|抽出)', clauses[i - 1])
                and re.search(rf'{name}.{{0,8}}(?:放进去|塞进去|放入)', clause)):
            return 'drawer'
    return None

def audit_plan(plan):
    """Return deterministic findings. 'blocker' prevents further *paid* stages.

    This is not AI semantic understanding. Unannotated/ambiguous actions remain
    review findings; never infer off-camera movements as proven errors.
    """
    shots = plan.get('shots', [])
    scenes = {s.get('id'): s.get('description', '') for s in plan.get('scenes', [])}
    issues = []
    def add(code, level, ids, reason, fix):
        if not any(f['code'] == code and f['shot_ids'] == ids for f in issues):
            issues.append({'code': code, 'severity': level, 'shot_ids': ids,
                           'reason': reason, 'suggestion': fix})

    # A shot's start position is inconsistent with a scene's fixed prop layout.
    for sh in shots:
        sid = sh.get('id', '?')
        shot_text = str(sh.get('visual', '')) + '；' + str((sh.get('action') or {}).get('start',''))
        scene = scenes.get(sh.get('scene_id'), '')
        if re.search(r'手(?:里|中).{0,6}(?:拿着|握着|持着).{0,4}(?:一?本)?书.{0,16}(?:从玄关|从门口|进客厅|走进客厅)', shot_text):
            if re.search(r'茶几上.{0,8}(?:书|书本)', scene):
                add('SCENE_PROP_DOUBLE_BOOK', 'review', [sid],
                    '场景预设书在茶几，镜头却从别处手持同一本书进入；需交代拿书前的物理位置。',
                    '镜头改为先在茶几上看见书，或明确上一镜从茶几拿起。')

    # Optional machine-checkable per-shot state contract. Any prop name works;
    # the Chinese NLP hints below are *additional* and deliberately limited.
    declared = {}
    for sh in shots:
        sid = sh.get('id', '?')
        contract = sh.get('continuity_state')
        if contract is None:
            continue
        if not isinstance(contract, dict):
            add('CONTINUITY_MANIFEST_INVALID', 'blocker', [sid],
                'continuity_state 必须是对象。', '填入 props_before、prop_moves、props_after。')
            continue
        before = contract.get('props_before', {})
        moves = contract.get('prop_moves', [])
        after = contract.get('props_after', {})
        if not isinstance(before, dict) or not isinstance(after, dict) or not isinstance(moves, list):
            add('CONTINUITY_MANIFEST_INVALID', 'blocker', [sid],
                'continuity_state 字段类型错误。', '按照 props_before、prop_moves、props_after 的格式填写。')
            continue
        for prop, loc in before.items():
            if prop in declared and declared[prop] != loc:
                add('DECLARED_PROP_STATE_MISMATCH', 'blocker', [sid],
                    f'{prop}上一明确位置是 {declared[prop]}，本镜却声明从 {loc} 开始。',
                    '修正上一镜结束位置或补足搬运动作。')
            declared[prop] = loc
        for move in moves:
            if not isinstance(move, dict) or any(not move.get(k) for k in ('prop', 'from', 'to')):
                add('CONTINUITY_MOVE_INVALID', 'blocker', [sid],
                    '物品转移记录需要 prop/from/to。', '补足结构化移动描述。')
                continue
            prop, origin, dest = move['prop'], move['from'], move['to']
            if declared.get(prop, origin) != origin:
                add('CONTINUITY_MOVE_FROM_MISMATCH', 'blocker', [sid],
                    f'{prop}物品转移起点 {origin} 不等于已知位置 {declared[prop]}。',
                    '按镜头时间线逐步补充合法取回/放置事件。')
            declared[prop] = dest
        for prop, loc in after.items():
            if declared.get(prop, loc) != loc:
                add('CONTINUITY_MOVE_NOT_RECORDED', 'blocker', [sid],
                    f'{prop}镜头结束位置 {loc} 与已知位置 {declared[prop]} 不同，缺少动作。',
                    '在 prop_moves 加一条物品转移，不能让道具无动作瞬移。')
            declared[prop] = loc

    # Prop ledger: only clear move events establish a physical location.
    state = {}  # name -> (location, shot_id)
    for sh in shots:
        sid = sh.get('id', '?')
        action = str((sh.get('action') or {}).get('action', ''))
        visual = str(sh.get('visual', ''))
        for name in PROPS:
            # A scripted pickup takes precedence over visual descriptions of
            # the shot's opening state (which can mention the old resting spot).
            dest = _placed(action, name)
            if dest is None and not _pickup(action, name):
                dest = _placed(visual, name)
            if dest:
                previous = state.get(name)
                if previous and previous[0] not in (dest, 'hand') and not _pickup(action, name):
                    add('PROP_TRANSFER_MISSING_' + PROPS[name].upper(), 'blocker',
                        [previous[1], sid],
                        f'{name}在{previous[1]}放于{previous[0]}，{sid}直接被放到{dest}，中间没有明确取回或搬运动作。',
                        f'在中间镜头明确拍到从{previous[0]}拿起{name}，再移至{dest}，并记录镜头结束位置。')
                state[name] = (dest, sid)
            elif _pickup(action, name):
                # An explicit pickup carries the object in the person's hand
                # into the next shot, so a later placement is not teleportation.
                state[name] = ('hand', sid)
            # Arrival as a prop on a new scene does not by itself prove a move.
            elif name == '书' and '同一本书' in str(sh.get('art', {}).get('set_props', '')):
                prev = state.get(name)
                scdesc = scenes.get(sh.get('scene_id'), '')
                if prev and prev[0] == 'coffee_table' and '书桌' in scdesc and not any(f['code']=='PROP_APPEARANCE_UNEXPLAINED_BOOK' for f in issues):
                    add('PROP_APPEARANCE_UNEXPLAINED_BOOK', 'review',
                        [prev[1], sid],
                        f'书在{prev[1]}被放在茶几，{sid}书桌道具清单却已有同一本书，未说明转移。',
                        '在人物移动时明确携带书，或者保持书在茶几并重新安排结尾。')

    # Adjacent character scene jumps are reviewable, not always errors: a cut
    # might intentionally omit travel. Only prompt for a human decision.
    for before, after in zip(shots, shots[1:]):
        shared = set(before.get('character_ids', [])) & set(after.get('character_ids', []))
        if not shared or before.get('scene_id') == after.get('scene_id'):
            continue
        movement = str((before.get('action') or {}).get('end', '')) + '；' + str((after.get('action') or {}).get('start', '')) + '；' + str((after.get('action') or {}).get('action', ''))
        if not re.search(r'(走到|走进|走出|起身|站起|站直|穿过|走向|迈步|经过|移动|回到|跑向)', movement):
            add('ACTOR_TRANSFER_UNEXPLAINED', 'review',
                [before.get('id', '?'), after.get('id', '?')],
                '相邻镜头同一角色换场，缺少起身/移动/到达描述；可能是有意省略的剪辑。',
                '明确选择跳切省略，或补一个从原位置到新位置的动作。')

    for sh in shots:
        action = (sh.get('action') or {}).get('action', '')
        if sh.get('visual_type') == 'ai_video' and sh.get('duration', 0) <= 5:
            if action.count('、') >= 2:
                add('ACTION_OVERLOAD', 'review', [sh.get('id', '?')],
                    f'{sh.get("duration")}秒镜头安排多个连续动作，可能无法自然完成：{action}',
                    '减少动作，或从重复镜头中重新分配时长。')

    # Editorial repetition: 3 consecutive shots entirely about the same activity.
    for triple in zip(shots, shots[1:], shots[2:]):
        if all(any(word in str(s.get('visual','')) for word in ('手机','滑动','上滑','打字','消息'))
               and s.get('purpose') == 'development'
               and (s.get('camera') or {}).get('shot_size') in ('特写','近景','中近景') for s in triple):
            add('REPETITIVE_PHONE_BEATS', 'review', [s.get('id', '?') for s in triple],
                '连续三个推进镜头围绕同一手机动作，容易视觉重复。',
                '增加时间跳跃、环境或景别变化，不用三个相似脸部特写。')

    prod = plan.get('production', {})
    for key, kind in [('music_license_check', '音乐'), ('asset_license_check', '素材')]:
        if prod.get(key) is True and not prod.get(key + '_evidence'):
            add('LICENSE_EVIDENCE_MISSING_' + key.upper(), 'review', [],
                f'{kind}授权检查标记为 true，但没有对应的核验依据；仅有计划不等于已经取得授权。',
                '核对实际素材授权后添加证据；此前应设为 false/待核实。')

    from continuity_contract import audit_contract
    issues.extend(audit_contract(plan))

    return {'version': 1, 'shot_count': len(shots),
            'blockers': sum(x['severity'] == 'blocker' for x in issues),
            'reviews': sum(x['severity'] == 'review' for x in issues),
            'findings': issues,
            'scope': 'deterministic partial checks; omitted actions and implicit cuts need human review'}


def format_report(result):
    lines = ['# 物理连续性与可执行性审查（本地自动生成）', '',
             f'镜头：{result["shot_count"]}；阻断：{result["blockers"]}；待人工确认：{result["reviews"]}',
             '', '只检查可观察的动作与明确位置。没有发现问题不等于保证物理连续。',
             '修订必须保留原文件，不得无声覆盖，不得自动产生模型费用。', '']
    for i, f in enumerate(result['findings'], 1):
        lines.extend([f'## {i}. {f["code"]} [{f["severity"]}]',
                      f'镜头：{", ".join(f["shot_ids"]) or "全局"}',
                      '问题：' + f['reason'], '建议：' + f['suggestion'], ''])
    lines.extend(['## 给 Codex 的安全修订任务', '',
                  '读取同目录 plan.json 与上述问题；先创建 plan.proposed.json，绝不覆盖原件。',
                  '消除所有 blocker，并逐项判断 review 是否合理；不要把误报直接变成新的虚构动作。',
                  '修复道具和人物转场时，同步修改 visual、action.start/action/end、continuity、set_props 和 continuity_state。',
                  '控制每镜动作数量与秒数，重新计算所有镜头 start，保持总 duration 与末镜结束时间一致。',
                  '不更改已经固定的角色面貌/服装/系列视觉设定，不添加未经验证的研究与素材授权。',
                  '候选稿必须再次通过 director.validate 与本审查器；保留人工审核状态。',
                  '整个修订过程不允许额外调用付费 API，不增加模型调用次数。', ''])
    return '\n'.join(lines)
