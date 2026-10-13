"""Substantive, auditable paragraph editing, never headline-length abstracts.

The model may choose paragraph IDs; it cannot supply replacement factual prose.
Statements, attribution, caveats and chronology remain the publisher's wording.
The original captured material and span hashes remain in the private checkpoint.
"""
from __future__ import annotations
import hashlib
import re

QUALIFIER = re.compile(r"\b(?:however|but|although|unless|only if|subject to|conditional|not yet|denied|disputed|critics?|opponents?|cautioned|uncertain|preliminary|limitations?|could|might|may|not|according to)\b", re.I)
FACT = re.compile(r"\b(?:\d|announc|approv|vot|enact|effective|deadline|percent|billion|million|previous|last year|scheduled|expected|said|told|reported)", re.I)
DEPENDENT = re.compile(r"^(?:He|She|They|It|This|That|These|Those|Such|The move|The decision|Meanwhile|However|But|Although)\b", re.I)
NOISE = re.compile(r"^(?:advertisement|sign up|subscribe|read more|related articles|follow us)\b", re.I)

def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))

def prepare_article(article):
    a = dict(article)
    original = a.get("source_reading_en", a.get("reading_en", ""))
    paragraphs = [p.strip() for p in original.split("\n\n") if p.strip()]
    protected = set(range(min(2, len(paragraphs))))
    for i, p in enumerate(paragraphs):
        if QUALIFIER.search(p) and not NOISE.search(p):
            protected.add(i)
    a.update(source_reading_en=original, source_paragraphs=paragraphs,
             protected_paragraph_ids=sorted(protected),
             source_sha256=hashlib.sha256(original.encode()).hexdigest())
    return a

def edit_article(article, proposed_ids=None, target_words=480):
    a = prepare_article(article)
    ps = a["source_paragraphs"]
    keep = set(a["protected_paragraph_ids"])
    if proposed_ids is not None:
        if not isinstance(proposed_ids, list) or not proposed_ids or any(type(i) is not int or i < 0 or i >= len(ps) for i in proposed_ids):
            raise ValueError("Invalid source paragraph IDs")
        keep.update(proposed_ids)
    else:
        # Complete source paragraphs; meaningful facts outrank colour and repetition.
        order = sorted(range(len(ps)), key=lambda i:(bool(FACT.search(ps[i])), -i), reverse=True)
        for i in order:
            if sum(word_count(ps[j]) for j in keep) >= target_words: break
            if not NOISE.search(ps[i]): keep.add(i)
    # A model cannot shrink a substantial article into a tiny abstract.
    minimum = min(330, word_count(a["source_reading_en"]))
    for i in range(len(ps)):
        if sum(word_count(ps[j]) for j in keep) >= minimum: break
        if not NOISE.search(ps[i]): keep.add(i)
    # Include antecedents and attribution before dependent opening paragraphs.
    changed = True
    while changed:
        changed = False
        for i in list(keep):
            if i > 0 and i-1 not in keep and DEPENDENT.search(ps[i]):
                keep.add(i-1); changed = True
    ids = sorted(keep)
    body = "\n\n".join(ps[i] for i in ids)
    a.update(reading_en=body, editing_mode="source_faithful_edited_report",
             original_paragraphs_kept=ids, editorial_trimmed=len(ids)<len(ps),
             captured_words=word_count(a["source_reading_en"]), retained_words=word_count(body),
             retention_rate=round(word_count(body)/max(1,word_count(a["source_reading_en"])),4),
             editing_method="ai_paragraph_selection" if proposed_ids is not None else "conservative_paragraph_selection",
             editorial_length_exception=word_count(body)>800,
             source_map=[{"paragraph_id":i, "sha256":hashlib.sha256(ps[i].encode()).hexdigest()} for i in ids])
    return a

def edit_grouped(grouped, plans=None):
    result = {}
    for category, articles in grouped.items():
        result[category] = []
        for a in articles:
            ids = (plans or {}).get(a.get("event_key", a.get("url")))
            try:
                edited = edit_article(a, ids)
            except ValueError:
                edited = edit_article(a)
                edited["editor_plan_rejected"] = True
            result[category].append(edited)
    return result
