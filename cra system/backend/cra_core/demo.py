"""Execute a synthetic engineering scenario; no external calls or real data."""
import json
from pathlib import Path
from .issues import Action, Issue, confirm_pd_reported, make_snapshot, previsit_selection
from .laboratory import LabRecord, compare_fields


def main():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "examples/synthetic_visit.json").read_text(encoding="utf-8"))
    issues = [Issue(**{**item, "actions": [Action(**action) for action in item["actions"]]}) for item in data["issues"]]
    snapshot = make_snapshot(issues, {"reviewed": "DEMO fields only", "unverified": ["medical assessment"]})
    letter = previsit_selection(issues, data["selected_previsit_issue_ids"])
    assert len(letter) == 2 and len(issues) == 3
    confirm_pd_reported(issues[0].actions[0], "合成用户确认：已上报", "DEMO-CRA")
    assert issues[0].actions[0].status == "completed"
    assert not issues[0].complete
    assert '"status":"open"' in snapshot.content_json
    common = dict(site="DEMO-SITE", subject="DEMO-SUBJECT", visit="DEMO-V1",
                  analyte="DEMO-ANALYTE", specimen="DEMO-SPECIMEN",
                  collected_at="2026-01-01", repeat_instance="initial",
                  unit="DEMO-UNIT", report_revision="1")
    result = compare_fields(LabRecord(value="12.0", **common), LabRecord(value="12", **common))
    assert result["status"] == "field_agreement"
    print(json.dumps({
        "mode": "synthetic_engineering_example_only",
        "full_carryover_count": len(issues),
        "selected_letter_count": len(letter),
        "pd_reporting": issues[0].actions[0].status,
        "edc_correction": issues[0].actions[1].status,
        "whole_issue_complete": issues[0].complete,
        "historical_snapshot_retained": True,
        "lab_result": result,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
