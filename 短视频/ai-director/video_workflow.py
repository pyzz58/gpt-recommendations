"""Single-shot operator workflow over the existing Seedance adapter.

No server, background worker, auto-retry, account discovery or batch generation.
Only explicit submit/query/download commands use the network. CLI secrets are
read from a no-echo terminal, never arguments, environment or saved records.
The caller must provide a trusted private runtime; this is not authentication.
"""
from __future__ import annotations
import argparse
import getpass
import hashlib
import html
import json
import math
import os
from pathlib import Path
import sys
import time
import warnings

import seedance_adapter as api

CHECKS = ('story_action', 'framing', 'dialogue', 'lip_sync', 'audio', 'timing', 'character_consistency')
DECISIONS = ('retain_candidate', 'revise', 'reject')
LABELS = {
    'prepared': '请求已准备，尚未提交', 'submission_unknown': '提交结果不明，须人工核对；禁止重发',
    'submitted': '已取得任务编号，等待查询', 'queued': '供应商排队中', 'running': '供应商生成中',
    'failed': '供应商返回失败', 'cancelled': '供应商任务已取消', 'expired': '供应商任务已过期',
    'download_ready': '生成已完成，尚未保存视频', 'save_incomplete': '视频保存记录不完整，须人工核对',
    'review_pending': '视频已保存，等待观看审片', 'retain_candidate': '人工记录：保留这一候选',
    'revise': '人工记录：需要修改', 'reject': '人工记录：弃用这一候选',
}


def _need(ok, code):
    if not ok: raise api.SeedanceError(code)


def _proposal(job):
    root = api._private_root(job)
    packet = api._read(root / 'proposal.json')
    api._packet(packet)
    if (root / 'intent.json').exists():
        intent = api._read(root / 'intent.json')
        _need(intent['packet'] == packet, 'PROPOSAL_INTENT_MISMATCH')
    return root, packet


def prepare_job(base, direction, shot_id, *, private_dir, provider, audio_mode='silent_post', reference_images=()):
    root = api._private_root(private_dir)
    _need(not any(root.iterdir()), 'NEW_EMPTY_PRIVATE_JOB_REQUIRED')
    packet = api.prepare_shot(base, direction, shot_id, provider=provider,
                              audio_mode=audio_mode, reference_images=reference_images)
    api._atomic_create(root / 'proposal.json', packet)
    return inspect_job(root)


def _media(root, packet, receipt):
    info = api._read(root / 'media.json')
    path = root / 'video.mp4'
    _need(not path.is_symlink() and path.is_file() and not path.stat().st_mode & 0o077
          and path.stat().st_size <= api.MAX_VIDEO, 'MEDIA_FILE_INVALID')
    sha = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''): sha.update(chunk)
    _need(info.get('task_id') == receipt['task_id']
          and info.get('request_digest') == packet['request_digest']
          and info.get('bytes') == path.stat().st_size
          and info.get('sha256') == sha.hexdigest(), 'MEDIA_BINDING_MISMATCH')
    return info


def inspect_job(private_dir):
    """Offline state derived from existing receipts, never a live provider poll."""
    root, packet = _proposal(private_dir)
    view = dict(shot_id=packet['shot_id'], request_digest=packet['request_digest'], provider=packet['provider'],
                scope=packet['scope'], planned_duration_s=packet['body']['duration'],
                audio_mode=packet['audio_mode'], requires_lip_sync=any(
                    x.get('kind') == 'onscreen_dialogue' for x in
                    (packet['postproduction'].get('speech') or {}).get('dialogue', [])),
                state='prepared', live_status_checked=False, media_sha256=None,
                human_review_recorded=False, production_approved=False, final_film_completed=False)
    if (root / 'intent.json').exists(): view['state'] = 'submission_unknown'
    if not (root / 'receipt.json').exists():
        _need(not any((root / f).exists() for f in ('result.json', 'video.mp4', 'media.json', 'review.json')),
              'ORPHANED_MEDIA_RECORD')
        return view
    receipt = api._read(root / 'receipt.json')
    _need((root / 'intent.json').exists()
          and receipt.get('request_digest') == packet['request_digest']
          and receipt.get('provider') == packet['provider']
          and isinstance(receipt.get('task_id'), str) and api.TASK_ID.fullmatch(receipt['task_id']),
          'RECEIPT_MISMATCH')
    view.update(state='submitted', task_id=receipt['task_id'])
    observations = sorted(root.glob('observation-*.json'))
    if observations:
        last = api._read(observations[-1])
        _need(last.get('request_digest') == packet['request_digest']
              and last.get('task_id') == receipt['task_id']
              and last.get('status') in ('queued', 'running', 'failed', 'cancelled', 'expired', 'succeeded'),
              'OBSERVATION_MISMATCH')
        view.update(state=last['status'] if last['status'] != 'succeeded' else 'download_ready',
                    last_query_unix_ns=last['queried_unix_ns'])
    if (root / 'result.json').exists():
        result = api._read(root / 'result.json')
        _need(result.get('id') == receipt['task_id'] and result.get('status') == 'succeeded'
              and result.get('model') == packet['body']['model'], 'RESULT_MISMATCH')
        view['state'] = 'download_ready'
    if (root / 'video.mp4').exists() or (root / 'media.json').exists():
        _need((root / 'result.json').exists(), 'RESULT_MISSING')
        if not ((root / 'video.mp4').exists() and (root / 'media.json').exists()):
            view['state'] = 'save_incomplete'
            return view
        info = _media(root, packet, receipt)
        view.update(state='review_pending', media_sha256=info['sha256'])
    if (root / 'review.json').exists():
        record = api._read(root / 'review.json')
        _check_review(record, view)
        view.update(state=record['decision'], human_review_recorded=True)
    return view


