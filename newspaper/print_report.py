"""V0.5 editorial report presentation: Chinese analysis first; short bilingual appendix.

This module formats source-limited, rule-based analysis. It is NOT an LLM,
a news fact checker, or a substitute for licensed journalism.
"""
from __future__ import annotations

import datetime as dt
import html
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from adviser import domain_advice, global_linkages

CSS = """
@page {
  size: A5 portrait;
  margin: 17mm 13.5mm 19mm 13.5mm;
  @bottom-left { content: "GLOBAL SITUATION BRIEF"; font-family: "Liberation Sans"; font-size: 6.8pt; color: #777; letter-spacing: 0.8pt; }
  @bottom-right { content: counter(page); font-family: "Liberation Sans"; font-size: 7.5pt; color: #555; }
}
@page:first { @bottom-left { content: ""; } }
html, body { margin:0; padding:0; background:white; }
body { font-family:"Noto Serif CJK SC","Noto Serif CJK","Source Han Serif SC",serif;
       font-size:10.45pt; color:#222326; line-height:1.70;
       -webkit-font-smoothing:antialiased; overflow-wrap:break-word; }
.cover { min-height:143mm; padding-top:23mm; page-break-after:always; }
.kicker { font: 700 8pt "Liberation Sans","Noto Sans CJK SC",sans-serif; letter-spacing:1.5pt; color:#912d36; }
.cover-rule { width:35mm; border-top:1.8pt solid #912d36; margin:7mm 0 13mm; }
.cover-title { margin:0 0 7mm; font:700 30pt/1.28 "Noto Serif CJK SC","Noto Serif CJK",serif; letter-spacing:2px; color:#14161a; }
.cover-subtitle { font: 10pt "Noto Sans CJK SC",sans-serif; color:#50555b; letter-spacing:1px; }
.cover-date { margin-top:20mm; font:10.4pt "Noto Sans CJK SC",sans-serif; color:#323940; }
.cover-note { margin-top:18mm; font-size:8.7pt; line-height:1.8; color:#595d62; border-top:0.6pt solid #ddd; padding-top:3mm; }
h1,h2,h3 { font-family:"Noto Sans CJK SC","Noto Sans CJK",sans-serif; color:#161a20; line-height:1.4; }
h2 { font-size:16pt; margin:11mm 0 5mm; padding-bottom:2mm; border-bottom:0.8pt solid #9e4549; break-after:avoid; }
h3 { font-size:11.8pt; margin:7mm 0 2.5mm; break-after:avoid; }
p { margin:0 0 3.7mm; text-align:justify; orphans:2; widows:2; }
.section-number { color:#98343d; font-family:"Liberation Serif",serif; font-weight:700; margin-right:2mm; }
.deck { font-size:10.4pt; color:#3a3f46; padding:3mm 0 2mm; break-inside:avoid; }
.source { font: 7.7pt/1.5 "Noto Sans CJK SC",sans-serif; color:#696c72; margin:2.5mm 0 4mm; overflow-wrap:anywhere; }
.meta { font-size:8pt; color:#74777d; letter-spacing:.2pt; }
.analysis { margin-top:3mm; }
.analysis p { margin-bottom:3.5mm; }
.note { padding-left:3mm; border-left:1pt solid #9e4549; font-size:8.7pt; color:#51545a; margin:4mm 0 5mm; }
.continuity { font-size:9.7pt; color:#343943; }
.essay { break-inside:auto; }
.folio { margin:4mm 0 7mm; padding-top:2mm; border-top:0.5pt solid #c6c6c8; }
a { color:#5b3033; text-decoration:none; overflow-wrap:anywhere; }
.appendix { page-break-before:always; }
.appendix-intro { color:#6a6768; font-size:9.2pt; }
.bilingual { margin:6mm 0; break-inside:avoid; }
.en { font: 10.1pt/1.55 "Liberation Serif",Georgia,serif; text-align:left; color:#1b2127; margin:0; }
.zh { font: 9.5pt/1.62 "Noto Serif CJK SC",serif; text-align:left; color:#45484d; margin:0; }
.grammar-mark { font-weight:700; text-decoration:underline; text-decoration-color:#982f37; text-underline-offset:2px; }
.grammar-mark sup { text-decoration:none; color:#912d36; font-size:7pt; margin-left:1px; }
.gloss { margin:4mm 0 2mm; padding-left:0; font-size:8.8pt; }
.gloss p { margin:0 0 2mm; }
.smallprint { font-size:8pt; color:#666; }
@media screen {
 body { max-width:720px; margin:0 auto; padding:25px 25px 70px; }
 .cover { min-height:70vh; }
}
"""

