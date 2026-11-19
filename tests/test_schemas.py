"""Tests for the AI answer models in tutor/schemas.py (GapExerciseDraft, GapExercise and the batch)."""

import pytest
from pydantic import ValidationError

from tutor.schemas import (
    GapExercise,
    GapExerciseBatch,
    GapExerciseDraft,
    GapExerciseItem,
    make_gap_exercise_batch_schema,
    make_gap_exercise_draft_schema,
    split_gap_exercise_items,
)

TRAP_WHY = "With she, the verb needs -s: she works."


def make_gap_exercise_values():
    return {"sentence": "She ___ (work) in a bank.", "signal": "in a bank", "expected_answer": "works",
            "accepted_answers": [], "trap": "work", "trap_why": TRAP_WHY, "skill_id": "present_simple",
            "hint": "he / she / it", "level": "A2"}


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
    exercise_values["signal"] = "yesterday"
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
    exercise_values["signal"] = "25 years old"
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


# ---------- GapExerciseDraft: what the AI returns ----------

def make_draft_values():
    return {"sentence": "She ___ (work) in a bank.", "signal": "in a bank", "expected_answer": "works",
            "accepted_answers": [], "trap": "work", "trap_why": TRAP_WHY, "hint": "he / she / it"}


def test_a_good_draft_is_accepted():
    draft = GapExerciseDraft(**make_draft_values())

    assert draft.sentence == "She ___ (work) in a bank."


@pytest.mark.parametrize("field_name, field_value", [("skill_id", "present_simple"), ("level", "A2")])
def test_the_draft_refuses_skill_id_and_level_from_the_ai(field_name, field_value):
    # The code chooses the skill and the level: the AI is not allowed to send them.
    draft_values = make_draft_values()
    draft_values[field_name] = field_value

    with pytest.raises(ValidationError):
        GapExerciseDraft(**draft_values)


def test_the_draft_keeps_the_hint_check():
    draft_values = make_draft_values()
    draft_values["hint"] = "Use works."

    with pytest.raises(ValidationError, match="gives the expected answer"):
        GapExerciseDraft(**draft_values)


def test_a_gap_exercise_is_built_from_a_draft_plus_skill_and_level():
    draft = GapExerciseDraft(**make_draft_values())

    gap_exercise = GapExercise(**draft.model_dump(), skill_id="present_simple", level="A2")

    assert gap_exercise.sentence == draft.sentence
    assert gap_exercise.skill_id == "present_simple"
    assert gap_exercise.level == "A2"


@pytest.mark.parametrize("used_sentence", ["She ___ (work) in a bank.", "she ___ (work)   in a BANK."])
def test_a_sentence_already_used_for_the_skill_is_refused(used_sentence):
    # Identical after normalizing (capital letters and spaces) = already used.
    draft_schema = make_gap_exercise_draft_schema([used_sentence])

    with pytest.raises(ValidationError, match="already used"):
        draft_schema(**make_draft_values())


def test_a_new_sentence_is_accepted_by_the_schema_with_used_sentences():
    draft_schema = make_gap_exercise_draft_schema(["He ___ (live) in Lisbon."])

    draft = draft_schema(**make_draft_values())

    assert draft.expected_answer == "works"


def test_the_used_sentences_are_not_sent_to_the_ai():
    # used_sentences is a ClassVar, not a field: it is not in the JSON schema that the AI receives.
    draft_schema = make_gap_exercise_draft_schema(["He ___ (live) in Lisbon."])

    schema_fields = draft_schema.model_json_schema()["properties"]

    assert list(schema_fields) == ["sentence", "signal", "expected_answer", "accepted_answers", "trap", "trap_why",
                                   "hint"]


def test_the_plain_draft_has_no_used_sentences():
    make_gap_exercise_draft_schema(["She ___ (work) in a bank."])

    draft = GapExerciseDraft(**make_draft_values())

    assert draft.sentence == "She ___ (work) in a bank."


# ---------- a batch of exercises: each item is checked alone ----------

def make_item_values(sentence, signal, expected_answer, hint):
    return {"sentence": sentence, "signal": signal, "expected_answer": expected_answer, "accepted_answers": [],
            "trap": "a wrong answer", "trap_why": TRAP_WHY, "hint": hint}


