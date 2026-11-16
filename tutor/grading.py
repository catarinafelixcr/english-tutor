"""Checking answers: first in code (no AI), then with the AI only when the code cannot decide (CLAUDE.md, rule 5).

This file sits between the screens (pages/) and the AI (llm.py), so the pages stay thin (CLAUDE.md, rule 7).
"""

import json
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from tutor import db, llm, prompts
from tutor.schemas import Attempt, make_gap_grade_schema

# One JSON line per grading problem: bad quotes, the fallback, a corrected sentence that does not match.
GRADING_PROBLEMS_LOG_PATH = db.PROJECT_FOLDER / "logs" / "grading_problems.jsonl"

# Curly apostrophes that phone keyboards type. They all become the straight one: ’ → '
CURLY_APOSTROPHES = ["’", "‘", "ʼ"]

# Double quote marks the AI may put around a quote. They are removed before comparing texts.
DOUBLE_QUOTE_MARKS = ["\"", "“", "”", "«", "»"]

# Punctuation removed at the END of a quote or a sentence before comparing: "finish." = "finish".
SENTENCE_END_PUNCTUATION = ".,!?;:"

# The verb in brackets right after the gap: "___ (finish)". It is a clue, not part of the sentence.
GAP_WITH_BRACKET_PATTERN = r"___\s*\([^)]*\)"

# Punctuation removed at the END of an answer only: "goes." = "goes". Never inside ("don't", "e.g").
FINAL_PUNCTUATION = ".,"

# The three results of check_answer_in_code().
EXACT_MATCH = "exact"
CAPITALIZATION_SLIP = "capitalization"
NO_MATCH = "no_match"


# ---------- check in code (no AI) ----------

def clean_answer(answer_text):
    # Keeps the capital letters (the capitalization check needs them). Changes only what never matters:
    # curly apostrophes, spaces at the ends, several spaces between words, a final full stop or comma.
    cleaned_text = answer_text

    for curly_apostrophe in CURLY_APOSTROPHES:
        cleaned_text = cleaned_text.replace(curly_apostrophe, "'")

    cleaned_text = " ".join(cleaned_text.split())
    cleaned_text = cleaned_text.rstrip(FINAL_PUNCTUATION).strip()

    return cleaned_text


def misses_a_capital_letter(your_answer, correct_answer):
    # True if the correct answer has a capital letter where I wrote a small one ("monday" for "Monday").
    # Both texts are cleaned and equal when we ignore capital letters, so they have the same length.
    if len(your_answer) != len(correct_answer):
        return False

    for your_letter, correct_letter in zip(your_answer, correct_answer):
        if correct_letter.isupper() and your_letter.islower():
            return True

    return False


def check_answer_in_code(your_answer, exercise):
    # Compares my answer with the expected answer and the accepted answers. Returns (result, matched answer):
    #   (EXACT_MATCH, answer)          correct. Capital letters I added myself ("Goes") do not matter.
    #   (CAPITALIZATION_SLIP, answer)  correct, but I wrote a small letter where a capital is needed ("monday")
    #   (NO_MATCH, None)               the code cannot decide: the AI grades it
    if exercise.expected_answer is None or exercise.expected_answer.strip() == "":
        raise ValueError("this exercise has no expected answer, so the code cannot check it")

    cleaned_your_answer = clean_answer(your_answer)

    if cleaned_your_answer == "":
        raise ValueError("the answer is empty")

    correct_answers = [exercise.expected_answer] + exercise.accepted_answers
    capitalization_match = None

    for correct_answer in correct_answers:
        cleaned_correct_answer = clean_answer(correct_answer)

        if cleaned_your_answer.lower() != cleaned_correct_answer.lower():
            continue

        if not misses_a_capital_letter(cleaned_your_answer, cleaned_correct_answer):
            return EXACT_MATCH, correct_answer

        # Remember it, but keep looking: another accepted answer could match with no capital missing.
        if capitalization_match is None:
            capitalization_match = correct_answer

    if capitalization_match is not None:
        return CAPITALIZATION_SLIP, capitalization_match

    return NO_MATCH, None


