# 004 - pytest

- **Date:** 2026-11-16
- **Step of the plan:** Step 1 (Part 1)
- **Files where I used it:** `tests/test_skills.py`, `pyproject.toml`

## what it is

pytest is a tool that runs small Python functions called tests. Each test calls my code and checks the result with `assert`.
If every `assert` is true, the test PASSES. If one is false, the test FAILS and pytest shows which value was wrong.

## why I needed it

The skill list has 53 skills and strict rules (unique ids, valid levels, ids never deleted...).
I cannot check all of that by eye every time I change the list. The tests check it in 0.2 seconds, every time -- run `pytest` before saying a task is done.

## how I used it here

A test is a function whose name starts with `test_`, in a file whose name starts with `test_`.
pytest finds them by itself:

```python
from tutor import skills


def test_skill_ids_are_unique():
    all_skill_ids = get_all_skill_ids()

    assert len(all_skill_ids) == len(set(all_skill_ids))
```

`set()` removes duplicates, so if the lengths are different, two skills have the same id.

A message after the `assert` explains the failure:

```python
assert permanent_skill_id in all_skill_ids, permanent_skill_id + " was renamed or deleted"
```

`monkeypatch` replaces something only during one test, then puts it back. Here it replaces the real skill list with a small fake list, so I can test `get_active_skills()` without touching the real data:

```python
def test_get_active_skills_leaves_out_retired_skills(monkeypatch):
    retired_skill = make_fake_skill("old_skill", "verbs", False)
    active_skill = make_fake_skill("new_skill", "verbs", True)
    monkeypatch.setattr(skills, "SKILLS", [retired_skill, active_skill])

    active_skills = skills.get_active_skills()

    assert active_skills == [active_skill]
```

Good test = 3 blocks separated by blank lines: prepare (fake data), act (call the function), check (`assert`).

Commands:

```text
.venv\Scripts\python.exe -m pytest           # run all tests (one dot per passed test)
.venv\Scripts\python.exe -m pytest -v        # one line per test, with PASSED / FAILED
.venv\Scripts\python.exe -m pytest -k unique # only tests with "unique" in the name
```

Setting in `pyproject.toml`, so tests can write `from tutor import skills`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

Today's result: `21 passed in 0.23s`.

Two ideas I learned:

- A test can protect a rule, not only a function. `test_permanent_skill_ids_are_never_removed` protects rule 10
  (ids are never deleted), and `test_every_skill_id_is_in_the_permanent_list` makes sure that list never gets out of date.
- A test should not be fragile: check the stable thing (the id), not a text that may change (the name).
  Build the expected text from the data (`skill["tag_when"]`), not from a sentence copied by hand.

## mistakes I made and how I fixed them

- `ModuleNotFoundError: tutor` can happen because pytest does not add the project folder to the import path.
  Fix: `pythonpath = ["."]` in `pyproject.toml` (added before the first run).

## links

- https://docs.pytest.org/en/stable/getting-started.html
- https://docs.pytest.org/en/stable/how-to/monkeypatch.html