# taskgrade

[![ci](https://github.com/TienMinh1727/taskgrade/actions/workflows/ci.yaml/badge.svg)](https://github.com/TienMinh1727/taskgrade/actions/workflows/ci.yaml)

Run a coding task's grader offline in Docker, then **stress-test the grader itself**: correct
solutions written in different ways must pass, and lazy, wrong or shortcut solutions must fail.

A grader that only checks "pytest exited 0" is easy to fool. In the bundled example, a solution
can ship a `conftest.py` that skips every test, or call `os._exit(0)` on import. Both make pytest
exit 0. `taskgrade stress` runs those solutions on purpose and reports any that get through as a
**grader hole**.

```text
$ taskgrade stress examples/parse-duration/task.toml
Stress test: parse-duration
  ROLE         SOLUTION        EXPECT  GOT   VERDICT  CAUGHT BY
  reference    reference       pass    pass  ok
  alternate    alt_scanner     pass    pass  ok
  adversarial  lazy_hardcode   fail    fail  ok       hidden-tests
  adversarial  no_order_check  fail    fail  ok       hidden-tests
  adversarial  skip_tests      fail    fail  ok       only-solution-files
  adversarial  exit_early      fail    fail  ok       no-process-exit
Grader is robust: 6/6 cases behaved as expected.
```

Delete the `only-solution-files` criterion from the spec and the same command reports
`GRADER HOLE: 'skip_tests' passed every required criterion` and exits 1.

## How it works

1. **Environment.** `[env].setup` is baked into an image once (`docker build`). That is the only
   step with network access, so dependencies are pinned and the repo builds offline afterwards.
2. **Workspace.** For each solution: copy the base repo, overlay the solution directory, then copy
   the hidden tests over `hidden_tests_dest`, **replacing** that folder. A solution cannot edit,
   add to or skip the tests that grade it from inside that folder. Symlinks in solutions are
   rejected.
3. **Criteria.** Each criterion is required or optional, and is one of:
   - `run`: a shell command that must exit 0 (runs in the sandbox).
   - `forbid`: a regex that must not match in the given file globs.
   - `only_modifies`: the solution may only add or change files matching these globs.
4. **Sandbox.** Every `run` command uses `docker run --network none --cap-drop ALL
   --security-opt no-new-privileges --pids-limit 256 --memory 1g` as your own UID, with a
   per-command timeout. The container is killed on timeout.
5. **Stress.** The reference and every alternate must pass. Every adversarial must fail at least
   one required criterion. The report names the criterion that caught each one.

## Usage

```bash
pip install git+https://github.com/TienMinh1727/taskgrade
taskgrade validate examples/parse-duration/task.toml
taskgrade grade examples/parse-duration/task.toml path/to/solution   # exit 0 = pass
taskgrade stress examples/parse-duration/task.toml --json             # exit 0 = robust
```

`--runner local` runs commands on the host without Docker. Use it only for code you trust,
such as this repo's own tests.

## Task spec

```toml
[task]
name = "parse-duration"
repo = "repo"                  # state before the change
hidden_tests = "hidden_tests"  # copied over hidden_tests_dest at grade time
hidden_tests_dest = "tests"

[env]
image = "python:3.12-slim"
setup = ["pip install --no-cache-dir pytest==8.3.4"]
timeout = 60

[[criteria]]
id = "hidden-tests"
required = true
run = "python3 -m pytest -q -p no:cacheprovider tests"

[[criteria]]
id = "only-solution-files"
required = true
only_modifies = ["duration.py"]

[solutions]
reference = "solutions/reference"
alternates = ["solutions/alt_scanner"]

[[solutions.adversarial]]
path = "solutions/skip_tests"
why = "Ships a root conftest.py that skips every test."
```

The full example, with its brief and all six solutions, is in
[`examples/parse-duration`](examples/parse-duration). Its hidden tests include cases a quick
solution tends to miss: `"1h\n"` (Python's `$` matches before a trailing newline), `"١h"`
(`\d` and `str.isdigit()` accept non-ASCII digits), and out-of-order or repeated units.

## Development

```bash
pip install -e '.[dev]'
ruff check . && ruff format --check .
pytest              # Docker tests are skipped automatically if no daemon is available
```

CI runs lint and the unit tests on Python 3.11 to 3.13, then runs `taskgrade stress` on the
example with the Docker runner.

## License

MIT
