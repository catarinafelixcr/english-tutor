"""Tests for grading.grade_gap_answer(): code first, then the AI, and every row saved.

A temporary database and a FAKE llm.ask(): no internet, no quota.
"""

import json

import pytest

from tutor import db, grading, llm
from tutor.schemas import Exercise

WRITE_SENTENCE = "She has ___ (write) the report already."


# ---------- helpers ----------

@pytest.fixture
def database_path(tmp_path, monkeypatch):
    # A new database and a new problems log for each test.
    monkeypatch.setattr(grading, "GRADING_PROBLEMS_LOG_PATH", tmp_path / "grading_problems.jsonl")
    temporary_database_path = tmp_path / "test_tutor.db"
    db.init_db(temporary_database_path)

    return temporary_database_path


def save_exercise(database_path, skill_id, sentence, expected_answer):
    exercise = Exercise(section="practice", exercise_type="gap", skill_id=skill_id, level="A2", topic="work",
                        prompt_text=sentence, expected_answer=expected_answer)
    exercise_id = db.save_exercise(exercise, database_path)

    return exercise_id, exercise


class FakeAsk:
    """Replaces llm.ask(). Each planned result is a dict (validated with the schema it receives, like the real
    parse()) or an exception to raise. It remembers the prompts and the budgets it received."""

    def __init__(self, planned_results):
        self.planned_results = list(planned_results)
        self.prompts_received = []
        self.budgets_received = []

    def ask(self, prompt_text, prompt_version, schema, task, budget=None, settings=None):
        self.prompts_received.append(prompt_text)
        self.budgets_received.append(budget)
        planned_result = self.planned_results.pop(0)

        if isinstance(planned_result, Exception):
            raise planned_result

        return schema(**planned_result), "fake-test-model"


def install_fake_ask(monkeypatch, planned_results):
    fake_ask = FakeAsk(planned_results)
    monkeypatch.setattr(llm, "ask", fake_ask.ask)

    return fake_ask


def read_problems(database_path):
    problems_log_path = database_path.parent / "grading_problems.jsonl"

    if not problems_log_path.exists():
        return []

    problem_names = []

    for problem_text in problems_log_path.read_text(encoding="utf-8").splitlines():
        problem_names.append(json.loads(problem_text)["problem"])

    return problem_names


def partial_grade(mistake_text):
    # "She has write the report already.": has, but no past participle.
    return {"verdict": "partial", "error_type": "grammar", "mistake_text": mistake_text, "correction": "has written",
            "why_wrong": "You wrote 'has write': after 'has' we need the past participle.",
            "rule": "has + past participle: has written.", "corrected_sentence": "She has written the report already.",
            "memory_tip": "write → wrote → written"}


# ---------- in code, no AI ----------

def test_an_exact_match_is_graded_by_code_with_no_ai_call(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, " Written ", False, 8.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert fake_ask.prompts_received == []
    assert result.state == "correct"
    assert result.graded_by == "code"
    assert result.corrected_sentence == "She has written the report already."
    assert len(saved_attempts) == 1
    assert saved_attempts.loc[0, "graded_by"] == "code"
    assert saved_attempts.loc[0, "verdict"] == "correct"


def test_a_capitalization_slip_saves_two_rows_with_no_ai_call(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [])
    exercise_id, exercise = save_exercise(database_path, "to_be", "___ (be) your office in Lisbon?", "Is")

    result = grading.grade_gap_answer(exercise_id, exercise, "is", False, 5.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert fake_ask.prompts_received == []
    assert result.state == "correct"
    assert "is → Is" in result.reminder
    assert list(saved_attempts["skill_id"]) == ["to_be", "capitalization"]
    assert list(saved_attempts["verdict"]) == ["correct", "wrong"]
    assert list(saved_attempts["source"]) == ["targeted", "detected"]
    assert saved_attempts["submission_id"].nunique() == 1


# ---------- with the AI: the four states ----------

def test_a_spelling_slip_is_green_with_a_reminder_and_a_detected_row(database_path, monkeypatch):
    spelling_grade = {"verdict": "correct", "corrected_sentence": "She has written the report already.",
                      "detected_mistake": {"skill_id": "spelling", "error_type": "spelling", "mistake_text": "writen",
                                           "correction": "written"}}
    install_fake_ask(monkeypatch, [spelling_grade])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "writen", False, 9.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert result.state == "correct"
    assert result.reminder == "Check the spelling: writen → written."
    assert list(saved_attempts["skill_id"]) == ["present_perfect", "spelling"]
    assert list(saved_attempts["verdict"]) == ["correct", "wrong"]
    assert list(saved_attempts["graded_by"]) == ["ai", "ai"]
    assert list(saved_attempts["model"]) == ["fake-test-model", "fake-test-model"]
    assert saved_attempts.loc[0, "prompt_version"].startswith("gap_grade@")


def test_a_wrong_irregular_form_is_almost(database_path, monkeypatch):
    writed_grade = {"verdict": "correct", "corrected_sentence": "She has written the report already.",
                    "detected_mistake": {"skill_id": "irregular_verbs", "error_type": "grammar",
                                         "mistake_text": "writed", "correction": "written"}}
    install_fake_ask(monkeypatch, [writed_grade])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "writed", False, 9.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert result.state == "almost"
    assert result.detected_skill_id == "irregular_verbs"
    assert result.reminder == ""
    assert list(saved_attempts["skill_id"]) == ["present_perfect", "irregular_verbs"]


def test_a_partial_answer_saves_the_three_parts_in_explanation(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [partial_grade("has write")])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "write", True, 15.5, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)
    saved_attempt = saved_attempts.loc[0]

    assert result.state == "partial"
    assert len(saved_attempts) == 1
    assert saved_attempt["mistake_text"] == "has write"
    assert saved_attempt["correction"] == "has written"
    assert saved_attempt["explanation"].startswith("You wrote: has write\nWhy: ")
    assert "\nRule: has + past participle" in saved_attempt["explanation"]
    assert bool(saved_attempt["hint_used"]) is True
    assert saved_attempt["seconds_taken"] == 15.5


def test_a_wrong_answer_is_red(database_path, monkeypatch):
    wrong_grade = partial_grade("has writes")
    wrong_grade["verdict"] = "wrong"
    install_fake_ask(monkeypatch, [wrong_grade])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "writes", False, 7.0, "English", database_path)

    assert result.state == "wrong"
    assert result.mistake_text == "has writes"


