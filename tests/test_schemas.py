"""Tests for the AI answer models in tutor/schemas.py (GapExercise)."""

import pytest
from pydantic import ValidationError

from tutor.schemas import GapExercise


def make_gap_exercise_values():
    return {"sentence": "She ___ (work) in a bank.", "expected_answer": "works", "accepted_answers": [],
            "skill_id": "present_simple", "hint": "he / she / it", "level": "A2"}


def test_a_good_gap_exercise_is_accepted():
    gap_exercise = GapExercise(**make_gap_exercise_values())

    assert gap_exercise.expected_answer == "works"


def test_expected_answer_spaces_are_removed():
    exercise_values = make_gap_exercise_values()
    exercise_values["expected_answer"] = "  works "

    gap_exercise = GapExercise(**exercise_values)

    assert gap_exercise.expected_answer == "works"


@pytest.mark.parametrize("bad_sentence", [
    "She works in a bank.",              # no gap
    "She ___ in a ___.",                 # two gaps
    "She ____ (work) in a bank.",        # four underscores
    "Check the user_id and ___ again.",  # another underscore
])
def test_a_sentence_without_exactly_one_gap_is_refused(bad_sentence):
    exercise_values = make_gap_exercise_values()
    exercise_values["sentence"] = bad_sentence

    with pytest.raises(ValidationError, match="exactly one gap"):
        GapExercise(**exercise_values)


def test_an_empty_expected_answer_is_refused():
    exercise_values = make_gap_exercise_values()
    exercise_values["expected_answer"] = "   "

    with pytest.raises(ValidationError, match="empty"):
        GapExercise(**exercise_values)


@pytest.mark.parametrize("bad_skill_id", ["invented_skill", "listening", "writing_general", "capitalization"])
def test_a_skill_that_cannot_be_used_in_fill_the_gap_is_refused(bad_skill_id):
    exercise_values = make_gap_exercise_values()
    exercise_values["skill_id"] = bad_skill_id

    with pytest.raises(ValidationError, match="cannot be used in fill the gap"):
        GapExercise(**exercise_values)


def test_an_unknown_field_from_the_ai_is_refused():
    exercise_values = make_gap_exercise_values()
    exercise_values["difficulty"] = "easy"

    with pytest.raises(ValidationError):
        GapExercise(**exercise_values)


def test_an_empty_hint_is_refused():
    exercise_values = make_gap_exercise_values()
    exercise_values["hint"] = "  "

    with pytest.raises(ValidationError, match="hint is empty"):
        GapExercise(**exercise_values)


@pytest.mark.parametrize("bad_hint", ["Use works.", "WORKS with s", "The answer is: works!"])
def test_a_hint_with_the_expected_answer_is_refused(bad_hint):
    exercise_values = make_gap_exercise_values()
    exercise_values["hint"] = bad_hint

    with pytest.raises(ValidationError, match="gives the expected answer"):
        GapExercise(**exercise_values)


def test_a_hint_with_an_accepted_answer_is_refused():
    exercise_values = make_gap_exercise_values()
    exercise_values["sentence"] = "I ___ my keys yesterday."
    exercise_values["expected_answer"] = "lost"
    exercise_values["accepted_answers"] = ["misplaced"]
    exercise_values["skill_id"] = "irregular_verbs"
    exercise_values["hint"] = "Think of misplaced, past form."

    with pytest.raises(ValidationError, match="gives an accepted answer"):
        GapExercise(**exercise_values)


def test_a_hint_with_the_answer_inside_another_word_is_accepted():
    # Expected "am": the hint "the same verb" must be accepted, because "am" is not a whole word there.
    exercise_values = make_gap_exercise_values()
    exercise_values["sentence"] = "I ___ 25 years old."
    exercise_values["expected_answer"] = "am"
    exercise_values["skill_id"] = "to_be"
    exercise_values["hint"] = "the same verb as in 'I ___ happy'"

    gap_exercise = GapExercise(**exercise_values)

    assert gap_exercise.expected_answer == "am"


@pytest.mark.parametrize("bad_accepted_answers, error_text", [
    ([""], "empty item"),
    (["Works "], "repeats the expected answer"),
    (["is working", "is  working"], "duplicate"),
])
def test_bad_accepted_answers_are_refused(bad_accepted_answers, error_text):
    exercise_values = make_gap_exercise_values()
    exercise_values["accepted_answers"] = bad_accepted_answers

    with pytest.raises(ValidationError, match=error_text):
        GapExercise(**exercise_values)


def test_an_unknown_level_is_refused():
    exercise_values = make_gap_exercise_values()
    exercise_values["level"] = "C2"

    with pytest.raises(ValidationError):
        GapExercise(**exercise_values)
