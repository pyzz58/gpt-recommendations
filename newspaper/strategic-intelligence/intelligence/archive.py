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

from .contracts import (MaterialUse, ObjectKind, PermissionState, ReferenceReadRequest, ReferenceUse,
                        ReferencedMaterial, Representation, RevocationResult, RightsGrant, Scope,
                        ScopeMode, StoredVersion, UseContext, UsePermission, ValidityMode,
                        VersionSubmission)

CURRENT_SCHEMA = 3
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
use_revocations = Table("rights_use_revocations", metadata,
    Column("rights_id", String, ForeignKey("rights_grants.rights_id"), primary_key=True),
    Column("use", String, primary_key=True),
    Column("reason", Text, nullable=False), Column("recorded_at", String, nullable=False))
navigation = Table("navigation_index", metadata,
    Column("version_id", String, ForeignKey("versions.version_id"), primary_key=True),
    Column("object_id", String, nullable=False), Column("kind", String, nullable=False),
    Column("title", Text, nullable=False))


class ArchiveError(Exception):
    """A known storage boundary failure; never a factual or content decision."""


class PrivatePathError(ArchiveError):
    """Private bytes cannot be written inside any Git worktree."""


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


def require_private_output_path(path: str | Path) -> Path:
    """Resolve a private output path and reject every enclosing Git worktree.

    A normal repository has a ``.git`` directory; linked worktrees and
    submodules use a ``.git`` file. Checking the real existing prefix also
    catches non-existent descendants and symlink aliases. A bare repository
    without a worktree marker is outside this worktree boundary.
    """
    requested = Path(path).expanduser().absolute()
    if os.path.lexists(requested) and requested.is_symlink():
        raise PrivatePathError(f"Private output cannot be an existing symlink: {requested}")
    resolved = requested.resolve(strict=False)
    cursor = resolved if resolved.is_dir() else resolved.parent
    for ancestor in (cursor, *cursor.parents):
        marker = ancestor/".git"
        if os.path.lexists(marker):
            raise PrivatePathError(
                f"Private output must be outside every Git worktree: {resolved}; "
                f"worktree marker: {marker}. Existing data was not modified; "
                "move it to an explicitly private location before retrying.")
    return resolved


def write_private_bytes(path: str | Path, data: bytes) -> Path:
    """Create one new private file atomically with mode 0600."""
    if type(data) is not bytes:
        raise TypeError("Private output requires exact bytes")
    target = require_private_output_path(path)
    created = False
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        created = True
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise
    return target