def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)

def _date_bj(value: dt.datetime | None) -> str:
    if not isinstance(value, dt.datetime):
        return "发布时间未提供"
    if value.tzinfo is None:
        return "发布时间未核验"
    return value.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%m月%d日 %H:%M（北京）")

def _legible_title(article: dict) -> str:
    return str(article.get("title_zh") or article.get("title") or "未命名报道").strip()

def _source_summary(articles: list[dict]) -> str:
    known = sorted({a.get("source", "").strip() for a in articles if a.get("source")})
    return "、".join(known[:5]) + (" 等来源" if len(known) > 5 else "") if known else "未取得可靠来源"

def _category_explanation(category: str) -> tuple[str, str]:
    """Only conditional mechanisms. Never claim that a market move already occurred."""
    return {
        "全球新闻": (
            "安全与政策事件的经济影响，通常取决于是否改变实际运输、供应链、政府政策或居民活动。媒体关注度上升本身不能证明能源供应已经中断。",
            "后续应核对官方公告、独立现场报道以及运输和商品市场的实际数据。若各方说法冲突，应暂缓作出确定判断。",
        ),
        "美股与投资": (
            "公司新闻需要同时放在盈利、现金流、资本开支和估值环境中理解。单日股价变化不必然代表企业长期价值发生同等变化。",
            "随后应对照监管披露、财报和管理层业绩指引，并区分已经实现的经营业绩与市场的未来预期。",
        ),
        "美联储与宏观": (
            "宏观数据通过通胀预期、债券收益率、资金成本与企业盈利等多条路径影响市场。任何单一经济指标都不足以独立决定利率或股价方向。",
            "值得核查实际公布值、此前预测与修订值，并观察政策部门的正式声明，避免把市场猜测当成已公布决策。",
        ),
        "创业与商业模式": (
            "融资额、用户数量与媒体曝光都不能单独证明商业模式成立。项目能否持续，需要结合付费客户、获客成本、留存与实际单位经济模型判断。",
            "后续重点是独立可核实的收入、客户、经营现金流及具体交易条款；数据缺席时，应保留评价。",
        ),
        "AI与科技": (
            "技术突破需要区分实验室指标、真实生产效率和商业收入。模型性能改进不一定自动转化为客户愿意支付的价值，也不能忽视部署与算力成本。",
            "需要继续核对公开论文、代码与独立复现、实际部署规模，以及企业的资本开支和现金流。",
        ),
        "医疗与科学": (
            "科研结论必须区分观察性关联、前临床验证、随机对照试验与监管批准。研究样本及终点设计不同，证据强度也不同。",
            "下一步应查验研究方法、样本量、主要终点、不良事件、同行评审和监管机构正式意见。",
        ),
    }.get(category, (
        "应将已经发生的事实与可能存在的影响路径分别判断，避免基于标题推断未核实的结果。",
        "继续核对相互独立的来源、时间、数据口径及重要后续信息。",
    ))

def _extract_fact(article: dict) -> str:
    """Source-bound short description, not an invented LLM paraphrase."""
    title = _legible_title(article).rstrip("，,。.")
    if title:
        return f"据{article.get('source', '相关媒体')}报道，{title}。"
    return "本条报道的可核查事实材料不足，暂不作出进一步判断。"

def _pick_appendix(grouped: dict, max_items: int = 12) -> list[tuple[dict, dict, dict | None]]:
    chosen = []
    for category, items in grouped.items():
        for article in items:
            all_pairs = article.get("bilingual_pairs") or []
            grammatical = article.get("grammar_lessons") or []
            # Prefer short complete sentences; quote <= 22 words per source.
            possible = [
                pair for pair in all_pairs
                if 6 <= len(str(pair.get("en", "")).split()) <= 22
                and 15 < len(str(pair.get("en", ""))) <= 210
                and pair.get("zh", "").strip()
            ]
            if not possible:
                continue
            with_rule = next((
                (p, lesson) for p in possible for lesson in grammatical
                if " ".join(p["en"].split()) == " ".join(lesson.get("sentence_en", "").split())
            ), None)
            pair, grammar = with_rule or (possible[0], None)
            chosen.append((article, pair, grammar))
            if len(chosen) >= max_items:
                return chosen
    return chosen

