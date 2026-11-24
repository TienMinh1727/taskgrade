import re

import pytest

from taskgrade.spec import SpecError, load_spec


def test_loads_example(example_task):
    spec = load_spec(example_task)
    assert spec.name == "parse-duration"
    assert [c.kind for c in spec.criteria] == ["run", "only_modifies", "forbid", "run"]
    assert spec.reference is not None and spec.reference.name == "reference"
    assert [a.path.name for a in spec.adversarial] == [
        "lazy_hardcode",
        "no_order_check",
        "skip_tests",
        "exit_early",
    ]
    assert spec.setup == ("pip install --no-cache-dir pytest==8.3.4",)


@pytest.mark.parametrize(
    ("criteria", "message"),
    [
        ("", "at least one [[criteria]]"),
        ('[[criteria]]\nid = "a"\n', "exactly one of"),
        (
            '[[criteria]]\nid = "a"\nrun = "true"\nforbid = {pattern="x", paths=["*"]}\n',
            "exactly one of",
        ),
        ('[[criteria]]\nid = "a"\nrun = "true"\n[[criteria]]\nid = "a"\nrun = "true"\n', "unique"),
        ('[[criteria]]\nid = "a"\nrun = "true"\nrequired = false\n', "must be required"),
        ('[[criteria]]\nid = "a"\nonly_modifies = []\n', "non-empty list"),
        ('[[criteria]]\nid = "a"\nforbid = {pattern = "x"}\n', "'pattern' and 'paths'"),
        ('[[criteria]]\nid = "a"\nrun = "  "\n', "non-empty command"),
    ],
)
def test_rejects_bad_criteria(tiny_task, criteria, message):
    task, _ = tiny_task(criteria)
    with pytest.raises(SpecError, match=re.escape(message)):
        load_spec(task)


def test_rejects_path_outside_task(tiny_task, tmp_path):
    (tmp_path / "elsewhere").mkdir()
    task, _ = tiny_task('[[criteria]]\nid = "a"\nrun = "true"\n')
    task.write_text(task.read_text().replace('repo = "repo"', 'repo = "../elsewhere"'))
    with pytest.raises(SpecError, match="outside the task directory"):
        load_spec(task)


def test_rejects_missing_directory(tiny_task):
    task, _ = tiny_task('[[criteria]]\nid = "a"\nrun = "true"\n')
    task.write_text(task.read_text().replace('repo = "repo"', 'repo = "nope"'))
    with pytest.raises(SpecError, match="does not exist"):
        load_spec(task)


def test_rejects_bad_timeout(tiny_task):
    task, _ = tiny_task('[env]\ntimeout = 0\n[[criteria]]\nid = "a"\nrun = "true"\n')
    with pytest.raises(SpecError, match="timeout"):
        load_spec(task)


def test_unreadable_toml(tmp_path):
    bad = tmp_path / "task.toml"
    bad.write_text("not = [valid")
    with pytest.raises(SpecError, match="cannot read"):
        load_spec(bad)