# ---------- the full sentence with my answer ----------

def build_sentence_with_answer(sentence, your_answer):
    # "She has ___ (finish) the report." + "finish" → "She has finish the report."
    # The verb in brackets is removed: a quote "finish" must not be found in the clue "(finish)".
    sentence_without_bracket = re.sub(GAP_WITH_BRACKET_PATTERN, "___", sentence, count=1)
    sentence_with_answer = sentence_without_bracket.replace("___", clean_answer(your_answer), 1)

    return sentence_with_answer


# ---------- checking the AI's quotes (mistake_text) ----------

def clean_for_comparing(text):
    # Ignores what never matters in a quote: capital letters, quote marks, apostrophe styles, extra spaces,
    # and punctuation at the end. Apostrophes INSIDE words stay ("don't").
    cleaned_text = text.lower()

    for curly_apostrophe in CURLY_APOSTROPHES:
        cleaned_text = cleaned_text.replace(curly_apostrophe, "'")

    for quote_mark in DOUBLE_QUOTE_MARKS:
        cleaned_text = cleaned_text.replace(quote_mark, " ")

    cleaned_text = " ".join(cleaned_text.split())
    cleaned_text = cleaned_text.rstrip(SENTENCE_END_PUNCTUATION).strip()

    # Single quotes AROUND the whole quote ('has finish') are quote marks, not apostrophes.
    if len(cleaned_text) >= 2 and cleaned_text.startswith("'") and cleaned_text.endswith("'"):
        cleaned_text = cleaned_text[1:-1].strip()

    return cleaned_text


def make_whole_words_pattern(cleaned_words):
    # Like \b, but it also works when the words start or end with an apostrophe or a hyphen.
    # (?<!\w) = no letter just before; (?!\w) = no letter just after. "go" is found in "I go now", not in "going".
    return r"(?<!\w)" + re.escape(cleaned_words) + r"(?!\w)"


def quote_is_in_sentence(quote, sentence_with_answer):
    cleaned_quote = clean_for_comparing(quote)

    if cleaned_quote == "":
        return False

    pattern = make_whole_words_pattern(cleaned_quote)

    return re.search(pattern, clean_for_comparing(sentence_with_answer)) is not None


def find_bad_quotes(grade, sentence_with_answer):
    # The names of the quotes that are NOT words of my sentence. An empty list = all quotes are good.
    bad_quote_names = []

    if grade.verdict != "correct" and not quote_is_in_sentence(grade.mistake_text, sentence_with_answer):
        bad_quote_names.append("mistake_text")

    detected_mistake = grade.detected_mistake

    if detected_mistake is not None and not quote_is_in_sentence(detected_mistake.mistake_text, sentence_with_answer):
        bad_quote_names.append("detected_mistake.mistake_text")

    return bad_quote_names


def use_my_answer_as_bad_quotes(grade, bad_quote_names, your_answer):
    # The fallback after 2 bad answers: my answer replaces each bad quote, so the screen still shows the
    # explanation (PLAN.md: "never block me"). Returns a NEW grade; the old one is not changed.
    my_answer = clean_answer(your_answer)
    changed_grade = grade

    if "mistake_text" in bad_quote_names:
        changed_grade = changed_grade.model_copy(update={"mistake_text": my_answer})

    if "detected_mistake.mistake_text" in bad_quote_names:
        changed_detected_mistake = changed_grade.detected_mistake.model_copy(update={"mistake_text": my_answer})
        changed_grade = changed_grade.model_copy(update={"detected_mistake": changed_detected_mistake})

    return changed_grade


# ---------- one slip, one skill ----------