def submit_job(private_dir, *, api_key, approval):
    root, packet = _proposal(private_dir)
    _need(inspect_job(root)['state'] == 'prepared', 'SUBMISSION_ALREADY_ATTEMPTED_RECONCILE')
    return api.submit_once(packet, private_dir=root, api_key=api_key, approval=approval)


def query_job(private_dir, *, api_key):
    root, packet = _proposal(private_dir)
    inspect_job(root)
    result = api.query_once(private_dir=root, api_key=api_key)
    now = time.time_ns()
    api._atomic_create(root / ('observation-%020d.json' % now),
                       dict(request_digest=packet['request_digest'], task_id=result['task_id'],
                            status=result['status'], queried_unix_ns=now))
    return inspect_job(root)


def download_job(private_dir):
    root, _ = _proposal(private_dir)
    _need(inspect_job(root)['state'] == 'download_ready', 'DOWNLOAD_NOT_READY')
    api.download_result(private_dir=root)
    return inspect_job(root)


def _check_review(record, view):
    _need(isinstance(record, dict) and set(record) == {
        'request_digest', 'media_sha256', 'decision', 'reviewer', 'watched_full_clip',
        'observed_duration_s', 'checks', 'notes'}, 'REVIEW_FIELDS_INVALID')
    _need(view['media_sha256'] is not None and record['media_sha256'] == view['media_sha256']
          and record['request_digest'] == view['request_digest'], 'REVIEW_MEDIA_MISMATCH')
    _need(record['decision'] in DECISIONS and record['watched_full_clip'] is True
          and isinstance(record['reviewer'], str) and bool(record['reviewer'].strip())
          and len(record['reviewer']) <= 200 and isinstance(record['notes'], str)
          and 0 < len(record['notes'].strip()) <= 4000, 'REVIEW_INCOMPLETE')
    duration = record['observed_duration_s']
    _need(type(duration) in (float, int) and math.isfinite(duration) and 0 < duration <= 60,
          'REVIEW_DURATION_INVALID')
    checks = record['checks']
    _need(isinstance(checks, dict) and set(checks) == set(CHECKS)
          and all(x in ('pass', 'fail', 'not_applicable', 'not_checked') for x in checks.values()),
          'REVIEW_CHECKS_INVALID')
    if record['decision'] == 'retain_candidate':
        _need(all(x in ('pass', 'not_applicable') for x in checks.values())
              and checks['story_action'] == checks['framing'] == checks['timing'] == 'pass',
              'UNRESOLVED_REVIEW_CHECKS')
        if view['audio_mode'] == 'native_dialogue':
            _need(checks['dialogue'] == checks['audio'] == 'pass'
                  and (not view['requires_lip_sync'] or checks['lip_sync'] == 'pass'),
                  'NATIVE_DIALOGUE_REVIEW_REQUIRED')
    # Human declarations, NOT authenticated identity or automatic media analysis.


def record_review(private_dir, record):
    root, _ = _proposal(private_dir)
    view = inspect_job(root)
    _need(view['state'] == 'review_pending', 'REVIEW_REQUIRES_UNREVIEWED_SAVED_MEDIA')
    _check_review(record, view)
    api._atomic_create(root / 'review.json', record)
    return inspect_job(root)


