"""Human-readable and JSON reports."""

from __future__ import annotations

import json

from .grader import GradeResult
from .stress import StressReport


def grade_text(g: GradeResult) -> str:
    lines = [f"Solution: {g.solution}"]
    for r in g.results:
        mark = "PASS" if r.passed else "FAIL"
        tag = "required" if r.required else "optional"
        lines.append(f"  [{mark}] {r.id} ({tag})")
        if not r.passed and r.detail:
            lines += [f"         {line}" for line in r.detail.splitlines()[-8:]]
    lines.append(f"Result: {'PASS' if g.passed else 'FAIL'}")
    return "\n".join(lines)


def grade_dict(g: GradeResult) -> dict:
    return {
        "solution": g.solution,
        "passed": g.passed,
        "criteria": [
            {"id": r.id, "required": r.required, "passed": r.passed, "detail": r.detail}
            for r in g.results
        ],
    }


def stress_text(rep: StressReport) -> str:
    rows = [("ROLE", "SOLUTION", "EXPECT", "GOT", "VERDICT", "CAUGHT BY")]
    for c in rep.cases:
        rows.append(
            (
                c.role,
                c.name,
                "pass" if c.expect_pass else "fail",
                "pass" if c.grade.passed else "fail",
                "ok" if c.ok else "HOLE" if c.role == "adversarial" else "BROKEN",
                ", ".join(c.grade.failed_required) if not c.expect_pass else "",
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = [f"Stress test: {rep.task}"]
    lines += [
        "  " + "  ".join(v.ljust(w) for v, w in zip(r, widths, strict=True)).rstrip() for r in rows
    ]

    for c in rep.cases:
        if c.ok:
            continue
        if c.role == "adversarial":
            lines.append(f"GRADER HOLE: '{c.name}' passed every required criterion. {c.why}")
        else:
            failed = ", ".join(c.grade.failed_required)
            lines.append(f"BROKEN: correct solution '{c.name}' was rejected by: {failed}")
    lines += [f"PROBLEM: {p}" for p in rep.problems]

    good = sum(c.ok for c in rep.cases)
    verdict = "robust" if rep.robust else "NOT robust"
    lines.append(f"Grader is {verdict}: {good}/{len(rep.cases)} cases behaved as expected.")
    return "\n".join(lines)


def stress_dict(rep: StressReport) -> dict:
    return {
        "task": rep.task,
        "robust": rep.robust,
        "problems": rep.problems,
        "cases": [
            {
                "role": c.role,
                "solution": c.name,
                "expect_pass": c.expect_pass,
                "ok": c.ok,
                "why": c.why,
                "grade": grade_dict(c.grade),
            }
            for c in rep.cases
        ],
    }


def to_json(data: dict) -> str:
    return json.dumps(data, indent=2)
