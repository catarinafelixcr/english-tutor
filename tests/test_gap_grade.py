"""Tests for GapGrade and DetectedMistake in tutor/schemas.py: the AI's grade of one fill-the-gap answer."""

import pytest
from pydantic import ValidationError

from tutor import skills
from tutor.schemas import DetectedMistake, GapGrade, get_detectable_skill_ids, make_gap_grade_schema

# The tested skill in these tests: "She has ___ (finish) the report."
GapGradeForPresentPerfect = make_gap_grade_schema("present_perfect")


def wrong_grade_values():
    # The sentence "She ___ (finish) the report already." and the wrong answer "finished" (past simple).
    return {"verdict": "wrong", "error_type": "grammar", "mistake_text": "finished", "correction": "has finished",
            "why_wrong": "You used the past simple, but 'already' asks for the present perfect.",
            "rule": "already + have/has + past participle: has finished.",
            "corrected_sentence": "She has already finished the report.", "memory_tip": "already → has + -ed"}


def correct_grade_values():
    return {"verdict": "correct", "note": "'has completed' is also natural here.",
            "corrected_sentence": "She has completed the report."}


def spelling_slip():
    return {"skill_id": "spelling", "error_type": "spelling", "mistake_text": "finised", "correction": "finished"}


# ---------- a good grade passes ----------

def test_a_good_wrong_grade_is_accepted():
    grade = GapGradeForPresentPerfect(**wrong_grade_values())

    assert grade.verdict == "wrong"
    assert grade.detected_mistake is None


def test_a_good_correct_grade_is_accepted():
    grade = GapGradeForPresentPerfect(**correct_grade_values())

    assert grade.verdict == "correct"


def test_spaces_at_the_ends_are_removed():
    grade_values = wrong_grade_values()
    grade_values["mistake_text"] = "  finished "

    grade = GapGradeForPresentPerfect(**grade_values)

    assert grade.mistake_text == "finished"


# ---------- the explanation fields follow the verdict ----------

@pytest.mark.parametrize("field_name", ["error_type", "mistake_text", "correction", "why_wrong", "rule"])
def test_a_wrong_grade_needs_every_explanation_field(field_name):
    grade_values = wrong_grade_values()
    del grade_values[field_name]

    with pytest.raises(ValidationError, match=field_name + " is required"):
        GapGradeForPresentPerfect(**grade_values)


def test_a_partial_grade_needs_the_explanation_too():
    grade_values = wrong_grade_values()
    grade_values["verdict"] = "partial"
    grade_values["why_wrong"] = "   "

    with pytest.raises(ValidationError, match="why_wrong is required"):
        GapGradeForPresentPerfect(**grade_values)


@pytest.mark.parametrize("field_name", ["mistake_text", "correction", "why_wrong", "rule"])
def test_a_correct_grade_must_have_no_explanation(field_name):
    grade_values = correct_grade_values()
    grade_values[field_name] = "something"

    with pytest.raises(ValidationError, match=field_name + " must be empty"):
        GapGradeForPresentPerfect(**grade_values)


def test_a_correct_grade_must_have_no_error_type():
    grade_values = correct_grade_values()
    grade_values["error_type"] = "grammar"

    with pytest.raises(ValidationError, match="error_type must be empty"):
        GapGradeForPresentPerfect(**grade_values)


# ---------- note ----------

def test_a_correct_grade_without_a_slip_needs_a_note():
    grade_values = correct_grade_values()
    grade_values["note"] = ""

    with pytest.raises(ValidationError, match="note is required"):
        GapGradeForPresentPerfect(**grade_values)


def test_a_correct_grade_with_a_slip_needs_no_note():
    # "She has finised the report": right structure, a typo. The reminder about spelling replaces the note.
    grade = GapGradeForPresentPerfect(verdict="correct", corrected_sentence="She has finished the report.",
                                      detected_mistake=spelling_slip())

    assert grade.note == ""
    assert grade.detected_mistake.skill_id == "spelling"


# ---------- the main error type spelling ----------

def test_the_main_mistake_cannot_be_spelling_when_another_skill_is_tested():
    # "She has finised the report" in a present perfect exercise: correct + a DETECTED spelling mistake.
    grade_values = wrong_grade_values()
    grade_values["error_type"] = "spelling"

    with pytest.raises(ValidationError, match="only for an exercise that tests spelling"):
        GapGradeForPresentPerfect(**grade_values)


def test_the_main_mistake_can_be_spelling_when_spelling_is_tested():
    gap_grade_for_spelling = make_gap_grade_schema("spelling")
    grade_values = wrong_grade_values()
    grade_values["error_type"] = "spelling"

    grade = gap_grade_for_spelling(**grade_values)

    assert grade.error_type == "spelling"


# ---------- other fields ----------

def test_corrected_sentence_cannot_be_empty():
    grade_values = correct_grade_values()
    grade_values["corrected_sentence"] = "  "

    with pytest.raises(ValidationError, match="corrected_sentence is empty"):
        GapGradeForPresentPerfect(**grade_values)


