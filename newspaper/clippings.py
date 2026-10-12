"""V0.6 Newspaper: original-wording clipping reader with sentence-aligned translation.

Preserves text exactly for material with recorded republication AND translation
rights. Other publishers receive only a short non-substitutive quotation and
a prominent original-article link; no rephrasing or template pseudo-analysis.
"""
from __future__ import annotations

import datetime as dt
import html
import re
from collections import defaultdict
from urllib.parse import urlparse

from print_report import CSS, _date_bj, _grammar_expression, _highlight_sentence, esc, mail_cover as old_mail_cover

MAX_UNLICENSED_WORDS = 25
SHORT_QUOTE_CSS = """
h2 { margin-top:9mm; }
.article { margin-bottom:10mm; }
.byline { font: 8.4pt/1.55 "Noto Sans CJK SC",sans-serif; color:#62646a; margin-bottom:4mm; }
.article-title-en { font: 10pt/1.5 "Liberation Serif",serif; color:#515359; margin:0 0 3mm; }
.clip-line { margin:0 0 3mm; }
.clip-line .en { font-size:10.25pt; line-height:1.65; margin:0; }
.clip-line .zh { font-size:10.15pt; line-height:1.7; margin:0; }
.clip-paragraph { margin-bottom:5mm; }
.license-note { font: 8.3pt "Noto Sans CJK SC",sans-serif; color:#9a4449; }
.source-link { font: 9pt "Noto Sans CJK SC",sans-serif; padding:2mm 0; }
.grammar-footnote { font-size:9pt; color:#4d4d4d; margin:3mm 0 2mm; }
.grammar-footnote p { margin:0 0 1.5mm; }
"""

def approved_full_text(article: dict) -> bool:
    """Only explicit repo-configured permission evidence qualifies."""
    rights = article.get("republication_rights", {})
    return (
        isinstance(rights, dict)
        and rights.get("allow_full_republication") is True
        and rights.get("allow_chinese_translation") is True
        and isinstance(rights.get("evidence_url"), str)
        and rights["evidence_url"].startswith("https://")
    )

def attach_rights(grouped: dict, licenses: dict) -> dict:
    """Do not accept publisher RSS or article HTML claims as legal authorization.

    Repo maintainer must explicitly add domain + evidence + permissions to
    a human-reviewed mapping. Empty mapping (default) grants no rights.
    """
    output={}
    for category, articles in grouped.items():
        output[category]=[]
        for a in articles:
            entry=dict(a)
            host=(urlparse(str(a.get("url",""))).hostname or "").lower()
            cfg=licenses.get(host,{}) if isinstance(licenses,dict) else {}
            entry["republication_rights"] = {
                "evidence_url":str(cfg.get("evidence_url","")),
                "allow_full_republication":cfg.get("allow_full_republication") is True,
                "allow_chinese_translation":cfg.get("allow_chinese_translation") is True,
            }
            output[category].append(entry)
    return output

def _choose_original_lines(article: dict) -> tuple[list[dict], bool]:
    pairs = article.get("bilingual_pairs") or []
    if approved_full_text(article):
        # Extractor may stop at a configured length; never claim full when so.
        return pairs, not article.get("reading_abbreviated",True)
    # For copyrighted sources without proof of reuse rights, include an
    # unchanged short original passage, preserving one-sentence boundaries.
    # Never cut a sentence mid-stream, invent connective wording or assemble
    # unrelated excerpts from other sections.
    chosen=[]
    budget=MAX_UNLICENSED_WORDS
    for item in pairs:
        en=str(item.get("en","")).strip()
        zh=str(item.get("zh","")).strip()
        words=len(en.split())
        if not en or not zh or words>budget:
            break
        chosen.append(item)
        budget-=words
        if budget<=0:
            break
    return chosen,False

