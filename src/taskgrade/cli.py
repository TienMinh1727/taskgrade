"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .grader import grade
from .report import grade_dict, grade_text, stress_dict, stress_text, to_json
from .runners import DockerRunner, LocalRunner, Runner
from .spec import SpecError, TaskSpec, load_spec
from .stress import stress
from .workspace import WorkspaceError


def _runner(name: str, spec: TaskSpec) -> Runner:
    return LocalRunner() if name == "local" else DockerRunner(spec)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="taskgrade", description=__doc__)
    p.add_argument("--version", action="version", version=f"taskgrade {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="check a task.toml")
    v.add_argument("task")

    for name, help_ in (
        ("grade", "grade one solution directory"),
        ("stress", "check the grader against reference, alternate and adversarial solutions"),
    ):
        s = sub.add_parser(name, help=help_)
        s.add_argument("task")
        if name == "grade":
            s.add_argument("solution", help="directory overlaid on the repo")
        s.add_argument(
            "--runner",
            choices=("docker", "local"),
            default="docker",
            help="docker (default, offline sandbox) or local (trusted code only)",
        )
        s.add_argument("--json", action="store_true", help="print a JSON report")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        spec = load_spec(args.task)
        if args.cmd == "validate":
            print(f"ok: {spec.name} ({len(spec.criteria)} criteria)")
            return 0
        runner = _runner(args.runner, spec)
        if args.cmd == "grade":
            solution = Path(args.solution)
            if not solution.is_dir():
                raise SpecError(f"solution directory not found: {solution}")
            runner.prepare()
            g = grade(spec, solution, runner)
            print(to_json(grade_dict(g)) if args.json else grade_text(g))
            return 0 if g.passed else 1
        rep = stress(spec, runner)
        print(to_json(stress_dict(rep)) if args.json else stress_text(rep))
        return 0 if rep.robust else 1
    except (SpecError, WorkspaceError, RuntimeError) as exc:
        print(f"taskgrade: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