def make_items(item_values_list):
    items = []

    for item_values in item_values_list:
        items.append(GapExerciseItem(**item_values))

    return items


GOOD_ITEM = make_item_values("She ___ (work) in a bank.", "in a bank", "works", "this is her job")
SECOND_GOOD_ITEM = make_item_values("He ___ (live) in Lisbon.", "in Lisbon", "lives", "his home town")
HINT_GIVES_THE_ANSWER = make_item_values("They ___ (play) tennis.", "tennis", "play", "they play every Sunday")
NO_GAP = make_item_values("We work in an office.", "in an office", "work", "our job")


def test_split_keeps_the_good_items_and_drops_the_bad_ones_with_a_reason():
    items = make_items([GOOD_ITEM, HINT_GIVES_THE_ANSWER, SECOND_GOOD_ITEM, NO_GAP])

    valid_items, rejected_items = split_gap_exercise_items(items, GapExerciseDraft)

    valid_positions = []

    for position, draft in valid_items:
        valid_positions.append(position)

    assert valid_positions == [0, 2]
    assert rejected_items[0]["position"] == 1
    assert "gives the expected answer" in rejected_items[0]["reason"]
    assert rejected_items[1]["position"] == 3
    assert "exactly one gap" in rejected_items[1]["reason"]
    assert rejected_items[1]["item"]["sentence"] == "We work in an office."


def test_split_drops_the_second_copy_of_a_sentence_in_the_same_batch():
    same_sentence_again = make_item_values("she ___ (WORK) in a bank.", "in a bank", "works", "her job again")
    items = make_items([GOOD_ITEM, same_sentence_again])

    valid_items, rejected_items = split_gap_exercise_items(items, GapExerciseDraft)

    assert len(valid_items) == 1
    assert rejected_items[0]["reason"] == "the same sentence twice in one batch"


def test_split_drops_a_sentence_already_saved_for_the_skill():
    draft_schema = make_gap_exercise_draft_schema(["She ___ (work) in a bank."])
    items = make_items([GOOD_ITEM, SECOND_GOOD_ITEM])

    valid_items, rejected_items = split_gap_exercise_items(items, draft_schema)

    assert len(valid_items) == 1
    assert valid_items[0][1].sentence == "He ___ (live) in Lisbon."
    assert "already used" in rejected_items[0]["reason"]


def test_a_batch_with_one_bad_item_is_still_accepted():
    batch = GapExerciseBatch(exercises=[GOOD_ITEM, HINT_GIVES_THE_ANSWER])

    assert len(batch.exercises) == 2


def test_a_batch_with_no_valid_item_is_an_invalid_answer():
    # llm.ask() sees a ValidationError and retries once.
    with pytest.raises(ValidationError, match="no valid exercise in the batch"):
        GapExerciseBatch(exercises=[HINT_GIVES_THE_ANSWER, NO_GAP])


def test_a_batch_where_every_sentence_was_already_saved_is_an_invalid_answer():
    batch_schema = make_gap_exercise_batch_schema(["She ___ (work) in a bank."], "base_word")

    with pytest.raises(ValidationError, match="already used"):
        batch_schema(exercises=[GOOD_ITEM])


def test_the_batch_schema_sent_to_the_ai_has_only_the_exercises_list():
    batch_schema = make_gap_exercise_batch_schema(["She ___ (work) in a bank."], "base_word")

    json_schema = batch_schema.model_json_schema()
    item_fields = json_schema["$defs"]["GapExerciseItem"]["properties"]

    assert list(json_schema["properties"]) == ["exercises"]
    assert list(item_fields) == ["sentence", "signal", "expected_answer", "accepted_answers", "trap", "trap_why",
                                 "hint"]


# ---------- the clue after the gap must match the skill (Step 2, Part 3b) ----------

def make_clue_draft_values(sentence, signal, expected_answer):
    return {"sentence": sentence, "signal": signal, "expected_answer": expected_answer, "accepted_answers": [],
            "trap": "a wrong answer", "trap_why": TRAP_WHY, "hint": "a short clue"}


