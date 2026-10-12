"""Transparent news value heuristics and cross-source event grouping.

Mature open-source building blocks: scikit-learn TF-IDF and cosine similarity.
This does NOT use an LLM and is not a factual verification or investment signal.
"""
from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CATEGORY_INTEREST = {
    "全球新闻": 17,
    "美股与投资": 25,
    "美联储与宏观": 25,
    "创业与商业模式": 24,
    "AI与科技": 22,
    "医疗与科学": 21,
}
IMPACT_PATTERNS = {
    "政策或监管动作": r"\b(central bank|federal reserve|fomc|rate cut|rate hike|tariff|sanction|"
                      r"legislation|regulation|supreme court|trade agreement|government order)\b",
    "宏观和金融市场": r"\b(inflation|jobs report|employment|unemployment|gdp|treasury yields?|"
                      r"earnings|guidance|s&p 500|nasdaq|stock market|bond yields?)\b",
    "重大商业变化": r"\b(acquisition|merger|ipo|bankruptcy|funding|series [a-f]|"
                      r"product launch|layoffs?|restructuring)\b",
    "科技和医疗突破": r"\b(clinical trial|regulatory approval|fda approves?|"
                      r"breakthrough|chip|semiconductor|ai model|fusion|researchers? discover)\b",
    "全球公共事件": r"\b(election|conflict|ceasefire|earthquake|pandemic|"
                      r"climate deal|state visit|summit|peace agreement)\b",
}
NOVEL_ACTION = re.compile(
    r"\b(announc(?:e|ed|es)|approv(?:e|ed|es)|launch(?:ed|es)?|"
    r"rais(?:ed|es)|cut|hike(?:d|s)?|votes?|agreed|acquir(?:e|ed|es)|"
    r"report(?:s|ed)?|reveal(?:s|ed)?|pass(?:ed|es)|"
    r"forecast(?:s|ed)?|expand(?:s|ed)?|sign(?:ed|s)?)\b", re.I
)
STOP = {
    "that", "this", "have", "from", "with", "after", "into", "over", "under",
    "says", "said", "news", "latest", "today", "could", "would", "about",
    "will", "amid", "more", "than", "their", "2026", "2025",
}


def _tokens(title: str) -> set[str]:
    return {x for x in re.findall(r"[a-zA-Z0-9]{3,}", title.lower())
            if x not in STOP}


def _story_groups(articles: list[dict], threshold: float = 0.55) -> list[list[int]]:
    """Greedy headline grouping: conservative, imperfect paraphrase detection."""
    if not articles:
        return []
    titles = [a.get("title", "") for a in articles]
    try:
        vec = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), sublinear_tf=True
        ).fit_transform(titles)
        similarities = cosine_similarity(vec)
    except ValueError:
        return [[i] for i in range(len(articles))]
    token_sets = [_tokens(t) for t in titles]
    groups: list[list[int]] = []
    for i, article in enumerate(articles):
        closest = None
        highest = threshold
        for group_index, group in enumerate(groups):
            for j in group:
                common = len(token_sets[i] & token_sets[j])
                # Avoid grouping unrelated generic Fed / market stories.
                if common >= 3 and similarities[i, j] > highest:
                    closest = group_index
                    highest = similarities[i, j]
        if closest is None:
            groups.append([i])
        else:
            groups[closest].append(i)
    return groups


def _score(article: dict, sources: int, news_start: dt.datetime | None) -> tuple[int, str]:
    """Explanatory 0–100 *heuristic*. 30/25/20/15/10 weighting."""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    signals = [name for name, pattern in IMPACT_PATTERNS.items()
               if re.search(pattern, text, flags=re.I)]
    # Impact 0..30, high-impact cues from different areas increase the score.
    impact = min(30, len(signals) * 12)
    interest = CATEGORY_INTEREST.get(article.get("category", ""), 15)
    cross = min(20, 10 + (sources - 2) * 5) if sources >= 2 else 0
    # "Novelty" is only an indicative proxy for actions / reported data;
    # without comparing previous-day articles it is NOT genuine novelty.
    novelty = int(bool(NOVEL_ACTION.search(text))) * 8
    novelty += min(7, len(re.findall(r"\b\d+(?:\.\d+)?%?\b", text)) * 3)
    recency = 5
    date = article.get("date")
    if news_start is not None and isinstance(date, dt.datetime):
        elapsed_hours = max(0., (date - news_start.astimezone(date.tzinfo)).total_seconds()/3600)
        recency = round(10 * min(24., elapsed_hours)/24.)
    total = min(100, impact + interest + cross + novelty + recency)
    reasons = [f"栏目匹配 {interest}/25"]
    if signals:
        reasons.append("事件信号：" + "、".join(signals[:2]))
    if sources >= 2:
        reasons.append(f"{sources} 个来源报道相关主题（不代表事实核验）")
    if novelty:
        reasons.append("出现新动作或数据线索")
    reasons.append("按昨日发布时间计入")
    return total, "；".join(reasons)


