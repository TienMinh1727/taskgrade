import os

import pytest

from taskgrade.spec import load_spec
from taskgrade.workspace import WorkspaceError, build_workspace, changed_files


def test_hidden_tests_replace_the_tests_folder(example_task, tmp_path):
    spec = load_spec(example_task)
    sol = tmp_path / "sol"
    (sol / "tests").mkdir(parents=True)
    (sol / "duration.py").write_text("def parse_duration(t):\n    return 0\n")
    (sol / "tests" / "test_duration.py").write_text("def test_x():\n    pass\n")
    (sol / "tests" / "conftest.py").write_text("# sneaky\n")

    ws = tmp_path / "ws"
    changed = build_workspace(spec, sol, ws)

    assert changed == ["duration.py", "tests/conftest.py", "tests/test_duration.py"]
    hidden = (spec.hidden_tests / "test_duration.py").read_text()
    assert (ws / "tests" / "test_duration.py").read_text() == hidden
    assert not (ws / "tests" / "conftest.py").exists()
    assert (ws / "duration.py").read_text().endswith("return 0\n")


def test_identical_files_are_not_changes(example_task, tmp_path):
    spec = load_spec(example_task)
    sol = tmp_path / "sol"
    sol.mkdir()
    (sol / "duration.py").write_bytes((spec.repo / "duration.py").read_bytes())
    assert changed_files(spec.repo, sol) == []


def test_symlinks_in_solution_are_rejected(example_task, tmp_path):
    spec = load_spec(example_task)
    sol = tmp_path / "sol"
    sol.mkdir()
    os.symlink("/etc/passwd", sol / "duration.py")
    with pytest.raises(WorkspaceError, match="symlinks"):
        build_workspace(spec, sol, tmp_path / "ws")
