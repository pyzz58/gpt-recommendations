"""Read-only audit observations on public fiction; all supplier I/O mocked.
Not a fix-verification gate and not a real media/creative quality test.
Run: python audit_probes/system_maturity_20261012.py
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import seedance_adapter as api
import video_workflow as flow


def observe():
    sample = ROOT / "examples/dinner-dialogue-review"
    base = json.loads((sample / "plan.json").read_text(encoding="utf-8"))
    direction = json.loads((sample / "direction_v02.json").read_text(encoding="utf-8"))

    def prepare(b, d):
        return api.prepare_shot(b, d, "S02", provider="volcengine",
                                audio_mode="native_dialogue")

    original = prepare(base, direction)
    cast = deepcopy(base)
    cast["characters"][1]["description"] = "AUDIT_MOTHER_APPEARANCE_SENTINEL"
    cast["characters"][1]["wardrobe"] = "AUDIT_MOTHER_WARDROBE_SENTINEL"
    cast_packet = prepare(cast, direction)
    camera = deepcopy(direction)
    camera["shots"][1]["camera"]["screen_axis"] = "AUDIT_AXIS_SENTINEL"
    camera["shots"][1]["camera"]["focal_length_mm"] = 85
    camera["shots"][1]["staging"]["spatial_constraints"] = ["AUDIT_SPATIAL_SENTINEL"]
    camera["shots"][1]["art"]["scene_geometry"] = {
        "anchor_positions": {"door": "AUDIT_DOOR_SENTINEL", "table": "AUDIT_TABLE_SENTINEL"},
        "key_light_position": "AUDIT_LIGHT_SENTINEL", "camera_axis": "AUDIT_CAMERA_SENTINEL"}
    camera_packet = prepare(base, camera)
    sound = deepcopy(direction)
    sound["shots"][1]["sound"]["ambient"] = "AUDIT_AMBIENT_SENTINEL"
    sound["shots"][1]["sound"]["music"] = "AUDIT_MUSIC_SENTINEL"
    sound_packet = prepare(base, sound)
    result = {
        "kind": "AUDIT_OBSERVATIONS_NOT_FIX_VERIFICATION",
        "AUD-030_cast_change_leaves_request_body_unchanged":
            original["body"] == cast_packet["body"],
        "AUD-030_camera_change_leaves_request_body_unchanged":
            original["body"] == camera_packet["body"],
        "AUD-031_sound_change_leaves_request_body_unchanged":
            original["body"] == sound_packet["body"],
        "all_four_packet_digests_differ":
            len({p["request_digest"] for p in
                 (original, cast_packet, camera_packet, sound_packet)}) == 4,
        "real_external_calls": 0,
    }
    with tempfile.TemporaryDirectory(prefix="director-audit-synthetic-") as folder:
        root = Path(folder)
        flow.prepare_job(base, direction, "S02", private_dir=root,
                         provider="volcengine", audio_mode="native_dialogue")
        with patch.object(api, "_request", return_value={"id": "synthetic_audit_task"}) as request:
            flow.submit_job(root, api_key="SYNTHETIC-NOT-A-KEY", approval={
                "request_digest": original["request_digest"], "rights_reviewed": True,
                "currency": "CNY", "quoted_cost": "1", "max_cost": "2"})
            response = dict(id="synthetic_audit_task", status="succeeded",
                            model=original["body"]["model"],
                            content={"video_url": "https://synthetic.tos-cn-beijing.volces.com/old"})
            request.return_value = response
            flow.query_job(root, api_key="SYNTHETIC-NOT-A-KEY")
            response = deepcopy(response)
            response["content"]["video_url"] = "https://synthetic.tos-cn-beijing.volces.com/new"
            request.return_value = response
            flow.query_job(root, api_key="SYNTHETIC-NOT-A-KEY")
            result["AUD-032_updated_success_url_discarded"] = (
                api._read(root / "result.json")["content"]["video_url"]
                != response["content"]["video_url"])
            result["mock_POST_count"] = sum(c.args[1] == "POST" for c in request.call_args_list)
            result["mock_GET_count"] = sum(c.args[1] == "GET" for c in request.call_args_list)
    return result


if __name__ == "__main__":
    print(json.dumps(observe(), ensure_ascii=False, indent=2))