def render_page(packet, view, review=None):
    """Read-only standalone page; escaped text, local video, no JS/network API."""
    api._packet(packet)
    _need(view['request_digest'] == packet['request_digest'], 'PAGE_PROPOSAL_MISMATCH')
    esc = lambda value: html.escape(str(value), quote=True)
    body = packet['body']
    media = ('<video controls preload="metadata" src="video.mp4"></video>'
             if view.get('media_sha256') else '<div class="empty">尚无已保存的视频<br><small>这里不会用占位动画冒充生成结果</small></div>')
    speech = packet['postproduction'].get('speech') or {}
    dialogue = ''.join('<tr><td>'+esc(x.get('speaker_id', ''))+'</td><td>'+esc(x.get('text', ''))+
                       '</td><td>'+esc(str(x.get('from_s'))+'–'+str(x.get('to_s'))+' 秒')+
                       '</td><td>'+esc('画外对白' if x.get('kind') == 'offscreen_dialogue' else
                                      '出镜对白' if x.get('kind') == 'onscreen_dialogue' else '类型待明确')+'</td></tr>'
                       for x in speech.get('dialogue', []))
    reviewed = '<p>还没有审片记录。</p>' if review is None else '<pre>'+esc(json.dumps(review, ensure_ascii=False, indent=2))+'</pre>'
    instructions = {
        'prepared': '下一步：核对本页的画面、台词、模型与费用，再由私人运行入口明确提交一次。',
        'submission_unknown': '下一步：人工核对供应商任务和账单，不能重新提交或换目录重试。',
        'download_ready': '下一步：保存视频，生成链接不是长期素材存储。',
        'review_pending': '下一步：完整观看，逐项检查动作、构图、台词、口型、声音、时长与人物；记录保留、修改或弃用。',
        'revise': '下一步：依据审片意见修订这一镜；当前不会自动重做或扣费。',
    }.get(view['state'], '状态来自本地记录，查看页面不会查询供应商或触发生成。')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; media-src 'self'; base-uri 'none'; form-action 'none'">