def _grammar_expression(sentence: str, lesson: dict) -> re.Match | None:
    kind = lesson.get("type") or ""
    patterns = {
        "present_perfect": r"\b(?:have|has|had)\b",
        "passive": r"\b(?:is|are|was|were|be|been|being)\b",
        "conditional": r"\b(?:if|unless)\b",
        "relative": r"\b(?:who|which|that)\b",
        "modal": r"\b(?:may|might|could|should|must|would)\b",
        "infinitive": r"\bto\s+[A-Za-z]+\b",
        "past": r"\b[A-Za-z]+ed\b",
    }
    pattern = patterns.get(kind)
    return re.search(pattern, sentence, flags=re.I) if pattern else None

def _highlight_sentence(sentence: str, match: re.Match | None, number: int | None) -> str:
    if not match or not number:
        return esc(sentence)
    return (esc(sentence[:match.start()]) +
            '<span class="grammar-mark">' + esc(sentence[match.start():match.end()]) +
            f"<sup>{number}</sup></span>" + esc(sentence[match.end():]))

def build_editorial_html(grouped: dict, day: dt.date) -> tuple[str, str]:
    """Return print-ready HTML and compact email text. No full article reproduction."""
    count = sum(len(a) for a in grouped.values())
    date_str = day.strftime("%Y年%m月%d日")
    html_parts = [
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>全球形势秘书简报 '+esc(date_str)+'</title>',
        '<style>'+CSS+'</style></head><body>',
        '<section class="cover">',
        '<div class="kicker">GLOBAL SITUATION BRIEF / NEWSPAPER V0.5</div>',
        '<div class="cover-rule"></div>',
        '<h1 class="cover-title">全球形势<br>秘书简报</h1>',
        '<div class="cover-subtitle">国际形势 · 金融市场 · 科技与医学</div>',
        '<div class="cover-date">'+esc(date_str)+'<br>北京时间前一自然日</div>',
        '<p class="cover-note">公开新闻来源自动整理与规则型观察分析。'
        '本文不具备独立新闻调查、交叉事实核验或专业投顾能力。'
        '如来源不足会明确标注；英文学习内容仅在文末附录。</p>',
        '</section>',
        '<section><div class="kicker">EDITOR\'S NOTE</div>',
        '<h2>编者导语</h2>',
        f'<p>本期依据已成功读取的 {count} 篇公开媒体报道编排，'
        '关注国际安全、宏观政策、美国股市、创业、人工智能及医学科研。'
        '选题以报道发布时间与可读来源为界，不能代表全天所有重要事件。</p>',
        '<p>以下为资料支持的局势观察：事件已发生的事实与其潜在影响分别呈现，'
        '分析侧重传导机制、观察指标和不确定性，'
        '不将报道数量、市场猜测或技术宣传直接等同于事实结论。</p>',
        '</section>',
    ]
    printable = [
        f"全球形势秘书简报｜{date_str}", f"本期可读取报道 {count} 篇",
        "规则型观察，不是独立多源事实核验或专业投资建议。",
    ]

    section_number = 0
    for category, articles in grouped.items():
        section_number += 1
        heading = domain_advice(category, articles)["heading"]
        lens, watch = _category_explanation(category)
        html_parts.append(
            '<section class="essay"><h2><span class="section-number">'
            f'{section_number:02d}</span>{esc(heading)}</h2>'
        )
        printable.append(f"\n{heading}")
        if not articles:
            html_parts.append(
                '<p>本期在指定时间窗口内未取得足够可验证且正文可读的该领域报道。'
                '这不代表相关领域没有新事件，因此不做今日趋势判断。</p></section>'
            )
            printable.append("未取得足够的合格新闻资料；不做趋势判断。")
            continue
        sources = _source_summary(articles)
        html_parts.append(
            f'<p class="deck">本节依据 {len(articles)} 篇报道，'
            f'可识别发布来源包括：{esc(sources)}。'
            '以下首先陈述报道中出现的事件，再说明可能的经济、政策或产业传导。</p>'
        )
        for idx, article in enumerate(articles, 1):
            title = _legible_title(article)
            url = str(article.get("url", ""))
            href = esc(url) if urlparse(url).scheme == "https" else ""
            source = str(article.get("source", "未知媒体"))
            stamped = _date_bj(article.get("date"))
            html_parts.append(f'<h3>{idx}. {esc(title)}</h3>')
            html_parts.append('<div class="meta">'+esc(source)+' · '+esc(stamped)+'</div>')
            html_parts.append(f'<div class="analysis"><p>{esc(_extract_fact(article))}</p>')
            html_parts.append(
                '<p>'+esc(lens)+'</p>'
                '<p>'+esc(watch)+'</p>'
                '</div>'
            )
            if href:
                html_parts.append(
                    '<div class="source">查阅来源：<a href="'+href+'">'+esc(source)+'</a>'
                    ' · '+esc(stamped)+'</div>'
                )
            else:
                html_parts.append('<div class="source">来源链接不可验证，略去。</div>')
            printable.extend([title, _extract_fact(article),lens,watch,
                              f"来源：{source} {stamped} {url}"])
        html_parts.append('</section>')

    chains = global_linkages(grouped)
    if chains:
        html_parts.append('<section><h2>跨领域观察</h2>')
        printable.append("\n跨领域观察")
        html_parts.append('<p>下面是一般性的条件传导路径，用于提醒读者关注关联指标，'
                          '不表示每一个环节都已经在当天发生。</p>')
        for item in chains[:4]:
            html_parts.append(
                '<h3>'+esc(item["title"])+'</h3>'
                '<p class="continuity">'+esc(item["caution"])+'</p>'
            )
            printable.extend([item["title"],item["caution"]])
        html_parts.append('</section>')

    choices = _pick_appendix(grouped)
    html_parts.extend([
        '<section class="appendix"><div class="kicker">LANGUAGE NOTES</div>',
        '<h2>英语阅读附录</h2>',
        '<p class="appendix-intro">以下短句来自可读取报道的原文选段；'
        '每句英文紧接对应中文。英语学习是附录，不影响正文阅读。</p>',
    ])
    grammar_notes = []
    for article, pair, grammar in choices:
        original = pair["en"].strip()
        chinese = pair["zh"].strip()
        match = _grammar_expression(original, grammar) if grammar and len(grammar_notes)<3 else None
        number = None
        if match and grammar:
            number = len(grammar_notes) + 1
            grammar_notes.append((number,match.group(0),grammar["explanation"]))
        html_parts.append(
            '<div class="bilingual">'
            '<p class="en">'+_highlight_sentence(original, match, number)+'</p>'
            '<p class="zh">'+esc(chinese)+'</p>'
            '</div>'
        )
        printable.append(original+"\n"+chinese)
    if grammar_notes:
        html_parts.append('<div class="folio"></div><div class="gloss">')
        for no, phrase, explanation in grammar_notes:
            html_parts.append(
                f'<p><strong>{no}. {esc(phrase)}</strong>：{esc(explanation)}</p>'
            )
            printable.append(f"{no}. {phrase}：{explanation}")
        html_parts.append('</div>')
    if not choices:
        html_parts.append(
            '<p class="smallprint">本期无符合选句长度和对应翻译质量要求的英文材料，'
            '不强行生成语言学习内容。</p>'
        )
    html_parts.append(
        '<p class="smallprint">报道原始网页请点击相应章节中的来源链接。'
        '中文解读为有限规则型分析；英文短句为简短来源摘录，'
        '不能将翻译或分析冒充媒体原文。'
        '</p></section></body></html>'
    )
    return "\n".join(html_parts), "\n\n".join(printable)

