"""Lossless-language editing: remove only low-information ORIGINAL paragraphs.

Never paraphrase or generate replacement journalist words. Aim to retain >=70%
of extracted English words, thereby removing at most 30% when warranted.
"""
from __future__ import annotations
import re
from collections import Counter

BOILERPLATE = re.compile(
 r"\b(?:sign up for|subscribe to our|more from this author|"
 r"advertisement|follow us on|read our newsletter|"
 r"this story has been updated|click here to|"
 r"for more of our coverage|related articles)\b",re.I)

def _words(text:str)->int:
    return len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b",text))

def trim_extracted_article(article:dict,min_retention:float=0.70)->dict:
    if not 2/3 <= min_retention <= 1:
        raise ValueError("Retention cannot dip below two-thirds")
    entry=dict(article)
    source=str(entry.get("reading_en") or "").strip()
    para=[p.strip() for p in source.split("\n\n") if p.strip()]
    total=_words(source)
    entry["editing_mode"]="extractive_only"
    entry["captured_words"]=total
    entry["retained_words"]=total
    entry["retention_rate"]=1.0
    entry["original_paragraphs_kept"]=list(range(len(para)))
    # Avoid corrupting short briefs and stories with few meaningful paragraphs.
    if len(para)<8 or total<800:
        return entry
    # Only obvious low-signal material is removable. Never drop more than 30%.
    removable=[]
    for idx,block in enumerate(para):
        if idx<2: continue
        count=_words(block)
        if count<15 or count>180: continue
        if re.search(r'\d|["“”]',block): continue
        if BOILERPLATE.search(block):
            removable.append(idx)
    removed=set()
    remaining=total
    for idx in removable:
        lost=_words(para[idx])
        if remaining-lost < min_retention*total: continue
        removed.add(idx)
        remaining-=lost
    if not removed:
        return entry
    keep=[i for i in range(len(para)) if i not in removed]
    selected="\n\n".join(para[i] for i in keep)
    assert _words(selected) >= min_retention*total
    entry["reading_en"]=selected
    entry["retained_words"]=_words(selected)
    entry["retention_rate"]=round(entry["retained_words"]/total,4)
    entry["original_paragraphs_kept"]=keep
    entry["editorial_trimmed"]=True
    return entry
