"""Evidence trail for the US-stock front page: fetch -> route -> pool -> print.

Diagnoses source availability and classification separately. Reports only
headline metadata, never full copyrighted article bodies. A quota is a
diagnostic target, not a mandate to invent or lower editorial standards.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import json
from pathlib import Path
from market_headline import market_evidence
from source_quality import newsworthiness
from newsroom import sections

MARKET_SECTION="美股·全球金融市场"
MARKET_FEED_GROUPS={"美股与投资","美联储与宏观"}
MAX_SAMPLES=12


def report_market_funnel(incoming, pool, selected, *, limits=None):
    by_url={}
    for a in incoming:
        if a.get("url"):
            by_url.setdefault(a["url"],a)
    candidate_urls={a["url"] for a in pool.get(MARKET_SECTION,[]) if a.get("url")}
    printed_urls={a["url"] for a in selected.get(MARKET_SECTION,[]) if a.get("url")}
    by_feed=defaultdict(lambda:Counter())
    reasons=Counter()
    stages=Counter()
    dropped=[]
    for url,a in by_url.items():
        source=str(a.get("source","unknown"))[:100]
        feed_category=str(a.get("category","unknown"))[:100]
        key=feed_category+" | "+source
        evidence=market_evidence(a)
        importance=newsworthiness(a)
        topical=MARKET_SECTION in sections(a)
        stats=by_feed[key]
        stats["unique_in_window"]+=1
        if feed_category in MARKET_FEED_GROUPS: stats["dedicated_finance_feed_articles"]+=1
        if evidence["eligible"]: stats["has_grounded_market_signal"]+=1
        if topical: stats["passes_market_section_routing"]+=1
        if url in candidate_urls: stats["candidate_pool"]+=1
        if url in printed_urls: stats["printed"]+=1
        reason=evidence["reason"]
        reasons[reason]+=1
        if url in printed_urls: stage="printed"
        elif url in candidate_urls: stage="pooled_not_printed"
        elif not importance["eligible"]: stage="excluded_by_low_value_filter"
        elif not topical: stage="not_market_relevant"
        else: stage="filtered_by_score_or_candidate_pool"
        stages[stage]+=1
        if stage!="printed" and (evidence["eligible"] or feed_category in MARKET_FEED_GROUPS):
            dropped.append({
                "source":source,"source_group":feed_category,
                "title":str(a.get("title",""))[:180],
                "url":url,"stage":stage,"market_reason":reason,
            })
    chosen=[{"title":str(a.get("title",""))[:180],
             "source":str(a.get("source",""))[:100],
             "url":str(a.get("url","")),
             "importance_score":a.get("importance_score")}
            for a in selected.get(MARKET_SECTION,[])]
    quota=(limits or {}).get(MARKET_SECTION,4)
    per_source=[]
    for key,counts in sorted(by_feed.items()):
        per_source.append({"feed":key,**dict(counts)})
    return {
        "schema":1,
        "target_section":MARKET_SECTION,
        "coverage_scope":"only_available_in_window_RSS_articles",
        "print_quota":quota,
        "printed":len(chosen),
        "shortfall":max(0,quota-len(chosen)),
        "total_unique_articles":len(by_url),
        "grounded_market_signal_count":sum(v["has_grounded_market_signal"] for v in by_feed.values()),
        "routed_market_count":sum(v["passes_market_section_routing"] for v in by_feed.values()),
        "candidate_pool_count":len(candidate_urls),
        "stage_counts":dict(sorted(stages.items())),
        "headline_gate_reasons":dict(sorted(reasons.items())),
        "by_feed":per_source,
        "selected_headlines":chosen,
        "nonselected_market_or_finance_feed_samples":dropped[:MAX_SAMPLES],
        "interpretation":(
            "Feed HTTP availability does not establish story coverage. "
            "Report contains ONLY RSS-observed items; missing world events "
            "and paywall extraction outcomes require independent investigation. "
            "Never pad a shortfall with generic or unrelated financial news."
        ),
    }


def save_market_funnel(report,output):
    dest=Path(output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    return dest