class Archive:
    """Local archive. Constructing an instance creates or migrates its schema.

    append(submission, body) -> StoredVersion; get(version_id) -> metadata;
    read_body(version_id) -> local retention recovery only;
    read_reference(request) -> bytes/metadata checked for the declared use;
    referrers/rebuild_index -> navigation.
    No method approves research, overwrites a version or changes a source time.
    """

    def __init__(self, root: str | Path):
        requested = require_private_output_path(root)
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
                current = 2
            if current == 2:
                use_revocations.create(c, checkfirst=True)
                c.execute(update(schema_info).where(schema_info.c.id == 1).values(version=3))
            # Defend accidental bulk updates, not just the append API.
            for name in ("objects", "rights_grants", "versions", "version_references",
                         "body_retention_revocations", "rights_use_revocations"):
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

    def append(self, submission: VersionSubmission, body: bytes | None = None,
               storage_context: UseContext | None = None,
               expected_current: dict[str, str | None] | None = None) -> StoredVersion:
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
                for expected_object_id, expected_version_id in (expected_current or {}).items():
                    row = c.execute(
                        select(versions.c.version_id)
                        .where(versions.c.object_id == expected_object_id)
                        .order_by(versions.c.ordinal.desc())
                        .limit(1)).scalar_one_or_none()
                    if row != expected_version_id:
                        raise Conflict(
                            f"Current version changed for {expected_object_id}: "
                            f"expected {expected_version_id}, found {row}")
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
                for coverage in sub.review_coverage:
                    for target_id in (
                            coverage.task_version_id, coverage.subject_version_id):
                        target = c.execute(
                            select(versions.c.object_id)
                            .where(versions.c.version_id == target_id)).first()
                        if target is None:
                            raise MissingVersion(target_id)
                    covered_task = c.execute(
                        select(objects.c.kind)
                        .select_from(versions.join(
                            objects, versions.c.object_id == objects.c.object_id))
                        .where(versions.c.version_id == coverage.task_version_id)).scalar_one()
                    if covered_task != ObjectKind.TASK.value:
                        raise ArchiveError("Review coverage task version is not a Task")
                known_grant = c.execute(select(grants.c.record).where(grants.c.rights_id == sub.rights.rights_id)).scalar_one_or_none()
                if known_grant is not None and known_grant != grant:
                    raise Conflict("Rights ID cannot be redefined; record a new checked grant")
                recorded_at = datetime.now(timezone.utc)
                if body is not None:
                    self._check_grant_use(
                        c, sub.rights, MaterialUse.STORE_BODY,
                        storage_context or UseContext(at=recorded_at),
                        legacy_local=False, require_full_content=True)
                globally_revoked = c.execute(select(revocations.c.rights_id).where(
                    revocations.c.rights_id == sub.rights.rights_id)).first()
                storage_revoked = c.execute(select(use_revocations.c.rights_id).where(
                    use_revocations.c.rights_id == sub.rights.rights_id,
                    use_revocations.c.use == MaterialUse.STORE_BODY.value)).first()
                if body is not None and (globally_revoked or storage_revoked):
                    raise PermissionDenied("Body retention grant was withdrawn")
                if not obj:
                    c.execute(insert(objects).values(object_id=sub.object_id, kind=sub.kind.value))
                if known_grant is None:
                    c.execute(insert(grants).values(rights_id=sub.rights.rights_id, record=grant))
                ordinal = latest["ordinal"] + 1 if latest else 1
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
            return self._stored(c, self._row(c, version_id))

    def latest(self, object_id: str) -> StoredVersion | None:
        """Return the latest committed version of one stable object ID."""
        with self.engine.connect() as c:
            row = c.execute(select(versions).where(versions.c.object_id == object_id)
                            .order_by(versions.c.ordinal.desc()).limit(1)).mappings().first()
            return self._stored(c, row) if row is not None else None

    def history(self, object_id: str) -> tuple[StoredVersion, ...]:
        """Return immutable committed versions in append order."""
        with self.engine.connect() as c:
            rows = c.execute(select(versions).where(versions.c.object_id == object_id)
                             .order_by(versions.c.ordinal)).mappings().all()
            return tuple(self._stored(c, row) for row in rows)

    @staticmethod
    def _stored(c: Connection, row) -> StoredVersion:
        sub = VersionSubmission.model_validate_json(row["record"])
        if (sub.version_id, sub.object_id, sub.parent_version_id, sub.rights.rights_id) != (
                row["version_id"], row["object_id"], row["parent_version_id"], row["rights_id"]):
            raise CorruptArchive("Version record identity mismatch")
        revoked = bool(c.execute(select(revocations.c.rights_id).where(
            revocations.c.rights_id == row["rights_id"])).first())
        revoked = revoked or bool(c.execute(select(use_revocations.c.rights_id).where(
            use_revocations.c.rights_id == row["rights_id"],
            use_revocations.c.use == MaterialUse.STORE_BODY.value)).first())
        return StoredVersion(submission=sub, ordinal=row["ordinal"],
            recorded_at=datetime.fromisoformat(row["recorded_at"]), body_sha256=row["body_sha256"],
            body_bytes=row["body_bytes"], body_retention_revoked=revoked)

    def read_body(self, version_id: str) -> bytes:
        """Recover retained bytes locally; does not authorize another purpose.

        Model processing, translation and delivery consumers use read_reference.
        This local Python API is not a host-file or outbound-network sandbox.
        """
        # Serialize permission checks and reads with revocation within this API.
        with self._write() as c:
            row = self._row(c, version_id)
            stored = self._stored(c, row)
            self._check_use(c, stored, MaterialUse.STORE_BODY, None)
            return self._read_body(row, stored)

    def check_version_use(self, version_id: str, intended_use: MaterialUse,
                          context: UseContext) -> tuple[str, ...]:
        """Check one exact committed version without returning its bytes."""
        if not isinstance(intended_use, MaterialUse):
            raise TypeError("check_version_use requires a MaterialUse")
        if not isinstance(context, UseContext):
            raise TypeError("check_version_use requires a UseContext")
        checked_context = UseContext.model_validate_json(
            context.model_dump_json(warnings=False))
        with self._write() as c:
            stored = self._stored(c, self._row(c, version_id))
            attribution = self._check_use(c, stored, intended_use, checked_context)
            if intended_use is not MaterialUse.INDEX:
                self._check_use(
                    c, stored, MaterialUse.STORE_BODY,
                    UseContext(at=checked_context.at))
                permission = self._permission(stored.submission.rights, intended_use)
                if permission is not None and self._requires_selection(permission):
                    raise PermissionDenied(
                        "A partial-content permission requires an exact MaterialSelection input")
            return attribution

    def _read_body(self, row, stored: StoredVersion) -> bytes:
        # Shared by local recovery and purpose-aware reads, under the same lock.
        if stored.body_retention_revoked:
            raise PermissionDenied("Body retention was withdrawn")
        if not row["body_path"] or MaterialUse.STORE_BODY not in stored.submission.rights.allowed_uses:
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

    @staticmethod
    def _permission(grant: RightsGrant, use: MaterialUse) -> UsePermission | None:
        return next((item for item in grant.permissions if item.use is use), None)

    @staticmethod
    def _scope_has(scope: Scope, value: str | None, label: str) -> None:
        if scope.mode is ScopeMode.ANY:
            return
        if scope.mode is ScopeMode.UNKNOWN:
            raise PermissionDenied(f"{label} scope is unknown: {scope.reason}")
        if not value or value.casefold() not in {item.casefold() for item in scope.values}:
            raise PermissionDenied(f"{label} is not covered by the recorded permission")

    def _revoked_uses(self, c: Connection, rights_id: str) -> set[MaterialUse]:
        return {MaterialUse(row["use"]) for row in c.execute(
            select(use_revocations).where(use_revocations.c.rights_id == rights_id)).mappings()}

    @staticmethod
    def _requires_selection(item: UsePermission) -> bool:
        return item.content_scope.mode is not ScopeMode.ANY or bool(item.excluded_content)

    def _check_grant_use(self, c: Connection, grant: RightsGrant, use: MaterialUse,
                         context: UseContext | None, *, legacy_local: bool = False,
                         require_full_content: bool = False) -> tuple[str, ...]:
        if use is MaterialUse.INDEX:
            return ()
        if use not in grant.allowed_uses:
            raise PermissionDenied(f"Recorded grant does not allow {use.value}")
        if use in self._revoked_uses(c, grant.rights_id):
            raise PermissionDenied(f"Recorded permission for {use.value} was withdrawn")
        item = self._permission(grant, use)
        if item is None:
            # Legacy local recovery remains available for the coarse local uses
            # already recorded. Missing structured fields never authorize a new
            # model, translation or delivery use.
            if use is MaterialUse.STORE_BODY and legacy_local:
                return ()
            raise PermissionDenied(f"No structured permission was recorded for {use.value}")
        if item.state is PermissionState.UNKNOWN:
            raise PermissionDenied(f"Permission for {use.value} is unresolved")
        if item.state is PermissionState.DENIED:
            raise PermissionDenied(f"Permission for {use.value} is explicitly denied")
        if item.validity is ValidityMode.UNKNOWN:
            raise PermissionDenied(f"Validity for {use.value} is unknown")
        at = context.at if context else datetime.now(timezone.utc)
        if item.validity is ValidityMode.BOUNDED:
            if item.effective_from is not None and at < item.effective_from:
                raise PermissionDenied(f"Permission for {use.value} is not yet effective")
            if item.effective_until is not None and at >= item.effective_until:
                raise PermissionDenied(f"Permission for {use.value} has expired")
        self._scope_has(item.territories, context.territory if context else None, "Territory")
        self._scope_has(item.providers, context.provider if context else None, "Provider")
        if item.content_scope.mode is ScopeMode.UNKNOWN:
            raise PermissionDenied(f"Content scope is unknown: {item.content_scope.reason}")
        if require_full_content and self._requires_selection(item):
            raise PermissionDenied("A partial-content permission cannot authorize this full body")
        if item.content_scope.mode is ScopeMode.LIST:
            if not context or not context.content:
                raise PermissionDenied("Content coverage requires the selected content labels")
            allowed_content = {value.casefold() for value in item.content_scope.values}
            if any(value.casefold() not in allowed_content for value in context.content):
                raise PermissionDenied("Selected content is not covered by the recorded permission")
        if item.excluded_content:
            if not context or not context.content:
                raise PermissionDenied("Excluded third-party content requires an explicit selection")
            excluded = {value.casefold() for value in item.excluded_content}
            if any(value.casefold() in excluded for value in context.content):
                raise PermissionDenied("Selected third-party content is excluded from the permission")
        if item.conditions and item.conditions_satisfied is not True:
            raise PermissionDenied("Permission conditions were not confirmed as satisfied")
        return item.attribution_requirements

    def _check_use(self, c: Connection, stored: StoredVersion, use: MaterialUse,
                   context: UseContext | None) -> tuple[str, ...]:
        """Check recorded rights for one concrete use, never content truth."""
        return self._check_grant_use(
            c, stored.submission.rights, use, context,
            legacy_local=(stored.submission.schema_version == 1 and use is MaterialUse.STORE_BODY),
            require_full_content=(use is MaterialUse.STORE_BODY))

    def read_reference(self, request: ReferenceReadRequest) -> ReferencedMaterial:
        """Resolve an owner's recorded reference without changing version/use.

        A retained body is not a grant to process, translate or deliver it.
        INDEX returns metadata, including withdrawal status, without reading a
        body. A receipt records retrieval only, not semantic adoption or approval.
        """
        if not isinstance(request, ReferenceReadRequest):
            raise TypeError("read_reference requires a ReferenceReadRequest contract")
        req = ReferenceReadRequest.model_validate_json(request.model_dump_json(warnings=False))
        with self._write() as c:
            owner = self._stored(c, self._row(c, req.owner_version_id))
            if req.reference not in owner.submission.references:
                raise Conflict("Requested reference is not committed by the owner version")
            row = self._row(c, req.reference.target_version_id)
            target = self._stored(c, row)
            if target.submission.kind is not req.expected_kind:
                raise Conflict("Referenced version has a different object kind")
            if req.expected_body_sha256 is not None and req.expected_body_sha256 != target.body_sha256:
                raise Conflict("Referenced body has a different committed identity")
            body = None
            attribution = ()
            selected = None
            if req.intended_use is not MaterialUse.INDEX:
                attribution = self._check_use(c, target, req.intended_use, req.use_context)
                # A model/translation/delivery read also depends on current
                # permission to retain the exact body it will receive.
                storage_at = req.use_context.at if req.use_context else datetime.now(timezone.utc)
                self._check_use(c, target, MaterialUse.STORE_BODY, UseContext(at=storage_at))
                permission = self._permission(target.submission.rights, req.intended_use)
                needs_selection = permission is not None and self._requires_selection(permission)
                selected_id = req.use_context.selected_version_id if req.use_context else None
                if needs_selection or selected_id is not None:
                    if not selected_id:
                        raise PermissionDenied("Partial content permission requires an approved selected-version ID")
                    selected_row = self._row(c, selected_id)
                    selected = self._stored(c, selected_row)
                    if selected.submission.kind is not ObjectKind.MATERIAL_SELECTION:
                        raise PermissionDenied("Selected content is not an approved material-selection version")
                    if selected.submission.representation is not Representation.FULL_BODY:
                        raise PermissionDenied("Selected material has no retained body")
                    if selected.submission.version_id == target.submission.version_id:
                        raise PermissionDenied("Selected content cannot be the same full-body version")
                    if not any(ref.target_version_id == target.submission.version_id
                               and ref.use in (ReferenceUse.SUPPORT, ReferenceUse.BASIS)
                               for ref in selected.submission.references):
                        raise PermissionDenied("Selected material does not reference its original version")
                    selected_attribution = self._check_use(
                        c, selected, req.intended_use, req.use_context)
                    attribution = tuple(dict.fromkeys((*attribution, *selected_attribution)))
                    selected_permission = self._permission(
                        selected.submission.rights, req.intended_use)
                    if selected_permission is None or self._requires_selection(selected_permission):
                        raise PermissionDenied("Selected material's own permission still requires narrowing")
                    self._check_use(c, selected, MaterialUse.STORE_BODY, UseContext(at=storage_at))
                    if (req.expected_selected_body_sha256 is not None
                            and req.expected_selected_body_sha256 != selected.body_sha256):
                        raise Conflict("Selected body has a different committed identity")
                    if selected.body_sha256 == target.body_sha256:
                        raise PermissionDenied("Selected content is byte-identical to the excluded full body")
                    body = self._read_body(selected_row, selected)
                else:
                    body = self._read_body(row, target)
            return ReferencedMaterial(request=req, owner=owner, version=target,
                selected_version=selected, recorded_at=datetime.now(timezone.utc), body=body,
                required_attribution=attribution)

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
            grant_record = c.execute(select(grants.c.record).where(
                grants.c.rights_id == rights_id)).scalar_one_or_none()
            if grant_record is None:
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
        revoked_uses = tuple(sorted(RightsGrant.model_validate_json(grant_record).allowed_uses, key=lambda item: item.value))
        return RevocationResult(rights_id=rights_id, revoked_uses=revoked_uses,
            affected_versions=tuple(r["version_id"] for r in rows),
            purged_versions=tuple(purged), failed_versions=tuple(failed), recorded_at=recorded_at)

    def revoke_rights(self, rights_id: str, uses: tuple[MaterialUse, ...],
                      reason: str) -> RevocationResult:
        """Withdraw selected uses while preserving unrelated uses and history.

        INDEX is retained as the minimum audit/navigation pointer. STORE_BODY
        revocation also removes retained bodies because no later use can then
        recover them. Other use revocations leave the stored body untouched.
        """
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Revocation needs a concrete reason")
        selected = tuple(dict.fromkeys(uses))
        if not selected:
            raise ValueError("Select at least one use to revoke")
        if MaterialUse.INDEX in selected:
            raise ValueError("The minimal index/pointer record cannot be partially revoked")
        with self._write() as c:
            grant_record = c.execute(select(grants.c.record).where(
                grants.c.rights_id == rights_id)).scalar_one_or_none()
            if grant_record is None:
                raise ArchiveError("Unknown rights ID")
            grant = RightsGrant.model_validate_json(grant_record)
            if any(use not in grant.allowed_uses for use in selected):
                raise ArchiveError("Cannot revoke a use that the grant did not authorize")
            now = datetime.now(timezone.utc)
            existing = {MaterialUse(row["use"]): datetime.fromisoformat(row["recorded_at"])
                        for row in c.execute(select(use_revocations).where(
                            use_revocations.c.rights_id == rights_id)).mappings()}
            for use in selected:
                if use not in existing:
                    c.execute(insert(use_revocations).values(
                        rights_id=rights_id, use=use.value, reason=reason.strip(),
                        recorded_at=now.isoformat()))
                    existing[use] = now
            rows = list(c.execute(select(versions.c.version_id, versions.c.body_path).where(
                versions.c.rights_id == rights_id)).mappings())
        purged, failed = [], []
        if MaterialUse.STORE_BODY in selected:
            for row in rows:
                if row["body_path"]:
                    try:
                        self._body_path(row["body_path"]).unlink(missing_ok=True)
                        purged.append(row["version_id"])
                    except (OSError, ArchiveError):
                        failed.append(row["version_id"])
        return RevocationResult(rights_id=rights_id, revoked_uses=selected,
            affected_versions=tuple(row["version_id"] for row in rows),
            purged_versions=tuple(purged), failed_versions=tuple(failed),
            recorded_at=max(existing[use] for use in selected))
