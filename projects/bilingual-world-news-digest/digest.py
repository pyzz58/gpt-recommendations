#!/usr/bin/env python3
"""API-key-free bilingual RSS digest, designed for scheduled GitHub Actions."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import email.message
import html
import json
import logging
import os
import re
import smtplib
import ssl
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import requests

ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger("daily-news")
VOCAB = {
    "全球新闻": [("diplomacy", "外交"), ("sanctions", "制裁"), ("summit", "峰会")],
    "美股与投资": [("earnings", "财报/收益"), ("volatility", "波动性"), ("rally", "上涨行情")],
    "美联储与宏观": [("rate cut", "降息"), ("inflation", "通货膨胀"), ("monetary policy", "货币政策")],
    "创业与商业模式": [("startup", "初创公司"), ("funding round", "融资轮次"), ("revenue", "营收")],
    "AI与科技": [("breakthrough", "突破"), ("inference", "推理"), ("semiconductor", "半导体")],
    "医疗与科学": [("clinical trial", "临床试验"), ("drug discovery", "药物研发"), ("peer review", "同行评议")],
}
PRIORITY = re.compile(
    r"\b(federal reserve|fomc|powell|interest rates?|rate cuts?|"
    r"s&p 500|nasdaq|earnings|treasur(?:y|ies)|"
    r"ipo|seed funding|series [a-f]|artificial intelligence|clinical trial)\b",
    re.I,
)


def clean(value: str, limit: int = 260) -> str:
    value = html.unescape(re.sub(r"<[^>]*>", " ", value or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value[: limit - 1].rstrip() + "…" if len(value) > limit else value


def published_at(entry: dict) -> dt.datetime | None:
    stamp = entry.get("published_parsed") or entry.get("updated_parsed")
    if not stamp:
        return None
    try:
        return dt.datetime(*stamp[:6], tzinfo=dt.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def fetch_one(category: str, feed: dict, now: dt.datetime, hours: int):
    """Return (items, success). A bad feed never aborts the other sources."""
    try:
        response = requests.get(
            feed["url"],
            timeout=15,
            headers={"User-Agent": "BilingualDailyDigest/0.1 (+https://github.com/pyzz58/gpt-recommendations)"},
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if not parsed.entries and parsed.get("bozo"):
            raise ValueError("RSS parser returned no entries")
        cutoff = now - dt.timedelta(hours=hours)
        articles = []
        for entry in parsed.entries:
            stamp = published_at(entry)
            if stamp is None or not cutoff <= stamp <= now + dt.timedelta(minutes=10):
                continue  # Never present an undated or stale item as today's news.
            title = clean(entry.get("title", ""), 230)
            link = str(entry.get("link", ""))
            if not title or not link.startswith(("https://", "http://")):
                continue
            articles.append({
                "category": category,
                "source": feed["name"],
                "title": title,
                "summary": clean(entry.get("summary", entry.get("description", ""))),
                "url": link,
                "date": stamp,
            })
        return articles, True
    except Exception as exc:
        LOG.warning("Feed failed: %s (%s)", feed["name"], exc)
        return [], False


def choose(items: list[dict], limits: dict) -> dict[str, list[dict]]:
    """Category quotas, exact-title/link deduplication, recency and keyword ranking."""
    output: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for category, limit in limits.items():
        candidates = [x for x in items if x["category"] == category]
        candidates.sort(
            key=lambda x: (
                bool(PRIORITY.search(x["title"])),
                x["date"],
            ),
            reverse=True,
        )
        output[category] = []
        for item in candidates:
            key = re.sub(r"\W+", "", item["title"].lower())
            if not key or key in seen or item["url"] in seen:
                continue
            seen.update({key, item["url"]})
            output[category].append(item)
            if len(output[category]) >= limit:
                break
    return output


def ensure_argos_translator():
    """Uses an offline model after first downloading it; no external model API key."""
    import argostranslate.package as package
    import argostranslate.translate as translate

    def installed():
        try:
            return translate.get_translation_from_codes("en", "zh")
        except Exception:
            return None

    translator = installed()
    if translator:
        return translator
    LOG.info("Downloading offline Argos en->zh language model.")
    package.update_package_index()
    candidate = next(
        (x for x in package.get_available_packages()
         if x.from_code == "en" and x.to_code == "zh"),
        None,
    )
    if candidate is None:
        raise RuntimeError("No Argos English-to-Chinese offline model found.")
    package.install_from_path(candidate.download())
    translator = installed()
    if not translator:
        raise RuntimeError("Offline translation installation did not succeed.")
    return translator


def bilingualize(grouped: dict, translator) -> dict:
    result = {}
    for category, articles in grouped.items():
        result[category] = []
        for article in articles:
            translated = dict(article)
            translated["title_zh"] = clean(translator.translate(article["title"]), 250)
            translated["summary_zh"] = (
                clean(translator.translate(article["summary"]), 450)
                if article["summary"] else ""
            )
            result[category].append(translated)
    return result


def render(grouped: dict, now: dt.datetime) -> tuple[str, str]:
    date = now.strftime("%Y-%m-%d")
    total = sum(map(len, grouped.values()))
    parts = [
        '<html><body style="font-family:Arial,sans-serif;max-width:760px;'
        'margin:auto;color:#172235;line-height:1.55">',
        '<h1 style="color:#203b67">全球新闻 · Bilingual Daily Brief</h1>',
        f'<p>{html.escape(date)} · 精选 {total} 条 · 英中对照</p>',
        '<p style="font-size:13px;color:#697483">基于各媒体公开 RSS 标题和摘要，'
        '并非全文翻译或投资建议。英译中为离线机器翻译，请点击原文核实。</p>',
    ]
    plain = [
        f"全球新闻 · Bilingual Daily Brief | {date}",
        f"精选 {total} 条；仅来自 RSS 标题和摘要，并非全文分析或投资建议。",
    ]
    for category, articles in grouped.items():
        parts.append(f'<h2 style="border-bottom:2px solid #edf0f6;padding-bottom:7px">'
                     f'{html.escape(category)} ({len(articles)})</h2>')
        plain.append(f"\n【{category}】({len(articles)})")
        if not articles:
            parts.append('<p style="color:#748094">过去 24 小时未发现符合条件的新内容。</p>')
            plain.append("过去 24 小时没有符合日期筛选的新内容。")
        for a in articles:
            title = html.escape(a["title"])
            zh = html.escape(a["title_zh"])
            excerpt = html.escape(a["summary"])
            excerpt_zh = html.escape(a["summary_zh"])
            source = html.escape(a["source"])
            link = html.escape(a["url"], quote=True)
            when = a["date"].astimezone(now.tzinfo).strftime("%m-%d %H:%M")
            parts.append(
                '<article style="padding:12px 0;border-bottom:1px solid #eef0f3">'
                f'<div style="font-size:12px;color:#697483">{source} · {when}</div>'
                f'<div><a href="{link}" style="color:#1953a3;text-decoration:none">'
                f'<strong>{title}</strong></a></div>'
                f'<div style="font-weight:600;margin:5px 0">{zh}</div>'
                f'<div style="font-size:13px;color:#586477">{excerpt}</div>'
                f'<div style="font-size:13px;margin-top:3px">{excerpt_zh}</div>'
                '</article>'
            )
            plain.append(
                f"{a['title']}\n{a['title_zh']}\n"
                f"{a['summary']}\n{a['summary_zh']}\n"
                f"{a['source']} | {a['url']}"
            )
    parts.append('<h2>English Corner · 今日主题词汇</h2><ul>')
    plain.append("\n【English Corner · 今日主题词汇】")
    for category, terms in VOCAB.items():
        for en, zh in terms[:2]:
            parts.append(f"<li><strong>{html.escape(en)}</strong> — {html.escape(zh)}</li>")
            plain.append(f"{en} — {zh}")
    parts.append('</ul><p style="color:#697483;font-size:12px">'
                 '选题基于发布时间、主题词和栏目配额；不代表新闻重要性的人工判断。'
                 '新闻版权属于原始发布者。</p></body></html>')
    return "\n".join(parts), "\n\n".join(plain)


def send_email(subject: str, html_body: str, text_body: str):
    sender = os.environ.get("SMTP_FROM", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    recipient = os.environ.get("DIGEST_TO", "").strip()
    if not all((sender, password, recipient)):
        raise RuntimeError("Set SMTP_FROM, SMTP_PASSWORD and DIGEST_TO in GitHub Actions secrets.")
    if "\n" in sender + recipient or "\r" in sender + recipient:
        raise ValueError("Newlines in email addresses are forbidden.")
    msg = email.message.EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    server = os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(server, port, timeout=30, context=ssl.create_default_context()) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Write HTML/TXT files; never send.")
    parser.add_argument("--demo", action="store_true", help="Generate example without RSS or translation download.")
    parser.add_argument("--output", default="/tmp/bilingual-news-digest")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = json.loads((ROOT / "feeds.json").read_text(encoding="utf-8"))
    now = dt.datetime.now(ZoneInfo(settings["timezone"]))
    if args.demo:
        grouped = {}
        for category in settings["max_per_category"]:
            grouped[category] = [{
                "category": category, "source": "DEMO ONLY",
                "title": "Example headline for format testing",
                "summary": "This is fictional test data, not current news.",
                "title_zh": "版式测试用的虚构标题",
                "summary_zh": "这是虚构的测试数据，并非真实新闻。",
                "url": "https://example.org/", "date": now,
            }]
    else:
        sources = [
            (category, feed)
            for category, feeds in settings["feeds"].items()
            for feed in feeds
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            jobs = [
                pool.submit(fetch_one, category, feed, now, settings["lookback_hours"])
                for category, feed in sources
            ]
            results = [job.result() for job in jobs]
        successful = sum(success for _, success in results)
        LOG.info("RSS sources: %d/%d fetched successfully", successful, len(sources))
        if successful == 0:
            raise RuntimeError("All RSS sources failed; refusing to send an empty report.")
        grouped = choose(
            [article for group, _ in results for article in group],
            settings["max_per_category"],
        )
        if sum(map(len, grouped.values())) == 0:
            raise RuntimeError("No recent dated RSS items available; refusing an empty report.")
        # Bilingual mode is mandatory: do not silently send English-only results.
        grouped = bilingualize(grouped, ensure_argos_translator())
    html_body, txt_body = render(grouped, now)
    if args.dry_run or args.demo:
        target = Path(args.output)
        target.with_suffix(".html").write_text(html_body, encoding="utf-8")
        target.with_suffix(".txt").write_text(txt_body, encoding="utf-8")
        LOG.info("Preview written: %s.html / %s.txt", target, target)
    else:
        send_email(f"全球新闻双语日报 | {now:%Y-%m-%d}", html_body, txt_body)
        LOG.info("Digest delivered to configured recipient.")


if __name__ == "__main__":
    main()
