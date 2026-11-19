"""Tests for tutor/prompts.py: prompt versions and the fill-the-gap prompt (ONE skill)."""

import re

import pytest

from tutor import prompts, skills
from tutor.schemas import Exercise


def build_prompt_for(skill_id, sentences_to_avoid):
    return prompts.build_gap_exercise_prompt("A2", "travel", "a delayed flight", skills.get_skill(skill_id),
                                             sentences_to_avoid)


def test_prompt_version_has_the_name_and_a_short_hash():
    prompt_version = prompts.make_prompt_version("gap_exercise", "Some template {level}")

    assert re.fullmatch("gap_exercise@[0-9a-f]{6}", prompt_version)


def test_the_same_template_with_different_values_gives_the_same_version():
    a2_prompt_text, a2_prompt_version = build_prompt_for("to_be", [])
    c1_prompt_text, c1_prompt_version = prompts.build_gap_exercise_prompt(
        "C1", "meetings", "a daily stand-up", skills.get_skill("inversion"), ["Never ___ I seen this."])

    assert a2_prompt_text != c1_prompt_text
    assert a2_prompt_version == c1_prompt_version


def test_changing_one_word_in_the_template_gives_a_new_version():
    original_template = prompts.GAP_EXERCISE_TEMPLATE
    changed_template = original_template.replace("ONE", "One", 1)

    original_version = prompts.make_prompt_version("gap_exercise", original_template)
    changed_version = prompts.make_prompt_version("gap_exercise", changed_template)

    assert changed_template != original_template
    assert changed_version != original_version


def test_the_prompt_has_level_topic_sub_topic_and_the_skill():
    skill = skills.get_skill("past_simple")

    prompt_text, prompt_version = build_prompt_for("past_simple", [])

    assert "Level (CEFR): A2" in prompt_text
    assert "Topic: travel" in prompt_text
    assert "Situation for the sentence: a delayed flight" in prompt_text
    assert skill["name"] in prompt_text
    assert skill["typical_mistake"] in prompt_text
    assert prompt_version.startswith("gap_exercise@")


def test_the_prompt_says_the_typical_mistake_is_only_an_illustration():
    prompt_text, prompt_version = build_prompt_for("to_be", [])

    assert "only an illustration" in prompt_text
    assert "Do not reuse its sentence or its words" in prompt_text


def test_the_tag_when_line_is_there_when_the_skill_has_one():
    prompt_text, prompt_version = build_prompt_for("past_simple", [])

    assert "Use this skill exactly when: " + skills.get_skill("past_simple")["tag_when"] in prompt_text


def test_the_tag_when_line_is_left_out_when_the_skill_has_none():
    assert "tag_when" not in skills.get_skill("to_be")

    prompt_text, prompt_version = build_prompt_for("to_be", [])

    assert "Use this skill exactly when" not in prompt_text


def test_the_prompt_lists_the_sentences_to_avoid():
    sentences_to_avoid = ["I ___ tired today.", "They ___ at home now."]

    prompt_text, prompt_version = build_prompt_for("to_be", sentences_to_avoid)

    assert "- I ___ tired today.\n- They ___ at home now." in prompt_text


def test_the_prompt_says_none_when_there_are_no_sentences_to_avoid():
    prompt_text, prompt_version = build_prompt_for("to_be", [])

    assert "Write a clearly different one (another verb, other words, another idea):\nnone" in prompt_text


def test_the_prompt_has_no_other_skill_ids():
    # The code chose the skill: the AI must not see a list of skills to choose from.
    prompt_text, prompt_version = build_prompt_for("to_be", [])

    for skill_id in skills.get_fill_the_gap_skill_ids():
        if "_" in skill_id:
            assert skill_id not in prompt_text, skill_id + " should not be in the prompt"


def test_the_prompt_has_no_empty_places_left():
    prompt_text, prompt_version = build_prompt_for("past_simple", ["I ___ (go) home."])

    assert "{" not in prompt_text
    assert "}" not in prompt_text


# ---------- the batch prompt (Step 2) ----------

BATCH_SUB_TOPICS = ["a delayed flight", "checking in at a hotel", "a lost suitcase"]


def build_batch_prompt_for(skill_id, sentences_to_avoid):
    return prompts.build_gap_exercise_batch_prompt("A2", "travel", BATCH_SUB_TOPICS, skills.get_skill(skill_id),
                                                   sentences_to_avoid, [])


def test_the_batch_prompt_lists_one_numbered_situation_per_exercise():
    prompt_text, prompt_version = build_batch_prompt_for("to_be", [])

    assert "Write 3 fill-the-gap exercises" in prompt_text
    assert "1. a delayed flight\n2. checking in at a hotel\n3. a lost suitcase" in prompt_text
    assert prompt_version.startswith("gap_exercise_batch@")


