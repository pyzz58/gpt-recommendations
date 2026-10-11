"""Test owner-scoped cloud-only pilot WITHOUT real credentials or networking."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import agent_live_pilot as pilot
import article_intake as intake
import live_pilot_readiness as readiness
import one_time_deepseek_cloud_trial as cloud
import test_editorial_storyboard as fiction_fixtures


class CloudOneTimeTrialTests(unittest.TestCase):
    def setUp(self):
        self.allowed = {
            "GITHUB_ACTIONS":"true",
            "GITHUB_EVENT_NAME":"workflow_dispatch",
            "GITHUB_REPOSITORY":cloud.REPO,
            "GITHUB_REF":"refs/heads/main",
            "GITHUB_ACTOR":"pyzz58",
            "GITHUB_RUN_ATTEMPT":"1",
            "DEEPSEEK_ONE_TIME_APPROVED":"YES_ONLY_TWO_CALLS",
        }

    def test_missing_each_cloud_guard_rejects_before_any_network(self):
        fields = tuple(self.allowed)
        with tempfile.TemporaryDirectory() as tmp:
            for key in fields:
                data=deepcopy(self.allowed)
                del data[key]
                with patch.dict(os.environ, data, clear=True):
                    with patch("one_time_deepseek_cloud_trial.pilot.DeepSeekHTTPSClient") as client:
                        with self.assertRaisesRegex(cloud.CloudTrialError,"CLOUD_"):
                            cloud.run_once_public_fiction(Path(tmp)/"private",api_key="FAKE_KEY_NEVER_NETWORKED")
                        client.assert_not_called()

    def test_github_rerun_is_blocked_even_if_secret_remains(self):
        bad=dict(self.allowed, GITHUB_RUN_ATTEMPT="2")
        with patch.dict(os.environ,bad,clear=True):
            with tempfile.TemporaryDirectory() as temp:
                target=Path(temp)/"no-retry"
                with patch("one_time_deepseek_cloud_trial.pilot.DeepSeekHTTPSClient") as client:
                    with self.assertRaisesRegex(cloud.CloudTrialError,
                                                "WORKFLOW_RERUN_FORBIDDEN"):
                        cloud.run_once_public_fiction(target,
                                                    api_key="NEVER_REAL_KEY_12345")
                    client.assert_not_called()
                self.assertFalse(target.exists())

    def test_wrong_actor_repo_and_non_manual_trigger_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for field,value in (("GITHUB_ACTOR","outsider"),
                                ("GITHUB_REPOSITORY","attacker/fork"),
                                ("GITHUB_EVENT_NAME","push"),
                                ("GITHUB_REF","refs/heads/feature")):
                allowed=deepcopy(self.allowed)
                allowed[field]=value
                with patch.dict(os.environ,allowed,clear=True):
                    with self.assertRaises(cloud.CloudTrialError):
                        cloud.run_once_public_fiction(
                            Path(tmp)/"will-not-exist",api_key="DO_NOT_USE_EXAMPLE_KEY")

    def test_missing_secret_rejected_before_creating_artifacts(self):
        with patch.dict(os.environ,self.allowed,clear=True):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/"new-result"
                with self.assertRaisesRegex(cloud.CloudTrialError,"SECRET_REQUIRED"):
                    cloud.run_once_public_fiction(path,api_key=None)
                self.assertFalse(path.exists())

    def test_public_preflight_does_not_access_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"preview"
            run=subprocess.run(
                [sys.executable,str(ROOT/"one_time_deepseek_cloud_trial.py"),
                 "--offline-preflight","--out",str(out)],
                env={"PATH":os.environ.get("PATH",""),"HOME":tmp},
                text=True,capture_output=True,check=False)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn("network_calls=0",run.stdout)
            doc=json.loads((out/"REAL_TEST_PREVIEW_ONLY_NO_CALL.json").read_text("utf-8"))
            self.assertFalse(doc["ready_for_live_dispatch"])
            self.assertEqual(doc["actual_provider_calls"],0)
            self.assertNotIn("DEEPSEEK_ONE_TIME_API_KEY",str(doc))

    def test_only_two_roles_are_permitted_by_contract(self):
        self.assertEqual(cloud.TRIAL_ROLES,("director_brief","script_edit"))
        self.assertEqual(cloud.MAX_REQUESTS,2)
        self.assertEqual(cloud.VERSION,
                         "deepseek-one-time-public-fiction-cloud-trial-v1")
        self.assertEqual(sum(cloud.RUBRIC.values()),100)

    def _synthetic_frames(self):
        # AI responses are PREWRITTEN human fixtures, not generated; they only
        # test the actual HTTPS transport's framing with no socket.
        original=fiction_fixtures.EditorialStoryboardTests(
            "test_strict_editorial_submit_end_to_end_without_model")
        original.setUp()
        brief=deepcopy(original.brief)
        tr=deepcopy(original.treatment)
        result=intake.prepare_episode(readiness.PUBLIC_FICTION,"EP01")
        shots=result["plan"]["shots"]
        proto=tr["story_treatment"]
        proto["beat_map"]=[{
            "shot_id":s["id"],
            "dramatic_function":"观察门后来源不明的敲击和信封",
            "handoff_to_next":"动作悬而未决引向下一个镜头",
        } for s in shots]
        first_pitch=proto["storyboard_pitch"]["shot_designs"][0]
        proto["storyboard_pitch"]["shot_designs"]=[
            {
                **deepcopy(first_pitch),
                "shot_id":s["id"],
                "visual_type":"ai_video" if i%2==0 else "text_card",
                "evidence_quote":s["narration"],
                "visual_intention":f"第{i+1}段具体画面：通过手的犹豫和信封位置显示冲突",
                "post_overlay":"",
            } for i,s in enumerate(shots)]
        return [brief,tr]

    def test_two_fictional_model_frames_complete_full_role_result_artifact(self):
        outcomes=self._synthetic_frames()
        requests=[]
        class FakeResponse:
            status=200
            def __init__(self,data):
                self.data=data
            def read(self,limit):
                return self.data
        class FakeHTTPS:
            def __init__(fake,*args,**kwargs):
                self.assertEqual(args[0],"api.deepseek.com")
            def request(fake,method,path,body,headers):
                self.assertEqual(path,"/chat/completions")
                self.assertEqual(method,"POST")
                self.assertEqual(headers.get("Authorization"),"Bearer NEVER_REAL_KEY_12345")
                requests.append(json.loads(body))
            def getresponse(fake):
                content=outcomes[len(requests)-1]
                response={
                    "object":"chat.completion","model":"deepseek-flash",
                    "choices":[{"finish_reason":"stop","message":{
                        "role":"assistant","content":json.dumps(
                            content,ensure_ascii=False)}}],
                    "usage":{"prompt_tokens":3000,"completion_tokens":2000,
                             "total_tokens":5000,"prompt_cache_hit_tokens":0,
                             "prompt_cache_miss_tokens":3000}}
                return FakeResponse(json.dumps(response,ensure_ascii=False).encode("utf-8"))
            def close(fake):
                pass
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ,self.allowed,clear=True):
                with patch("agent_live_pilot.http.client.HTTPSConnection",FakeHTTPS):
                    report=cloud.run_once_public_fiction(Path(tmp)/"results",
                                                        api_key="NEVER_REAL_KEY_12345")
            self.assertEqual(len(requests),2)
            self.assertEqual(report["replies_accepted"],2)
            self.assertEqual(report["real_network_attempts_recorded"],2)
            self.assertEqual(report["status"],
                             "TWO_VALID_RESPONSES_NEED_HUMAN_QUALITY_REVIEW")
            self.assertFalse(report["provider_invoice_verified"])
            out=Path(tmp)/"results"
            quality=json.loads((out/"REAL_DEEPSEEK_PUBLIC_FICTION_ROLE_OUTPUTS.json").read_text("utf-8"))
            self.assertTrue(quality["shot_coverages_complete"])
            self.assertTrue(quality["source_narration_unchanged"])
            self.assertIsNone(quality["human_creative_quality_score"])
            self.assertFalse(quality["proposed_candidate"]["author_approved"])
            for p in out.iterdir():
                self.assertNotIn("NEVER_REAL_KEY_12345",p.read_text("utf-8"))
                self.assertNotIn("Bearer ",p.read_text("utf-8"))

    def test_first_role_rejected_means_no_second_request_or_auto_retry(self):
        class FailResponse:
            status=200
            def read(self,n):
                return b'{"bad":"provider format"}'
        class FakeHTTPS:
            calls=0
            def __init__(fake,*args,**kwargs):
                pass
            def request(fake,*args,**kwargs):
                FakeHTTPS.calls+=1
            def getresponse(fake):
                return FailResponse()
            def close(fake):
                pass
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ,self.allowed,clear=True):
                with patch("agent_live_pilot.http.client.HTTPSConnection",FakeHTTPS):
                    r=cloud.run_once_public_fiction(Path(tmp)/"results",
                                                    api_key="NEVER_REAL_KEY_12345")
            self.assertEqual(FakeHTTPS.calls,1)
            self.assertEqual(r["replies_accepted"],0)
            self.assertEqual(r["status"],"HALTED_NO_AUTOMATIC_RETRY")
            self.assertEqual(len(r["outcome_by_role"]),1)
            self.assertEqual(r["outcome_by_role"][0]["role"],"director_brief")
            self.assertFalse((Path(tmp)/"results"/"REAL_DEEPSEEK_PUBLIC_FICTION_ROLE_OUTPUTS.json").exists())


if __name__=="__main__":
    unittest.main()
