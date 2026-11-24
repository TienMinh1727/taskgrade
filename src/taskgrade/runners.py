"""Where grading commands run: locally (trusted code only) or in an offline container."""

from __future__ import annotations

import hashlib
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .spec import TaskSpec

_ENV = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}


@dataclass(frozen=True)
class CmdResult:
    exit_code: int
    output: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class Runner(Protocol):
    def prepare(self) -> None: ...
    def run(self, workspace: Path, cmd: str, timeout: int) -> CmdResult: ...


class LocalRunner:
    """Runs commands on the host. Only for trusted solutions (tests, authoring)."""

    def prepare(self) -> None:
        return None

    def run(self, workspace: Path, cmd: str, timeout: int) -> CmdResult:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=workspace,
                env={**os.environ, **_ENV},
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return CmdResult(-1, _text(exc.stdout) + _text(exc.stderr), timed_out=True)
        return CmdResult(proc.returncode, proc.stdout + proc.stderr)


class DockerRunner:
    """Bakes the environment into an image once, then runs every command with no network."""

    def __init__(self, spec: TaskSpec, docker: str = "docker") -> None:
        self.spec = spec
        self.docker = docker
        digest = hashlib.sha256("\n".join((spec.image, *spec.setup)).encode()).hexdigest()
        self.tag = f"taskgrade/{_slug(spec.name)}:{digest[:12]}"

    def dockerfile(self) -> str:
        lines = [f"FROM {self.spec.image}", "WORKDIR /work"]
        lines += [f"RUN {cmd}" for cmd in self.spec.setup]
        return "\n".join(lines) + "\n"

    def prepare(self) -> None:
        # Dependencies are fetched here, at build time; grading itself never touches the network.
        proc = subprocess.run(
            [self.docker, "build", "-q", "-t", self.tag, "-"],
            input=self.dockerfile(),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"docker build failed:\n{proc.stderr.strip()}")

    def command(self, workspace: Path, cmd: str, name: str) -> list[str]:
        env = [arg for k, v in _ENV.items() for arg in ("-e", f"{k}={v}")]
        return [
            self.docker, "run", "--rm", "--name", name,
            "--network", "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "256",
            "--memory", "1g",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-e", "HOME=/tmp", *env,
            "-v", f"{workspace.resolve()}:/work",
            "-w", "/work",
            self.tag, "sh", "-c", cmd,
        ]  # fmt: skip

    def run(self, workspace: Path, cmd: str, timeout: int) -> CmdResult:
        name = f"taskgrade-{uuid.uuid4().hex[:12]}"
        try:
            proc = subprocess.run(
                self.command(workspace, cmd, name),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            subprocess.run([self.docker, "kill", name], capture_output=True)
            return CmdResult(-1, _text(exc.stdout) + _text(exc.stderr), timed_out=True)
        return CmdResult(proc.returncode, proc.stdout + proc.stderr)


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "-" for c in name.lower()) or "task"


def _text(data: bytes | str | None) -> str:
    if data is None:
        return ""
    return data.decode(errors="replace") if isinstance(data, bytes) else data
