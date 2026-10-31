from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


class UnsafeWorkspacePathError(ValueError):
    pass


@dataclass(frozen=True)
class RunWorkspace:
    project_id: UUID
    task_id: UUID
    attempt_id: UUID
    root: Path
    input_dir: Path
    output_dir: Path
    temporary_dir: Path

    def read_input(self, relative_path: str | Path) -> bytes:
        path = _safe_child(self.input_dir, relative_path)
        resolved = path.resolve()
        if not resolved.is_relative_to(self.input_dir.resolve()):
            raise UnsafeWorkspacePathError("Input path escapes through a symbolic link")
        if not resolved.is_file():
            raise FileNotFoundError("Input file not found")
        return resolved.read_bytes()

    def write_output(
        self, relative_path: str | Path, content: bytes, *, max_bytes: int = 20 * 1024 * 1024
    ) -> Path:
        if len(content) > max_bytes:
            raise ValueError("Output exceeds the work-package size limit")
        path = _safe_child(self.output_dir, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.parent.resolve().is_relative_to(self.output_dir.resolve()):
            raise UnsafeWorkspacePathError("Output path escapes through a symbolic link")
        with path.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return path


class RunWorkspaceManager:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def prepare(
        self,
        project_id: UUID,
        task_id: UUID,
        attempt_id: UUID,
        *,
        input_files: Mapping[str, bytes] | None = None,
    ) -> RunWorkspace:
        root = self._root / str(project_id) / str(task_id) / str(attempt_id)
        input_dir = root / "input"
        output_dir = root / "output"
        temporary_dir = root / "tmp"
        for directory in (input_dir, output_dir, temporary_dir):
            directory.mkdir(parents=True, exist_ok=True)
        for relative_path, content in (input_files or {}).items():
            target = _safe_child(input_dir, relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        input_dir.chmod(0o555)
        output_dir.chmod(0o750)
        temporary_dir.chmod(0o700)
        return RunWorkspace(
            project_id=project_id,
            task_id=task_id,
            attempt_id=attempt_id,
            root=root,
            input_dir=input_dir,
            output_dir=output_dir,
            temporary_dir=temporary_dir,
        )


def _safe_child(parent: Path, relative_path: str | Path) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or not relative.parts:
        raise UnsafeWorkspacePathError("Workspace paths must be relative")
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise UnsafeWorkspacePathError("Workspace path contains an unsafe segment")
    candidate = parent.joinpath(relative)
    if not candidate.resolve().is_relative_to(parent.resolve()):
        raise UnsafeWorkspacePathError("Workspace path escapes its assigned directory")
    return candidate
