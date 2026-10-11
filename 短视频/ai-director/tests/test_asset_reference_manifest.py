"""Versioned, source-locked reference cards using fictional in-memory headers.

No actual user photos, private paths, DeepSeek network or media generated.
Image header bytes are fictional, NOT proof of decodable/reference quality.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import hashlib
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import asset_reference_manifest as refs
import agent_team as team
import editorial_review_lock as review
import agent_live_crew as crew
import agent_role_contracts as roles
import test_editorial_review_lock as editorial_fixture


class AssetReferenceManifestTests(unittest.TestCase):
    def setUp(self):
        self.text="Entirely fictitious short scene."
        self.digest=hashlib.sha256(self.text.encode()).hexdigest()
        self.base={
            "scenes":[{"id":"LOC01","description":"Invented room"}],
            "characters":[{"id":"CHAR01","name":"Fiction person"}],
            "props":[{"id":"PROP01","description":"Fiction envelope"}],
            "shots":[
                {"id":"S01","visual_type":"ai_video","scene_id":"LOC01",
                 "character_ids":["CHAR01"],"prop_ids":["PROP01"],
                 "duration":3,"narration":"She reaches for the envelope"},
                {"id":"S02","visual_type":"ai_video","scene_id":"LOC01",
                 "character_ids":["CHAR01"],"prop_ids":["PROP01"],
                 "duration":3,"narration":"She hesitates"}]}
        self.manifest=refs.create_empty(self.base,self.digest)
        self.bytes=b"\x89PNG\r\n\x1a\n"+b"FICTIONAL_HEADER_ONLY_NOT_VALID_PHOTO_CONTENT"

    def register(self,manifest=None,*,raw=None,asset="ASSET_CHAR01"):
        return refs.register_image(
            self.base,self.digest,manifest or self.manifest,
            asset_id=asset,entity_id="CHAR01",slot="identity_front",
            image_bytes=self.bytes if raw is None else raw,media_type="image/png")

    def bind_both(self,manifest):
        for shot in ("S01","S02"):
            manifest=refs.bind_shot(
                self.base,self.digest,manifest,shot_id=shot,
                entity_id="CHAR01",asset_id="ASSET_CHAR01")
        return manifest

    def test_empty_manifest_marks_missing_not_verified(self):
        a=refs.validate(self.base,self.digest,self.manifest)
        self.assertEqual(a["missing_bindings_count"],6)
        self.assertFalse(a["actual_reference_file_exists_verified"])
        self.assertFalse(a["human_approved"])
        self.assertFalse(a["ready_to_generate"])

    def test_register_content_hash_not_bytes_and_verify_in_private_memory(self):
        after=self.register()
        rev=after["cards"]["ASSET_CHAR01"]["versions"][0]
        self.assertEqual(rev["sha256"],hashlib.sha256(self.bytes).hexdigest())
        self.assertEqual(rev["version"],1)
        self.assertEqual(rev["rights_status"],"unverified")
        self.assertNotIn("FICTIONAL_HEADER_ONLY",json.dumps(after))
        self.assertNotIn("storage_path",json.dumps(after))
        check=refs.verify_bytes(after,"ASSET_CHAR01",1,self.bytes)
        self.assertTrue(check["sha256_matches"])
        self.assertFalse(check["identity_matches_persona"])
        self.assertFalse(check["rights_verified"])
        self.assertFalse(check["bytes_persisted_by_module"])

    def test_reject_content_hash_mismatch(self):
        after=self.register()
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "CONTENT_MISMATCH"):
            refs.verify_bytes(after,"ASSET_CHAR01",1,
                              self.bytes+b"changed")

    def test_shot_reference_explicit_binding_and_revision_history(self):
        original=self.register()
        bound=self.bind_both(original)
        r=refs.validate(self.base,self.digest,bound)
        self.assertEqual(r["missing_bindings_count"],4)
        self.assertTrue(r["per_entity_references_consistent"])
        rev2=self.register(bound,raw=self.bytes+b"VERSION_TWO")
        self.assertEqual(len(rev2["cards"]["ASSET_CHAR01"]["versions"]),2)
        self.assertEqual(rev2["cards"]["ASSET_CHAR01"]["versions"][1][
            "previous_revision_digest"],team.fingerprint(
                rev2["cards"]["ASSET_CHAR01"]["versions"][0]))
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "STALE_OR_WRONG_ENTITY"):
            refs.validate(self.base,self.digest,rev2)
        after=refs.bind_shot(self.base,self.digest,rev2,shot_id="S01",
                             entity_id="CHAR01",asset_id="ASSET_CHAR01")
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "STALE_OR_WRONG_ENTITY"):
            refs.validate(self.base,self.digest,after)
        final=refs.bind_shot(self.base,self.digest,after,shot_id="S02",
                             entity_id="CHAR01",asset_id="ASSET_CHAR01")
        self.assertTrue(refs.validate(self.base,self.digest,final)[
            "per_entity_references_consistent"])

    def test_no_implicit_reassignment_and_no_fake_reference(self):
        m=self.register()
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "ID_REASSIGNMENT_FORBIDDEN"):
            refs.register_image(self.base,self.digest,m,asset_id="ASSET_CHAR01",
                entity_id="PROP01",slot="prop_reference",
                image_bytes=self.bytes,media_type="image/png")
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "BINDING_WRONG_ENTITY"):
            refs.bind_shot(self.base,self.digest,m,shot_id="S01",
                           entity_id="PROP01",asset_id="ASSET_CHAR01")
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "BINDING_TARGET_INVALID"):
            refs.bind_shot(self.base,self.digest,m,shot_id="NOT_SHOT",
                           entity_id="CHAR01",asset_id="ASSET_CHAR01")

    def test_fake_rights_consent_or_human_approval_never_accepted(self):
        for key,val in (("human_approved",True),("usage_rights_verified",True),
                        ("paid_api_authorized",True),
                        ("reference_bytes_persisted",True)):
            forged=deepcopy(self.manifest)
            forged[key]=val
            with self.subTest(key=key):
                with self.assertRaisesRegex(refs.AssetReferenceError,
                                            "SOURCE_OR_AUTHORITY_INVALID"):
                    refs.validate(self.base,self.digest,forged)
        forged=self.register()
        forged["cards"]["ASSET_CHAR01"]["versions"][0]["rights_status"]="cleared"
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "REVISION_CHAIN_OR_RIGHTS_INVALID"):
            refs.validate(self.base,self.digest,forged)

    def test_source_or_plan_change_invalidates_manifest(self):
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "SOURCE_OR_AUTHORITY_INVALID"):
            refs.validate(self.base,"f"*64,self.manifest)
        bad=deepcopy(self.base)
        bad["shots"][0]["narration"]="different original"
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "SOURCE_OR_AUTHORITY_INVALID"):
            refs.validate(bad,self.digest,self.manifest)

    def test_wrong_mime_or_url_or_unlisted_field_rejected(self):
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "MEDIA_HEADER_MISMATCH"):
            refs.register_image(self.base,self.digest,self.manifest,
                asset_id="ASSET_CHAR01",entity_id="CHAR01",
                slot="identity_front",image_bytes=self.bytes,
                media_type="image/jpeg")
        forged=deepcopy(self.manifest)
        forged["public_url"]="https://example.invalid/private.jpg"
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "SOURCE_OR_AUTHORITY_INVALID"):
            refs.validate(self.base,self.digest,forged)

    def test_switching_character_reference_between_shots_needs_human_review(self):
        m=self.register()
        m=refs.register_image(self.base,self.digest,m,asset_id="ASSET_OTHER",
            entity_id="CHAR01",slot="identity_side",
            image_bytes=b"\x89PNG\r\n\x1a\n"+b"FICTIONAL_OTHER_VIEW",media_type="image/png")
        m=refs.bind_shot(self.base,self.digest,m,shot_id="S01",
                         entity_id="CHAR01",asset_id="ASSET_CHAR01")
        m=refs.bind_shot(self.base,self.digest,m,shot_id="S02",
                         entity_id="CHAR01",asset_id="ASSET_OTHER")
        report=refs.validate(self.base,self.digest,m)
        self.assertFalse(report["per_entity_references_consistent"])
        self.assertEqual(report["reference_switches"][0]["entity_id"],"CHAR01")
        self.assertFalse(report["media_identity_verified"])

    def test_missing_authoritative_character_ref_not_invented(self):
        m=self.manifest
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "ENTITY_OR_SLOT_NOT_AUTHORIZED"):
            refs.register_image(self.base,self.digest,m,
                asset_id="ASSET_INTRUDER",entity_id="CHAR_OUTSIDER",
                slot="identity_front",image_bytes=self.bytes,
                media_type="image/png")

    def test_snapshot_attachment_immutability_and_role_version_guard(self):
        f=editorial_fixture.EditorialReviewLockTests(
            "test_complete_review_locks_only_planning_snapshot")
        f.setUp()
        locked=review.lock_planning_snapshot(
            f.candidate,f.source,f.decide())
        empty=refs.create_empty(locked["plan"],locked["source_digest"])
        added=review.attach_reference_manifest(locked,f.source,empty)
        self.assertNotIn("asset_reference_manifest",locked)
        staged=review.stage_locked_team(added,f.source)
        self.assertEqual(staged["team"]["asset_reference_manifest_digest"],
                         team.fingerprint(empty))
        self.assertFalse(staged["reference_media_identity_verified"])
        packet=roles.build_role_messages(
            added["plan"],staged["team"],"director_brief",
            source_text=f.source,
            editorial_handoff=added["creative_handoff"],
            reference_manifest=added["asset_reference_manifest"])
        self.assertIn("versioned_reference_assets",
                      packet["messages"][1]["content"])
        self.assertNotIn("FICTIONAL_HEADER_ONLY",packet["messages"][1]["content"])
        # The old role state cannot silently run with another new manifest.
        old=review.stage_locked_team(locked,f.source)["team"]
        with self.assertRaisesRegex(Exception,
                                    "PILOT_LOCKED_REFERENCE_VERSION_DRIFT"):
            crew.inspect_locked_role(added,f.source,old,"director_brief")
        wrong=deepcopy(added)
        wrong["asset_reference_manifest"]["human_approved"]=True
        with self.assertRaisesRegex(review.EditorialReviewError,
                                    "ASSET_MANIFEST_INVALID"):
            review.stage_locked_team(wrong,f.source)

    def test_version_digest_tamper_rejected(self):
        f=editorial_fixture.EditorialReviewLockTests(
            "test_complete_review_locks_only_planning_snapshot")
        f.setUp()
        snap=review.lock_planning_snapshot(f.candidate,f.source,f.decide())
        m=refs.create_empty(snap["plan"],snap["source_digest"])
        locked=review.attach_reference_manifest(snap,f.source,m)
        locked["asset_reference_manifest_digest"]="0"*64
        with self.assertRaisesRegex(review.EditorialReviewError,
                                    "ASSET_MANIFEST_INVALID"):
            review.stage_locked_team(locked,f.source)


if __name__=="__main__":
    unittest.main()