def test_corrected_sentence_cannot_keep_the_gap():
    grade_values = correct_grade_values()
    grade_values["corrected_sentence"] = "She has ___ the report."

    with pytest.raises(ValidationError, match="still has the gap"):
        GapGradeForPresentPerfect(**grade_values)


def test_other_good_answers_cannot_have_an_empty_item():
    grade_values = correct_grade_values()
    grade_values["other_good_answers"] = ["has completed", " "]

    with pytest.raises(ValidationError, match="empty item"):
        GapGradeForPresentPerfect(**grade_values)


def test_unknown_fields_are_refused():
    grade_values = correct_grade_values()
    grade_values["skill_id"] = "present_perfect"

    with pytest.raises(ValidationError):
        GapGradeForPresentPerfect(**grade_values)


# ---------- detected mistake ----------

def test_a_wrong_irregular_form_is_a_grammar_detected_mistake():
    # "She has writed the report": present perfect correct, irregular_verbs wrong ("Almost").
    detected_mistake = {"skill_id": "irregular_verbs", "error_type": "grammar", "mistake_text": "writed",
                        "correction": "written"}

    grade = GapGradeForPresentPerfect(verdict="correct", corrected_sentence="She has written the report.",
                                      detected_mistake=detected_mistake)

    assert grade.detected_mistake.skill_id == "irregular_verbs"


def test_a_wrong_answer_can_also_have_a_detected_mistake():
    grade_values = wrong_grade_values()
    grade_values["detected_mistake"] = spelling_slip()

    grade = GapGradeForPresentPerfect(**grade_values)

    assert grade.detected_mistake is not None


def test_the_detected_mistake_cannot_be_the_tested_skill():
    detected_mistake = {"skill_id": "present_perfect", "error_type": "grammar", "mistake_text": "finished",
                        "correction": "has finished"}

    with pytest.raises(ValidationError):
        GapGradeForPresentPerfect(verdict="correct", corrected_sentence="She has finished the report.",
                                  detected_mistake=detected_mistake)


def test_the_detected_mistake_cannot_be_an_unknown_skill():
    detected_mistake = {"skill_id": "verb_tenses", "error_type": "grammar", "mistake_text": "finished",
                        "correction": "has finished"}

    with pytest.raises(ValidationError):
        GapGradeForPresentPerfect(verdict="correct", corrected_sentence="She has finished the report.",
                                  detected_mistake=detected_mistake)


def test_the_detected_mistake_cannot_be_a_general_skill():
    # The enum stops it, and so does the code check on the base model (used without the enum).
    with pytest.raises(ValidationError, match="not an active learning skill"):
        DetectedMistake(skill_id="writing_general", error_type="grammar", mistake_text="x", correction="y")


def test_spelling_needs_the_error_type_spelling():
    with pytest.raises(ValidationError, match="needs the error type spelling"):
        DetectedMistake(skill_id="spelling", error_type="grammar", mistake_text="finised", correction="finished")


def test_the_error_type_spelling_is_only_for_spelling_skills():
    # "writed" is a grammar mistake, never spelling (PLAN.md, Step 2).
    with pytest.raises(ValidationError, match="only for the skills spelling and capitalization"):
        DetectedMistake(skill_id="irregular_verbs", error_type="spelling", mistake_text="writed",
                        correction="wrote")


def test_capitalization_with_the_error_type_spelling_is_accepted():
    detected_mistake = DetectedMistake(skill_id="capitalization", error_type="spelling", mistake_text="monday",
                                       correction="Monday")

    assert detected_mistake.skill_id == "capitalization"


def test_the_detected_mistake_needs_mistake_text_and_correction():
    with pytest.raises(ValidationError):
        DetectedMistake(skill_id="spelling", error_type="spelling", mistake_text="", correction="finished")


# ---------- the enum sent to the AI ----------

def test_detectable_skills_are_every_learning_skill_except_the_tested_one():
    detectable_skill_ids = get_detectable_skill_ids("present_perfect")

    assert "present_perfect" not in detectable_skill_ids
    assert "irregular_verbs" in detectable_skill_ids
    assert "spelling" in detectable_skill_ids
    assert "writing_general" not in detectable_skill_ids
    assert len(detectable_skill_ids) == len(skills.get_learning_skills()) - 1


def test_the_json_schema_limits_the_detected_skill_id_to_an_enum():
    json_schema = GapGradeForPresentPerfect.model_json_schema()
    detected_mistake_schema = json_schema["$defs"]["NewDetectedMistake"]
    allowed_skill_ids = detected_mistake_schema["properties"]["skill_id"]["enum"]

    assert allowed_skill_ids == get_detectable_skill_ids("present_perfect")


def test_the_json_schema_does_not_show_the_tested_skill_id():
    # tested_skill_id is a ClassVar: the AI never sees it.
    json_schema = GapGradeForPresentPerfect.model_json_schema()

    assert "tested_skill_id" not in json_schema["properties"]


def test_the_base_gap_grade_accepts_any_learning_skill_as_detected():
    # Without make_gap_grade_schema() there is no tested skill, so only the learning-skill check applies.
    grade = GapGrade(verdict="correct", corrected_sentence="She has finished the report.",
                     detected_mistake=spelling_slip())

    assert grade.detected_mistake.skill_id == "spelling"
