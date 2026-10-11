"""Synthetic fault injection: no secrets, provider calls, or user material."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_live_pilot as pilot
import private_result_checkpoint as checkpoints
import test_agent_live_pilot as fixtures


class RecoverySafetyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.LivePilotTests(
            "test_one_task_creative_director_and_script_editor_use_original_dag")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.request = {"body": {"model": self.fixture.config["model"]}}

    def call(self, ledger, vault, state, task, payload):
        return pilot.run_one_creative_task(
            self.fixture.intake, state, self.fixture.source, ledger,
            permit=self.fixture.permit(task), task_id=task, result_vault=vault,
            client=pilot.StaticHTTPSFrame(self.fixture.frame(payload)))[0]

    def chain(self, ledger, vault):
        first = self.call(ledger, vault, self.fixture.state,
                          "director_brief", self.fixture.brief)
        last = self.call(ledger, vault, first,
                         "script_edit", self.fixture.treatment)
        return first, last

    def rewrite(self, vault, attempt, mutate):
        path = vault.root / ("attempt-%04d.json" % attempt)
        data = json.loads(path.read_text("utf-8"))
        mutate(data)
        path.write_text(json.dumps(data), encoding="utf-8")
        os.chmod(path, 0o600)

    def test_reserve_failure_before_replace_poisoned_until_reopen(self):
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as ledger:
            with patch("agent_live_pilot.os.replace", side_effect=OSError("fault")):
                with self.assertRaises(OSError):
                    ledger.reserve("director_brief", 1, self.request)
            self.assertTrue(ledger.poisoned)
            with self.assertRaisesRegex(pilot.PilotError, "CLOSED_OR_MODIFIED"):
                ledger.reserve("director_brief", 1, self.request)
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as reopened:
            self.assertEqual(reopened.summary()["attempts"], [])

    def test_reserve_failure_after_replace_preserves_uncertainty_on_restart(self):
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as ledger:
            real_fsync = os.fsync
            count = 0
            def fail_directory(fd):
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError("fault after rename")
                return real_fsync(fd)
            with patch("agent_live_pilot.os.fsync", side_effect=fail_directory):
                with self.assertRaises(OSError):
                    ledger.reserve("director_brief", 1, self.request)
            self.assertTrue(ledger.poisoned)
            with self.assertRaises(pilot.PilotError):
                ledger.reserve("director_brief", 1, self.request)
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as reopened:
            self.assertEqual(reopened.summary()["attempts"][0]["status"],
                             "pending_uncertain")
            with self.assertRaisesRegex(pilot.PilotError, "UNKNOWN_ATTEMPT_BLOCKS_NEXT"):
                reopened.reserve("director_brief", 1, self.request)

    def test_dispatch_never_calls_provider_when_reservation_commit_fails(self):
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as ledger:
            vault = checkpoints.PrivateResultVault(ledger)
            fake = pilot.StaticHTTPSFrame(self.fixture.frame(self.fixture.brief))
            with patch.object(ledger, "_save", side_effect=OSError("fault")):
                with self.assertRaises(OSError):
                    pilot.run_one_creative_task(
                        self.fixture.intake, self.fixture.state, self.fixture.source,
                        ledger, permit=self.fixture.permit("director_brief"),
                        task_id="director_brief", result_vault=vault, client=fake)
            self.assertEqual(fake.calls, 0)
            self.assertTrue(ledger.poisoned)

    def test_checkpoint_chain_rejects_unlinked_before_digest(self):
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as ledger:
            vault = checkpoints.PrivateResultVault(ledger)
            _, last = self.chain(ledger, vault)
            self.rewrite(vault, 2, lambda d: d.update(before_state_digest="f" * 64))
            with self.assertRaisesRegex(checkpoints.CheckpointError, "PREVIOUS_STATE_MISMATCH"):
                vault.assert_existing_accepted_checkpoint_chain(last)

    def test_recovery_checks_predecessor_before_accepting_pending_result(self):
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as ledger:
            vault = checkpoints.PrivateResultVault(ledger)
            first = self.call(ledger, vault, self.fixture.state,
                              "director_brief", self.fixture.brief)
            with patch.object(ledger, "finish", side_effect=OSError("fault")):
                with self.assertRaises(pilot.PilotError):
                    self.call(ledger, vault, first, "script_edit", self.fixture.treatment)
            self.rewrite(vault, 1, lambda d: d.update(request_digest="e" * 64))
            with self.assertRaises(checkpoints.CheckpointError):
                vault.reconcile_saved_result(2, first,
                    operator_acknowledgement=checkpoints.RECOVER_CONSENT)
            self.assertEqual(ledger.records["attempts"][1]["status"], "pending_uncertain")

    def test_accepted_checkpoint_usage_must_match_durable_journal(self):
        with pilot.PilotJournal(self.fixture.tmp.name, self.fixture.config) as ledger:
            vault = checkpoints.PrivateResultVault(ledger)
            state = self.call(ledger, vault, self.fixture.state,
                              "director_brief", self.fixture.brief)
            self.rewrite(vault, 1, lambda d: d["usage"].update(total_tokens=1))
            with self.assertRaisesRegex(checkpoints.CheckpointError, "USAGE_LEDGER_MISMATCH"):
                vault.assert_existing_accepted_checkpoint_chain(state)

    def test_pending_checkpoint_invalid_or_overrun_usage_cannot_be_recovered(self):
        for cost, tokens in (("NaN", 1), ("Infinity", 1), ("-0.1", 1),
                             ("0.001", -1), ("1000", 1)):
            with self.subTest(cost=cost, tokens=tokens):
                with tempfile.TemporaryDirectory() as directory:
                    with pilot.PilotJournal(directory, self.fixture.config) as ledger:
                        vault = checkpoints.PrivateResultVault(ledger)
                        with patch.object(ledger, "finish", side_effect=OSError("fault")):
                            with self.assertRaises(pilot.PilotError):
                                self.call(ledger, vault, self.fixture.state,
                                          "director_brief", self.fixture.brief)
                        self.rewrite(vault, 1, lambda d: d["usage"].update(
                            estimated_usage_cost_cny=cost, total_tokens=tokens))
                        with self.assertRaises(checkpoints.CheckpointError):
                            vault.reconcile_saved_result(1, self.fixture.state,
                                operator_acknowledgement=checkpoints.RECOVER_CONSENT)
                        self.assertEqual(ledger.records["attempts"][0]["status"],
                                         "pending_uncertain")


if __name__ == "__main__":
    unittest.main()
