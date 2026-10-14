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
from market_headline import market_evidence

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
        return primary_topic_guard(item, result)
    if item.get("source_type") in ("primary_regulator","primary_central_bank","exchange_company") and matches(FINANCE, s):
        result.add("美股·全球金融市场")
    for label, pattern in (("国际政治与全球事件", POLITICS), ("美股·全球金融市场", FINANCE),
                           ("AI与数字产业", AI), ("科技、能源与前沿科学", SCIENCE + "|" + ENERGY),
                           ("创业、商业与企业竞争", BUSINESS),
                           ("医疗、生命科学与公共健康", HEALTH)):
        if matches(pattern, s): result.add(label)
    if market_evidence(item)["eligible"]:
        result.add("美股·全球金融市场")
    return primary_topic_guard(item, result)


# Title-level topical evidence is intentionally stricter than generic summary
# keywords. A war mentioning "energy" is not a science breakthrough, and
# "inflation in India" is not a US equities headline.
US_MARKET_HEADLINE = (
    r"\b(?:wall street|nasdaq|s&p\s*500|dow jones|dow industrial|"
    r"federal reserve|fomc|fed|u\.?s\.?\s+(?:stocks?|equities|shares?|"
    r"treasury|bond|inflation|cpi|gdp|jobs|unemployment|rate|"
    r"markets?|economic|earnings)|american\s+(?:stocks?|markets?|"
    r"economy)|sec\s+(?:charges?|approves?|rules?|filing)|"
    r"stock\s+market|stock\s+indexes?|stock\s+futures?)\b"
)
US_MARKET_ZH = r"美股|美联储|纳斯达克|纳指|标普\s*500|道琼斯|道指|美国国债|美债|华尔街|美国(?:股市|通胀|就业|利率|经济)"
TECHNICAL_HEADLINE = (
    r"\b(?:quantum|semiconductor|microchips?|chipmaking|"
    r"nuclear fusion|fusion reactor|superconduct\w*|robot\w*|"
    r"spacecraft|satellite|rocket|scientific discovery|"
    r"battery technolog\w*|lithium extraction|solar technolog\w*|"
    r"researchers? (?:discover|develop|demonstrate)|"
    r"scientists? (?:discover|develop|demonstrate))\b"
)
TECHNICAL_ZH = r"量子|半导体|芯片|核聚变|超导|机器人|航天|卫星|科技突破|科研突破|新能源技术|电池技术"
ENTERPRISE_HEADLINE = (
    r"\b(?:startups?|start-ups?|entrepreneur\w*|venture capital|"
    r"funding round|raises? \$|merger|acquisition|acquires?|"
    r"bankruptcy|restructur\w*|ipo|initial public offering|"
    r"earnings|revenue|profit|business model|"
    r"(?:company|companies|business(?:es)?) (?:reports?|launches?|"
    r"announces?|buys?|cuts?|raises?|acquires?|merges?|files?))\b"
)
ENTERPRISE_ZH = r"创业|初创|融资|并购|收购|上市|财报|营收|利润|企业重组|商业模式|破产"


def primary_topic_guard(item, labels):
    """Require a defensible title/primary-source connection for specialized desks.

    This is a simple deterministic eligibility guard, not a second scoring
    service. Country and international reporting remain broad, so important
    news can still be selected in their proper sections.
    """
    title = str(item.get("title", ""))
    summary = str(item.get("summary", ""))
    url = str(item.get("url", "")).lower()
    keep = set(labels)
    market = market_evidence(item)["eligible"]
    if not market:
        keep.discard("美股·全球金融市场")
    # A macro forecast that refers to a war only as an economic backdrop
    # is not itself a new diplomatic or military development.
    if (re.search(r"\b(?:IMF|international monetary fund|world bank|OECD)\b", title, re.I)
            and re.search(r"\b(?:economic|slowdown|growth|outlook|financial|debt|jobs|employment|share crash|market stability)\b", title, re.I)
            and not re.search(r"\b(?:election|ceasefire agreed|treaty signed|sanctions imposed|military strike|government approves|war declared)\b", title, re.I)):
        keep.discard("国际政治与全球事件")
    if not (matches(TECHNICAL_HEADLINE, title) or
            re.search(TECHNICAL_ZH, title)):
        keep.discard("科技、能源与前沿科学")
    if not (matches(ENTERPRISE_HEADLINE, title) or
            re.search(ENTERPRISE_ZH, title)):
        keep.discard("创业、商业与企业竞争")
    return keep

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


_COMMON_TITLE_WORDS = {
    "the", "and", "for", "from", "after", "with", "that", "will",
    "says", "said", "what", "could", "would", "over", "into", "than",
    "more", "this", "new", "about", "against", "amid", "how", "why"
}


