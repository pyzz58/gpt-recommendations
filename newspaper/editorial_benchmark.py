"""P1 reproducible *fixture* benchmark on the actual newsroom selection path.

Not a historical replay: only five headlines have dated primary-source links.
Synthetic distractors, mixtures and duplicate variants are explicitly labeled.
This benchmark cannot estimate real-world news coverage recall.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from newsroom import prepare_pool, select_readable

DATA = Path(__file__).resolve().parent / "benchmarks" / "p1_headline_v2.json"


def load_cases(path=DATA):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    cases=data["cases"]
    if len(cases)!=50 or len({c["id"] for c in cases})!=50:
        raise ValueError("Frozen headline benchmark requires 50 unique cases")
    for case in cases:
        if case["kind"]=="historical_source_reference":
            if not case.get("primary_source_url", "").startswith("https://"):
                raise ValueError("Historical reference requires a primary URL")
            if not case.get("historical_event_date"):
                raise ValueError("Historical reference requires event date")
        elif not case["kind"].startswith("synthetic"):
            raise ValueError("Unlabelled case provenance")
    return data


def calculate_metrics(cases, selected_urls):
    """Micro-average event-level recall, event-level precision and article duplication."""
    lookup={c["url"]:c for c in cases}
    if len(lookup)!=len(cases):
        raise ValueError("URLs must be unique in frozen fixture")
    selected=[lookup[url] for url in selected_urls]
    gold={c["gold_event_id"] for c in cases if c["expected_material"]}
    included={c["gold_event_id"] for c in selected if c["expected_material"]}
    false_positive=[c for c in selected if not c["expected_material"]]
    counts=Counter(c["gold_event_id"] for c in selected)
    duplicates=sum(n-1 for n in counts.values() if n>1)
    # Precision counts the actual article slots, preventing extra copies from
    # artificially improving the metric.
    true_positive_slots=sum(1 for c in selected if c["expected_material"])-duplicates
    precision=true_positive_slots / len(selected) if selected else 0.0
    recall=len(included)/len(gold) if gold else 1.0
    return {
        "expected_material_events":len(gold),
        "selected_article_slots":len(selected),
        "selected_material_events":len(included),
        "missed_material_events":sorted(gold-included),
        "false_positive_selected_ids":[c["id"] for c in false_positive],
        "duplicate_article_slots":duplicates,
        "event_recall":round(recall,4),
        "selection_precision":round(precision,4),
        "duplicate_slot_rate":round(duplicates/len(selected),4) if selected else 0.0,
    }


def run_benchmark(data=None):
    data=data or load_cases()
    all_cases=data["cases"]
    episode_ids=sorted({c["episode"] for c in all_cases})
    scored=[]
    for episode in episode_ids:
        group=[c for c in all_cases if c["episode"]==episode]
        # Critical: gold labels, historical dates and benchmark ID are NEVER
        # passed into the selector. It sees only ordinary news metadata.
        inputs=[{key:c[key] for key in ("title","summary","source","url")}
                for c in group]
        pooled=prepare_pool(inputs,per_section=20)
        enriched={item["url"]:item for section in pooled.values() for item in section}
        selected,diagnostics=select_readable(pooled,enriched)
        urls=[item["url"] for articles in selected.values() for item in articles]
        metrics=calculate_metrics(group,urls)
        scored.append({"episode":episode,**metrics,
                       "by_section":{section:len(items) for section,items in selected.items()},
                       "section_shortfalls":{section:d["shortfall"] for section,d in diagnostics.items() if d["shortfall"]}})
    # Global weighted micro counts (never average rounded daily rates).
    exp=sum(x["expected_material_events"] for x in scored)
    tp=sum(x["selected_material_events"] for x in scored)
    slots=sum(x["selected_article_slots"] for x in scored)
    dup=sum(x["duplicate_article_slots"] for x in scored)
    fp=sum(len(x["false_positive_selected_ids"]) for x in scored)
    summary={
        "label":"SYNTHETIC_FIXTURE_WITH_FIVE_HISTORICAL_SOURCE_REFERENCES",
        "NOT_REAL_HISTORICAL_REPLAY":True,
        "case_count":len(all_cases),
        "historical_primary_source_reference_count":sum(c["kind"]=="historical_source_reference" for c in all_cases),
        "synthetic_case_count":sum(c["kind"].startswith("synthetic") for c in all_cases),
        "episode_count":len(scored),
        "expected_material_events":exp,
        "selected_material_events":tp,
        "selected_article_slots":slots,
        "false_positive_slots":fp,
        "duplicate_article_slots":dup,
        "missed_material_events":sum(len(x["missed_material_events"]) for x in scored),
        "event_recall":round(tp/exp,4) if exp else 1.0,
        "selection_precision":round((tp)/slots,4) if slots else 0.0,
        "duplicate_slot_rate":round(dup/slots,4) if slots else 0.0,
        "episodes":scored,
        "limit":"Offline headline/readability simulation; not real publication-date replay, not external coverage recall and not expert-reviewed."
    }
    return summary


def main():
    result=run_benchmark()
    location=Path("/tmp/newspaper-p1-benchmark.json")
    location.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("NEWSROOM_P1_BENCHMARK="+json.dumps({k:v for k,v in result.items() if k not in ("episodes",)},ensure_ascii=False,sort_keys=True))
    print("NEWSROOM_P1_BENCHMARK_PATH="+str(location))


if __name__=="__main__":
    main()
