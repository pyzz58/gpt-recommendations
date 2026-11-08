from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

from medical_one_person.domain.artifacts import StoredObject

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class LocalArtifactStore:
    """Content-addressed immutable byte storage beneath one explicit root."""

    def __init__(self, root: Path, *, max_bytes: int = 100 * 1024 * 1024) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._max_bytes = max_bytes

    def put(self, content: bytes) -> StoredObject:
        if len(content) > self._max_bytes:
            raise ValueError("Artifact exceeds the configured size limit")
        digest = hashlib.sha256(content).hexdigest()
        object_key = f"sha256/{digest[:2]}/{digest[2:4]}/{digest}"
        target = self._safe_path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError("Existing content-addressed object failed verification")
            return StoredObject(object_key=object_key, sha256=digest, size_bytes=len(content))

        temporary_directory = self._root / ".tmp"
        temporary_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=temporary_directory, delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
        return StoredObject(object_key=object_key, sha256=digest, size_bytes=len(content))

    def put_path(self, source: Path) -> StoredObject:
        size = source.stat().st_size
        if size > self._max_bytes:
            raise ValueError("Artifact exceeds the configured size limit")
        digest_handle = hashlib.sha256()
        with source.open("rb") as source_handle:
            for block in iter(lambda: source_handle.read(1024 * 1024), b""):
                digest_handle.update(block)
        digest = digest_handle.hexdigest()
        object_key = f"sha256/{digest[:2]}/{digest[2:4]}/{digest}"
        target = self._safe_path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.stat().st_size != size or not _file_sha256(target) == digest:
                raise ValueError("Existing content-addressed object failed verification")
            return StoredObject(object_key=object_key, sha256=digest, size_bytes=size)

        temporary_directory = self._root / ".tmp"
        temporary_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=temporary_directory, delete=False) as handle:
            temporary_path = Path(handle.name)
            with source.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, handle, length=1024 * 1024)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            if _file_sha256(temporary_path) != digest:
                raise ValueError("Staged artifact changed while being persisted")
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
        return StoredObject(object_key=object_key, sha256=digest, size_bytes=size)

    def read(self, object_key: str, expected_sha256: str) -> bytes:
        if not _SHA256_PATTERN.fullmatch(expected_sha256):
            raise ValueError("Invalid expected SHA-256")
        path = self._safe_path(object_key)
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            raise ValueError("Artifact hash verification failed")
        return content

    def _safe_path(self, object_key: str) -> Path:
        candidate = (self._root / object_key).resolve()
        if not candidate.is_relative_to(self._root):
            raise ValueError("Artifact object key escapes the configured root")
        return candidate

    def trusted_path(self, object_key: str) -> Path:
        """Return a path only to trusted parser processes, never through HTTP."""

        path = self._safe_path(object_key)
        if not path.is_file():
            raise FileNotFoundError("Artifact object not found")
        return path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
