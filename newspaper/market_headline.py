"""Source-aware but conservative US-equities news eligibility.

A connected feed is not an endorsement. Only a material, headline-grounded
connection to the US securities market qualifies a story for the front page.
This does NOT score importance or confirm a headline is factually correct.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse

US_MARKET = re.compile(
    r"\b(?:wall street|s&p\s*500|nasdaq(?:\s*100)?|nyse|dow jones|"
    r"dow industrials?|u\.?s\.?\s+(?:stocks?|equities|shares?|"
    r"markets?|stock market|treasur(?:y|ies)|bond yields?|"
    r"government bonds?|inflation|cpi|gdp|jobs|payrolls|unemployment|"
    r"interest rates?|economic data|earnings)|american (?:stocks?|"
    r"equities|markets?|treasur(?:y|ies)))\b", re.I)
FED = re.compile(r"\b(?:federal reserve|fomc|fed)\b", re.I)
SEC = re.compile(r"\b(?:sec|securities and exchange commission)\b", re.I)
POLICY_ACTION = re.compile(
    r"\b(?:policy|rates?|inflation|fomc|monetary|balance sheet|"
    r"liquidity|bank capital|supervision|banking regulation|"
    r"treasur(?:y|ies)|securities|filing|disclosure|rules?|"
    r"enforcement|charges?|fraud|lawsuit|settlement|approve[ds]?|adopts?)\b", re.I)
STOCK_IMPACT = re.compile(
    r"\b(?:stocks?|shares?|equities|market|futures|index|indices|"
    r"yields?|bond|treasur(?:y|ies)|quarterly earnings|"
    r"earnings|revenue|profit|guidance|dividend|buyback|"
    r"ipo|takeover|acquisition|merger|price target|"
    r"analyst upgrades?|analyst downgrades?|downgrades?|upgrades?)\b", re.I)
MATERIAL_COMPANY = re.compile(
    r"\b(?:quarterly|earnings|revenue|profits?|forecast|"
    r"guidance|dividends?|buybacks?|stock|stocks|shares?|"
    r"ipo|takeover|acquisition|merger|acquires?|"
    r"upgrades?|downgrades?|price target|market cap|"
    r"shareholders?)\b", re.I)
US_ISSUERS = re.compile(
    r"\b(?:nvidia|apple|microsoft|alphabet|google|meta platforms|"
    r"tesla|amazon|oracle|palantir|broadcom|amd|intel|"
    r"berkshire hathaway|jpmorgan|j\.?p\.?\s*morgan|"
    r"goldman sachs|morgan stanley|bank of america|"
    r"walmart|costco|exxon mobil|chevron|eli lilly|"
    r"unitedhealth|boeing|netflix|salesforce|"
    r"micron technology|qualcomm|uber|airbnb|"
    r"blackrock|citigroup|wells fargo)\b", re.I)
MARKET_SPECIFIC_FEEDS = {"CNBC Markets", "CNBC Investing"}
# An explicit foreign-equity lead is not a US-stock story just because it
# mentions a forthcoming US economic indicator in the background.
FOREIGN_EQUITIES_LEAD = re.compile(
    r"^\s*(?:ftse\s*100|european stocks?|european shares?|"
    r"europe stocks?|eurozone stocks?|uk stocks?|london stocks?|"
    r"japanese stocks?|hong kong stocks?|chinese stocks?)\b", re.I)
US_EQUITIES_LEAD = re.compile(
    r"\b(?:wall street|u\.?s\.?\s+(?:stocks?|equities|shares?|markets?)|"
    r"s&p\s*500|nasdaq(?:\s*100)?|dow jones|nyse)\b", re.I)
OPINION_LEAD = re.compile(r"^\s*(?:opinion|op-ed|editorial|column)\s*:", re.I)
# Author-owned CNBC/portfolio recommendations are not independent events.
# Explicitly named third-party analyst changes can remain market news.
EDITORIAL_STOCK_PICK = re.compile(
    r"^\s*(?:we(?:'|’)?re\s+(?:upgrading|downgrading|buying|selling)|"
    r"our\s+(?:top\s+)?(?:stock\s+)?picks?\b|"
    r"why\s+we(?:'|’)?re\s+(?:buying|selling)|"
    r"\d+\s+stocks?\s+to\s+buy\b)", re.I)
MARKET_RESEARCH = re.compile(
    r"\b(?:goldman sachs|j\.?p\.?\s*morgan|bank of america|"
    r"morgan stanley|citigroup|ubs|barclays)\b.*"
    r"\b(?:rates?|upgrades?|downgrades?|price target|"
    r"revises?|raises?|lowers?|cuts?)\b", re.I)


def _official_domain(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith("." + suffix)


def market_evidence(item: dict) -> dict:
    """Return a reason tag for front-page eligibility; never use article body."""
    title = str(item.get("title") or "")
    summary = str(item.get("summary") or "")
    source = str(item.get("source") or "")
    source_type = str(item.get("source_type") or "")
    language = str(item.get("source_language") or "en")
    host = (urlparse(str(item.get("url") or "")).hostname or "").lower()

    if OPINION_LEAD.search(title):
        return {"eligible": False, "reason": "opinion_not_factual_market_report"}
    if EDITORIAL_STOCK_PICK.search(title):
        return {"eligible": False, "reason": "publisher_stock_pick_not_material_market_event"}
    if FOREIGN_EQUITIES_LEAD.search(title) and not US_EQUITIES_LEAD.search(title):
        return {"eligible": False, "reason": "non_us_market_primary_subject"}

    if language == "zh":
        # Exclude generic Chinese/HK equities unless clear US market involvement.
        if re.search(r"美股|纳指|纳斯达克|标普\s*500|道指|道琼斯|华尔街|"
                     r"美联储|美国国债|美债|美国(?:股市|资本市场|通胀|就业|利率|经济)|"
                     r"在美上市|纽交所", title):
            return {"eligible": True, "reason": "chinese_us_market_headline"}
        return {"eligible": False, "reason": "no_us_market_headline_anchor"}

    if US_MARKET.search(title):
        # A venue name in an unrelated press item is insufficient.
        if re.search(r"\b(?:nasdaq|nyse)\b",title,re.I) and not (STOCK_IMPACT.search(title) or POLICY_ACTION.search(title)):
            return {"eligible": False, "reason": "exchange_name_without_market_development"}
        return {"eligible": True, "reason": "explicit_us_market_headline"}

    if FED.search(title) and POLICY_ACTION.search(title + " " + summary):
        return {"eligible": True, "reason": "fed_monetary_or_banking_action"}

    if (source_type in {"primary_regulator","primary_central_bank","primary_treasury",
                        "primary_economic_data"}
            and ((_official_domain(host,"sec.gov") and re.search(
                r"\b(?:securities|trading|investment|disclosure|enforcement|"
                r"charges?|fraud|regulation|rule|rules|funds?|market|ipo|"
                r"settlement|listing)\b",title,re.I))
                 or (_official_domain(host,"federalreserve.gov")
                     and POLICY_ACTION.search(title)))):
        return {"eligible": True, "reason": "verified_us_primary_market_institution"}

    # CNBC's dedicated *market* desks may cover issuers beyond a fixed
    # company-name list, but must show a financial development in the title.
    if source in MARKET_SPECIFIC_FEEDS and STOCK_IMPACT.search(title):
        return {"eligible": True, "reason": "dedicated_market_feed_with_financial_headline"}

    # Material US-listed corporate disclosure, including coverage surfaced
    # through a technology or business feed. A new gadget alone does not pass.
    if (US_ISSUERS.search(title) and MATERIAL_COMPANY.search(title)
            and (STOCK_IMPACT.search(title) or MARKET_RESEARCH.search(title))):
        return {"eligible": True, "reason": "us_issuer_material_financial_development"}

    if re.search(r"\b(?:nasdaq|nyse)\s*:\s*[a-z]{1,6}\b", title, re.I) and MATERIAL_COMPANY.search(title):
        return {"eligible": True, "reason": "exchange_ticker_and_material_action"}

    return {"eligible": False, "reason": "no_verifiable_us_equities_or_market_event_anchor"}
