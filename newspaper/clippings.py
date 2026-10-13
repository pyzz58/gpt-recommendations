"""Newspaper personal reading edition: extracted journalist prose and line-by-line ZH.

Evidence-mapped editorial rewrites are explicitly labelled; they are not
journalist originals. The original URL remains internal metadata only. Access only
public readable pages (no paywall bypass).
"""
from __future__ import annotations
import datetime as dt
from print_report import CSS, _date_bj, _grammar_expression, _highlight_sentence, esc

READER_CSS = """
h2 { margin-top:9mm; border-bottom:0.7pt solid #933f46; }
.article { margin-bottom:9mm; }
h3 { font-size:13pt; line-height:1.44; margin:6mm 0 1.5mm; break-after:avoid; }
.source-meta { font:8.2pt/1.5 "Noto Sans CJK SC",sans-serif;color:#6c6e72;margin:2mm 0 5mm; }
.article-title-en { font:10.6pt/1.52 "Liberation Serif",Georgia,serif;color:#50545a;margin:0 0 2.5mm; }
.story-line { margin:0 0 2mm; padding:0; }
.story-line .en { font:10.4pt/1.62 "Liberation Serif",Georgia,serif; color:#1c242b; margin:0; text-align:left; }
.story-line .zh { font:10.0pt/1.70 "Noto Serif CJK SC",serif; color:#45484e; margin:0; text-align:left; }
.story-paragraph { margin:0 0 4.5mm; }
.notes { margin:4mm 0 2mm;font-size:8.7pt;color:#4b4e52;border-left:1pt solid #993e49;padding-left:3mm; }
.notes p { margin:0 0 1mm; }
.part-mark { font:7.7pt "Noto Sans CJK SC",sans-serif;color:#777; }
"""

