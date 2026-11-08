from __future__ import annotations

from dataclasses import dataclass
from shutil import which

from medical_one_person.domain.skills import ResourceLimits
from medical_one_person.infrastructure.run_workspace import RunWorkspace


class ContainerUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ContainerSandboxPolicy:
    image_digest: str
    limits: ResourceLimits

    def command(
        self,
        *,
        workspace: RunWorkspace,
        argv: tuple[str, ...],
    ) -> list[str]:
        if not self.image_digest.startswith("sha256:") or len(self.image_digest) != 71:
            raise ValueError("Container image must be pinned by sha256 digest")
        if not argv:
            raise ValueError("Container command cannot be empty")
        return [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "10001:10001",
            "--pids-limit",
            str(self.limits.max_processes),
            "--memory",
            f"{self.limits.memory_mb}m",
            "--cpus",
            str(self.limits.cpu_count),
            "--mount",
            f"type=bind,src={workspace.input_dir},dst=/workspace/input,readonly",
            "--mount",
            f"type=bind,src={workspace.output_dir},dst=/workspace/output",
            "--mount",
            f"type=bind,src={workspace.temporary_dir},dst=/workspace/tmp",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            self.image_digest,
            *argv,
        ]


def require_container_runtime() -> str:
    runtime = which("docker")
    if runtime is None:
        raise ContainerUnavailableError(
            "Container runtime is unavailable; container skills cannot execute"
        )
    return runtime
