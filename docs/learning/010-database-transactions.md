# 010 - Database transactions: all or nothing

- **Date:** 2026-11-16
- **Step of the plan:** Step 2 (Part 2)
- **Files where I used it:** `tutor/db.py` (`save_attempts()`, `connect()`), `tests/test_db.py`

## what it is

A transaction is a group of database changes that count as ONE change. Either every change is saved (commit), or none is (rollback). The database never keeps half of the group.

In Python's `sqlite3`, a transaction starts by itself before the first `INSERT`, and lasts until `commit()` or `rollback()`.

## why I needed it

One answer can create two rows in `attempts`: "She has writed the report" gives a targeted row (`present_perfect`, correct) and a detected row (`irregular_verbs`, wrong), with the same `submission_id`.

Saved with two separate `save_attempt()` calls, there were two transactions. If the second failed (for example, a wrong `exercise_id`), the first row stayed alone: the database would say "present perfect correct" and forget the irregular-verb mistake. My mastery numbers would be wrong, and nothing would show it.

## how I used it here

`save_attempts()` inserts every row of ONE answer inside ONE `with connect(...)` block:

```python
with connect(database_path) as connection:
    for attempt in attempt_list:
        cursor = connection.execute(INSERT_ATTEMPT_SQL, make_attempt_values(attempt, default_created_at))
        new_attempt_ids.append(cursor.lastrowid)
```

`connect()` (note 005) does the rest: `commit()` at the end of the block, `rollback()` if any error happens inside it. So the loop is all or nothing.

Before the loop, guard clauses check what ONE answer means:

- the list is not empty;
- every item is an `Attempt` model;
- all rows have the same `submission_id` (rows of two answers must not be saved together).

The rows also get the same date, so "one answer" stays one moment in the charts.

The test that proves it: the second row points to exercise 999, which does not exist.

```python
with pytest.raises(sqlite3.IntegrityError):
    db.save_attempts([targeted_attempt, detected_attempt], database_path)

assert count_rows(database_path, "attempts") == 0   # the first row was undone too
```

`save_attempt()` (one row) now calls `save_attempts([attempt])`: the insert code lives in one place.

## mistakes I made and how I fixed them

- None in code. The risk was invisible: two separate saves work perfectly until the day the second one fails. The question to ask is "which rows must exist together?"

## links

- Note 005 (SQLite): how `connect()` commits and rolls back.
- Note 009 (migrations): the same idea, one transaction per migration step.
- Python `sqlite3`, transaction control: https://docs.python.org/3/library/sqlite3.html#transaction-control
