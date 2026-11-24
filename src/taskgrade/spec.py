"""Load and validate a task spec (``task.toml``)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

KINDS = ("run", "forbid", "only_modifies")


class SpecError(ValueError):
    """The task spec is invalid."""


@dataclass(frozen=True)
class Criterion:
    id: str
    description: str
    required: bool
    kind: str
    run: str | None = None
    pattern: str | None = None
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Adversarial:
    path: Path
    why: str


@dataclass(frozen=True)
class TaskSpec:
    name: str
    root: Path
    repo: Path
    hidden_tests: Path | None
    hidden_tests_dest: str
    image: str
    setup: tuple[str, ...]
    timeout: int
    criteria: tuple[Criterion, ...]
    reference: Path | None
    alternates: tuple[Path, ...]
    adversarial: tuple[Adversarial, ...]


def _dir(root: Path, rel: object, field: str) -> Path:
    if not isinstance(rel, str) or not rel:
        raise SpecError(f"{field}: expected a relative path")
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise SpecError(f"{field}: {rel!r} points outside the task directory")
    if not path.is_dir():
        raise SpecError(f"{field}: directory {rel!r} does not exist")
    return path


def _criterion(raw: dict) -> Criterion:
    cid = raw.get("id")
    if not isinstance(cid, str) or not cid:
        raise SpecError("criteria: every criterion needs an 'id'")
    kinds = [k for k in KINDS if k in raw]
    if len(kinds) != 1:
        raise SpecError(f"criteria.{cid}: set exactly one of {', '.join(KINDS)}")
    kind = kinds[0]
    common = {
        "id": cid,
        "description": str(raw.get("description", "")),
        "required": bool(raw.get("required", True)),
        "kind": kind,
    }
    if kind == "run":
        if not isinstance(raw["run"], str) or not raw["run"].strip():
            raise SpecError(f"criteria.{cid}: 'run' must be a non-empty command")
        return Criterion(**common, run=raw["run"])
    if kind == "forbid":
        rule = raw["forbid"]
        if not isinstance(rule, dict) or not rule.get("pattern") or not rule.get("paths"):
            raise SpecError(f"criteria.{cid}: 'forbid' needs 'pattern' and 'paths'")
        return Criterion(**common, pattern=rule["pattern"], paths=tuple(rule["paths"]))
    paths = raw["only_modifies"]
    if not isinstance(paths, list) or not paths:
        raise SpecError(f"criteria.{cid}: 'only_modifies' must be a non-empty list of globs")
    return Criterion(**common, paths=tuple(paths))


def load_spec(path: str | Path) -> TaskSpec:
    path = Path(path).resolve()
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SpecError(f"cannot read {path}: {exc}") from exc
    root = path.parent

    task = data.get("task", {})
    env = data.get("env", {})
    sols = data.get("solutions", {})
    name = task.get("name")
    if not isinstance(name, str) or not name:
        raise SpecError("task.name is required")

    criteria = tuple(_criterion(c) for c in data.get("criteria", []))
    if not criteria:
        raise SpecError("at least one [[criteria]] is required")
    ids = [c.id for c in criteria]
    if len(ids) != len(set(ids)):
        raise SpecError("criteria ids must be unique")
    if not any(c.required for c in criteria):
        raise SpecError("at least one criterion must be required")

    timeout = env.get("timeout", 120)
    if not isinstance(timeout, int) or timeout <= 0:
        raise SpecError("env.timeout must be a positive integer (seconds)")

    hidden = task.get("hidden_tests")
    return TaskSpec(
        name=name,
        root=root,
        repo=_dir(root, task.get("repo"), "task.repo"),
        hidden_tests=_dir(root, hidden, "task.hidden_tests") if hidden else None,
        hidden_tests_dest=task.get("hidden_tests_dest", "tests"),
        image=env.get("image", "python:3.12-slim"),
        setup=tuple(env.get("setup", [])),
        timeout=timeout,
        criteria=criteria,
        reference=_dir(root, sols["reference"], "solutions.reference")
        if "reference" in sols
        else None,
        alternates=tuple(_dir(root, p, "solutions.alternates") for p in sols.get("alternates", [])),
        adversarial=tuple(
            Adversarial(_dir(root, a.get("path"), "solutions.adversarial"), str(a.get("why", "")))
            for a in sols.get("adversarial", [])
        ),
    )
