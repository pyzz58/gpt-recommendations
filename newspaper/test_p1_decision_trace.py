"""P1 true selector decision traces; actual sourced headlines, synthetic metadata."""
import json
from pathlib import Path
import unittest
from newsroom import SECTIONS, select_readable
from market_funnel import report_market_funnel
from selection_audit import make_selection_audit

MARKET="美股·全球金融市场"
SNAPSHOT=Path(__file__).resolve().parent/"benchmarks"/"p1_market_candidate_trace_v1.json"


def sample():
    fixture=json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert fixture["schema"]==1
    records=[]
    for row in fixture["market_candidates"]:
        records.append({
            "title":row["title"],
            "summary":row["title"],
            "url":row["url"],
            "source":row["source"],
            "source_language":"en",
            "source_type":"financial_media",
            "category":"美股与投资",
            "importance_score":row["importance_score"],
            "event_key":row["test_event_key"],
            "publisher_family":row["publisher_family"],
            "countries":["美国"],
        })
    return fixture,records


def select(records,candidates=None,enriched=None):
    arr=records if candidates is None else candidates
    pool={MARKET:arr,"中国与美国":[]}
    env={x["url"]:x for x in arr} if enriched is None else enriched
    return select_readable(pool,env),pool,env


class P1DecisionTraceTests(unittest.TestCase):
    def test_frozen_market_titles_keep_pretrace_selection_and_report_cap(self):
        fixture,records=sample()
        (chosen,diag),pool,env=select(records)
        self.assertEqual([x["url"] for x in chosen[MARKET]],fixture["expected_prechange_urls"])
        self.assertEqual(diag[MARKET]["quota"],4)
        self.assertEqual(diag[MARKET]["shortfall"],2)
        decisions={x["url"]:x for x in diag[MARKET]["candidate_decisions"]}
        self.assertEqual([decisions[u]["reason_code"] for u in fixture["expected_prechange_urls"]],
                         ["selected","selected"])
        blocked=decisions[records[2]["url"]]
        self.assertEqual(blocked["reason_code"],"publisher_family_cap_two")
        self.assertEqual(blocked["importance_score"],44)
        self.assertTrue(blocked["readable"])
        self.assertIsNone(blocked["blocked_by_url"])
        report=report_market_funnel(records,pool,chosen,diagnostics=diag)
        self.assertEqual(report["candidate_pool_count"],3)
        self.assertEqual(report["market_section_selector_reasons"]["publisher_family_cap_two"],1)
        self.assertEqual(report["printed"],2)
        rejected=next(x for x in report["nonselected_market_or_finance_feed_samples"]
                      if x["url"]==records[2]["url"])
        self.assertEqual(rejected["selector_reason"],"publisher_family_cap_two")
        audit=make_selection_audit(records,pool,chosen,diag)
        self.assertEqual(audit["selection_reason_provenance"],"actual_selector_attempts")
        self.assertEqual(audit["reasons_by_unique_url"].get("publisher_family_cap_two"),1)
        self.assertEqual(audit["section_health"][MARKET]["decision_reasons"]["selected"],2)
        self.assertNotIn("reading_en",json.dumps(audit))

    def test_unreadable_candidate_is_not_reported_as_publisher_cap(self):
        _,records=sample()
        env={row["url"]:row for row in records}
        env[records[2]["url"]]=None
        (chosen,diag),pool,_=select(records,enriched=env)
        self.assertEqual(len(chosen[MARKET]),2)
        reason={x["url"]:x for x in diag[MARKET]["candidate_decisions"]}
        self.assertEqual(reason[records[2]["url"]]["reason_code"],
                         "article_unreadable_or_inaccessible")

    def test_quota_filled_is_distinct_from_rejection(self):
        _,records=sample()
        # Four independent article families all admissible, plus one not visited.
        allrows=[]
        for i in range(5):
            row={**records[i%len(records)],"url":f"https://sample.example/news-{i}",
                 "event_key":f"independent-{i}","publisher_family":f"pub{i}",
                 "title":f"Distinct US-market financial report {i}"}
            allrows.append(row)
        (chosen,diag),_,_=select(allrows)
        self.assertEqual(len(chosen[MARKET]),SECTIONS[MARKET])
        reasons=[r["reason_code"] for r in diag[MARKET]["candidate_decisions"]]
        self.assertEqual(reasons,["selected"]*4+["section_quota_full_not_attempted"])

    def test_same_event_rejected_and_blocker_identified(self):
        _,records=sample()
        duplicate={**records[0],
                   "url":"https://different.example/another-reprint",
                   "publisher_family":"different", "title":records[0]["title"]}
        (chosen,diag),_,_=select([records[0],duplicate])
        self.assertEqual(len(chosen[MARKET]),1)
        dec=diag[MARKET]["candidate_decisions"][1]
        self.assertIn(dec["reason_code"],
                      ("event_selected_same_section","near_duplicate_same_section"))
        self.assertEqual(dec["blocked_by_url"],records[0]["url"])

    def test_second_pass_geographic_exception_clears_false_rejection(self):
        _,records=sample()
        # Two distinct UK developments: first pass blocks second, second pass
        # explicitly allows a substantiated concentration exception.
        a={**records[0],"url":"https://a.example/one","event_key":"a",
           "title":"Britain announces new defence procurement policy",
           "publisher_family":"a","countries":["英国"],"importance_score":75}
        b={**records[1],"url":"https://b.example/two","event_key":"b",
           "title":"UK government announces separate railway construction plan",
           "publisher_family":"b","countries":["英国"],"importance_score":71}
        chosen,diag=select_readable({"国际政治与全球事件":[a,b]},
                                    {a["url"]:a,b["url"]:b})
        self.assertEqual(len(chosen["国际政治与全球事件"]),2)
        self.assertEqual([d["reason_code"] for d in diag["国际政治与全球事件"]["candidate_decisions"]],
                         ["selected","selected"])


if __name__=="__main__":
    unittest.main()
