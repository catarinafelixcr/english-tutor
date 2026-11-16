"""Tests for tutor/prompts.py: prompt versions and the fill-the-gap prompt."""

import re

from tutor import prompts, skills


def test_prompt_version_has_the_name_and_a_short_hash():
    prompt_version = prompts.make_prompt_version("gap_exercise", "Some template {level}")

    assert re.fullmatch("gap_exercise@[0-9a-f]{6}", prompt_version)


def test_the_same_template_with_different_values_gives_the_same_version():
    a2_skills = [skills.get_skill("to_be")]
    c1_skills = [skills.get_skill("inversion"), skills.get_skill("mixed_conditionals")]

    a2_prompt_text, a2_prompt_version = prompts.build_gap_exercise_prompt("A2", "travel", a2_skills)
    c1_prompt_text, c1_prompt_version = prompts.build_gap_exercise_prompt("C1", "meetings", c1_skills)

    assert a2_prompt_text != c1_prompt_text
    assert a2_prompt_version == c1_prompt_version


def test_changing_one_word_in_the_template_gives_a_new_version():
    original_template = prompts.GAP_EXERCISE_TEMPLATE
    changed_template = original_template.replace("ONE", "One", 1)

    original_version = prompts.make_prompt_version("gap_exercise", original_template)
    changed_version = prompts.make_prompt_version("gap_exercise", changed_template)

    assert changed_template != original_template
    assert changed_version != original_version


def test_gap_exercise_prompt_contains_level_topic_and_every_skill_id():
    skill_list = skills.get_fill_the_gap_skills()

    prompt_text, prompt_version = prompts.build_gap_exercise_prompt("B1", "data science and work", skill_list)

    assert "Level (CEFR): B1" in prompt_text
    assert "Topic of the sentence: data science and work" in prompt_text
    assert prompt_version.startswith("gap_exercise@")

    for skill in skill_list:
        assert skill["id"] + " | " in prompt_text, skill["id"] + " is missing from the prompt"


def test_gap_exercise_prompt_has_no_empty_places_left():
    prompt_text, prompt_version = prompts.build_gap_exercise_prompt("A2", "travel", [skills.get_skill("to_be")])

    assert "{" not in prompt_text
    assert "}" not in prompt_text
