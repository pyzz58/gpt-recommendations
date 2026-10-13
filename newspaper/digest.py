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
from english_lessons import attach_lessons, english_parser
from adviser import domain_advice, article_advice, global_linkages
from print_report import write_pdf
from clippings import build_clippings_html, mail_cover_clippings
from ai_commentary import email_commentary
from extractive_editor import trim_extracted_article
from translation_editor import polish_translation
from editorial_selection import pick_politics, tech_candidates, political_regions
from newsroom import prepare_pool, select_readable, publisher
from brief_editor import edit_grouped, apply_reports
from edition_budget import EditionBudget
from news_editor import edit_reports_in_batches, write_compact_commentary
from market_snapshot import fetch_market_snapshot

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



BEIJING_TZ = ZoneInfo("Asia/Shanghai")
EDITION_CUTOFF = dt.time(1, 0)
# Reserve three minutes for SMTP delivery; do not initiate late sends.
LATEST_SEND_START = dt.timedelta(minutes=57)


def edition_window(now: dt.datetime) -> tuple[dt.datetime, dt.datetime, dt.date]:
    """Fixed Beijing 01:00-to-01:00 reporting interval, independent of runner delay."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("An aware timestamp is required for the edition window.")
    local = now.astimezone(BEIJING_TZ)
    edition_date = local.date() if local.time() >= EDITION_CUTOFF else local.date() - dt.timedelta(days=1)
    end = dt.datetime.combine(edition_date, EDITION_CUTOFF, tzinfo=BEIJING_TZ)
    start = end - dt.timedelta(hours=24)
    return start, end, edition_date


def require_live_delivery_window(now: dt.datetime, edition_end: dt.datetime) -> None:
    """Fail visibly instead of emailing an obsolete report after 02:00 Beijing."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("An aware timestamp is required for the delivery deadline.")
    local = now.astimezone(BEIJING_TZ)
    if not edition_end <= local < edition_end + LATEST_SEND_START:
        raise RuntimeError(
            "Outside Beijing delivery window (01:00–01:57). "
            "Do not send a stale edition; inspect the scheduled workflow."
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
    """Collect links published in the fixed preceding 24-hour Beijing window."""
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
                    "author": clean(entry.get("author", ""), 150),
                    "source_type": feed.get("source_type", "media"),
                    "source_language": "zh" if feed.get("source_type") == "cn_business_media" or feed.get("source_type") == "cn_state_media" else "en",
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
    if "中国与美国" in limits:
        return prepare_pool(items, per_section=pool_size)
    output = {}
    for category in limits:
        pool = [item for item in items if item["category"] == category]
        if category == "AI与科技":
            pool = tech_candidates(pool)
        ranked = rank_and_pool(pool, pool_size=pool_size, news_start=news_start)
        if category == "全球新闻":
            # Protect China and US headlines from being displaced by other
            # high-scoring world stories before article extraction even starts.
            already = {x["url"] for x in ranked}
            for region in ("中国", "美国"):
                dedicated = rank_and_pool(
                    [a for a in pool if region in political_regions(a)],
                    pool_size=5, news_start=news_start
                )
                for item in dedicated:
                    if item["url"] not in already:
                        ranked.append(item)
                        already.add(item["url"])
        output[category] = ranked
    return output

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
        enriched = {}
        for url, fut in futures.items():
            article = fut.result()
            enriched[url] = article if "中国与美国" in candidates else (trim_extracted_article(article) if article else None)
    if "中国与美国" in candidates:
        return select_readable(candidates, enriched)
    output = {category: [] for category in candidates}
    selected_global = []
    diagnostics = {}
    for category, arr in candidates.items():
        quota = settings["max_per_category"][category]
        source_max = settings.get("source_limit_per_category", 2)
        available = [enriched[item["url"]] for item in arr if enriched[item["url"]]]
        if category == "AI与科技":
            available = tech_candidates(available)
        if category == "全球新闻":
            accepted, pdiag = pick_politics(
                available, quota, selected_global, _duplicate,
                source_max=source_max,
                extra_limit=settings.get("political_major_event_extra", 2),
            )
            if pdiag["political_shortfall"]:
                LOG.warning("Political sourcing shortfall: %s", pdiag["political_shortfall"])
            selected_global.extend(accepted)
            output[category] = accepted
            diagnostics[category] = {
                "quota":quota, "candidate_count":len(arr),
                "readable":len(available),"selected":len(accepted),
                "sources":sorted(set(x["source"] for x in accepted)),
                **pdiag,
            }
            LOG.info("%s: %s", category, diagnostics[category])
            continue
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
    """Strict EN sentence immediately followed by its own ZH translation.

    spaCy locates sentence boundaries; Argos translates the corresponding
    sentence, never a disconnected entire paragraph. Preserves paragraph IDs.
    """
    nlp = english_parser()
    output = {}
    for category, articles in grouped.items():
        output[category] = []
        for article in articles:
            entry = dict(article)
            entry["title_zh"] = clean(translator.translate(article["title"]), 280)
            pairs = []
            qa_flags = []
            for paragraph_id, paragraph in enumerate(article["reading_en"].split("\n\n")):
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                doc = nlp(paragraph)
                sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
                if not sentences:
                    sentences = [paragraph]
                for sentence in sentences:
                    chinese, flags = polish_translation(
                        sentence, translator.translate(sentence)
                    )
                    if flags:
                        qa_flags.append({"paragraph":paragraph_id,"flags":flags})
                    if not chinese:
                        raise RuntimeError("Translation returned blank; refuse misaligned bilingual report.")
                    pairs.append({
                        "en": sentence, "zh": chinese, "paragraph_id": paragraph_id,
                    })
            if not pairs:
                raise RuntimeError("No sentence pairs extracted from article.")
            entry["bilingual_pairs"] = pairs
            entry["translation_qa_flags"] = qa_flags
            # Backward compatibility with non-visual tests/report consumers.
            entry["reading_zh"] = "\n\n".join(
                " ".join(p["zh"] for p in pairs if p["paragraph_id"] == pid)
                for pid in sorted(set(p["paragraph_id"] for p in pairs))
            )
            output[category].append(entry)
    return output

def render(grouped: dict, now: dt.datetime, news_day: dt.date, diagnostics: dict) -> tuple[str, str]:
    """Research-adviser report, not a top-five news roundup.

    All original English sentences are directly followed by their Chinese
    translations. Advice is rule-based, evidence-limited, explicitly labelled.
    """
    day = news_day.isoformat()
    total = sum(len(articles) for articles in grouped.values())
    parts = [
        '<html><body style="font-family:Arial,sans-serif;max-width:800px;'
        'margin:auto;color:#172235;line-height:1.65">',
        '<h1>全球形势顾问报告 · Global Situation Adviser</h1>',
        f'<p>{html.escape(day)} 北京时间昨日观察 · {total} 篇证据材料</p>',
        '<p style="color:#687589;font-size:13px">本报告先按领域梳理可核实事实，'
        '再给出分析框架、后续观察指标与不确定性。现阶段分析为规则生成，'
        '不是大模型独立调查，也不是事实核验或投资建议；'
        '报道正文是公开可读取的连续选段，不能替代完整授权原文。</p>',
    ]
    plain = [
        f"全球形势顾问报告 | {day}",
        f"已采集可读材料：{total} 篇；顾问分析为可解释的规则框架，尚非大模型研究结论。",
    ]
    def p(text: str):
        return html.escape(str(text))

    for category, articles in grouped.items():
        advice = domain_advice(category, articles)
        parts.append(
            f'<h2 style="margin-top:30px;border-bottom:2px solid #e3e9f3">'
            f'{p(advice["heading"])}</h2>'
            f'<p><strong>本领域形势：</strong>{p(advice["situation"])}</p>'
            f'<p><strong>分析视角：</strong>{p(advice["analytical_lens"])}</p>'
            f'<p><strong>接下来关注：</strong>{p(advice["what_to_watch"])}</p>'
        )
        plain.extend([
            f"\n【{advice['heading']}】",
            f"本领域形势：{advice['situation']}",
            f"分析视角：{advice['analytical_lens']}",
            f"接下来关注：{advice['what_to_watch']}",
        ])
        if not articles:
            parts.append('<p>昨天未采到满足正文质量与日期要求的材料，'
                         '因此不表示该领域无事发生。</p>')
            continue
        for idx, a in enumerate(articles, 1):
            title = p(a["title"])
            zh_title = p(a["title_zh"])
            source = p(a.get("source", ""))
            time = a["date"].astimezone(now.tzinfo).strftime("%Y-%m-%d %H:%M")
            url = p(a.get("url", ""))
            parts.append(
                f'<section style="margin:24px 0;padding-top:12px;border-top:1px solid #dfe5ed">'
                f'<h3 style="margin-bottom:6px">{idx}. {zh_title}</h3>'
                f'<div style="color:#64748b;font-size:13px">{source} · {time} 北京时间</div>'
                '<div style="margin-top:12px;padding:10px 13px;background:#f3f6fb;border-radius:6px">'
                '<strong>英文标题 · English title</strong>'
                f'<p style="margin:4px 0">{title}</p>'
                f'<p style="margin:4px 0;color:#1d4b73">{zh_title}</p></div>'
                '<h4 style="margin-top:16px">事实材料 · 英文一行 / 中文下一行</h4>'
            )
            plain.extend([
                f"\n{idx}. {a['title']}",a["title_zh"],
                f"{a.get('source','')} | {time} 北京时间",
                "【事实材料：英文一行、中文下一行、逐句对应】",
            ])
            pairs = a.get("bilingual_pairs", [])
            if not pairs:
                # Compatibility with old fixtures/manual imports, never
                # pretend a full paragraph is already sentence aligned.
                pairs = [{"en": a.get("reading_en", ""), "zh": a.get("reading_zh", ""),
                          "paragraph_id": 0}]
            bilingual_lines = []
            for pair in pairs:
                parts.append(
                    '<div style="margin:0;padding:0;line-height:1.55">'
                    f'<div style="margin:0;color:#283547">{p(pair["en"])}</div>'
                    f'<div style="margin:0;color:#215582">{p(pair["zh"])}</div>'
                    '</div>'
                )
                # One English line, one Chinese line, next English line, etc.
                # The whole block is ONE plaintext section; joining global
                # sections must not create blank lines between sentence pairs.
                bilingual_lines.extend([pair["en"], pair["zh"]])
            plain.append("\n".join(bilingual_lines))
            evaluation = article_advice(a)
            parts.append(
                '<div style="margin:16px 0;padding:12px;background:#f7f8fa;border-radius:6px">'
                '<h4>顾问观察 · Analysis</h4>'
                f'<p><strong>为什么需要关注：</strong>{p(evaluation["assessment"])}</p>'
                f'<p><strong>接下来看什么：</strong>{p(evaluation["watch"])}</p>'
                f'<p><strong>证据限制：</strong>{p(evaluation["uncertainty"])}</p>'
                f'<p><a href="{url}">核对来源 · Original reporting</a></p>'
                '</div>'
            )
            plain.extend([
                "【顾问观察（规则推导，不代表确认的未来事实）】",
                f"为什么关注：{evaluation['assessment']}",
                f"接下来看什么：{evaluation['watch']}",
                f"证据限制：{evaluation['uncertainty']}",
                f"来源：{a.get('url','')}",
            ])
            lessons = a.get("grammar_lessons", [])
            if lessons:
                parts.append('<div style="padding:12px;background:#eef4fb;border-radius:6px">'
                             '<h4>Grammar Focus · 本篇语法</h4>')
                plain.append("【本篇语法】")
                for lesson in lessons:
                    parts.append(
                        f'<p><strong>{p(lesson["title"])}</strong></p>'
                        f'<p style="margin:3px 0">{p(lesson["sentence_en"])}</p>'
                        f'<p style="margin:3px 0;color:#215582">{p(lesson["sentence_zh"])}</p>'
                        f'<p style="font-size:13px">结构：{p(lesson["pattern"])}；'
                        f'用法：{p(lesson["explanation"])}</p>'
                    )
                    plain.extend([
                        lesson["title"], lesson["sentence_en"], lesson["sentence_zh"],
                        f"结构：{lesson['pattern']}",
                        f"用法：{lesson['explanation']}",
                    ])
                parts.append('</div>')
            parts.append('</section>')
    links = global_linkages(grouped)
    if links:
        parts.append('<h2>跨领域联动研判 · Connections to Watch</h2>')
        plain.append("\n【跨领域联动研判】")
        for link in links:
            parts.append(f'<p><strong>{p(link["title"])}</strong></p>'
                         f'<p>{p(link["caution"])}</p>')
            plain.extend([link["title"], link["caution"]])
    parts.append(
        '<p style="font-size:12px;color:#687589">请注意：'
        '本版不做原创大模型深度调查，模板只提供分析框架；'
        '未授权的受版权保护报道不得作为完整原文对外公开转载。'
        '不确定事实会保持不确定。</p></body></html>'
    )
    return "\n".join(parts), "\n\n".join(plain)

def send_email(subject: str, html_body: str, text_body: str, pdf_attachment: Path | None = None):
    sender = os.environ.get("SMTP_FROM", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    recipient = os.environ.get("NEWSPAPER_TO", "").strip()
    if not all((sender, password, recipient)):
        raise RuntimeError("Set SMTP_FROM, SMTP_PASSWORD and NEWSPAPER_TO in GitHub Actions secrets.")
    if "\n" in sender + recipient or "\r" in sender + recipient:
        raise ValueError("Newlines in email addresses are forbidden.")
    if pdf_attachment is not None:
        pdf_attachment = Path(pdf_attachment)
        if not pdf_attachment.is_file() or pdf_attachment.read_bytes()[:5] != b"%PDF-":
            raise RuntimeError("Do not send: required PDF attachment missing or invalid.")
    msg = email.message.EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    if pdf_attachment is not None:
        msg.add_attachment(
            pdf_attachment.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=pdf_attachment.name,
        )
    server = os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(server, port, timeout=30, context=ssl.create_default_context()) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

def quality_sample_window(now: dt.datetime) -> tuple[dt.datetime, dt.datetime, dt.date]:
    """Ad hoc sample: the exact preceding 24 hours, not a scheduled edition."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware timestamp required for quality sample")
    end = now.astimezone(BEIJING_TZ)
    return end - dt.timedelta(hours=24), end, end.date()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Write preview files; do not send.")
    parser.add_argument("--quality-sample", action="store_true", help="Send one explicitly-requested real-news quality sample; never consume daily receipt.")
    parser.add_argument("--demo", action="store_true", help="Offline layout demo; not live news.")
    parser.add_argument("--output", default="/tmp/newspaper-preview")
    args = parser.parse_args()
    if args.quality_sample and (args.dry_run or args.demo):
        parser.error("--quality-sample cannot be combined with --dry-run or --demo")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = json.loads((ROOT / "feeds.json").read_text(encoding="utf-8"))
    now = dt.datetime.now(BEIJING_TZ)
    start, end, news_day = quality_sample_window(now) if args.quality_sample else edition_window(now)
    if not (args.dry_run or args.demo or args.quality_sample):
        require_live_delivery_window(now, end)
    LOG.info("News reporting window (Beijing): %s inclusive to %s exclusive", start.isoformat(), end.isoformat())
    diagnostics = {}
    edited_commentary = None
    editorial_audit = {"edited": 0, "total": 0, "fallback": 0}
    edition_cost = None
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
                "bilingual_pairs": [{
                    "en": "This is a fictional example.",
                    "zh": "这是一个虚构的例子。",
                    "paragraph_id": 0,
                }],
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
            if not feed.get("disabled", False)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            rss_futures = [
                pool.submit(fetch_one, category, feed, start, end)
                for category, feed in sources
            ]
            collected = [job.result() for job in rss_futures]
        successful = sum(ok for _, ok in collected)
        incoming = [item for articles, _ in collected for item in articles]
        unique_publishers = {publisher(a) for a in incoming}
        active_feeds_with_new_material = sum(bool(items) for items, _ in collected)
        LOG.info(
            "RSS source health: reachable=%d/%d enabled feeds, "
            "recent_24h_nonempty=%d, stories=%d, distinct_publisher_families=%d",
            successful, len(sources), active_feeds_with_new_material,
            len(incoming), len(unique_publishers))
        if successful == 0:
            raise RuntimeError("No RSS feeds reachable; aborting rather than sending fake news.")
        if not incoming:
            raise RuntimeError("No verified in-window RSS items; do not fake a daily report.")
        pool = choose_candidates(
            incoming,
            settings["max_per_category"],
            settings["candidate_pool_per_category"],
            news_start=start,
        )
        readable, diagnostics = build_readings(pool, settings)
        if sum(len(x) for x in readable.values()) == 0:
            raise RuntimeError("No articles successfully extracted; aborting the email.")
        # The model edits at most two sourced articles per request.
        # All billable requests, including commentary, share one <=1 CNY ledger.
        # Preview uses no API. A failed article falls back individually with
        # explicit degraded-quality counts; other articles remain eligible.
        ai_key = os.environ.get("NEWSPAPER_LLM_API_KEY", "")
        editorial_audit["total"] = sum(len(items) for items in readable.values())
        if not args.dry_run and ai_key:
            ledger = EditionBudget()
            def before_editorial_request():
                if not args.quality_sample:
                    require_live_delivery_window(dt.datetime.now(BEIJING_TZ), end)
            plans, failed_batches = edit_reports_in_batches(
                readable, ai_key, ledger,
                before_request=before_editorial_request)
            readable = apply_reports(readable, plans)
            editorial_audit["edited"] = sum(
                a.get("editing_mode") == "evidence_mapped_edited_report"
                for articles in readable.values() for a in articles)
            editorial_audit["fallback"] = (
                editorial_audit["total"] - editorial_audit["edited"])
            editorial_audit["failed_batches"] = failed_batches
            try:
                # Independent strategic commentary is shorter and cheaper than
                # source-grounded full-length article editing.
                edited_commentary = write_compact_commentary(
                    readable, news_day, ai_key, ledger,
                    before_request=before_editorial_request)
            except Exception as exc:
                LOG.warning("Independent strategic commentary unavailable: %s",
                            type(exc).__name__)
            edition_cost = ledger.snapshot()
            LOG.info(
                "Edition editorial audit: validated=%d/%d, fallback=%d, "
                "api_calls=%d, conservative_peak_RMB=%s (cap 1.00)",
                editorial_audit["edited"], editorial_audit["total"],
                editorial_audit["fallback"], edition_cost["request_count"],
                edition_cost["estimated_peak_cost_rmb"])
        else:
            readable = edit_grouped(readable)
            editorial_audit["fallback"] = editorial_audit["total"]
        translator = ensure_argos_translator()
        grouped = attach_lessons(
            bilingualize(readable, translator),
            translator,
            grammar_limit=settings.get("grammar_examples_per_article", 3),
            vocab_limit=0,
        )
    # Print evidence-mapped edited reports; keep commentary outside news copy.
    market_data = None
    if not args.demo:
        market_data = fetch_market_snapshot()
        LOG.info("FRED market dashboard: verified=%d missing=%d",
                 len(market_data["values"]), len(market_data["missing"]))
    html_body, text_body = build_clippings_html(grouped, news_day, market_snapshot=market_data)
    if args.quality_sample:
        # Label the PDF prominently: sample is not the scheduled daily edition.
        html_body = html_body.replace(
            "全球新闻<br>选编</h1>", "全球新闻<br>质量测试样刊</h1>", 1)
    if args.dry_run or args.demo:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.with_suffix(".html").write_text(html_body, encoding="utf-8")
        target.with_suffix(".txt").write_text(text_body, encoding="utf-8")
        pdf_path = write_pdf(html_body, target.with_suffix(".pdf"))
        LOG.info("Clippings PDF preview generated (no email): %s / .html / .txt", pdf_path)
    else:
        pdf_path = write_pdf(
            html_body, Path("/tmp") / f"global-briefing-{news_day.isoformat()}.pdf"
        )
        cover_html, cover_txt = mail_cover_clippings(news_day, grouped)
        if edited_commentary:
            cover_html, cover_txt = email_commentary(
                news_day, edited_commentary,
                sum(len(entries) for entries in grouped.values()))
        if editorial_audit["total"] and editorial_audit["fallback"]:
            note = (
                "编辑质量提示：本期%d篇采用来源可追溯的AI完整编辑报道，"
                "%d篇因证据校验或预算约束退回原文完整段落选编；"
                "未将降级稿冒充为精编稿。"
                % (editorial_audit["edited"], editorial_audit["fallback"])
            )
            cover_html += "<p style='font-size:12px;color:#666'>" + html.escape(note) + "</p>"
            cover_txt += "\n" + note
        if edition_cost:
            LOG.info("Whole-issue DeepSeek budget accounting: %s",
                     json.dumps(edition_cost, ensure_ascii=False))
        if args.quality_sample:
            window = (f"北京时间 {start:%Y-%m-%d %H:%M} 至 {end:%Y-%m-%d %H:%M}")
            note = ("【新版质量测试样刊｜非正式日报】\\n"
                    "此邮件为用户明确要求的即时样刊，不占用凌晨01:00正式日报的发送记录。\\n"
                    f"取材窗口：{window}。内容来自真实采集源，未经人工逐条复核。")
            cover_html = (
                '<div style="border:1px solid #9b353b;padding:12px;color:#611d22">'
                + html.escape(note).replace("\\n", "<br>")
                + "</div>" + cover_html
            )
            cover_txt = note + "\\n\\n" + cover_txt
            subject = f"【质量测试·非正式日报】全球新闻选编｜{news_day}"
        else:
            require_live_delivery_window(dt.datetime.now(BEIJING_TZ), end)
            subject = f"全球新闻选编｜{news_day} 01:00截稿"
        send_email(subject, cover_html, cover_txt, pdf_attachment=pdf_path)
        LOG.info("PDF report handed to SMTP server: %s (%d bytes)", pdf_path.name, pdf_path.stat().st_size)

if __name__ == "__main__":
    main()
