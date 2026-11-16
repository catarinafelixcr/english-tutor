"""Tests for tutor/prompts.py: prompt versions and the fill-the-gap prompt (ONE skill)."""

import re

from tutor import prompts, skills


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
                                                   sentences_to_avoid)


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


def test_the_batch_prompt_asks_for_a_signal_that_makes_only_the_tested_form_natural():
    prompt_text, prompt_version = build_batch_prompt_for("to_be", [])

    assert "makes the form of the tested skill the ONLY natural answer" in prompt_text
    assert "no signal that calls for another\n  form" in prompt_text
    assert "read each sentence again with the gap filled" in prompt_text
    assert "Use vocabulary at the A2 level or easier" in prompt_text


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


def test_the_batch_prompt_version_does_not_depend_on_the_values():
    a2_prompt_text, a2_prompt_version = build_batch_prompt_for("to_be", [])
    c1_prompt_text, c1_prompt_version = prompts.build_gap_exercise_batch_prompt(
        "C1", "meetings", ["a daily stand-up"], skills.get_skill("inversion"), ["Never ___ I seen this."])

    assert a2_prompt_text != c1_prompt_text
    assert a2_prompt_version == c1_prompt_version


def test_the_batch_prompt_has_no_other_skill_ids_and_no_empty_places():
    prompt_text, prompt_version = build_batch_prompt_for("to_be", [])

    for skill_id in skills.get_fill_the_gap_skill_ids():
        if "_" in skill_id:
            assert skill_id not in prompt_text, skill_id + " should not be in the prompt"

    assert "{" not in prompt_text
    assert "}" not in prompt_text
