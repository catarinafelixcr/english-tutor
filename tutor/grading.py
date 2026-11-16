"""Checking answers: first in code (no AI), then with the AI only when the code cannot decide (CLAUDE.md, rule 5).

This file sits between the screens (pages/) and the AI (llm.py), so the pages stay thin (CLAUDE.md, rule 7).
"""

# Curly apostrophes that phone keyboards type. They all become the straight one: ’ → '
CURLY_APOSTROPHES = ["’", "‘", "ʼ"]

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
