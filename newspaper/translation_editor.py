"""Deterministic Chinese news copy-editing and translation quality audit.

Does not turn a weak MT model into a human translator. Only repairs a small
set of meaning-preserving established terminology and formatting. Suspect
pairs are flagged, never replaced by a fabricated paraphrase.
"""
from __future__ import annotations
import re

TERM_CORRECTIONS=[
    (r"\bfederal reserve\b",{
      "联邦储备":"美联储","美联邦储备":"美联储","美国联邦储备":"美联储"}),
    (r"\bnuclear fusion\b",{"核融合":"核聚变","核融合反应":"核聚变反应"}),
    (r"\bclinical trials?\b",{"临床实验":"临床试验"}),
    (r"\bquantum computing\b",{"量子电脑":"量子计算"}),
    (r"\btreasury yields?\b",{"财政部收益率":"国债收益率"}),
    (r"\bsuperconduct(?:or|ivity|ing)\b",{"超级导电":"超导"}),
    (r"\bartificial intelligence\b",{"人工智慧":"人工智能"}),
]

def polish_translation(english:str,chinese:str)->tuple[str,list[str]]:
    result=str(chinese or "").strip()
    flags=[]
    if not result:
        return "",["empty_translation"]
    for source_pattern, substitutions in TERM_CORRECTIONS:
        if re.search(source_pattern,english,re.I):
            for before,after in substitutions.items():
                result=result.replace(before,after)
    result=re.sub(r"\s+([，。；：？！])",r"\1",result)
    result=re.sub(r"([，。；：？！])\s+",r"\1",result)
    result=result.replace(" ,","，").replace(" ;","；")
    if len(result)>12 and len(re.findall(r"[\u4e00-\u9fff]",result))<4:
        flags.append("low_chinese_content")
    if re.search(r"\b(?:not|never|no longer|without)\b",english,re.I):
        # Audit possible negation loss; do not overwrite journalist intent.
        if not any(word in result for word in ("不","未","无","没","非","否","除","免")):
            flags.append("possible_negation_loss")
    percentages=re.findall(r"\d+(?:\.\d+)?\s*%",english)
    for val in percentages:
        digits=re.search(r"\d+(?:\.\d+)?",val).group(0)
        if digits not in result:
            flags.append("percentage_requires_review")
            break
    return result,flags


def polish_news_title(english: str, chinese: str) -> tuple[str, list[str]]:
    """Safely display an MT news headline without inventing a better translation.

    A broken translated headline is worse than a legible, attributed original.
    This simple guard catches *obvious* truncation, not subtle semantic errors.
    """
    source = str(english or "").strip()
    translated = str(chinese or "").strip()
    normalized, flags = polish_translation(source, translated)
    normalized = normalized.strip()
    if not normalized:
        return source, ["title_translation_empty"]
    if re.search(r"[,，、:：;；]$", normalized):
        return source, ["title_translation_ends_mid_clause"]
    han = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    if len(source) >= 25 and han < 5:
        return source, ["title_translation_too_little_chinese"]
    if "low_chinese_content" in flags:
        return source, ["title_translation_too_little_chinese"]
    return normalized, [f"title_{x}" for x in flags]