@pytest.mark.parametrize("gap_clue, sentence, signal, expected_answer", [
    ("base_word", "She ___ (work) in a bank every day.", "every day", "works"),
    ("base_word", "If we had left earlier, we ___ (not / miss) the train.", "had left", "wouldn't have missed"),
    ("words", "What ___ (he / ask) for in this email?", "What", "is he asking"),
    ("portuguese", "I ___ (perder) the bus, so I was late for work.", "so I was late", "missed"),
    ("none", "My sister is ___ engineer at a big company.", "engineer", "an"),
])
def test_a_sentence_with_the_clue_of_its_skill_is_accepted(gap_clue, sentence, signal, expected_answer):
    draft_schema = make_gap_exercise_draft_schema([], gap_clue)

    draft = draft_schema(**make_clue_draft_values(sentence, signal, expected_answer))

    assert draft.sentence == sentence


@pytest.mark.parametrize("gap_clue, sentence, error_text", [
    ("none", "She is ___ (be) nurse every day.", "has no clue, but the sentence has brackets"),
    ("none", "She (Ana) is ___ nurse every day.", "has no clue, but the sentence has brackets"),
    ("base_word", "She ___ in a bank every day.", "one clue in round brackets right after the gap"),
    ("base_word", "She (work) ___ in a bank every day.", "one clue in round brackets right after the gap"),
    ("base_word", "She ___ () in a bank every day.", "one clue in round brackets right after the gap"),
    ("words", "She ___ (work) in a bank (Lisbon) every day.", "one clue in round brackets right after the gap"),
    ("base_word", "She ___ [work] in a bank every day.", "square brackets"),
])
def test_a_sentence_with_the_wrong_clue_is_refused(gap_clue, sentence, error_text):
    # Every sentence contains the signal "every day", so only the clue check can refuse it.
    draft_schema = make_gap_exercise_draft_schema([], gap_clue)

    with pytest.raises(ValidationError, match=error_text):
        draft_schema(**make_clue_draft_values(sentence, "every day", "works"))


def test_a_portuguese_clue_that_contains_the_english_answer_is_refused():
    draft_schema = make_gap_exercise_draft_schema([], "portuguese")
    draft_values = make_clue_draft_values("I ___ (missed / perder) the bus, so I was late.", "so I was late",
                                          "missed")

    with pytest.raises(ValidationError, match="contains the English answer"):
        draft_schema(**draft_values)


def test_a_portuguese_clue_that_contains_an_accepted_answer_is_refused():
    draft_schema = make_gap_exercise_draft_schema([], "portuguese")
    draft_values = make_clue_draft_values("Please ___ (fill out) this form before Friday.", "this form",
                                          "fill in")
    draft_values["accepted_answers"] = ["fill out"]

    with pytest.raises(ValidationError, match="contains the English answer"):
        draft_schema(**draft_values)


def test_the_plain_draft_does_not_check_the_clue():
    # The Step 1 prompt (kept as a record) has no clue type: any brackets pass, as before.
    draft = GapExerciseDraft(**make_clue_draft_values("She ___ [work] in a bank every day.", "every day",
                                                      "works"))

    assert draft.expected_answer == "works"


def test_the_clue_type_is_not_sent_to_the_ai():
    batch_schema = make_gap_exercise_batch_schema([], "portuguese")

    item_fields = batch_schema.model_json_schema()["$defs"]["GapExerciseItem"]["properties"]

    assert "gap_clue" not in item_fields


@pytest.mark.parametrize("sentence, signal, expected_answer, accepted_answers", [
    ("I cleaned the dataset ___ (last week).", "cleaned", "last week", []),
    ("___ (life) is hard for many families.", "many families", "Life", []),
    ("My sister is ___ (engineer) at a big company.", "big company", "an engineer", []),
    ("I am waiting ___ (the bus stop) near the office.", "near the office", "at the bus stop", ["by the bus stop"]),
])
def test_an_add_words_answer_that_ends_with_the_clue_is_accepted(sentence, signal, expected_answer,
                                                                 accepted_answers):
    # Capital letters do not matter: (life) → "Life".
    draft_schema = make_gap_exercise_draft_schema([], "add_words")
    draft_values = make_clue_draft_values(sentence, signal, expected_answer)
    draft_values["accepted_answers"] = accepted_answers

    draft = draft_schema(**draft_values)

    assert draft.expected_answer == expected_answer