def build_clippings_html(grouped: dict, day: dt.date) -> tuple[str, str]:
    """Keep the preferred A5 publication layout, eliminate boilerplate prose."""
    date_str=day.strftime("%Y年%m月%d日")
    count=sum(len(items) for items in grouped.values())
    body=[
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>全球新闻原文选编 '+esc(date_str)+'</title>',
        '<style>'+CSS+SHORT_QUOTE_CSS+'</style></head><body>',
        '<section class="cover">',
        '<div class="kicker">GLOBAL NEWS CLIPPINGS / ORIGINAL EDITION</div>',
        '<div class="cover-rule"></div>',
        '<h1 class="cover-title">全球新闻<br>原文选编</h1>',
        '<div class="cover-subtitle">原文精选 · 逐句对译 · 语法边注</div>',
        '<div class="cover-date">'+esc(date_str)+'</div>',
        '<p class="cover-note">保留媒体原始英文遣词。'
        '有明确再版及翻译授权的来源可收录其可取得的全文；'
        '其他报道仅收入可供本版展示的原句选段，保存原有英文与中文对照。'
        '评论另见邮件正文。</p></section>',
    ]
    plain=[f"全球新闻原文选编 | {date_str}", f"入选文章来源：{count}"]
    number=0
    for category,articles in grouped.items():
        if not articles:
            continue
        number+=1
        body.append(
            '<section><h2><span class="section-number">'
            f'{number:02d}</span>{esc(category)}</h2>'
        )
        plain.append("\n"+category)
        for idx,article in enumerate(articles,1):
            en_title=str(article.get("title","")).strip()
            zh_title=str(article.get("title_zh") or en_title).strip()
            source=str(article.get("source","未知媒体")).strip()
            byline=source + (" · " + str(article.get("author")).strip() if article.get("author") else "") + " · " + _date_bj(article.get("date"))
            selected,full=_choose_original_lines(article)
            rights=approved_full_text(article)
            body.extend([
                '<article class="article">',
                f'<h3>{idx}. {esc(zh_title)}</h3>',
                f'<p class="article-title-en">{esc(en_title)}</p>',
                '<div class="byline">'+esc(byline)+'</div>',
            ])
            plain.extend([zh_title,en_title,byline])
            if rights and full:
                statement="原始英文正文 · 已登记全文和中文翻译使用许可"
            elif rights:
                statement="原始英文连续选段 · 已登记使用许可；抓取正文未覆盖全文"
            else:
                statement="原始英文短摘 · 此来源未获整篇再版及翻译授权"
            body.append(f'<p class="license-note">{esc(statement)}</p>')
            plain.append(statement)
            notes=[]
            used_types=set()
            prev_para=None
            for pair in selected:
                pid=pair.get("paragraph_id",0)
                if pid != prev_para:
                    if prev_para is not None:
                        body.append('</div>')
                    body.append('<div class="clip-paragraph">')
                    prev_para=pid
                sentence=str(pair.get("en","")).strip()
                translation=str(pair.get("zh","")).strip()
                highlight=None
                selected_number=None
                for lesson in article.get("grammar_lessons") or []:
                    if len(notes)>=3:
                        break
                    if lesson.get("type") in used_types:
                        continue
                    if " ".join(str(lesson.get("sentence_en","")).split()) != " ".join(sentence.split()):
                        continue
                    hit=_grammar_expression(sentence,lesson)
                    if not hit:
                        continue
                    selected_number=len(notes)+1
                    highlight=hit
                    used_types.add(lesson.get("type"))
                    notes.append((selected_number,hit.group(0),lesson.get("explanation","")))
                    break
                body.append(
                    '<div class="clip-line">'
                    f'<p class="en">{_highlight_sentence(sentence,highlight,selected_number)}</p>'
                    f'<p class="zh">{esc(translation)}</p>'
                    '</div>'
                )
                plain.append(sentence+"\n"+translation)
            if prev_para is not None:
                body.append('</div>')
            if not selected:
                body.append('<p>没有符合当前使用范围的完整英文句子。</p>')
                plain.append("本篇未提供可刊用完整原句。")
            if notes:
                body.append('<div class="grammar-footnote">')
                for n,phrase,meaning in notes:
                    body.append(f'<p>{n}. <strong>{esc(phrase)}</strong>：{esc(meaning)}</p>')
                    plain.append(f"{n}. {phrase}：{meaning}")
                body.append('</div>')
            # Reader-first publication: source URLs stay available in the
            # article metadata for provenance/audit but are NEVER printed in
            # the PDF or its plaintext companion. No "read more" links.
            body.append('</article>')
        body.append('</section>')
    body.append(
        '<p class="smallprint">栏目按相关新闻归类；英文短句保持提取结果中的原句内容，'
        '中文由离线模型翻译，可能存在翻译错误。源站内容的著作权属于权利人。'
        '本 PDF 不含未授权商业媒体的整篇报道，也不以程序套话冒充专业评论。</p>'
        '</body></html>'
    )
    return "\n".join(body), "\n\n".join(plain)

def mail_cover_clippings(day:dt.date, grouped:dict) -> tuple[str,str]:
    """No fictitious world-situation commentary. Mail is a neutral delivery note."""
    date_str=day.strftime("%Y-%m-%d")
    count=sum(len(items) for items in grouped.values())
    txt=(f"全球新闻原文选编 | {date_str}\n"
         f"今日纳入 {count} 篇来源报道，PDF 附件收录原文短摘及逐句中文翻译，"
         "有转载及翻译许可的材料可刊用完整正文。"
         "各篇附有媒体名称和发布时间。\n"
         "编辑评论：当前没有接入可验证的研究型大模型，本期不自动生成空泛观点。\n")
    html_text=(
        '<div style="font-family:Arial,sans-serif;line-height:1.7;max-width:600px">'
        '<h2>全球新闻原文选编</h2>'
        '<p>'+esc(date_str)+' · '+str(count)+' 篇来源报道</p>'
        '<p>PDF 附件已生成，英文原句与中文翻译逐句对应。'
        '当前无完整再版许可的文章只收录短摘，内容覆盖会受限。'
        '本期不自动生成缺乏证据支持的评论。</p></div>'
    )
    return html_text,txt
