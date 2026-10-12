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
from reader import fetch_reading
from ranking import rank_and_pool
from english_lessons import attach_lessons

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


def fetch_one(category: str, feed: dict, start: dt.datetime, end: dt.datetime):
    """Collect links published during the previous Beijing calendar day."""
    try:
        response = requests.get(
            feed["url"],
            timeout=18,
            headers={"User-Agent": "BilingualPersonalNewspaper/0.2"},
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if not parsed.entries and parsed.get("bozo"):
            raise ValueError("RSS parsing failed")
        articles = []
        for entry in parsed.entries:
            stamp = published_at(entry)
            # Refuse unverifiable dates: never present stale articles as yesterday's news.
            if stamp is None or not start <= stamp.astimezone(start.tzinfo) < end:
                continue
            title = clean(entry.get("title", ""), 230)
            link = str(entry.get("link", ""))
            if title and link.startswith(("https://", "http://")):
                articles.append({
                    "category": category, "source": feed["name"],
                    "title": title, "summary": clean(entry.get("summary", "")),
                    "url": link, "date": stamp,
                })
        return articles, True
    except Exception as exc:
        LOG.warning("RSS feed unavailable: %s - %s", feed["name"], exc)
        return [], False


def _title_tokens(title: str) -> set[str]:
    stop = {"the", "that", "with", "about", "from", "says",
            "this", "after", "into", "over", "have", "their"}
    return {t for t in re.findall(r"[a-z0-9]+", title.lower())
            if len(t) > 2 and t not in stop}


def _duplicate(item: dict, selected: list[dict]) -> bool:
    this = _title_tokens(item["title"])
    for other in selected:
        if item["url"] == other["url"]:
            return True
        that = _title_tokens(other["title"])
        if len(this) >= 5 and len(that) >= 5:
            similarity = len(this & that) / max(1, len(this | that))
            if similarity >= 0.72:
                return True
    return False


def choose_candidates(
    items: list[dict], limits: dict, pool_size: int,
    news_start: dt.datetime | None = None,
) -> dict:
    """Prefer valuable, distinct events and keep readable outlet fallbacks."""
    return {
        category: rank_and_pool(
            [item for item in items if item["category"] == category],
            pool_size=pool_size,
            news_start=news_start,
        )
        for category in limits
    }

def build_readings(candidates: dict, settings: dict) -> tuple[dict, dict]:
    """
    Extract accessible original articles and fill topic quotas from backup sources.
    Skip inaccessible/short/paywalled bodies instead of faking detailed coverage.
    """
    all_candidates = [item for category in candidates for item in candidates[category]]
    unique = {}
    for item in all_candidates:
        unique.setdefault(item["url"], item)
    LOG.info("Reading candidate article pages: %d", len(unique))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = {
            url: pool.submit(
                fetch_reading, article, settings["longread_min_chars"],
                settings["longread_max_chars"],
            )
            for url, article in unique.items()
        }
        enriched = {url: fut.result() for url, fut in futures.items()}
    output = {category: [] for category in candidates}
    selected_global = []
    diagnostics = {}
    for category, arr in candidates.items():
        quota = settings["max_per_category"][category]
        source_max = settings.get("source_limit_per_category", 2)
        available = [enriched[item["url"]] for item in arr if enriched[item["url"]]]
        accepted = []
        counts = {}
        # First pass prioritizes unique outlets. Second pass fills gaps.
        for diversify in (True, False):
            for item in available:
                if len(accepted) >= quota:
                    break
                if item in accepted or _duplicate(item, selected_global + accepted):
                    continue
                if any(
                    old.get("category") == item.get("category")
                    and old.get("story_id") == item.get("story_id")
                    for old in accepted
                ):
                    continue
                if diversify and counts.get(item["source"], 0) >= source_max:
                    continue
                accepted.append(item)
                counts[item["source"]] = counts.get(item["source"], 0) + 1
        selected_global.extend(accepted)
        output[category] = accepted
        diagnostics[category] = {
            "quota": quota, "candidate_count": len(arr),
            "readable": len(available), "selected": len(accepted),
            "sources": sorted(set(x["source"] for x in accepted)),
        }
        LOG.info("%s: %s", category, diagnostics[category])
    return output, diagnostics


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
    """Translate the extracted article reading edition, not merely RSS blurbs."""
    result = {}
    for category, articles in grouped.items():
        result[category] = []
        for article in articles:
            translated = dict(article)
            translated["title_zh"] = clean(translator.translate(article["title"]), 280)
            # Offline translation may collapse lines. Translate each paragraph individually.
            blocks = [
                para for para in article["reading_en"].split("\n\n")
                if para.strip()
            ]
            translated["reading_zh"] = "\n\n".join(
                translator.translate(block) for block in blocks
            )
            result[category].append(translated)
    return result


def render(grouped: dict, now: dt.datetime, news_day: dt.date, diagnostics: dict) -> tuple[str, str]:
    day = news_day.isoformat()
    total = sum(map(len, grouped.values()))
    parts = [
        '<html><body style="font-family:Arial,sans-serif;max-width:800px;'
        'margin:auto;color:#172235;line-height:1.7">',
        '<h1 style="color:#203b67">全球新闻 · Newspaper</h1>',
        f'<p><strong>{html.escape(day)} 北京时间前一日新闻</strong> · '
        f'{total} 篇中英对照报道 · 每日 07:00 定时投递</p>',
        '<p style="font-size:13px;color:#657187">正文由公开可读取新闻页面提取并截选，'
        '译文由离线翻译生成；并非付费文章全文、也非 AI 事实核查。'
        '原文可能更长；推荐分数由关键词、主题匹配、不同媒体覆盖度、'
        '新动作或数据线索和时效性计算，不能代表事实已核验。</p>',
    ]
    plain = [f"全球新闻 Newspaper | {day}", f"北京时间前一日新闻 · {total} 篇双语深度阅读选段"]
    # Editorial front page: high-scoring articles, no duplicates or fabricated headlines.
    all_articles = [
        article for articles in grouped.values() for article in articles
    ]
    top_articles = sorted(
        all_articles, key=lambda a: a.get("importance_score", 0), reverse=True,
    )[:5]
    if top_articles:
        parts.append('<h2>今日重点 · Editor Picks</h2><ol>')
        plain.append("\n【今日重点 / Editor Picks】")
        for article in top_articles:
            label = html.escape(article.get("title_zh") or article["title"])
            score = int(article.get("importance_score", 0))
            parts.append(
                f'<li>{label} <span style="color:#687489">'
                f'（推荐参考分 {score}/100）</span></li>'
            )
            plain.append(f"{label} · 推荐参考分 {score}/100")
        parts.append('</ol><p style="font-size:12px;color:#687489">'
                     '推荐分数是可解释的程序启发式结果，不代表投资建议或事实核查。</p>')
    for category, articles in grouped.items():
        parts.append(
            f'<h2 style="border-bottom:2px solid #edf0f6;padding-bottom:7px">'
            f'{html.escape(category)} ({len(articles)})</h2>'
        )
        plain.append(f"\n【{category}】({len(articles)})")
        if not articles:
            parts.append('<p style="color:#748094">当天没有可读取且符合日期要求的报道；已尝试候补新闻源。</p>')
            plain.append("当天没有可读取的有效报道；已尝试候补来源。")
        for a in articles:
            title = html.escape(a["title"])
            zh = html.escape(a["title_zh"])
            body = html.escape(a["reading_en"]).replace("\n\n", "</p><p>")
            body_zh = html.escape(a["reading_zh"]).replace("\n\n", "</p><p>")
            source = html.escape(a["source"])
            url = html.escape(a["url"], quote=True)
            when = a["date"].astimezone(now.tzinfo).strftime("%Y-%m-%d %H:%M")
            omitted = "（精选选段，非全文）" if a["reading_abbreviated"] else "（可提取正文）"
            score = int(a.get("importance_score", 0))
            why = html.escape(a.get("why_recommended", "未生成评分依据"))
            parts.append(
                '<div style="font-size:12px;color:#506682">'
                f'推荐参考分 {score}/100 · {why}</div>'
            )
            parts.append(
                '<article style="padding:16px 0;border-bottom:1px solid #e2e6ed">'
                f'<div style="font-size:12px;color:#687489">{source} · {when} 北京时间 · '
                f'{omitted}</div><h3>{title}</h3>'
                f'<p style="font-weight:600">{zh}</p>'
                '<div style="background:#f5f7fa;border-radius:6px;padding:8px 12px">'
                f'<p>{body_zh}</p></div>'
                '<p style="font-size:12px;color:#657187">English reading · 英文阅读</p>'
                f'<div style="font-size:14px;color:#37485e"><p>{body}</p></div>'
                f'<p><a href="{url}">原始来源 · Original source</a></p>'
                '</article>'
            )
            # Attach vocabulary and actual grammatical examples immediately below
            # THIS article rather than a generic topic list at the end of the email.
            vocab = a.get("vocabulary", [])
            lessons = a.get("grammar_lessons", [])
            if vocab or lessons:
                parts.append('<section style="margin:10px 0 20px;padding:10px 14px;'
                             'background:#eef4fb;border-radius:6px">'
                             '<h4>English Learning · 本篇英语学习</h4>')
                plain.append("\n【本篇英语学习】")
            if vocab:
                parts.append('<p><strong>Vocabulary · 词汇</strong></p><ul>')
                for word in vocab:
                    parts.append(
                        f'<li><strong>{html.escape(word["word"])}</strong>：'
                        f'{html.escape(word["definition"])}</li>'
                    )
                    plain.append(f'{word["word"]} — {word["definition"]}')
                parts.append('</ul>')
            if lessons:
                parts.append('<p><strong>Grammar Focus · 本篇语法</strong></p>')
                for lesson in lessons:
                    label = html.escape(lesson["title"])
                    quote = html.escape(lesson["sentence_en"])
                    cn = html.escape(lesson["sentence_zh"])
                    pattern = html.escape(lesson["pattern"])
                    note = html.escape(lesson["explanation"])
                    parts.append(
                        f'<div style="margin-bottom:12px"><strong>{label}</strong>'
                        f'<p style="margin:4px 0"><em>{quote}</em></p>'
                        f'<p style="margin:4px 0">{cn}</p>'
                        f'<p style="margin:4px 0">结构：{pattern}</p>'
                        f'<p style="margin:4px 0">用法：{note}</p></div>'
                    )
                    plain.append(
                        f'\n{lesson["title"]}\n原文例句：{lesson["sentence_en"]}'
                        f'\n中文：{lesson["sentence_zh"]}'
                        f'\n结构：{lesson["pattern"]}\n用法：{lesson["explanation"]}'
                    )
            if vocab or lessons:
                parts.append('</section>')
            plain.append(
                f"推荐参考分 {a.get('importance_score', 0)}/100 · {a.get('why_recommended', '')}\n"
                f"{a['title']}\n{a['title_zh']}\n"
                f"【中文阅读】\n{a['reading_zh']}\n"
                f"【English reading】\n{a['reading_en']}\n"
                f"{a['source']} | {a['url']}"
            )
    parts.append(
        '<p style="font-size:12px;color:#687489">'
        '未绕过付费墙或登录限制；未能取得正文的新闻会改用可访问报道。'
        '自动采集需尊重各来源使用条款，个人阅读不代表可公开转载。</p></body></html>'
    )
    return "\n".join(parts), "\n\n".join(plain)


def send_email(subject: str, html_body: str, text_body: str):
    sender = os.environ.get("SMTP_FROM", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    recipient = os.environ.get("NEWSPAPER_TO", "").strip()
    if not all((sender, password, recipient)):
        raise RuntimeError("Set SMTP_FROM, SMTP_PASSWORD and NEWSPAPER_TO in GitHub Actions secrets.")
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
    parser.add_argument("--dry-run", action="store_true", help="Write preview files; do not send.")
    parser.add_argument("--demo", action="store_true", help="Offline layout demo; not live news.")
    parser.add_argument("--output", default="/tmp/newspaper-preview")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = json.loads((ROOT / "feeds.json").read_text(encoding="utf-8"))
    now = dt.datetime.now(ZoneInfo("Asia/Shanghai"))
    news_day = (now - dt.timedelta(days=1)).date()
    start = dt.datetime.combine(news_day, dt.time.min, tzinfo=now.tzinfo)
    end = start + dt.timedelta(days=1)
    diagnostics = {}
    if args.demo:
        grouped = {}
        for category in settings["max_per_category"]:
            grouped[category] = [{
                "category": category, "source": "DEMO ONLY",
                "title": "Fictional news headline, format test only",
                "title_zh": "仅为排版测试的虚构新闻标题",
                "reading_en": "This is a fictional example article. " * 20,
                "reading_zh": "这是虚构测试内容。 " * 20,
                "reading_abbreviated": True,
                "importance_score": 78,
                "why_recommended": "仅供版式测试的虚构评分依据",
                "vocabulary": [{"word": "example", "definition": "例子"}],
                "grammar_lessons": [{
                    "title": "一般过去时 · Simple Past",
                    "sentence_en": "The group reported the results yesterday.",
                    "sentence_zh": "该团队昨天报告了结果。",
                    "pattern": "动词过去式",
                    "explanation": "用于叙述过去发生的事件。",
                }],
                "url": "https://example.org/", "date": now,
            }]
    else:
        sources = [
            (category, feed)
            for category, feeds in settings["feeds"].items() for feed in feeds
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            rss_futures = [
                pool.submit(fetch_one, category, feed, start, end)
                for category, feed in sources
            ]
            collected = [job.result() for job in rss_futures]
        successful = sum(ok for _, ok in collected)
        LOG.info("RSS sources: %d/%d reachable", successful, len(sources))
        if successful == 0:
            raise RuntimeError("No RSS feeds reachable; aborting rather than sending fake news.")
        pool = choose_candidates(
            [item for articles, _ in collected for item in articles],
            settings["max_per_category"],
            settings["candidate_pool_per_category"],
            news_start=start,
        )
        readable, diagnostics = build_readings(pool, settings)
        if sum(len(x) for x in readable.values()) == 0:
            raise RuntimeError("No articles successfully extracted; aborting the email.")
        translator = ensure_argos_translator()
        grouped = attach_lessons(
            bilingualize(readable, translator),
            translator,
            grammar_limit=settings.get("grammar_examples_per_article", 3),
            vocab_limit=settings.get("vocabulary_per_article", 5),
        )
    html_body, text_body = render(grouped, now, news_day, diagnostics)
    if args.dry_run or args.demo:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.with_suffix(".html").write_text(html_body, encoding="utf-8")
        target.with_suffix(".txt").write_text(text_body, encoding="utf-8")
        LOG.info("Preview files saved (not emailed): %s.html and .txt", target, target)
    else:
        send_email(f"Newspaper 全球新闻双语日报｜{news_day}", html_body, text_body)
        LOG.info("Email handed to SMTP server.")


if __name__ == "__main__":
    main()
