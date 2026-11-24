import re

import pytest

from taskgrade.report import stress_text
from taskgrade.runners import DockerRunner, LocalRunner
from taskgrade.spec import load_spec
from taskgrade.stress import stress

from .conftest import docker_available

EXPECTED_CATCHES = {
    "lazy_hardcode": ["hidden-tests"],
    "no_order_check": ["hidden-tests"],
    "skip_tests": ["only-solution-files"],
    "exit_early": ["no-process-exit"],
}


def _check_example(rep):
    assert rep.robust, stress_text(rep)
    caught = {c.name: c.grade.failed_required for c in rep.cases if c.role == "adversarial"}
    assert caught == EXPECTED_CATCHES


def test_example_grader_is_robust(example_task):
    _check_example(stress(load_spec(example_task), LocalRunner()))


@pytest.mark.parametrize(
    ("criterion", "hole"),
    [("only-solution-files", "skip_tests"), ("no-process-exit", "exit_early")],
)
def test_removing_a_criterion_opens_a_hole(example_copy, criterion, hole):
    task = example_copy / "task.toml"
    text = task.read_text()
    blocks = text.split("[[criteria]]")
    blocks = [b for b in blocks if f'id = "{criterion}"' not in b]
    task.write_text("[[criteria]]".join(blocks))

    rep = stress(load_spec(task), LocalRunner())
    assert not rep.robust
    holes = [c.name for c in rep.cases if not c.ok]
    assert holes == [hole]
    assert f"GRADER HOLE: '{hole}'" in stress_text(rep)


def test_broken_reference_is_reported(example_copy):
    (example_copy / "solutions" / "reference" / "duration.py").write_text(
        "def parse_duration(text):\n    return 0\n"
    )
    rep = stress(load_spec(example_copy / "task.toml"), LocalRunner())
    assert not rep.robust
    assert "BROKEN: correct solution 'reference'" in stress_text(rep)


def test_missing_reference_and_adversarial_are_problems(tiny_task):
    task, _ = tiny_task('[[criteria]]\nid = "a"\nrun = "true"\n')
    rep = stress(load_spec(task), LocalRunner())
    assert not rep.robust
    text = stress_text(rep)
    assert re.search(r"PROBLEM: no reference", text)
    assert re.search(r"PROBLEM: no adversarial", text)


def test_docker_command_is_sandboxed(example_task, tmp_path):
    runner = DockerRunner(load_spec(example_task))
    cmd = runner.command(tmp_path, "true", "n")
    joined = " ".join(cmd)
    for flag in ("--network none", "--cap-drop ALL", "--security-opt no-new-privileges"):
        assert flag in joined
    assert runner.tag.startswith("taskgrade/parse-duration:")
    assert runner.dockerfile().splitlines()[-1] == "RUN pip install --no-cache-dir pytest==8.3.4"


@pytest.mark.docker
@pytest.mark.skipif(not docker_available(), reason="docker not available")
def test_example_grader_is_robust_in_docker(example_task):
    _check_example(stress(load_spec(example_task), DockerRunner(load_spec(example_task))))