@pytest.mark.parametrize("expected_answer, accepted_answers", [
    ("communication", []),             # the demo bug: the whole noun in the gap, not the clue
    ("in last weekend", []),           # "weekend" is not "week": whole words only
    ("last week", ["the week before"]),
])
def test_an_add_words_answer_that_does_not_end_with_the_clue_is_refused(expected_answer, accepted_answers):
    draft_schema = make_gap_exercise_draft_schema([], "add_words")
    draft_values = make_clue_draft_values("I cleaned the dataset ___ (last week) with Ana.", "with Ana",
                                          expected_answer)
    draft_values["accepted_answers"] = accepted_answers

    with pytest.raises(ValidationError, match="does not end with the words in brackets"):
        draft_schema(**draft_values)


# ---------- the trap: the likely wrong answer (Step 2, Part 3b) ----------

@pytest.mark.parametrize("field_name", ["trap", "trap_why"])
def test_an_empty_trap_field_is_refused(field_name):
    draft_values = make_draft_values()
    draft_values[field_name] = "  "

    with pytest.raises(ValidationError, match="the " + field_name + " is empty"):
        GapExerciseDraft(**draft_values)


@pytest.mark.parametrize("trap, accepted_answers", [("Works", []), ("does work", ["does work"])])
def test_a_trap_that_is_a_correct_answer_is_refused(trap, accepted_answers):
    # The code grades the trap as wrong, so it can never be correct.
    draft_values = make_draft_values()
    draft_values["trap"] = trap
    draft_values["accepted_answers"] = accepted_answers

    with pytest.raises(ValidationError, match="the trap is a correct answer"):
        GapExerciseDraft(**draft_values)


def test_the_trap_fields_lose_their_spaces():
    draft_values = make_draft_values()
    draft_values["trap"] = "  work "

    draft = GapExerciseDraft(**draft_values)

    assert draft.trap == "work"


def test_a_batch_drops_the_items_with_the_wrong_clue_and_keeps_the_others():
    # The bug of 2026-11-19: a verb in brackets for a word_choice exercise.
    batch_schema = make_gap_exercise_batch_schema([], "portuguese")
    good_item = make_clue_draft_values("I ___ (perder) the bus, so I was late for work.", "so I was late", "missed")
    tense_item = make_clue_draft_values("Last week, the team ___ [clean] the dataset.", "Last week", "cleaned")
    items = make_items([good_item, tense_item])

    valid_items, rejected_items = split_gap_exercise_items(items, batch_schema.strict_draft_schema)

    assert len(valid_items) == 1
    assert "square brackets" in rejected_items[0]["reason"]


# ---------- the signal: the words that make only the tested form natural ----------

def make_signal_draft_values(sentence, signal):
    draft_values = make_draft_values()
    draft_values["sentence"] = sentence
    draft_values["signal"] = signal

    return draft_values


@pytest.mark.parametrize("sentence, signal, cleaned_signal", [
    ("The museum ___ (open) at nine every morning.", "every morning", "every morning"),
    ("The museum ___ (open) at nine every morning.", "  Every Morning. ", "Every Morning"),
    ("She always ___ (ask) for a passport.", "always", "always"),
])
def test_a_signal_from_the_sentence_is_accepted(sentence, signal, cleaned_signal):
    draft = GapExerciseDraft(**make_signal_draft_values(sentence, signal))

    assert draft.signal == cleaned_signal


@pytest.mark.parametrize("signal, error_text", [
    ("", "signal is empty"),
    (" . ", "signal is empty"),
    ("every evening", "not in the sentence"),
    ("morn", "not in the sentence"),           # part of a word is not a whole word
    ("___", "signal is the gap"),
    ("museum ___", "signal is the gap"),
    ("(open)", "verb in brackets"),
    ("open", "verb in brackets"),
])
def test_a_bad_signal_is_refused(signal, error_text):
    draft_values = make_signal_draft_values("The museum ___ (open) at nine every morning.", signal)

    with pytest.raises(ValidationError, match=error_text):
        GapExerciseDraft(**draft_values)


def test_a_batch_item_with_a_bad_signal_is_dropped_alone():
    bad_signal_item = make_item_values("He ___ (live) in Lisbon.", "today", "lives", "his home town")
    items = make_items([GOOD_ITEM, bad_signal_item])

    valid_items, rejected_items = split_gap_exercise_items(items, GapExerciseDraft)

    assert len(valid_items) == 1
    assert "not in the sentence" in rejected_items[0]["reason"]
