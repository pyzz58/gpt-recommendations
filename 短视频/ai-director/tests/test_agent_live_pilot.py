"""Isolated single-task live transport integration WITHOUT REAL NETWORK.

Mocks urllib/http connections or injects STATIC frames. Does not use API key
from environment, disclose user documents or make chargeable requests.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_live_pilot as pilot
import private_result_checkpoint as private_checkpoints
import agent_team as team
import agent_provider_wire as wire
import editorial_storyboard as creative
import test_editorial_storyboard as fixture


class LivePilotTests(unittest.TestCase):
    def setUp(self):
        f = fixture.EditorialStoryboardTests(
            methodName="test_strict_editorial_submit_end_to_end_without_model")
        f.setUp()
        self.intake = f.intake
        self.state = f.state
        self.source = f.source
        self.base = f.base
        self.brief = f.brief
        self.treatment = f.treatment
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = pilot.create_pilot_config(
            model="deepseek-flash", source_digest=self.state["source_digest"],
            base_digest=self.state["base_digest"],
            cap_cny="0.50", max_output_tokens=2048, max_attempts=2,
            cache_hit_cny_m="0.50", cache_miss_cny_m="2.00",
            output_cny_m="4.00")

    def frame(self, payload, *, model="deepseek-flash", stop="stop",
              prompt=500, completion=300):
        return {
            "object": "chat.completion", "model": model,
            "choices": [{"finish_reason": stop, "message": {
                "role": "assistant",
                "content": json.dumps(payload, ensure_ascii=False)}}],
            "usage": {
                "prompt_tokens": prompt, "completion_tokens": completion,
                "total_tokens": prompt+completion,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": prompt,
            },
        }

    def permit(self, task):
        return pilot.explicit_pilot_permit(
            self.config, task_id=task,
            acknowledgement=pilot.CONSENT_TEXT,
            privacy_consent=True, spending_consent=True)

    def test_pilot_is_off_by_default_and_does_not_reserve(self):
        with pilot.PilotJournal(self.tmp.name, self.config) as journal:
            fake = pilot.StaticHTTPSFrame(self.frame(self.brief))
            with self.assertRaisesRegex(pilot.PilotError, "EXPLICIT_CONSENT_MISSING"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    client=fake,api_key=None)
            self.assertEqual(journal.summary()["attempts"], [])
            self.assertEqual(fake.calls, 0)

    def test_consent_must_name_exact_task_transfer_and_price(self):
        for kwargs in (
                {"acknowledgement": "continue", "privacy_consent": True,
                 "spending_consent": True},
                {"acknowledgement": pilot.CONSENT_TEXT, "privacy_consent": False,
                 "spending_consent": True},
                {"acknowledgement": pilot.CONSENT_TEXT, "privacy_consent": True,
                 "spending_consent": False}):
            with self.assertRaisesRegex(pilot.PilotError, "EXPLICIT_CONSENT_MISSING"):
                pilot.explicit_pilot_permit(
                    self.config, task_id="director_brief", **kwargs)
        with self.assertRaisesRegex(pilot.PilotError, "ROLE_OUT_OF_SCOPE"):
            self.permit("unregistered_department")

    def test_one_task_creative_director_and_script_editor_use_original_dag(self):
        with pilot.PilotJournal(self.tmp.name, self.config) as journal:
            out, receipt = pilot.run_one_creative_task(
                self.intake, self.state, self.source, journal,
                permit=self.permit("director_brief"),
                client=pilot.StaticHTTPSFrame(self.frame(self.brief)))
            self.assertEqual(team.ready(out), ["script_edit"])
            self.assertEqual(receipt["transport"], "synthetic_fixture")
            self.assertFalse(receipt["network_attempted"])
            self.assertEqual(receipt["provider_invoice_verified"], False)
            self.assertEqual(journal.summary()["attempts"][0]["status"],
                             "response_accepted")
            end, receipt2 = pilot.run_one_creative_task(
                self.intake, out, self.source, journal,
                permit=self.permit("script_edit"),
                client=pilot.StaticHTTPSFrame(self.frame(self.treatment)))
            self.assertEqual(team.ready(end), ["director_lock"])
            proposed = creative.propose_directed_storyboard(
                self.intake, end, self.source)
            self.assertEqual(proposed["status"], "author_review_required")
            self.assertFalse(proposed["author_approved"])
            self.assertFalse(receipt2["network_attempted"])
            self.assertEqual(len(journal.summary()["attempts"]), 2)

    def test_durable_reservation_is_fsynced_before_fake_send(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            fake=pilot.StaticHTTPSFrame(self.frame(self.brief))
            origin=pilot.StaticHTTPSFrame.complete
            def captured(real_self,request,api_key):
                self.assertTrue(journal.journal.exists())
                record=json.loads(journal.journal.read_text("utf-8"))
                self.assertEqual(record["attempts"][0]["status"],"pending_uncertain")
                self.assertTrue(record["attempts"][0]["request_digest"])
                return origin(real_self,request,api_key)
            with patch.object(pilot.StaticHTTPSFrame, "complete", captured):
                _,receipt=pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),client=fake)
            self.assertFalse(receipt["network_attempted"])
            self.assertEqual(journal.summary()["attempts"][0]["status"],
                             "response_accepted")

    def test_usage_bad_data_does_not_mutate_pending_spend_record(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            req=wire.prepare_chat_request(
                [{"role":"system","content":"Fiction test only"},
                 {"role":"user","content":"Only offline test input"}],
                model=self.config["model"],
                max_output_tokens=self.config["max_output_tokens"])
            journal.reserve("director_brief",1,req)
            before=deepcopy(journal.summary()["attempts"][0])
            for bad in ({"total_tokens":100,"estimated_usage_cost_cny":"nan"},
                        {"total_tokens":-1,"estimated_usage_cost_cny":"0.2"},
                        {"total_tokens":42,"estimated_usage_cost_cny":"bad"}):
                with self.subTest(value=bad):
                    with self.assertRaisesRegex(pilot.PilotError,"USAGE_INVALID"):
                        journal.finish(1,"response_accepted",bad)
                    self.assertEqual(journal.summary()["attempts"][0],before)
                    self.assertEqual(json.loads(journal.journal.read_text(
                        "utf-8"))["attempts"][0],before)

    def test_finish_durable_write_failure_poisoned_no_bill_replay(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            req=wire.prepare_chat_request(
                [{"role":"system","content":"No provider requests"},
                 {"role":"user","content":"Synthetic role task"}],
                model=self.config["model"],
                max_output_tokens=self.config["max_output_tokens"])
            journal.reserve("director_brief",1,req)
            original=deepcopy(journal.summary()["attempts"][0])
            with patch.object(journal,"_save",side_effect=OSError(
                    "synthetic filesystem failure before durable finish")):
                with self.assertRaises(OSError):
                    journal.finish(1,"response_accepted",{
                        "total_tokens":5,"estimated_usage_cost_cny":"0.0003"})
            self.assertTrue(journal.poisoned)
            self.assertEqual(journal.records["attempts"][0],original)
            self.assertEqual(json.loads(journal.journal.read_text(
                "utf-8"))["attempts"][0],original)
            with self.assertRaisesRegex(pilot.PilotError,
                                        "LEDGER_CLOSED_OR_MODIFIED"):
                journal.reserve("script_edit",1,req)
            with self.assertRaisesRegex(pilot.PilotError,
                                        "LEDGER_CLOSED_OR_MODIFIED"):
                journal.summary()
        # After restart the journal still remembers the pending reservation,
        # blocks any new sends until external reconciliation occurs.
        with pilot.PilotJournal(self.tmp.name,self.config) as restored:
            with self.assertRaisesRegex(pilot.PilotError,
                                        "UNKNOWN_ATTEMPT_BLOCKS_NEXT"):
                restored.reserve("script_edit",1,req)

    def test_https_success_path_is_tested_with_mocked_socket_only(self):
        class FakeResponse:
            status=200
            def read(inner,limit):
                self.assertGreater(limit,0)
                return json.dumps(self.frame(self.brief),
                                  ensure_ascii=False).encode("utf-8")
        class FakeHTTPS:
            def __init__(inner,*args,**kwargs):
                self.assertEqual(args[0],"api.deepseek.com")
                self.assertEqual(kwargs["port"],443)
            def request(inner,method,path,body,headers):
                self.assertEqual(method,"POST")
                self.assertEqual(path,"/chat/completions")
                self.assertEqual(headers["Authorization"],
                                 "Bearer TEST_ONLY_NOT_REAL_KEY")
                self.assertEqual(json.loads(body)["model"],"deepseek-flash")
            def getresponse(inner):
                return FakeResponse()
            def close(inner):
                pass
        with patch("agent_live_pilot.http.client.HTTPSConnection",FakeHTTPS):
            with pilot.PilotJournal(self.tmp.name,self.config) as journal:
                vault=private_checkpoints.PrivateResultVault(journal)
                state, receipt=pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),
                    client=pilot.DeepSeekHTTPSClient(),
                    api_key="TEST_ONLY_NOT_REAL_KEY",result_vault=vault)
                self.assertEqual(team.ready(state),["script_edit"])
                self.assertEqual(receipt["transport"],"real_https")
                self.assertEqual(journal.summary()["attempts"][0]["status"],
                                 "response_accepted")
                self.assertNotIn("TEST_ONLY_NOT_REAL_KEY",
                                 journal.journal.read_text("utf-8"))

    def test_cap_rejects_before_sending_or_reserving(self):
        config=pilot.create_pilot_config(
            model="deepseek-flash",source_digest=self.state["source_digest"],
            base_digest=self.state["base_digest"],cap_cny="0.00000001",
            cache_hit_cny_m="1",cache_miss_cny_m="2",output_cny_m="4",
            max_output_tokens=2048)
        with pilot.PilotJournal(self.tmp.name,config) as journal:
            fake=pilot.StaticHTTPSFrame(self.frame(self.brief))
            with self.assertRaisesRegex(pilot.PilotError,"CAP_BEFORE_SEND"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=pilot.explicit_pilot_permit(
                        config,task_id="director_brief",
                        acknowledgement=pilot.CONSENT_TEXT,
                        privacy_consent=True,spending_consent=True),
                    client=fake)
            self.assertEqual(fake.calls,0)
            self.assertEqual(journal.summary()["attempts"],[])

    def test_duplicate_revision_has_no_retry_even_if_first_succeeded(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            pilot.run_one_creative_task(
                self.intake,self.state,self.source,journal,
                permit=self.permit("director_brief"),
                client=pilot.StaticHTTPSFrame(self.frame(self.brief)))
            fake=pilot.StaticHTTPSFrame(self.frame(self.brief))
            with self.assertRaisesRegex(pilot.PilotError,"NO_AUTOMATIC_RETRY"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),client=fake)
            self.assertEqual(fake.calls,0)

    def test_usage_exceeding_reservation_blocks_downstream(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            fake=pilot.StaticHTTPSFrame(self.frame(
                self.brief,prompt=900000,completion=500))
            with self.assertRaisesRegex(pilot.PilotError, "RESPONSE_REJECTED_NO_RETRY"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),client=fake)
            self.assertEqual(
                journal.summary()["attempts"][0]["status"],
                "usage_overrun_requires_review")
            with self.assertRaisesRegex(pilot.PilotError,"UNKNOWN_ATTEMPT_BLOCKS_NEXT"):
                journal.reserve("script_edit",1,wire.prepare_chat_request(
                    [{"role":"system","content":"JSON only"},
                     {"role":"user","content":"Synthetic writing task"}],
                    model="deepseek-flash",max_output_tokens=2048))

    def test_timeout_blocks_all_following_calls_and_persists(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            with self.assertRaisesRegex(pilot.PilotError,"TIMEOUT_CHARGE_UNKNOWN"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),
                    client=pilot.StaticHTTPSFrame("TIMEOUT"))
            self.assertEqual(journal.summary()["attempts"][0]["status"],"timeout_unknown")
        with pilot.PilotJournal(self.tmp.name,self.config) as reopened:
            with self.assertRaisesRegex(pilot.PilotError,"UNKNOWN_ATTEMPT_BLOCKS_NEXT"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,reopened,
                    permit=self.permit("director_brief"),
                    client=pilot.StaticHTTPSFrame(self.frame(self.brief)))

    def test_transport_uncertain_blocks_resume(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            with self.assertRaisesRegex(pilot.PilotError, "NETWORK_OR_PROVIDER_STATUS_UNKNOWN"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),
                    client=pilot.StaticHTTPSFrame("CONNECTION"))
            self.assertEqual(journal.summary()["attempts"][0]["status"],"transport_unknown")

    def test_model_response_mismatch_is_rejected_and_never_retried(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            fake=pilot.StaticHTTPSFrame(self.frame(self.brief,model="wrong-model"))
            with self.assertRaisesRegex(pilot.PilotError,"RESPONSE_REJECTED_NO_RETRY"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),client=fake)
            self.assertEqual(journal.summary()["attempts"][0]["status"],"response_rejected")

    def test_malformed_creative_editor_output_is_rejected_and_original_state_untouched(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            first,_ = pilot.run_one_creative_task(
                self.intake,self.state,self.source,journal,
                permit=self.permit("director_brief"),
                client=pilot.StaticHTTPSFrame(self.frame(self.brief)))
            before=deepcopy(first)
            wrong=deepcopy(self.treatment)
            del wrong["story_treatment"]["storyboard_pitch"]
            with self.assertRaisesRegex(pilot.PilotError,"RESPONSE_REJECTED_NO_RETRY"):
                pilot.run_one_creative_task(
                    self.intake,first,self.source,journal,
                    permit=self.permit("script_edit"),
                    client=pilot.StaticHTTPSFrame(self.frame(wrong)))
            self.assertEqual(first,before)
            self.assertEqual(journal.summary()["attempts"][-1]["status"],"response_rejected")

    def test_wrong_source_and_wrong_task_refused_before_send(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            f=pilot.StaticHTTPSFrame(self.frame(self.brief))
            with self.assertRaisesRegex(pilot.PilotError,"SOURCE_DIGEST_MISMATCH|BASE_OR_SOURCE_CHANGED"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source+"tamper",journal,
                    permit=self.permit("director_brief"),client=f)
            with self.assertRaisesRegex(pilot.PilotError,"TASK_NOT_ALLOWED"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("script_edit"),client=f)
            self.assertEqual(f.calls,0)
            self.assertEqual(journal.summary()["attempts"],[])

    def test_no_raw_scripts_replies_or_keys_in_ledger(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            pilot.run_one_creative_task(
                self.intake,self.state,self.source,journal,
                permit=self.permit("director_brief"),
                client=pilot.StaticHTTPSFrame(self.frame(self.brief)))
            raw=journal.journal.read_text("utf-8")
            self.assertNotIn(self.source,raw)
            self.assertNotIn("creative_brief",raw)
            self.assertNotIn("api_key",raw)
            self.assertEqual(journal.journal.stat().st_mode & 0o777,0o600)
            self.assertEqual((journal.path/"crew_live_pilot.journal.lock").stat().st_mode & 0o777,0o600)

    def test_journal_mismatched_config_fails_closed(self):
        with pilot.PilotJournal(self.tmp.name,self.config):
            pass
        other=deepcopy(self.config)
        other["cap_cny"]="1.0"
        with self.assertRaisesRegex(pilot.PilotError,"LEDGER_INTEGRITY"):
            pilot.PilotJournal(self.tmp.name,other)

    def test_no_arbitrary_callback_or_network_service_for_live(self):
        class MaliciousClient:
            def complete(self,*args):
                raise AssertionError("must not execute")
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            with self.assertRaisesRegex(pilot.PilotError,"TRANSPORT_NOT_ALLOWED"):
                pilot.run_one_creative_task(
                    self.intake,self.state,self.source,journal,
                    permit=self.permit("director_brief"),
                    client=MaliciousClient())
            self.assertEqual(journal.summary()["attempts"],[])

    def test_https_transport_has_fixed_endpoint_and_does_not_follow_redirect(self):
        # Mock the lower socket layer, so not a byte is sent to any provider.
        class FakeResponse:
            status=302
        class FakeHTTPS:
            def __init__(inner,*args,**kwargs):
                self.assertEqual(args[:2],("api.deepseek.com",))
                self.assertEqual(kwargs.get("port"),443)
                self.assertIsNotNone(kwargs.get("context"))
            def request(inner, method,path,body,headers):
                self.assertEqual(method,"POST")
                self.assertEqual(path,"/chat/completions")
                self.assertIn("Authorization",headers)
            def getresponse(inner):
                return FakeResponse()
            def close(inner):
                pass
        req=wire.prepare_chat_request(
            [{"role":"system","content":"Reply JSON"},
             {"role":"user","content":"Synthetic fictional message"}],
            model="deepseek-flash",max_output_tokens=32)
        with patch("agent_live_pilot.http.client.HTTPSConnection",FakeHTTPS):
            with self.assertRaisesRegex(pilot.PilotError,"PROVIDER_NON_200"):
                pilot.DeepSeekHTTPSClient().complete(req,"dummy_test_secret")
        self.assertFalse(req["dispatch_authorized"])

    def test_https_no_key_means_no_connection_attempt(self):
        req=wire.prepare_chat_request(
            [{"role":"system","content":"Reply JSON"},
             {"role":"user","content":"Synthetic fictional message"}],
            model="deepseek-flash",max_output_tokens=32)
        with patch("agent_live_pilot.http.client.HTTPSConnection") as conn:
            with self.assertRaisesRegex(pilot.PilotError,"PRIVATE_API_KEY_MISSING"):
                pilot.DeepSeekHTTPSClient().complete(req,None)
            conn.assert_not_called()

    def test_live_transport_is_never_invoked_by_normal_offline_executor(self):
        import agent_executor
        class FakeClient(pilot.DeepSeekHTTPSClient):
            def complete(self,*args):
                raise AssertionError("should never run")
        with self.assertRaisesRegex(ValueError,"only exact FixtureOnlyAdapter"):
            agent_executor.execute_one(self.base,self.state,FakeClient(),
                                        source_text=self.source)

    def test_illegal_model_and_invalid_cost_are_rejected(self):
        with self.assertRaisesRegex(pilot.PilotError,"MODEL_NOT_VERIFIED"):
            pilot.create_pilot_config(
                model="unreviewed-model",source_digest=self.state["source_digest"],
                base_digest=self.state["base_digest"],cap_cny="1",
                max_output_tokens=2048,cache_hit_cny_m="1",
                cache_miss_cny_m="2",output_cny_m="4")
        for cap in ("nan", "-4", "0", "Inf"):
            with self.assertRaises(pilot.PilotError):
                pilot.create_pilot_config(
                    model="deepseek-flash",source_digest=self.state["source_digest"],
                    base_digest=self.state["base_digest"],cap_cny=cap,
                    max_output_tokens=2048,cache_hit_cny_m="1",
                    cache_miss_cny_m="2",output_cny_m="4")


if __name__=="__main__":
    unittest.main()
