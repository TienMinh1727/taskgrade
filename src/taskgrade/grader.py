"""Grade one solution against every criterion of a task."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from .runners import Runner
from .spec import Criterion, TaskSpec
from .workspace import build_workspace

_TAIL = 1500


@dataclass(frozen=True)
class CriterionResult:
    id: str
    required: bool
    passed: bool
    detail: str = ""


@dataclass
class GradeResult:
    solution: str
    results: list[CriterionResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results if r.required)

    @property
    def failed_required(self) -> list[str]:
        return [r.id for r in self.results if r.required and not r.passed]


def _matches(rel: str, globs: tuple[str, ...]) -> bool:
    return any(fnmatch(rel, g) for g in globs)


def _check_forbid(c: Criterion, ws: Path) -> CriterionResult:
    rx = re.compile(c.pattern or "")
    hits = []
    for f in sorted(p for p in ws.rglob("*") if p.is_file()):
        rel = f.relative_to(ws).as_posix()
        if not _matches(rel, c.paths):
            continue
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if rx.search(line):
                hits.append(f"{rel}:{n}: {line.strip()}")
    return CriterionResult(c.id, c.required, not hits, "\n".join(hits[:10]))


def _check_only_modifies(c: Criterion, changed: list[str]) -> CriterionResult:
    extra = [f for f in changed if not _matches(f, c.paths)]
    detail = "touched files outside the allowed set: " + ", ".join(extra) if extra else ""
    return CriterionResult(c.id, c.required, not extra, detail)


def _check_run(c: Criterion, ws: Path, runner: Runner, timeout: int) -> CriterionResult:
    res = runner.run(ws, c.run or "", timeout)
    if res.timed_out:
        detail = f"timed out after {timeout}s"
    else:
        detail = f"exit {res.exit_code}\n{res.output[-_TAIL:]}".rstrip()
    return CriterionResult(c.id, c.required, res.ok, detail)


def grade(spec: TaskSpec, solution: Path, runner: Runner, label: str | None = None) -> GradeResult:
    result = GradeResult(solution=label or solution.name)
    with tempfile.TemporaryDirectory(prefix="taskgrade-") as tmp:
        ws = Path(tmp) / "work"
        changed = build_workspace(spec, solution, ws)
        for c in spec.criteria:
            if c.kind == "forbid":
                r = _check_forbid(c, ws)
            elif c.kind == "only_modifies":
                r = _check_only_modifies(c, changed)
            else:
                r = _check_run(c, ws, runner, spec.timeout)
            result.results.append(r)
    return result
