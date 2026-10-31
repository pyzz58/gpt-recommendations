"""W13 integration/failure tests with explicitly synthetic, owned fixtures.

These exercise real SQLite transactions and private files. They do not certify
content, legal permission assessments, natural historical changes or production.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from intelligence.archive import (Archive, ArchiveError, BodyUnavailable, Conflict, CorruptArchive,
                                  MissingVersion, PermissionDenied, PrivatePathError,
                                  require_private_output_path, navigation, versions)
from intelligence.contracts import (DataPeriod, MaterialUse, ObjectKind, Precision,
    PermissionState, ReferencedMaterial, ReferenceReadRequest, ReferenceUse, Representation,
    RightsBasis, RightsGrant, Scope, ScopeMode, SourceTimes, TimePoint, UseContext,
    UsePermission, ValidityMode, VersionReference, VersionSubmission)

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
BODY = "公开合成测试稿：1 MW持续1小时为1 MWh。\n".encode()


def permission(use, *, state=PermissionState.ALLOWED, validity=ValidityMode.OPEN_ENDED,
               effective_from=None, effective_until=None, territories=None, providers=None,
               content_scope=None, excluded_content=(), conditions=(), conditions_satisfied=None,
               attribution_requirements=()):
    any_scope = lambda: Scope(mode=ScopeMode.ANY)
    return UsePermission(use=use, state=state, validity=validity,
        effective_from=effective_from, effective_until=effective_until,
        territories=territories or any_scope(), providers=providers or any_scope(),
        content_scope=content_scope or any_scope(), excluded_content=excluded_content,
        conditions=conditions, conditions_satisfied=conditions_satisfied,
        attribution_requirements=attribution_requirements)


def grant(rights_id=None, pointer=False, extra_uses=(), permissions=None, **metadata):
    structured = list(permissions) if permissions is not None else [permission(use) for use in extra_uses]
    if not pointer and not any(item.use is MaterialUse.STORE_BODY for item in structured):
        structured.insert(0, permission(MaterialUse.STORE_BODY))
    return RightsGrant(rights_id=rights_id or ('RIGHTS-POINTER' if pointer else 'RIGHTS-OWN'),
        basis=RightsBasis.POINTER_ONLY if pointer else RightsBasis.OWN_WORK,
        allowed_uses=frozenset({MaterialUse.INDEX} if pointer else {MaterialUse.INDEX,MaterialUse.STORE_BODY,*extra_uses}),
        evidence="Explicit synthetic fixture authored for these tests", checked_by="test fixture", checked_at=AT,
        permissions=tuple(structured),
        **metadata)


def submission(version="DOC-v001", *, object_id="DOC", parent=None, kind=ObjectKind.DOCUMENT,
               refs=(), rights=None, pointer=False, title="公开合成测试稿"):
    return VersionSubmission(object_id=object_id, version_id=version, parent_version_id=parent,
        kind=kind, title=title, spec_sha256="a"*64, created_at=AT,
        source_times=SourceTimes(event=TimePoint(precision=Precision.DATE,value="2026-10-18")),
        rights=rights or grant(pointer=pointer), references=refs,
        representation=Representation.POINTER_ONLY if pointer else Representation.FULL_BODY,
        source_locator="https://example.invalid/original" if pointer else None)


def read_request(**changes):
    context = UseContext(at=AT, provider="fixture-provider", territory="NZ",
                         content=("synthetic body",))
    values = dict(request_id="READ-1", spec_sha256="a"*64, created_at=AT,
        consumer="T01", owner_version_id="OWNER-v001",
        reference=VersionReference(target_version_id="DOC-v001",use=ReferenceUse.SOURCE,locator="section 2"),
        expected_kind=ObjectKind.DOCUMENT, intended_use=MaterialUse.STORE_BODY,
        expected_body_sha256=hashlib.sha256(BODY).hexdigest(), use_context=context)
    return ReferenceReadRequest(**{**values,**changes})


class ContractTests(unittest.TestCase):
    def test_unknown_and_date_precision_never_invent_midnight(self):
        sub = submission()
        self.assertEqual(sub.source_times.event.value, "2026-10-18")
        self.assertIsNone(sub.source_times.published.value)
        self.assertEqual(sub.source_times.published.precision, Precision.UNKNOWN)
        for value in ({"precision":"UNKNOWN","value":"2026-10-18","reason":"unknown"},
                      {"precision":"DATE","value":"2026-10-18T00:00:00Z"},
                      {"precision":"DATE","value":"2026-W01-1"},
                      {"precision":"INSTANT","value":"2026-10-18T12:00:00"}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                TimePoint.model_validate_json(json.dumps(value))

    def test_instant_and_data_period_require_aware_ordered_times(self):
        point = TimePoint(precision=Precision.INSTANT,value="2026-10-18T23:00:00+13:00")
        self.assertEqual(point.value,"2026-10-18T23:00:00+13:00")
        with self.assertRaises(ValidationError):
            DataPeriod(start=AT,end_exclusive=AT)

    def test_event_ranges_preserve_timezone_provenance_and_endpoint_semantics(self):
        date_range=TimePoint(precision=Precision.DATE_RANGE,start_value="2026-10-18",
            end_value="2026-10-20",source_timezone="Pacific/Auckland",
            provenance="Published policy and effective notice",uncertainty="Inclusive publication dates")
        self.assertEqual((date_range.start_value,date_range.end_value),("2026-10-18","2026-10-20"))
        self.assertTrue(date_range.start_inclusive and date_range.end_inclusive)
        instant_range=TimePoint(precision=Precision.INSTANT_RANGE,
            start_value="2026-10-18T23:00:00+13:00",end_value="2026-10-19T06:00:00+09:00",
            source_timezone="Mixed source offsets",provenance="Two first-party notices")
        self.assertEqual(instant_range.source_timezone,"Mixed source offsets")
        partial=TimePoint(precision=Precision.PARTIAL_RANGE,start_value="2026-10-18",
            endpoint_precision=Precision.DATE,reason="End date not established",
            provenance="First-party notice",uncertainty="Only opening bound known")
        self.assertIsNone(partial.end_value)
        for invalid in (
            dict(precision=Precision.DATE_RANGE,start_value="2026-10-20",end_value="2026-10-18"),
            dict(precision=Precision.INSTANT_RANGE,start_value="2026-10-19T00:00:00+13:00",
                 end_value="2026-10-18T00:00:00+13:00"),
            dict(precision=Precision.PARTIAL_RANGE,start_value="2026-10-18",
                 endpoint_precision=Precision.DATE),
            dict(precision=Precision.PARTIAL_RANGE,start_value="2026-10-18"),
        ):
            with self.subTest(invalid=invalid),self.assertRaises(ValidationError):
                TimePoint(**invalid)

    def test_legacy_time_contract_roundtrips_without_inventing_new_fields(self):
        legacy=TimePoint.model_validate_json(json.dumps({
            "precision":"DATE","value":"2026-10-18"}))
        self.assertEqual(legacy,TimePoint(precision=Precision.DATE,value="2026-10-18"))
        self.assertIsNone(legacy.source_timezone)

    def test_legacy_version_contract_remains_readable_and_is_not_widened(self):
        raw=json.loads(submission().model_dump_json())
        raw["schema_version"]=1
        for key in ("work_title","source_locator","terms_url","terms_version","grantor","permissions"):
            raw["rights"].pop(key,None)
        for key in ("start_value","end_value","endpoint_precision","start_inclusive","end_inclusive",
                    "source_timezone","provenance","uncertainty"):
            raw["source_times"]["event"].pop(key,None)
        legacy=VersionSubmission.model_validate_json(json.dumps(raw))
        self.assertEqual(legacy.schema_version,1)
        self.assertEqual(legacy.rights.permissions,())
        self.assertEqual(submission().schema_version,2)

    def test_strict_types_enums_and_unknown_fields(self):
        original=json.loads(submission().model_dump_json())
        for key,value in [('schema_version','1'),('kind','Unrecognised'),('publication_enabled',True),
                          ('version_id','../escape'),('spec_sha256','not-a-digest')]:
            with self.subTest(key=key),self.assertRaises(ValidationError):
                VersionSubmission.model_validate_json(json.dumps({**original,key:value}))

    def test_unknown_time_requires_reason(self):
        with self.assertRaises(ValidationError):
            TimePoint()

    def test_pointer_grant_cannot_authorize_full_text(self):
        with self.assertRaises(ValidationError):
            submission(rights=grant(pointer=True))
        with self.assertRaises(ValidationError):
            RightsGrant(rights_id="R",basis=RightsBasis.POINTER_ONLY,
                allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
                evidence="not a full-text grant",checked_by="test",checked_at=AT)

    def test_self_or_duplicate_reference_is_rejected(self):
        ref=VersionReference(target_version_id="SOURCE-1",use=ReferenceUse.SOURCE,locator="page 1")
        for refs in [(ref,ref),(ref.model_copy(update={'target_version_id':'DOC-v001'}),)]:
            with self.subTest(refs=refs),self.assertRaises(ValidationError):
                submission(refs=refs)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'archive'
        self.archive=Archive(self.root)
        self.addCleanup(self.archive.close)

    def test_roundtrip_original_bytes_survives_a_new_connection(self):
        before=datetime.now(timezone.utc)
        stored=self.archive.append(submission(),BODY)
        after=datetime.now(timezone.utc)
        self.assertEqual(stored.body_sha256,hashlib.sha256(BODY).hexdigest())
        self.assertEqual(stored.body_bytes,len(BODY))
        self.assertEqual(stored.submission.source_times,submission().source_times)
        with Archive(self.root) as reopened:
            self.assertEqual(reopened.read_body('DOC-v001'),BODY)
            self.assertGreaterEqual(reopened.get('DOC-v001').recorded_at,before)
            self.assertLessEqual(reopened.get('DOC-v001').recorded_at,after)
        self.assertEqual(self.root.stat().st_mode & 0o777,0o700)
        self.assertEqual(next((self.root/'bodies').glob('*.bin')).stat().st_mode & 0o777,0o600)

    def test_private_archive_cannot_be_created_inside_source_directory(self):
        target=ROOT/'must-not-create-private-archive'
        with self.assertRaises(ArchiveError):Archive(target)
        self.assertFalse(target.exists())

    def test_private_output_rejects_all_git_worktrees_and_preserves_existing_data(self):
        repo=ROOT.parents[1]
        for target in (repo,repo/'private-new',
                       repo/'newspaper'/'private-nested'/'not-created'):
            with self.subTest(target=target),self.assertRaises(PrivatePathError):
                Archive(target)
            if target != repo:
                self.assertFalse(target.exists())
        with tempfile.TemporaryDirectory() as temp:
            fake_repo=Path(temp)/'repo';fake_repo.mkdir();(fake_repo/'.git').mkdir()
            existing=fake_repo/'existing-private-probe';existing.mkdir()
            (existing/'archive.sqlite3').write_bytes(b'preserve me')
            (existing/'bodies').mkdir()
            with self.assertRaises(PrivatePathError) as denied:Archive(existing)
            self.assertIn('Existing data was not modified',str(denied.exception))
            self.assertEqual((existing/'archive.sqlite3').read_bytes(),b'preserve me')
            self.assertTrue((existing/'bodies').is_dir())

    def test_private_output_handles_linked_worktrees_aliases_and_outside_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            linked=base/'linked-worktree';linked.mkdir()
            (linked/'.git').write_text('gitdir: /synthetic/not-needed-for-marker-check\n')
            marker_dir=base/'other-worktree';marker_dir.mkdir();(marker_dir/'.git').mkdir()
            for target in (linked/'private',marker_dir/'private'):
                with self.subTest(target=target),self.assertRaises(PrivatePathError):
                    require_private_output_path(target)
            alias=base/'repo-alias';alias.symlink_to(ROOT.parents[1],target_is_directory=True)
            with self.assertRaises(PrivatePathError):
                require_private_output_path(alias/'private')
            outside=base/'outside';outside.mkdir()
            self.assertEqual(require_private_output_path(outside/'nested'/'private'),
                (outside/'nested'/'private').resolve())

    def test_private_output_symlink_and_out_of_worktree_archive_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);outside=base/'outside';outside.mkdir()
            alias=base/'file-link';alias.symlink_to(outside/'target')
            with self.assertRaises(PrivatePathError):
                require_private_output_path(alias)
            with Archive(outside/'archive') as archive:
                self.assertEqual(archive.schema_version(),3)
            self.assertEqual((outside/'archive').stat().st_mode & 0o777,0o700)

    def test_full_body_admission_requires_explicit_active_storage_permission(self):
        now=datetime.now(timezone.utc)
        missing=RightsGrant(rights_id='RIGHTS-NO-STORAGE',basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence='Owned audit fixture with no structured storage term',
            checked_by='test fixture',checked_at=now,permissions=())
        cases=(
            ('DENIED',permission(MaterialUse.STORE_BODY,state=PermissionState.DENIED)),
            ('EXPIRED',permission(MaterialUse.STORE_BODY,validity=ValidityMode.BOUNDED,
                effective_until=now-timedelta(seconds=1))),
            ('UNCONFIRMED',permission(MaterialUse.STORE_BODY,
                conditions=('written approval required',))),
        )
        for label,item in cases:
            rights=grant(f'RIGHTS-{label}',permissions=(item,))
            with self.subTest(label=label),self.assertRaises(PermissionDenied):
                self.archive.append(submission(f'{label}-v001',object_id=label,rights=rights),BODY)
            self.assertEqual(list((self.root/'bodies').iterdir()),[])
        with self.assertRaises(PermissionDenied):
            self.archive.append(submission('MISSING-v001',object_id='MISSING',rights=missing),BODY)
        with self.assertRaises(PermissionDenied):
            self.archive.append(submission('MISSING-v1-v001',object_id='MISSING-V1',
                rights=missing).model_copy(update={'schema_version':1}),BODY)
        self.assertEqual(list((self.root/'bodies').iterdir()),[])

    def test_old_schema_one_body_remains_readable_without_widening_new_writes(self):
        self.archive.append(submission(),BODY)
        self.archive.close()
        with sqlite3.connect(self.root/'archive.sqlite3') as c:
            c.execute('DROP TRIGGER immutable_versions_update')
            record=json.loads(c.execute("SELECT record FROM versions WHERE version_id='DOC-v001'").fetchone()[0])
            record['schema_version']=1
            record['rights']['permissions']=[]
            c.execute('UPDATE versions SET record=? WHERE version_id=?',(json.dumps(record),'DOC-v001'))
        with Archive(self.root) as legacy:
            self.assertEqual(legacy.read_body('DOC-v001'),BODY)

    def test_model_read_requires_current_storage_permission(self):
        now=datetime.now(timezone.utc)
        storage=permission(MaterialUse.STORE_BODY,validity=ValidityMode.BOUNDED,
            effective_until=now+timedelta(seconds=30))
        model=permission(MaterialUse.MODEL_PROCESS)
        rights=grant('RIGHTS-STORAGE-EXPIRY',extra_uses=(MaterialUse.MODEL_PROCESS,),
            permissions=(storage,model))
        self.reference_fixture(rights=rights)
        request=read_request(intended_use=MaterialUse.MODEL_PROCESS,
            use_context=UseContext(at=now+timedelta(minutes=1),
                provider='fixture-provider',territory='NZ',content=('synthetic body',)))
        with self.assertRaisesRegex(PermissionDenied,'expired'):
            self.archive.read_reference(request)

    def test_partial_content_returns_only_explicitly_authorized_selection(self):
        storage=permission(MaterialUse.STORE_BODY)
        model=permission(MaterialUse.MODEL_PROCESS,
            content_scope=Scope(mode=ScopeMode.LIST,values=('approved-text','excluded-photo')),
            excluded_content=('excluded-photo',))
        mixed=b'OWNED APPROVED TEXT\nOWNED SYNTHETIC EXCLUDED PHOTO BYTES\n'
        self.archive.append(submission(rights=grant('RIGHTS-MIXED',
            extra_uses=(MaterialUse.MODEL_PROCESS,),permissions=(storage,model))),mixed)
        owner=self.archive.append(submission('OWNER-v001',object_id='OWNER',kind=ObjectKind.TASK,
            refs=(read_request().reference,)),BODY)
        self.assertEqual(owner.submission.version_id,'OWNER-v001')
        request=read_request(intended_use=MaterialUse.MODEL_PROCESS,
            expected_body_sha256=hashlib.sha256(mixed).hexdigest(),
            use_context=UseContext(at=AT,provider='fixture-provider',territory='NZ',
                content=('approved-text',)))
        with self.assertRaisesRegex(PermissionDenied,'selected-version'):
            self.archive.read_reference(request)
        selected_body=b'OWNED APPROVED TEXT\n'
        selected_rights=grant('RIGHTS-SELECTED',extra_uses=(MaterialUse.MODEL_PROCESS,))
        selected=self.archive.append(VersionSubmission(
            object_id='SELECTED',version_id='SELECTED-v001',kind=ObjectKind.MATERIAL_SELECTION,
            title='Approved owned excerpt',spec_sha256='a'*64,created_at=AT,rights=selected_rights,
            representation=Representation.FULL_BODY,
            references=(VersionReference(target_version_id='DOC-v001',use=ReferenceUse.SUPPORT,
                locator='approved-text'),)),selected_body)
        approved=read_request(intended_use=MaterialUse.MODEL_PROCESS,
            expected_body_sha256=hashlib.sha256(mixed).hexdigest(),
            expected_selected_body_sha256=hashlib.sha256(selected_body).hexdigest(),
            use_context=UseContext(at=AT,provider='fixture-provider',territory='NZ',
                content=('approved-text',),selected_version_id='SELECTED-v001'))
        material=self.archive.read_reference(approved)
        self.assertEqual(material.body,selected_body)
        self.assertNotIn(b'EXCLUDED PHOTO BYTES',material.body)
        self.assertEqual(material.selected_version.submission.version_id,selected.submission.version_id)
        same_rights=grant('RIGHTS-SELECTED-SAME',extra_uses=(MaterialUse.MODEL_PROCESS,))
        self.archive.append(VersionSubmission(
            object_id='SELECTED-SAME',version_id='SELECTED-SAME-v001',
            kind=ObjectKind.MATERIAL_SELECTION,title='Relabelled excluded bytes',
            spec_sha256='a'*64,created_at=AT,rights=same_rights,
            representation=Representation.FULL_BODY,
            references=(VersionReference(target_version_id='DOC-v001',use=ReferenceUse.SUPPORT,
                locator='attempted relabel'),)),mixed)
        with self.assertRaisesRegex(PermissionDenied,'byte-identical'):
            self.archive.read_reference(read_request(
                intended_use=MaterialUse.MODEL_PROCESS,
                expected_body_sha256=hashlib.sha256(mixed).hexdigest(),
                use_context=UseContext(at=AT,provider='fixture-provider',territory='NZ',
                    content=('approved-text',),selected_version_id='SELECTED-SAME-v001')))

    def test_unrelated_nonempty_directory_is_not_modified(self):
        target=Path(self.temp.name)/'unrelated';target.mkdir();(target/'keep.txt').write_text('keep')
        mode=target.stat().st_mode
        with self.assertRaises(ArchiveError):Archive(target)
        self.assertEqual(target.stat().st_mode,mode)
        self.assertEqual([p.name for p in target.iterdir()],['keep.txt'])

    def test_unrelated_database_is_not_adopted_as_an_archive(self):
        target=Path(self.temp.name)/'other-database';target.mkdir()
        with sqlite3.connect(target/'archive.sqlite3') as c:c.execute('CREATE TABLE unrelated(value TEXT)')
        with self.assertRaises(CorruptArchive):Archive(target)
        with sqlite3.connect(target/'archive.sqlite3') as c:
            self.assertEqual(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('unrelated',)])

    def test_append_preserves_old_manuscript_and_judgment(self):
        self.archive.append(submission(),BODY)
        self.archive.append(submission('DOC-v002',parent='DOC-v001'),b'revised own draft')
        self.assertEqual(self.archive.read_body('DOC-v001'),BODY)
        self.assertEqual(self.archive.read_body('DOC-v002'),b'revised own draft')
        self.assertEqual(self.archive.get('DOC-v002').ordinal,2)

    def test_duplicate_id_or_foreign_stale_parent_cannot_overwrite(self):
        self.archive.append(submission(),BODY)
        for sub in [submission(),submission('DOC-v002',parent='missing'),
                    submission('OTHER-v001',object_id='OTHER',parent='DOC-v001')]:
            with self.subTest(sub=sub.version_id),self.assertRaises(Conflict):
                self.archive.append(sub,b'wrong')
        self.archive.append(submission('DOC-v002',parent='DOC-v001'),b'new')
        with self.assertRaises(Conflict):
            self.archive.append(submission('DOC-v003',parent='DOC-v001'),b'stale')
        self.assertEqual(self.archive.read_body('DOC-v001'),BODY)

    def test_object_kind_and_grant_identity_cannot_change(self):
        self.archive.append(submission(),BODY)
        with self.assertRaises(Conflict):
            self.archive.append(submission('DOC-v002',parent='DOC-v001',kind=ObjectKind.ARTICLE),BODY)
        changed=grant().model_copy(update={'evidence':'different permission assessment'})
        with self.assertRaises(Conflict):
            self.archive.append(submission('OTHER-v001',object_id='OTHER',rights=changed),BODY)

    def test_dangling_reference_rolls_back_objects_grants_files_and_index(self):
        missing=VersionReference(target_version_id='MISSING',use=ReferenceUse.SUPPORT,locator='claim 1')
        with self.assertRaises(MissingVersion):
            self.archive.append(submission(refs=(missing,)),BODY)
        self.assertEqual(list((self.root/'bodies').iterdir()),[])
        self.assertEqual(self.archive.find('测试稿'),[])
        with self.assertRaises(MissingVersion):
            self.archive.get('DOC-v001')
        self.archive.append(submission(),BODY)

    def test_one_source_version_shared_by_multiple_module_records(self):
        source=submission('SOURCE-v001',object_id='SOURCE',kind=ObjectKind.SOURCE,pointer=True)
        self.archive.append(source)
        ref=VersionReference(target_version_id='SOURCE-v001',use=ReferenceUse.SOURCE,locator='section 2')
        for kind in [ObjectKind.TASK,ObjectKind.DOSSIER,ObjectKind.ARTICLE,ObjectKind.REVIEW,ObjectKind.EDITION]:
            self.archive.append(submission(kind.value+'-v001',object_id=kind.value,kind=kind,refs=(ref,)),BODY)
        self.assertEqual(len(self.archive.referrers('SOURCE-v001')),5)
        with self.archive.engine.connect() as c:
            rows=c.execute(select(versions.c.version_id).where(versions.c.object_id=='SOURCE')).all()
        self.assertEqual(rows,[('SOURCE-v001',)])

    def test_pointer_index_is_never_returned_as_original(self):
        self.archive.append(submission(pointer=True))
        self.assertEqual(len(self.archive.find('测试稿')),1)
        with self.assertRaises(PermissionDenied):
            self.archive.read_body('DOC-v001')
        with self.assertRaises(PermissionDenied):
            self.archive.append(submission('OTHER-v001',object_id='OTHER',pointer=True),BODY)

    def test_missing_or_corrupt_body_is_detected_without_index_fallback(self):
        self.archive.append(submission(),BODY)
        body_path=next((self.root/'bodies').glob('*.bin'))
        body_path.write_bytes(b'changed')
        with self.assertRaises(CorruptArchive):
            self.archive.read_body('DOC-v001')
        body_path.unlink()
        with self.assertRaises(BodyUnavailable):
            self.archive.read_body('DOC-v001')
        self.assertEqual(len(self.archive.find('测试稿')),1)

    def test_body_symlink_is_rejected(self):
        self.archive.append(submission(),BODY)
        body_path=next((self.root/'bodies').glob('*.bin'))
        outside=Path(self.temp.name)/'outside';outside.write_bytes(BODY)
        body_path.unlink();body_path.symlink_to(outside)
        with self.assertRaises(CorruptArchive):
            self.archive.read_body('DOC-v001')

    def test_revocation_denies_and_purges_all_same_grant_versions(self):
        self.archive.append(submission(),BODY)
        self.archive.append(submission('DOC-v002',parent='DOC-v001'),b'new')
        result=self.archive.revoke_body_retention('RIGHTS-OWN','synthetic permission withdrawal')
        self.assertEqual(set(result.purged_versions),{'DOC-v001','DOC-v002'})
        self.assertEqual(result.failed_versions,())
        self.assertEqual(list((self.root/'bodies').iterdir()),[])
        for vid in result.affected_versions:
            self.assertTrue(self.archive.get(vid).body_retention_revoked)
            with self.assertRaises(PermissionDenied):self.archive.read_body(vid)
        with self.assertRaises(PermissionDenied):
            self.archive.append(submission('DOC-v003',parent='DOC-v002'),BODY)
        again=self.archive.revoke_body_retention('RIGHTS-OWN','idempotent retry')
        self.assertEqual(again.recorded_at,result.recorded_at)

    def test_failed_purge_never_rolls_back_denial_and_retry_can_finish(self):
        self.archive.append(submission(),BODY)
        original=Path.unlink
        def deny(path,*args,**kwargs):
            if path.suffix=='.bin':raise OSError('simulated disk denial')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',deny):
            result=self.archive.revoke_body_retention('RIGHTS-OWN','test failed deletion')
        self.assertEqual(result.failed_versions,('DOC-v001',))
        with self.assertRaises(PermissionDenied):self.archive.read_body('DOC-v001')
        result=self.archive.revoke_body_retention('RIGHTS-OWN','retry purge')
        self.assertEqual(result.failed_versions,())

    def test_revocation_does_not_delete_other_permission_copies(self):
        self.archive.append(submission(),BODY)
        self.archive.append(submission('OTHER-v001',object_id='OTHER',rights=grant('RIGHTS-OTHER')),BODY)
        self.archive.revoke_body_retention('RIGHTS-OWN','test one grant')
        self.assertEqual(self.archive.read_body('OTHER-v001'),BODY)

    def test_index_rebuild_uses_authoritative_records(self):
        self.archive.append(submission(),BODY)
        with self.archive.engine.begin() as c:c.execute(delete(navigation))
        self.assertEqual(self.archive.find('测试稿'),[])
        self.assertEqual(self.archive.read_body('DOC-v001'),BODY)
        self.assertEqual(self.archive.rebuild_index(),1)
        self.assertEqual(self.archive.find('测试稿')[0]['version_id'],'DOC-v001')

    def test_schema_v1_compatible_test_copy_migrates_without_rewriting(self):
        # Explicit migration fixture: the compatible v1 schema lacks only the index.
        self.archive.append(submission(),BODY)
        before=self.archive.get('DOC-v001').model_dump_json()
        with self.archive.engine.begin() as c:
            c.execute(text('DROP TABLE navigation_index'))
            c.execute(text('DROP TABLE rights_use_revocations'))
            c.execute(text('UPDATE schema_info SET version=1 WHERE id=1'))
        with Archive(self.root) as migrated:
            self.assertEqual(migrated.schema_version(),3)
            self.assertEqual(migrated.get('DOC-v001').model_dump_json(),before)
            self.assertEqual(migrated.read_body('DOC-v001'),BODY)
            self.assertEqual(migrated.find('测试稿')[0]['version_id'],'DOC-v001')

    def test_future_schema_is_not_silently_downgraded(self):
        with self.archive.engine.begin() as c:c.execute(text('UPDATE schema_info SET version=99 WHERE id=1'))
        with self.assertRaises(CorruptArchive):Archive(self.root)

    def test_database_blocks_accidental_bulk_history_update(self):
        self.archive.append(submission(),BODY)
        for sql in ["UPDATE versions SET record='{}'","DELETE FROM versions","DELETE FROM rights_grants"]:
            with self.subTest(sql=sql),self.assertRaises(IntegrityError):
                with self.archive.engine.begin() as c:c.execute(text(sql))
        self.assertEqual(self.archive.read_body('DOC-v001'),BODY)

    def test_post_file_transaction_failure_cleans_uncommitted_file(self):
        # Failure injected after the body write, before commit.
        with self.archive.engine.begin() as c:
            c.execute(text("CREATE TRIGGER reject_index BEFORE INSERT ON navigation_index BEGIN SELECT RAISE(ABORT,'test rejection'); END"))
        with self.assertRaises(Conflict):self.archive.append(submission(),BODY)
        self.assertEqual(list((self.root/'bodies').iterdir()),[])
        with self.assertRaises(MissingVersion):self.archive.get('DOC-v001')

    def test_two_writers_do_not_lose_a_version_update(self):
        self.archive.append(submission(),BODY)
        def writer(number):
            with Archive(self.root) as a:
                try:
                    a.append(submission(f'DOC-v00{number}',parent='DOC-v001'),str(number).encode())
                    return 'committed'
                except Conflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(writer,[2,3]))
        self.assertEqual(sorted(result),['committed','conflict'])
        self.assertEqual(self.archive.read_body('DOC-v001'),BODY)

    def test_unvalidated_construct_cannot_bypass_contract(self):
        bad=submission().model_copy(update={'schema_version':'1'})
        with self.assertRaises(ValidationError):self.archive.append(bad,BODY)

    def test_arbitrary_binary_material_is_retrieved_exactly(self):
        body=b'%PDF-1.7\x00\xff\r\nsynthetic binary test'
        self.archive.append(submission(),body)
        self.assertEqual(self.archive.read_body('DOC-v001'),body)

    def reference_fixture(self, *, rights=None, pointer=False, body=BODY):
        target=submission(rights=rights,pointer=pointer)
        self.archive.append(target,None if pointer else body)
        self.archive.append(submission('OWNER-v001',object_id='OWNER',kind=ObjectKind.TASK,
            refs=(read_request().reference,)),b'owned reference record')
        return target

    def test_reference_consumers_share_the_pinned_original_after_revision(self):
        rights=grant('RIGHTS-PROCESS',extra_uses=(MaterialUse.MODEL_PROCESS,))
        self.reference_fixture(rights=rights)
        self.archive.append(submission('DOC-v002',parent='DOC-v001',rights=rights),b'newer original')
        for consumer in ('T01','T04','T05','T09','T10'):
            before=datetime.now(timezone.utc)
            result=self.archive.read_reference(read_request(consumer=consumer,intended_use=MaterialUse.MODEL_PROCESS))
            self.assertEqual(result.body,BODY)
            self.assertEqual(result.version.submission.version_id,'DOC-v001')
            self.assertEqual(result.owner.submission.version_id,'OWNER-v001')
            self.assertEqual(result.request.consumer,consumer)
            self.assertGreaterEqual(result.recorded_at,before)
            self.assertLessEqual(result.recorded_at,datetime.now(timezone.utc))
        with self.archive.engine.connect() as c:
            self.assertEqual(c.execute(select(versions.c.version_id).where(versions.c.version_id=='DOC-v001')).all(),[('DOC-v001',)])

    def test_reference_cannot_invent_owner_target_use_or_locator(self):
        self.reference_fixture()
        self.archive.append(submission('OTHER-v001',object_id='OTHER'),BODY)
        request=read_request()
        for change in ({'target_version_id':'OTHER-v001'},{'use':ReferenceUse.BASIS},{'locator':'unrecorded page'}):
            forged=request.reference.model_copy(update=change)
            with self.subTest(change=change),self.assertRaises(Conflict):
                self.archive.read_reference(read_request(reference=forged))
        with self.assertRaises(Conflict):
            self.archive.read_reference(read_request(owner_version_id='OTHER-v001'))
        with self.assertRaises(MissingVersion):
            self.archive.read_reference(read_request(owner_version_id='MISSING'))

    def test_reference_checks_kind_and_digest_and_ignores_navigation_substitutes(self):
        self.reference_fixture()
        for change in ({'expected_kind':ObjectKind.SOURCE},{'expected_body_sha256':'b'*64}):
            with self.subTest(change=change),self.assertRaises(Conflict):
                self.archive.read_reference(read_request(**change))
        with self.archive.engine.begin() as c:
            c.execute(text("UPDATE navigation_index SET title='fake body',kind='Source'"))
        self.assertEqual(self.archive.read_reference(read_request()).body,BODY)
        path=next((self.root/'bodies').glob(hashlib.sha256(b'DOC-v001').hexdigest()+'.bin'))
        path.write_bytes(b'corrupt')
        with self.assertRaises(CorruptArchive):self.archive.read_reference(read_request())
        path.unlink()
        with self.assertRaises(BodyUnavailable):self.archive.read_reference(read_request())

    def test_retention_does_not_authorize_processing_translation_or_delivery(self):
        self.reference_fixture()
        self.assertEqual(self.archive.read_body('DOC-v001'),BODY)
        self.assertEqual(self.archive.read_reference(read_request()).body,BODY)
        for purpose in (MaterialUse.MODEL_PROCESS,MaterialUse.TRANSLATE,MaterialUse.PRIVATE_DELIVERY):
            with self.subTest(purpose=purpose),self.assertRaises(PermissionDenied):
                self.archive.read_reference(read_request(intended_use=purpose))

    def test_explicit_purpose_grants_allow_exact_bytes(self):
        purposes=(MaterialUse.MODEL_PROCESS,MaterialUse.TRANSLATE,MaterialUse.PRIVATE_DELIVERY)
        self.reference_fixture(rights=grant('RIGHTS-USES',extra_uses=purposes))
        for purpose in purposes:
            self.assertEqual(self.archive.read_reference(read_request(intended_use=purpose)).body,BODY)

    def test_use_specific_validity_supplier_territory_and_conditions(self):
        from datetime import timedelta
        model=permission(MaterialUse.MODEL_PROCESS,validity=ValidityMode.BOUNDED,
            effective_from=AT-timedelta(days=1),effective_until=AT+timedelta(days=1),
            territories=Scope(mode=ScopeMode.LIST,values=("NZ",)),
            providers=Scope(mode=ScopeMode.LIST,values=("provider-a",)),
            conditions=("Private analysis only",),conditions_satisfied=True,
            attribution_requirements=("Cite the original publisher",))
        translate=permission(MaterialUse.TRANSLATE,validity=ValidityMode.BOUNDED,
            effective_until=AT)
        rights=grant('RIGHTS-SCOPED',extra_uses=(MaterialUse.MODEL_PROCESS,MaterialUse.TRANSLATE),
            permissions=(model,translate),work_title="Synthetic licensed report",
            source_locator="https://example.invalid/report",terms_url="https://example.invalid/terms",
            terms_version="2026-10-25",grantor="Fixture Publisher")
        self.reference_fixture(rights=rights)
        context=UseContext(at=AT,provider="PROVIDER-A",territory="nz",content=("approved",))
        allowed=self.archive.read_reference(read_request(intended_use=MaterialUse.MODEL_PROCESS,
            use_context=context))
        self.assertEqual(allowed.body,BODY)
        self.assertEqual(allowed.required_attribution,("Cite the original publisher",))
        self.assertEqual(allowed.version.submission.rights.terms_version,"2026-10-25")
        self.assertEqual(allowed.version.submission.rights.grantor,"Fixture Publisher")
        denials=[
            UseContext(at=AT,provider="provider-b",territory="NZ",content=("approved",)),
            UseContext(at=AT,provider="provider-a",territory="AU",content=("approved",)),
            UseContext(at=AT-timedelta(days=2),provider="provider-a",territory="NZ",content=("approved",)),
            UseContext(at=AT+timedelta(days=2),provider="provider-a",territory="NZ",content=("approved",)),
        ]
        for denied in denials:
            with self.subTest(denied=denied),self.assertRaises(PermissionDenied):
                self.archive.read_reference(read_request(intended_use=MaterialUse.MODEL_PROCESS,
                    use_context=denied))
        with self.assertRaises(PermissionDenied):
            self.archive.read_reference(read_request(intended_use=MaterialUse.TRANSLATE,
                use_context=UseContext(at=AT)))
        unconfirmed=grant('RIGHTS-CONDITION',extra_uses=(MaterialUse.MODEL_PROCESS,),
            permissions=(permission(MaterialUse.MODEL_PROCESS,
                conditions=("Written approval required",),conditions_satisfied=None),))
        self.assertEqual(unconfirmed.permissions[0].conditions_satisfied,None)
        self.archive.append(submission('COND-v001',object_id='COND',rights=unconfirmed),BODY)
        with self.archive.engine.connect() as c:
            with self.assertRaises(PermissionDenied):
                self.archive._check_use(c,self.archive.get('COND-v001'),
                    MaterialUse.MODEL_PROCESS,UseContext(at=AT))

    def test_unknown_permission_does_not_expand_legacy_allowed_uses(self):
        old=grant('RIGHTS-LEGACY',extra_uses=(MaterialUse.MODEL_PROCESS,),permissions=())
        self.assertEqual(old.allowed_uses,{MaterialUse.INDEX,MaterialUse.STORE_BODY,MaterialUse.MODEL_PROCESS})
        self.reference_fixture(rights=old)
        self.assertEqual(self.archive.read_body('DOC-v001'),BODY)
        with self.assertRaises(PermissionDenied):
            self.archive.read_reference(read_request(intended_use=MaterialUse.MODEL_PROCESS))
        self.assertIsNone(self.archive.read_reference(read_request(
            intended_use=MaterialUse.INDEX,expected_body_sha256=None)).body)
        unknown=grant('RIGHTS-UNKNOWN',extra_uses=(MaterialUse.TRANSLATE,),
            permissions=(permission(MaterialUse.TRANSLATE,state=PermissionState.UNKNOWN),))
        self.archive.append(submission('UNKNOWN-v001',object_id='UNKNOWN',rights=unknown),BODY)
        with self.archive.engine.connect() as c:
            with self.assertRaises(PermissionDenied):
                self.archive._check_use(c,self.archive.get('UNKNOWN-v001'),
                    MaterialUse.TRANSLATE,UseContext(at=AT))

    def test_partial_revocation_preserves_unrelated_uses_and_invalidates_dependent_storage(self):
        purposes=(MaterialUse.MODEL_PROCESS,MaterialUse.TRANSLATE)
        rights=grant('RIGHTS-PARTIAL',extra_uses=purposes)
        self.reference_fixture(rights=rights)
        self.assertEqual(self.archive.read_reference(read_request(
            intended_use=MaterialUse.TRANSLATE)).body,BODY)
        result=self.archive.revoke_rights(rights.rights_id,(MaterialUse.TRANSLATE,),
            "Translation permission withdrawn")
        self.assertEqual(result.revoked_uses,(MaterialUse.TRANSLATE,))
        self.assertEqual(result.purged_versions,())
        with self.assertRaises(PermissionDenied):
            self.archive.read_reference(read_request(intended_use=MaterialUse.TRANSLATE))
        self.assertEqual(self.archive.read_reference(read_request(
            intended_use=MaterialUse.MODEL_PROCESS)).body,BODY)
        storage=self.archive.revoke_rights(rights.rights_id,(MaterialUse.STORE_BODY,),
            "Storage permission withdrawn")
        self.assertIn('DOC-v001',storage.purged_versions)
        self.assertTrue(self.archive.get('DOC-v001').body_retention_revoked)
        self.assertIsNone(self.archive.read_reference(read_request(
            intended_use=MaterialUse.INDEX,expected_body_sha256=None)).body)
        with self.assertRaises(PermissionDenied):
            self.archive.read_reference(read_request(intended_use=MaterialUse.MODEL_PROCESS))
        with self.assertRaises(PermissionDenied):
            self.archive.append(submission('DOC-v002',parent='DOC-v001',rights=rights),b'new')
        other=self.archive.append(submission('OTHER-v001',object_id='OTHER',rights=grant('RIGHTS-OTHER')),BODY)
        self.assertEqual(other.submission.version_id,'OTHER-v001')
        with self.assertRaises(ValueError):
            self.archive.revoke_rights(rights.rights_id,(MaterialUse.INDEX,),"not a real withdrawal")

    def test_pointer_metadata_is_not_substituted_for_body(self):
        self.reference_fixture(pointer=True)
        metadata=self.archive.read_reference(read_request(intended_use=MaterialUse.INDEX,expected_body_sha256=None))
        self.assertIsNone(metadata.body)
        self.assertEqual(metadata.version.submission.representation,Representation.POINTER_ONLY)
        with self.assertRaises(PermissionDenied):
            self.archive.read_reference(read_request(intended_use=MaterialUse.MODEL_PROCESS,expected_body_sha256=None))

    def test_processing_permission_cannot_create_an_unretained_original(self):
        self.reference_fixture(pointer=True,rights=grant('RIGHTS-PROCESS',extra_uses=(MaterialUse.MODEL_PROCESS,)))
        with self.assertRaises(BodyUnavailable):
            self.archive.read_reference(read_request(intended_use=MaterialUse.MODEL_PROCESS,expected_body_sha256=None))

    def test_reference_withdrawal_blocks_body_even_when_purge_fails(self):
        self.reference_fixture(rights=grant('RIGHTS-PROCESS',extra_uses=(MaterialUse.MODEL_PROCESS,MaterialUse.TRANSLATE)))
        original=Path.unlink
        def deny(path,*args,**kwargs):
            if path.suffix=='.bin':raise OSError('simulated disk denial')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',deny):
            result=self.archive.revoke_body_retention('RIGHTS-PROCESS','test withdrawal with failed purge')
        self.assertEqual(result.failed_versions,('DOC-v001',))
        for purpose in (MaterialUse.STORE_BODY,MaterialUse.MODEL_PROCESS,MaterialUse.TRANSLATE):
            with self.subTest(purpose=purpose),self.assertRaises(PermissionDenied):
                self.archive.read_reference(read_request(intended_use=purpose))
        metadata=self.archive.read_reference(read_request(intended_use=MaterialUse.INDEX))
        self.assertIsNone(metadata.body)
        self.assertTrue(metadata.version.body_retention_revoked)
        self.assertEqual(self.archive.revoke_body_retention('RIGHTS-PROCESS','retry').failed_versions,())

    def test_reference_request_cannot_bypass_strict_contract(self):
        self.reference_fixture()
        original=json.loads(read_request().model_dump_json())
        for change in ({'consumer':'T99'},{'schema_version':'1'},{'intended_use':'UNKNOWN'},
                       {'approval':'PASS'},{'created_at':'2026-10-23T00:00:00'}):
            with self.subTest(change=change),self.assertRaises(ValidationError):
                ReferenceReadRequest.model_validate_json(json.dumps({**original,**change}))
        with self.assertRaises(ValidationError):
            self.archive.read_reference(read_request().model_copy(update={'schema_version':'1'}))
        with self.assertRaises(TypeError):self.archive.read_reference(original)

    def test_reference_binary_receipt_roundtrips_without_utf8_assumption(self):
        binary=b'%PDF-1.7\x00\xff\r\nowned binary fixture'
        self.reference_fixture(body=binary)
        result=self.archive.read_reference(read_request(expected_body_sha256=hashlib.sha256(binary).hexdigest()))
        restored=ReferencedMaterial.model_validate_json(result.model_dump_json())
        self.assertEqual(restored.body,binary)
        self.assertTrue(ReferencedMaterial.model_config['extra']=='forbid')


class CliTests(unittest.TestCase):
    def test_cli_reference_schema_and_metadata_only_output_boundaries(self):
        schema=subprocess.run([sys.executable,'-m','intelligence','schema','--contract','reference-read'],
            cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(schema.returncode,0,schema.stderr)
        self.assertEqual(json.loads(schema.stdout)['title'],'ReferenceReadRequest')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);request_file=root/'request.json';out=root/'retrieved.bin'
            with Archive(root/'archive') as archive:
                archive.append(submission(),BODY)
                archive.append(submission('OWNER-v001',object_id='OWNER',kind=ObjectKind.TASK,
                    refs=(read_request().reference,)),b'owned reference record')
            command=[sys.executable,'-m','intelligence','--root',str(root/'archive'),
                'read-reference','--request',str(request_file)]
            request_file.write_text(read_request(intended_use=MaterialUse.MODEL_PROCESS).model_dump_json())
            denied=subprocess.run(command+['--body-output',str(out)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(denied.returncode,2)
            self.assertEqual(json.loads(denied.stderr)['error'],'PermissionDenied')
            self.assertFalse(out.exists());self.assertEqual(denied.stdout,'')
            request_file.write_text(read_request(intended_use=MaterialUse.INDEX).model_dump_json())
            index=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(index.returncode,0,index.stderr)
            self.assertNotIn('body',json.loads(index.stdout))
            no_body=subprocess.run(command+['--body-output',str(out)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(no_body.returncode,2);self.assertFalse(out.exists())
            request_file.write_text(read_request().model_dump_json())
            fetched=subprocess.run(command+['--body-output',str(out)],cwd=ROOT,capture_output=True,text=True,umask=0o022)
            self.assertEqual(fetched.returncode,0,fetched.stderr)
            self.assertEqual(out.read_bytes(),BODY)
            self.assertEqual(out.stat().st_mode & 0o777,0o600)
            self.assertNotIn('body',json.loads(fetched.stdout))
            self.assertNotIn(BODY.decode().strip(),fetched.stdout)
            again=subprocess.run(command+['--body-output',str(out)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(again.returncode,2);self.assertEqual(out.read_bytes(),BODY)

    def test_cli_import_retrieve_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);meta=root/'record.json';body=root/'body.md';out=root/'restored.md'
            meta.write_text(submission().model_dump_json());body.write_bytes(BODY)
            prefix=[sys.executable,'-m','intelligence','--root',str(root/'archive')]
            put=subprocess.run(prefix+['put','--metadata',str(meta),'--body',str(body)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(put.returncode,0,put.stderr)
            get=subprocess.run(prefix+['get','DOC-v001','--body-output',str(out)],cwd=ROOT,capture_output=True,text=True,umask=0o022)
            self.assertEqual(get.returncode,0,get.stderr);self.assertEqual(out.read_bytes(),BODY)
            self.assertEqual(out.stat().st_mode & 0o777,0o600)
            again=subprocess.run(prefix+['get','DOC-v001','--body-output',str(out)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(again.returncode,2);self.assertEqual(out.read_bytes(),BODY)

    def test_cli_body_exports_reject_paths_inside_repository(self):
        repo=ROOT.parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);meta=root/'record.json';body=root/'body.md';request=root/'request.json'
            meta.write_text(submission().model_dump_json());body.write_bytes(BODY)
            prefix=[sys.executable,'-m','intelligence','--root',str(root/'archive')]
            put=subprocess.run(prefix+['put','--metadata',str(meta),'--body',str(body)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(put.returncode,0,put.stderr)
            for relative in ('private-get-output.bin','newspaper/private-reference-output.bin'):
                output=repo/relative
                with self.subTest(relative=relative):
                    command=prefix+['get','DOC-v001','--body-output',str(output)]
                    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
                    self.assertEqual(result.returncode,2)
                    self.assertEqual(json.loads(result.stderr)['error'],'PrivatePathError')
                    self.assertFalse(output.exists())
            owner_meta=root/'owner.json'
            owner_meta.write_text(submission('OWNER-v001',object_id='OWNER',kind=ObjectKind.TASK,
                refs=(read_request().reference,)).model_dump_json())
            put_owner=subprocess.run(prefix+['put','--metadata',str(owner_meta),'--body',str(body)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(put_owner.returncode,0,put_owner.stderr)
            request.write_text(read_request().model_dump_json())
            read_output=repo/'newspaper'/'private-read-reference-output.bin'
            read=subprocess.run(prefix+['read-reference','--request',str(request),
                '--body-output',str(read_output)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(read.returncode,2)
            self.assertEqual(json.loads(read.stderr)['error'],'PrivatePathError')
            self.assertFalse(read_output.exists())

    def test_cli_partial_revocation_records_named_use(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);meta=root/'record.json';body=root/'body.md'
            rights=grant('RIGHTS-CLI',extra_uses=(MaterialUse.MODEL_PROCESS,MaterialUse.TRANSLATE))
            meta.write_text(submission(rights=rights).model_dump_json());body.write_bytes(BODY)
            prefix=[sys.executable,'-m','intelligence','--root',str(root/'archive')]
            put=subprocess.run(prefix+['put','--metadata',str(meta),'--body',str(body)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(put.returncode,0,put.stderr)
            revoked=subprocess.run(prefix+['revoke-use','RIGHTS-CLI','--use','TRANSLATE',
                '--reason','Synthetic translation withdrawal'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(revoked.returncode,0,revoked.stderr)
            result=json.loads(revoked.stdout)
            self.assertEqual(result['revoked_uses'],['TRANSLATE'])
            self.assertEqual(result['purged_versions'],[])
            self.assertTrue(next((root/'archive'/'bodies').iterdir()).is_file())


if __name__=='__main__':unittest.main()