def test_the_batch_prompt_has_the_skill_the_tag_when_and_the_sentences_to_avoid():
    skill = skills.get_skill("past_simple")

    prompt_text, prompt_version = build_batch_prompt_for("past_simple", ["I ___ (go) home."])

    assert skill["name"] in prompt_text
    assert skill["typical_mistake"] in prompt_text
    assert "Use this skill exactly when: " + skill["tag_when"] in prompt_text
    assert "- I ___ (go) home." in prompt_text


def test_the_batch_prompt_asks_for_hints_about_meaning_not_grammar():
    prompt_text, prompt_version = build_batch_prompt_for("to_be", [])

    assert "clue about the MEANING" in prompt_text
    assert "Do not name the" in prompt_text


def test_the_batch_prompt_asks_for_a_signal_that_makes_only_the_tested_answer_natural():
    prompt_text, prompt_version = build_batch_prompt_for("to_be", [])

    assert "makes the answer of the tested skill the ONLY natural answer" in prompt_text
    assert "no signal that calls for\n  another answer" in prompt_text
    assert "read each sentence again with the gap filled" in prompt_text
    assert "Use vocabulary at the A2 level or easier, and grammar at the A2 level or easier" in prompt_text


def test_the_batch_prompt_says_the_gap_tests_only_its_skill():
    # The bug of 2026-11-19: word_choice exercises that tested tenses.
    prompt_text, prompt_version = build_batch_prompt_for("word_choice", [])

    assert "The gap must test the skill above and nothing else" in prompt_text


def test_the_batch_prompt_no_longer_speaks_about_time_words_or_verb_forms():
    template_in_small_letters = prompts.GAP_EXERCISE_BATCH_TEMPLATE.lower()

    for tense_words in ["time word", "base verb", "verb form", "another tense"]:
        assert tense_words not in template_in_small_letters, tense_words


@pytest.mark.parametrize("skill_id, gap_clue", [("past_simple", "base_word"), ("questions_negatives", "words"),
                                                ("word_choice", "portuguese"), ("articles_a_an", "add_words"),
                                                ("to_be", "none")])
def test_the_batch_prompt_has_only_the_clue_rules_of_the_skill(skill_id, gap_clue):
    prompt_text, prompt_version = build_batch_prompt_for(skill_id, [])

    for clue_type, clue_rules in prompts.GAP_CLUE_RULES.items():
        if clue_type == gap_clue:
            assert clue_rules in prompt_text, clue_type
        else:
            assert clue_rules not in prompt_text, clue_type


def test_the_batch_prompt_asks_for_a_trap_that_is_clearly_wrong_and_its_reason():
    prompt_text, prompt_version = build_batch_prompt_for("present_simple", [])

    assert "- trap: the wrong answer a Portuguese speaker would most likely write" in prompt_text
    assert "not half right, not a spelling slip, and not\n  a mistake of another skill" in prompt_text
    assert "- trap_why: for a learner who wrote the trap" in prompt_text
    assert "Then read it with the trap: the trap\nmust be clearly wrong." in prompt_text


def test_the_add_words_clue_says_the_answer_ends_with_the_words_in_brackets():
    prompt_text, prompt_version = build_batch_prompt_for("prepositions_time", [])

    assert "The expected answer and every accepted answer end with the words in brackets" in prompt_text
    assert "with nothing before them when no word is needed" in prompt_text


def test_word_traps_are_added_to_their_situation_lines():
    word_traps = skills.WORD_TRAPS["false_friends"][:3]

    prompt_text, prompt_version = prompts.build_gap_exercise_batch_prompt(
        "B1", "travel", BATCH_SUB_TOPICS, skills.get_skill("false_friends"), [], word_traps)

    assert ("1. a delayed flight | Portuguese word: atualmente | answer: currently | trap: actually"
            " | the answer is right for: at the present time") in prompt_text
    assert "2. checking in at a hotel | Portuguese word: assistir a | answer: attend | trap: assist" in prompt_text


def test_a_pair_with_other_right_answers_lists_them_on_its_line():
    costume_trap = None

    for word_trap in skills.WORD_TRAPS["false_friends"]:
        if word_trap["portuguese"] == "costume":
            costume_trap = word_trap

    prompt_text, prompt_version = prompts.build_gap_exercise_batch_prompt(
        "B1", "travel", ["a delayed flight"], skills.get_skill("false_friends"), [], [costume_trap])

    assert "| trap: costume |" in prompt_text
    assert "| also right, put in accepted_answers: custom" in prompt_text