def quotes_overlap(first_quote, second_quote):
    # True if one quote contains the other as whole words: "writed" and "has writed" overlap.
    cleaned_first_quote = clean_for_comparing(first_quote)
    cleaned_second_quote = clean_for_comparing(second_quote)

    if cleaned_first_quote == "" or cleaned_second_quote == "":
        return False

    if re.search(make_whole_words_pattern(cleaned_second_quote), cleaned_first_quote) is not None:
        return True

    return re.search(make_whole_words_pattern(cleaned_first_quote), cleaned_second_quote) is not None


def has_same_words_twice(grade):
    # True when the main and the detected mistake quote the same words: one slip would count against two skills
    # (the grade demo, 2026-11-16: "writed" was the main mistake AND a detected irregular_verbs mistake).
    if grade.verdict == "correct" or grade.detected_mistake is None:
        return False

    return quotes_overlap(grade.mistake_text, grade.detected_mistake.mistake_text)


def drop_detected_mistake(grade):
    # My rule: keep the main verdict, drop the detected row. Never count one slip against two skills.
    return grade.model_copy(update={"detected_mistake": None})


# ---------- checking corrected_sentence (only logged, never retried) ----------

def replace_quote(cleaned_sentence, quote, correction):
    # Replaces the FIRST place where the quote appears (whole words) with the correction.
    # Returns the sentence unchanged when the quote is not there.
    cleaned_quote = clean_for_comparing(quote)

    if cleaned_quote == "":
        return cleaned_sentence

    found_quote = re.search(make_whole_words_pattern(cleaned_quote), cleaned_sentence)

    if found_quote is None:
        return cleaned_sentence

    text_before = cleaned_sentence[:found_quote.start()]
    text_after = cleaned_sentence[found_quote.end():]
    corrected_text = text_before + clean_for_comparing(correction) + text_after

    return corrected_text


def build_expected_corrected_sentence(grade, sentence_with_answer):
    # My sentence with each quote replaced by its correction: what corrected_sentence should be.
    # Compared after clean_for_comparing(), so it is in small letters.
    expected_sentence = clean_for_comparing(sentence_with_answer)

    if grade.verdict != "correct":
        expected_sentence = replace_quote(expected_sentence, grade.mistake_text, grade.correction)

    if grade.detected_mistake is not None:
        detected_mistake = grade.detected_mistake
        expected_sentence = replace_quote(expected_sentence, detected_mistake.mistake_text, detected_mistake.correction)

    return expected_sentence


def corrected_sentence_matches(grade, sentence_with_answer):
    # True if corrected_sentence = my sentence with the corrections applied (ignoring capitals, quotes, spaces,
    # final punctuation). For a correct answer with no slip, corrected_sentence must be my own sentence.
    expected_sentence = build_expected_corrected_sentence(grade, sentence_with_answer)

    return clean_for_comparing(grade.corrected_sentence) == expected_sentence


# ---------- the result the page shows ----------

class GapResult(BaseModel):
    """What the Practice page shows after one answer. The page only draws it (CLAUDE.md, rule 7).

    state: correct (green), almost (yellow: tested skill right + a grammar slip of another skill),
    partial (yellow "Partly right"), wrong (red).
    """

    submission_id: str
    state: Literal["correct", "almost", "partial", "wrong"]
    graded_by: Literal["code", "ai"]
    your_answer: str
    corrected_sentence: str
    mistake_text: str = ""
    correction: str = ""
    why_wrong: str = ""
    rule: str = ""
    note: str = ""
    memory_tip: str = ""
    other_good_answers: list[str] = Field(default_factory=list)
    # A slip of another skill: "writed" → "written" (irregular_verbs), "finised" → "finished" (spelling).
    detected_skill_id: str = ""
    detected_mistake_text: str = ""
    detected_correction: str = ""
    # A short line for a spelling or capitalization slip, shown under a green result.
    reminder: str = ""


def choose_state(verdict, detected_mistake):
    if verdict == "wrong":
        return "wrong"

    if verdict == "partial":
        return "partial"

    # Correct. A grammar slip of another skill ("writed") is "Almost"; a spelling slip stays green + reminder.
    if detected_mistake is not None and detected_mistake.error_type != "spelling":
        return "almost"

    return "correct"