def near_duplicate_titles(a, b):
    """Conservative same-actor/same-topic headline check alongside event IDs."""
    def words(title):
        normalized = re.sub(r"\bregulat(?:e|es|ed|ion|ions|ory|ions?)\b",
                            "regulat", title.lower())
        aliases = {
            "ukrainian": "ukraine", "russian": "russia",
            "american": "america", "announced": "announce",
            "reported": "report", "reports": "report",
            "strikes": "strike", "striking": "strike",
        }
        return {aliases.get(w, w) for w in re.findall(r"[a-z]{2,}", normalized)
                if (w not in _COMMON_TITLE_WORDS and len(w) > 2) or w == "ai"}
    # Distinct explicitly stated magnitudes distinguish material decisions.
    quantities_a = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:basis points?|bps|percentage points?|%)", a.lower()))
    quantities_b = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:basis points?|bps|percentage points?|%)", b.lower()))
    if quantities_a and quantities_b and quantities_a.isdisjoint(quantities_b):
        return False
    first, second = words(a), words(b)
    if min(len(first), len(second)) < 4:
        return _high_confidence_same_event(a, b)
    shared = len(first & second)
    generic_shared = {"china","government","announces","announce","export",
                      "federal","reserve","the","policy","new","rules","us"}
    event_specific = (first & second) - generic_shared
    exact_word_overlap = bool(event_specific) and (
        shared >= 4 and shared / min(len(first), len(second)) >= 0.60
        or shared >= 5 and shared / min(len(first), len(second)) >= 0.50
    )
    return exact_word_overlap or _high_confidence_same_event(a, b)


def _high_confidence_same_event(first_title, second_title):
    """Narrow editorial paraphrase dedup with actor, action and object anchors.

    Avoid general embeddings: two different Fed decisions or two China
    announcements must NOT be merged merely because they share an institution.
    """
    replacements = [
        (r"\b(?:u\.?s\.? )?federal reserve\b", "fed"),
        (r"\bworld health organization\b", "who"),
        (r"\beuropean (?:union )?council\b", "eu_council"),
        (r"\b(?:target )?federal funds rate\b", "policy_rate"),
        (r"\bbenchmark interest rate\b", "policy_rate"),
        (r"\bhalf a percentage point\b", "50bps"),
        (r"\b50 basis points\b", "50bps"),
        (r"\bspot bitcoin exchange traded products\b", "bitcoin_etp"),
        (r"\bbitcoin spot exchange products\b", "bitcoin_etp"),
        (r"\bspot bitcoin exchange products\b", "bitcoin_etp"),
        (r"\bartificial intelligence\b", "ai"),
        (r"\bsickle cell (?:disease|patients)\b", "sickle_cell"),
        (r"\bgenome editing\b", ""),
        (r"\bbanking|banks\b", "bank"),
        (r"\bplatforms\b", "platform"),
        (r"\bcontrols\b", "control"),
        (r"\bexports\b", "export"),
        (r"\btariffs\b", "tariff"),
        (r"\bregulations\b", "regulation"),
        (r"\b(?:approves?|approved|approval|allows?|clears?)\b", "approve"),
        (r"\b(?:cuts?|lowers?|reduced|reduces?)\b", "cut"),
        (r"\b(?:announces?|announced|details)\b", "announce"),
        (r"\b(?:proposes?|proposed)\b", "propose"),
        (r"\b(?:declares?|characterizes?)\b", "declare"),
        (r"\b(?:issues? .*? decision|decides?)\b", "decide"),
        (r"\b(?:outlines?|outlined)\b", "outline"),
    ]
    noise = {
        "the","new","major","national","nationwide","global","final",
        "first","that","and","with","from","under","after","on","for",
        "at","in","a","an","of","as","to","into","by","rules",
        "requirement","requirements","government","the","its","affecting",
    }
    actors = {"fed","sec","who","eu_council","fda","china","us",
              "supreme","russia","ukraine","microsoft","nvidia"}
    actions = {"approve","cut","announce","propose","declare","decide","outline"}
    generic = actors | actions | {"bank","act","policy","regulation",
                                  "trade","law","product","new","system",
                                  "export","tariff","control","rate"}
    def terms(title):
        value = title.lower()
        for pattern,replacement in replacements:
            value = re.sub(pattern,replacement,value)
        result = {w for w in re.findall(r"[a-z_]+|\d+(?:bps|%)?",value)
                  if len(w)>=2 and w not in noise}
        return result
    a,b=terms(first_title),terms(second_title)
    common=a & b
    if not (common & actors) or not (common & actions):
        return False
    if not common - generic:
        return False
    nums_a={x for x in a if re.search(r"\d",x)}
    nums_b={x for x in b if re.search(r"\d",x)}
    if nums_a and nums_b and not (nums_a & nums_b):
        return False
    return len(common)>=3 and len(common)/max(1,min(len(a),len(b)))>=0.60


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
            # TF-IDF alone misses some different-worded titles from the same
            # speaker and announcement; avoid obvious repeated editorial slots.
            if any(near_duplicate_titles(str(a.get("title", "")),
                                         str(old.get("title", "")))
                   for arr in output.values() for old in arr):
                return False
            if any(near_duplicate_titles(str(a.get("title", "")),
                                         str(old.get("title", "")))
                   for old in selected):
                return False
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
