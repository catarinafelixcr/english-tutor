"""SQLite tables and queries. Every answer is saved here with save_attempt().

Rules:
- Every connection goes through connect(), which turns on foreign keys (SQLite turns them off by default).
- init_db() is safe to run many times: it never deletes anything (CLAUDE.md, rule 10).
- All dates are stored in UTC, in ISO format: 2026-11-16T21:04:05+00:00
- A database with an older version is migrated by init_db(), after a backup copy (data/backups/).
"""

import json
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tutor import skills
from tutor.schemas import Attempt, Exercise

PROJECT_FOLDER = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_FOLDER / "data" / "tutor.db"

# Change this number only together with a new entry in MIGRATIONS (below).
SCHEMA_VERSION = 2


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS skills (
    id        TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    level     TEXT NOT NULL,
    category  TEXT NOT NULL,
    active    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS exercises (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    section          TEXT NOT NULL,
    exercise_type    TEXT,
    skill_id         TEXT NOT NULL REFERENCES skills (id),
    level            TEXT NOT NULL,
    topic            TEXT,
    sub_topic        TEXT,
    prompt_text      TEXT NOT NULL,
    expected_answer  TEXT,
    accepted_answers TEXT NOT NULL DEFAULT '[]',
    hint             TEXT,
    model            TEXT,
    prompt_version   TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id   TEXT NOT NULL,
    exercise_id     INTEGER NOT NULL REFERENCES exercises (id),
    section         TEXT NOT NULL,
    skill_id        TEXT NOT NULL REFERENCES skills (id),
    source          TEXT NOT NULL,
    your_answer     TEXT NOT NULL,
    verdict         TEXT NOT NULL,
    error_type      TEXT,
    explanation     TEXT NOT NULL DEFAULT '',
    mistake_text    TEXT,
    correction      TEXT,
    hint_used       INTEGER NOT NULL DEFAULT 0,
    seconds_taken   REAL,
    graded_by       TEXT NOT NULL,
    model           TEXT,
    prompt_version  TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS attempts_by_skill ON attempts (skill_id, created_at);
CREATE INDEX IF NOT EXISTS attempts_by_submission ON attempts (submission_id);

CREATE TABLE IF NOT EXISTS reviews (
    exercise_id  INTEGER PRIMARY KEY REFERENCES exercises (id),
    box          INTEGER NOT NULL,
    due_date     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lessons (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id     TEXT NOT NULL REFERENCES skills (id),
    lesson_text  TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lesson_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id   TEXT NOT NULL REFERENCES skills (id),
    opened_at  TEXT NOT NULL
);
"""

# Migrations: for each version number, the SQL statements that bring the database from the version before to it.
# CREATE_TABLES_SQL above is always the LATEST shape: a new database gets it directly and needs no migration.
MIGRATIONS = {
    2: [
        "ALTER TABLE exercises ADD COLUMN exercise_type TEXT",
        "UPDATE exercises SET exercise_type = 'gap' WHERE section = 'practice'",
    ],
}

UPSERT_SKILL_SQL = """
INSERT INTO skills (id, name, level, category, active) VALUES (?, ?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET
    name = excluded.name, level = excluded.level, category = excluded.category, active = excluded.active
"""

INSERT_EXERCISE_SQL = """
INSERT INTO exercises (
    section, exercise_type, skill_id, level, topic, sub_topic, prompt_text, expected_answer, accepted_answers, hint,
    model, prompt_version, created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

INSERT_ATTEMPT_SQL = """
INSERT INTO attempts (
    submission_id, exercise_id, section, skill_id, source, your_answer, verdict, error_type, explanation,
    mistake_text, correction, hint_used, seconds_taken, graded_by, model, prompt_version, created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


# ---------- small helpers ----------

def utc_now():
    return datetime.now(timezone.utc)


def to_iso_text(moment):
    # One format for every date in the database, always with "+00:00" at the end.
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def new_submission_id():
    # A random unique text. All attempts from one answer share it.
    return uuid.uuid4().hex


# ---------- connection and setup ----------

@contextmanager
def connect(database_path=DEFAULT_DATABASE_PATH):
    # Use it with "with": it saves (commit) at the end, undoes everything (rollback) on an error, and always closes.
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def find_skill_ids_missing_from_code(connection):
    skill_ids_in_code = set()

    for skill in skills.SKILLS:
        skill_ids_in_code.add(skill["id"])

    missing_skill_ids = []

    for row in connection.execute("SELECT id FROM skills ORDER BY id"):
        if row[0] not in skill_ids_in_code:
            missing_skill_ids.append(row[0])

    return missing_skill_ids


def read_schema_version(database_path):
    # 0 = a new, empty database (SQLite starts every file at 0).
    with connect(database_path) as connection:
        database_version = connection.execute("PRAGMA user_version").fetchone()[0]

    return database_version


def back_up_database(database_path):
    # A copy of the whole file before a migration: data/backups/tutor_before_v2_20261116T210405Z.db
    database_path = Path(database_path)
    backup_folder = database_path.parent / "backups"
    backup_folder.mkdir(parents=True, exist_ok=True)

    time_text = utc_now().strftime("%Y%m%dT%H%M%SZ")
    backup_name = database_path.stem + "_before_v" + str(SCHEMA_VERSION) + "_" + time_text + ".db"
    backup_path = backup_folder / backup_name

    # copy2 also keeps the file dates. No connection is open now, so the copy is complete.
    shutil.copy2(database_path, backup_path)

    return backup_path


def migrate_database(database_path, database_version):
    # One version at a time (1 → 2, later 2 → 3...). Each step is ONE transaction: its statements and the new
    # version number are saved together, or not at all (SQLite can undo an ALTER TABLE too).
    for target_version in range(database_version + 1, SCHEMA_VERSION + 1):
        with connect(database_path) as connection:
            connection.execute("BEGIN")

            for migration_statement in MIGRATIONS[target_version]:
                connection.execute(migration_statement)

            connection.execute("PRAGMA user_version = " + str(target_version))


def init_db(database_path=DEFAULT_DATABASE_PATH):
    # Safe to run many times: migrates an old database (after a backup), creates what is missing,
    # updates the skills, never deletes.
    database_version = read_schema_version(database_path)

    if database_version > SCHEMA_VERSION:
        raise RuntimeError("The database is newer than this code (version " + str(database_version) + ").")

    # A new database (version 0) is created directly in the latest shape: no backup, no migration.
    if 0 < database_version < SCHEMA_VERSION:
        back_up_database(database_path)
        migrate_database(database_path, database_version)

    with connect(database_path) as connection:
        connection.executescript(CREATE_TABLES_SQL)

        missing_skill_ids = find_skill_ids_missing_from_code(connection)

        if missing_skill_ids:
            raise RuntimeError("These skill ids are in the database but not in skills.py: "
                               + ", ".join(missing_skill_ids) + ". Skill ids are never deleted: set active False.")

        for skill in skills.SKILLS:
            skill_values = (skill["id"], skill["name"], skill["level"], skill["category"], int(skill["active"]))
            connection.execute(UPSERT_SKILL_SQL, skill_values)

        # PRAGMA does not accept "?" placeholders, so the number is written into the text (it is our own constant).
        connection.execute("PRAGMA user_version = " + str(SCHEMA_VERSION))


# ---------- saving ----------

def save_exercise(exercise, database_path=DEFAULT_DATABASE_PATH):
    # Returns the id of the new row.
    if not isinstance(exercise, Exercise):
        raise TypeError("save_exercise() needs an Exercise model, not " + type(exercise).__name__)

    created_at = exercise.created_at or utc_now()

    # A list cannot go in one SQLite column, so it is saved as JSON text: ["is working", "'s working"]
    accepted_answers_text = json.dumps(exercise.accepted_answers, ensure_ascii=False)

    exercise_values = (
        exercise.section, exercise.exercise_type, exercise.skill_id, exercise.level, exercise.topic, exercise.sub_topic,
        exercise.prompt_text, exercise.expected_answer, accepted_answers_text, exercise.hint, exercise.model,
        exercise.prompt_version, to_iso_text(created_at),
    )

    with connect(database_path) as connection:
        cursor = connection.execute(INSERT_EXERCISE_SQL, exercise_values)
        new_exercise_id = cursor.lastrowid

    return new_exercise_id


def make_attempt_values(attempt, default_created_at):
    # The values of one attempt, in the order of INSERT_ATTEMPT_SQL.
    created_at = attempt.created_at or default_created_at
    attempt_values = (
        attempt.submission_id, attempt.exercise_id, attempt.section, attempt.skill_id, attempt.source,
        attempt.your_answer, attempt.verdict, attempt.error_type, attempt.explanation, attempt.mistake_text,
        attempt.correction, int(attempt.hint_used), attempt.seconds_taken, attempt.graded_by, attempt.model,
        attempt.prompt_version, to_iso_text(created_at),
    )

    return attempt_values


def save_attempts(attempt_list, database_path=DEFAULT_DATABASE_PATH):
    # Saves ALL rows of ONE answer (for example a targeted row + a detected row) in one transaction:
    # all rows are saved, or none (connect() undoes everything on an error). Returns the new ids, in order.
    # An unknown exercise_id or skill_id is refused by the foreign keys.
    if len(attempt_list) == 0:
        raise ValueError("save_attempts() needs at least one attempt")

    for attempt in attempt_list:
        if not isinstance(attempt, Attempt):
            raise TypeError("save_attempts() needs Attempt models, not " + type(attempt).__name__)

    first_submission_id = attempt_list[0].submission_id

    for attempt in attempt_list:
        if attempt.submission_id != first_submission_id:
            raise ValueError("all attempts saved together must come from one answer (one submission_id)")

    # The rows of one answer get the same date, unless an attempt already has its own.
    default_created_at = utc_now()
    new_attempt_ids = []

    with connect(database_path) as connection:
        for attempt in attempt_list:
            cursor = connection.execute(INSERT_ATTEMPT_SQL, make_attempt_values(attempt, default_created_at))
            new_attempt_ids.append(cursor.lastrowid)

    return new_attempt_ids


def save_attempt(attempt, database_path=DEFAULT_DATABASE_PATH):
    # Returns the id of the new row. One answer with ONE row (CLAUDE.md, rule 3: every answer is saved).
    if not isinstance(attempt, Attempt):
        raise TypeError("save_attempt() needs an Attempt model, not " + type(attempt).__name__)

    new_attempt_ids = save_attempts([attempt], database_path)

    return new_attempt_ids[0]


# ---------- reading ----------

def get_attempts(skill_id=None, database_path=DEFAULT_DATABASE_PATH):
    # All attempts (or only one skill) as a pandas DataFrame, oldest first, with real dates and booleans.
    query = "SELECT * FROM attempts ORDER BY created_at, id"
    query_values = ()

    if skill_id is not None:
        query = "SELECT * FROM attempts WHERE skill_id = ? ORDER BY created_at, id"
        query_values = (skill_id,)

    with connect(database_path) as connection:
        attempts_table = pd.read_sql_query(query, connection, params=query_values)

    attempts_table["created_at"] = pd.to_datetime(attempts_table["created_at"], utc=True)
    attempts_table["hint_used"] = attempts_table["hint_used"].astype(bool)

    return attempts_table


def get_exercise_sentences(skill_id, database_path=DEFAULT_DATABASE_PATH):
    # Every sentence already saved for one skill, newest first. Used to avoid the same sentence again.
    query = "SELECT prompt_text FROM exercises WHERE skill_id = ? ORDER BY created_at DESC, id DESC"

    with connect(database_path) as connection:
        sentence_rows = connection.execute(query, (skill_id,)).fetchall()

    sentences = []

    for sentence_row in sentence_rows:
        sentences.append(sentence_row[0])

    return sentences


def row_to_exercise(exercise_row):
    # One sqlite3.Row of the exercises table → an Exercise model (the JSON text becomes a list again).
    exercise = Exercise(section=exercise_row["section"], exercise_type=exercise_row["exercise_type"],
                        skill_id=exercise_row["skill_id"], level=exercise_row["level"], topic=exercise_row["topic"],
                        sub_topic=exercise_row["sub_topic"], prompt_text=exercise_row["prompt_text"],
                        expected_answer=exercise_row["expected_answer"],
                        accepted_answers=json.loads(exercise_row["accepted_answers"]), hint=exercise_row["hint"],
                        model=exercise_row["model"], prompt_version=exercise_row["prompt_version"],
                        created_at=datetime.fromisoformat(exercise_row["created_at"]))

    return exercise


def get_unanswered_exercises(exercise_type, level, skill_id=None, topic=None, database_path=DEFAULT_DATABASE_PATH):
    # Practice exercises that were created but never answered, oldest first, as a list of (exercise id, Exercise).
    # The page shows these before asking the AI for new ones (no request spent).
    # skill_id or topic = None means "any".
    query = """
    SELECT * FROM exercises
    WHERE section = 'practice' AND exercise_type = ? AND level = ?
      AND NOT EXISTS (SELECT 1 FROM attempts WHERE attempts.exercise_id = exercises.id)
    """
    query_values = [exercise_type, level]

    if skill_id is not None:
        query = query + " AND skill_id = ?"
        query_values.append(skill_id)

    if topic is not None:
        query = query + " AND topic = ?"
        query_values.append(topic)

    query = query + " ORDER BY created_at, id"

    with connect(database_path) as connection:
        # Row lets us read a column by its name: exercise_row["skill_id"].
        connection.row_factory = sqlite3.Row
        exercise_rows = connection.execute(query, query_values).fetchall()

    unanswered_exercises = []

    for exercise_row in exercise_rows:
        unanswered_exercises.append((exercise_row["id"], row_to_exercise(exercise_row)))

    return unanswered_exercises
