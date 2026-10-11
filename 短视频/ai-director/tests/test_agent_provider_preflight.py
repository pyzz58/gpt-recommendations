"""All tests use synthetic data and provider-shaped responses, NEVER API calls."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team as team
import agent_provider_wire as wire
import agent_durable_preflight as durable
import test_agent_role_contracts as sample


class ProviderPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture = sample.ProfessionalRoleContractsTests(
            "test_complete_ten_role_strict_pipeline")
        self.fixture.setUp()
        self.base = self.fixture.base
        self.source = self.fixture.original
        self.state = team.start(self.base, source_text=self.source)
        self.config = durable.policy(
            model="deepseek-flash",
            source_digest=self.state["source_digest"],
            base_digest=self.state["base_digest"], cap_cny="50",
            max_attempts=12, max_output_tokens=4096,
            cache_hit_cny_m="0.04", cache_miss_cny_m="2",
            output_cny_m="8")

    def provider_response(self, task="director_brief", raw=None, usage=None,
                          model="deepseek-flash", finish="stop"):
        content = raw if raw is not None else json.dumps(
            self.fixture.payload(task), ensure_ascii=False)
        return {"id": "synthetic-completion-123",
                "object": "chat.completion", "model": model,
                "choices": [{
                    "index": 0, "finish_reason": finish,
                    "message": {"role": "assistant", "content": content}}],
                "usage": usage if usage is not None else {
                    "prompt_tokens": 130, "completion_tokens": 40,
                    "total_tokens": 170,
                    "prompt_cache_hit_tokens": 50,
                    "prompt_cache_miss_tokens": 80}}

    def responses(self):
        return durable.OfflineResponseFrames({
            task: {"1": self.provider_response(task)}
            for task in team.SPECS})

    def parse(self, raw=None, **kwargs):
        return wire.parse_chat_completion(
            self.provider_response() if raw is None else raw,
            expected_model="deepseek-flash", max_output_tokens=4096,
            hit_price_cny_m="0.04", miss_price_cny_m="2",
            output_price_cny_m="8", **kwargs)

    def test_official_chat_request_shape_but_no_transport(self):
        req = wire.prepare_chat_request([
            {"role": "system", "content": "Respond with JSON."},
            {"role": "user", "content": "Synthetic movie draft."}
        ], model="deepseek-flash", max_output_tokens=2048)
        self.assertEqual(req["endpoint"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["body"]["response_format"], {"type": "json_object"})
        self.assertFalse(req["body"]["stream"])
        self.assertFalse(req["dispatch_authorized"])
        self.assertNotIn("Authorization", req)
        self.assertNotIn("api_key", json.dumps(req))

    def test_chat_response_converts_provider_usage_with_cached_tokens(self):
        result = self.parse()
        u = result["usage"]
        self.assertEqual(u["prompt_cache_hit_tokens"], 50)
        self.assertEqual(u["prompt_cache_miss_tokens"], 80)
        self.assertEqual(u["total_tokens"], 170)
        self.assertEqual(u["estimated_usage_cost_cny"], "0.00048200")
        self.assertFalse(u["invoice_verified"])
        self.assertEqual(result["protocol"], "deepseek-chat-completions")

    def test_cache_breakdown_absent_conservatively_counts_as_all_miss(self):
        raw = self.provider_response(usage={
            "prompt_tokens": 130, "completion_tokens": 40,
            "total_tokens": 170})
        usage = self.parse(raw)["usage"]
        self.assertEqual(usage["prompt_cache_miss_tokens"], 130)
        self.assertEqual(usage["prompt_cache_hit_tokens"], 0)
        self.assertEqual(usage["cache_breakdown"], "cache_split_absent_all_miss")

    def test_partial_or_inconsistent_cache_report_fails_closed(self):
        for usage in (
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
             "prompt_cache_hit_tokens": 2},
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
             "prompt_cache_hit_tokens": 9, "prompt_cache_miss_tokens": 2},
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 99,
             "prompt_cache_hit_tokens": 4, "prompt_cache_miss_tokens": 6},
        ):
            with self.assertRaises(wire.ProviderProtocolError):
                self.parse(self.provider_response(usage=usage))

    def test_malformed_usage_rejected_including_bool_negative_and_nan(self):
        for invalid in (True, -1, 1.5, "3", None):
            usage = {"prompt_tokens": invalid, "completion_tokens": 5,
                     "total_tokens": 10}
            with self.assertRaises(wire.ProviderProtocolError):
                self.parse(self.provider_response(usage=usage))
        with self.assertRaises(wire.ProviderProtocolError):
            wire.normalize_usage(
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                hit_price_cny_m="NaN", miss_price_cny_m="2",
                output_price_cny_m="8")

    def test_model_switch_truncation_or_multiple_choices_rejected(self):
        wrong = self.provider_response(model="deepseek-v4-pro")
        with self.assertRaisesRegex(wire.ProviderProtocolError, "MODEL_RESPONSE_MISMATCH"):
            self.parse(wrong)
        truncated = self.provider_response(finish="length")
        with self.assertRaisesRegex(wire.ProviderProtocolError, "NON_FINAL"):
            self.parse(truncated)
        multiple = self.provider_response()
        multiple["choices"].append(deepcopy(multiple["choices"][0]))
        with self.assertRaisesRegex(wire.ProviderProtocolError, "CHOICE_COUNT"):
            self.parse(multiple)

    def test_invalid_inner_role_json_rejected_even_if_outer_valid(self):
        with self.assertRaisesRegex(wire.ProviderProtocolError, "INVALID_ROLE_JSON_CONTENT"):
            self.parse(self.provider_response(raw="```json\n{\"ok\":1}\n```"))

    def test_duplicate_response_json_keys_are_rejected(self):
        raw = '{"object":"chat.completion","object":"chat.completion"}'
        with self.assertRaisesRegex(wire.ProviderProtocolError, "INVALID_RESPONSE_JSON"):
            self.parse(raw)

    def test_no_script_or_api_key_in_durable_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as journal:
                state, receipt = durable.run_one_offline(
                    self.base, self.state, journal, self.responses(),
                    source_text=self.source)
                self.assertEqual(state["tasks"]["director_brief"]["status"], "completed")
                self.assertEqual(receipt["actual_network_calls"], 0)
                self.assertFalse(receipt["invoice_verified"])
                stored = (Path(folder)/"crew_budget.journal.json").read_text("utf-8")
                self.assertNotIn(self.source, stored)
                self.assertNotIn("synthetic-completion-123", stored)
                self.assertNotIn('"messages"', stored)
                self.assertGreater(journal.reserved_cny, Decimal("0"))
                self.assertEqual(journal.summary()["unreconciled_count"], 0)

    def test_full_ten_stage_synthetic_provider_protocol_with_revisions(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as journal:
                current = self.state
                frames = self.responses()
                for tid in team.SPECS:
                    current, receipt = durable.run_one_offline(
                        self.base, current, journal, frames, tid,
                        source_text=self.source, allow_mock_director_final=True)
                    self.assertEqual(receipt["task_id"], tid)
                self.assertEqual(team.ready(current), [])
                self.assertEqual(journal.summary()["record_count"], 10)
                self.assertTrue(current["release"]["director_ai_review_complete"])
                self.assertFalse(current["release"]["human_approved"])
                self.assertFalse(current["release"]["paid_api_authorized"])
                self.assertEqual(journal.summary()["actual_network_calls"], 0)

    def test_crash_after_reservation_blocks_replay_on_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as first:
                pkt = __import__("agent_role_contracts").build_role_messages(
                    self.base, self.state, "director_brief",
                    source_text=self.source)
                idx = first.reserve(
                    task_id="director_brief", revision=1,
                    messages=pkt["messages"])
                self.assertEqual(idx, 1)
            with durable.PrivateReservationJournal(folder, self.config) as resumed:
                self.assertEqual(resumed.summary()["unreconciled_count"], 1)
                with self.assertRaisesRegex(durable.DurablePreflightError, "UNRECONCILED"):
                    durable.run_one_offline(
                        self.base, self.state, resumed, self.responses(),
                        source_text=self.source)
                self.assertEqual(resumed.summary()["record_count"], 1)

    def test_timeout_stays_unknown_and_never_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as first:
                timeout = durable.OfflineResponseFrames({
                    "director_brief": {"1": "SIMULATE_TIMEOUT"}})
                with self.assertRaises(TimeoutError):
                    durable.run_one_offline(
                        self.base, self.state, first, timeout,
                        source_text=self.source)
                self.assertEqual(first.summary()["unreconciled_count"], 1)
                self.assertEqual(first.data["attempts"][0]["status"], "timeout_unknown")
            with durable.PrivateReservationJournal(folder, self.config) as second:
                with self.assertRaisesRegex(durable.DurablePreflightError, "UNRECONCILED"):
                    durable.run_one_offline(
                        self.base, self.state, second, self.responses(),
                        source_text=self.source)

    def test_response_invalid_still_charges_attempt_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as journal:
                corrupted = self.provider_response(raw='{"creative_brief": {}}')
                fake = durable.OfflineResponseFrames({"director_brief": {"1": corrupted}})
                with self.assertRaises(ValueError):
                    durable.run_one_offline(
                        self.base, self.state, journal, fake,
                        source_text=self.source)
                self.assertEqual(journal.data["attempts"][0]["status"],
                                 "response_rejected")
                self.assertEqual(journal.summary()["record_count"], 1)

    def test_one_job_cannot_be_opened_by_two_writers(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config):
                with self.assertRaisesRegex(
                        durable.DurablePreflightError, "ALREADY_LOCKED"):
                    durable.PrivateReservationJournal(folder, self.config)

    def test_resume_rejects_changed_prices_source_or_model(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config):
                pass
            for change in (
                {"cache_miss_cny_m": "0.001"},
                {"source_digest": "f"*64},
                {"model": "deepseek-v4-pro"}):
                modified = dict(self.config)
                modified.update(change)
                with self.assertRaisesRegex(durable.DurablePreflightError, "CONFIG_MISMATCH"):
                    durable.PrivateReservationJournal(folder, modified)

    def test_spend_limit_and_duplicate_attempt_rejected(self):
        config = dict(self.config)
        config["cap_cny"] = "0.00000001"
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, config) as journal:
                with self.assertRaisesRegex(durable.DurablePreflightError, "CAP_PREVENTS"):
                    durable.run_one_offline(
                        self.base, self.state, journal, self.responses(),
                        source_text=self.source)
                self.assertEqual(journal.summary()["record_count"], 0)
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as journal:
                after, _ = durable.run_one_offline(
                    self.base, self.state, journal, self.responses(),
                    source_text=self.source)
                with self.assertRaisesRegex(durable.DurablePreflightError, "DUPLICATE"):
                    durable.run_one_offline(
                        self.base, self.state, journal, self.responses(),
                        source_text=self.source)
                self.assertEqual(after["tasks"]["director_brief"]["status"],
                                 "completed")

    def test_current_source_digest_must_match_before_reserving(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as journal:
                with self.assertRaisesRegex(ValueError, "fingerprint"):
                    durable.run_one_offline(
                        self.base, self.state, journal, self.responses(),
                        source_text="Tampered input")
                self.assertEqual(journal.summary()["record_count"], 0)

    def test_protocol_responders_cannot_be_custom_network_objects(self):
        class NetworkTransport:
            def fetch(self, *_args):
                raise RuntimeError("should never be called")
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as journal:
                with self.assertRaisesRegex(
                        durable.DurablePreflightError, "LIVE_TRANSPORT_NOT_IMPLEMENTED"):
                    durable.run_one_offline(
                        self.base, self.state, journal, NetworkTransport(),
                        source_text=self.source)
                self.assertEqual(journal.summary()["record_count"], 0)

    def test_final_director_stops_unless_mock_permission(self):
        with tempfile.TemporaryDirectory() as folder:
            with durable.PrivateReservationJournal(folder, self.config) as journal:
                current = self.state
                for tid in list(team.SPECS)[:-1]:
                    current, _ = durable.run_one_offline(
                        self.base, current, journal, self.responses(), tid,
                        source_text=self.source)
                with self.assertRaisesRegex(
                        durable.DurablePreflightError, "DIRECTOR_FINAL"):
                    durable.run_one_offline(
                        self.base, current, journal, self.responses(),
                        source_text=self.source)
                self.assertEqual(journal.summary()["record_count"], 9)


if __name__ == "__main__":
    unittest.main()
