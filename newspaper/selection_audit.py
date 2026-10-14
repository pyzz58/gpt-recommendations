"""Selection audit: evidence of what the daily newsroom kept, rejected and missed.

This is a *within-observed-feed* coverage report, not a claim that unobserved
world events were found. Preserve metadata only; never copy news article text.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from newsroom import score, sections
from source_quality import newsworthiness

IMPORTANT_SCORE = 75
MAX_DISPLAY = 40


def make_selection_audit(incoming, candidates, selected, diagnostics=None):
    all_by_url={a.get("url"):a for a in incoming if a.get("url")}
    candidate_by_url={a["url"]:a for part in candidates.values() for a in part if a.get("url")}
    selected_by_url={a["url"]:a for part in selected.values() for a in part if a.get("url")}
    candidate_event_by_url={a["url"]:a.get("event_key") for a in candidate_by_url.values()}
    selected_events={a.get("event_key") for a in selected_by_url.values() if a.get("event_key")}
    selected_sections={a["url"]:a.get("category","") for a in selected_by_url.values()}
    # Genuine decisions from the selector, not inferred after the fact.
    # Prefer the market desk when a URL competed in multiple sections.
    per_section_decisions={
        section:details.get("candidate_decisions",[])
        for section,details in (diagnostics or {}).items()
    }
    decision_by_url={}
    for section in sorted(per_section_decisions, key=lambda x:(x!="美股·全球金融市场", x)):
        for decision in per_section_decisions[section]:
            decision_by_url.setdefault(decision["url"],{**decision,"section":section})
    reasons=Counter()
    unselected=[]
    for url,a in all_by_url.items():
        if url in selected_by_url:
            reasons["selected"]+=1
            continue
        materiality=newsworthiness(a)
        kinds=sections(a)
        value,evidence=score(a,1)
        if not materiality["eligible"]:
            reason="hard_rejected_as_low_value"
        elif not kinds:
            reason="no_editorial_section"
        elif url not in candidate_by_url:
            reason="not_in_candidate_pool_or_below_threshold"
        elif url in decision_by_url:
            reason=decision_by_url[url]["reason_code"]
        elif candidate_event_by_url[url] in selected_events:
            reason="same_cluster_event_already_selected"
        else:
            reason="candidate_not_selected_or_unreadable"
        reasons[reason]+=1
        in_pool=url in candidate_by_url
        importance=candidate_by_url[url].get("importance_score",value) if in_pool else value
        if in_pool and importance >= IMPORTANT_SCORE and reason != "same_cluster_event_already_selected":
            unselected.append({
                "url":url,
                "title":str(a.get("title") or "")[:200],
                "source":str(a.get("source") or "")[:90],
                "candidate_score":importance,
                "score_is_heuristic":True,
                "reason":reason,
                "possible_coverage_gap_only":True,
            })
    unselected.sort(key=lambda a:(-a["candidate_score"],a["url"]))
    section_health={section:{
        "pool_candidates":len(articles),
        "printed_candidates":len(selected.get(section,[])),
        "quota_shortfall":(diagnostics or {}).get(section,{}).get("shortfall"),
        "decision_reasons":dict(sorted(Counter(
            x["reason_code"] for x in per_section_decisions.get(section,[])
        ).items())),
    } for section,articles in candidates.items()}
    selected_records=[]
    for url,a in sorted(selected_by_url.items(),key=lambda kv:(kv[1].get("category",""),kv[0])):
        selected_records.append({
            "url":url,"title":str(a.get("title") or "")[:200],
            "source":str(a.get("source") or "")[:90],
            "section":selected_sections[url],
            "event_key":a.get("event_key"),
            "score":a.get("importance_score"),
            "score_evidence":a.get("score_evidence"),
            "why_recommended":a.get("why_recommended"),
        })
    return {
        "schema":1,
        "coverage_scope":"observed_RSS_items_only",
        "independent_global_major_event_recall":"NOT_MEASURED",
        "articles_observed":len(incoming),
        "distinct_observed_urls":len(all_by_url),
        "candidate_urls":len(candidate_by_url),
        "selected_urls":len(selected_by_url),
        "reasons_by_unique_url":dict(sorted(reasons.items())),
        "section_health":section_health,
        "candidate_decisions_by_section":{
            section:[
                {**decision, "title":str(candidate_by_url.get(decision["url"],{}).get("title") or "")[:200]}
                for decision in entries
            ]
            for section,entries in per_section_decisions.items()
        },
        "selection_reason_provenance":(
            "actual_selector_attempts" if any(per_section_decisions.values())
            else "fallback_posthoc_inference"
        ),
        "candidate_high_score_unselected_count":len(unselected),
        "candidate_high_score_unselected_top":unselected[:MAX_DISPLAY],
        "selected_records":selected_records,
        "selected_event_keys_unique":len(selected_events),
        "possible_event_key_repeats":max(0,len(selected_by_url)-len(selected_events)),
        "limits":[
            "High score is a heuristic, not proof an event is significant.",
            "A missing item from outside subscribed RSS feeds cannot be detected here.",
            "Individual fetch failures are recorded only as unreadable/inaccessible; HTTP vs paywall vs text length requires extractor diagnostics.",
        ],
    }


def save_selection_audit(report, output):
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    return path
