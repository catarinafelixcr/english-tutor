"""Tests for tutor/db.py and the Exercise / Attempt models.

Every test uses a temporary database, never data/tutor.db.
"""

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
    return Exercise(section="practice", skill_id=skill_id, level="A2", topic="daily life",
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


def test_save_attempt_needs_an_attempt_model(database_path):
    with pytest.raises(TypeError):
        db.save_attempt({"skill_id": "to_be"}, database_path)


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