def make_reminder(skill_id, mistake_text, correction):
    if skill_id == "capitalization":
        return "Remember the capital letter: " + mistake_text + " → " + correction + "."

    if skill_id == "spelling":
        return "Check the spelling: " + mistake_text + " → " + correction + "."

    return ""


def choose_note_to_show(grade):
    # The AI sometimes writes a note where the prompt says to leave it empty (the grade demo, 2026-11-16).
    # My rules: a note only for a correct answer (wrong/partial have the 3 parts), and not when there is a slip
    # (the reminder is enough).
    if grade.verdict != "correct":
        return ""

    if grade.detected_mistake is not None:
        return ""

    return grade.note


def join_explanation(grade):
    # The text saved in the "explanation" column: the 3 parts, or the "also right" note.
    if grade.verdict == "correct":
        return choose_note_to_show(grade)

    return "You wrote: " + grade.mistake_text + "\nWhy: " + grade.why_wrong + "\nRule: " + grade.rule


# ---------- logging grading problems ----------

def write_grading_problem(problem_name, exercise_id, exercise, your_answer, grade, details):
    # Never blocks the learner: the problem is only written down, to look at later.
    problem_line = {
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "problem": problem_name,
        "exercise_id": exercise_id,
        "skill_id": exercise.skill_id,
        "sentence": exercise.prompt_text,
        "your_answer": your_answer,
        "details": details,
        "grade": grade.model_dump(),
    }

    GRADING_PROBLEMS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(GRADING_PROBLEMS_LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(problem_line, ensure_ascii=False, default=str) + "\n")


# ---------- grading in code: the rows ----------

def make_code_attempt(submission_id, exercise_id, exercise, your_answer, hint_used, seconds_taken):
    # Attempt is a Pydantic model: it needs keyword names (the exception in CLAUDE.md).
    return Attempt(submission_id=submission_id, exercise_id=exercise_id, section=exercise.section,
                   skill_id=exercise.skill_id, source="targeted", your_answer=your_answer, verdict="correct",
                   hint_used=hint_used, seconds_taken=seconds_taken, graded_by="code")


def grade_exact_match(submission_id, exercise_id, exercise, your_answer, matched_answer, hint_used, seconds_taken,
                      database_path):
    attempt = make_code_attempt(submission_id, exercise_id, exercise, your_answer, hint_used, seconds_taken)
    db.save_attempts([attempt], database_path)

    # The matched correct answer, not mine: "Written" (a capital I added myself) must not stay mid-sentence.
    corrected_sentence = build_sentence_with_answer(exercise.prompt_text, matched_answer)

    return GapResult(submission_id=submission_id, state="correct", graded_by="code", your_answer=your_answer,
                     corrected_sentence=corrected_sentence)


def grade_capitalization_slip(submission_id, exercise_id, exercise, your_answer, matched_answer, hint_used,
                              seconds_taken, database_path):
    # PLAN.md: the targeted attempt is correct + one detected capitalization attempt, with no AI call.
    my_answer = clean_answer(your_answer)
    reminder = make_reminder("capitalization", my_answer, matched_answer)

    targeted_attempt = make_code_attempt(submission_id, exercise_id, exercise, your_answer, hint_used, seconds_taken)
    detected_attempt = Attempt(submission_id=submission_id, exercise_id=exercise_id, section=exercise.section,
                               skill_id="capitalization", source="detected", your_answer=your_answer,
                               verdict="wrong", error_type="spelling", explanation=reminder, mistake_text=my_answer,
                               correction=matched_answer, hint_used=hint_used, seconds_taken=seconds_taken,
                               graded_by="code")
    db.save_attempts([targeted_attempt, detected_attempt], database_path)

    corrected_sentence = build_sentence_with_answer(exercise.prompt_text, matched_answer)

    return GapResult(submission_id=submission_id, state="correct", graded_by="code", your_answer=your_answer,
                     corrected_sentence=corrected_sentence, detected_skill_id="capitalization",
                     detected_mistake_text=my_answer, detected_correction=matched_answer, reminder=reminder)


