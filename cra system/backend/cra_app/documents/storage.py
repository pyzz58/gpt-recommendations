"""Private object storage adapters; no public or permanent URLs are issued."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from cra_app.shared.config import Settings


class PrivateObjectStorage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None: ...

    def read(self, key: str) -> bytes: ...


class LocalPrivateStorage:
    """Development adapter that keeps files outside the public web root."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("storage key escapes private storage root")
        return candidate

    def put(self, key: str, content: bytes, content_type: str) -> None:
        destination = self._path(key)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class S3PrivateStorage:
    """Thin boto3 adapter. The enclosing API enforces CRA scope before reads."""

    def __init__(self, settings: Settings):
        if not settings.private_storage_endpoint:
            raise ValueError("CRA_PRIVATE_STORAGE_ENDPOINT is required for S3")
        if not settings.private_storage_access_key:
            raise ValueError("S3 access key is required")
        if not settings.private_storage_secret_key:
            raise ValueError("S3 secret key is required")
        self.bucket = settings.private_storage_bucket
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=settings.private_storage_endpoint,
            aws_access_key_id=settings.private_storage_access_key,
            aws_secret_access_key=(
                settings.private_storage_secret_key.get_secret_value()
            ),
            region_name=settings.private_storage_region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, content: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata={"cra-private": "true"},
        )

    def read(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()


def build_private_storage(settings: Settings) -> PrivateObjectStorage:
    if settings.private_storage_backend == "s3":
        storage = S3PrivateStorage(settings)
        storage.ensure_bucket()
        return storage
    return LocalPrivateStorage(
        Path(settings.private_storage_local_path).expanduser()
    )
