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
