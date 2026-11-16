# 009 - database migrations (SQLite, PRAGMA user_version)

- **Date:** 2026-11-16
- **Step of the plan:** Step 2 (Part 1)
- **Files where I used it:** `tutor/db.py`, `tests/test_db.py`

## what it is

A **migration** is a small, numbered change to the shape of a database that already has data: add a column, add a table, fill a new column. The database remembers its own version number, so the code knows which changes are still missing. In SQLite this number is `PRAGMA user_version`: an integer stored in the file itself, 0 in a new file.

## why I needed it

Step 2 has three exercise types (fill the gap, fix the error, word order), but the `exercises` table had no column to tell them apart. My `data/tutor.db` already had real rows from the Step 1 demo, so I could not just change `CREATE TABLE`: `CREATE TABLE IF NOT EXISTS` does nothing when the table already exists. And deleting the database is not an option once I study with the app every day.

## how I used it here

**1. The version number and the list of migrations live in the code.**

```python
SCHEMA_VERSION = 2

MIGRATIONS = {
    2: [
        "ALTER TABLE exercises ADD COLUMN exercise_type TEXT",
        "UPDATE exercises SET exercise_type = 'gap' WHERE section = 'practice'",
    ],
}
```

`CREATE_TABLES_SQL` is always the LATEST shape. A migration only describes how to go from the version before to this one. A test checks that every version above 1 has an entry in `MIGRATIONS`.

**2. `init_db()` decides what to do from the version in the file.**

| Version in the file | What happens |
| --- | --- |
| 0 (new file) | Create all tables in the latest shape. No backup, no migration |
| 1 (older than the code) | Backup copy, then migration 2, then the normal setup |
| 2 (same as the code) | Normal setup only (safe to run many times) |
| 3 (newer than the code) | Stop with an error: old code must not touch a newer database |

**3. A backup copy BEFORE any migration.**

```python
backup_name = database_path.stem + "_before_v" + str(SCHEMA_VERSION) + "_" + time_text + ".db"
shutil.copy2(database_path, backup_path)
```

The real one: `data/backups/tutor_before_v2_20261116T165559Z.db`. No connection is open during the copy, so the file is complete.

**4. One transaction per migration step.**

```python
with connect(database_path) as connection:
    connection.execute("BEGIN")

    for migration_statement in MIGRATIONS[target_version]:
        connection.execute(migration_statement)

    connection.execute("PRAGMA user_version = " + str(target_version))
```

The statements AND the new version number are saved together, or not at all. SQLite can undo an `ALTER TABLE` inside a transaction, which many databases cannot. Without this, a failure after the `ALTER TABLE` would leave the column added but the version still 1, and the next start would try to add the column again ("duplicate column" error, forever).

**5. Testing with a frozen copy of the old shape.** `tests/test_db.py` keeps the Step 1 `CREATE TABLE` text (`VERSION_1_TABLES_SQL`) and builds a real version-1 database from it. The tests check that:

- the rows are kept and get `exercise_type = 'gap'`
- the backup is still version 1 with its rows
- a new database gets no backup
- running `init_db()` twice makes only one backup
- a broken migration changes nothing: no new column, version still 1

The copy is frozen on purpose: if the test used `CREATE_TABLES_SQL`, it would build a version-2 database after the next change, and stop testing the migration.

## mistakes I made and how I fixed them

- No mistake in the code, but one decision: the new column is nullable (`TEXT`, no `NOT NULL DEFAULT 'gap'`). A Writing exercise has no type, and "gap" as a default would be a lie for it. The rule "a Practice exercise needs a type" lives in the Pydantic model `Exercise` instead.
- A precaution, not a problem we saw: `with sqlite3.connect(...)` saves at the end but does NOT close the connection (unlike `with open(...)`). The test fixture closes it by hand, so no open connection can disturb the file copy.

## links

- SQLite `PRAGMA user_version`: https://www.sqlite.org/pragma.html#pragma_user_version
- SQLite `ALTER TABLE`: https://www.sqlite.org/lang_altertable.html
- Python `sqlite3` and transactions: https://docs.python.org/3/library/sqlite3.html#transaction-control
