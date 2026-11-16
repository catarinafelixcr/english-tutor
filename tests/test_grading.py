"""Tests for tutor/grading.py. The code check needs no AI and no database."""

import pytest

from tutor import grading
from tutor.schemas import Exercise


def make_exercise(expected_answer, accepted_answers):
    return Exercise(section="practice", exercise_type="gap", skill_id="present_simple", level="A2",
                    prompt_text="She ___ (go) to work by bus.", expected_answer=expected_answer,
                    accepted_answers=accepted_answers)


# ---------- clean_answer ----------

def test_clean_answer_keeps_capital_letters():
    assert grading.clean_answer("Monday") == "Monday"


def test_clean_answer_removes_extra_spaces():
    assert grading.clean_answer("  has   finished ") == "has finished"


def test_clean_answer_turns_curly_apostrophes_into_straight_ones():
    assert grading.clean_answer("doesn’t") == "doesn't"
    assert grading.clean_answer("doesn‘t") == "doesn't"


def test_clean_answer_removes_a_final_full_stop_or_comma():
    assert grading.clean_answer("goes.") == "goes"
    assert grading.clean_answer("goes,") == "goes"
    assert grading.clean_answer("goes .") == "goes"


def test_clean_answer_keeps_punctuation_inside_the_answer():
    assert grading.clean_answer("e.g. this") == "e.g. this"


# ---------- check_answer_in_code: exact match ----------

def test_the_expected_answer_is_an_exact_match():
    exercise = make_exercise("goes", [])

    assert grading.check_answer_in_code("goes", exercise) == (grading.EXACT_MATCH, "goes")


def test_an_accepted_answer_is_an_exact_match():
    exercise = make_exercise("is working", ["'s working"])

    assert grading.check_answer_in_code("'s working", exercise) == (grading.EXACT_MATCH, "'s working")


def test_spaces_and_a_final_full_stop_do_not_matter():
    exercise = make_exercise("has finished", [])

    result, matched_answer = grading.check_answer_in_code("  has  finished. ", exercise)

    assert result == grading.EXACT_MATCH


def test_a_curly_apostrophe_matches_a_straight_one():
    exercise = make_exercise("doesn't", [])

    result, matched_answer = grading.check_answer_in_code("doesn’t", exercise)

    assert result == grading.EXACT_MATCH


def test_a_straight_apostrophe_matches_a_curly_one_in_the_expected_answer():
    exercise = make_exercise("doesn’t", [])

    result, matched_answer = grading.check_answer_in_code("doesn't", exercise)

    assert result == grading.EXACT_MATCH


def test_a_capital_letter_i_added_myself_is_still_an_exact_match():
    exercise = make_exercise("goes", [])

    result, matched_answer = grading.check_answer_in_code("Goes", exercise)

    assert result == grading.EXACT_MATCH


# ---------- check_answer_in_code: capitalization slip ----------

def test_a_missing_capital_letter_is_a_capitalization_slip():
    exercise = make_exercise("on Monday", [])

    assert grading.check_answer_in_code("on monday", exercise) == (grading.CAPITALIZATION_SLIP, "on Monday")


def test_a_small_i_is_a_capitalization_slip():
    exercise = make_exercise("I am", ["I'm"])

    assert grading.check_answer_in_code("i'm", exercise) == (grading.CAPITALIZATION_SLIP, "I'm")


def test_an_accepted_answer_with_no_missing_capital_wins_over_a_slip():
    # "english" matches the expected answer with a slip, but the accepted answer exactly: exact wins.
    exercise = make_exercise("English", ["english"])

    assert grading.check_answer_in_code("english", exercise) == (grading.EXACT_MATCH, "english")


# ---------- check_answer_in_code: no match ----------

def test_a_different_answer_is_no_match():
    exercise = make_exercise("goes", ["is going"])

    assert grading.check_answer_in_code("go", exercise) == (grading.NO_MATCH, None)


def test_a_spelling_slip_is_no_match_so_the_ai_decides():
    exercise = make_exercise("has finished", [])

    assert grading.check_answer_in_code("has finised", exercise) == (grading.NO_MATCH, None)


# ---------- check_answer_in_code: guard clauses ----------

def test_an_empty_answer_is_refused():
    exercise = make_exercise("goes", [])

    with pytest.raises(ValueError, match="empty"):
        grading.check_answer_in_code("  . ", exercise)


def test_an_exercise_without_an_expected_answer_is_refused():
    exercise = Exercise(section="writing", skill_id="writing_general", level="A2", prompt_text="My weekend")

    with pytest.raises(ValueError, match="no expected answer"):
        grading.check_answer_in_code("I went to the beach.", exercise)
