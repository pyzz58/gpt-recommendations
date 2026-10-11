"""No-network tests of model routing and conservative offline budget simulation."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team as team
import agent_model_gateway as gateway
import test_agent_role_contracts as synthetic


class ModelGatewayTests(unittest.TestCase):
    def setUp(self):
        helper = synthetic.ProfessionalRoleContractsTests(
            methodName="test_complete_ten_role_strict_pipeline")
        helper.setUp()
        self.base = deepcopy(helper.base)
        self.source = helper.original
        self.state = team.start(self.base, source_text=self.source)
        self.responses = {
            tid: {"1": json.dumps(helper.payload(tid), ensure_ascii=False)}
            for tid in team.SPECS
        }
        self.model_profiles = {
            "flash": {
                "provider": "synthetic_deepseek_profile",
                "model": "example-not-real-flash",
                "max_input_tokens": 200000,
                "max_output_tokens": 4096,
                "input_cny_per_m": "3.20",
                "output_cny_per_m": "18.90",
            },
            "film": {
                "provider": "synthetic_secondary_profile",
                "model": "example-not-real-film",
                "max_input_tokens": 200000,
                "max_output_tokens": 4096,
                "input_cny_per_m": "4.10",
                "output_cny_per_m": "23.30",
            },
        }
        self.routing = {"*": "flash", "camera_art": "film"}

    def policy(self, *, cap_cny="50", max_attempts=20, profiles=None, routing=None):
        return gateway.configure_profiles(
            self.model_profiles if profiles is None else profiles,
            self.routing if routing is None else routing,
            cap_cny=cap_cny, max_attempts=max_attempts)

    def book(self, **kwargs):
        return gateway.OfflineBudgetBook(self.policy(**kwargs))

    def transport(self, records=None):
        return gateway.OfflineMockTransport(
            self.responses if records is None else records)

    def test_full_ten_role_model_simulation_and_budget_receipts(self):
        original = deepcopy(self.state)
        book = self.book()
        result, receipt = gateway.simulate_until_pause(
            self.base, self.state, book, self.transport(),
            source_text=self.source, allow_mock_director_final=True)
        self.assertEqual(receipt["processed_count"], 10)
        self.assertEqual(receipt["status"], "no_ready_tasks")
        self.assertEqual(result["tasks"]["director_final"]["status"], "completed")
        self.assertEqual(receipt["actual_provider_calls"], 0)
        self.assertEqual(receipt["actual_billed_cny"], "0")
        self.assertTrue(book.total_reserved_cny > Decimal("0"))
        self.assertEqual(len(book.attempts), 10)
        self.assertEqual(book.attempts[4]["model_key"], "film")
        self.assertEqual([x["task_id"] for x in receipt["processed"]], list(team.SPECS))
        self.assertFalse(result["release"]["human_approved"])
        self.assertFalse(result["release"]["paid_api_authorized"])
        self.assertEqual(original, self.state)

    def test_private_text_only_in_ephemeral_request_not_public_receipts(self):
        book = self.book()
        request = gateway.prepare_request(
            self.base, self.state, "director_brief", book,
            source_text=self.source)
        self.assertIn(self.source, json.dumps(request))
        self.assertFalse(request["live_calls_authorized"])
        state, receipt = gateway.simulate_one(
            self.base, self.state, book, self.transport(),
            source_text=self.source)
        self.assertNotIn(self.source, json.dumps(book.safe_summary()))
        self.assertNotIn(self.source, json.dumps(receipt))
        self.assertEqual(book.safe_summary()["actual_billed_cny"], "0")
        self.assertEqual(state["tasks"]["director_brief"]["revision"], 1)

    def test_default_final_director_stop(self):
        book = self.book()
        result, rec = gateway.simulate_until_pause(
            self.base, self.state, book, self.transport(),
            source_text=self.source)
        self.assertEqual(rec["processed_count"], 9)
        self.assertEqual(rec["status"],
                         "director_final_requires_explicit_mock_permission")
        self.assertEqual(rec["ready_tasks"], ["director_final"])
        self.assertFalse(result["release"]["director_ai_review_complete"])
        with self.assertRaisesRegex(ValueError, "mock director final"):
            gateway.simulate_one(self.base, result, book, self.transport(),
                                 source_text=self.source)

    def test_model_profile_uses_per_role_routing(self):
        book = self.book()
        state = self.state
        for tid in ("director_brief", "script_edit", "director_lock", "acting"):
            state, _ = gateway.simulate_one(
                self.base, state, book, self.transport(), tid,
                source_text=self.source)
        req = gateway.prepare_request(
            self.base, state, "camera_art", book, source_text=self.source)
        self.assertEqual(req["provider"], "synthetic_secondary_profile")
        self.assertEqual(req["model"], "example-not-real-film")
        self.assertEqual(req["quote"]["model_key"], "film")

    def test_missing_mock_response_stops_without_reserving_or_mutating_state(self):
        data = deepcopy(self.responses)
        del data["director_lock"]
        book = self.book()
        result, receipt = gateway.simulate_until_pause(
            self.base, self.state, book, self.transport(data),
            source_text=self.source)
        self.assertEqual(receipt["processed_count"], 2)
        self.assertEqual(receipt["status"], "mock_response_missing")
        self.assertEqual(len(book.attempts), 2)
        self.assertEqual(team.ready(result), ["director_lock"])

    def test_incorrect_json_response_does_not_commit_and_reserves_attempt(self):
        data = deepcopy(self.responses)
        data["director_brief"]["1"] = '{"creative_brief":{"audience":"ok"}}'
        book = self.book()
        original = deepcopy(self.state)
        with self.assertRaises(ValueError):
            gateway.simulate_one(
                self.base, self.state, book, self.transport(data),
                source_text=self.source)
        self.assertEqual(self.state, original)
        self.assertEqual(book.attempts[0]["status"], "rejected_mock_response_reserved")
        self.assertGreater(book.total_reserved_cny, Decimal("0"))

    def test_cap_prevents_spend_before_any_attempt(self):
        book = self.book(cap_cny="0.00000001")
        with self.assertRaisesRegex(gateway.ModelBudgetError, "cap exceeded"):
            gateway.simulate_one(
                self.base, self.state, book, self.transport(),
                source_text=self.source)
        self.assertEqual(book.attempts, [])

    def test_attempt_limit_blocks_more_reservations(self):
        book = self.book(max_attempts=2)
        result, _ = gateway.simulate_one(
            self.base, self.state, book, self.transport(), source_text=self.source)
        result, _ = gateway.simulate_one(
            self.base, result, book, self.transport(), source_text=self.source)
        with self.assertRaisesRegex(gateway.ModelBudgetError, "max model attempts"):
            gateway.simulate_one(
                self.base, result, book, self.transport(), source_text=self.source)
        self.assertEqual(len(book.attempts), 2)

    def test_bad_models_and_currency_inputs_rejected_fail_closed(self):
        for value in ("0", "-1", "NaN", "Infinity", "", float("inf")):
            with self.assertRaises((ValueError, gateway.ModelBudgetError)):
                self.policy(cap_cny=value)
        for value in (0, False, 1.5, 26):
            with self.assertRaises(ValueError):
                self.policy(max_attempts=value)
        for routes in ({"*": "missing"}, {"not_a_role": "flash", "*": "flash"}):
            with self.assertRaises(ValueError):
                self.policy(routing=routes)

    def test_zero_or_negative_price_rejected_and_no_default_prices(self):
        for field in ("input_cny_per_m", "output_cny_per_m"):
            p = deepcopy(self.model_profiles)
            p["flash"][field] = "0"
            with self.assertRaises(gateway.ModelBudgetError):
                self.policy(profiles=p)
        p = deepcopy(self.model_profiles)
        del p["flash"]["input_cny_per_m"]
        with self.assertRaises(ValueError):
            self.policy(profiles=p)

    def test_context_token_proxy_cap_blocks_request(self):
        p = deepcopy(self.model_profiles)
        p["flash"]["max_input_tokens"] = 256
        book = gateway.OfflineBudgetBook(self.policy(profiles=p))
        with self.assertRaisesRegex(gateway.ModelBudgetError, "context cap"):
            gateway.prepare_request(
                self.base, self.state, "director_brief", book,
                source_text=self.source)

    def test_source_digest_mismatch_blocks_before_reservation(self):
        book = self.book()
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            gateway.simulate_one(self.base, self.state, book,
                                 self.transport(), source_text="changed")
        self.assertEqual(len(book.attempts), 0)

    def test_forged_live_budget_flag_fails_closed(self):
        p = self.policy()
        p["live_calls_authorized"] = True
        with self.assertRaises(gateway.ModelBudgetError):
            gateway.OfflineBudgetBook(p)
        p = self.policy()
        p["private_data_transfer_authorized"] = True
        with self.assertRaises(gateway.ModelBudgetError):
            gateway.OfflineBudgetBook(p)

    def test_only_exact_offline_transport_and_book_accepted(self):
        class SecretCaller:
            def complete(self, request):
                raise AssertionError("network should not be reached")

        class MockSubclass(gateway.OfflineMockTransport):
            def complete(self, request):
                raise AssertionError("subclass could execute network")

        for transport in (SecretCaller(), MockSubclass(self.responses)):
            with self.assertRaisesRegex(ValueError, "LIVE_MODEL_TRANSPORT_DISABLED"):
                gateway.simulate_one(self.base, self.state,
                                     self.book(), transport, source_text=self.source)
        self.assertFalse(hasattr(gateway, "requests"))
        self.assertFalse(hasattr(gateway, "urllib"))

    def test_revision_scoping_still_works_after_mock_model_run(self):
        book = self.book()
        state, _ = gateway.simulate_until_pause(
            self.base, self.state, book, self.transport(),
            source_text=self.source, allow_mock_director_final=True)
        revised = team.request_revision(state, "acting", ["S02"], "Repair hand pose")
        response = deepcopy(self.responses)
        scoped_payload = synthetic.ProfessionalRoleContractsTests(
            methodName="test_complete_ten_role_strict_pipeline")
        scoped_payload.setUp()
        response["acting"]["2"] = json.dumps(
            scoped_payload.payload("acting", ["S02"]), ensure_ascii=False)
        new_book = self.book()  # separate offline simulation budget session
        updated, receipt = gateway.simulate_one(
            self.base, revised, new_book, self.transport(response), "acting",
            source_text=self.source)
        self.assertEqual(receipt["revision"], 2)
        self.assertEqual(updated["tasks"]["acting"]["revision"], 2)
        self.assertEqual(updated["tasks"]["camera_art"]["revision"], 1)
        self.assertEqual(updated["tasks"]["editing_animation"]["status"], "stale")

    def test_budget_quote_does_not_auto_verify_actual_provider_prices(self):
        book = self.book()
        quote = gateway.prepare_request(
            self.base, self.state, "director_brief", book,
            source_text=self.source)["quote"]
        self.assertIn("proxy", quote["method"])
        self.assertFalse(quote["live_calls_authorized"])
        self.assertGreater(Decimal(quote["reserved_cny"]), Decimal("0"))
        self.assertGreater(quote["reserved_output_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