def write_pdf(html_content: str, destination: str | Path) -> Path:
    """Build an actual searchable PDF; missing fonts / renderer must fail closed."""
    from weasyprint import HTML
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content).write_pdf(str(target))
    if not target.exists() or target.stat().st_size < 4000:
        raise RuntimeError("PDF generation produced an empty or suspiciously small document.")
    if target.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError("Generated file does not have a PDF header.")
    return target

def mail_cover(day: dt.date) -> tuple[str,str]:
    date_str = day.strftime("%Y-%m-%d")
    txt = (
        f"《全球形势秘书简报》 {date_str}\n"
        "新版 A5 排版 PDF 已作为附件发送。请打开 PDF 查看中文形势分析和文末逐句双语学习附录。\n"
        "内容是从公开来源自动整理的规则型观察，不能代替独立核实及专业投资意见。\n"
    )
    body = (
        '<div style="font-family:Arial,sans-serif;line-height:1.8;max-width:580px;color:#242424">'
        '<h2 style="font-family:Georgia,serif;border-bottom:2px solid #963842;padding-bottom:12px">'
        '全球形势秘书简报</h2>'
        '<p><strong>'+esc(date_str)+'</strong></p>'
        '<p>本期 PDF 已附在邮件中。请使用手机 PDF 阅读器打开，'
        '查看中文形势评论及文末的逐句英文/中文附录。</p>'
        '<p style="color:#777;font-size:12px">自动整理与规则型观察；并非独立专家核实。</p>'
        '</div>'
    )
    return body,txt