def test_the_situation_lines_have_no_trap_when_the_skill_has_none():
    prompt_text, prompt_version = build_batch_prompt_for("present_simple", [])

    assert "1. a delayed flight\n2. checking in at a hotel\n3. a lost suitcase" in prompt_text
    assert "Portuguese word:" not in prompt_text


def test_word_traps_need_one_pair_per_situation():
    word_traps = skills.WORD_TRAPS["false_friends"][:2]

    with pytest.raises(ValueError, match="one pair per sub-topic"):
        prompts.build_gap_exercise_batch_prompt("B1", "travel", BATCH_SUB_TOPICS, skills.get_skill("false_friends"),
                                                [], word_traps)


def test_the_word_trap_values_do_not_change_the_prompt_version():
    word_traps = skills.WORD_TRAPS["false_friends"][:3]
    prompt_text, version_without_traps = build_batch_prompt_for("present_simple", [])

    prompt_text, version_with_traps = prompts.build_gap_exercise_batch_prompt(
        "B1", "travel", BATCH_SUB_TOPICS, skills.get_skill("false_friends"), [], word_traps)

    assert version_with_traps == version_without_traps


def test_every_clue_type_has_clue_rules():
    assert sorted(prompts.GAP_CLUE_RULES) == sorted(skills.GAP_CLUE_TYPES)


def test_the_portuguese_clue_asks_for_european_portuguese_and_never_the_answer():
    portuguese_rules = prompts.GAP_CLUE_RULES["portuguese"]

    assert "European Portuguese, from Portugal" in portuguese_rules
    assert "Never write the English answer" in portuguese_rules


def test_the_prompt_version_is_the_same_for_every_clue_type():
    base_word_text, base_word_version = build_batch_prompt_for("past_simple", [])
    portuguese_text, portuguese_version = build_batch_prompt_for("word_choice", [])

    assert base_word_version == portuguese_version


def test_changing_one_clue_block_gives_a_new_prompt_version(monkeypatch):
    prompt_text, old_prompt_version = build_batch_prompt_for("past_simple", [])
    changed_clue_rules = dict(prompts.GAP_CLUE_RULES)
    changed_clue_rules["none"] = changed_clue_rules["none"] + " One more word."
    monkeypatch.setattr(prompts, "GAP_CLUE_RULES", changed_clue_rules)

    # past_simple does not use the "none" block, but its version must still change.
    prompt_text, new_prompt_version = build_batch_prompt_for("past_simple", [])

    assert new_prompt_version != old_prompt_version


def test_both_prompts_ask_for_the_signal():
    single_prompt_text, single_prompt_version = build_prompt_for("to_be", [])
    batch_prompt_text, batch_prompt_version = build_batch_prompt_for("to_be", [])

    assert "- signal: the exact words of your sentence" in single_prompt_text
    assert "- signal: the exact words of your sentence" in batch_prompt_text
    assert "If you cannot point to a signal, the sentence is ambiguous" in batch_prompt_text


def test_the_batch_template_has_no_example_of_one_particular_skill():
    # The template is shared by ALL skills: an example of one tense would push every skill toward it.
    # Examples come only from the skill itself (its typical mistake and tag_when).
    template_in_small_letters = prompts.GAP_EXERCISE_BATCH_TEMPLATE.lower()

    for skill_specific_text in ["present simple", "(work)", "she ___", "every weekday"]:
        assert skill_specific_text not in template_in_small_letters, skill_specific_text

    # The clue blocks too: each one is shared by many skills.
    for clue_type, clue_rules in prompts.GAP_CLUE_RULES.items():
        assert "___ (" not in clue_rules, clue_type
        assert "(perder)" not in clue_rules, clue_type
        assert "(fazer)" not in clue_rules, clue_type


def test_the_batch_prompt_version_does_not_depend_on_the_values():
    a2_prompt_text, a2_prompt_version = build_batch_prompt_for("to_be", [])
    c1_prompt_text, c1_prompt_version = prompts.build_gap_exercise_batch_prompt(
        "C1", "meetings", ["a daily stand-up"], skills.get_skill("inversion"), ["Never ___ I seen this."], [])

    assert a2_prompt_text != c1_prompt_text
    assert a2_prompt_version == c1_prompt_version


def test_the_batch_prompt_has_no_other_skill_ids_and_no_empty_places():
    prompt_text, prompt_version = build_batch_prompt_for("to_be", [])

    for skill_id in skills.get_fill_the_gap_skill_ids():
        if "_" in skill_id:
            assert skill_id not in prompt_text, skill_id + " should not be in the prompt"

    assert "{" not in prompt_text
    assert "}" not in prompt_text


# ---------- the grader prompt (Step 2, Part 2) ----------