# ---------- grading with the AI ----------

def get_bad_quote_texts(grade, bad_quote_names):
    bad_quote_texts = []

    if "mistake_text" in bad_quote_names:
        bad_quote_texts.append(grade.mistake_text)

    if "detected_mistake.mistake_text" in bad_quote_names:
        bad_quote_texts.append(grade.detected_mistake.mistake_text)

    return bad_quote_texts


def ask_ai_for_grade(exercise_id, exercise, your_answer, explanation_language):
    # Returns (grade, model returned, prompt version). Two code checks on the grade:
    # - its quotes are words of my sentence (if not: my answer replaces them after the retry);
    # - one slip counts against one skill (if not: the detected mistake is dropped after the retry).
    # ONE retry fixes both, with a note per problem. Every request for this answer shares ONE budget:
    # about 4 requests and 20 seconds in total (my rule).
    my_answer = clean_answer(your_answer)
    sentence_with_answer = build_sentence_with_answer(exercise.prompt_text, your_answer)
    prompt_text, prompt_version = prompts.build_gap_grade_prompt(exercise, my_answer, sentence_with_answer,
                                                                 explanation_language)
    grade_schema = make_gap_grade_schema(exercise.skill_id)
    shared_budget = llm.make_normal_budget()

    # No try here: if the first grade fails, the page shows the error and nothing is saved.
    grade, model_returned = llm.ask(prompt_text, prompt_version, grade_schema, "grade", shared_budget)
    bad_quote_names = find_bad_quotes(grade, sentence_with_answer)
    same_words_twice = has_same_words_twice(grade)

    if len(bad_quote_names) > 0 or same_words_twice:
        bad_quote_texts = get_bad_quote_texts(grade, bad_quote_names)

        if len(bad_quote_texts) > 0:
            write_grading_problem("bad_quotes", exercise_id, exercise, your_answer, grade, bad_quote_texts)

        if same_words_twice:
            write_grading_problem("same_words_twice", exercise_id, exercise, your_answer, grade, "")

        retry_prompt_text = prompts.add_retry_notes(prompt_text, bad_quote_texts, same_words_twice,
                                                    sentence_with_answer)

        try:
            grade, model_returned = llm.ask(retry_prompt_text, prompt_version, grade_schema, "grade", shared_budget)
        except llm.AIError as error:
            # Busy, out of budget, invalid... The first grade is still good enough to show, after the fixes below.
            write_grading_problem("retry_failed", exercise_id, exercise, your_answer, grade, str(error))

        bad_quote_names = find_bad_quotes(grade, sentence_with_answer)

    if len(bad_quote_names) > 0:
        bad_quote_texts = get_bad_quote_texts(grade, bad_quote_names)
        write_grading_problem("quote_fallback", exercise_id, exercise, your_answer, grade, bad_quote_texts)
        grade = use_my_answer_as_bad_quotes(grade, bad_quote_names, your_answer)

    # Checked AFTER the quote fallback: my answer as both quotes would also be the same words twice.
    if has_same_words_twice(grade):
        write_grading_problem("detected_mistake_dropped", exercise_id, exercise, your_answer, grade, "")
        grade = drop_detected_mistake(grade)

    # Addition C: only logged, never retried.
    if not corrected_sentence_matches(grade, sentence_with_answer):
        expected_sentence = build_expected_corrected_sentence(grade, sentence_with_answer)
        write_grading_problem("corrected_sentence_mismatch", exercise_id, exercise, your_answer, grade,
                              expected_sentence)

    return grade, model_returned, prompt_version


