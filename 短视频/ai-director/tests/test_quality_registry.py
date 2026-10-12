"""Quality-phase master ledger tests; metadata only, no private scripts or APIs."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "quality-optimization"))
import quality_registry as q


class QualityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(q.SOURCE.read_text("utf-8"))

    def test_authoritative_registry_and_generated_board_are_synchronized(self):
        report = q.validate(self.data)
        self.assertEqual(report["total"], 35)
        self.assertEqual(report["stages"],
                         {"now_screenwriter": 11, "now_director": 14, "future_dept": 10})
        self.assertEqual(report["complete"], 0)
        self.assertEqual(report["new_paid_requests"], 0)
        self.assertEqual(q.BOARD.read_text("utf-8"), q.render(self.data))
        self.assertIn("QO-W01", q.BOARD.read_text("utf-8"))
        self.assertIn("QO-F10", q.BOARD.read_text("utf-8"))

    def test_cannot_remove_or_recycle_historical_issue_identifiers(self):
        d = deepcopy(self.data)
        d["items"].pop()
        with self.assertRaisesRegex(q.QualityLedgerError, "EXISTING_ID_REMOVED"):
            q.validate(d)
        d = deepcopy(self.data)
        d["items"][1]["id"] = d["items"][0]["id"]
        with self.assertRaisesRegex(q.QualityLedgerError, "DUPLICATE"):
            q.validate(d)

    def test_dependency_graph_has_no_unknown_or_cyclic_reference(self):
        d = deepcopy(self.data)
        d["items"][0]["depends_on"] = ["QO-Z99"]
        with self.assertRaisesRegex(q.QualityLedgerError, "DEPENDENCY_INVALID"):
            q.validate(d)
        d = deepcopy(self.data)
        d["items"][0]["depends_on"] = ["QO-D01"]
        with self.assertRaisesRegex(q.QualityLedgerError, "CYCLIC_DEPENDENCY"):
            q.validate(d)

    def test_cannot_mark_done_without_real_evidence_or_history(self):
        d = deepcopy(self.data)
        d["items"][0]["status"] = "complete"
        with self.assertRaisesRegex(q.QualityLedgerError, "STATUS_HISTORY_INVALID"):
            q.validate(d)
        d["items"][0]["history"].append({
            "date": "2026-10-13", "status": "complete",
            "note": "假装已达到专业水平，实际上没有经过独立质量测试",
            "evidence_ref": "https://github.com/pyzz58/gpt-recommendations/pull/21"
        })
        with self.assertRaisesRegex(q.QualityLedgerError, "FALSE_DONE_WITHOUT_EVIDENCE"):
            q.validate(d)

    def test_code_checks_alone_cannot_close_director_without_real_media(self):
        d = deepcopy(self.data)
        row = next(x for x in d["items"] if x["id"] == "QO-D01")
        row["status"] = "complete"
        row["history"].append({
            "date": "2026-10-13", "status": "complete",
            "note": "假设结构及独立创作审核通过，但没有可验证的真实视频样本",
            "evidence_ref": "https://github.com/pyzz58/gpt-recommendations/pull/21"
        })
        row["evidence"].update({
            "implementation_pr": "https://github.com/pyzz58/gpt-recommendations/pull/21",
            "commit_sha": "a" * 40,
            "automated_test": "tests/test_director_v2.py::test_example",
            "independent_review": "independent screenplay and director comparison report",
            "closure_note": "此处只是合成测试样本用于验证结构和门禁判定逻辑，实际没有产生任何真实视频，不能称作完成真人媒体验收",
            "closed_on": "2026-10-13",
        })
        with self.assertRaisesRegex(q.QualityLedgerError, "MEDIA_DEPARTMENT_NEEDS_REAL_MEDIA"):
            q.validate(d)

    def test_dependent_issue_cannot_be_closed_before_prerequisites(self):
        d = deepcopy(self.data)
        row = next(x for x in d["items"] if x["id"] == "QO-W02")
        row["status"] = "complete"
        row["history"].append({
            "date": "2026-10-13", "status": "complete",
            "note": "本测试假造形式上完整的证据，以便验证上游关键问题未关闭时的依赖门禁",
            "evidence_ref": "https://github.com/pyzz58/gpt-recommendations/pull/23"
        })
        row["evidence"].update({
            "implementation_pr": "https://github.com/pyzz58/gpt-recommendations/pull/23",
            "commit_sha": "a" * 40,
            "automated_test": "tests/test_quality_registry.py::test_dependent",
            "independent_review": "independent documented synthetic specialist review",
            "closure_note": "这是形式合法的单元测试模拟条目，实际并未完成专业质量复核和上游编剧问题关闭",
            "closed_on": "2026-10-13",
        })
        with self.assertRaisesRegex(q.QualityLedgerError, "DEPENDENCY_NOT_CLOSED"):
            q.validate(d)

    def test_future_unreviewed_stage_not_marked_progress_or_done(self):
        d = deepcopy(self.data)
        row = next(x for x in d["items"] if x["id"] == "QO-F01")
        row["status"] = "in_progress"
        row["history"].append({
            "date": "2026-10-13", "status": "in_progress",
            "note": "开始按专业标准审核尚未检查过的未来部门，目前无独立审查证据",
            "evidence_ref": ""
        })
        with self.assertRaisesRegex(q.QualityLedgerError, "FUTURE_NEEDS_PROFESSIONAL_AUDIT"):
            q.validate(d)

    def test_preserve_previous_closed_history_when_reopening(self):
        d = deepcopy(self.data)
        row = next(x for x in d["items"] if x["id"] == "QO-W01")
        row["history"].append({
            "date": "2026-10-14", "status": row["status"],
            "note": "补充新的公开合成案例，问题仍未完成完整的职业级质量验收",
            "evidence_ref": "https://github.com/pyzz58/gpt-recommendations/pull/26"
        })
        self.assertEqual(q.validate(d)["complete"], 0)
        self.assertIn("2026-10-14:" + row["status"], q.render(d))


if __name__ == "__main__":
    unittest.main()
