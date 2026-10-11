"""Asset-registry regressions. Synthetic image headers only; no private media."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import reference_assets as refs
import director_v2 as v2


class ReferenceAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = v2.read_json(ROOT / "examples/quit-smoking/plan.json")
        cls.direction = v2.read_json(ROOT / "examples/quit-smoking/direction_v02.json")

    def setup_manifest(self):
        return refs.scaffold(self.base, self.direction)

    def test_scaffold_has_stable_character_scene_ids_and_missing_views(self):
        m = self.setup_manifest()
        self.assertIn("CHAR01", m["assets"])
        self.assertIn("LOC01", m["assets"])
        self.assertEqual(m["assets"]["CHAR01"]["kind"], "character")
        self.assertEqual(set(m["assets"]["CHAR01"]["views"]), {"front","three_quarter","full_body"})
        self.assertEqual(m["assets"]["CHAR01"]["views"]["front"]["status"],"not_created")
        self.assertFalse(m["policy"]["identity_consistency_verified"])
        self.assertFalse(m["policy"]["private_media_in_public_repo"])
        self.assertEqual(len(m["shot_requirements"]),len(self.base["shots"]))

    def test_offscreen_character_does_not_require_reference(self):
        m = self.setup_manifest()
        self.assertNotIn("CHAR01",[b["asset_id"] for b in m["shot_requirements"]["S02"]])

    def test_missing_reference_is_visible_not_approved(self):
        result = refs.audit(self.base, self.direction, self.setup_manifest())
        self.assertEqual(result["blockers"],0)
        self.assertGreater(result["missing"],0)
        self.assertFalse(result["ready_for_reference_preflight"])
        self.assertFalse(result["human_visual_consistency_verified"])

    def test_unknown_reference_is_blocked(self):
        m = self.setup_manifest()
        m["shot_requirements"]["S01"].append({"asset_id":"CH_UNKNOWN","view":"front","role":"identity"})
        report = refs.audit(self.base, self.direction, m)
        self.assertIn("UNKNOWN_ASSET",[f["code"] for f in report["findings"]])
        self.assertGreater(report["blockers"],0)

    def test_missing_asset_view_is_blocked(self):
        m = self.setup_manifest()
        del m["assets"]["CHAR01"]["views"]["three_quarter"]
        codes = [f["code"] for f in refs.audit(self.base,self.direction,m)["findings"]]
        self.assertIn("MISSING_VIEW",codes)

    def test_removed_compulsory_binding_is_reported(self):
        m = self.setup_manifest()
        m["shot_requirements"]["S01"]=[]
        codes=[f["code"] for f in refs.audit(self.base,self.direction,m)["findings"]]
        self.assertIn("REQUIRED_REFERENCE_UNBOUND", codes)

    def test_unknown_asset_kind_is_blocked(self):
        m = self.setup_manifest()
        m["assets"]["CHAR01"]["kind"]="location"
        self.assertGreater(refs.audit(self.base,self.direction,m)["blockers"],0)

    def test_prop_from_continuity_contract_can_be_bound_explicitly(self):
        b=copy.deepcopy(self.base)
        b["continuity_contract"]={"props":{"PROP_KEY":{"label":"key","initial":"LOC01:table"}}}
        d=copy.deepcopy(self.direction)
        d["shots"][0]["generation"]["reference_bindings"]=[
            {"asset_id":"PROP_KEY","view":"detail","role":"continuity"}]
        m=refs.scaffold(b,d)
        self.assertEqual(m["assets"]["PROP_KEY"]["kind"],"prop")
        self.assertIn("PROP_KEY",[x["asset_id"] for x in m["shot_requirements"]["S01"]])
        self.assertIn("REFERENCE_NOT_READY",[x["code"] for x in refs.audit(b,d,m)["findings"]])

    def test_cannot_claim_approved_without_provenance(self):
        m=self.setup_manifest()
        m["assets"]["CHAR01"]["views"]["three_quarter"]["status"]="approved"
        report=refs.audit(self.base,self.direction,m)
        self.assertIn("APPROVAL_EVIDENCE_MISSING",[f["code"] for f in report["findings"]])
        self.assertFalse(report["ready_for_reference_preflight"])

    def test_candidate_cannot_claim_human_approval(self):
        m=self.setup_manifest()
        record=m["assets"]["CHAR01"]["views"]["three_quarter"]
        record["status"]="candidate"
        record["human_approved"]=True
        self.assertIn("UNAPPROVED_MARKED_APPROVED",
                      [f["code"] for f in refs.audit(self.base,self.direction,m)["findings"]])

    def test_private_asset_path_escape_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in ("../outside.png","/etc/passwd","sub\\unsafe.png","sub/../../outside.png"):
                p,err=refs._safe_image(tmp,path)
                self.assertIsNone(p,path)
                self.assertTrue(err,path)

    def test_file_hash_and_metadata_gate(self):
        m=self.setup_manifest()
        for asset in m["assets"].values():
            for view in asset["views"].values():
                view.update(status="approved",human_approved=True,
                            rights_status="verified",source="self_generated",
                            rights_evidence="manual creator rights review",
                            reviewer="human",path="ref.png")
        with tempfile.TemporaryDirectory() as tmp:
            # A synthetic signature-only test file: checks bytes and paths,
            # NOT actual image decode, face similarity or artistic quality.
            p=Path(tmp)/"ref.png"
            p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"synthetic fixture")
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            for asset in m["assets"].values():
                for view in asset["views"].values():
                    view["sha256"]=digest
            report=refs.audit(self.base,self.direction,m,tmp)
            self.assertEqual(report["blockers"],0,report["findings"])
            self.assertEqual(report["missing"],0,report["findings"])
            self.assertTrue(report["ready_for_reference_preflight"])
            self.assertFalse(report["human_visual_consistency_verified"])
            m["assets"]["CHAR01"]["views"]["three_quarter"]["sha256"]="0"*64
            report=refs.audit(self.base,self.direction,m,tmp)
            self.assertIn("IMAGE_DIGEST_MISMATCH",[f["code"] for f in report["findings"]])
            self.assertFalse(report["ready_for_reference_preflight"])

    def test_approved_missing_root_is_not_ready(self):
        m=self.setup_manifest()
        rec=m["assets"]["CHAR01"]["views"]["three_quarter"]
        rec.update(status="approved",human_approved=True,rights_status="verified",
                   source="self_generated",rights_evidence="proof",reviewer="human",
                   path="ref.png",sha256="a"*64)
        report=refs.audit(self.base,self.direction,m)
        self.assertIn("FILE_NOT_CHECKED",[f["code"] for f in report["findings"]])
        self.assertFalse(report["ready_for_reference_preflight"])

    def test_director_compiler_has_reference_preflight_but_does_not_generate(self):
        m=self.setup_manifest()
        errors,warnings=v2.validate(self.base,self.direction,m)
        self.assertEqual(errors,[])
        self.assertTrue(any("missing/unverified" in w for w in warnings))
        pack=v2.compile_package(self.base,self.direction,m)
        self.assertFalse(pack["reference_asset_preflight"]["ready_for_reference_preflight"])
        self.assertTrue(pack["not_generated_video"])
        self.assertFalse(pack["publishing_allowed"])
        self.assertFalse(pack["shots"][0]["reference_preflight_ready"])
        self.assertFalse(pack["shots"][0]["reference_media_supplied"])

    def test_legacy_without_manifest_is_backward_compatible(self):
        errors,_=v2.validate(self.base,self.direction)
        self.assertEqual(errors,[])
        pack=v2.compile_package(self.base,self.direction)
        self.assertEqual(pack["reference_asset_preflight"]["status"],"not_assessed")

    def test_manifest_is_not_saved_by_scaffold_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"asset_catalog.json"
            command=[sys.executable,str(ROOT/"reference_assets.py"),"scaffold",
                     "--base",str(ROOT/"examples/quit-smoking/plan.json"),
                     "--direction",str(ROOT/"examples/quit-smoking/direction_v02.json"),
                     "--out",str(target)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(target.exists())
            original=target.read_bytes()
            second=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(target.read_bytes(),original)

    def test_director_cli_compiles_with_optional_asset_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            manifest=root/"catalog.json"
            manifest.write_text(json.dumps(self.setup_manifest()),encoding="utf-8")
            out=root/"compiled.json"
            command=[sys.executable,str(ROOT/"director_v2.py"),"compile",
                     "--base",str(ROOT/"examples/quit-smoking/plan.json"),
                     "--direction",str(ROOT/"examples/quit-smoking/direction_v02.json"),
                     "--assets",str(manifest),"--out",str(out)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn("reference_asset_preflight",json.loads(out.read_text()))
