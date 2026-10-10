#!/usr/bin/env python3
"""Localhost-only, no-cost source paste interface for Codex work packets.
Not a paid LLM controller. No internet resources or third-party packages.
"""
from __future__ import annotations
from datetime import datetime
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, unquote, urlparse
import webbrowser

from local_director import ROOT, DirectorError, create_prepare

JOBS = ROOT / "jobs"
MAX_BODY = 130_000

BASE_CSS = """body{background:#101721;color:#eaf0fb;font:16px/1.65 system-ui,-apple-system,'PingFang SC',sans-serif;max-width:830px;padding:30px;margin:auto}h1{font-size:27px}textarea,input{box-sizing:border-box;width:100%;padding:12px;border-radius:8px;border:1px solid #516074;background:#222f41;color:#f7fcff;font:inherit}textarea{min-height:350px}button{padding:12px 22px;background:#7abef0;color:#06233c;border:0;border-radius:9px;cursor:pointer;font-weight:700}code,pre{background:#26354a;padding:4px;border-radius:5px}pre{padding:12px;overflow-x:auto}a{color:#93d1ff}.notice{padding:14px;background:#313c4c;border-radius:9px}.alert{background:#473333;padding:14px;border-radius:9px}small{color:#b1c0d1}"""


def page(title, body):
    return ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{BASE_CSS}</style></head><body>{body}</body></html>")


def safe_job(text):
    text = text.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,40}", text):
        raise DirectorError("项目名请使用英文、数字、短横线或下划线（至少2个字符），例如 quit-smoking")
    return text


class App(BaseHTTPRequestHandler):
    def respond(self, body, status=200):
        data=body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url=urlparse(self.path)
        if url.path == "/":
            form="""<h1>AI 导演 v0.3 · 本地文案输入</h1>
            <p class='notice'>所有内容仅保存到本机。这个页面<b>不会调用收费 LLM 或上传 GitHub</b>，先创建 Codex 制作任务。若需API全自动可在终端按 README_V03.md 明确授权。</p>
            <form action='/prepare' method='post'>
             <p><label>项目英文名 <input name='slug' required placeholder='my-video' value='my-video'></label></p>
             <p><label>直接粘贴完整中文文案</label><textarea name='article' required placeholder='把文章粘贴到这里，长文也可以...'></textarea></p>
             <button type='submit'>保存文案并生成 Codex 导演任务</button>
            </form><p><small>本地运行不需要 ChatGPT/GitHub 登录；创意生成仍由已配置的 Codex + DeepSeek 执行。</small></p>"""
            return self.respond(page("本地 AI 导演", form))
        return self.respond(page("找不到", "<p>页面不存在</p><a href='/'>返回</a>"),404)

    def do_POST(self):
        # Reject cross-site forms and DNS rebinding attempts against localhost.
        host = self.headers.get('Host', '')
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        origin = self.headers.get('Origin', '')
        allowed_origins = {'http://' + h for h in allowed}
        if host not in allowed or (origin and origin not in allowed_origins):
            return self.respond(page('访问被拒绝','<p>只允许本机同源网页提交文案。</p>'),403)
        if urlparse(self.path).path != '/prepare':
            return self.respond(page('找不到','请求不存在'),404)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>MAX_BODY:
                raise DirectorError("输入过长或为空，单次不超过约50,000中文字")
            if self.headers.get('Content-Type','').split(';')[0] != 'application/x-www-form-urlencoded':
                raise DirectorError("只接收网页表单")
            fields=parse_qs(self.rfile.read(length).decode('utf-8'),keep_blank_values=True)
            slug=safe_job(fields.get('slug',[''])[0])
            article=fields.get('article',[''])[0].strip()
            if not article or len(article)>45000:
                raise DirectorError("请粘贴 1–45000 字的正文")
            project=JOBS/slug
            if project.exists():
                slug += '-'+datetime.now().strftime('%Y%m%d-%H%M%S')
                project=JOBS/slug
            JOBS.mkdir(parents=True,exist_ok=True)
            temp=JOBS / ('.incoming_'+slug+'.md')
            try:
                temp.write_text(article,encoding='utf-8')
                create_prepare(temp,project)
            finally:
                temp.unlink(missing_ok=True)
            success=(f"<h1>文案已保存在本地</h1><p>项目：<b>{html.escape(slug)}</b></p>"
              "<p class='notice'>还没有自动生成导演镜头。现在请在你的Codex里让它读取以下任务文件，继续使用已经配置好的DeepSeek：</p>"
              f"<pre>{html.escape(str(project/'CODEX_TASK.md'))}</pre>"
              f"<p>制作后运行：<code>python3 local_director.py review --job jobs/{html.escape(slug)}</code></p>"
              f"<p>再双击或打开 <code>jobs/{html.escape(slug)}/index.html</code> 查看分镜。</p>"
              "<p><a href='/'>继续输入另一篇文章</a></p>")
            return self.respond(page('创建成功',success))
        except (DirectorError, UnicodeDecodeError, ValueError, OSError) as exc:
            return self.respond(page('未创建成功',f"<h1>暂时无法保存</h1><p class='alert'>{html.escape(str(exc))}</p><a href='/'>返回修改</a>"),400)


def main(argv=None):
    from argparse import ArgumentParser
    p=ArgumentParser(description='Local-only text paste page; no external access')
    p.add_argument('--port',type=int,default=8765)
    args=p.parse_args(argv)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),App)
    url=f'http://127.0.0.1:{args.port}/'
    print('仅在本机打开：',url, '\n按 Control+C 结束。不会调用任何模型。')
    webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:print('\n已结束。')
    finally:server.server_close()

if __name__=='__main__':raise SystemExit(main())