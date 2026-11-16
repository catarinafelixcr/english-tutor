"""Tests for tutor/db.py and the Exercise / Attempt models.

Every test uses a temporary database, never data/tutor.db.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from tutor import db, skills
from tutor.schemas import Attempt, Exercise

ALL_TABLES = ["skills", "exercises", "attempts", "reviews", "lessons", "lesson_events"]


# ---------- helpers ----------

@pytest.fixture
def database_path(tmp_path):
    # tmp_path is a new empty folder for each test, created by pytest and deleted later.
    temporary_database_path = tmp_path / "test_tutor.db"
    db.init_db(temporary_database_path)

    return temporary_database_path


def make_exercise(skill_id):
    return Exercise(section="practice", exercise_type="gap", skill_id=skill_id, level="A2", topic="daily life",
                    prompt_text="I ___ 25 years old.", expected_answer="am")


def make_wrong_attempt(exercise_id, skill_id):
    return Attempt(submission_id=db.new_submission_id(), exercise_id=exercise_id, section="practice",
                   skill_id=skill_id, source="targeted", your_answer="have", verdict="wrong", error_type="grammar",
                   explanation="We use 'be' for age.", mistake_text="I have 25 years old",
                   correction="I am 25 years old", hint_used=True, seconds_taken=12.5, graded_by="ai",
                   model="fake-test-model", prompt_version="fake_prompt@000000")


def count_rows(database_path, table_name):
    with db.connect(database_path) as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM " + table_name).fetchone()[0]

    return row_count


# ---------- init_db ----------

def test_init_db_creates_all_tables(database_path):
    with db.connect(database_path) as connection:
        table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()

    table_names = []

    for table_row in table_rows:
        table_names.append(table_row[0])

    for table_name in ALL_TABLES:
        assert table_name in table_names, table_name + " was not created"


def test_init_db_fills_the_skills_table(database_path):
    assert count_rows(database_path, "skills") == len(skills.SKILLS)


def test_init_db_twice_gives_no_duplicates_and_keeps_the_data(database_path):
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)
    db.save_attempt(make_wrong_attempt(exercise_id, "to_be"), database_path)

    db.init_db(database_path)

    assert count_rows(database_path, "skills") == len(skills.SKILLS)
    assert count_rows(database_path, "exercises") == 1
    assert count_rows(database_path, "attempts") == 1


def test_init_db_sets_the_schema_version(database_path):
    with db.connect(database_path) as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert schema_version == db.SCHEMA_VERSION


def test_init_db_stops_when_a_skill_was_deleted_from_the_code(database_path, monkeypatch):
    skills_without_to_be = []

    for skill in skills.SKILLS:
        if skill["id"] != "to_be":
            skills_without_to_be.append(skill)

    monkeypatch.setattr(skills, "SKILLS", skills_without_to_be)

    with pytest.raises(RuntimeError, match="to_be"):
        db.init_db(database_path)


def test_init_db_retires_a_skill_without_deleting_it(database_path, monkeypatch):
    skills_with_to_be_retired = []

    for skill in skills.SKILLS:
        skill_copy = dict(skill)

        if skill_copy["id"] == "to_be":
            skill_copy["active"] = False

        skills_with_to_be_retired.append(skill_copy)

    monkeypatch.setattr(skills, "SKILLS", skills_with_to_be_retired)
    db.init_db(database_path)

    with db.connect(database_path) as connection:
        active_value = connection.execute("SELECT active FROM skills WHERE id = 'to_be'").fetchone()[0]

    assert active_value == 0
    assert count_rows(database_path, "skills") == len(skills.SKILLS)


def test_init_db_refuses_a_database_newer_than_the_code(database_path):
    with db.connect(database_path) as connection:
        connection.execute("PRAGMA user_version = " + str(db.SCHEMA_VERSION + 1))

    with pytest.raises(RuntimeError, match="newer"):
        db.init_db(database_path)


# ---------- migration from version 1 (Step 1) to version 2 (Step 2) ----------

# A FROZEN copy of the Step 1 tables (commit cfa8e2c), so this test keeps building a real version-1 database
# even when CREATE_TABLES_SQL changes again later. Only the tables the migration touches or needs.
VERSION_1_TABLES_SQL = """
CREATE TABLE skills (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, level TEXT NOT NULL, category TEXT NOT NULL, active INTEGER NOT NULL
);
CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT, section TEXT NOT NULL, skill_id TEXT NOT NULL REFERENCES skills (id),
    level TEXT NOT NULL, topic TEXT, sub_topic TEXT, prompt_text TEXT NOT NULL, expected_answer TEXT,
    accepted_answers TEXT NOT NULL DEFAULT '[]', hint TEXT, model TEXT, prompt_version TEXT, created_at TEXT NOT NULL
);
INSERT INTO skills VALUES ('to_be', 'Verb to be', 'A2', 'verbs', 1);
INSERT INTO exercises (section, skill_id, level, topic, prompt_text, expected_answer, created_at)
VALUES ('practice', 'to_be', 'A2', 'travel', 'I ___ tired after the flight.', 'am', '2026-11-16T21:04:05+00:00');
PRAGMA user_version = 1;
"""


@pytest.fixture
def version_1_database_path(tmp_path):
    old_database_path = tmp_path / "old_tutor.db"

    with sqlite3.connect(old_database_path) as connection:
        connection.executescript(VERSION_1_TABLES_SQL)

    # "with sqlite3.connect()" saves but does not close: close it, so Windows lets the test copy the file.
    connection.close()

    return old_database_path


def read_version(database_path):
    connection = sqlite3.connect(database_path)
    database_version = connection.execute("PRAGMA user_version").fetchone()[0]
    connection.close()

    return database_version


def list_backups(database_path):
    backup_folder = database_path.parent / "backups"

    if not backup_folder.exists():
        return []

    return sorted(backup_folder.glob("*.db"))


def test_init_db_upgrades_a_version_1_database_and_keeps_its_rows(version_1_database_path):
    db.init_db(version_1_database_path)

    with db.connect(version_1_database_path) as connection:
        exercise_row = connection.execute("SELECT exercise_type, prompt_text FROM exercises").fetchone()

    assert read_version(version_1_database_path) == 2
    assert exercise_row == ("gap", "I ___ tired after the flight.")
    assert count_rows(version_1_database_path, "exercises") == 1
    assert count_rows(version_1_database_path, "skills") == len(skills.SKILLS)


def test_init_db_makes_a_backup_of_the_old_version_before_migrating(version_1_database_path):
    db.init_db(version_1_database_path)

    backups = list_backups(version_1_database_path)

    assert len(backups) == 1
    assert backups[0].name.startswith("old_tutor_before_v2_")
    # The backup is the database as it was BEFORE: still version 1, and its exercise is still there.
    assert read_version(backups[0]) == 1
    assert count_rows(backups[0], "exercises") == 1


def test_a_new_database_gets_no_backup(database_path):
    assert list_backups(database_path) == []


def test_init_db_twice_on_an_old_database_makes_only_one_backup(version_1_database_path):
    db.init_db(version_1_database_path)
    db.init_db(version_1_database_path)

    assert len(list_backups(version_1_database_path)) == 1
    assert read_version(version_1_database_path) == 2


def test_a_failing_migration_changes_nothing(version_1_database_path, monkeypatch):
    # The second statement fails: the first one (ALTER TABLE) must be undone too, and the version stays 1.
    broken_migrations = {2: ["ALTER TABLE exercises ADD COLUMN exercise_type TEXT", "UPDATE no_such_table SET x = 1"]}
    monkeypatch.setattr(db, "MIGRATIONS", broken_migrations)

    with pytest.raises(sqlite3.OperationalError):
        db.init_db(version_1_database_path)

    with db.connect(version_1_database_path) as connection:
        column_rows = connection.execute("PRAGMA table_info(exercises)").fetchall()

    column_names = []

    for column_row in column_rows:
        column_names.append(column_row[1])

    assert "exercise_type" not in column_names
    assert read_version(version_1_database_path) == 1
    assert len(list_backups(version_1_database_path)) == 1


def test_every_version_above_1_has_a_migration():
    for version_number in range(2, db.SCHEMA_VERSION + 1):
        assert version_number in db.MIGRATIONS, "no migration for version " + str(version_number)


# ---------- connect ----------

def test_connect_turns_on_foreign_keys(database_path):
    with db.connect(database_path) as connection:
        foreign_keys_setting = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert foreign_keys_setting == 1


def test_connect_undoes_everything_after_an_error(database_path):
    with pytest.raises(ZeroDivisionError):
        with db.connect(database_path) as connection:
            connection.execute("DELETE FROM skills")
            1 / 0

    assert count_rows(database_path, "skills") == len(skills.SKILLS)


# ---------- save and read ----------

def test_save_one_attempt_and_read_it_back(database_path):
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)
    attempt = make_wrong_attempt(exercise_id, "to_be")

    db.save_attempt(attempt, database_path)
    attempts_table = db.get_attempts(None, database_path)

    assert len(attempts_table) == 1

    saved_row = attempts_table.iloc[0]

    assert saved_row["submission_id"] == attempt.submission_id
    assert saved_row["exercise_id"] == exercise_id
    assert saved_row["skill_id"] == "to_be"
    assert saved_row["source"] == "targeted"
    assert saved_row["verdict"] == "wrong"
    assert saved_row["error_type"] == "grammar"
    assert saved_row["mistake_text"] == "I have 25 years old"
    assert saved_row["correction"] == "I am 25 years old"
    assert saved_row["hint_used"] == True  # noqa: E712 (numpy bool: "is True" would fail)
    assert saved_row["seconds_taken"] == 12.5
    assert saved_row["graded_by"] == "ai"
    assert saved_row["model"] == "fake-test-model"
    assert saved_row["prompt_version"] == "fake_prompt@000000"


def test_get_attempts_can_filter_by_skill(database_path):
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)
    db.save_attempt(make_wrong_attempt(exercise_id, "to_be"), database_path)
    db.save_attempt(make_wrong_attempt(exercise_id, "spelling"), database_path)

    to_be_attempts = db.get_attempts("to_be", database_path)

    assert list(to_be_attempts["skill_id"]) == ["to_be"]


def test_dates_are_saved_in_utc_iso_format(database_path):
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)
    lisbon_summer_time = timezone(timedelta(hours=1))
    attempt = make_wrong_attempt(exercise_id, "to_be")
    attempt.created_at = datetime(2026, 7, 1, 0, 30, tzinfo=lisbon_summer_time)

    db.save_attempt(attempt, database_path)

    with db.connect(database_path) as connection:
        saved_date_text = connection.execute("SELECT created_at FROM attempts").fetchone()[0]

    # 00:30 in Lisbon summer time is 23:30 of the day before in UTC.
    assert saved_date_text == "2026-06-30T23:30:00+00:00"


def test_an_exercise_keeps_sub_topic_accepted_answers_and_hint(database_path):
    exercise = Exercise(section="practice", exercise_type="gap", skill_id="present_continuous", level="A2",
                        topic="meetings",
                        sub_topic="a daily stand-up", prompt_text="I ___ (work) on the report now.",
                        expected_answer="am working", accepted_answers=["'m working"], hint="right now",
                        model="fake-test-model", prompt_version="fake_prompt@000000")

    exercise_id = db.save_exercise(exercise, database_path)

    with db.connect(database_path) as connection:
        saved_row = connection.execute("SELECT sub_topic, accepted_answers, hint FROM exercises WHERE id = ?",
                                       (exercise_id,)).fetchone()

    assert saved_row[0] == "a daily stand-up"
    assert json.loads(saved_row[1]) == ["'m working"]
    assert saved_row[2] == "right now"


def test_an_exercise_without_accepted_answers_saves_an_empty_list(database_path):
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)

    with db.connect(database_path) as connection:
        accepted_answers_text = connection.execute("SELECT accepted_answers FROM exercises WHERE id = ?",
                                                   (exercise_id,)).fetchone()[0]

    assert accepted_answers_text == "[]"


def test_get_exercise_sentences_gives_one_skill_newest_first(database_path):
    first_exercise = make_exercise("to_be")
    first_exercise.prompt_text = "I ___ tired."
    second_exercise = make_exercise("to_be")
    second_exercise.prompt_text = "They ___ at home."
    other_skill_exercise = make_exercise("present_simple")
    other_skill_exercise.prompt_text = "She ___ (work) in a bank."

    db.save_exercise(first_exercise, database_path)
    db.save_exercise(second_exercise, database_path)
    db.save_exercise(other_skill_exercise, database_path)

    assert db.get_exercise_sentences("to_be", database_path) == ["They ___ at home.", "I ___ tired."]


def test_get_exercise_sentences_is_empty_for_a_new_skill(database_path):
    assert db.get_exercise_sentences("to_be", database_path) == []


def test_a_practice_exercise_needs_an_exercise_type():
    with pytest.raises(ValidationError, match="exercise_type"):
        Exercise(section="practice", skill_id="to_be", level="A2", prompt_text="I ___ tired.", expected_answer="am")


def test_a_writing_exercise_has_no_exercise_type():
    writing_exercise = Exercise(section="writing", skill_id="writing_general", level="B1",
                                prompt_text="Write an email to your manager.")

    assert writing_exercise.exercise_type is None


# ---------- get_unanswered_exercises ----------

def save_practice_exercise(database_path, skill_id, level, topic, exercise_type, sentence):
    exercise = Exercise(section="practice", exercise_type=exercise_type, skill_id=skill_id, level=level,
                        topic=topic, prompt_text=sentence, expected_answer="am", accepted_answers=["'m"],
                        hint="how you feel")

    return db.save_exercise(exercise, database_path)


def test_get_unanswered_exercises_leaves_out_answered_ones(database_path):
    answered_id = save_practice_exercise(database_path, "to_be", "A2", "travel", "gap", "I ___ tired.")
    unanswered_id = save_practice_exercise(database_path, "to_be", "A2", "travel", "gap", "We ___ late.")
    db.save_attempt(make_wrong_attempt(answered_id, "to_be"), database_path)

    unanswered_exercises = db.get_unanswered_exercises("gap", "A2", "to_be", "travel", database_path)

    assert len(unanswered_exercises) == 1

    exercise_id, exercise = unanswered_exercises[0]

    assert exercise_id == unanswered_id
    assert exercise.prompt_text == "We ___ late."
    assert exercise.accepted_answers == ["'m"]
    assert exercise.exercise_type == "gap"
    assert exercise.created_at.tzinfo is not None


def test_get_unanswered_exercises_filters_type_level_skill_and_topic(database_path):
    wanted_id = save_practice_exercise(database_path, "to_be", "A2", "travel", "gap", "I ___ tired.")
    save_practice_exercise(database_path, "to_be", "A2", "travel", "fix_error", "I have tired.")
    save_practice_exercise(database_path, "to_be", "B1", "travel", "gap", "They ___ at the gate.")
    save_practice_exercise(database_path, "present_simple", "A2", "travel", "gap", "She ___ (work) here.")
    save_practice_exercise(database_path, "to_be", "A2", "meetings", "gap", "We ___ ready.")

    unanswered_exercises = db.get_unanswered_exercises("gap", "A2", "to_be", "travel", database_path)

    assert len(unanswered_exercises) == 1
    assert unanswered_exercises[0][0] == wanted_id


def test_get_unanswered_exercises_with_any_skill_and_any_topic_oldest_first(database_path):
    first_id = save_practice_exercise(database_path, "to_be", "A2", "travel", "gap", "I ___ tired.")
    second_id = save_practice_exercise(database_path, "present_simple", "A2", "meetings", "gap", "She ___ (work).")

    unanswered_exercises = db.get_unanswered_exercises("gap", "A2", None, None, database_path)

    exercise_ids = []

    for exercise_id, exercise in unanswered_exercises:
        exercise_ids.append(exercise_id)

    assert exercise_ids == [first_id, second_id]


def test_save_attempt_needs_an_attempt_model(database_path):
    with pytest.raises(TypeError):
        db.save_attempt({"skill_id": "to_be"}, database_path)


# ---------- save_attempts: all rows of one answer, or none ----------

def make_detected_spelling_attempt(submission_id, exercise_id):
    # "She has finised the report": the detected row of the answer.
    return Attempt(submission_id=submission_id, exercise_id=exercise_id, section="practice", skill_id="spelling",
                   source="detected", your_answer="finised", verdict="wrong", error_type="spelling",
                   mistake_text="finised", correction="finished", graded_by="ai", model="fake-test-model",
                   prompt_version="fake_prompt@000000")


def test_save_attempts_saves_every_row_of_one_answer(database_path):
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)
    targeted_attempt = make_wrong_attempt(exercise_id, "to_be")
    detected_attempt = make_detected_spelling_attempt(targeted_attempt.submission_id, exercise_id)

    new_attempt_ids = db.save_attempts([targeted_attempt, detected_attempt], database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert len(new_attempt_ids) == 2
    assert list(saved_attempts["source"]) == ["targeted", "detected"]
    assert saved_attempts["submission_id"].nunique() == 1
    assert saved_attempts["created_at"].nunique() == 1


def test_save_attempts_saves_nothing_when_one_row_is_refused(database_path):
    # The second row points to an exercise that does not exist: the first row must not stay alone.
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)
    targeted_attempt = make_wrong_attempt(exercise_id, "to_be")
    detected_attempt = make_detected_spelling_attempt(targeted_attempt.submission_id, 999)

    with pytest.raises(sqlite3.IntegrityError):
        db.save_attempts([targeted_attempt, detected_attempt], database_path)

    assert count_rows(database_path, "attempts") == 0


def test_save_attempts_refuses_rows_from_two_answers(database_path):
    exercise_id = db.save_exercise(make_exercise("to_be"), database_path)
    first_attempt = make_wrong_attempt(exercise_id, "to_be")
    second_attempt = make_wrong_attempt(exercise_id, "to_be")

    with pytest.raises(ValueError, match="one submission_id"):
        db.save_attempts([first_attempt, second_attempt], database_path)

    assert count_rows(database_path, "attempts") == 0


def test_save_attempts_refuses_an_empty_list(database_path):
    with pytest.raises(ValueError, match="at least one attempt"):
        db.save_attempts([], database_path)


def test_save_attempts_needs_attempt_models(database_path):
    with pytest.raises(TypeError):
        db.save_attempts([{"skill_id": "to_be"}], database_path)


# ---------- foreign keys ----------

def test_an_attempt_with_an_unknown_exercise_id_is_refused(database_path):
    attempt = make_wrong_attempt(999, "to_be")

    with pytest.raises(sqlite3.IntegrityError):
        db.save_attempt(attempt, database_path)


def test_the_database_refuses_an_unknown_skill_id_even_without_pydantic(database_path):
    # Pydantic already refuses it (next test). This proves the database refuses it too.
    with pytest.raises(sqlite3.IntegrityError):
        with db.connect(database_path) as connection:
            connection.execute("INSERT INTO lesson_events (skill_id, opened_at) VALUES ('invented_skill', '2026')")


# ---------- Attempt rules ----------

def test_attempt_refuses_an_unknown_skill_id():
    with pytest.raises(ValidationError, match="unknown skill id"):
        make_wrong_attempt(1, "invented_skill")


def test_attempt_refuses_an_unknown_field():
    valid_attempt_values = make_wrong_attempt(1, "to_be").model_dump()
    valid_attempt_values["verdikt"] = "wrong"

    with pytest.raises(ValidationError):
        Attempt(**valid_attempt_values)


def test_attempt_refuses_a_value_outside_the_allowed_list():
    attempt_values = make_wrong_attempt(1, "to_be").model_dump()
    attempt_values["verdict"] = "almost"

    with pytest.raises(ValidationError):
        Attempt(**attempt_values)


def test_a_wrong_answer_needs_an_error_type():
    attempt_values = make_wrong_attempt(1, "to_be").model_dump()
    attempt_values["error_type"] = None

    with pytest.raises(ValidationError, match="needs an error type"):
        Attempt(**attempt_values)


def test_a_correct_answer_cannot_have_a_grammar_error():
    attempt_values = make_wrong_attempt(1, "to_be").model_dump()
    attempt_values["verdict"] = "correct"

    with pytest.raises(ValidationError, match="correct answer"):
        Attempt(**attempt_values)


def test_naturalness_is_a_correct_detected_row():
    attempt_values = make_wrong_attempt(1, "word_choice").model_dump()
    attempt_values["verdict"] = "correct"
    attempt_values["error_type"] = "naturalness"
    attempt_values["source"] = "detected"

    naturalness_attempt = Attempt(**attempt_values)

    assert naturalness_attempt.error_type == "naturalness"


def test_naturalness_cannot_be_targeted():
    attempt_values = make_wrong_attempt(1, "word_choice").model_dump()
    attempt_values["verdict"] = "correct"
    attempt_values["error_type"] = "naturalness"

    with pytest.raises(ValidationError, match="always detected"):
        Attempt(**attempt_values)


def test_graded_by_code_has_no_model_and_no_prompt_version():
    attempt_values = make_wrong_attempt(1, "to_be").model_dump()
    attempt_values["graded_by"] = "code"

    with pytest.raises(ValidationError, match="graded by code"):
        Attempt(**attempt_values)


def test_graded_by_ai_needs_model_and_prompt_version():
    attempt_values = make_wrong_attempt(1, "to_be").model_dump()
    attempt_values["prompt_version"] = None

    with pytest.raises(ValidationError, match="graded by ai"):
        Attempt(**attempt_values)


def test_a_date_without_time_zone_is_refused():
    attempt_values = make_wrong_attempt(1, "to_be").model_dump()
    attempt_values["created_at"] = datetime(2026, 11, 16, 21, 0)

    with pytest.raises(ValidationError, match="time zone"):
        Attempt(**attempt_values)
