"""Versioned, source-locked reference cards using fictional valid in-memory PNGs.

No actual user photos, private paths, DeepSeek network or media generated.
Generated synthetic pixels can decode, but are NOT reference-quality proof.
"""
from __future__ import annotations
from copy import deepcopy
import json
import struct
import zlib
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
import test_agent_live_crew as crew_fixture
import agent_live_pilot as pilot
import production_delivery as delivery


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
        self.bytes=self.png(b"FICTIONAL_PRIMARY_ASSET")


    @staticmethod
    def png(seed, width=1, height=1):
        """Generate a 1x1 PNG using the stdlib, no personal photos."""
        def chunk(tag, payload):
            return (struct.pack(">I",len(payload))+tag+payload+
                    struct.pack(">I",zlib.crc32(tag+payload)&0xffffffff))
        pixel=hashlib.sha256(seed).digest()[:3]
        header=struct.pack(">IIBBBBB",width,height,8,2,0,0,0)
        return (b"\x89PNG\r\n\x1a\n"+
                chunk(b"IHDR",header)+
                chunk(b"IDAT",zlib.compress(b"\x00"+pixel))+
                chunk(b"IEND",b""))

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
        self.assertNotIn(self.bytes.hex(),json.dumps(after))
        self.assertNotIn("storage_path",json.dumps(after))
        check=refs.verify_bytes(after,"ASSET_CHAR01",1,self.bytes)
        self.assertTrue(check["sha256_matches"])
        self.assertFalse(check["identity_matches_persona"])
        self.assertFalse(check["rights_verified"])
        self.assertFalse(check["bytes_persisted_by_module"])
        self.assertTrue(check["pixels_decoded"])
        self.assertEqual(check["dimensions_px"],[1,1])

    def test_reject_content_hash_mismatch(self):
        after=self.register()
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "CONTENT_MISMATCH"):
            refs.verify_bytes(after,"ASSET_CHAR01",1,
                              self.bytes+b"changed")


    def test_magic_header_only_must_be_rejected(self):
        fake=b"\x89PNG\r\n\x1a\n"+b"NOT_A_DECODABLE_PNG"
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "ASSET_IMAGE_DECODE_INVALID"):
            self.register(raw=fake)

    def test_truncated_valid_image_must_be_rejected(self):
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "ASSET_IMAGE_DECODE_INVALID"):
            self.register(raw=self.bytes[:-13])
        self.assertEqual(self.manifest["cards"],{})

    def test_oversize_pixel_dimensions_must_be_rejected(self):
        fake=self.png(b"TOO_LARGE",width=9000,height=9000)
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "ASSET_IMAGE_DIMENSIONS_EXCEEDED"):
            self.register(raw=fake)

    def test_missing_decoder_must_fail_closed(self):
        with patch.dict(sys.modules,{"PIL":None,"PIL.Image":None}):
            with self.assertRaisesRegex(refs.AssetReferenceError,
                                        "ASSET_IMAGE_DECODER_UNAVAILABLE"):
                self.register()

    def test_unsafe_truncated_decoder_configuration_must_fail_closed(self):
        from PIL import ImageFile
        with patch.object(ImageFile,"LOAD_TRUNCATED_IMAGES",True):
            with self.assertRaisesRegex(refs.AssetReferenceError,
                                        "ASSET_IMAGE_DECODER_UNSAFE_CONFIGURATION"):
                self.register()

    def test_shot_reference_explicit_binding_and_revision_history(self):
        original=self.register()
        bound=self.bind_both(original)
        r=refs.validate(self.base,self.digest,bound)
        self.assertEqual(r["missing_bindings_count"],4)
        self.assertTrue(r["per_entity_references_consistent"])
        rev2=self.register(bound,raw=self.png(b"VERSION_TWO"))
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
            image_bytes=self.png(b"OTHER_VIEW"),media_type="image/png")
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

    def test_multi_slot_identity_and_wardrobe_bind_simultaneously(self):
        m=self.register()
        m=refs.register_image(
            self.base,self.digest,m,asset_id="ASSET_SIDE",
            entity_id="CHAR01",slot="identity_side",
            image_bytes=self.png(b"SECOND_VIEW"),media_type="image/png")
        m=refs.register_image(
            self.base,self.digest,m,asset_id="ASSET_WARDROBE",
            entity_id="CHAR01",slot="wardrobe",
            image_bytes=self.png(b"WARDROBE_BLUE"),media_type="image/png")
        for sid in ("S01","S02"):
            for aid in ("ASSET_CHAR01","ASSET_SIDE","ASSET_WARDROBE"):
                m=refs.bind_shot(self.base,self.digest,m,shot_id=sid,
                                 entity_id="CHAR01",asset_id=aid)
        report=refs.validate(self.base,self.digest,m)
        self.assertEqual(report["missing_bindings_count"],4)
        self.assertEqual(report["slot_binding_count"],6)
        self.assertEqual(m["shot_bindings"]["S01"]["CHAR01"]["asset_id"],
                         "ASSET_CHAR01")
        self.assertEqual(set(m["shot_slot_bindings"]["S01"]["CHAR01"]),
                         {"identity_front","identity_side","wardrobe"})
        self.assertFalse(report["reference_switches"])
        self.assertEqual(report["missing_recommended_slot_count"],4)
        self.assertNotIn("FICTIONAL_HEADER_ONLY",json.dumps(m))

    def test_wardrobe_switch_detected_without_face_switch(self):
        m=self.register()
        for asset,suffix in (("WARDROBE_BLUE",b"BLUE"),
                             ("WARDROBE_RED",b"RED")):
            m=refs.register_image(
                self.base,self.digest,m,asset_id=asset,
                entity_id="CHAR01",slot="wardrobe",
                image_bytes=self.bytes+suffix,media_type="image/png")
        for sid,wardrobe in (("S01","WARDROBE_BLUE"),
                             ("S02","WARDROBE_RED")):
            m=refs.bind_shot(self.base,self.digest,m,shot_id=sid,
                             entity_id="CHAR01",asset_id="ASSET_CHAR01")
            m=refs.bind_shot(self.base,self.digest,m,shot_id=sid,
                             entity_id="CHAR01",asset_id=wardrobe)
        report=refs.validate(self.base,self.digest,m)
        changes=[v for v in report["reference_switches"]
                 if v["slot"]=="wardrobe"]
        self.assertEqual(len(changes),1)
        self.assertEqual(changes[0]["shot_id"],"S02")
        self.assertFalse(report["per_entity_references_consistent"])
        self.assertEqual(m["shot_bindings"]["S01"]["CHAR01"],
                         m["shot_bindings"]["S02"]["CHAR01"])

    def test_changing_wardrobe_version_invalidates_specific_slot_binding(self):
        m=self.register()
        m=refs.register_image(
            self.base,self.digest,m,asset_id="ASSET_WARDROBE",
            entity_id="CHAR01",slot="wardrobe",
            image_bytes=self.png(b"FIRST"),media_type="image/png")
        for sid in ("S01","S02"):
            m=refs.bind_shot(self.base,self.digest,m,shot_id=sid,
                             entity_id="CHAR01",asset_id="ASSET_CHAR01")
            m=refs.bind_shot(self.base,self.digest,m,shot_id=sid,
                             entity_id="CHAR01",asset_id="ASSET_WARDROBE")
        m=refs.register_image(
            self.base,self.digest,m,asset_id="ASSET_WARDROBE",
            entity_id="CHAR01",slot="wardrobe",
            image_bytes=self.png(b"CHANGED"),media_type="image/png")
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "STALE_OR_WRONG_ENTITY"):
            refs.validate(self.base,self.digest,m)
        m=refs.bind_shot(self.base,self.digest,m,shot_id="S01",
                         entity_id="CHAR01",asset_id="ASSET_WARDROBE")
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "STALE_OR_WRONG_ENTITY"):
            refs.validate(self.base,self.digest,m)
        m=refs.bind_shot(self.base,self.digest,m,shot_id="S02",
                         entity_id="CHAR01",asset_id="ASSET_WARDROBE")
        report=refs.validate(self.base,self.digest,m)
        self.assertTrue(report["per_entity_references_consistent"])
        self.assertEqual(m["shot_bindings"]["S01"]["CHAR01"]["asset_id"],
                         "ASSET_CHAR01")
        self.assertEqual(m["shot_slot_bindings"]["S02"]["CHAR01"][
            "wardrobe"]["version"],2)

    def test_injected_slot_or_entity_reference_is_rejected(self):
        m=self.bind_both(self.register())
        wrong=deepcopy(m)
        wrong["shot_slot_bindings"]["S01"]["CHAR01"]["wardrobe"]=deepcopy(
            wrong["shot_bindings"]["S01"]["CHAR01"])
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "STALE_OR_WRONG_ENTITY"):
            refs.validate(self.base,self.digest,wrong)
        wrong=deepcopy(m)
        wrong["shot_slot_bindings"]["S01"]["CHAR01"]["untrusted_url"]={}
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "SLOT_BINDINGS_INVALID"):
            refs.validate(self.base,self.digest,wrong)
        wrong=deepcopy(m)
        wrong["shot_slot_bindings"]["S01"]["PERSON_NOT_IN_SCRIPT"]={}
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "ENTITY_BINDINGS_INVALID"):
            refs.validate(self.base,self.digest,wrong)
        wrong=deepcopy(m)
        wrong["shot_bindings"]["S01"]["CHAR01"]=None
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "PRIMARY_MISSING_WITH_SLOTS"):
            refs.validate(self.base,self.digest,wrong)

    def test_old_v1_manifest_fails_closed_requires_explicit_migration(self):
        old=deepcopy(self.manifest)
        old["version"]="private-visual-reference-manifest-v1"
        old.pop("shot_slot_bindings")
        with self.assertRaisesRegex(refs.AssetReferenceError,
                                    "SOURCE_OR_AUTHORITY_INVALID"):
            refs.validate(self.base,self.digest,old)

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
        self.assertIn("unbound_references",
                      packet["messages"][1]["content"])
        self.assertIn("shot_slot_bindings",
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

    def test_full_synthetic_ten_role_delivery_only_exports_reference_metadata(self):
        f=crew_fixture.LockedCrewPilotTests(
            "test_full_chain_exports_real_video_model_work_orders_not_only_team_flags")
        f.setUp()
        self.addCleanup(f.doCleanups)
        original_snapshot=deepcopy(f.snapshot)
        manifest=refs.create_empty(f.plan,f.state["source_digest"])
        # Bind a fictional location image to each shot with LOC01, if present.
        scene_id=f.plan["shots"][0].get("scene_id")
        if scene_id is not None:
            manifest=refs.register_image(
                f.plan,f.state["source_digest"],manifest,
                asset_id="ASSET_ROOM01",entity_id=scene_id,
                slot="location_reference",image_bytes=self.bytes,
                media_type="image/png")
            for sh in f.plan["shots"]:
                if sh.get("scene_id")==scene_id:
                    manifest=refs.bind_shot(
                        f.plan,f.state["source_digest"],manifest,
                        shot_id=sh["id"],entity_id=scene_id,
                        asset_id="ASSET_ROOM01")
        f.snapshot=review.attach_reference_manifest(
            original_snapshot,f.original,manifest)
        f.state=review.stage_locked_team(f.snapshot,f.original)["team"]
        self.assertIsNotNone(f.state["asset_reference_manifest_digest"])
        with pilot.PilotJournal(f.tmp.name,f.config) as journal:
            state=f.state
            for task in team.SPECS:
                state,_=f._step(journal,state,task)
        report=delivery.build_locked_crew_delivery(f.snapshot,f.original,state)
        self.assertIn("reference_manifest_review",report)
        self.assertEqual(report["reference_manifest_review"]["manifest_digest"],
                         team.fingerprint(manifest))
        self.assertFalse(report["reference_manifest_review"]["visual_identity_verified"])
        self.assertFalse(report["reference_manifest_review"]["rights_verified"])
        self.assertIn("missing_bindings",
                      report["reference_manifest_review"])
        self.assertIn("reference_switches_needing_review",
                      report["reference_manifest_review"])
        self.assertFalse(report["ready_to_call_video_model"])
        for work in report["shots"]:
            self.assertIn("versioned_reference_bindings",work)
            self.assertIn("versioned_reference_slot_bindings",work)
            self.assertEqual(
                work["versioned_reference_slot_bindings"],
                manifest["shot_slot_bindings"][work["shot_id"]])
        rendered=delivery.render_operator_markdown(report)
        self.assertIn("版本锁定的参考资产",rendered)
        self.assertIn("按用途分别锁定的参考资产",rendered)
        self.assertNotIn("FICTIONAL_HEADER_ONLY",rendered)
        self.assertNotIn("human_approved=true",rendered)

    def test_final_delivery_cannot_use_state_from_other_asset_snapshot(self):
        f=crew_fixture.LockedCrewPilotTests(
            "test_full_chain_exports_real_video_model_work_orders_not_only_team_flags")
        f.setUp()
        self.addCleanup(f.doCleanups)
        empty=refs.create_empty(f.plan,f.state["source_digest"])
        new_snapshot=review.attach_reference_manifest(
            f.snapshot,f.original,empty)
        with pilot.PilotJournal(f.tmp.name,f.config) as journal:
            state=f.state
            for task in team.SPECS:
                state,_=f._step(journal,state,task)
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "REFERENCE_MANIFEST_CHANGED"):
            delivery.build_locked_crew_delivery(
                new_snapshot,f.original,state)

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
