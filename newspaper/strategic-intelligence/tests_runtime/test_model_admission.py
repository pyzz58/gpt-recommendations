"""W19 synthetic model-configuration evidence and limited-admission tests."""
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

from intelligence.archive import Archive, PermissionDenied
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState, ReferenceUse,
                                    Representation, RightsBasis, RightsGrant, Scope, ScopeMode,
                                    UsePermission, ValidityMode, VersionReference,
                                    VersionSubmission)
from intelligence.model_admission import (AdmissionStatus, ModelAdmissionController,
                                          ModelAdmissionError, ModelDuty, ModelTaskConfiguration,
                                          ModelUseAdmission, ModelValidation, ToolConfiguration,
                                          ValidationAttempt, ValidationKind,
                                          ValidationOutcome)

AT=datetime(2026,10,25,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic W19 model-admission fixture\n"


class ModelAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.rights=RightsGrant(rights_id="RIGHTS-W19",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic model admission journal",checked_by="test fixture",
            checked_at=AT,permissions=(UsePermission(use=MaterialUse.STORE_BODY,
                state=PermissionState.ALLOWED,validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.controller=ModelAdmissionController(self.archive,self.rights)
        self.case=self.record("CASE-W19","CASE-W19-v001",ObjectKind.DOCUMENT)

    def record(self, object_id, version_id, kind, *, refs=()):
        return self.archive.append(VersionSubmission(
            object_id=object_id,version_id=version_id,kind=kind,title=object_id,
            spec_sha256=SPEC,created_at=AT,rights=self.rights,
            representation=Representation.FULL_BODY,
            references=tuple(refs)),BODY)

    def config(self, configuration_id="CONFIG-W19", *, prompt="b"*64,
               model_version="2026-10", unknown_fields=()):
        return ModelTaskConfiguration(configuration_id=configuration_id,
            provider_id="fixture-provider",model_id="fixture-model",
            model_version=model_version,spec_sha256=SPEC,
            task_instruction_sha256="c"*64,prompt_sha256=prompt,
            context_policy_sha256="d"*64,generation_settings_sha256="e"*64,
            method_version="fixture-method-v1",
            tools=(ToolConfiguration(tool_id="fixture-tool",tool_version="1",
                settings_sha256="f"*64),),
            duties=(ModelDuty.FACT_EXTRACTION,ModelDuty.ADVISER,
                ModelDuty.TEACHER,ModelDuty.REVIEW),
            domains=("global-politics","technology"),
            material_forms=("owned-text",),unknown_fields=tuple(unknown_fields),
            created_at=AT)

    def config_version(self, configuration_id):
        return self.controller._config_version(configuration_id)

    def validation_version(self, validation_id):
        return self.controller._validation_version(validation_id)

    def artifact_for_config(self, object_id, version_id, configuration_id):
        return self.record(object_id,version_id,ObjectKind.ARTICLE,refs=(
            VersionReference(target_version_id=self.config_version(configuration_id),
                use=ReferenceUse.BASIS,locator="model configuration"),))

    def review_for(self, version_id, targets):
        return self.record("REVIEW-"+version_id,version_id,ObjectKind.REVIEW,
            refs=tuple(VersionReference(target_version_id=target,
                use=ReferenceUse.REVIEW_OF,locator="exact validation target")
                for target in targets))

    def validation(self, validation_id, configuration_id, review_id, *,
                   kind=ValidationKind.GIVEN_MATERIAL,
                   duty=ModelDuty.FACT_EXTRACTION,
                   domains=("global-politics",), artifact_id=None,
                   baseline=None, constrained=None, operation_ids=(),
                   primary=ValidationOutcome.PASS, attempts=None):
        if attempts is None:
            attempts=(ValidationAttempt(attempt_id="ATT-"+validation_id+"-1",
                artifact_version_id=artifact_id,outcome=primary),)
        return ModelValidation(validation_id=validation_id,
            configuration_id=configuration_id,spec_sha256=SPEC,kind=kind,
            duty=duty,domains=tuple(domains),case_version_ids=("CASE-W19-v001",),
            baseline_artifact_version_id=baseline,
            constrained_artifact_version_id=constrained,
            operation_receipt_ids=tuple(operation_ids),
            review_version_id=review_id,primary_outcome=primary,
            attempts=tuple(attempts),
            unverified_scope=("Only synthetic owned fixtures",),created_at=AT)

    def admission(self, admission_id, configuration_id, review_id, *,
                  validations=(), duties=(ModelDuty.FACT_EXTRACTION,),
                  domains=("global-politics",), known_failures=(),
                  given=True, retrieval=False, constraint=False,
                  manual=False, status=AdmissionStatus.APPROVED):
        return ModelUseAdmission(admission_id=admission_id,
            configuration_id=configuration_id,spec_sha256=SPEC,
            duties=tuple(duties),domains=tuple(domains),
            validation_ids=tuple(validations),
            known_failure_ids=tuple(known_failures),
            allow_given_material=given,allow_real_retrieval=retrieval,
            constraint_gain_verified=constraint,manual_review_required=manual,
            restrictions=("Synthetic scope only",),
            review_version_id=review_id,status=status,
            valid_from=AT,valid_until=AT+timedelta(days=10),created_at=AT)

    def approved_fixture(self, configuration_id="CONFIG-W19",
                         validation_id="VALIDATION-W19-GIVEN",
                         admission_id="ADMISSION-W19-GIVEN"):
        self.controller.append_configuration(self.config(configuration_id))
        artifact=self.artifact_for_config("ART-W19-GIVEN","ART-W19-GIVEN-v001",
            configuration_id)
        validation_review=self.review_for("REVIEW-VAL-GIVEN-v001",(
            self.config_version(configuration_id),artifact.submission.version_id))
        validation=self.validation(validation_id,configuration_id,
            validation_review.submission.version_id,
            artifact_id=artifact.submission.version_id)
        self.controller.append_validation(validation)
        admission_review=self.review_for("REVIEW-ADM-GIVEN-v001",(
            self.config_version(configuration_id),
            self.validation_version(validation_id)))
        admission=self.admission(admission_id,configuration_id,
            admission_review.submission.version_id,validations=(validation_id,))
        self.controller.append_admission(admission)
        return admission

    def test_configuration_identity_is_stable_and_unknown_version_is_explicit(self):
        config=self.config("CONFIG-UNKNOWN",model_version=None,
            unknown_fields=("model_version",))
        self.controller.append_configuration(config)
        loaded=self.controller.load_configuration("CONFIG-UNKNOWN")
        self.assertEqual(loaded.configuration_sha256,loaded.fingerprint())
        self.assertEqual(loaded.unknown_fields,("model_version",))
        with self.assertRaises(Exception):
            ModelTaskConfiguration.model_validate_json(
                loaded.model_copy(update={"configuration_sha256":"0"*64}).model_dump_json())

    def test_given_material_admission_does_not_authorize_real_retrieval_or_other_scope(self):
        self.approved_fixture()
        self.assertTrue(self.controller.authorizes("ADMISSION-W19-GIVEN",
            configuration_id="CONFIG-W19",duty=ModelDuty.FACT_EXTRACTION,
            domains=("global-politics",),require_given_material=True,at=AT))
        self.assertFalse(self.controller.authorizes("ADMISSION-W19-GIVEN",
            configuration_id="CONFIG-W19",duty=ModelDuty.FACT_EXTRACTION,
            domains=("global-politics",),require_real_retrieval=True,at=AT))
        self.assertFalse(self.controller.authorizes("ADMISSION-W19-GIVEN",
            configuration_id="CONFIG-W19",duty=ModelDuty.REVIEW,
            domains=("global-politics",),require_given_material=True,at=AT))
        self.assertFalse(self.controller.authorizes("ADMISSION-W19-GIVEN",
            configuration_id="CONFIG-W19",duty=ModelDuty.FACT_EXTRACTION,
            domains=("technology",),require_given_material=True,at=AT))

    def test_admission_cannot_expand_to_an_unvalidated_duty_or_retrieval_claim(self):
        self.approved_fixture()
        review=self.review_for("REVIEW-EXPAND-v001",(
            self.config_version("CONFIG-W19"),
            self.validation_version("VALIDATION-W19-GIVEN")))
        expanded=self.admission("ADMISSION-EXPAND","CONFIG-W19",
            review.submission.version_id,
            validations=("VALIDATION-W19-GIVEN",),
            duties=(ModelDuty.FACT_EXTRACTION,ModelDuty.ADVISER),
            given=True,retrieval=True)
        with self.assertRaises(ModelAdmissionError):
            self.controller.append_admission(expanded)

    def test_failed_attempt_is_retained_and_cannot_be_hidden_by_best_result(self):
        self.controller.append_configuration(self.config())
        failed=self.artifact_for_config("ART-W19-FAIL","ART-W19-FAIL-v001","CONFIG-W19")
        passed=self.artifact_for_config("ART-W19-PASS","ART-W19-PASS-v001","CONFIG-W19")
        review=self.review_for("REVIEW-FAILED-v001",(
            self.config_version("CONFIG-W19"),failed.submission.version_id,
            passed.submission.version_id))
        attempts=(
            ValidationAttempt(attempt_id="ATT-FAIL",artifact_version_id="ART-W19-FAIL-v001",
                outcome=ValidationOutcome.FAIL),
            ValidationAttempt(attempt_id="ATT-PASS",artifact_version_id="ART-W19-PASS-v001",
                outcome=ValidationOutcome.PASS),
        )
        validation=self.validation("VALIDATION-FAILED","CONFIG-W19",
            review.submission.version_id,artifact_id="ART-W19-PASS-v001",attempts=attempts)
        self.controller.append_validation(validation)
        adm_review=self.review_for("REVIEW-FAILED-ADM-v001",(
            self.config_version("CONFIG-W19"),self.validation_version("VALIDATION-FAILED")))
        hidden=self.admission("ADMISSION-HIDDEN","CONFIG-W19",
            adm_review.submission.version_id,validations=("VALIDATION-FAILED",))
        with self.assertRaisesRegex(ModelAdmissionError,"known failed"):
            self.controller.append_admission(hidden)
        retained=self.admission("ADMISSION-RETAINED","CONFIG-W19",
            adm_review.submission.version_id,validations=("VALIDATION-FAILED",),
            known_failures=("VALIDATION-FAILED",),manual=True,
            status=AdmissionStatus.LIMITED)
        self.controller.append_admission(retained)
        self.assertFalse(self.controller.authorizes("ADMISSION-RETAINED",
            configuration_id="CONFIG-W19",duty=ModelDuty.FACT_EXTRACTION,
            domains=("global-politics",),require_given_material=True,at=AT))

    def test_constraint_gain_requires_distinct_baseline_and_reviewed_comparison(self):
        self.controller.append_configuration(self.config())
        baseline=self.artifact_for_config("BASE-W19","BASE-W19-v001","CONFIG-W19")
        constrained=self.artifact_for_config("GAIN-W19","GAIN-W19-v001","CONFIG-W19")
        review=self.review_for("REVIEW-GAIN-v001",(
            self.config_version("CONFIG-W19"),baseline.submission.version_id,
            constrained.submission.version_id))
        validation=self.validation("VALIDATION-GAIN","CONFIG-W19",
            review.submission.version_id,kind=ValidationKind.CONSTRAINT_GAIN,
            artifact_id=constrained.submission.version_id,
            baseline=baseline.submission.version_id,
            constrained=constrained.submission.version_id)
        self.controller.append_validation(validation)
        adm_review=self.review_for("REVIEW-GAIN-ADM-v001",(
            self.config_version("CONFIG-W19"),self.validation_version("VALIDATION-GAIN")))
        admission=self.admission("ADMISSION-GAIN","CONFIG-W19",
            adm_review.submission.version_id,validations=("VALIDATION-GAIN",),
            given=False,constraint=True)
        self.controller.append_admission(admission)
        self.assertTrue(self.controller.authorizes("ADMISSION-GAIN",
            configuration_id="CONFIG-W19",duty=ModelDuty.FACT_EXTRACTION,
            domains=("global-politics",),require_constraint_gain=True,at=AT))
        with self.assertRaises(Exception):
            self.validation("VALIDATION-GAIN-BAD","CONFIG-W19",
                review.submission.version_id,kind=ValidationKind.CONSTRAINT_GAIN,
                artifact_id=constrained.submission.version_id,
                baseline=constrained.submission.version_id,
                constrained=constrained.submission.version_id)

    def test_controlled_trial_is_not_approved_and_manual_help_is_visible(self):
        self.controller.append_configuration(self.config())
        artifact=self.artifact_for_config("ART-TRIAL","ART-TRIAL-v001","CONFIG-W19")
        help_record=self.record("HELP-W19","HELP-W19-v001",ObjectKind.DOCUMENT)
        review=self.review_for("REVIEW-TRIAL-v001",(
            self.config_version("CONFIG-W19"),artifact.submission.version_id))
        attempts=(ValidationAttempt(attempt_id="ATT-TRIAL",
            artifact_version_id=artifact.submission.version_id,
            outcome=ValidationOutcome.PASS,
            human_help_version_ids=(help_record.submission.version_id,)),)
        validation=self.validation("VALIDATION-TRIAL","CONFIG-W19",
            review.submission.version_id,artifact_id=artifact.submission.version_id,
            attempts=attempts)
        self.controller.append_validation(validation)
        adm_review=self.review_for("REVIEW-TRIAL-ADM-v001",(
            self.config_version("CONFIG-W19"),self.validation_version("VALIDATION-TRIAL")))
        trial=self.admission("ADMISSION-TRIAL","CONFIG-W19",
            adm_review.submission.version_id,validations=("VALIDATION-TRIAL",),
            manual=True,status=AdmissionStatus.CONTROLLED_TRIAL)
        self.controller.append_admission(trial)
        self.assertFalse(self.controller.authorizes("ADMISSION-TRIAL",
            configuration_id="CONFIG-W19",duty=ModelDuty.FACT_EXTRACTION,
            domains=("global-politics",),require_given_material=True,at=AT))

    def test_configuration_change_invalidates_old_admission_and_requires_revalidation(self):
        self.approved_fixture()
        changed=self.config("CONFIG-W19-CHANGED",prompt="9"*64)
        self.controller.append_configuration(changed)
        self.assertFalse(self.controller.authorizes("ADMISSION-W19-GIVEN",
            configuration_id="CONFIG-W19-CHANGED",duty=ModelDuty.FACT_EXTRACTION,
            domains=("global-politics",),require_given_material=True,at=AT))
        plan=self.controller.revalidation_requirements(
            self.controller.load_configuration("CONFIG-W19"),changed)
        self.assertIn("prompt_sha256",plan.changed_fields)
        self.assertEqual(set(plan.required_kinds),{
            ValidationKind.GIVEN_MATERIAL,
            ValidationKind.REAL_RETRIEVAL,
            ValidationKind.CONSTRAINT_GAIN,
        })
        scope_changed=ModelTaskConfiguration.model_validate_json(
            changed.model_copy(update={"configuration_id":"CONFIG-W19-SCOPE",
                "domains":("global-politics","technology","business")}).model_dump_json())
        scope_plan=self.controller.revalidation_requirements(changed,scope_changed)
        self.assertEqual(set(scope_plan.required_kinds),{
            ValidationKind.GIVEN_MATERIAL,
            ValidationKind.REAL_RETRIEVAL,
        })


if __name__=="__main__":
    unittest.main()
