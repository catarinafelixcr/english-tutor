"""Tests for grading.grade_gap_answer(): code first, then the AI, and every row saved.

A temporary database and a FAKE llm.ask(): no internet, no quota.
"""

import json
import threading

import pytest

from tutor import db, grading, llm, prompts
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


# ---------- in code, no AI: the trap (Step 2, Part 3b) ----------

MISS_SENTENCE = "Hurry up, or we will ___ (perder) the last train."
MISS_TRAP_WHY = "You lose an object, but you miss a bus or a train that leaves without you: miss the train."


def save_exercise_with_trap(database_path):
    exercise = Exercise(section="practice", exercise_type="gap", skill_id="word_choice", level="B1", topic="travel",
                        prompt_text=MISS_SENTENCE, expected_answer="miss", trap="lose", trap_why=MISS_TRAP_WHY)
    exercise_id = db.save_exercise(exercise, database_path)

    return exercise_id, exercise


@pytest.mark.parametrize("your_answer", ["lose", " Lose. "])
def test_the_trap_is_graded_wrong_by_code_with_its_reason(database_path, monkeypatch, your_answer):
    fake_ask = install_fake_ask(monkeypatch, [])
    exercise_id, exercise = save_exercise_with_trap(database_path)

    result = grading.grade_gap_answer(exercise_id, exercise, your_answer, False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert fake_ask.prompts_received == []
    assert result.state == "wrong"
    assert result.graded_by == "code"
    assert result.why_wrong == MISS_TRAP_WHY
    assert result.rule == ""
    assert result.correction == "miss"
    assert result.corrected_sentence == "Hurry up, or we will miss the last train."
    assert len(saved_attempts) == 1
    assert saved_attempts.loc[0, "verdict"] == "wrong"
    assert saved_attempts.loc[0, "graded_by"] == "code"
    assert saved_attempts.loc[0, "error_type"] == "vocabulary"
    assert saved_attempts.loc[0, "mistake_text"] == your_answer.strip().rstrip(".")
    assert saved_attempts.loc[0, "correction"] == "miss"
    assert MISS_TRAP_WHY in saved_attempts.loc[0, "explanation"]


def test_an_answer_that_is_not_the_trap_still_goes_to_the_ai(database_path, monkeypatch):
    wrong_grade = {"verdict": "wrong", "error_type": "vocabulary", "mistake_text": "loose", "correction": "miss",
                   "why_wrong": "You wrote 'loose': it means not tight.", "rule": "miss a train",
                   "corrected_sentence": "Hurry up, or we will miss the last train."}
    fake_ask = install_fake_ask(monkeypatch, [wrong_grade])
    exercise_id, exercise = save_exercise_with_trap(database_path)

    result = grading.grade_gap_answer(exercise_id, exercise, "loose", False, 6.0, "English", database_path)

    assert len(fake_ask.prompts_received) == 1
    assert result.graded_by == "ai"


def test_an_old_exercise_without_a_trap_goes_to_the_ai(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [partial_grade("has write")])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    grading.grade_gap_answer(exercise_id, exercise, "write", False, 8.0, "English", database_path)

    assert len(fake_ask.prompts_received) == 1


@pytest.mark.parametrize("skill_id, error_type", [("word_choice", "vocabulary"), ("make_do", "vocabulary"),
                                                  ("adverb_position", "word_order"), ("spelling", "spelling"),
                                                  ("present_simple", "grammar")])
def test_the_trap_error_type_comes_from_the_skill_category(skill_id, error_type):
    assert grading.choose_trap_error_type(skill_id) == error_type


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
    assert read_problems(database_path) == ["bad_quotes", "retry_failed", "quote_fallback",
                                            "corrected_sentence_mismatch"]
    assert len(db.get_attempts(database_path=database_path)) == 1


# ---------- one slip, one skill (the grade demo, 2026-11-16) ----------

def writed_counted_twice():
    # What Gemini really answered for "writed": a wrong verdict AND a detected irregular_verbs on the same word.
    return {"verdict": "wrong", "error_type": "grammar", "mistake_text": "writed", "correction": "written",
            "why_wrong": "You wrote 'writed', but write is irregular.", "rule": "write → written.",
            "corrected_sentence": "She has written the report already.",
            "detected_mistake": {"skill_id": "irregular_verbs", "error_type": "grammar", "mistake_text": "writed",
                                 "correction": "written"}}


def writed_counted_once():
    return {"verdict": "correct", "corrected_sentence": "She has written the report already.",
            "detected_mistake": {"skill_id": "irregular_verbs", "error_type": "grammar", "mistake_text": "writed",
                                 "correction": "written"}}


def test_the_same_words_twice_are_retried_with_a_note(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [writed_counted_twice(), writed_counted_once()])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "writed", False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert len(fake_ask.prompts_received) == 2
    assert fake_ask.prompts_received[1].endswith(prompts.GAP_GRADE_SAME_WORDS_RETRY_NOTE)
    assert result.state == "almost"
    assert list(saved_attempts["verdict"]) == ["correct", "wrong"]
    assert read_problems(database_path) == ["same_words_twice"]


def test_the_same_words_twice_again_keep_the_verdict_and_drop_the_detected_row(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [writed_counted_twice(), writed_counted_twice()])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "writed", False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert result.state == "wrong"
    assert result.detected_skill_id == ""
    assert list(saved_attempts["skill_id"]) == ["present_perfect"]
    assert "detected_mistake_dropped" in read_problems(database_path)


def test_a_detected_slip_on_other_words_is_kept(database_path, monkeypatch):
    # "She has writes the reprot": the main mistake and a spelling slip on ANOTHER word. Both rows are right.
    wrong_with_typo = partial_grade("has writes")
    wrong_with_typo["verdict"] = "wrong"
    wrong_with_typo["corrected_sentence"] = "She has written the report already."
    wrong_with_typo["detected_mistake"] = {"skill_id": "spelling", "error_type": "spelling", "mistake_text": "reprot",
                                           "correction": "report"}
    fake_ask = install_fake_ask(monkeypatch, [wrong_with_typo])
    sentence = "She has ___ (write) the reprot already."
    exercise_id, exercise = save_exercise(database_path, "present_perfect", sentence, "written")

    grading.grade_gap_answer(exercise_id, exercise, "writes", False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert len(fake_ask.prompts_received) == 1
    assert list(saved_attempts["skill_id"]) == ["present_perfect", "spelling"]


# ---------- note: only for a correct answer with no slip ----------

def test_a_note_on_a_wrong_answer_is_ignored(database_path, monkeypatch):
    wrong_with_note = partial_grade("has writes")
    wrong_with_note["verdict"] = "wrong"
    wrong_with_note["note"] = "Please provide a valid past participle."
    install_fake_ask(monkeypatch, [wrong_with_note])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "writes", False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert result.note == ""
    assert "Please provide" not in saved_attempts.loc[0, "explanation"]


def test_a_note_next_to_a_slip_is_not_shown(database_path, monkeypatch):
    spelling_with_note = writed_counted_once()
    spelling_with_note["detected_mistake"] = {"skill_id": "spelling", "error_type": "spelling",
                                              "mistake_text": "writen", "correction": "written"}
    spelling_with_note["note"] = "Your answer is correct, with a small spelling slip."
    install_fake_ask(monkeypatch, [spelling_with_note])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")

    result = grading.grade_gap_answer(exercise_id, exercise, "writen", False, 6.0, "English", database_path)
    saved_attempts = db.get_attempts(database_path=database_path)

    assert result.note == ""
    assert result.reminder == "Check the spelling: writen → written."
    assert saved_attempts.loc[0, "explanation"] == ""


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


# ---------- one answer is never saved twice (Step 2, Part 3) ----------

def test_the_same_answer_graded_twice_is_refused_before_the_ai_call(database_path, monkeypatch):
    # A double click on Check: the second grading stops BEFORE the AI, so no request is spent.
    fake_ask = install_fake_ask(monkeypatch, [partial_grade("has write")])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")
    submission_id = db.new_submission_id()

    first_result = grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path,
                                            submission_id)

    with pytest.raises(db.AnswerAlreadySavedError):
        grading.grade_gap_answer(exercise_id, exercise, "write", False, 7.0, "English", database_path, submission_id)

    saved_attempts = db.get_attempts(database_path=database_path)

    assert first_result.submission_id == submission_id
    assert len(fake_ask.prompts_received) == 1
    assert len(saved_attempts) == 1
    assert saved_attempts.loc[0, "seconds_taken"] == 6.0


def test_the_same_exact_match_graded_twice_is_saved_once(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [])
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")
    submission_id = db.new_submission_id()

    grading.grade_gap_answer(exercise_id, exercise, "written", False, 6.0, "English", database_path, submission_id)

    with pytest.raises(db.AnswerAlreadySavedError):
        grading.grade_gap_answer(exercise_id, exercise, "written", False, 6.0, "English", database_path,
                                 submission_id)

    assert len(db.get_attempts(database_path=database_path)) == 1


def test_two_gradings_at_the_same_moment_save_the_answer_once(database_path, monkeypatch):
    # A rerun while the AI is grading: Streamlit starts a second run, and the first one can still finish.
    # The barrier holds both threads inside the fake AI call, so BOTH have passed the first check
    # (is_answer_saved) before either one saves. Only the lock in save_attempts() can stop the second one.
    both_threads_are_grading = threading.Barrier(2, timeout=10)

    def slow_fake_ask(prompt_text, prompt_version, schema, task, budget=None, settings=None):
        both_threads_are_grading.wait()
        return schema(**partial_grade("has write")), "fake-test-model"

    monkeypatch.setattr(llm, "ask", slow_fake_ask)
    exercise_id, exercise = save_exercise(database_path, "present_perfect", WRITE_SENTENCE, "written")
    submission_id = db.new_submission_id()
    outcomes = []

    def grade_in_a_thread():
        try:
            grading.grade_gap_answer(exercise_id, exercise, "write", False, 6.0, "English", database_path,
                                     submission_id)
            outcomes.append("saved")
        except db.AnswerAlreadySavedError:
            outcomes.append("already saved")

    first_thread = threading.Thread(target=grade_in_a_thread)
    second_thread = threading.Thread(target=grade_in_a_thread)
    first_thread.start()
    second_thread.start()
    first_thread.join(timeout=20)
    second_thread.join(timeout=20)

    assert sorted(outcomes) == ["already saved", "saved"]
    assert len(db.get_attempts(database_path=database_path)) == 1
