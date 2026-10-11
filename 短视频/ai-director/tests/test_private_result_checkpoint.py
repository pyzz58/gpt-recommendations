"""Offline crash recovery tests; NO provider network, no real user material."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
import os

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import agent_live_pilot as pilot
import agent_live_crew as crew
import agent_team as team
import private_result_checkpoint as vault_mod
import test_agent_live_pilot as early_fixture
import test_agent_live_crew as crew_fixture


class PrivateCheckpointTests(unittest.TestCase):
    def setUp(self):
        fixture=early_fixture.LivePilotTests(
            "test_one_task_creative_director_and_script_editor_use_original_dag")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fix=fixture

    def fake_call(self,journal,vault,state,task,payload):
        return pilot.run_one_creative_task(
            self.fix.intake,state,self.fix.source,journal,
            permit=self.fix.permit(task),
            client=pilot.StaticHTTPSFrame(self.fix.frame(payload)),
            task_id=task,result_vault=vault)

    def test_validated_full_private_results_survive_restart_both_roles(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as ledger:
            vault=vault_mod.PrivateResultVault(ledger)
            state1,_=self.fake_call(ledger,vault,self.fix.state,
                                    "director_brief",self.fix.brief)
            self.assertEqual(ledger.summary()["attempts"][0]["status"],
                             "response_accepted")
            state2,_=self.fake_call(ledger,vault,state1,"script_edit",
                                    self.fix.treatment)
            self.assertEqual(vault.assert_existing_accepted_checkpoint_chain(
                state2)["accepted_private_results"],2)
            file=vault.root/"attempt-0001.json"
            self.assertEqual(file.stat().st_mode & 0o777,0o600)
            self.assertEqual(vault.root.stat().st_mode & 0o777,0o700)
            self.assertIn("creative_brief",file.read_text("utf-8"))
            self.assertNotIn("Authorization",file.read_text("utf-8"))
            self.assertNotIn("creative_brief",ledger.journal.read_text("utf-8"))
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as reopened:
            restored=vault_mod.PrivateResultVault(reopened)
            self.assertEqual(restored.load(2,expected_before=state1)["team"],state2)
            self.assertEqual(restored.assert_existing_accepted_checkpoint_chain(
                state2)["accepted_private_results"],2)

    def test_real_https_without_private_result_vault_rejected_pre_network(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as journal:
            with patch("agent_live_pilot.http.client.HTTPSConnection") as socket:
                with self.assertRaisesRegex(pilot.PilotError,
                                            "PRIVATE_RESULT_VAULT_REQUIRED"):
                    pilot.run_one_creative_task(
                        self.fix.intake,self.fix.state,self.fix.source,journal,
                        permit=self.fix.permit("director_brief"),
                        client=pilot.DeepSeekHTTPSClient(),
                        api_key="FAKE_ONLY_NOT_A_REAL_KEY",
                        task_id="director_brief")
                socket.assert_not_called()
            self.assertEqual(journal.summary()["attempts"],[])

    def test_response_received_but_checkpoint_disk_failure_never_resends(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as journal:
            vault=vault_mod.PrivateResultVault(journal)
            fake=pilot.StaticHTTPSFrame(self.fix.frame(self.fix.brief))
            with patch("private_result_checkpoint._atomic_create",
                       side_effect=OSError("synthetic disk outage")):
                with self.assertRaisesRegex(
                        pilot.PilotError,"RESULT_CHECKPOINT_UNCERTAIN_NO_RETRY"):
                    pilot.run_one_creative_task(
                        self.fix.intake,self.fix.state,self.fix.source,journal,
                        permit=self.fix.permit("director_brief"),
                        client=fake,task_id="director_brief",result_vault=vault)
            self.assertEqual(fake.calls,1)
            self.assertFalse((vault.root/"attempt-0001.json").exists())
            self.assertEqual(journal.summary()["attempts"][0]["status"],
                             "pending_uncertain")
            with self.assertRaisesRegex(
                    vault_mod.CheckpointError,"UNKNOWN_BILLING_BLOCKS_NEXT"):
                vault.assert_existing_accepted_checkpoint_chain(self.fix.state)
            with self.assertRaisesRegex(pilot.PilotError,
                                        "UNKNOWN_ATTEMPT_BLOCKS_NEXT"):
                journal.reserve("script_edit",1,{
                    "body":{"model":self.fix.config["model"]}})
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as reopened:
            self.assertEqual(reopened.summary()["attempts"][0]["status"],
                             "pending_uncertain")
            with self.assertRaises(vault_mod.CheckpointError):
                vault_mod.PrivateResultVault(reopened).reconcile_saved_result(
                    1,self.fix.state,
                    operator_acknowledgement=vault_mod.RECOVER_CONSENT)

    def test_crash_after_result_fsync_before_ledger_commit_manual_recovery(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as journal:
            vault=vault_mod.PrivateResultVault(journal)
            with patch.object(journal,"finish",
                              side_effect=OSError("synthetic crash prefinish")):
                with self.assertRaisesRegex(
                        pilot.PilotError,"LEDGER_COMMIT_UNCERTAIN_RECOVERY_REQUIRED"):
                    self.fake_call(journal,vault,self.fix.state,
                                   "director_brief",self.fix.brief)
            self.assertTrue((vault.root/"attempt-0001.json").is_file())
            self.assertEqual(journal.summary()["attempts"][0]["status"],
                             "pending_uncertain")
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as reopened:
            vault=vault_mod.PrivateResultVault(reopened)
            with self.assertRaisesRegex(vault_mod.CheckpointError,
                                        "MANUAL_RECONCILIATION_REQUIRED"):
                vault.reconcile_saved_result(1,self.fix.state,
                                             operator_acknowledgement="continue")
            recovered=vault.reconcile_saved_result(
                1,self.fix.state,
                operator_acknowledgement=vault_mod.RECOVER_CONSENT)
            self.assertEqual(recovered["provider_calls"],0)
            self.assertFalse(recovered["provider_invoice_verified"])
            self.assertEqual(reopened.summary()["attempts"][0]["status"],
                             "response_accepted")
            state=recovered["after_state"]
            self.assertEqual(team.ready(state),["script_edit"])
            end,_=self.fake_call(reopened,vault,state,
                                 "script_edit",self.fix.treatment)
            self.assertEqual(len(reopened.summary()["attempts"]),2)
            self.assertEqual(team.ready(end),["director_lock"])

    def test_missing_checkpoint_or_stale_before_state_blocks_new_paid_work(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as journal:
            vault=vault_mod.PrivateResultVault(journal)
            out,_=self.fake_call(journal,vault,self.fix.state,
                                 "director_brief",self.fix.brief)
            with self.assertRaisesRegex(vault_mod.CheckpointError,
                                        "CALLER_STATE_NOT_LATEST"):
                vault.assert_existing_accepted_checkpoint_chain(self.fix.state)
            with self.assertRaisesRegex(vault_mod.CheckpointError,
                                        "PREVIOUS_STATE_MISMATCH"):
                vault.load(1,expected_before=out)
            (vault.root/"attempt-0001.json").unlink()
            with self.assertRaisesRegex(vault_mod.CheckpointError,
                                        "MISSING_OR_UNTRUSTED"):
                vault.assert_existing_accepted_checkpoint_chain(out)

    def test_checkpoint_tamper_role_request_sha_and_permissions_fail_closed(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as journal:
            vault=vault_mod.PrivateResultVault(journal)
            self.fake_call(journal,vault,self.fix.state,
                           "director_brief",self.fix.brief)
            file=vault.root/"attempt-0001.json"
            original=file.read_text("utf-8")
            parsed=json.loads(original)
            parsed["request_digest"]="f"*64
            file.write_text(json.dumps(parsed),encoding="utf-8")
            os.chmod(file,0o600)
            with self.assertRaisesRegex(vault_mod.CheckpointError,
                                        "BINDING_MISMATCH"):
                vault.load(1)
            file.write_text(original,encoding="utf-8")
            os.chmod(file,0o644)
            with self.assertRaisesRegex(vault_mod.CheckpointError,
                                        "FILE_PERMISSIONS_OR_SIZE"):
                vault.load(1)

    def test_overwrite_other_user_record_forbidden(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as journal:
            vault=vault_mod.PrivateResultVault(journal)
            out,_=self.fake_call(journal,vault,self.fix.state,
                                 "director_brief",self.fix.brief)
            with self.assertRaisesRegex(vault_mod.CheckpointError,
                                        "ATTEMPT_ALREADY_FINISHED"):
                vault.save(1,self.fix.state,out,usage={
                    "total_tokens":1,"estimated_usage_cost_cny":"0.1"})

    def test_git_worktree_cannot_be_used_as_private_result_vault(self):
        with tempfile.TemporaryDirectory() as root:
            repo=Path(root)/"public-code"
            repo.mkdir()
            (repo/".git").mkdir()
            nested=repo/"private-ish"
            nested.mkdir(mode=0o700)
            with pilot.PilotJournal(nested,self.fix.config) as ledger:
                with self.assertRaisesRegex(vault_mod.CheckpointError,
                                            "NO_PRIVATE_RESULTS_IN_GIT"):
                    vault_mod.PrivateResultVault(ledger)

    def test_atomic_link_after_fsync_then_ledger_failure_recovers_from_disk(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as ledger:
            vault=vault_mod.PrivateResultVault(ledger)
            original=vault_mod._fsync_folder
            state={"failed":False}
            def crash_once(path):
                if not state["failed"]:
                    state["failed"]=True
                    raise OSError("synthetic crash AFTER atomic hardlink")
                return original(path)
            with patch("private_result_checkpoint._fsync_folder",
                       side_effect=crash_once):
                with self.assertRaisesRegex(
                        pilot.PilotError,"RESULT_CHECKPOINT_UNCERTAIN_NO_RETRY"):
                    self.fake_call(ledger,vault,self.fix.state,
                                   "director_brief",self.fix.brief)
            self.assertEqual(ledger.summary()["attempts"][0]["status"],
                             "pending_uncertain")
            self.assertTrue((vault.root/"attempt-0001.json").exists())
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as reopened:
            vault=vault_mod.PrivateResultVault(reopened)
            recovered=vault.reconcile_saved_result(
                1,self.fix.state,
                operator_acknowledgement=vault_mod.RECOVER_CONSENT)
            self.assertEqual(recovered["provider_calls"],0)
            self.assertEqual(reopened.summary()["attempts"][0]["status"],
                             "response_accepted")
            self.assertEqual(recovered["after_state"]["tasks"][
                "director_brief"]["status"],"completed")

    def test_restarted_vault_rejects_checkpoint_from_different_config(self):
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as ledger:
            vault=vault_mod.PrivateResultVault(ledger)
            self.fake_call(ledger,vault,self.fix.state,
                           "director_brief",self.fix.brief)
            p=vault.root/"attempt-0001.json"
            a=json.loads(p.read_text("utf-8"))
            a["config_digest"]="a"*64
            p.write_text(json.dumps(a),encoding="utf-8")
            os.chmod(p,0o600)
        with pilot.PilotJournal(self.fix.tmp.name,self.fix.config) as reopened:
            with self.assertRaisesRegex(
                    vault_mod.CheckpointError,"BINDING_MISMATCH"):
                vault_mod.PrivateResultVault(reopened).load(1)

    def test_locked_professional_two_role_chain_survives_restart(self):
        f=crew_fixture.LockedCrewPilotTests(
            "test_first_three_roles_real_protocol_contract_offline")
        f.setUp()
        self.addCleanup(f.doCleanups)
        with pilot.PilotJournal(f.tmp.name,f.config) as ledger:
            vault=vault_mod.PrivateResultVault(ledger)
            state=f.state
            snapshots=[]
            for task in ("director_brief","script_edit"):
                original=state
                state,_=crew.run_one_locked_role(
                    f.snapshot,f.original,state,ledger,
                    permit=f._permit(task),
                    client=pilot.StaticHTTPSFrame(
                        f._frame(f._payload(task,state))),
                    task_id=task,result_vault=vault)
                snapshots.append((original,state))
        with pilot.PilotJournal(f.tmp.name,f.config) as reopened:
            vault=vault_mod.PrivateResultVault(reopened)
            self.assertEqual(vault.load(1,expected_before=snapshots[0][0])[
                "team"],snapshots[0][1])
            self.assertEqual(vault.load(2,expected_before=snapshots[1][0])[
                "team"],snapshots[1][1])
            self.assertEqual(vault.assert_existing_accepted_checkpoint_chain(
                state)["accepted_private_results"],2)
            self.assertEqual(team.ready(state),["director_lock"])

    def test_locked_professional_creative_dispatch_checkpointed_privately(self):
        f=crew_fixture.LockedCrewPilotTests(
            "test_first_three_roles_real_protocol_contract_offline")
        f.setUp()
        self.addCleanup(f.doCleanups)
        with pilot.PilotJournal(f.tmp.name,f.config) as ledger:
            vault=vault_mod.PrivateResultVault(ledger)
            old=f.state
            new,receipt=crew.run_one_locked_role(
                f.snapshot,f.original,old,ledger,
                permit=f._permit("director_brief"),
                client=pilot.StaticHTTPSFrame(f._frame(
                    f._payload("director_brief",old))),
                task_id="director_brief",result_vault=vault)
            self.assertFalse(receipt["network_attempted"])
            self.assertEqual(vault.load(1,expected_before=old)["team"],new)
            self.assertFalse(new["release"]["human_approved"])
            self.assertEqual(ledger.summary()["attempts"][0]["status"],
                             "response_accepted")

if __name__=="__main__":
    unittest.main()