<title>单镜制作审阅</title><style>
*{box-sizing:border-box}body{margin:0;background:#10151c;color:#edf0f5;font:16px/1.7 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:32px 22px}header{border-bottom:1px solid #394452;padding-bottom:22px}
h1{font-size:30px;margin:4px 0}h2{font-size:20px}small,.muted{color:#acb9c9}.badge{color:#8ee6cd}
.grid{display:grid;grid-template-columns:minmax(240px,1fr) minmax(0,1.7fr);gap:24px;margin:28px 0}
section{background:#1b2430;padding:24px;border-radius:12px;min-width:0}video,.empty{width:100%;aspect-ratio:9/16;background:#080c11;border-radius:8px}.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.7 system-ui,sans-serif}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px 6px;border-bottom:1px solid #394452;vertical-align:top}.note{border-left:3px solid #8ee6cd;padding:12px 18px;background:#1b2430}summary{cursor:pointer}@media(max-width:700px){.grid{grid-template-columns:1fr}video,.empty{max-height:480px}main{padding:20px 14px}section{padding:18px}}
</style><main><header><div class="badge">AI 导演 · 单镜制作</div><h1>'''+esc(packet['shot_id'])+''' · 请求与审片</h1><div>'''+esc(LABELS[view['state']])+'''</div></header><p class="note">'''+esc(instructions)+'''</p><div class="grid"><section>'''+media+'''</section><section><h2>本镜制作安排</h2><p>'''+esc(packet['provider'])+' · '+esc(body['model'])+'''</p><p>'''+esc(body['duration'])+' 秒 · '+esc(body['ratio'])+' · '+esc(body['resolution'])+' · '+esc('原生对白' if body['generate_audio'] else '静音视频，声音后期制作')+'''</p><p class="muted">'''+esc('无参考图的技术试验，不能证明人物跨镜一致性。' if packet['scope']=='reference_free_technical_probe' else '已传入参考图地址；权利和实际一致性仍需核实。')+'''</p><h2>精确对白</h2><table><tr><th>角色</th><th>台词</th><th>时间</th><th>声画类型</th></tr>'''+dialogue+'''</table><p>旁白：'''+esc((speech.get('voiceover') or {}).get('text') or '无')+'''</p><p class="muted">时间是导演计划，实际视频时长与口型尚需核对。技术候选保留不等于整片或正式制作批准。</p></section></div><section><h2>审片记录</h2>'''+reviewed+'''<p>检查：动作与故事、构图、台词、口型、声音、时长、人物一致性。</p></section><details><summary>查看完整生成指令与后期安排</summary><pre>'''+esc(body['content'][0]['text'])+'\n\n'+esc(json.dumps(packet['postproduction'],ensure_ascii=False,indent=2))+'''</pre></details><footer class="muted"><p>只读页面 · 不含密钥或供应商下载链接 · 不执行生成、重试或发布</p></footer></main></html>'''


def save_page(private_dir):
    root, packet = _proposal(private_dir)
    view = inspect_job(root)
    review = api._read(root / 'review.json') if view['human_review_recorded'] else None
    source = render_page(packet, view, review)
    filename = 'review-' + hashlib.sha256(source.encode()).hexdigest()[:16] + '.html'
    target = root / filename
    # New derived version on content change; never overwrite a human-edited page.
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _need(not target.is_symlink() and target.is_file()
              and target.read_text(encoding='utf-8') == source, 'REVIEW_PAGE_CHANGED')
        return target
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(source); f.flush(); os.fsync(f.fileno())
    api._fsync_folder(root)
    return target


def save_review_template(private_dir):
    root, _ = _proposal(private_dir)
    view = inspect_job(root)
    _need(view['state'] == 'review_pending', 'REVIEW_REQUIRES_UNREVIEWED_SAVED_MEDIA')
    template = dict(request_digest=view['request_digest'], media_sha256=view['media_sha256'],
                    decision='revise', reviewer='', watched_full_clip=False,
                    observed_duration_s=None, checks={x: 'not_checked' for x in CHECKS}, notes='')
    api._atomic_create(root / 'review.draft.json', template)
    return {'review_draft_created': True, 'human_review_recorded': False}


def _key():
    _need(sys.stdin.isatty(), 'PRIVATE_INTERACTIVE_TERMINAL_REQUIRED')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass('API Key（不回显，不保存）：')


def main(argv=None):
    parser = argparse.ArgumentParser(description='单镜制作入口；默认离线，不自动重试或发布')
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help='离线准备一个镜头')
    prepare.add_argument('--base', required=True); prepare.add_argument('--direction', required=True)
    prepare.add_argument('--shot', required=True); prepare.add_argument('--provider', choices=api.PROVIDERS, required=True)
    prepare.add_argument('--audio-mode', choices=('silent_post', 'native_dialogue'), default='silent_post')
    prepare.add_argument('--reference-image', action='append', default=[])
    for name in ('status', 'page', 'submit', 'query', 'download', 'review-template', 'review'):
        sub = commands.add_parser(name)
        if name == 'submit':
            sub.add_argument('--approval', required=True, help='私有审批JSON，绑定准确请求及费用估计')
            sub.add_argument('--execute-reviewed-request', action='store_true', help='操作者明确执行；不是账户认证')
        if name == 'review': sub.add_argument('--record', required=True, help='私有审片JSON，绑定视频哈希')
        sub.add_argument('--job', required=True)
    prepare.add_argument('--job', required=True, help='已存在且为空的0700私有目录')
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            # Source input may be a public fixture; outputs are always private.
            base = json.loads(Path(args.base).read_text(encoding='utf-8'))
            direction = json.loads(Path(args.direction).read_text(encoding='utf-8'))
            result = prepare_job(base, direction, args.shot, private_dir=args.job, provider=args.provider,
                                 audio_mode=args.audio_mode, reference_images=args.reference_image)
        elif args.command == 'status': result = inspect_job(args.job)
        elif args.command == 'page':
            page = save_page(args.job); result = {'review_page_saved': True, 'filename': page.name}
        elif args.command == 'submit':
            _need(args.execute_reviewed_request, 'EXPLICIT_EXECUTION_REQUIRED')
            approval = api._read(Path(args.approval))
            submit_job(args.job, api_key=_key(), approval=approval)
            result = inspect_job(args.job)
        elif args.command == 'query': result = query_job(args.job, api_key=_key())
        elif args.command == 'download': result = download_job(args.job)
        elif args.command == 'review-template': result = save_review_template(args.job)
        else: result = record_review(args.job, api._read(Path(args.record)))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, EOFError, getpass.GetPassWarning):
        # Never print an exception containing source text, a signed URL or a key.
        print('VIDEO_OPERATION_STOPPED: 核对私有文件、操作条件及已有任务；不要重发未知提交。', file=sys.stderr)
        return 2


if __name__ == '__main__': raise SystemExit(main())
