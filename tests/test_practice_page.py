"""Tests for the Practice page (pages/practice.py) with Streamlit's AppTest: the page runs with no browser.

A temporary database with 5 saved sentences (the stock, so no refill), and a FAKE llm.ask(): no internet, no quota.
AppTest runs the page in the same Python process, so the monkeypatch changes below reach the page too.
"""

import pytest
from streamlit.testing.v1 import AppTest

from tutor import db, grading, llm, skills
from tutor.schemas import Exercise

PAGE_PATH = str(db.PROJECT_FOLDER / "pages" / "practice.py")

STOCK_SENTENCES = ["I ___ (be) tired today.", "I ___ (be) at home now.", "I ___ (be) ready for the trip.",
                   "I ___ (be) hungry after work.", "I ___ (be) in Lisbon this week."]

WRONG_GRADE = {"verdict": "wrong", "error_type": "grammar", "mistake_text": "I is", "correction": "I am",
               "why_wrong": "With I, the verb be is am.", "rule": "I am, you are, he is.",
               "corrected_sentence": "I am tired today.", "memory_tip": "I am = eu sou / eu estou."}


# ---------- helpers ----------

class FakeAsk:
    """Replaces llm.ask(). Each planned result is a dict (validated with the schema it receives) or an exception.
    With no planned result left, the AI is "busy": an unplanned request never reaches the internet."""

    def __init__(self, planned_results):
        self.planned_results = list(planned_results)
        self.request_count = 0

    def ask(self, prompt_text, prompt_version, schema, task, budget=None, settings=None):
        self.request_count = self.request_count + 1

        if len(self.planned_results) == 0:
            raise llm.AIUnavailableError("The AI is busy. Try again in a minute.")

        planned_result = self.planned_results.pop(0)

        if isinstance(planned_result, Exception):
            raise planned_result

        return schema(**planned_result), "fake-test-model"


def install_fake_ask(monkeypatch, planned_results):
    fake_ask = FakeAsk(planned_results)
    monkeypatch.setattr(llm, "ask", fake_ask.ask)

    return fake_ask


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    # The page reads db.DEFAULT_DATABASE_PATH at call time, so it uses this temporary database.
    temporary_database_path = tmp_path / "test_tutor.db"
    db.init_db(temporary_database_path)
    monkeypatch.setattr(db, "DEFAULT_DATABASE_PATH", temporary_database_path)
    monkeypatch.setattr(grading, "GRADING_PROBLEMS_LOG_PATH", tmp_path / "grading_problems.jsonl")

    for sentence in STOCK_SENTENCES:
        exercise = Exercise(section="practice", exercise_type="gap", skill_id="to_be", level="A2", topic="travel",
                            prompt_text=sentence, expected_answer="am", accepted_answers=["'m"],
                            hint="How do you feel?")
        db.save_exercise(exercise, temporary_database_path)

    return temporary_database_path


def open_page():
    page = AppTest.from_file(PAGE_PATH, default_timeout=15)
    page.run()

    return page


def answer(page, answer_text):
    page.text_input[0].input(answer_text)
    page.button(key="practice_check").click()
    page.run()


def get_caption_text(page):
    caption_texts = []

    for caption in page.caption:
        caption_texts.append(caption.value)

    return " | ".join(caption_texts)


def count_attempts(database_path):
    return len(db.get_attempts(database_path=database_path))


# ---------- opening the page ----------

def test_the_page_opens_with_a_sentence_from_the_stock_and_no_ai_call(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [])

    page = open_page()

    assert len(page.exception) == 0
    assert page.session_state["practice_exercise"].prompt_text in STOCK_SENTENCES
    assert page.selectbox(key="practice_level").value == "A2"
    assert fake_ask.request_count == 0


def test_any_skill_hides_the_skill_name_until_i_answer(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [])
    skill_name = skills.get_skill("to_be")["name"]
    page = open_page()

    assert skill_name not in get_caption_text(page)

    answer(page, "am")

    assert skill_name in get_caption_text(page)


def test_choosing_a_b1_skill_moves_the_level_to_b1(database_path, monkeypatch):
    # No B1 sentence in the stock and a busy AI: the page shows the error with "Try again", never a crash.
    install_fake_ask(monkeypatch, [])
    page = open_page()

    page.selectbox(key="practice_skill_id").set_value("present_perfect").run()

    assert page.selectbox(key="practice_level").value == "B1"
    assert "A2" not in page.selectbox(key="practice_level").options
    assert len(page.exception) == 0
    assert "busy" in page.error[0].value
    assert page.button(key="practice_try_again_load") is not None


# ---------- answering ----------