def build_clippings_html(grouped:dict, day:dt.date, market_snapshot=None)->tuple[str,str]:
    """Render source-faithful edited reporting with paired English-Chinese lines."""
    formatted=day.strftime("%Y年%m月%d日")
    page=[
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>全球新闻选编 '+esc(formatted)+'</title>',
        '<style>'+CSS+READER_CSS+'</style></head><body>',
        '<section class="cover">',
        '<div class="kicker">GLOBAL NEWS · PERSONAL EDITION</div>',
        '<div class="cover-rule"></div>',
        '<h1 class="cover-title">全球新闻<br>选编</h1>',
        '<div class="cover-subtitle">美股 · 全球金融 · 中美 · 政治 · AI · 商业 · 科学</div>',
        '<div class="cover-date">'+esc(formatted)+'</div>',
        '<p class="cover-note">面向决策者的完整编辑报道 · 英中逐句对照<br>'
        '删节重复与枝节，保留关键事实、背景、观点归属与限制条件。</p>',
        '</section>',
    ]
    plain=[f"全球新闻选编 | {formatted}"]
    # A concise, sourced US market dashboard precedes all editorial sections.
    # The 01:00 Beijing edition cannot truthfully claim a complete same-day
    # US close: FRED values are dated completed-session observations only.
    if market_snapshot is not None:
        observations = market_snapshot.get("values", [])
        page.append('<section class="market-overview">'
                    '<h2>美股头版 · 指数、波动率与利率</h2>'
                    '<p class="part-mark">FRED公开日度数据；逐项注明数据日期，非实时行情。'
                    '缺失数据不推测，百分比变化仅与上一条有效日度观测比较。</p>')
        plain.append("美股头版 · FRED已公布的最近日度数据（非实时行情）")
        for item in observations:
            name = str(item["name"])
            value = float(item["value"])
            as_of = str(item["as_of"])
            suffix = "%" if item["series"].startswith("DGS") else ""
            change = item.get("change_percent")
            change_str = (
                ("；较上一个有效观测日 " + ("%+.2f%%" % float(change)))
                if change is not None and not suffix else ""
            )
            statement = f"{name}：{value:,.2f}{suffix}（{as_of}）{change_str}"
            page.append(f'<p class="story-line zh">{esc(statement)}</p>')
            plain.append(statement)
        if not observations:
            page.append('<p>本期无法核实FRED指数及收益率数据，因此不发布数值。</p>')
            plain.append("本期FRED市场数据不可核实，未提供数字。")
        if market_snapshot.get("missing"):
            page.append('<p class="part-mark">未取得最新可核实数据：'
                        + esc("、".join(market_snapshot["missing"])) + '</p>')
        page.append('</section>')
    for sect, (category, articles) in enumerate(
            [(k,v) for k,v in grouped.items() if v],1):
        page.append(
            '<section><h2><span class="section-number">'
            +f"{sect:02d}</span>{esc(category)}</h2>"
        )
        plain.append(category)
        for idx,article in enumerate(articles,1):
            en_title=str(article.get("title","")).strip()
            zh_title=str(article.get("title_zh") or en_title).strip()
            source=str(article.get("source","")).strip()
            author=str(article.get("author","")).strip()
            meta=" · ".join([x for x in (source,author,_date_bj(article.get("date"))) if x])
            pairs=article.get("bilingual_pairs") or []
            if not pairs:
                continue
            page.extend([
                '<article class="article">',
                f"<h3>{idx}. {esc(zh_title)}</h3>",
                f'<p class="article-title-en">{esc(en_title)}</p>',
                f'<div class="source-meta">{esc(meta)}</div>'
            ])
            plain.extend([zh_title,en_title,meta])
            if article.get("source_language") == "zh":
                page.append('<p class="part-mark">中文原始来源；未生成或冒充英文原文译文。</p>')
            used=set()
            notes=[]
            previous=None
            for pair in pairs:
                en=str(pair.get("en","")).strip()
                zh=str(pair.get("zh","")).strip()
                if not zh:
                    continue
                pid=pair.get("paragraph_id",0)
                if pid!=previous:
                    if previous is not None:
                        page.append("</div>")
                    page.append('<div class="story-paragraph">')
                    previous=pid
                matched=None
                no=None
                for lesson in article.get("grammar_lessons") or []:
                    if len(notes)>=3 or lesson.get("type") in used:
                        continue
                    if " ".join(en.split())!=" ".join(str(lesson.get("sentence_en","")).split()):
                        continue
                    hit=_grammar_expression(en,lesson)
                    if hit is None:
                        continue
                    matched=hit
                    no=len(notes)+1
                    notes.append((no,hit.group(0),lesson.get("explanation","")))
                    used.add(lesson.get("type"))
                    break
                if en:
                    page.append(
                        '<div class="story-line">'
                        +f'<p class="en">{_highlight_sentence(en,matched,no)}</p>'
                        +f'<p class="zh">{esc(zh)}</p>'
                        +'</div>'
                    )
                    plain.append(en+"\\n"+zh)
                else:
                    page.append('<p class="story-line zh">' + esc(zh) + '</p>')
                    plain.append(zh)
            if previous is not None:
                page.append("</div>")
            if article.get("editing_mode") == "evidence_mapped_edited_report":
                page.append('<div class="part-mark">依据来源整理的编辑报道，非记者原文；事实与观点归属保留，编辑段落可回查来源。</div>')
            if article.get("editing_mode") == "source_faithful_edited_report":
                page.append('<div class="part-mark">编辑选编：保留来源完整段落及叙述顺序；非全文转载。'
                            +('为保留关键限制条件，本篇篇幅较长。' if article.get("editorial_length_exception") else '')+'</div>')
            if article.get("reading_abbreviated"):
                page.append('<div class="part-mark">来源正文提取不完整；本篇依据可取得部分编辑。</div>')
            if notes:
                page.append('<div class="notes">')
                for n,phrase,explanation in notes:
                    page.append(f'<p>{n}. <strong>{esc(phrase)}</strong>：{esc(explanation)}</p>')
                    plain.append(f"{n}. {phrase}：{explanation}")
                page.append("</div>")
            page.append("</article>")
        page.append("</section>")
    page.append("</body></html>")
    return "\n".join(page),"\n\n".join(plain)


def mail_cover_clippings(day:dt.date,grouped:dict)->tuple[str,str]:
    count=sum(len(x) for x in grouped.values())
    title="全球新闻选编｜"+day.isoformat()
    text=f"{title}\n本期收录{count}篇报道。详见附件 PDF（编辑报道及逐句中文译文）。"
    html_text=('<div style="font-family:Georgia,serif;max-width:670px;line-height:1.8">'
               '<h2>'+esc(title)+'</h2><p>今日入选 '+str(count)
               +' 篇报道，编辑报道与逐句中文译文已排入附件 PDF。</p></div>')
    return html_text,text
