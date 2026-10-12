"""Newsroom selection rules: China + US political coverage, frontier-only tech.

All classification operates on actual RSS metadata, not invented events.
Shortfalls are reported as shortfalls; don't pad with unrelated headlines.
"""
from __future__ import annotations
import re

CHINA = re.compile(
    r"\b(?:china|chinese|beijing|xi jinping|hong kong|taiwan|shanghai|"
    r"communist party|prc|sino[\s-])\b",re.I)
USA = re.compile(
    r"\b(?:u\.?s\.?|united states|america|american|washington|white house|"
    r"congress|pentagon|us senate|trump|federal government|supreme court)\b",re.I)
PUBLIC = re.compile(
    r"\b(?:government|president|leader|minister|election|diploma|"
    r"tariff|policy|politic|military|war|security|trade|sanction|"
    r"treaty|protest|parliament|border|govern|conflict|state|"
    r"legislation|negotiat|summit|tension|missile|attack|"
    r"geopolitic|congress|administration|bilateral|strategic)\w*",re.I)
POP_CULTURE = re.compile(
    r"\b(?:trailer|teaser|nycc|comic[\s-]?con|prime video|"
    r"blade runner|movie|film festival|tv series|television series|"
    r"season premiere|streaming premiere|netflix series|"
    r"marvel film|celebrity|red carpet|box office|"
    r"video game review|game trailer|movie review|"
    r"cast members|soundtrack|anime series)\b",re.I)
FRONTIER = re.compile(
    r"\b(?:artificial intelligence|(?:generative|agentic|physical) ai|"
    r"\bai\b|large language model|llms?|inference|"
    r"machine learning|deep learning|neural network|"
    r"robot(?:ics)?|autonomous systems|"
    r"quantum|superconduct|fusion|tokamak|stellarator|"
    r"plasma physic|particle physics|dark matter|"
    r"semiconductor|advanced chip|photonic|"
    r"new material|materials science|"
    r"research breakthrough|laboratory|experiment|"
    r"scientists|researchers|peer.review|"
    r"battery technolog|nuclear reactor|energy storage|"
    r"spacecraft|space science|space telescope|"
    r"computational biolog|protein folding|"
    r"clinical research|accelerator|"
    r"scientific discovery|physics)\w*",re.I)
MATERIAL = re.compile(
    r"\b(?:breakthrough|demonstrat|scientists|research|"
    r"study|develop|new model|new method|discovery|"
    r"test|trial|improv|prototype|unveil|"
    r"experiment|publish|perform|achiev|announce|"
    r"design|fabricat|efficien|funding|commerciali|"
    r"deployment|regulat|launch)\w*",re.I)

def text(item:dict)->str:
    return " ".join(str(item.get(k,"")) for k in ("title","summary"))[:2600]

def is_tech_substantive(item:dict)->bool:
    s=text(item)
    if POP_CULTURE.search(s):
        return False
    return bool(FRONTIER.search(s) and MATERIAL.search(s))

def political_regions(item:dict)->set[str]:
    s=text(item)
    if not PUBLIC.search(s):
        return set()
    regions=set()
    if CHINA.search(s): regions.add("中国")
    if USA.search(s): regions.add("美国")
    return regions

def pick_politics(items:list[dict],quota:int,selected_global:list[dict],duplicate,
                  source_max:int=2,extra_limit:int=2)->tuple[list[dict],dict]:
    """Select separate China and US stories, then third-world reporting.

    Important supplementary stories may add up to extra_limit slots; shortage is
    explicit if suitable readable stories do not exist.
    """
    used=[]
    def qualifies(item:dict)->bool:
        if item in used or duplicate(item,selected_global+used):
            return False
        return True
    def pick_region(region:str)->bool:
        for a in items:
            if region in political_regions(a) and qualifies(a):
                used.append(a)
                return True
        return False
    china=pick_region("中国")
    usa=pick_region("美国")
    base=max(quota,3)
    counts={}
    for a in used: counts[a.get("source","")]=counts.get(a.get("source",""),0)+1
    # Candidate pool is already scored by impact; prioritize diverse publishers.
    for diversify in (True,False):
        for item in items:
            if len(used)>=base: break
            if not qualifies(item): continue
            if not PUBLIC.search(text(item)): continue
            if diversify and counts.get(item.get("source",""),0)>=source_max:
                continue
            used.append(item)
            name=item.get("source","")
            counts[name]=counts.get(name,0)+1
    # Significant distinct events may be included in addition to the baseline.
    if len(used)>=base:
        for item in items:
            if len(used)>=base+extra_limit: break
            if not qualifies(item): continue
            if not PUBLIC.search(text(item)): continue
            if float(item.get("importance_score",0))>=90:
                used.append(item)
    return used,{
        "china_covered":china,"us_covered":usa,
        "minimum_met":len(used)>=3,
        "political_total":len(used),
        "political_shortfall":"; ".join(
            k for k,v in (("中国",china),("美国",usa),("合计不足3篇",len(used)>=3)) if not v
        ),
    }

def tech_candidates(items:list[dict])->list[dict]:
    return [a for a in items if is_tech_substantive(a)]