def test_an_exact_answer_is_green_and_saved_once(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [])
    page = open_page()

    answer(page, "am")
    page.run()

    saved_attempts = db.get_attempts(database_path=database_path)

    assert page.success[0].value.startswith("**Correct!**")
    assert fake_ask.request_count == 0
    assert len(saved_attempts) == 1
    assert saved_attempts.loc[0, "skill_id"] == "to_be"
    assert saved_attempts.loc[0, "submission_id"] == page.session_state["practice_submission_id"]
    assert not saved_attempts.loc[0, "hint_used"]
    assert saved_attempts.loc[0, "seconds_taken"] >= 0
    assert "1 answer · 1 correct" in get_caption_text(page)


def test_the_hint_is_shown_and_saved_with_the_answer(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [])
    page = open_page()

    page.button(key="practice_hint").click().run()

    assert "How do you feel?" in page.info[0].value

    answer(page, "am")

    assert db.get_attempts(database_path=database_path).loc[0, "hint_used"]


def test_an_empty_answer_is_not_checked(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [])
    page = open_page()

    answer(page, "   ")

    assert page.warning[0].value == "Type an answer first."
    assert count_attempts(database_path) == 0


def test_a_wrong_answer_graded_by_the_ai_shows_the_three_parts(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [WRONG_GRADE])
    page = open_page()

    answer(page, "is")

    result_text = page.error[0].value
    saved_attempts = db.get_attempts(database_path=database_path)

    assert result_text.startswith("**Not quite**")
    assert "You wrote: **I is**" in result_text
    assert "Why: With I, the verb be is am." in result_text
    assert "Rule: I am, you are, he is." in result_text
    assert len(saved_attempts) == 1
    assert saved_attempts.loc[0, "verdict"] == "wrong"
    assert saved_attempts.loc[0, "graded_by"] == "ai"


def test_an_ai_error_while_grading_saves_nothing_and_check_works_again(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, [llm.AIUnavailableError("The AI is busy."), WRONG_GRADE])
    page = open_page()

    answer(page, "is")

    assert "not saved" in page.error[0].value
    assert count_attempts(database_path) == 0

    answer(page, "is")

    assert page.error[0].value.startswith("**Not quite**")
    assert count_attempts(database_path) == 1
    assert fake_ask.request_count == 2


def test_next_shows_another_sentence(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [])
    page = open_page()
    first_exercise_id = page.session_state["practice_exercise_id"]

    answer(page, "am")
    page.button(key="practice_next").click().run()

    assert page.session_state["practice_exercise_id"] != first_exercise_id
    assert page.session_state["practice_result"] is None
    assert count_attempts(database_path) == 1


# ---------- reporting a problem ----------

def test_skip_a_bad_sentence_saves_a_report_and_takes_it_out_of_the_stock(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [])
    page = open_page()
    bad_exercise_id = page.session_state["practice_exercise_id"]

    page.button(key="practice_skip_bad_sentence").click().run()

    saved_reports = db.get_problem_reports(database_path)
    stock_exercise_ids = []

    for exercise_id, exercise in db.get_unanswered_exercises("gap", "A2", None, None, database_path):
        stock_exercise_ids.append(exercise_id)

    assert len(page.exception) == 0
    assert len(saved_reports) == 1
    assert saved_reports.loc[0, "exercise_id"] == bad_exercise_id
    assert saved_reports.loc[0, "kind"] == "bad_sentence"
    assert saved_reports.loc[0, "your_answer"] == ""
    assert bad_exercise_id not in stock_exercise_ids
    assert page.session_state["practice_exercise_id"] != bad_exercise_id
    assert count_attempts(database_path) == 0
    assert "0 answers" in get_caption_text(page)
    assert "will not come back" in get_caption_text(page)

def test_a_bad_sentence_report_is_saved_once_with_my_answer(database_path, monkeypatch):
    install_fake_ask(monkeypatch, [])
    page = open_page()
    exercise_id = page.session_state["practice_exercise_id"]
    submission_id = page.session_state["practice_submission_id"]

    answer(page, "am")
    page.radio(key="practice_report_kind_" + submission_id).set_value("bad_sentence")
    page.text_input(key="practice_report_comment_" + submission_id).input("two answers fit")
    page.button(key="practice_send_report").click().run()
    page.button(key="practice_send_report").click().run()

    saved_reports = db.get_problem_reports(database_path)

    assert len(saved_reports) == 1
    assert saved_reports.loc[0, "exercise_id"] == exercise_id
    assert saved_reports.loc[0, "kind"] == "bad_sentence"
    assert saved_reports.loc[0, "your_answer"] == "am"
    assert saved_reports.loc[0, "comment"] == "two answers fit"
    assert "Saved: " in get_caption_text(page)
