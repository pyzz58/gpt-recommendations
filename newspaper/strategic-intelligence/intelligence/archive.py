"""W13 shared SQLite + private version files, using SQLAlchemy Core.

One archive supplies the same immutable versions to T01/T04/T05/T09/T10/T11.
References and an index never turn a source into an established fact. Permission
assessment, content approval, as-of research queries and production recovery are
separate work packages. Files are private; an interrupted pre-commit write can
leave an unindexed file, which this API never treats as a committed version.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Iterator

from sqlalchemy import (Column, ForeignKey, Integer, MetaData, String, Table, Text,
                        UniqueConstraint, create_engine, delete, event, insert,
                        inspect, select, update)
from sqlalchemy.engine import Connection, URL
from sqlalchemy.exc import IntegrityError

from .contracts import (MaterialUse, Representation, RevocationResult,
                        StoredVersion, VersionSubmission)

CURRENT_SCHEMA = 2
metadata = MetaData()
schema_info = Table("schema_info", metadata, Column("id", Integer, primary_key=True),
                    Column("version", Integer, nullable=False))
objects = Table("objects", metadata, Column("object_id", String, primary_key=True),
                Column("kind", String, nullable=False))
grants = Table("rights_grants", metadata, Column("rights_id", String, primary_key=True),
               Column("record", Text, nullable=False))
versions = Table("versions", metadata,
    Column("version_id", String, primary_key=True),
    Column("object_id", String, ForeignKey("objects.object_id"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("parent_version_id", String, ForeignKey("versions.version_id")),
    Column("rights_id", String, ForeignKey("rights_grants.rights_id"), nullable=False),
    Column("record", Text, nullable=False), Column("recorded_at", String, nullable=False),
    Column("body_path", String), Column("body_sha256", String), Column("body_bytes", Integer),
    UniqueConstraint("object_id", "ordinal"))
references = Table("version_references", metadata,
    Column("version_id", String, ForeignKey("versions.version_id"), primary_key=True),
    Column("target_version_id", String, ForeignKey("versions.version_id"), primary_key=True),
    Column("use", String, primary_key=True), Column("locator", String, primary_key=True))
revocations = Table("body_retention_revocations", metadata,
    Column("rights_id", String, ForeignKey("rights_grants.rights_id"), primary_key=True),
    Column("reason", Text, nullable=False), Column("recorded_at", String, nullable=False))
navigation = Table("navigation_index", metadata,
    Column("version_id", String, ForeignKey("versions.version_id"), primary_key=True),
    Column("object_id", String, nullable=False), Column("kind", String, nullable=False),
    Column("title", Text, nullable=False))


class ArchiveError(Exception):
    """A known storage boundary failure; never a factual or content decision."""


class Conflict(ArchiveError):
    pass


class MissingVersion(ArchiveError):
    pass


class PermissionDenied(ArchiveError):
    pass


class BodyUnavailable(ArchiveError):
    pass


class CorruptArchive(ArchiveError):
    pass


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Archive:
    """Local archive. Constructing an instance creates or migrates its schema.

    append(submission, body) -> StoredVersion; get(version_id) -> metadata;
    read_body(version_id) -> original bytes; referrers/rebuild_index -> navigation.
    No method approves research, overwrites a version or changes a source time.
    """

    def __init__(self, root: str | Path):
        requested = Path(root).absolute()
        if requested.is_symlink():
            raise ArchiveError("Archive root cannot be a symlink")
        if requested.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
            raise ArchiveError("Private archive must be outside the public source directory")
        if requested.exists() and any(requested.iterdir()) and not (requested/"archive.sqlite3").is_file():
            raise ArchiveError("Existing nonempty directory is not a dedicated archive")
        requested.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root = requested.resolve()
        os.chmod(self.root, 0o700)
        self.bodies = self.root/"bodies"
        if self.bodies.is_symlink():
            raise ArchiveError("Body directory cannot be a symlink")
        self.bodies.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.bodies, 0o700)
        database = self.root/"archive.sqlite3"
        if database.is_symlink():
            raise ArchiveError("Database cannot be a symlink")
        self.engine = create_engine(URL.create("sqlite", database=str(database)),
                                    connect_args={"timeout": 10})

        @event.listens_for(self.engine, "connect")
        def sqlite_settings(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")

        try:
            self._migrate()
            os.chmod(database, 0o600)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self) -> Archive:
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def _write(self) -> Iterator[Connection]:
        # Take the SQLite write lock before checking parent/grant identity.
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _migrate(self) -> None:
        with self._write() as c:
            existing = inspect(c).get_table_names()
            if existing and "schema_info" not in existing:
                raise CorruptArchive("Nonempty database has no archive schema identity")
            schema_info.create(c, checkfirst=True)
            current = c.execute(select(schema_info.c.version).where(schema_info.c.id == 1)).scalar_one_or_none()
            if current is None:
                current = 0
            if current > CURRENT_SCHEMA or current < 0:
                raise CorruptArchive(f"Unsupported archive schema {current}")
            if current == 0:
                for table in (objects, grants, versions, references, revocations):
                    table.create(c, checkfirst=False)
                c.execute(insert(schema_info).values(id=1, version=1))
                current = 1
            if current == 1:
                navigation.create(c, checkfirst=False)
                self._rebuild_index(c)
                c.execute(update(schema_info).where(schema_info.c.id == 1).values(version=2))
            # Defend accidental bulk updates, not just the append API.
            for name in ("objects", "rights_grants", "versions", "version_references", "body_retention_revocations"):
                for action in ("UPDATE", "DELETE"):
                    c.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS immutable_{name}_{action.lower()} "
                        f"BEFORE {action} ON {name} BEGIN SELECT RAISE(ABORT, 'append-only record'); END")

    def schema_version(self) -> int:
        with self.engine.connect() as c:
            return c.execute(select(schema_info.c.version).where(schema_info.c.id == 1)).scalar_one()

    def _body_path(self, relative: str) -> Path:
        # DB metadata does not grant access to arbitrary host paths.
        p = self.root/relative
        if p.parent != self.bodies or p.is_symlink():
            raise CorruptArchive("Unsafe or redirected body path")
        if self.bodies.is_symlink():
            raise CorruptArchive("Body directory was redirected")
        return p

    def _write_body(self, relative: str, body: bytes) -> None:
        p = self._body_path(relative)
        descriptor = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            p.unlink(missing_ok=True)
            raise

    def append(self, submission: VersionSubmission, body: bytes | None = None) -> StoredVersion:
        if not isinstance(submission, VersionSubmission):
            raise TypeError("append requires a VersionSubmission contract")
        # model_construct/model_copy must not bypass the public input contract.
        sub = VersionSubmission.model_validate_json(submission.model_dump_json(warnings=False))
        if sub.representation is Representation.FULL_BODY:
            if type(body) is not bytes:
                raise ValueError("Full-body submission requires exact bytes")
        elif body is not None:
            raise PermissionDenied("A pointer/index cannot carry original body bytes")
        record = canonical(json.loads(sub.model_dump_json()))
        grant = canonical(json.loads(sub.rights.model_dump_json()))
        body_path = None
        created_file = False
        try:
            with self._write() as c:
                if c.execute(select(versions.c.version_id).where(versions.c.version_id == sub.version_id)).first():
                    raise Conflict("Version ID is already committed")
                obj = c.execute(select(objects).where(objects.c.object_id == sub.object_id)).mappings().first()
                if obj and obj["kind"] != sub.kind.value:
                    raise Conflict("Object identity cannot change kind")
                latest = c.execute(select(versions).where(versions.c.object_id == sub.object_id)
                                   .order_by(versions.c.ordinal.desc()).limit(1)).mappings().first()
                if sub.parent_version_id != (latest["version_id"] if latest else None):
                    raise Conflict("Parent is missing, foreign or no longer the current version")
                for ref in sub.references:
                    if not c.execute(select(versions.c.version_id).where(versions.c.version_id == ref.target_version_id)).first():
                        raise MissingVersion(ref.target_version_id)
                known_grant = c.execute(select(grants.c.record).where(grants.c.rights_id == sub.rights.rights_id)).scalar_one_or_none()
                if known_grant is not None and known_grant != grant:
                    raise Conflict("Rights ID cannot be redefined; record a new checked grant")
                revoked = c.execute(select(revocations.c.rights_id).where(revocations.c.rights_id == sub.rights.rights_id)).first()
                if body is not None and revoked:
                    raise PermissionDenied("Body retention grant was withdrawn")
                if not obj:
                    c.execute(insert(objects).values(object_id=sub.object_id, kind=sub.kind.value))
                if known_grant is None:
                    c.execute(insert(grants).values(rights_id=sub.rights.rights_id, record=grant))
                ordinal = latest["ordinal"] + 1 if latest else 1
                recorded_at = datetime.now(timezone.utc)
                if body is not None:
                    body_path = "bodies/" + hashlib.sha256(sub.version_id.encode()).hexdigest() + ".bin"
                    self._write_body(body_path, body)
                    created_file = True
                c.execute(insert(versions).values(version_id=sub.version_id, object_id=sub.object_id,
                    ordinal=ordinal, parent_version_id=sub.parent_version_id, rights_id=sub.rights.rights_id,
                    record=record, recorded_at=recorded_at.isoformat(), body_path=body_path,
                    body_sha256=hashlib.sha256(body).hexdigest() if body is not None else None,
                    body_bytes=len(body) if body is not None else None))
                for ref in sub.references:
                    c.execute(insert(references).values(version_id=sub.version_id,
                        target_version_id=ref.target_version_id, use=ref.use.value, locator=ref.locator))
                c.execute(insert(navigation).values(version_id=sub.version_id, object_id=sub.object_id,
                    kind=sub.kind.value, title=sub.title))
        except BaseException as exc:
            if created_file and body_path:
                self._body_path(body_path).unlink(missing_ok=True)
            if isinstance(exc, IntegrityError):
                raise Conflict("Database rejected a duplicate or inconsistent version") from exc
            raise
        return self.get(sub.version_id)

    @staticmethod
    def _row(c: Connection, version_id: str):
        row = c.execute(select(versions).where(versions.c.version_id == version_id)).mappings().first()
        if row is None:
            raise MissingVersion(version_id)
        return row

    def get(self, version_id: str) -> StoredVersion:
        with self.engine.connect() as c:
            row = self._row(c, version_id)
            sub = VersionSubmission.model_validate_json(row["record"])
            revoked = bool(c.execute(select(revocations.c.rights_id).where(revocations.c.rights_id == row["rights_id"])).first())
            return StoredVersion(submission=sub, ordinal=row["ordinal"],
                recorded_at=datetime.fromisoformat(row["recorded_at"]), body_sha256=row["body_sha256"],
                body_bytes=row["body_bytes"], body_retention_revoked=revoked)

    def read_body(self, version_id: str) -> bytes:
        # Serialize permission checks and reads with revocation within this API.
        with self._write() as c:
            row = self._row(c, version_id)
            sub = VersionSubmission.model_validate_json(row["record"])
            if c.execute(select(revocations.c.rights_id).where(revocations.c.rights_id == row["rights_id"])).first():
                raise PermissionDenied("Body retention was withdrawn")
            if not row["body_path"] or MaterialUse.STORE_BODY not in sub.rights.allowed_uses:
                raise BodyUnavailable("Pointer/index only; original body was not retained")
            p = self._body_path(row["body_path"])
            try:
                descriptor = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(descriptor, "rb") as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise CorruptArchive("Body is not a regular file")
                    body = stream.read()
            except FileNotFoundError as exc:
                raise BodyUnavailable("Retained original file is missing; index is not a substitute") from exc
            if len(body) != row["body_bytes"] or hashlib.sha256(body).hexdigest() != row["body_sha256"]:
                raise CorruptArchive("Original body does not match its committed identity")
            return body

    def referrers(self, target_version_id: str) -> list[dict]:
        with self.engine.connect() as c:
            self._row(c, target_version_id)
            return [dict(r) for r in c.execute(select(references).where(
                references.c.target_version_id == target_version_id).order_by(references.c.version_id)).mappings()]

    def _rebuild_index(self, c: Connection) -> int:
        rows = list(c.execute(select(versions.c.version_id, versions.c.record)).mappings())
        entries = []
        for row in rows:
            sub = VersionSubmission.model_validate_json(row["record"])
            if sub.version_id != row["version_id"]:
                raise CorruptArchive("Version record identity mismatch")
            entries.append(dict(version_id=sub.version_id, object_id=sub.object_id, kind=sub.kind.value, title=sub.title))
        c.execute(delete(navigation))
        if entries:
            c.execute(insert(navigation), entries)
        return len(entries)

    def rebuild_index(self) -> int:
        with self._write() as c:
            return self._rebuild_index(c)

    def find(self, title: str) -> list[dict]:
        """Navigation only. Body and authority always come from get/read_body."""
        with self.engine.connect() as c:
            return [dict(row) for row in c.execute(select(navigation).where(
                navigation.c.title.contains(title, autoescape=True)).order_by(navigation.c.version_id)).mappings()]

    def revoke_body_retention(self, rights_id: str, reason: str) -> RevocationResult:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Revocation needs a concrete reason")
        # Commit denial before deletion. A deletion failure must never re-enable access.
        with self._write() as c:
            if not c.execute(select(grants.c.rights_id).where(grants.c.rights_id == rights_id)).first():
                raise ArchiveError("Unknown rights ID")
            old = c.execute(select(revocations).where(revocations.c.rights_id == rights_id)).mappings().first()
            recorded_at = datetime.fromisoformat(old["recorded_at"]) if old else datetime.now(timezone.utc)
            if not old:
                c.execute(insert(revocations).values(rights_id=rights_id, reason=reason.strip(), recorded_at=recorded_at.isoformat()))
            rows = list(c.execute(select(versions.c.version_id, versions.c.body_path).where(versions.c.rights_id == rights_id)).mappings())
        purged, failed = [], []
        for row in rows:
            if row["body_path"]:
                try:
                    self._body_path(row["body_path"]).unlink(missing_ok=True)
                    purged.append(row["version_id"])
                except (OSError, ArchiveError):
                    failed.append(row["version_id"])
        return RevocationResult(rights_id=rights_id, affected_versions=tuple(r["version_id"] for r in rows),
            purged_versions=tuple(purged), failed_versions=tuple(failed), recorded_at=recorded_at)
