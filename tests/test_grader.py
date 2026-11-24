from taskgrade.grader import grade
from taskgrade.runners import LocalRunner
from taskgrade.spec import load_spec


def _grade(task, sol):
    return grade(load_spec(task), sol, LocalRunner())


def test_run_criterion_pass_and_fail(tiny_task):
    task, sol = tiny_task(
        """
        [[criteria]]
        id = "value-is-one"
        run = "grep -q 'VALUE = 1' app.py"
        [[criteria]]
        id = "never"
        required = false
        run = "exit 3"
        """
    )
    g = _grade(task, sol)
    assert g.passed  # the failing criterion is optional
    by_id = {r.id: r for r in g.results}
    assert by_id["value-is-one"].passed
    assert not by_id["never"].passed and by_id["never"].detail.startswith("exit 3")


def test_required_failure_fails_the_grade(tiny_task):
    task, sol = tiny_task('[[criteria]]\nid = "x"\nrun = "false"\n')
    g = _grade(task, sol)
    assert not g.passed and g.failed_required == ["x"]


def test_timeout_is_a_failure(tiny_task):
    task, sol = tiny_task('[env]\ntimeout = 1\n[[criteria]]\nid = "slow"\nrun = "sleep 5"\n')
    r = _grade(task, sol).results[0]
    assert not r.passed and "timed out" in r.detail


def test_forbid_reports_file_and_line(tiny_task):
    task, sol = tiny_task(
        '[[criteria]]\nid = "no-eval"\nforbid = { pattern = "eval\\\\(", paths = ["*.py"] }\n',
        {"app.py": "VALUE = 1\nX = eval('2')\n"},
    )
    r = _grade(task, sol).results[0]
    assert not r.passed
    assert r.detail == "app.py:2: X = eval('2')"


def test_only_modifies(tiny_task):
    task, sol = tiny_task(
        '[[criteria]]\nid = "scope"\nonly_modifies = ["app.py"]\n',
        {"app.py": "VALUE = 1\n", "lib/helper.py": "pass\n"},
    )
    r = _grade(task, sol).results[0]
    assert not r.passed and "lib/helper.py" in r.detail
