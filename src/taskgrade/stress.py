"""Stress-test a grader: correct solutions must pass, adversarial ones must fail."""

from __future__ import annotations

from dataclasses import dataclass, field

from .grader import GradeResult, grade
from .runners import Runner
from .spec import TaskSpec


@dataclass
class StressCase:
    role: str  # reference | alternate | adversarial
    name: str
    expect_pass: bool
    grade: GradeResult
    why: str = ""

    @property
    def ok(self) -> bool:
        return self.grade.passed == self.expect_pass


@dataclass
class StressReport:
    task: str
    cases: list[StressCase] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def robust(self) -> bool:
        return not self.problems and all(c.ok for c in self.cases)


def stress(spec: TaskSpec, runner: Runner) -> StressReport:
    report = StressReport(task=spec.name)
    if spec.reference is None:
        report.problems.append("no reference solution: cannot show the task is solvable")
    if not spec.adversarial:
        report.problems.append("no adversarial solutions: nothing shows bad work is rejected")

    runner.prepare()
    plan = []
    if spec.reference is not None:
        plan.append(("reference", spec.reference, True, ""))
    plan += [("alternate", p, True, "") for p in spec.alternates]
    plan += [("adversarial", a.path, False, a.why) for a in spec.adversarial]

    for role, path, expect, why in plan:
        result = grade(spec, path, runner)
        report.cases.append(StressCase(role, path.name, expect, result, why))
    return report