def make_ai_attempts(submission_id, exercise_id, exercise, your_answer, hint_used, seconds_taken, grade,
                     model_returned, prompt_version):
    # The targeted row, and a detected row when the AI found a slip of another skill.
    targeted_attempt = Attempt(submission_id=submission_id, exercise_id=exercise_id, section=exercise.section,
                               skill_id=exercise.skill_id, source="targeted", your_answer=your_answer,
                               verdict=grade.verdict, error_type=grade.error_type,
                               explanation=join_explanation(grade), mistake_text=grade.mistake_text or None,
                               correction=grade.correction or None, hint_used=hint_used,
                               seconds_taken=seconds_taken, graded_by="ai", model=model_returned,
                               prompt_version=prompt_version)
    attempt_list = [targeted_attempt]

    detected_mistake = grade.detected_mistake

    if detected_mistake is None:
        return attempt_list

    detected_explanation = make_reminder(detected_mistake.skill_id, detected_mistake.mistake_text,
                                         detected_mistake.correction)
    detected_attempt = Attempt(submission_id=submission_id, exercise_id=exercise_id, section=exercise.section,
                               skill_id=detected_mistake.skill_id, source="detected", your_answer=your_answer,
                               verdict="wrong", error_type=detected_mistake.error_type,
                               explanation=detected_explanation, mistake_text=detected_mistake.mistake_text,
                               correction=detected_mistake.correction, hint_used=hint_used,
                               seconds_taken=seconds_taken, graded_by="ai", model=model_returned,
                               prompt_version=prompt_version)
    attempt_list.append(detected_attempt)

    return attempt_list


def make_ai_result(submission_id, your_answer, grade):
    detected_mistake = grade.detected_mistake
    result = GapResult(submission_id=submission_id, state=choose_state(grade.verdict, detected_mistake),
                       graded_by="ai", your_answer=your_answer, corrected_sentence=grade.corrected_sentence,
                       mistake_text=grade.mistake_text, correction=grade.correction, why_wrong=grade.why_wrong,
                       rule=grade.rule, note=choose_note_to_show(grade), memory_tip=grade.memory_tip,
                       other_good_answers=grade.other_good_answers)

    if detected_mistake is None:
        return result

    result.detected_skill_id = detected_mistake.skill_id
    result.detected_mistake_text = detected_mistake.mistake_text
    result.detected_correction = detected_mistake.correction
    result.reminder = make_reminder(detected_mistake.skill_id, detected_mistake.mistake_text,
                                    detected_mistake.correction)

    return result


# ---------- the function the page calls ----------

def grade_gap_answer(exercise_id, exercise, your_answer, hint_used, seconds_taken,
                     explanation_language=prompts.DEFAULT_EXPLANATION_LANGUAGE,
                     database_path=db.DEFAULT_DATABASE_PATH):
    # Grades one fill-the-gap answer, saves every row (CLAUDE.md, rule 3) and returns a GapResult.
    # The code first (no AI); the AI only when the code cannot decide (CLAUDE.md, rule 5).
    # An AI error goes up to the page: nothing is saved, so the exercise stays in the stock to try again.
    result_kind, matched_answer = check_answer_in_code(your_answer, exercise)
    submission_id = db.new_submission_id()

    if result_kind == EXACT_MATCH:
        return grade_exact_match(submission_id, exercise_id, exercise, your_answer, matched_answer, hint_used,
                                 seconds_taken, database_path)

    if result_kind == CAPITALIZATION_SLIP:
        return grade_capitalization_slip(submission_id, exercise_id, exercise, your_answer, matched_answer,
                                         hint_used, seconds_taken, database_path)

    grade, model_returned, prompt_version = ask_ai_for_grade(exercise_id, exercise, your_answer,
                                                             explanation_language)
    attempt_list = make_ai_attempts(submission_id, exercise_id, exercise, your_answer, hint_used, seconds_taken,
                                    grade, model_returned, prompt_version)
    db.save_attempts(attempt_list, database_path)

    return make_ai_result(submission_id, your_answer, grade)
