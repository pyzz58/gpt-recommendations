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
    "美股市场与机构观察": 5,
    "中国与美国": 3,
    "国际政治与全球事件": 3,
    "全球宏观与金融政策": 1,
    "AI与数字产业": 1,
    "科技、能源与前沿科学": 1,
    "创业、商业与企业竞争": 1,
    "医疗、生命科学与公共健康": 1
}
COUNTRIES = {
    "中国": r"\b(?:china|chinese|beijing|shanghai|shenzhen|xi jinping)\b|中国|我国|北京|国务院|全国人大|财政部|人民银行",
    "美国": r"\b(?:united states|american|america|washington|white house|congress|pentagon|federal reserve|trump)\b|\bU\.?S\.?\b|美国|美股|美联储|纳斯达克|华尔街|标普500",
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
POLITICS = r"中国|美国|政府|外交|战争|停火|选举|制裁|军事|地震|政策|外交|议会|\b(?:election|president|government|parliament|diplomac\w*|war|ceasefire|military|sanctions?|treaty|coup|missile|invasion|earthquake|pandemic|floods?|hurricane|summit)\b"
FINANCE = r"美股|标普|纳斯达克|道琼斯|收益率|国债|美联储|人民银行|货币政策|财报|通胀|利率|金融|央行|经济|股市|基金|\b(?:federal reserve|central bank|interest rates?|inflation|gdp|treasury|bond yields?|stock market|nasdaq|s&p|earnings|financial|banking|currency|recession|unemployment|monetary|fiscal|tariffs?|imports?|exports?|trade)\b"
AI = r"人工智能|大模型|算力|机器人|智能体|芯片|\b(?:AI|artificial intelligence|LLMs?|large language model|machine learning|data cent(?:er|re)|cloud computing|cybersecurity|software|digital platform)\b"
SCIENCE = r"量子|航天|半导体|科技|突破|新能源|\b(?:quantum|physics|scientists?|researchers?|semiconductor|chip|robot\w*|spacecraft|satellite|rocket|superconduct\w*|materials science)\b"
BUSINESS = r"创业|融资|并购|收购|商业模式|企业|公司|营收|上市|产业|\b(?:startup|start-up|entrepreneur\w*|business model|venture capital|funding|series [a-f]|acquisition|merger|IPO|bankruptcy|restructuring|supply chain|retail|revenue|profit|commerciali\w*|company|companies)\b"
ENERGY = r"能源|石油|天然气|电网|核电|光伏|锂电|稀土|供应链|\b(?:energy|oil|gas|OPEC|electricity|power grid|nuclear|fusion|solar|wind power|battery|lithium|copper|rare earth|critical minerals|shipping|supply chain|food exports?|grain|export ban)\b"
HEALTH = r"医疗|医药|临床|癌症|新药|公共卫生|\b(?:health|medical|clinical|drug|vaccine|cancer|hospital|biotech|gene|protein|disease|FDA|WHO)\b"
PROMO = r"\b(?:trailer|celebrity|movie review|coupon|best deals|horoscope|sponsored content|affiliate links)\b"
ACTION = r"\b(?:announc\w*|approv\w*|enact\w*|launch\w*|cut|hike\w*|votes?|agreed|acquir\w*|report\w*|reveal\w*|signed|ban\w*|strikes?|invad\w*|deploy\w*|discover\w*|demonstrat\w*|limit\w*|restrict\w*|caps?)\b"

US_MARKET = r"\b(?:s&p 500|nasdaq|dow jones|russell 2000|wall street|nyse|us stocks?|u\.s\. stocks?|stock index|market breadth|market closing|equities|earnings|sec filing|sec (?:announc\w*|report\w*|charges?|rule\w*)|securities exchange|institutional investors?|institutional holdings?|hedge funds?|exchange traded funds?|etfs?|etf flows?|buyback|volatility|vix|10.year treasury|yield curve)\b|美股|纳斯达克|道琼斯|标普|华尔街|美国股市|机构持仓|财报|ETF资金流"
MARKET_THEME = {
    "index": r"\b(?:s&p|nasdaq|dow jones|russell|stock market|equities|vix|volatility|market breadth|index)\b|指数|大盘|标普|纳斯达克|道琼斯",
    "institution": r"\b(?:sec|nasdaq inc|exchange|13f|institutional|federal reserve|regulator|form 4)\b|监管|机构|证券交易委员会|美联储",
    "rates": r"\b(?:treasury|yields?|interest rates?|fomc|fed decision|inflation|monetary policy)\b|利率|国债|美联储|通胀",
    "earnings": r"\b(?:earnings|results|quarterly|profit|guidance|revenue|filing|10-k|10-q)\b|财报|利润|营收|业绩|季度",
    "flows": r"\b(?:etfs?|capital flows?|fund flows?|rotation|buyback|positioning|hedge funds?|breadth|institutional holdings?)\b|资金流|板块轮动|ETF|持仓|回购",
}
def market_theme(item):
    s=item.get("title","")+" "+item.get("summary","")
    for label,pattern in MARKET_THEME.items():
        if matches(pattern,s):return label
    return "other"

def matches(pattern, text):
    return bool(re.search(pattern, text, re.I))

def countries(item):
    title = item.get("title", "")
    # Title is the primary-event proxy. Incidental countries in background should
    # not turn every international article into a China/US story.
    result = set()
    for name, pattern in COUNTRIES.items():
        if name == "美国":
            if matches(pattern.replace(r"|\bU\.?S\.?\b",""), title) or re.search(r"\bU\.?S\.?\b",title):
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
    if not newsworthiness(item)["eligible"]:
        return set()
    result = set()
    if item.get('source_kind') == 'investment_opinion':
        return {'美股市场与机构观察'} if matches(US_MARKET,s) else set()
    if matches(US_MARKET, s) and (matches(r"\b(?:us|u.s.|american|nasdaq|dow jones|s&p|nyse|sec|federal reserve|fomc|wall street|etf)\b|美股|标普|纳斯达克|道琼斯|华尔街|美国|美联储|机构持仓|ETF", s) or item.get("source_type") in ("primary_exchange","primary_regulator")):
        result.add("美股市场与机构观察")
    # Dedicated American-market desks need not repeat "U.S." in titles.
    if item.get("source") in ("CNBC Markets","CNBC Investing"):
        if matches(r"\b(?:stocks?|shares|market|futures|index|equities|earnings|treasury|yield|nasdaq|dow|fed|investors?|funds?|etfs?)\b",s):
            result.add("美股市场与机构观察")
    if item.get("source_type") in ("primary_regulator","primary_exchange"):
        if matches(r"\b(?:stocks?|securities|etfs?|investors?|markets?|listings?|exchange|registrations?|filings?)\b",s):
            result.add("美股市场与机构观察")
    if countries(item) & {"中国", "美国"}: result.add("中国与美国")
    for label, pattern in (("国际政治与全球事件", POLITICS), ("全球宏观与金融政策", FINANCE),
                           ("AI与数字产业", AI), ("科技、能源与前沿科学", SCIENCE + "|" + ENERGY),
                           ("创业、商业与企业竞争", BUSINESS),
                           ("医疗、生命科学与公共健康", HEALTH)):
        if matches(pattern, s): result.add(label)
    return result

def score(item, independent_publishers):
    s = item.get("title", "") + " " + item.get("summary", "")
    cs = countries(item)
    global_signal = matches(r"全球|国际|出口限制|国际贸易|金融市场|\b(?:global|worldwide|international|cross-border|world trade|supply chain|export ban|shipping|OPEC|federal reserve|imports?|exports?|trade)\b", s)
    scope = 30 if global_signal else 22 if len(cs) >= 2 else 10 if cs else 5
    systemic = matches(r"央行|美联储|国债|制裁|法案|战争|重大|国家|监管|并购|\b(?:central bank|federal reserve|interest rate|war|invasion|pandemic|financial crisis|trade agreement|national election|export ban|power grid)\b", s)
    scale = 25 if systemic else 16 if matches(FINANCE + "|" + ENERGY, s) else 8
    structural = matches(r"发布|实施|通过|限制|批准|政策|监管|并购|创新|重大|\b(?:law|legislation|treaty|regulation|sanction|tariff|approval|breakthrough|acquisition|merger|bankruptcy|infrastructure|ban|quota|restrict|limit)\w*", s)
    duration = 20 if structural else 10 if matches(SCIENCE + "|" + BUSINESS, s) else 5
    new = 15 if matches(ACTION+r"|宣布|发布|通过|批准|出台|实施|决定|报告|上调|下调", s) else 5
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
    # Select combined China/US priorities first to preserve three distinct
    # stories; PDF and rendered front page still lead with the US market.
    selection_order=["中国与美国"]+[name for name in SECTIONS if name!="中国与美国"]
    for section in selection_order:
        quota=SECTIONS[section]
        available = [enriched[a["url"]] for a in candidates.get(section, []) if enriched.get(a["url"])]
        selected, families, concentration, exceptions = [], Counter(), Counter(), []
        def add(a, allow_exception=False):
            if a["url"] in used_urls or a["event_key"] in used_events: return False
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
        if section == "美股市场与机构观察":
            # Prefer one news event per institutional market evidence bucket.
            for theme in ("index","institution","rates","earnings","flows"):
                for a in available:
                    if len(selected)>=quota:break
                    if market_theme(a)==theme and add(a):break
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
    return {k:output.get(k,[]) for k in SECTIONS}, {k:diagnostics.get(k,{}) for k in SECTIONS}