def make_exercise(skill_id, sentence, expected_answer, accepted_answers):
    return Exercise(section="practice", exercise_type="gap", skill_id=skill_id, level="A2", prompt_text=sentence,
                    expected_answer=expected_answer, accepted_answers=accepted_answers)


def build_grade_prompt_for(skill_id, accepted_answers, explanation_language):
    exercise = make_exercise(skill_id, "She has ___ (finish) the report already.", "finished", accepted_answers)

    return prompts.build_gap_grade_prompt(exercise, "finish", "She has finish the report already.",
                                          explanation_language)


def test_the_grade_prompt_has_the_exercise_my_answer_and_my_full_sentence():
    prompt_text, prompt_version = build_grade_prompt_for("present_perfect", [], "English")

    assert "Exercise: She has ___ (finish) the report already." in prompt_text
    assert "Expected answer: finished" in prompt_text
    assert "The learner's answer: finish" in prompt_text
    assert "The learner's full sentence: She has finish the report already." in prompt_text
    assert skills.get_skill("present_perfect")["name"] in prompt_text


def test_the_grade_prompt_lists_the_accepted_answers_or_none():
    prompt_without_accepted, prompt_version = build_grade_prompt_for("present_perfect", [], "English")
    prompt_with_accepted, prompt_version = build_grade_prompt_for("present_perfect", ["completed", "done"], "English")

    assert "Other accepted answers: none" in prompt_without_accepted
    assert "Other accepted answers: completed, done" in prompt_with_accepted


def test_the_grade_prompt_has_the_tag_when_lines_of_the_other_skills():
    prompt_text, prompt_version = build_grade_prompt_for("present_perfect", [], "English")

    assert "- irregular_verbs: " + skills.get_skill("irregular_verbs")["tag_when"] in prompt_text
    assert "- spelling: " + skills.get_skill("spelling")["tag_when"] in prompt_text


def test_the_tested_skill_is_not_in_the_detectable_lines():
    # irregular_verbs is tested: its tag_when is the tested skill's line, not a "- irregular_verbs:" line.
    tag_when_lines = prompts.make_detectable_tag_when_lines("irregular_verbs")

    assert "- irregular_verbs:" not in tag_when_lines
    assert "- spelling:" in tag_when_lines


def test_only_learning_skills_with_a_tag_when_are_listed():
    tag_when_lines = prompts.make_detectable_tag_when_lines("to_be").split("\n")
    expected_line_count = 0

    for skill in skills.get_learning_skills():
        if "tag_when" in skill:
            expected_line_count = expected_line_count + 1

    assert len(tag_when_lines) == expected_line_count


def test_the_grade_prompt_uses_the_explanation_language():
    prompt_text, prompt_version = build_grade_prompt_for("present_perfect", [], "Portuguese (Portugal)")

    assert "in Portuguese (Portugal)." in prompt_text
    assert prompts.DEFAULT_EXPLANATION_LANGUAGE == "English"


def test_the_grade_prompt_version_does_not_depend_on_the_values():
    first_prompt_text, first_version = build_grade_prompt_for("present_perfect", [], "English")
    second_prompt_text, second_version = build_grade_prompt_for("irregular_verbs", ["done"], "Portuguese")

    assert first_prompt_text != second_prompt_text
    assert first_version == second_version
    assert first_version.startswith("gap_grade@")


def test_the_quote_retry_note_names_the_bad_quotes_and_my_sentence():
    prompt_text, prompt_version = build_grade_prompt_for("present_perfect", [], "English")

    retry_prompt_text = prompts.add_retry_notes(prompt_text, ["have finish"], False,
                                                "She has finish the report already.")

    assert retry_prompt_text.startswith(prompt_text)
    assert "\"have finish\"" in retry_prompt_text
    assert "exactly from this sentence: She has finish the report already." in retry_prompt_text
    assert prompts.GAP_GRADE_SAME_WORDS_RETRY_NOTE not in retry_prompt_text


def test_the_same_words_note_is_added_alone_or_with_the_quote_note():
    prompt_text, prompt_version = build_grade_prompt_for("present_perfect", [], "English")

    same_words_only = prompts.add_retry_notes(prompt_text, [], True, "She has writed the report already.")
    both_notes = prompts.add_retry_notes(prompt_text, ["wrote"], True, "She has writed the report already.")

    assert same_words_only == prompt_text + prompts.GAP_GRADE_SAME_WORDS_RETRY_NOTE
    assert "\"wrote\"" in both_notes
    assert both_notes.endswith(prompts.GAP_GRADE_SAME_WORDS_RETRY_NOTE)


def test_the_grade_prompt_has_no_place_left_empty():
    prompt_text, prompt_version = build_grade_prompt_for("present_perfect", [], "English")

    assert "{" not in prompt_text
    assert "}" not in prompt_text
