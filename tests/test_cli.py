import json

from taskgrade.cli import main


def test_validate(example_task, capsys):
    assert main(["validate", str(example_task)]) == 0
    assert "ok: parse-duration (4 criteria)" in capsys.readouterr().out


def test_grade_reference_passes(example_task, capsys):
    sol = example_task.parent / "solutions" / "reference"
    assert main(["grade", str(example_task), str(sol), "--runner", "local"]) == 0
    assert capsys.readouterr().out.strip().endswith("Result: PASS")


def test_grade_adversarial_fails_with_json(example_task, capsys):
    sol = example_task.parent / "solutions" / "no_order_check"
    assert main(["grade", str(example_task), str(sol), "--runner", "local", "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["passed"] is False
    assert [c["id"] for c in data["criteria"] if not c["passed"]] == ["hidden-tests"]


def test_stress_json(example_task, capsys):
    assert main(["stress", str(example_task), "--runner", "local", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["robust"] is True
    assert len(data["cases"]) == 6


def test_errors_exit_2(tmp_path, capsys):
    assert main(["validate", str(tmp_path / "missing.toml")]) == 2
    assert "taskgrade: error: cannot read" in capsys.readouterr().err
