"""Checking answers: first in code (no AI), then with the AI only when the code cannot decide (CLAUDE.md, rule 5).

This file sits between the screens (pages/) and the AI (llm.py), so the pages stay thin (CLAUDE.md, rule 7).
"""

import re

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
