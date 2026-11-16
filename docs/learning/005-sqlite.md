# 005 - SQLite

- **Date:** 2026-11-16
- **Step of the plan:** Step 1 (Part 2)
- **Files where I used it:** `tutor/db.py`, `tests/test_db.py`

## what it is

SQLite is a database in one single file (`data/tutor.db`). There is no server to install or start:
Python talks to it with the built-in `sqlite3` module, and I use normal SQL (`CREATE TABLE`, `INSERT`, `SELECT`).
It is perfect for one user on one computer, and pandas reads it directly.

## why I needed it

Every answer must be saved (rule 3), and the tutor, the reviews and the dashboard all read the same data.
A CSV file cannot protect the data (wrong ids, half-written rows); SQLite can, with foreign keys and transactions.

## how I used it here

**1. Every connection goes through `connect()`**, a context manager used with `with`:

```python
with db.connect(database_path) as connection:
    connection.execute("INSERT INTO lesson_events (skill_id, opened_at) VALUES (?, ?)", ("to_be", now_text))
```

At the end of the `with` block it saves (commit). If an error happens inside, it undoes everything (rollback).
It always closes the connection. A test proves the rollback: it deletes all skills, then divides by zero,
and the skills are still there.

**2. Foreign keys must be turned on in EVERY connection.** SQLite turns them off by default:

```python
connection.execute("PRAGMA foreign_keys = ON")
```

With them on, an attempt with `exercise_id = 999` (no such exercise) is refused with `sqlite3.IntegrityError`.
A foreign key accepts NULL unless the column is `NOT NULL`; `exercise_id` is `NOT NULL` by my design choice.

**3. `?` placeholders, never text joined by hand:**

```python
connection.execute("SELECT * FROM attempts WHERE skill_id = ?", (skill_id,))
```

SQLite puts the value in safely (no SQL injection, no problem with quotes like "don't").
Note the comma in `(skill_id,)`: a tuple with one item.

**4. `init_db()` is safe to run many times:**

- `CREATE TABLE IF NOT EXISTS` creates a table only if it is missing.
- "Upsert" = insert, or update if the id already exists:
  `INSERT ... ON CONFLICT (id) DO UPDATE SET name = excluded.name, ...`
- Nothing is ever deleted (rule 10). A retired skill gets `active = 0`.

**5. `PRAGMA user_version`** is a free number inside the database file. I use it as the schema version (1).
Later, when a step needs a new column, a migration will change the table and set the number to 2.
`CREATE TABLE IF NOT EXISTS` never adds a column to an existing table, so migrations are needed for that.

**6. Dates are text in UTC ISO format** (SQLite has no real date type):

```text
00:30 on 1 July in Lisbon (summer, UTC+1)  →  saved as 2026-06-30T23:30:00+00:00
```

**7. Reading into pandas:**

```python
attempts_table = pd.read_sql_query("SELECT * FROM attempts ORDER BY created_at, id", connection)
attempts_table["created_at"] = pd.to_datetime(attempts_table["created_at"], utc=True)
```

SQLite has no boolean either: `hint_used` is saved as 0/1 and turned back into `True`/`False` in pandas.

**8. Tests never touch my real data:** pytest's `tmp_path` gives each test a new empty folder,
and the test database lives there.

## mistakes I made and how I fixed them

- I first thought a foreign key could not be empty. Wrong: SQLite foreign keys allow NULL unless the column
  is `NOT NULL`. Making `exercise_id` required is a design choice, not a technical limit.

## links

- https://docs.python.org/3/library/sqlite3.html
- https://www.sqlite.org/foreignkeys.html
- https://www.sqlite.org/lang_upsert.html
- https://www.sqlite.org/pragma.html#pragma_user_version