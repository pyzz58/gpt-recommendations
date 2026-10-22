"""W13 integration/failure tests with explicitly synthetic, owned fixtures.

These exercise real SQLite transactions and private files. They do not certify
content, legal permission assessments, natural historical changes or production.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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
                                  MissingVersion, PermissionDenied, navigation, versions)
from intelligence.contracts import (DataPeriod, MaterialUse, ObjectKind, Precision,
    ReferenceUse, Representation, RightsBasis, RightsGrant, SourceTimes, TimePoint,
    VersionReference, VersionSubmission)

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
BODY = "公开合成测试稿：1 MW持续1小时为1 MWh。\n".encode()


def grant(rights_id=None, pointer=False):
    return RightsGrant(rights_id=rights_id or ('RIGHTS-POINTER' if pointer else 'RIGHTS-OWN'),
        basis=RightsBasis.POINTER_ONLY if pointer else RightsBasis.OWN_WORK,
        allowed_uses=frozenset({MaterialUse.INDEX} if pointer else {MaterialUse.INDEX,MaterialUse.STORE_BODY}),
        evidence="Explicit synthetic fixture authored for these tests", checked_by="test fixture", checked_at=AT)


def submission(version="DOC-v001", *, object_id="DOC", parent=None, kind=ObjectKind.DOCUMENT,
               refs=(), rights=None, pointer=False, title="公开合成测试稿"):
    return VersionSubmission(object_id=object_id, version_id=version, parent_version_id=parent,
        kind=kind, title=title, spec_sha256="a"*64, created_at=AT,
        source_times=SourceTimes(event=TimePoint(precision=Precision.DATE,value="2026-10-18")),
        rights=rights or grant(pointer=pointer), references=refs,
        representation=Representation.POINTER_ONLY if pointer else Representation.FULL_BODY,
        source_locator="https://example.invalid/original" if pointer else None)


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
        with self.assertRaises(BodyUnavailable):
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
            c.execute(text('UPDATE schema_info SET version=1 WHERE id=1'))
        with Archive(self.root) as migrated:
            self.assertEqual(migrated.schema_version(),2)
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


class CliTests(unittest.TestCase):
    def test_cli_import_retrieve_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);meta=root/'record.json';body=root/'body.md';out=root/'restored.md'
            meta.write_text(submission().model_dump_json());body.write_bytes(BODY)
            prefix=[sys.executable,'-m','intelligence','--root',str(root/'archive')]
            put=subprocess.run(prefix+['put','--metadata',str(meta),'--body',str(body)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(put.returncode,0,put.stderr)
            get=subprocess.run(prefix+['get','DOC-v001','--body-output',str(out)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(get.returncode,0,get.stderr);self.assertEqual(out.read_bytes(),BODY)
            again=subprocess.run(prefix+['get','DOC-v001','--body-output',str(out)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(again.returncode,2);self.assertEqual(out.read_bytes(),BODY)


if __name__=='__main__':unittest.main()
