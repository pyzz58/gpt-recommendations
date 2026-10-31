from __future__ import annotations

import os
from uuid import uuid4

import pytest

from medical_one_person.infrastructure.run_workspace import (
    RunWorkspaceManager,
    UnsafeWorkspacePathError,
)


def test_run_workspace_isolates_inputs_outputs_and_rejects_escape(tmp_path) -> None:
    manager = RunWorkspaceManager(tmp_path / "runs")
    workspace = manager.prepare(
        uuid4(),
        uuid4(),
        uuid4(),
        input_files={"source.txt": b"synthetic source"},
    )
    workspace.write_output("analysis/result.txt", b"synthetic result")

    assert workspace.read_input("source.txt") == b"synthetic source"
    assert (workspace.output_dir / "analysis/result.txt").read_bytes() == b"synthetic result"
    assert os.stat(workspace.input_dir).st_mode & 0o222 == 0

    for unsafe in ("../escape.txt", "/tmp/escape.txt", "analysis/../../escape.txt"):
        with pytest.raises(UnsafeWorkspacePathError):
            workspace.write_output(unsafe, b"blocked")

    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside")
    workspace.input_dir.chmod(0o755)
    (workspace.input_dir / "escape-link").symlink_to(outside)
    workspace.input_dir.chmod(0o555)
    with pytest.raises(UnsafeWorkspacePathError):
        workspace.read_input("escape-link")

    (workspace.output_dir / "escape-dir").symlink_to(tmp_path)
    with pytest.raises(UnsafeWorkspacePathError):
        workspace.write_output("escape-dir/blocked.txt", b"blocked")
