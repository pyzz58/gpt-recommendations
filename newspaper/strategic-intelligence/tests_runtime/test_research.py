"""W16 shared revision and paired commit tests with owned synthetic records."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from intelligence.archive import Archive, Conflict
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState, ReferenceUse,
                                    Representation, RightsBasis, RightsGrant, Scope, ScopeMode,
                                    UsePermission, ValidityMode, VersionReference,
                                    VersionSubmission)
from intelligence.research import (ArtifactCompatibility, ArtifactLink, ResearchCommitRequest,
                                   ResearchError, ResearchRevision,
                                   ResearchRevisionController, ResearchRole)

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

    def artifact(self, object_id, version_id, spec=SPEC, *, kind=ObjectKind.ARTICLE,
                 refs=(), body=BODY):
        return self.archive.append(VersionSubmission(
            object_id=object_id,version_id=version_id,kind=kind,title=object_id,
            spec_sha256=spec,created_at=AT,rights=self.rights,
            representation=Representation.FULL_BODY,references=tuple(refs)),body)

    def revision(self, revision_id, parent=None, created_at=AT, spec=SPEC,
                 inputs=(), evidence=(), noncritical=()):
        return ResearchRevision(revision_id=revision_id,theme_id="THEME-1",spec_sha256=spec,
            based_on_revision_id=parent,input_version_ids=tuple(inputs),
            evidence_version_ids=tuple(evidence),
            noncritical_input_version_ids=tuple(noncritical),
            reason="Owned fixture revision update",created_at=created_at)

    def link(self, link_id, revision_id, artifact_id, role, created_at=AT,
             basis=(), compatibility=None):
        return ArtifactLink(link_id=link_id,theme_id="THEME-1",revision_id=revision_id,
            artifact_version_id=artifact_id,role=role,
            basis_version_ids=tuple(basis),compatibility_id=compatibility,
            created_at=created_at)

    def request(self, commit_id, revision_id, links, expected=None, created_at=AT):
        return ResearchCommitRequest(commit_id=commit_id,theme_id="THEME-1",spec_sha256=SPEC,
            revision_id=revision_id,link_ids=tuple(links),expected_commit_id=expected,
            created_at=created_at)

    def review(self, version_id, refs, created_at=AT):
        return self.artifact("REVIEW-"+version_id,version_id,kind=ObjectKind.REVIEW,
            refs=tuple(refs),body=b"Owned synthetic compatibility Review\n")

    def compatibility(self, compatibility_id, artifact_id, source, target, review_id,
                      reviewed_inputs, *, added=(), removed=(), created_at=AT):
        return ArtifactCompatibility(compatibility_id=compatibility_id,theme_id="THEME-1",
            artifact_version_id=artifact_id,source_revision_id=source,
            target_revision_id=target,review_version_id=review_id,
            reviewed_input_version_ids=tuple(reviewed_inputs),
            accepted_added_input_version_ids=tuple(added),
            accepted_removed_dependency_ids=tuple(removed),
            reason="Owned non-critical compatibility fixture",created_at=created_at)

    def bound_artifact(self, object_id, version_id, revision_id, *, inputs=(), spec=SPEC):
        refs=[
            VersionReference(target_version_id=revision_id,
                use=ReferenceUse.BASIS,locator="exact research revision"),
        ]
        refs.extend(VersionReference(target_version_id=version_id,
            use=ReferenceUse.SUPPORT,locator=f"input {index}")
            for index,version_id in enumerate(inputs))
        return self.artifact(object_id,version_id,spec=spec,refs=tuple(refs))

    def linked_pair(self, revision_id, *, inputs=()):
        result={}
        for role,label,object_id in (
                (ResearchRole.ADVISER,"A","PAIR-ADVISER-"+revision_id),
                (ResearchRole.TEACHER,"T","PAIR-TEACHER-"+revision_id)):
            artifact_id=f"{object_id}-v001"
            link_id=f"PAIR-LINK-{label}-{revision_id}-v001"
            self.bound_artifact(object_id,artifact_id,revision_id,inputs=inputs)
            self.controller.append_artifact_link(self.link(
                link_id,revision_id,artifact_id,role,basis=tuple(inputs)))
            result[role]=(artifact_id,link_id)
        return result

    def test_paired_outputs_commit_to_one_current_revision(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        pair=self.linked_pair("REV-THEME-1-v001")
        self.controller.commit(self.request("COMMIT-THEME-1-v001","REV-THEME-1-v001",
            (pair[ResearchRole.ADVISER][1],pair[ResearchRole.TEACHER][1])))
        current=self.controller.current_commit("THEME-1")
        self.assertEqual({item.role for item in current.artifacts},
                         {ResearchRole.ADVISER,ResearchRole.TEACHER})
        self.assertTrue(self.controller.is_current(current.commit_id))

    def test_b1_new_revision_with_b2_old_revision_is_rejected(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        pair=self.linked_pair("REV-THEME-1-v001")
        self.controller.append_revision(self.revision("REV-THEME-1-v002","REV-THEME-1-v001",
            created_at=AT+timedelta(minutes=1)),"REV-THEME-1-v001")
        self.bound_artifact("ADVISER-NEW","ADVISER-NEW-v001","REV-THEME-1-v002")
        self.controller.append_artifact_link(self.link("LINK-A-v002","REV-THEME-1-v002",
            "ADVISER-NEW-v001",ResearchRole.ADVISER,AT+timedelta(minutes=2)))
        with self.assertRaisesRegex(ResearchError,"exact research revision"):
            self.controller.commit(self.request("COMMIT-THEME-1-v001","REV-THEME-1-v002",
                ("LINK-A-v002",pair[ResearchRole.TEACHER][1]),
                created_at=AT+timedelta(minutes=3)))

    def test_new_revision_invalidates_old_commit_and_stale_writer_cannot_overwrite(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        pair=self.linked_pair("REV-THEME-1-v001")
        self.controller.commit(self.request("COMMIT-THEME-1-v001","REV-THEME-1-v001",
            (pair[ResearchRole.ADVISER][1],pair[ResearchRole.TEACHER][1])))
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
        pair=self.linked_pair("REV-THEME-1-v001")
        link_ids=(pair[ResearchRole.ADVISER][1],pair[ResearchRole.TEACHER][1])
        def writer(suffix):
            with Archive(self.archive.root) as archive:
                controller=ResearchRevisionController(archive,self.rights)
                try:
                    controller.commit(self.request(f"COMMIT-THEME-1-{suffix}",
                        "REV-THEME-1-v001",link_ids))
                    return "committed"
                except Conflict:
                    return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(writer,("v001","v002")))
        self.assertEqual(sorted(outcomes),["committed","conflict"])
        self.assertTrue(self.controller.current_commit("THEME-1").commit_id)

    def test_critical_evidence_change_cannot_be_relabelled_by_new_links(self):
        evidence_v1=self.artifact("EVIDENCE","EVIDENCE-v001",kind=ObjectKind.EVIDENCE)
        self.controller.append_revision(self.revision(
            "REV-THEME-1-v001",inputs=("EVIDENCE-v001",),
            evidence=("EVIDENCE-v001",)),None)
        old_refs=(
            VersionReference(target_version_id="REV-THEME-1-v001",
                use=ReferenceUse.BASIS,locator="original revision"),
            VersionReference(target_version_id="EVIDENCE-v001",
                use=ReferenceUse.SUPPORT,locator="decisive evidence v1"),
        )
        self.artifact("OLD-ADVISER","OLD-ADVISER-v001",refs=old_refs)
        self.artifact("OLD-TEACHER","OLD-TEACHER-v001",refs=old_refs)
        self.archive.append(VersionSubmission(
            object_id="EVIDENCE",version_id="EVIDENCE-v002",
            parent_version_id="EVIDENCE-v001",kind=ObjectKind.EVIDENCE,
            title="EVIDENCE",spec_sha256=SPEC,created_at=AT,rights=self.rights,
            representation=Representation.FULL_BODY),b"Owned corrected decisive evidence\n")
        self.controller.append_revision(self.revision(
            "REV-THEME-1-v002","REV-THEME-1-v001",created_at=AT+timedelta(minutes=1),
            inputs=("EVIDENCE-v002",),evidence=("EVIDENCE-v002",)),"REV-THEME-1-v001")
        self.controller.append_artifact_link(self.link(
            "LINK-OLD-A","REV-THEME-1-v002","OLD-ADVISER-v001",
            ResearchRole.ADVISER,basis=("EVIDENCE-v001",),
            created_at=AT+timedelta(minutes=2)))
        self.controller.append_artifact_link(self.link(
            "LINK-OLD-T","REV-THEME-1-v002","OLD-TEACHER-v001",
            ResearchRole.TEACHER,basis=("EVIDENCE-v001",),
            created_at=AT+timedelta(minutes=2)))
        with self.assertRaisesRegex(ResearchError,"compatibility|critical"):
            self.controller.commit(self.request("COMMIT-CRITICAL",
                "REV-THEME-1-v002",("LINK-OLD-A","LINK-OLD-T"),
                created_at=AT+timedelta(minutes=3)))

        review_refs=(
            VersionReference(target_version_id="OLD-ADVISER-v001",
                use=ReferenceUse.REVIEW_OF,locator="artifact"),
            VersionReference(target_version_id="REV-THEME-1-v001",
                use=ReferenceUse.REVIEW_OF,locator="source revision"),
            VersionReference(target_version_id="REV-THEME-1-v002",
                use=ReferenceUse.REVIEW_OF,locator="target revision"),
        )
        self.review("REVIEW-CRITICAL-v001",review_refs)
        with self.assertRaisesRegex(ResearchError,"critical added"):
            self.controller.append_compatibility(self.compatibility(
                "COMPAT-CRITICAL-v001","OLD-ADVISER-v001",
                "REV-THEME-1-v001","REV-THEME-1-v002","REVIEW-CRITICAL-v001",
                ("EVIDENCE-v002",),added=("EVIDENCE-v002",),
                removed=("EVIDENCE-v001",)))

    def test_old_artifact_cannot_be_relabelled_even_when_target_inputs_are_empty(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        old_refs=(VersionReference(target_version_id="REV-THEME-1-v001",
            use=ReferenceUse.BASIS,locator="original revision"),)
        self.artifact("OLD-EMPTY-A","OLD-EMPTY-A-v001",refs=old_refs)
        self.artifact("OLD-EMPTY-T","OLD-EMPTY-T-v001",refs=old_refs)
        self.controller.append_revision(self.revision(
            "REV-THEME-1-v002","REV-THEME-1-v001",
            created_at=AT+timedelta(minutes=1)),"REV-THEME-1-v001")
        self.controller.append_artifact_link(self.link(
            "LINK-EMPTY-A","REV-THEME-1-v002","OLD-EMPTY-A-v001",
            ResearchRole.ADVISER,created_at=AT+timedelta(minutes=2)))
        self.controller.append_artifact_link(self.link(
            "LINK-EMPTY-T","REV-THEME-1-v002","OLD-EMPTY-T-v001",
            ResearchRole.TEACHER,created_at=AT+timedelta(minutes=2)))
        with self.assertRaisesRegex(ResearchError,"compatibility"):
            self.controller.commit(self.request("COMMIT-EMPTY",
                "REV-THEME-1-v002",("LINK-EMPTY-A","LINK-EMPTY-T"),
                created_at=AT+timedelta(minutes=3)))

    def test_explicit_compatibility_accepts_only_unrelated_material_change(self):
        self.artifact("EVIDENCE","EVIDENCE-v001",kind=ObjectKind.EVIDENCE)
        self.artifact("BACKGROUND","BACKGROUND-v002",kind=ObjectKind.BACKGROUND,
            body=b"Owned unrelated background addition\n")
        self.controller.append_revision(self.revision(
            "REV-THEME-1-v001",inputs=("EVIDENCE-v001",),
            evidence=("EVIDENCE-v001",)),None)
        old_refs=(
            VersionReference(target_version_id="REV-THEME-1-v001",
                use=ReferenceUse.BASIS,locator="original revision"),
            VersionReference(target_version_id="EVIDENCE-v001",
                use=ReferenceUse.SUPPORT,locator="unchanged evidence"),
        )
        self.artifact("OLD-ADVISER","OLD-ADVISER-v001",refs=old_refs)
        self.controller.append_revision(self.revision(
            "REV-THEME-1-v002","REV-THEME-1-v001",created_at=AT+timedelta(minutes=1),
            inputs=("EVIDENCE-v001","BACKGROUND-v002"),
            evidence=("EVIDENCE-v001",),noncritical=("BACKGROUND-v002",)),
            "REV-THEME-1-v001")
        review_refs=(
            VersionReference(target_version_id="OLD-ADVISER-v001",
                use=ReferenceUse.REVIEW_OF,locator="artifact"),
            VersionReference(target_version_id="REV-THEME-1-v001",
                use=ReferenceUse.REVIEW_OF,locator="source revision"),
            VersionReference(target_version_id="REV-THEME-1-v002",
                use=ReferenceUse.REVIEW_OF,locator="target revision"),
        )
        self.review("REVIEW-COMPAT-v001",review_refs)
        self.controller.append_compatibility(self.compatibility(
            "COMPAT-v001","OLD-ADVISER-v001","REV-THEME-1-v001",
            "REV-THEME-1-v002","REVIEW-COMPAT-v001",
            ("EVIDENCE-v001","BACKGROUND-v002"),added=("BACKGROUND-v002",),
            created_at=AT+timedelta(minutes=2)))
        self.controller.append_artifact_link(self.link(
            "LINK-COMPAT-A","REV-THEME-1-v002","OLD-ADVISER-v001",
            ResearchRole.ADVISER,basis=("EVIDENCE-v001",),
            compatibility="COMPAT-v001",created_at=AT+timedelta(minutes=3)))
        rebuilt_refs=(
            VersionReference(target_version_id="REV-THEME-1-v002",
                use=ReferenceUse.BASIS,locator="target revision"),
            VersionReference(target_version_id="EVIDENCE-v001",
                use=ReferenceUse.SUPPORT,locator="unchanged evidence"),
            VersionReference(target_version_id="BACKGROUND-v002",
                use=ReferenceUse.SUPPORT,locator="non-critical background"),
        )
        self.artifact("TEACHER-REBUILT","TEACHER-REBUILT-v001",refs=rebuilt_refs)
        self.controller.append_artifact_link(self.link(
            "LINK-REBUILT-T","REV-THEME-1-v002","TEACHER-REBUILT-v001",
            ResearchRole.TEACHER,basis=("EVIDENCE-v001","BACKGROUND-v002"),
            created_at=AT+timedelta(minutes=3)))
        self.controller.commit(self.request("COMMIT-COMPAT-v001",
            "REV-THEME-1-v002",("LINK-COMPAT-A","LINK-REBUILT-T"),
            created_at=AT+timedelta(minutes=4)))
        self.assertTrue(self.controller.is_current("COMMIT-COMPAT-v001"))

    def test_revision_change_between_check_and_commit_causes_atomic_conflict(self):
        self.controller.append_revision(self.revision("REV-THEME-1-v001"),None)
        pair=self.linked_pair("REV-THEME-1-v001")
        request=self.request("COMMIT-THEME-1-v001","REV-THEME-1-v001",
            (pair[ResearchRole.ADVISER][1],pair[ResearchRole.TEACHER][1]))
        original_append=self.archive.append
        injected=[]
        def interleave(submission,body=None,**kwargs):
            if (submission.kind is ObjectKind.RESEARCH_COMMIT
                    and not injected):
                injected.append(True)
                with Archive(self.archive.root) as other:
                    controller=ResearchRevisionController(other,self.rights)
                    controller.append_revision(self.revision(
                        "REV-THEME-1-v002","REV-THEME-1-v001",
                        created_at=AT+timedelta(minutes=1)),"REV-THEME-1-v001")
            return original_append(submission,body,**kwargs)
        with patch.object(self.archive,"append",side_effect=interleave):
            with self.assertRaises(Conflict):
                self.controller.commit(request)
        self.assertEqual(self.controller.current_revision("THEME-1").revision_id,
            "REV-THEME-1-v002")
        self.assertIsNone(self.controller.current_commit("THEME-1"))

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
