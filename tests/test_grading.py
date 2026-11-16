"""Tests for tutor/grading.py. The code check needs no AI and no database."""

import pytest

from tutor import grading
from tutor.schemas import Exercise, make_gap_grade_schema


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


# ---------- build_sentence_with_answer ----------

PRESENT_PERFECT_SENTENCE = "She has ___ (finish) the report already."

GapGradeForPresentPerfect = make_gap_grade_schema("present_perfect")


def test_my_answer_goes_into_the_gap_and_the_bracket_is_removed():
    sentence_with_answer = grading.build_sentence_with_answer(PRESENT_PERFECT_SENTENCE, "finish")

    assert sentence_with_answer == "She has finish the report already."


def test_a_sentence_without_a_bracket_also_works():
    sentence_with_answer = grading.build_sentence_with_answer("I ___ 25 years old.", "  have ")

    assert sentence_with_answer == "I have 25 years old."


# ---------- quote_is_in_sentence ----------

def test_a_quote_can_use_words_of_the_sentence_and_of_my_answer():
    # "has" is in the sentence, "finish" is my answer: the quote is checked in the FULL sentence.
    sentence_with_answer = grading.build_sentence_with_answer(PRESENT_PERFECT_SENTENCE, "finish")

    assert grading.quote_is_in_sentence("has finish", sentence_with_answer)


def test_a_quote_found_only_in_the_bracket_is_refused():
    sentence_with_answer = grading.build_sentence_with_answer("She ___ (finish) the report.", "finished")

    assert not grading.quote_is_in_sentence("finish", sentence_with_answer)


def test_a_quote_must_be_whole_words():
    assert not grading.quote_is_in_sentence("go", "She goes to work.")


@pytest.mark.parametrize("quote", ["“Has Finish”", "\"has finish\"", "'has finish'", "has  finish.", "«has finish»"])
def test_a_quote_ignores_capitals_quote_marks_spaces_and_final_punctuation(quote):
    assert grading.quote_is_in_sentence(quote, "She has finish the report already.")


def test_a_quote_ignores_the_apostrophe_style():
    assert grading.quote_is_in_sentence("doesn’t works", "He doesn't works on Fridays.")
    assert grading.quote_is_in_sentence("doesn't works", "He doesn’t works on Fridays.")


def test_an_empty_quote_is_never_in_the_sentence():
    assert not grading.quote_is_in_sentence("  ", "She has finish the report.")


# ---------- find_bad_quotes and the fallback ----------

def make_partial_grade(mistake_text, detected_mistake=None):
    # "She has finish the report already.": half of the present perfect (has, but no past participle).
    return GapGradeForPresentPerfect(verdict="partial", error_type="grammar", mistake_text=mistake_text,
                                     correction="has finished", why_wrong="After 'has' we need the past participle.",
                                     rule="has + past participle: has finished.",
                                     corrected_sentence="She has finished the report already.",
                                     detected_mistake=detected_mistake)


def make_writed_grade(detected_quote):
    # "She has writed the report already.": present perfect correct, irregular_verbs wrong ("Almost").
    detected_mistake = {"skill_id": "irregular_verbs", "error_type": "grammar", "mistake_text": detected_quote,
                        "correction": "written"}

    return GapGradeForPresentPerfect(verdict="correct", corrected_sentence="She has written the report already.",
                                     detected_mistake=detected_mistake)


def test_good_quotes_give_no_bad_quote():
    grade = make_partial_grade("has finish")

    assert grading.find_bad_quotes(grade, "She has finish the report already.") == []


def test_a_main_quote_that_is_not_in_my_sentence_is_bad():
    grade = make_partial_grade("have finish")

    assert grading.find_bad_quotes(grade, "She has finish the report already.") == ["mistake_text"]


def test_a_detected_quote_that_is_not_in_my_sentence_is_bad():
    grade = make_writed_grade("wrote")

    assert grading.find_bad_quotes(grade, "She has writed the report already.") == ["detected_mistake.mistake_text"]


def test_a_correct_grade_has_no_main_quote_to_check():
    grade = make_writed_grade("writed")

    assert grading.find_bad_quotes(grade, "She has writed the report already.") == []


def test_the_fallback_puts_my_answer_in_both_bad_quotes():
    detected_mistake = {"skill_id": "spelling", "error_type": "spelling", "mistake_text": "finsh",
                        "correction": "finish"}
    grade = make_partial_grade("have finish", detected_mistake)
    bad_quote_names = ["mistake_text", "detected_mistake.mistake_text"]

    changed_grade = grading.use_my_answer_as_bad_quotes(grade, bad_quote_names, " finish ")

    assert changed_grade.mistake_text == "finish"
    assert changed_grade.detected_mistake.mistake_text == "finish"
    assert grade.mistake_text == "have finish"
    assert grade.detected_mistake.mistake_text == "finsh"


def test_the_fallback_changes_only_the_bad_quote():
    grade = make_writed_grade("wrote")

    changed_grade = grading.use_my_answer_as_bad_quotes(grade, ["detected_mistake.mistake_text"], "writed")

    assert changed_grade.detected_mistake.mistake_text == "writed"
    assert changed_grade.mistake_text == ""


# ---------- quotes_overlap ----------

@pytest.mark.parametrize("first_quote, second_quote", [("writed", "writed"), ("has writed", "writed"),
                                                       ("writed", "Has Writed.")])
def test_quotes_that_share_the_same_words_overlap(first_quote, second_quote):
    assert grading.quotes_overlap(first_quote, second_quote)


@pytest.mark.parametrize("first_quote, second_quote", [("has writes", "reprot"), ("go", "goes"), ("", "writed")])
def test_quotes_on_other_words_do_not_overlap(first_quote, second_quote):
    assert not grading.quotes_overlap(first_quote, second_quote)


# ---------- corrected_sentence_matches ----------

def test_the_corrected_sentence_matches_after_replacing_the_main_quote():
    grade = make_partial_grade("has finish")

    assert grading.corrected_sentence_matches(grade, "She has finish the report already.")


def test_the_corrected_sentence_matches_after_replacing_the_detected_quote():
    grade = make_writed_grade("writed")

    assert grading.corrected_sentence_matches(grade, "She has writed the report already.")


def test_a_corrected_sentence_that_changes_other_words_does_not_match():
    grade = make_partial_grade("has finish")
    grade = grade.model_copy(update={"corrected_sentence": "She has finished the whole report already."})

    assert not grading.corrected_sentence_matches(grade, "She has finish the report already.")


def test_an_also_right_answer_keeps_my_sentence():
    grade = GapGradeForPresentPerfect(verdict="correct", note="'has completed' is also natural here.",
                                      corrected_sentence="She has completed the report already.")

    assert grading.corrected_sentence_matches(grade, "She has completed the report already")
    assert not grading.corrected_sentence_matches(grade, "She has done the report already.")
