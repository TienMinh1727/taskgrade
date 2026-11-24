from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "parse-duration"


@pytest.fixture
def example_task() -> Path:
    return EXAMPLE / "task.toml"


@pytest.fixture
def example_copy(tmp_path: Path) -> Path:
    """A writable copy of the example task, for tests that edit the spec."""
    dest = tmp_path / "parse-duration"
    shutil.copytree(EXAMPLE, dest)
    return dest


@pytest.fixture
def tiny_task(tmp_path: Path):
    """Factory for a minimal task: repo/app.py + a solution overlay."""

    def make(criteria: str, solution: dict[str, str] | None = None) -> tuple[Path, Path]:
        root = tmp_path / "task"
        (root / "repo").mkdir(parents=True)
        (root / "repo" / "app.py").write_text("VALUE = 0\n")
        sol = root / "sol"
        sol.mkdir()
        for name, body in (solution or {"app.py": "VALUE = 1\n"}).items():
            (sol / name).parent.mkdir(parents=True, exist_ok=True)
            (sol / name).write_text(body)
        spec = textwrap.dedent(
            """
            [task]
            name = "tiny"
            repo = "repo"
            """
        )
        (root / "task.toml").write_text(spec + textwrap.dedent(criteria))
        return root / "task.toml", sol

    return make


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0