def test_an_also_right_answer_saves_the_note_as_explanation(database_path, monkeypatch):
    also_right_grade = {"verdict": "correct", "note": "'finished' is also natural here.",
                        "corrected_sentence": "She has finished the report already."}
    install_fake_ask(monkeypatch, [also_right_grade])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "finished", False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert result.state == "correct"
    assert result.note == "'finished' is also natural here."
    assert saved_attempts.loc[0, "explanation"] == "'finished' is also natural here."
    assert read_problems(database_path) == []


# ---------- bad quotes: one retry, then my answer ----------

def test_a_bad_quote_is_retried_once_with_a_note_and_the_same_budget(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [partial_grade("have write"), partial_grade("has write")])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path)

    assert len(fake_ask.prompts_received) == 2
    assert "\"have write\"" in fake_ask.prompts_received[1]
    assert fake_ask.budgets_received[0] is fake_ask.budgets_received[1]
    assert result.mistake_text == "has write"
    assert read_problems(database_path) == ["bad_quotes"]


def test_two_bad_quotes_use_my_answer_and_are_logged(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [partial_grade("have write"), partial_grade("had write")])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert len(fake_ask.prompts_received) == 2
    assert result.mistake_text == "write"
    assert saved_attempts.loc[0, "mistake_text"] == "write"
    assert "quote_fallback" in read_problems(database_path)


def test_a_failed_quote_retry_keeps_the_first_grade(database_path, monkeypatch):
    planned_results = [partial_grade("have write"), llm.AIUnavailableError("The AI is busy.")]
    install_fake_ask(monkeypatch, planned_results)
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path)

    assert result.state == "partial"
    assert result.mistake_text == "write"
    # The fallback quote "write" + the correction "has written" gives "has has written": a 4th problem, as expected.
    assert read_problems(database_path) == ["bad_quotes", "quote_retry_failed", "quote_fallback",
                                            "corrected_sentence_mismatch"]
    assert len(db.get_attempts(database_path=database_path)) == 1


# ---------- corrected_sentence and AI errors ----------

def test_a_corrected_sentence_that_does_not_match_is_only_logged(database_path, monkeypatch):
    changed_grade = partial_grade("has write")
    changed_grade["corrected_sentence"] = "She has already written the whole report."
    fake_ask = install_fake_ask(monkeypatch, [changed_grade])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path)

    assert len(fake_ask.prompts_received) == 1
    assert result.state == "partial"
    assert read_problems(database_path) == ["corrected_sentence_mismatch"]


def test_an_ai_error_saves_nothing_and_goes_up_to_the_page(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [llm.AIUnavailableError("The AI is busy.")])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    with pytest.raises(llm.AIUnavailableError):
        grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path)

    assert len(db.get_attempts(database_path=database_path)) == 0


def test_the_prompt_gets_my_full_sentence_without_the_bracket(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [partial_grade("has write")])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path)

    assert "The learner's full sentence: She has write the report already." in fake_ask.prompts_received[0]
