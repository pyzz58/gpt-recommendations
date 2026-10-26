"""W16 shared revision and paired commit tests with owned synthetic records."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from intelligence.archive import Archive, Conflict
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState, Representation,
                                    RightsBasis, RightsGrant, Scope, ScopeMode, UsePermission,
                                    ValidityMode, VersionSubmission)
from intelligence.research import (ArtifactLink, ResearchCommitRequest, ResearchError,
                                   ResearchRevision, ResearchRevisionController, ResearchRole)

AT=datetime(2026,10,25,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic research revision fixture\n"


class ResearchRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.rights=RightsGrant(rights_id="RIGHTS-RESEARCH",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic research journal",checked_by="test fixture",checked_at=AT,
            permissions=(UsePermission(use=MaterialUse.STORE_BODY,state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),content_scope=Scope(mode=ScopeMode.ANY)),))
        self.controller=ResearchRevisionController(self.archive,self.rights)
        self.artifact("ADVISER-1","ADVISER-1-v001")
        self.artifact("TEACHER-1","TEACHER-1-v001")

    def artifact(self, object_id, version_id, spec=SPEC):
        return self.archive.append(VersionSubmission(
            object_id=object_id,version_id=version_id,kind=ObjectKind.ARTICLE,title=object_id,
            spec_sha256=spec,created_at=AT,rights=self.rights,
            representation=Representation.FULL_BODY),BODY)

    def revision(self, revision_id, parent=None, created_at=AT, spec=SPEC):
        return ResearchRevision(revision_id=revision_id,theme_id="THEME-1",spec_sha256=spec,
            based_on_revision_id=parent,input_version_ids=(),reason="Owned fixture revision update",
            created_at=created_at)

    def link(self, link_id, revision_id, artifact_id, role, created_at=AT):
        return ArtifactLink(link_id=link_id,theme_id="THEME-1",revision_id=revision_id,
            artifact_version_id=artifact_id,role=role,created_at=created_at)

    def request(self, commit_id, revision_id, links, expected=None, created_at=AT):
        return ResearchCommitRequest(commit_id=commit_id,theme_id="THEME-1",spec_sha256=SPEC,
            revision_id=revision_id,link_ids=tuple(links),expected_commit_id=expected,
            created_at=created_at)

    def test_paired_outputs_commit_to_one_current_revision(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        self.controller.append_artifact_link(self.link("LINK-A-v001","REV-THEME-1-v001",
            "ADVISER-1-v001",ResearchRole.ADVISER))
        self.controller.append_artifact_link(self.link("LINK-T-v001","REV-THEME-1-v001",
            "TEACHER-1-v001",ResearchRole.TEACHER))
        self.controller.commit(self.request("COMMIT-THEME-1-v001","REV-THEME-1-v001",
            ("LINK-A-v001","LINK-T-v001")))
        current=self.controller.current_commit("THEME-1")
        self.assertEqual({item.role for item in current.artifacts},
                         {ResearchRole.ADVISER,ResearchRole.TEACHER})
        self.assertTrue(self.controller.is_current(current.commit_id))

    def test_b1_new_revision_with_b2_old_revision_is_rejected(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        self.controller.append_artifact_link(self.link("LINK-A-v001","REV-THEME-1-v001",
            "ADVISER-1-v001",ResearchRole.ADVISER))
        self.controller.append_artifact_link(self.link("LINK-T-v001","REV-THEME-1-v001",
            "TEACHER-1-v001",ResearchRole.TEACHER))
        self.controller.append_revision(self.revision("REV-THEME-1-v002","REV-THEME-1-v001",
            created_at=AT+timedelta(minutes=1)),"REV-THEME-1-v001")
        self.controller.append_artifact_link(self.link("LINK-A-v002","REV-THEME-1-v002",
            "ADVISER-1-v001",ResearchRole.ADVISER,AT+timedelta(minutes=2)))
        with self.assertRaisesRegex(ResearchError,"exact research revision"):
            self.controller.commit(self.request("COMMIT-THEME-1-v001","REV-THEME-1-v002",
                ("LINK-A-v002","LINK-T-v001"),created_at=AT+timedelta(minutes=3)))

    def test_new_revision_invalidates_old_commit_and_stale_writer_cannot_overwrite(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        self.controller.append_artifact_link(self.link("LINK-A-v001","REV-THEME-1-v001",
            "ADVISER-1-v001",ResearchRole.ADVISER))
        self.controller.append_artifact_link(self.link("LINK-T-v001","REV-THEME-1-v001",
            "TEACHER-1-v001",ResearchRole.TEACHER))
        self.controller.commit(self.request("COMMIT-THEME-1-v001","REV-THEME-1-v001",
            ("LINK-A-v001","LINK-T-v001")))
        self.controller.append_revision(self.revision("REV-THEME-1-v002","REV-THEME-1-v001",
            created_at=AT+timedelta(minutes=1)),"REV-THEME-1-v001")
        self.assertFalse(self.controller.is_current("COMMIT-THEME-1-v001"))
        def writer(suffix):
            with Archive(self.archive.root) as archive:
                controller=ResearchRevisionController(archive,self.rights)
                try:
                    controller.append_revision(self.revision(
                        f"REV-THEME-1-{suffix}","REV-THEME-1-v002",
                        created_at=AT+timedelta(minutes=2)),"REV-THEME-1-v002")
                    return "committed"
                except Conflict:
                    return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(writer,("v003","v004")))
        self.assertEqual(sorted(outcomes),["committed","conflict"])
        self.assertFalse(self.controller.is_current("COMMIT-THEME-1-v001"))

    def test_stale_commit_writer_loses_without_overwriting_current_commit(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        self.controller.append_artifact_link(self.link("LINK-A-v001","REV-THEME-1-v001",
            "ADVISER-1-v001",ResearchRole.ADVISER))
        self.controller.append_artifact_link(self.link("LINK-T-v001","REV-THEME-1-v001",
            "TEACHER-1-v001",ResearchRole.TEACHER))
        def writer(suffix):
            with Archive(self.archive.root) as archive:
                controller=ResearchRevisionController(archive,self.rights)
                try:
                    controller.commit(self.request(f"COMMIT-THEME-1-{suffix}",
                        "REV-THEME-1-v001",("LINK-A-v001","LINK-T-v001")))
                    return "committed"
                except Conflict:
                    return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(writer,("v001","v002")))
        self.assertEqual(sorted(outcomes),["committed","conflict"])
        self.assertTrue(self.controller.current_commit("THEME-1").commit_id)

    def test_spec_mismatch_and_unbound_stale_revision_are_rejected(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        self.controller.append_artifact_link(self.link("LINK-A-v001","REV-THEME-1-v001",
            "ADVISER-1-v001",ResearchRole.ADVISER))
        bad=self.artifact("OTHER","OTHER-v001",spec="b"*64)
        self.assertEqual(bad.submission.version_id,"OTHER-v001")
        with self.assertRaisesRegex(ResearchError,"different specification"):
            self.controller.append_artifact_link(self.link("LINK-X-v001","REV-THEME-1-v001",
                "OTHER-v001",ResearchRole.REVIEW))
        with self.assertRaises(Conflict):
            self.controller.append_revision(self.revision("REV-THEME-1-v002","MISSING-PARENT",
                created_at=AT+timedelta(minutes=1)),"MISSING-PARENT")


if __name__=="__main__":
    unittest.main()
