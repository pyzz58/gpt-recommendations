"""Event-first, evidence-labelled edition selection. Scores are routing heuristics.

No media-volume signal is treated as independent fact verification. A publisher's
multiple feeds count once; identical syndicated stories share an event slot.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import re
from urllib.parse import urlparse
from ranking import _story_groups

SECTIONS = {
    "中国与美国": 3,
    "国际政治与全球事件": 3,
    "金融、宏观与美股": 3,
    "AI与数字产业": 2,
    "科技与前沿科学": 1,
    "全球商业与创业前沿": 2,
    "能源、资源与供应链": 1,
    "医疗与生命科学": 1,
}
COUNTRIES = {
    "中国": r"\b(?:china|chinese|beijing|shanghai|shenzhen|xi jinping)\b",
    "美国": r"\b(?:united states|american|america|washington|white house|congress|pentagon|federal reserve|trump)\b|\bU\.?S\.?\b",
    "印度": r"\b(?:india|indian|new delhi|modi|mumbai)\b",
    "俄罗斯": r"\b(?:russia|russian|moscow|putin)\b",
    "乌克兰": r"\b(?:ukraine|ukrainian|kyiv|zelensky)\b",
    "英国": r"\b(?:britain|british|united kingdom|london|UK)\b",
    "德国": r"\b(?:germany|german|berlin)\b",
    "法国": r"\b(?:france|french|paris|macron)\b",
    "日本": r"\b(?:japan|japanese|tokyo)\b",
    "以色列": r"\b(?:israel|israeli|netanyahu)\b",
    "伊朗": r"\b(?:iran|iranian|tehran)\b",
    "巴勒斯坦": r"\b(?:palestine|palestinian|gaza)\b",
    "韩国": r"\b(?:south korea|korean|seoul)\b",
    "巴西": r"\b(?:brazil|brazilian)\b",
    "澳大利亚": r"\b(?:australia|australian|canberra)\b",
    "加拿大": r"\b(?:canada|canadian|ottawa)\b",
    "欧盟": r"\b(?:EU|European Union|European Commission|Brussels)\b",
}
POLITICS = r"\b(?:election|president|government|parliament|diplomac\w*|war|ceasefire|military|sanctions?|treaty|coup|missile|invasion|earthquake|pandemic|floods?|hurricane|summit)\b"
FINANCE = r"\b(?:federal reserve|central bank|interest rates?|inflation|gdp|treasury|bond yields?|stock market|nasdaq|s&p|earnings|financial|banking|currency|recession|unemployment|monetary|fiscal|tariffs?|imports?|exports?|trade)\b"
AI = r"\b(?:AI|artificial intelligence|LLMs?|large language model|machine learning|data cent(?:er|re)|cloud computing|cybersecurity|software|digital platform)\b"
SCIENCE = r"\b(?:quantum|physics|scientists?|researchers?|semiconductor|chip|robot\w*|spacecraft|satellite|rocket|superconduct\w*|materials science)\b"
BUSINESS = r"\b(?:startup|start-up|entrepreneur\w*|business model|venture capital|funding|series [a-f]|acquisition|merger|IPO|bankruptcy|restructuring|supply chain|retail|revenue|profit|commerciali\w*|company|companies)\b"
ENERGY = r"\b(?:energy|oil|gas|OPEC|electricity|power grid|nuclear|fusion|solar|wind power|battery|lithium|copper|rare earth|critical minerals|shipping|supply chain|food exports?|grain|export ban)\b"
HEALTH = r"\b(?:health|medical|clinical|drug|vaccine|cancer|hospital|biotech|gene|protein|disease|FDA|WHO)\b"
PROMO = r"\b(?:trailer|celebrity|movie review|coupon|best deals|horoscope|sponsored content|affiliate links)\b"
ACTION = r"\b(?:announc\w*|approv\w*|enact\w*|launch\w*|cut|hike\w*|votes?|agreed|acquir\w*|report\w*|reveal\w*|signed|ban\w*|strikes?|invad\w*|deploy\w*|discover\w*|demonstrat\w*|limit\w*|restrict\w*|caps?)\b"

def matches(pattern, text):
    return bool(re.search(pattern, text, re.I))

def countries(item):
    title = item.get("title", "")
    # Title is the primary-event proxy. Incidental countries in background should
    # not turn every international article into a China/US story.
    result = set()
    for name, pattern in COUNTRIES.items():
        if name == "美国":
            if matches(pattern.split("|\\bU")[0], title) or re.search(r"\bU\.?S\.?\b", title):
                result.add(name)
        elif matches(pattern, title):
            result.add(name)
    return result

def publisher(item):
    text = item.get("summary", "")
    if re.search(r"\b(?:by|©|copyright)\s+(?:reuters|associated press)\b", text, re.I):
        return "reuters" if "reuters" in text.lower() else "associated-press"
    host = (urlparse(item.get("url", "")).hostname or "").lower().removeprefix("www.")
    for suffix, family in (("bbc.co.uk", "bbc"), ("bbc.com", "bbc"),
                           ("theguardian.com", "guardian"), ("cnbc.com", "cnbc"),
                           ("techcrunch.com", "techcrunch"), ("mit.edu", "mit")):
        if host == suffix or host.endswith("." + suffix):
            return family
    return host or item.get("source", "unknown").lower()

def sections(item):
    title = item.get("title", "")
    s = title + " " + item.get("summary", "")
    if matches(PROMO, s):
        return set()
    result = set()
    if countries(item) & {"中国", "美国"}: result.add("中国与美国")
    for label, pattern in (("国际政治与全球事件", POLITICS), ("金融、宏观与美股", FINANCE),
                           ("AI与数字产业", AI), ("科技与前沿科学", SCIENCE),
                           ("全球商业与创业前沿", BUSINESS), ("能源、资源与供应链", ENERGY),
                           ("医疗与生命科学", HEALTH)):
        if matches(pattern, s): result.add(label)
    return result

def score(item, independent_publishers):
    s = item.get("title", "") + " " + item.get("summary", "")
    cs = countries(item)
    global_signal = matches(r"\b(?:global|worldwide|international|cross-border|world trade|supply chain|export ban|shipping|OPEC|federal reserve|imports?|exports?|trade)\b", s)
    scope = 30 if global_signal else 22 if len(cs) >= 2 else 10 if cs else 5
    systemic = matches(r"\b(?:central bank|federal reserve|interest rate|war|invasion|pandemic|financial crisis|trade agreement|national election|export ban|power grid)\b", s)
    scale = 25 if systemic else 16 if matches(FINANCE + "|" + ENERGY, s) else 8
    structural = matches(r"\b(?:law|legislation|treaty|regulation|sanction|tariff|approval|breakthrough|acquisition|merger|bankruptcy|infrastructure|ban|quota|restrict|limit)\w*", s)
    duration = 20 if structural else 10 if matches(SCIENCE + "|" + BUSINESS, s) else 5
    new = 15 if matches(ACTION, s) else 5
    # Publisher breadth is only a capped proxy; geographic independence unknown.
    breadth = min(10, max(0, independent_publishers - 1) * 3)
    evidence = {"cross_border_proxy": scope, "scale_proxy": scale,
                "structural_change_proxy": duration, "new_development_proxy": new,
                "publisher_breadth_proxy": breadth}
    return sum(evidence.values()), evidence

def prepare_pool(items, per_section=20):
    unique = {}
    for a in items:
        unique.setdefault(a["url"], dict(a))
    all_items = list(unique.values())
    groups = _story_groups(all_items, threshold=0.48)
    for indices in groups:
        families = {publisher(all_items[i]) for i in indices}
        event = hashlib.sha256(min(all_items[i]["url"] for i in indices).encode()).hexdigest()[:20]
        for i in indices:
            a = all_items[i]
            value, evidence = score(a, len(families))
            a.update(event_key=event, importance_score=value, score_evidence=evidence,
                     publisher_family=publisher(a), countries=sorted(countries(a)),
                     eligible_sections=sorted(sections(a)), related_publishers=sorted(families),
                     why_recommended="全球影响启发式；各维度保留依据，不代表事实核验")
    result = {}
    for section in SECTIONS:
        candidates = sorted((a for a in all_items if section in a["eligible_sections"] and a["importance_score"] >= 35),
                            key=lambda a: a["importance_score"], reverse=True)
        # Protect both regions before fetching and keep same-event alternatives.
        preferred = []
        if section == "中国与美国":
            for country in ("中国", "美国"):
                preferred.extend([a for a in candidates if country in a["countries"]][:5])
        families = Counter()
        for a in candidates:
            if families[a["publisher_family"]] < 4:
                preferred.append(a)
                families[a["publisher_family"]] += 1
        preferred.extend(candidates)
        picked = {}
        for a in preferred:
            picked.setdefault(a["url"], a)
        result[section] = sorted(list(picked.values())[:per_section], key=lambda a:a["importance_score"], reverse=True)
    return result

def select_readable(candidates, enriched):
    output, diagnostics = {}, {}
    used_events, used_urls = set(), set()
    for section, quota in SECTIONS.items():
        available = [enriched[a["url"]] for a in candidates.get(section, []) if enriched.get(a["url"])]
        selected, families, concentration, exceptions = [], Counter(), Counter(), []
        def add(a, allow_exception=False):
            if a["url"] in used_urls or a["event_key"] in used_events: return False
            cs = set(a.get("countries", [])) - {"中国", "美国"}
            overcrowded = section == "国际政治与全球事件" and any(concentration[c] >= 1 for c in cs)
            if overcrowded and not (allow_exception and a["importance_score"] >= 80): return False
            if families[a["publisher_family"]] >= 2: return False
            if overcrowded:
                exceptions.append({"event": a["event_key"], "reason": "同国重大事件达到80分；保留集中度复核标记"})
            selected.append({**a, "category": section})
            used_events.add(a["event_key"]); used_urls.add(a["url"])
            families[a["publisher_family"]] += 1
            concentration.update(cs)
            return True
        if section == "中国与美国":
            for country in ("中国", "美国"):
                if any(country in a.get("countries", []) for a in selected): continue
                for a in available:
                    if country in a.get("countries", []) and add(a): break
        for exceptional in (False, True):
            for a in available:
                if len(selected) >= quota: break
                add(a, exceptional)
        output[section] = selected
        missing = [c for c in ("中国", "美国") if not any(c in a.get("countries", []) for a in selected)] if section == "中国与美国" else []
        diagnostics[section] = {"quota": quota, "candidate_count": len(candidates.get(section, [])),
            "readable": len(available), "selected": len(selected), "missing_regions": missing,
            "shortfall": max(0, quota-len(selected)), "country_counts": dict(concentration),
            "concentration_exceptions": exceptions}
    return output, diagnostics
