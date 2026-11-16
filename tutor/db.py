"""SQLite tables and queries. Every answer is saved here with save_attempt().

Rules:
- Every connection goes through connect(), which turns on foreign keys (SQLite turns them off by default).
- init_db() is safe to run many times: it never deletes anything (CLAUDE.md, rule 10).
- All dates are stored in UTC, in ISO format: 2026-11-16T21:04:05+00:00
"""

import json
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

# change this number only together with a migration (see PLAN.md, Step 1).
SCHEMA_VERSION = 1


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

UPSERT_SKILL_SQL = """
INSERT INTO skills (id, name, level, category, active) VALUES (?, ?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET
    name = excluded.name, level = excluded.level, category = excluded.category, active = excluded.active
"""

INSERT_EXERCISE_SQL = """
INSERT INTO exercises (
    section, skill_id, level, topic, sub_topic, prompt_text, expected_answer, accepted_answers, hint, model,
    prompt_version, created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def init_db(database_path=DEFAULT_DATABASE_PATH):
    # Safe to run many times: creates what is missing, updates the skills, never deletes.
    with connect(database_path) as connection:
        database_version = connection.execute("PRAGMA user_version").fetchone()[0]

        if database_version > SCHEMA_VERSION:
            raise RuntimeError("The database is newer than this code (version " + str(database_version) + ").")

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
        exercise.section, exercise.skill_id, exercise.level, exercise.topic, exercise.sub_topic, exercise.prompt_text,
        exercise.expected_answer, accepted_answers_text, exercise.hint, exercise.model, exercise.prompt_version,
        to_iso_text(created_at),
    )

    with connect(database_path) as connection:
        cursor = connection.execute(INSERT_EXERCISE_SQL, exercise_values)
        new_exercise_id = cursor.lastrowid

    return new_exercise_id


def save_attempt(attempt, database_path=DEFAULT_DATABASE_PATH):
    # Returns the id of the new row. An unknown exercise_id or skill_id is refused by the foreign keys.
    if not isinstance(attempt, Attempt):
        raise TypeError("save_attempt() needs an Attempt model, not " + type(attempt).__name__)

    created_at = attempt.created_at or utc_now()
    attempt_values = (
        attempt.submission_id, attempt.exercise_id, attempt.section, attempt.skill_id, attempt.source,
        attempt.your_answer, attempt.verdict, attempt.error_type, attempt.explanation, attempt.mistake_text,
        attempt.correction, int(attempt.hint_used), attempt.seconds_taken, attempt.graded_by, attempt.model,
        attempt.prompt_version, to_iso_text(created_at),
    )

    with connect(database_path) as connection:
        cursor = connection.execute(INSERT_ATTEMPT_SQL, attempt_values)
        new_attempt_id = cursor.lastrowid

    return new_attempt_id


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
