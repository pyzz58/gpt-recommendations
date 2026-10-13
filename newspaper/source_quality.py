"""Editorial materiality gate before ranking; low-value headlines do not win by keywords.

Inspired by newsroom event-first filtering and RAG grounding patterns. Nothing in
this module asserts that articles are true, only whether they merit review.
"""
from __future__ import annotations
import re

# Obvious advertisements / entertainment clips should not spend article slots.
# Apply to the HEADLINE, not entire article: significant finance/policy stories
# often mention celebrities or entertainment as incidental context.
HARD = re.compile(
    r"\b(?:sponsored|advertorial|paid partnership|promo code|coupon codes?|"
    r"horoscope|astrology|celebrity gossip|dating rumours?|dating rumors?|"
    r"red carpet|movie review|film review|trailer|watch the trailer|"
    r"streaming guide|best deals? (?:on|for)|buy now|product roundup|"
    r"football scores?|soccer scores?|nfl highlights?|nba highlights?|"
    r"fantasy football|recipe of the day|lifestyle tips?)\b",
    re.I,
)
SOFT = re.compile(
    r"\b(?:celebrit(?:y|ies)|pop star|influencer|red carpet|hollywood|"
    r"reality tv|viral video|social media feud|rumours?|rumors?|"
    r"fashion week|wedding|divorce|dating|box office|"
    r"gaming tips?|video game reviews?|"
    r"launches? (?:a |an )?(?:new )?(?:ai |mobile |smart )?(?:app|gadget|phone|tool)|"
    r"top \d+ (?:gadgets|apps|shows|movies)|"
    r"local (?:festival|concert|fair)|"
    r"best (?:phones?|headphones?|shoes?|restaurants?|smartwatches?))\b",
    re.I,
)
# Strict exceptions for genuinely consequential developments, not generic
# mentions of 'global', 'AI', 'investment', 'revenue' or 'company'.
MATERIAL = re.compile(
    r"\b(?:central bank|federal reserve|monetary policy|"
    r"interest rates?|inflation|unemployment|gdp|"
    r"government|congress|parliament|supreme court|"
    r"regulators?|regulation|legislation|sanctions?|tariffs?|"
    r"import bans?|export controls?|antitrust|lawsuits?|"
    r"acquisitions?|mergers?|bankruptc\w*|"
    r"public health emergency|clinical trials?|fda approv\w*|"
    r"treaty|ceasefire|conflict|missile|invasion|"
    r"critical infrastructure|grid outage|"
    r"chip export|semiconductor ban|national security)\b",
    re.I,
)
LOW_VALUE = re.compile(
    r"\b(?:opinion:|review:|what to watch|how to|"
    r"everything you need to know|here's why|"
    r"you won't believe|viral|"
    r"tips (?:to|for)|best \d+|"
    r"product teaser|"
    r"company unveils (?:new )?(?:feature|app|gadget))\b",
    re.I,
)


def newsworthiness(item: dict) -> dict:
    """Transparent negative signals; only unambiguously trivial items are excluded."""
    title = str(item.get("title") or "")
    if re.search(r"明星八卦|明星恋情|优惠券|广告推广|明星穿搭|新剧预告|福利视频|星座运势|游戏攻略",title):
        return {"eligible":False,"penalty":100,"reason":"chinese_entertainment_or_advertising"}
    if re.search(r"抽奖活动|限时优惠|新品种草|明星同款|网红探店|带货直播",title):
        return {"eligible":True,"penalty":42,"reason":"chinese_promotional_noise"}
    if HARD.search(title):
        return {"eligible": False, "penalty": 100,
                "reason": "hard_advertising_entertainment_or_sports"}
    contextual = bool(MATERIAL.search(title))
    if SOFT.search(title):
        return {"eligible": True, "penalty": 0 if contextual else 42,
                "reason": "substantive_public_event" if contextual else "soft_lifestyle_or_product_noise"}
    if LOW_VALUE.search(title):
        return {"eligible": True, "penalty": 0 if contextual else 22,
                "reason": "substantive_public_event" if contextual else "low_information_or_clickbait"}
    return {"eligible": True, "penalty": 0, "reason": "candidate_for_further_review"}
