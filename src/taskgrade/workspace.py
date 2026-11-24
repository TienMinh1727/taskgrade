"""Build a grading workspace: base repo + solution overlay + hidden tests."""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path

from .spec import TaskSpec


class WorkspaceError(ValueError):
    """A solution cannot be applied safely."""


def _files(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise WorkspaceError(f"symlinks are not allowed in solutions: {p.relative_to(root)}")
        if p.is_file():
            out.append(p)
    return out


def changed_files(repo: Path, solution: Path) -> list[str]:
    """Paths (posix, relative) that the solution adds or changes compared to the repo."""
    changed = []
    for src in _files(solution):
        rel = src.relative_to(solution)
        base = repo / rel
        if not base.is_file() or not filecmp.cmp(src, base, shallow=False):
            changed.append(rel.as_posix())
    return changed


def build_workspace(spec: TaskSpec, solution: Path, dest: Path) -> list[str]:
    """Populate ``dest`` and return the files the solution touched.

    Hidden tests are copied last and *replace* the destination folder, so a solution
    cannot edit, add to or skip the tests that grade it from inside that folder.
    """
    changed = changed_files(spec.repo, solution)
    shutil.copytree(spec.repo, dest, symlinks=True)
    shutil.copytree(solution, dest, dirs_exist_ok=True)
    if spec.hidden_tests is not None:
        target = (dest / spec.hidden_tests_dest).resolve()
        if not target.is_relative_to(dest.resolve()):
            raise WorkspaceError("hidden_tests_dest points outside the workspace")
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(spec.hidden_tests, target)
    return changed
