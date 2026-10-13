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
from source_quality import newsworthiness

SECTIONS = {
    "美股·全球金融市场": 4,
    "中国与美国": 3,
    "国际政治与全球事件": 3,
    "AI与数字产业": 2,
    "科技、能源与前沿科学": 1,
    "创业、商业与企业竞争": 2,
    "医疗、生命科学与公共健康": 1
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
    if re.search(r"中国|中方|北京|国务院|央行|央企", title):
        result.add("中国")
    if re.search(r"美国|美联储|华尔街|白宫|美股|特朗普", title):
        result.add("美国")
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
    if not newsworthiness(item)["eligible"]:
        return set()
    result = set()
    if countries(item) & {"中国", "美国"}: result.add("中国与美国")
    if item.get("source_language") == "zh":
        # Preserve Chinese as the publisher's original text (never invent an
        # English translation). Chinese-specific relevance routing is required.
        if re.search(r"美股|纳指|标普|道指|美联储|美国国债|财报|港股|股市|利率|通胀|资本市场", s):
            result.add("美股·全球金融市场")
        if re.search(r"国际|外交|冲突|关税|战事|军事|政策|选举|制裁|条约|总统", s):
            result.add("国际政治与全球事件")
        if re.search(r"人工智能|大模型|算力|芯片|AI|数字经济", s, re.I):
            result.add("AI与数字产业")
        if re.search(r"科技|能源|核电|航天|半导体|机器人|材料|量子|新能源", s):
            result.add("科技、能源与前沿科学")
        if re.search(r"创业|融资|企业|并购|商业|上市|营收|利润|零售", s):
            result.add("创业、商业与企业竞争")
        if re.search(r"医疗|卫生|临床|疾病|生物科技|新药|医保", s):
            result.add("医疗、生命科学与公共健康")
        if re.search(r"八卦|追星|恋爱|短剧|电视剧|花边|明星绯闻|优惠券|博彩|抽奖", title):
            return set()
        return result
    if item.get("source_type") in ("primary_regulator","primary_central_bank","exchange_company") and matches(FINANCE, s):
        result.add("美股·全球金融市场")
    for label, pattern in (("国际政治与全球事件", POLITICS), ("美股·全球金融市场", FINANCE),
                           ("AI与数字产业", AI), ("科技、能源与前沿科学", SCIENCE + "|" + ENERGY),
                           ("创业、商业与企业竞争", BUSINESS),
                           ("医疗、生命科学与公共健康", HEALTH)):
        if matches(pattern, s): result.add(label)
    return result

def score(item, independent_publishers):
    s = item.get("title", "") + " " + item.get("summary", "")
    cs = countries(item)
    global_signal = matches(r"\b(?:global|worldwide|international|cross-border|world trade|supply chain|export ban|shipping|OPEC|federal reserve|imports?|exports?|trade)\b", s)
    scope = 30 if global_signal else 22 if len(cs) >= 2 else 10 if cs else 5
    if item.get("source_language") == "zh":
        material = bool(re.search(r"政策|央行|利率|通胀|股市|财报|上市|监管|法律|关税|国家|国际|贸易|出口|产业|核电|临床|制裁|金融市场", s))
        score_value = (62 if material else 24) + (10 if len(cs) >= 2 else 0)
        rating = newsworthiness(item)
        return min(100,score_value), {
            "cross_border_proxy":scope, "scale_proxy": 20 if material else 5,
            "structural_change_proxy": 15 if material else 5,
            "new_development_proxy": 10, "publisher_breadth_proxy": 0,
            "editorial_materiality_reason": "Chinese language source: native text retained",
            "editorial_noise_penalty": -rating["penalty"],
            "editorial_eligible": rating["eligible"]
        }
    systemic = matches(r"\b(?:central bank|federal reserve|interest rate|war|invasion|pandemic|financial crisis|trade agreement|national election|export ban|power grid)\b", s)
    scale = 25 if systemic else 16 if matches(FINANCE + "|" + ENERGY, s) else 8
    structural = matches(r"\b(?:law|legislation|treaty|regulation|sanction|tariff|approval|breakthrough|acquisition|merger|bankruptcy|infrastructure|ban|quota|restrict|limit)\w*", s)
    duration = 20 if structural else 10 if matches(SCIENCE + "|" + BUSINESS, s) else 5
    new = 15 if matches(ACTION, s) else 5
    # Publisher breadth is only a capped proxy; geographic independence unknown.
    breadth = min(10, max(0, independent_publishers - 1) * 3)
    editorial = newsworthiness(item)
    evidence = {"cross_border_proxy": scope, "scale_proxy": scale,
                "structural_change_proxy": duration, "new_development_proxy": new,
                "publisher_breadth_proxy": breadth,
                "editorial_materiality_reason": editorial["reason"],
                "editorial_noise_penalty": -editorial["penalty"],
                "editorial_eligible": editorial["eligible"]}
    return max(0, sum((scope, scale, duration, new, breadth)) - editorial["penalty"]), evidence

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
                     editorial_materiality_reason=evidence["editorial_materiality_reason"],
                     publisher_family=publisher(a), countries=sorted(countries(a)),
                     eligible_sections=sorted(sections(a)), related_publishers=sorted(families),
                     why_recommended="全球影响启发式；各维度保留依据，不代表事实核验")
    result = {}
    for section in SECTIONS:
        candidates = sorted((a for a in all_items if section in a["eligible_sections"]
                             and a["score_evidence"]["editorial_eligible"]
                             and a["importance_score"] >= 35),
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
    # Moving finance to the front must not consume the last three eligible
    # China/US events; front-page reporting and that fixed three-item panel
    # share one deduplicated event pool.
    china_us_events = {
        enriched[a["url"]]["event_key"]
        for a in candidates.get("中国与美国", [])
        if enriched.get(a["url"])
    }
    for section, quota in SECTIONS.items():
        available = [enriched[a["url"]] for a in candidates.get(section, []) if enriched.get(a["url"])]
        selected, families, concentration, exceptions = [], Counter(), Counter(), []
        def add(a, allow_exception=False):
            if a["url"] in used_urls or a["event_key"] in used_events: return False
            if (section == "美股·全球金融市场"
                    and a["event_key"] in china_us_events
                    and len(china_us_events - used_events) <= 3):
                return False
            cs = set(a.get("countries", [])) - {"中国", "美国"}
            overcrowded = section == "国际政治与全球事件" and any(concentration[c] >= 1 for c in cs)
            # Geographic concentration triggers a review, not an absolute veto.
            # Pass one prefers country diversity; pass two may retain a
            # substantiated event and must record the exception.
            if overcrowded and not allow_exception: return False
            if families[a["publisher_family"]] >= 2: return False
            if overcrowded:
                exceptions.append({"event": a["event_key"], "reason": "同国重要新闻集中，记录来源和必要性待复核；不自动删除事件"})
            selected.append({**a, "category": section})
            used_events.add(a["event_key"]); used_urls.add(a["url"])
            families[a["publisher_family"]] += 1
            concentration.update(cs)
            return True
        if section == "美股·全球金融市场":
            # Reserve one slot for a genuinely important primary institutional
            # release when available. Do not fill the paper with routine SEC
            # event notices or ordinary Treasury auctions merely for variety.
            for article in available:
                if article.get("source_type") in {
                    "primary_regulator", "primary_central_bank",
                    "primary_treasury", "primary_economic_data"
                } and article.get("importance_score", 0) >= 65:
                    if add(article):
                        break
        if section == "中国与美国":
            for country in ("中国", "美国"):
                if any(country in a.get("countries", []) for a in selected): continue
                for a in available:
                    if country in a.get("countries", []) and add(a): break
        for exceptional in (False, True):
            for a in available:
                if len(selected) >= quota: break
                add(a, exceptional)
        # Additional exceptional political events may exceed the normal quota.
        # Only very high-ranking distinct events qualify; never fill to a fixed
        # page count merely to make the newsletter longer.
        if section == "国际政治与全球事件":
            for article in available:
                if len(selected) >= quota + 2:
                    break
                if article["importance_score"] >= 90:
                    add(article, allow_exception=True)
        output[section] = selected
        missing = [c for c in ("中国", "美国") if not any(c in a.get("countries", []) for a in selected)] if section == "中国与美国" else []
        diagnostics[section] = {"quota": quota, "candidate_count": len(candidates.get(section, [])),
            "readable": len(available), "selected": len(selected), "missing_regions": missing,
            "shortfall": max(0, quota-len(selected)), "country_counts": dict(concentration),
            "concentration_exceptions": exceptions}
    return output, diagnostics