def rank_and_pool(
    items: list[dict],
    *,
    pool_size: int,
    news_start: dt.datetime | None = None,
    max_per_source_first_pass: int = 3,
) -> list[dict]:
    """Keep top stories plus backup versions and avoid one outlet dominating.

    - Rank story groups; story-level score uses coverage by distinct news outlets.
    - Include a readable candidate for each story and a backup from another outlet,
      then fill extra slots with lower-value stories.
    - Do not label shared reporting as independent confirmation.
    """
    if not items or pool_size <= 0:
        return []
    # Deduplicate identical URLs, even across feeds of the same publisher.
    unique, urls = [], set()
    for a in items:
        if a.get("url") not in urls:
            urls.add(a.get("url"))
            unique.append(a)
    groups = _story_groups(unique)
    groups_with_scores = []
    for story_index, ids in enumerate(groups):
        sources = sorted({unique[i]["source"] for i in ids})
        variants = []
        for i in ids:
            article = dict(unique[i])
            score, why = _score(article, len(sources), news_start)
            article.update({
                "importance_score": score,
                "why_recommended": why,
                "story_id": story_index,
                "related_sources": sources,
            })
            variants.append(article)
        variants.sort(
            key=lambda a: (a["importance_score"], bool(a.get("summary")),
                           a.get("date") or dt.datetime.min.replace(tzinfo=dt.timezone.utc)),
            reverse=True,
        )
        groups_with_scores.append(variants)
    groups_with_scores.sort(
        key=lambda variants: variants[0]["importance_score"], reverse=True,
    )
    selected = []
    counts: dict[str, int] = defaultdict(int)
    chosen_urls = set()

    def add_article(article: dict) -> bool:
        if article["url"] in chosen_urls:
            return False
        selected.append(article)
        chosen_urls.add(article["url"])
        counts[article["source"]] += 1
        return True

    # Reserve some slots for an independently published alternative report on
    # the *same* story. Without this reservation, a large set of distinct
    # stories would consume all slots and the backup pass would never run.
    primary_slots = max(1, round(pool_size * 0.75))
    for variants in groups_with_scores:
        if len(selected) >= primary_slots:
            break
        primary = variants[0]
        if counts[primary["source"]] < max_per_source_first_pass:
            add_article(primary)
        else:
            alternate = next(
                (a for a in variants if
                 counts[a["source"]] < max_per_source_first_pass), None
            )
            if alternate:
                add_article(alternate)

    # Source-independent backups help when the first article cannot be read.
    covered_stories = {a["story_id"] for a in selected}
    for variants in groups_with_scores:
        if len(selected) >= pool_size:
            break
        if variants[0]["story_id"] not in covered_stories:
            continue
        already = {a["source"] for a in selected
                   if a["story_id"] == variants[0]["story_id"]}
        for article in variants:
            if (article["source"] not in already and
                    counts[article["source"]] < max_per_source_first_pass and
                    add_article(article)):
                break

    # If there are few alternative outlets, fill the remaining slots with the
    # next-ranked distinct events rather than making up missing articles.
    if len(selected) < pool_size:
        for variants in groups_with_scores:
            if len(selected) >= pool_size:
                break
            for article in variants:
                if (counts[article["source"]] < max_per_source_first_pass and
                        add_article(article)):
                    break

    if len(selected) < pool_size:
        for variants in groups_with_scores:
            if len(selected) >= pool_size:
                break
            for article in variants:
                if len(selected) >= pool_size:
                    break
                add_article(article)
    return selected[:pool_size]
