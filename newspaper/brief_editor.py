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

def validate_rewritten_report(article, paragraphs):
    """Structural/source checks; not a claim of complete semantic verification.

Reject new numeric claims, altered direct quotes, removed explicit negation or
uncertainty, missing protected source coverage, and headline-length responses.
Unknown or rejected results fall back per article instead of publishing them.
"""
    a = prepare_article(article)
    source = a["source_paragraphs"]
    if not isinstance(paragraphs,list) or not 3 <= len(paragraphs) <= 12:
        raise ValueError("Expected a complete report with mapped paragraphs")
    covered, blocks, mapping = set(), [], []
    numbers = lambda s: set(re.findall(r"\b\d+(?:[,.]\d+)*(?:%)?", s))
    uncertainty = re.compile(r"\b(?:could|may|might|would|possible|potential|uncertain|preliminary|expected|forecast|estimate|propos\w*|subject to|if|unless)\b",re.I)
    negative = re.compile(r"\b(?:not|no|never|denied|without|unapproved|unproven)\b",re.I)
    for paragraph in paragraphs:
        if not isinstance(paragraph,dict): raise ValueError("Invalid report paragraph")
        text, ids = paragraph.get("en"), paragraph.get("source_ids")
        if not isinstance(text,str) or not isinstance(ids,list) or not ids:
            raise ValueError("Missing report evidence")
        if any(type(i) is not int or i < 0 or i >= len(source) for i in ids):
            raise ValueError("Unknown source span")
        evidence = "\n".join(source[i] for i in ids)
        if not numbers(text) <= numbers(evidence): raise ValueError("Unsupported numeric claim")
        for quote in re.findall(r'["“]([^"”]{8,})["”]',text):
            if quote not in evidence: raise ValueError("Changed direct quotation")
        if negative.search(evidence) and not negative.search(text):
            raise ValueError("Source negation may have been lost")
        if uncertainty.search(evidence) and not uncertainty.search(text):
            raise ValueError("Source uncertainty may have been hardened")
        blocks.append(text.strip()); covered.update(ids)
        mapping.append({"source_paragraph_ids":ids,"edited_sha256":hashlib.sha256(text.strip().encode()).hexdigest()})
    if not set(a["protected_paragraph_ids"]) <= covered: raise ValueError("Protected facts or caveats omitted")
    body = "\n\n".join(blocks)
    if not min(300, word_count(a["source_reading_en"])*0.8) <= word_count(body) <= 850:
        raise ValueError("Report is too short or exceeds substantive report limit")
    a.update(reading_en=body,editing_mode="evidence_mapped_edited_report",
             editing_method="ai_source_based_rewrite",editorial_trimmed=True,
             captured_words=word_count(a["source_reading_en"]),retained_words=word_count(body),
             retention_rate=round(word_count(body)/max(1,word_count(a["source_reading_en"])),4),
             source_map=mapping,original_paragraphs_kept=sorted(covered),
             editorial_length_exception=word_count(body)>650)
    return a

def apply_reports(grouped, reports):
    output = {}
    for section, articles in grouped.items():
        output[section] = []
        for article in articles:
            try:
                proposal = reports.get(article.get("event_key", article.get("url")))
                edited = validate_rewritten_report(article,proposal)
            except (ValueError,TypeError) as exc:
                edited = edit_article(article)
                edited["editor_plan_rejected"] = True
                edited["editor_rejection_reason"] = str(exc)
            output[section].append(edited)
    return output
