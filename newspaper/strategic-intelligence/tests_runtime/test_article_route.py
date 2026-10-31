"""W37 owned-fixture source selection, update and correction routing."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import unittest

from pydantic import ValidationError

from intelligence.adoption import (AdoptionController, CheckerRole,
                                   DecisionRequest, StepState,
                                   StepSubmission)
from intelligence.archive import canonical
from intelligence.article_route import (ArticleRouteController,
                                        ArticleRouteError,
                                        ArticleRouteRequest,
                                        PriorResearchState,
                                        RouteResponsibility, ShortFormKind)
from intelligence.contracts import (ObjectKind, ReferenceUse,
                                    Representation, ReviewCoverage,
                                    SourceTimes, VersionReference,
                                    VersionSubmission)
from intelligence.correction import (CorrectionBeginRequest,
                                     CorrectionController, CorrectionKind)
from intelligence.discovery import LineageRole
from intelligence.editorial import (ArticleType, DecisionStage,
                                    EditionPlacement,
                                    EditionPlacementProposal,
                                    ResearchAdmission,
                                    S8PrerequisitePackage, TopicDecision,
                                    TopicDecisionCode, ValueBasis)
from intelligence.editorial_review import (AuthorResponseRequest,
                                           AuthorResponseItem,
                                           ClosureOutcome, FinalReviewRequest,
                                           InquiryType, IssueClosure,
                                           IssueSeverity, ReviewDisposition,
                                           ReviewExposure, ReviewerInquiry,
                                           ShortFormOpenReviewRequest,
                                           ShortFormReviewController)
from intelligence.evidence import (EvidenceNature, EvidenceNodeBinding,
                                   EvidenceRecord)
from intelligence.materials import (ChineseMaterialMode, OmissionRecord)
from intelligence.presentation import (EditionEntryRole,
                                        EditionSourceRequest,
                                        ReviewedEditionEntry)

BASE = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)


def _version(prefix, identity):
    raw = json.dumps([prefix, identity], ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:32]


class SourceSelectionRouteTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_materials import ChineseMaterialTests
        self.fx = ChineseMaterialTests(
            methodName="test_excerpt_translation_and_source_map_are_exact")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.archive = self.fx.archive
        self.rights = self.fx.journal_rights
        self.editorial = self.fx.editorial
        self.routes = ArticleRouteController(self.archive, self.rights)

    def seed(self):
        admission = self.editorial.append_research_admission(
            ResearchAdmission(
                research_admission_id="ADMISSION-W37-SOURCE",
                topic_decision_id=self.fx.cover.decision_id,
                topic_id="TOPIC-W26",
                theme_id="THEME-W26",
                edition_id="EDITION-W42",
                spec_sha256="a" * 64,
                allowed_article_types=(ArticleType.SOURCE_SELECTION,),
                scope="Produce only the selected source reading material",
                restrictions=("No publication authorization",),
                created_at=self.fx.cover.created_at + timedelta(seconds=1)))
        node = self.fx.structure_a.nodes[0]
        material = self.fx.materials.append_material(
            self.fx.base_request(
                material_id="MATERIAL-W37-SOURCE",
                intake=self.fx.intake_a,
                structure=self.fx.structure_a,
                evidence_id=self.fx.evidence_a.submission.version_id,
                mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
                selected=(node.node_id,),
                segments=(self.fx.segment(
                    "SEG-W37-SOURCE", (node.node_id,),
                    "自有精选译文：试验未获批准。"),),
                omissions=(OmissionRecord(
                    locator=self.fx.structure_a.nodes[1].locator,
                    reason="Owned excerpt omits the unrelated second paragraph"),),
                title="精选阅读材料"))
        task = self.archive.append(VersionSubmission(
            schema_version=2, object_id="TASK-W37-SOURCE",
            version_id="TASK-W37-SOURCE-v001", kind=ObjectKind.TASK,
            title="W37 source-selection task", spec_sha256="a" * 64,
            created_at=BASE + timedelta(minutes=6), rights=self.rights,
            representation=Representation.FULL_BODY), b"Owned W37 task")
        decision_version = self.editorial._version(
            "TOPIC-DECISION-", self.fx.cover.decision_id)
        references = (
            VersionReference(
                target_version_id=decision_version,
                use=ReferenceUse.BASIS, locator="W23 S8 selection"),
            VersionReference(
                target_version_id=admission.submission.version_id,
                use=ReferenceUse.BASIS, locator="research admission"),
            VersionReference(
                target_version_id=task.submission.version_id,
                use=ReferenceUse.BASIS, locator="task"),
            VersionReference(
                target_version_id=material.submission.version_id,
                use=ReferenceUse.SOURCE, locator="W26 Chinese material"),
            VersionReference(
                target_version_id=self.fx.evidence_a.submission.version_id,
                use=ReferenceUse.SUPPORT, locator="source evidence"),
        )
        article = self.archive.append(VersionSubmission(
            schema_version=2, object_id="ARTICLE-W37-SOURCE",
            version_id="ARTICLE-W37-SOURCE-v001", kind=ObjectKind.ARTICLE,
            title="W37 source-selection reader draft",
            spec_sha256="a" * 64,
            created_at=BASE + timedelta(minutes=6, seconds=1),
            rights=self.rights,
            representation=Representation.FULL_BODY,
            references=references),
            ("# 精选：一项未获批准的试验\n\n"
             "这份材料为何值得读：它保存了一个清楚的否定事实。\n\n"
             "必要背景、原文定位与节选限制随文给出。").encode())
        route = self.routes.record(ArticleRouteRequest(
            route_id="ROUTE-W37-SOURCE",
            spec_sha256="a" * 64,
            task_version_id=task.submission.version_id,
            topic_decision_id=self.fx.cover.decision_id,
            research_admission_id="ADMISSION-W37-SOURCE",
            article_version_id=article.submission.version_id,
            short_form=ShortFormKind.SOURCE_SELECTION,
            material_version_id=material.submission.version_id,
            evidence_version_ids=(
                self.fx.evidence_a.submission.version_id,),
            source_value="The selected original preserves a clear negative fact.",
            background="The selected sentence is read with its own period and source.",
            limitations=("Excerpt only; the second paragraph is omitted",),
            created_at=BASE + timedelta(minutes=7)))
        return route, article, task

    def review(self, route, article, task):
        controller = ShortFormReviewController(
            self.archive, self.rights, self.routes)
        inquiry = ReviewerInquiry(
            inquiry_id="INQ-W37-SOURCE",
            inquiry_type=InquiryType.ARTICLE_INTEGRITY,
            severity=IssueSeverity.MINOR,
            article_locator="opening rationale",
            quoted_text="这份材料为何值得读",
            concern="The selection value must remain explicit.",
            required_check="Check the reader-facing selection reason.",
            formed_at=BASE + timedelta(minutes=7, seconds=30))
        case = controller.open_case(ShortFormOpenReviewRequest(
            review_case_id="CASE-W37-SOURCE",
            article_route_version_id=route.submission.version_id,
            task_version_id=task.submission.version_id,
            article_version_id=article.submission.version_id,
            spec_sha256="a" * 64,
            reviewer_id="REVIEWER-W37-SOURCE",
            author_ids=("AUTHOR-W37-SOURCE",),
            producer_id="AUTHOR-W37-SOURCE",
            reviewed_scope=("W37_SHORT_FORM", "WEEKLY"),
            exposure=ReviewExposure(
                started_from_draft=True,
                author_self_assessment_seen=False,
                prior_review_seen=False),
            evidence_version_ids=(
                self.fx.evidence_a.submission.version_id,),
            inquiries=(inquiry,),
            created_at=BASE + timedelta(minutes=8)))
        responded = controller.respond(AuthorResponseRequest(
            review_case_version_id=case.review_case_version_id,
            expected_current_case_version_id=(
                case.review_case_version_id),
            responder_id="AUTHOR-W37-SOURCE",
            article_version_id=article.submission.version_id,
            responses=(AuthorResponseItem(
                inquiry_id=inquiry.inquiry_id,
                responder_id="AUTHOR-W37-SOURCE",
                response="The opening sentence states the selection value.",
                proposed_resolution="Retain the sentence.",
                responded_at=BASE + timedelta(minutes=8, seconds=30)),),
            note="Owned short-form response.",
            responded_at=BASE + timedelta(minutes=9)))
        result = controller.decide(FinalReviewRequest(
            review_case_version_id=responded.review_case_version_id,
            expected_current_case_version_id=(
                responded.review_case_version_id),
            review_id="REVIEW-W37-SOURCE",
            article_version_id=article.submission.version_id,
            reviewer_id="REVIEWER-W37-SOURCE",
            decision=ReviewDisposition.PASS,
            reviewed_scope=("W37_SHORT_FORM", "WEEKLY"),
            closures=(IssueClosure(
                inquiry_id=inquiry.inquiry_id,
                outcome=ClosureOutcome.RESOLVED,
                basis_version_ids=(
                    self.fx.evidence_a.submission.version_id,),
                rationale="The exact opening sentence remains present.",
                checked_at=BASE + timedelta(minutes=9, seconds=30)),),
            decision_reason="Owned source-selection content review.",
            expires_at=BASE + timedelta(days=1),
            decided_at=BASE + timedelta(minutes=10)))
        return controller, result

    def test_source_selection_uses_w26_material_and_shared_review_w15(self):
        route, article, task = self.seed()
        record = self.routes.load(route.submission.version_id)
        self.assertIs(record.short_form, ShortFormKind.SOURCE_SELECTION)
        self.assertIn(
            RouteResponsibility.SOURCE_VALUE_AND_LIMITS,
            record.required_responsibilities)
        self.assertIn(
            RouteResponsibility.WEEKLY_DEPTH_REMAINS,
            record.required_responsibilities)
        self.assertFalse(record.publication_authorized)

        controller, result = self.review(route, article, task)
        from intelligence.editorial_review import EditorialReviewController
        loaded = EditorialReviewController(
            self.archive, self.rights).load_review(
                result.review_version_id)
        self.assertIs(loaded.decision, ReviewDisposition.PASS)
        self.assertEqual(
            loaded.article_route_version_id,
            route.submission.version_id)
        self.assertFalse(loaded.publication_authorized)
        decision = controller.adoption.load(
            result.adoption_decision_version_id)
        self.assertEqual(decision.subject_version_id,
                         article.submission.version_id)
        self.assertTrue(controller.adoption.is_current(
            result.adoption_decision_version_id))

    def test_deep_and_short_forms_cannot_be_relabelled(self):
        route, article, task = self.seed()
        with self.assertRaisesRegex(
                ArticleRouteError, "article type differ"):
            self.routes.record(ArticleRouteRequest(
                route_id="ROUTE-W37-WRONG-TYPE",
                spec_sha256="a" * 64,
                task_version_id=task.submission.version_id,
                topic_decision_id=self.fx.cover.decision_id,
                research_admission_id="ADMISSION-W37-SOURCE",
                article_version_id=article.submission.version_id,
                short_form=ShortFormKind.INITIAL_FACT,
                evidence_version_ids=(
                    self.fx.evidence_a.submission.version_id,),
                fact_time=BASE,
                what_happened="A verified fact.",
                why_important="It matters.",
                unknowns=("What follows is unknown",),
                reopen_conditions=("New official evidence",),
                created_at=BASE + timedelta(minutes=7, seconds=1)))


class UpdateRouteIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_presentation import EditionPresentationTests
        self.fx = EditionPresentationTests(
            methodName="test_composes_reviewed_readable_edition_without_publication_authority")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.archive = self.fx.archive
        self.rights = self.fx.rights
        self.spec = self.fx.rf.pf.revision.spec_sha256
        self.task = self.fx.rf.task
        self.time = self.fx.time + timedelta(minutes=10)
        self.routes = ArticleRouteController(self.archive, self.rights)
        self.reviewer = ShortFormReviewController(
            self.archive, self.rights, self.routes)
        self.evidence1 = self.fx.rf.pf.fx.evidence_version_id
        self.evidence2 = self.add_evidence("FOLLOW")
        self.evidence3 = self.add_evidence("CORRECTION")
        self.initial_basis = self.make_basis(
            "INITIAL", self.evidence1)
        self.follow_basis = self.make_basis(
            "FOLLOW", self.evidence2)
        self.correction_basis = self.make_basis(
            "CORRECTION", self.evidence3)
        self.correction_context = self.make_correction_case()

        self.initial_article = self.make_article(
            "ARTICLE-W37-INITIAL",
            "# Initial Fact: Observation\n\n"
            "A verified event occurred and its date is stated below.",
            self.initial_basis, self.evidence1)
        self.initial_route = self.make_route(
            "INITIAL", ShortFormKind.INITIAL_FACT,
            self.initial_basis, self.initial_article, self.evidence1,
            fact_time=self.time - timedelta(days=1),
            what_happened="A verified event occurred.",
            why_important="It changes the factual baseline for this question.",
            unknowns=("The next observable step remains unknown",),
            reopen_conditions=("A dated follow-up record appears",))

        self.follow_article = self.make_article(
            "ARTICLE-W37-FOLLOW",
            "# Follow-up: New Evidence\n\n"
            "A later dated record adds one observable change.",
            self.follow_basis, self.evidence2,
            (self.initial_article.submission.version_id,))
        self.follow_route = self.make_route(
            "FOLLOW", ShortFormKind.FOLLOW_UP,
            self.follow_basis, self.follow_article, self.evidence2,
            prior_article_version_id=self.initial_article.submission.version_id,
            prior_state=PriorResearchState.PUBLISHED_ARTICLE,
            fact_time=self.time - timedelta(hours=12),
            what_happened="A later dated record adds one observable change.",
            why_important="The new step narrows the earlier unknown.",
            unknowns=("The mechanism behind the step remains open",),
            reopen_conditions=("Implementation evidence appears",),
            change_summary="A new record appeared after the initial fact.",
            impact_summary="The factual baseline advances but causality is not established.")

        self.correction_article = self.make_article(
            "ARTICLE-W37-CORRECTION",
            "# Correction: Revised Figure\n\n"
            "The earlier claim is quoted: \"The verified number was 100.\" "
            "The corrected figure is 90.",
            self.correction_basis, self.evidence3,
            (
                self.correction_context["old_article"].submission.version_id,
                self.correction_context["case"].correction_case_version_id,
            ))
        self.correction_route = self.make_route(
            "CORRECTION", ShortFormKind.CORRECTION,
            self.correction_basis, self.correction_article,
            self.evidence3,
            prior_article_version_id=(
                self.correction_context["old_article"].submission.version_id),
            prior_state=PriorResearchState.PUBLISHED_ARTICLE,
            correction_case_version_id=(
                self.correction_context["case"].correction_case_version_id),
            what_happened="The old figure was corrected from 100 to 90.",
            why_important="The old public figure changes and its dependent uses need recheck.",
            impact_summary="The corrected figure narrows the earlier factual support.",
            previous_excerpt_locator="Opening factual sentence",
            previous_excerpt="The verified number was 100.")

        self.w37_proposal = self.make_proposal()

    def add_evidence(self, label):
        evidence_id = "EVIDENCE-W37-" + label
        version_id = _version("EVIDENCE-RECORD-", evidence_id)
        record = EvidenceRecord(
            evidence_id=evidence_id,
            theme_id="THEME-W29", spec_sha256=self.spec,
            intake_version_id="INTAKE-W37-" + label,
            structure_version_id="STRUCTURE-W37-" + label,
            source_id="SOURCE-W37-" + label,
            source_sha256=hashlib.sha256(label.encode()).hexdigest(),
            lineage_proposal_id="LINEAGE-W37-" + label,
            cluster_id="CLUSTER-W37-" + label,
            lineage_role=LineageRole.ORIGINAL,
            lineage_root_ids=("ROOT-W37-" + label,),
            independence_known=True,
            nodes=(EvidenceNodeBinding(
                node_id="NODE-W37-" + label,
                locator="owned sentence",
                text_sha256=hashlib.sha256(
                    ("body-" + label).encode()).hexdigest()),),
            nature=EvidenceNature.DOCUMENTED_FACT,
            created_at=self.time)
        return self.archive.append(VersionSubmission(
            schema_version=2,
            object_id="EVIDENCE-OBJECT-W37-" + label,
            version_id=version_id,
            kind=ObjectKind.EVIDENCE,
            title="Owned W37 Evidence " + label,
            spec_sha256=self.spec,
            created_at=self.time,
            rights=self.rights,
            representation=Representation.FULL_BODY),
            canonical(record.model_dump(mode="json")).encode()
        ).submission.version_id

    def make_basis(self, label, evidence_version_id):
        self.time += timedelta(seconds=1)
        topic_id = "TOPIC-W37-" + label
        package = S8PrerequisitePackage(
            package_id="PACKAGE-W37-" + label,
            topic_id=topic_id,
            edition_id="EDITION-W32",
            spec_sha256=self.spec,
            discovery_proposal_id=self.fx.discovery.proposal_id,
            question_version_id=(
                self.fx.rf.pf.fx.question.submission.version_id),
            source_material_version_ids=(
                self.fx.rf.pf.fx.baseline.submission.version_id,),
            evidence_version_ids=(evidence_version_id,),
            rights_record_version_ids=(
                self.fx.rights_record.submission.version_id,),
            reading_plan_version_id=(
                self.fx.reading_plan.submission.version_id),
            limitations=("Owned W37 short-form integration fixture",),
            candidate_index_ids=(self.fx.index.index_id,),
            coverage_audit_ids=self.fx.package.coverage_audit_ids,
            created_at=self.time)
        self.fx.editorial.append_package(package)
        decision = TopicDecision(
            decision_id="DECISION-W37-" + label,
            topic_id=topic_id,
            theme_id="THEME-W29",
            edition_id="EDITION-W32",
            spec_sha256=self.spec,
            discovery_proposal_id=self.fx.discovery.proposal_id,
            question_version_id=(
                self.fx.rf.pf.fx.question.submission.version_id),
            candidate_index_ids=(self.fx.index.index_id,),
            candidate_ids=(self.fx.candidate.candidate_id,),
            cluster_ids=(self.fx.cluster.cluster_id,),
            stage=DecisionStage.S8,
            publication_basis=self.fx.w23_decision.publication_basis,
            article_type=ArticleType.UPDATE_CORRECTION,
            value_bases=(ValueBasis.DIRECT_IMPACT,),
            decision=TopicDecisionCode.COVER,
            reasons=("Owned W37 short update has an explicit editorial use",),
            gaps=(),
            research_investment_note="Owned W37 offline fixture",
            s8_package_id=package.package_id,
            created_at=self.time)
        decision_stored = self.fx.editorial.append_decision(decision)
        admission = ResearchAdmission(
            research_admission_id="ADMISSION-W37-" + label,
            topic_decision_id=decision.decision_id,
            topic_id=topic_id,
            theme_id="THEME-W29",
            edition_id="EDITION-W32",
            spec_sha256=self.spec,
            allowed_article_types=(ArticleType.UPDATE_CORRECTION,),
            scope="Produce the exact short update only",
            restrictions=("No publication authorization",),
            created_at=self.time + timedelta(seconds=1))
        admission_stored = self.fx.editorial.append_research_admission(
            admission)
        self.time = admission.created_at
        return {
            "decision": decision,
            "decision_version": decision_stored.submission.version_id,
            "admission": admission,
            "admission_version": admission_stored.submission.version_id,
        }

    def make_article(self, object_id, body, basis, evidence_id,
                     extra_refs=()):
        self.time += timedelta(seconds=1)
        references = (
            VersionReference(
                target_version_id=basis["decision_version"],
                use=ReferenceUse.BASIS, locator="W23 short-form COVER"),
            VersionReference(
                target_version_id=basis["admission_version"],
                use=ReferenceUse.BASIS, locator="short-form admission"),
            VersionReference(
                target_version_id=self.task.submission.version_id,
                use=ReferenceUse.BASIS, locator="task"),
            VersionReference(
                target_version_id=evidence_id,
                use=ReferenceUse.SUPPORT, locator="short-form evidence"),
            *(
                VersionReference(
                    target_version_id=version_id,
                    use=ReferenceUse.BASIS,
                    locator=f"explicit route dependency {index}")
                for index, version_id in enumerate(extra_refs)
            ),
        )
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id,
            version_id=object_id + "-v001", kind=ObjectKind.ARTICLE,
            title=object_id, spec_sha256=self.spec,
            created_at=self.time, rights=self.rights,
            representation=Representation.FULL_BODY,
            references=references), body.encode())

    def make_route(self, label, short_form, basis, article, evidence_id,
                   **updates):
        self.time += timedelta(seconds=1)
        return self.routes.record(ArticleRouteRequest(
            route_id="ROUTE-W37-" + label,
            spec_sha256=self.spec,
            task_version_id=self.task.submission.version_id,
            topic_decision_id=basis["decision"].decision_id,
            research_admission_id=(
                basis["admission"].research_admission_id),
            article_version_id=article.submission.version_id,
            short_form=short_form,
            evidence_version_ids=(evidence_id,),
            created_at=self.time, **updates))

    def make_correction_case(self):
        def store(object_id, version_id, kind, body, *, parent=None,
                  references=(), coverage=()):
            self.time += timedelta(seconds=1)
            return self.archive.append(VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=version_id, parent_version_id=parent,
                kind=kind, title=object_id, spec_sha256=self.spec,
                created_at=self.time, source_times=SourceTimes(),
                rights=self.rights,
                representation=Representation.FULL_BODY,
                references=tuple(references),
                review_coverage=tuple(coverage)), body)

        old_source = store(
            "SOURCE-W37-CORR", "SOURCE-W37-CORR-v001",
            ObjectKind.DOCUMENT, b"The old official figure was 100.")
        new_source = store(
            "SOURCE-W37-CORR", "SOURCE-W37-CORR-v002",
            ObjectKind.DOCUMENT, b"The corrected official figure is 90.",
            parent=old_source.submission.version_id)
        evidence = store(
            "EVIDENCE-W37-CORR-OLD", "EVIDENCE-W37-CORR-OLD-v001",
            ObjectKind.EVIDENCE, b"Old evidence used the 100 figure.",
            references=(VersionReference(
                target_version_id=old_source.submission.version_id,
                use=ReferenceUse.SOURCE, locator="old figure"),))
        claim = store(
            "CLAIM-W37-CORR", "CLAIM-W37-CORR-v001",
            ObjectKind.CLAIM, b"The earlier claim used 100.",
            references=(VersionReference(
                target_version_id=evidence.submission.version_id,
                use=ReferenceUse.SUPPORT, locator="old number"),))
        old_article = store(
            "ARTICLE-W37-CORR-OLD", "ARTICLE-W37-CORR-OLD-v001",
            ObjectKind.ARTICLE,
            b"# Earlier Fact\n\nThe verified number was 100.",
            references=(VersionReference(
                target_version_id=claim.submission.version_id,
                use=ReferenceUse.BASIS, locator="old claim"),))
        review = store(
            "REVIEW-W37-CORR-OLD", "REVIEW-W37-CORR-OLD-v001",
            ObjectKind.REVIEW, b"Owned old review",
            references=(VersionReference(
                target_version_id=old_article.submission.version_id,
                use=ReferenceUse.REVIEW_OF, locator="old Article"),),
            coverage=(ReviewCoverage(
                task_version_id=self.task.submission.version_id,
                subject_version_id=old_article.submission.version_id,
                reviewed_scope=("publication",)),))
        adoption = AdoptionController(self.archive, self.rights)
        submission = adoption.submit(StepSubmission(
            schema_version=2, submission_id="SUB-W37-CORR-OLD",
            work_id="W37-CORRECTION", step_id="CONTENT",
            spec_sha256=self.spec,
            task_version_id=self.task.submission.version_id,
            subject_version_id=old_article.submission.version_id,
            producer_id="AUTHOR-W37-CORR-OLD",
            proposed_state=StepState.READY,
            claimed_scope=("publication",),
            input_version_ids=(old_article.submission.version_id,),
            evidence_version_ids=(review.submission.version_id,),
            created_at=self.time))
        adoption.decide(DecisionRequest(
            decision_id="DEC-W37-CORR-OLD",
            submission_version_id=submission.submission.version_id,
            state=StepState.READY, checker_id="REVIEWER-W37-CORR-OLD",
            checker_role=CheckerRole.L5,
            review_version_id=review.submission.version_id,
            allowed_scope=("publication",),
            reason="Owned old adoption",
            decided_at=self.time))
        case = CorrectionController(
            self.archive, self.rights).begin(CorrectionBeginRequest(
                correction_id="CORRECTION-W37",
                previous_version_id=old_source.submission.version_id,
                corrected_version_id=new_source.submission.version_id,
                kind=CorrectionKind.SOURCE_CORRECTION,
                reason="Owned official figure corrected from 100 to 90",
                changed_at=self.time,
                affected_scopes=("publication",),
                adoption_decision_ids=("DEC-W37-CORR-OLD",),
                scope_limitation=(
                    "Only explicitly linked effects are covered"),
                created_at=self.time))
        loaded = CorrectionController(
            self.archive, self.rights).load(
                case.correction_case_version_id)
        self.assertIn(
            old_article.submission.version_id,
            loaded.affected_version_ids)
        return {
            "old_article": old_article,
            "case": loaded,
            "result": case,
        }

    def review_route(self, label, route, article):
        self.time += timedelta(seconds=1)
        case = self.reviewer.open_case(ShortFormOpenReviewRequest(
            review_case_id="CASE-W37-" + label,
            article_route_version_id=route.submission.version_id,
            task_version_id=self.task.submission.version_id,
            article_version_id=article.submission.version_id,
            spec_sha256=self.spec,
            reviewer_id="REVIEWER-W37-" + label,
            author_ids=("AUTHOR-W37-" + label,),
            producer_id="AUTHOR-W37-" + label,
            reviewed_scope=("W37_SHORT_FORM", "WEEKLY"),
            exposure=ReviewExposure(
                started_from_draft=True,
                author_self_assessment_seen=False,
                prior_review_seen=False),
            evidence_version_ids=tuple(
                self.routes.load(
                    route.submission.version_id).evidence_version_ids),
            created_at=self.time))
        self.time += timedelta(seconds=1)
        responded = self.reviewer.respond(AuthorResponseRequest(
            review_case_version_id=case.review_case_version_id,
            expected_current_case_version_id=(
                case.review_case_version_id),
            responder_id="AUTHOR-W37-" + label,
            article_version_id=article.submission.version_id,
            responses=(), note="Owned clean short-form draft.",
            responded_at=self.time))
        self.time += timedelta(seconds=1)
        result = self.reviewer.decide(FinalReviewRequest(
            review_case_version_id=responded.review_case_version_id,
            expected_current_case_version_id=(
                responded.review_case_version_id),
            review_id="REVIEW-W37-" + label,
            article_version_id=article.submission.version_id,
            reviewer_id="REVIEWER-W37-" + label,
            decision=ReviewDisposition.PASS,
            reviewed_scope=("W37_SHORT_FORM", "WEEKLY"),
            closures=(),
            decision_reason="Owned short-form content review.",
            expires_at=self.time + timedelta(days=1),
            decided_at=self.time))
        return result

    def make_proposal(self):
        self.time += timedelta(seconds=1)
        proposal = EditionPlacementProposal(
            edition_proposal_id="EDITION-PROPOSAL-W37",
            edition_id="EDITION-W32",
            spec_sha256=self.spec,
            placements=(
                EditionPlacement(
                    placement_id="PLACEMENT-W32-MAIN",
                    topic_decision_id=self.fx.w23_decision.decision_id,
                    research_admission_id=(
                        self.fx.w23_admission.research_admission_id),
                    topic_id=self.fx.w23_decision.topic_id,
                    article_type=ArticleType.DEEP_THEME,
                    publication_basis=(
                        self.fx.w23_decision.publication_basis),
                    slot_order=2,
                    editorial_role="Reviewed depth feature",
                    reason="The weekly edition retains its depth feature"),
                EditionPlacement(
                    placement_id="PLACEMENT-W37-INITIAL",
                    topic_decision_id=(
                        self.initial_basis["decision"].decision_id),
                    research_admission_id=(
                        self.initial_basis["admission"].research_admission_id),
                    topic_id=self.initial_basis["decision"].topic_id,
                    article_type=ArticleType.UPDATE_CORRECTION,
                    publication_basis=(
                        self.initial_basis["decision"].publication_basis),
                    slot_order=3,
                    editorial_role="Verified initial fact",
                    reason="Verified first fact belongs in the weekly record"),
                EditionPlacement(
                    placement_id="PLACEMENT-W37-FOLLOW",
                    topic_decision_id=(
                        self.follow_basis["decision"].decision_id),
                    research_admission_id=(
                        self.follow_basis["admission"].research_admission_id),
                    topic_id=self.follow_basis["decision"].topic_id,
                    article_type=ArticleType.UPDATE_CORRECTION,
                    publication_basis=(
                        self.follow_basis["decision"].publication_basis),
                    slot_order=4,
                    editorial_role="Verified follow-up",
                    reason="A dated new observation advances the record"),
                EditionPlacement(
                    placement_id="PLACEMENT-W37-CORRECTION",
                    topic_decision_id=(
                        self.correction_basis["decision"].decision_id),
                    research_admission_id=(
                        self.correction_basis[
                            "admission"].research_admission_id),
                    topic_id=self.correction_basis["decision"].topic_id,
                    article_type=ArticleType.UPDATE_CORRECTION,
                    publication_basis=(
                        self.correction_basis[
                            "decision"].publication_basis),
                    slot_order=5,
                    editorial_role="Verified correction",
                    reason="The corrected figure must be published"),
            ),
            combination_reason=(
                "One reviewed depth feature plus bounded factual updates"),
            created_at=self.time)
        return self.fx.editorial.append_edition_proposal(proposal)

    def test_initial_followup_and_correction_share_review_and_weekly_edition(self):
        initial_review = self.review_route(
            "INITIAL", self.initial_route, self.initial_article)
        follow_review = self.review_route(
            "FOLLOW", self.follow_route, self.follow_article)
        correction_review = self.review_route(
            "CORRECTION", self.correction_route,
            self.correction_article)
        base = self.fx.request()
        composed_at = self.time + timedelta(seconds=1)
        request = EditionSourceRequest.model_validate_json(
            base.model_copy(update={
                "edition_proposal_id": "EDITION-PROPOSAL-W37",
                "composition_id": "COMPOSITION-W37",
                "coverage_end": composed_at,
                "knowledge_cutoff": composed_at,
                "created_at": composed_at,
                "entries": (
                    base.entries[0],
                    base.entries[1],
                    ReviewedEditionEntry(
                        entry_id="INITIAL",
                        role=EditionEntryRole.UPDATE,
                        slot_order=3,
                        article_version_id=(
                            self.initial_article.submission.version_id),
                        review_version_id=(
                            initial_review.review_version_id),
                        adoption_decision_id=(
                            initial_review.adoption_decision_version_id),
                        placement_id="PLACEMENT-W37-INITIAL",
                        title="Initial Fact: Observation",
                        required_scope=(
                            "W37_SHORT_FORM", "WEEKLY")),
                    ReviewedEditionEntry(
                        entry_id="FOLLOW",
                        role=EditionEntryRole.UPDATE,
                        slot_order=4,
                        article_version_id=(
                            self.follow_article.submission.version_id),
                        review_version_id=(
                            follow_review.review_version_id),
                        adoption_decision_id=(
                            follow_review.adoption_decision_version_id),
                        placement_id="PLACEMENT-W37-FOLLOW",
                        title="Follow-up: New Evidence",
                        required_scope=(
                            "W37_SHORT_FORM", "WEEKLY")),
                    ReviewedEditionEntry(
                        entry_id="CORRECTION",
                        role=EditionEntryRole.UPDATE,
                        slot_order=5,
                        article_version_id=(
                            self.correction_article.submission.version_id),
                        review_version_id=(
                            correction_review.review_version_id),
                        adoption_decision_id=(
                            correction_review.adoption_decision_version_id),
                        placement_id="PLACEMENT-W37-CORRECTION",
                        title="Correction: Revised Figure",
                        required_scope=(
                            "W37_SHORT_FORM", "WEEKLY")),
                ),
            }).model_dump_json())
        result = self.fx.controller.compose(request)
        from pathlib import Path
        html = Path(result.output_path).read_text(encoding="utf-8")
        for expected in (
                "Bounded Commitment", "Initial Fact: Observation",
                "Follow-up: New Evidence", "Correction: Revised Figure"):
            self.assertIn(expected, html)
        edition = self.fx.controller.load_edition(
            result.edition_version_id)
        self.assertEqual(
            [item.role for item in edition.entries],
            [EditionEntryRole.COVER, EditionEntryRole.FEATURE,
             EditionEntryRole.UPDATE, EditionEntryRole.UPDATE,
             EditionEntryRole.UPDATE])
        self.assertFalse(edition.publication_authorized)

    def test_short_feature_and_deep_update_relabel_are_rejected(self):
        initial_review = self.review_route(
            "INITIAL", self.initial_route, self.initial_article)
        base = self.fx.request()
        self.time += timedelta(seconds=1)
        short_feature_proposal = self.fx.editorial.append_edition_proposal(
            EditionPlacementProposal(
                edition_proposal_id="EDITION-PROPOSAL-W37-SHORT-FEATURE",
                edition_id="EDITION-W32",
                spec_sha256=self.spec,
                placements=(
                    EditionPlacement(
                        placement_id="PLACEMENT-W37-INITIAL",
                        topic_decision_id=(
                            self.initial_basis["decision"].decision_id),
                        research_admission_id=(
                            self.initial_basis[
                                "admission"].research_admission_id),
                        topic_id=self.initial_basis["decision"].topic_id,
                        article_type=ArticleType.UPDATE_CORRECTION,
                        publication_basis=(
                            self.initial_basis[
                                "decision"].publication_basis),
                        slot_order=2,
                        editorial_role="Invalid short feature",
                        reason="Expected route-role rejection"),
                    EditionPlacement(
                        placement_id="PLACEMENT-W32-MAIN",
                        topic_decision_id=self.fx.w23_decision.decision_id,
                        research_admission_id=(
                            self.fx.w23_admission.research_admission_id),
                        topic_id=self.fx.w23_decision.topic_id,
                        article_type=ArticleType.DEEP_THEME,
                        publication_basis=(
                            self.fx.w23_decision.publication_basis),
                        slot_order=3,
                        editorial_role="Depth control",
                        reason="Keep a valid depth placement"),
                ),
                combination_reason="Invalid role relation for W37 negative test",
                created_at=self.time))
        short_feature = ReviewedEditionEntry(
            entry_id="SHORT-FEATURE",
            role=EditionEntryRole.FEATURE,
            slot_order=2,
            article_version_id=(
                self.initial_article.submission.version_id),
            review_version_id=initial_review.review_version_id,
            adoption_decision_id=(
                initial_review.adoption_decision_version_id),
            placement_id="PLACEMENT-W37-INITIAL",
            title="Initial Fact: Observation",
            required_scope=("W37_SHORT_FORM", "WEEKLY"))
        request = base.model_copy(update={
            "edition_proposal_id": "EDITION-PROPOSAL-W37-SHORT-FEATURE",
            "composition_id": "COMPOSITION-W37-RELATIONAL",
            "entries": (base.entries[0], short_feature),
        })
        with self.assertRaisesRegex(
                Exception, "short form cannot replace"):
            self.fx.controller.compose(request)

        deep_update = base.entries[1].model_copy(update={
            "entry_id": "DEEP-UPDATE",
            "role": EditionEntryRole.UPDATE,
        })
        with self.assertRaisesRegex(
                Exception, "deep-theme Article cannot be relabelled"):
            self.fx.controller.compose(base.model_copy(update={
                "edition_proposal_id": "EDITION-PROPOSAL-W37",
                "composition_id": "COMPOSITION-W37-DEEP-LABEL",
                "entries": (
                    base.entries[0], deep_update,
                    short_feature.model_copy(update={
                        "entry_id": "SHORT-FEATURE-CONTROL",
                        "slot_order": 3,
                    })),
            }))

    def test_follow_up_needs_new_evidence_beyond_the_prior_article(self):
        repeated_article = self.make_article(
            "ARTICLE-W37-FOLLOW-REPEAT",
            "# Follow-up: Repeated Basis\n\nNo new Evidence was added.",
            self.follow_basis, self.evidence1,
            (self.initial_article.submission.version_id,))
        with self.assertRaisesRegex(
                ArticleRouteError, "evidence beyond the prior basis"):
            self.make_route(
                "FOLLOW-REPEAT", ShortFormKind.FOLLOW_UP,
                self.follow_basis, repeated_article, self.evidence1,
                prior_article_version_id=(
                    self.initial_article.submission.version_id),
                prior_state=PriorResearchState.PUBLISHED_ARTICLE,
                what_happened="The prior evidence was restated.",
                why_important="It would only repeat the old support.",
                unknowns=("No new unknown was resolved",),
                reopen_conditions=("New Evidence appears",),
                change_summary="No actual change occurred.",
                impact_summary="No support change is established.")

    def test_follow_up_can_reference_researched_but_unpublished_dossier(self):
        dossier_stored, _ = self.fx.rf.pf.workflow.current_snapshot(
            "DOSSIER-W29")
        article = self.make_article(
            "ARTICLE-W37-DOSSIER-FOLLOW",
            "# Follow-up: Prior Research\n\n"
            "New evidence advances a previously unpublished dossier.",
            self.follow_basis, self.evidence2,
            (dossier_stored.submission.version_id,))
        route = self.make_route(
            "DOSSIER-FOLLOW", ShortFormKind.FOLLOW_UP,
            self.follow_basis, article, self.evidence2,
            prior_dossier_version_id=(
                dossier_stored.submission.version_id),
            prior_state=PriorResearchState.UNPUBLISHED_RESEARCH,
            what_happened="A new dated observation appeared.",
            why_important="It advances the unpublished research question.",
            unknowns=("The broader mechanism remains unresolved",),
            reopen_conditions=("A second independent observation appears",),
            change_summary="New evidence exists beyond the prior dossier.",
            impact_summary="The issue becomes fit for a bounded public update.")
        record = self.routes.load(route.submission.version_id)
        self.assertIs(
            record.prior_state, PriorResearchState.UNPUBLISHED_RESEARCH)
        self.assertIn(
            RouteResponsibility.PRIOR_REFERENCE,
            record.required_responsibilities)

    def test_initial_fact_cannot_invent_history_and_correction_needs_exact_quote(
            self):
        with self.assertRaisesRegex(
                ValidationError, "cannot carry prior_article_version_id"):
            ArticleRouteRequest(
                route_id="ROUTE-W37-INITIAL-WITH-HISTORY",
                spec_sha256=self.spec,
                task_version_id=self.task.submission.version_id,
                topic_decision_id=(
                    self.initial_basis["decision"].decision_id),
                research_admission_id=(
                    self.initial_basis["admission"].research_admission_id),
                article_version_id=(
                    self.initial_article.submission.version_id),
                short_form=ShortFormKind.INITIAL_FACT,
                evidence_version_ids=(self.evidence1,),
                prior_article_version_id=(
                    self.follow_article.submission.version_id),
                prior_state=PriorResearchState.PUBLISHED_ARTICLE,
                fact_time=self.time,
                what_happened="A fact.",
                why_important="Importance.",
                unknowns=("Unknown",),
                reopen_conditions=("New evidence",),
                created_at=self.time + timedelta(seconds=1))

        bad_correction = self.make_article(
            "ARTICLE-W37-CORRECTION-BAD",
            "# Correction: Missing Quote\n\nThe replacement omits the old wording.",
            self.correction_basis, self.evidence3,
            (
                self.correction_context["old_article"].submission.version_id,
                self.correction_context["case"].correction_case_version_id,
            ))
        with self.assertRaisesRegex(
                ArticleRouteError, "affected old Article and exact excerpt"):
            self.make_route(
                "CORRECTION-BAD", ShortFormKind.CORRECTION,
                self.correction_basis, bad_correction, self.evidence3,
                prior_article_version_id=(
                    self.correction_context[
                        "old_article"].submission.version_id),
                prior_state=PriorResearchState.PUBLISHED_ARTICLE,
                correction_case_version_id=(
                    self.correction_context[
                        "case"].correction_case_version_id),
                what_happened="The figure changed.",
                why_important="Dependent uses must be rechecked.",
                impact_summary="The old support is narrowed.",
                previous_excerpt_locator="Absent old sentence",
                previous_excerpt="A sentence that is not in the old Article.")


if __name__ == "__main__":
    unittest.main()
