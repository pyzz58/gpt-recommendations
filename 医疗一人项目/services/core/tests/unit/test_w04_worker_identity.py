from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from medical_one_person.agents.runner import _run_key


def test_run_key_uses_semantic_execution_identity_not_lifecycle_revision() -> None:
    task = SimpleNamespace(
        project_id=uuid4(),
        id=uuid4(),
        input_version="v1",
        input_snapshot_sha256="a" * 64,
        revision=3,
        review_id=None,
        purpose="same-semantic-execution",
    )
    role = SimpleNamespace(role_id="A04", version=1)
    first = _run_key(task, role)
    task.revision = 7
    assert _run_key(task, role) == first

    task.input_snapshot_sha256 = "b" * 64
    changed_input = _run_key(task, role)
    assert changed_input != first

    task.input_snapshot_sha256 = "a" * 64
    task.review_id = uuid4()
    changed_review = _run_key(task, role)
    assert changed_review != first
