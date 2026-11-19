"""Tests for tutor/skills.py: the fixed skill list must stay clean and complete."""

import re

import pytest

from tutor import skills

REQUIRED_FIELDS = ["id", "name", "level", "category", "active", "typical_mistake"]
OPTIONAL_FIELDS = ["tag_when"]

# Rule 10 in CLAUDE.md: skill ids are never renamed or deleted.
# Every id here must stay in skills.py forever. When you add a new skill, add its id here too.
PERMANENT_SKILL_IDS = [
    "to_be", "there_is_are", "present_simple", "present_continuous", "past_simple", "irregular_verbs",
    "past_continuous", "present_perfect", "present_perfect_for_since", "future_forms", "used_to",
    "gerund_infinitive", "past_perfect", "reported_speech",
    "modals_base_verb", "modals_obligation", "modals_deduction",
    "articles_a_an", "articles_no_article",
    "uncountable_nouns", "much_many",
    "prepositions_time", "prepositions_place", "dependent_prepositions",
    "subject_pronouns", "possessive_pronouns", "relative_pronouns",
    "comparatives_superlatives", "too_enough",
    "conditional_first", "conditional_second", "conditional_third", "wish", "mixed_conditionals",
    "passive_voice", "have_something_done", "passive_reporting",
    "questions_negatives", "adjective_position", "adverb_position", "indirect_questions", "inversion",
    "phrasal_verbs_common", "phrasal_verbs_separable",
    "make_do", "common_collocations",
    "word_choice", "false_friends",
    "spelling", "capitalization",
    "writing_general", "listening", "speaking",
]

GENERAL_SKILL_IDS = ["writing_general", "listening", "speaking"]

# Skills that overlap with another one must explain when to choose them.
SKILLS_THAT_NEED_TAG_WHEN = [
    "past_simple", "irregular_verbs", "present_perfect", "present_perfect_for_since",
    "make_do", "common_collocations", "word_choice", "false_friends", "spelling", "capitalization",
]


def get_all_skill_ids():
    all_skill_ids = []

    for skill in skills.SKILLS:
        all_skill_ids.append(skill["id"])

    return all_skill_ids


def get_skill_ids_of(skill_list):
    skill_ids = []

    for skill in skill_list:
        skill_ids.append(skill["id"])

    return skill_ids


def make_fake_skill(skill_id, category, is_active):
    return {"id": skill_id, "name": "Fake " + skill_id, "level": "A2", "category": category, "active": is_active,
            "typical_mistake": "wrong → right"}


# ---------- ids ----------

def test_skill_ids_are_unique():
    all_skill_ids = get_all_skill_ids()

    assert len(all_skill_ids) == len(set(all_skill_ids))


def test_permanent_skill_ids_are_never_removed():
    all_skill_ids = get_all_skill_ids()

    for permanent_skill_id in PERMANENT_SKILL_IDS:
        assert permanent_skill_id in all_skill_ids, permanent_skill_id + " was renamed or deleted"


def test_every_skill_id_is_in_the_permanent_list():
    # Keeps PERMANENT_SKILL_IDS up to date: a new skill must be added there too.
    for skill_id in get_all_skill_ids():
        assert skill_id in PERMANENT_SKILL_IDS, skill_id + " is missing from PERMANENT_SKILL_IDS"


def test_skill_ids_use_snake_case():
    for skill in skills.SKILLS:
        assert re.fullmatch("[a-z][a-z0-9_]*", skill["id"]), skill["id"]


# ---------- fields ----------

def test_every_skill_has_the_required_fields_and_no_unknown_field():
    allowed_fields = REQUIRED_FIELDS + OPTIONAL_FIELDS

    for skill in skills.SKILLS:
        for required_field in REQUIRED_FIELDS:
            assert required_field in skill, skill["id"] + " has no " + required_field

        for field_name in skill:
            assert field_name in allowed_fields, skill["id"] + " has an unknown field: " + field_name


def test_names_are_not_empty_and_are_unique():
    all_names = []

    for skill in skills.SKILLS:
        assert skill["name"].strip() != "", skill["id"] + " has an empty name"
        all_names.append(skill["name"])

    assert len(all_names) == len(set(all_names))


def test_active_is_true_or_false():
    for skill in skills.SKILLS:
        assert skill["active"] is True or skill["active"] is False, skill["id"]


def test_overlapping_skills_have_tag_when():
    for skill_id in SKILLS_THAT_NEED_TAG_WHEN:
        skill = skills.get_skill(skill_id)

        assert "tag_when" in skill, skill_id + " needs tag_when"
        assert skill["tag_when"].strip() != "", skill_id


# ---------- levels and categories ----------

def test_every_level_is_valid():
    for skill in skills.SKILLS:
        assert skill["level"] in skills.VALID_LEVELS, skill["id"]


def test_every_level_has_at_least_one_skill():
    used_levels = set()

    for skill in skills.SKILLS:
        used_levels.add(skill["level"])

    for level in skills.VALID_LEVELS:
        assert level in used_levels, level + " has no skill"


def test_every_category_is_valid():
    for skill in skills.SKILLS:
        assert skill["category"] in skills.CATEGORIES, skill["id"]


def test_every_category_has_at_least_one_skill():
    used_categories = set()

    for skill in skills.SKILLS:
        used_categories.add(skill["category"])

    for category in skills.CATEGORIES:
        assert category in used_categories, category + " has no skill"


def test_general_category_has_exactly_the_three_general_skills():
    general_skill_ids = []

    for skill in skills.SKILLS:
        if skill["category"] == "general":
            general_skill_ids.append(skill["id"])

    assert sorted(general_skill_ids) == sorted(GENERAL_SKILL_IDS)


# ---------- typical mistakes ----------

def test_learning_skills_show_mistakes_with_two_different_sides():
    # Every example is "wrong → right": both sides have text, and they are different.
    # A skill can have several examples, separated by " ; ".
    for skill in skills.SKILLS:
        if skill["category"] == "general":
            continue

        examples = skill["typical_mistake"].split(" ; ")

        for example in examples:
            assert example.count("→") == 1, skill["id"] + ": needs exactly one → in: " + example

            wrong_side, right_side = example.split("→")

            assert wrong_side.strip() != "", skill["id"] + ": empty wrong side"
            assert right_side.strip() != "", skill["id"] + ": empty right side"
            assert wrong_side.strip() != right_side.strip(), skill["id"] + ": both sides are the same"


# ---------- helper functions ----------

def test_get_skill_finds_a_known_skill():
    skill = skills.get_skill("to_be")

    assert skill["id"] == "to_be"


def test_get_skill_returns_none_for_an_unknown_skill():
    assert skills.get_skill("invented_skill") is None


def test_is_valid_skill_id():
    assert skills.is_valid_skill_id("present_perfect") is True
    assert skills.is_valid_skill_id("invented_skill") is False


def test_get_active_skills_leaves_out_retired_skills(monkeypatch):
    retired_skill = make_fake_skill("old_skill", "verbs", False)
    active_skill = make_fake_skill("new_skill", "verbs", True)
    monkeypatch.setattr(skills, "SKILLS", [retired_skill, active_skill])

    active_skills = skills.get_active_skills()

    assert active_skills == [active_skill]


def test_get_learning_skills_leaves_out_general_and_retired_skills(monkeypatch):
    learning_skill = make_fake_skill("normal_skill", "verbs", True)
    general_skill = make_fake_skill("general_skill", "general", True)
    retired_skill = make_fake_skill("retired_skill", "verbs", False)
    monkeypatch.setattr(skills, "SKILLS", [learning_skill, general_skill, retired_skill])

    learning_skills = skills.get_learning_skills()

    assert learning_skills == [learning_skill]


def test_get_learning_skills_never_contains_the_real_general_skills():
    learning_skill_ids = get_skill_ids_of(skills.get_learning_skills())

    for general_skill_id in GENERAL_SKILL_IDS:
        assert general_skill_id not in learning_skill_ids


def test_fill_the_gap_skills_never_contain_capitalization_or_general_skills():
    fill_the_gap_skill_ids = skills.get_fill_the_gap_skill_ids()

    assert "capitalization" not in fill_the_gap_skill_ids

    for general_skill_id in GENERAL_SKILL_IDS:
        assert general_skill_id not in fill_the_gap_skill_ids

    assert len(fill_the_gap_skill_ids) == len(skills.get_learning_skills()) - 1


def test_fill_the_gap_skills_up_to_b1_are_the_a2_and_b1_skills():
    selected_skills = skills.get_fill_the_gap_skills_up_to_level("B1")
    selected_levels = set()

    for skill in selected_skills:
        selected_levels.add(skill["level"])

    assert selected_levels == {"A2", "B1"}

    for skill in skills.get_fill_the_gap_skills():
        if skill["level"] in ["A2", "B1"]:
            assert skill in selected_skills, skill["id"] + " is missing"


def test_get_levels_from_gives_this_level_and_the_ones_above():
    assert skills.get_levels_from("A2") == ["A2", "B1", "B2", "C1"]
    assert skills.get_levels_from("B1") == ["B1", "B2", "C1"]
    assert skills.get_levels_from("C1") == ["C1"]


def test_skills_by_category_has_the_same_skills_as_fill_the_gap():
    sorted_skill_ids = get_skill_ids_of(skills.get_fill_the_gap_skills_by_category())

    assert sorted(sorted_skill_ids) == sorted(skills.get_fill_the_gap_skill_ids())


def test_skills_by_category_follow_the_category_order_then_the_level_order():
    sorted_skills = skills.get_fill_the_gap_skills_by_category()

    for position in range(1, len(sorted_skills)):
        previous_skill = sorted_skills[position - 1]
        skill = sorted_skills[position]
        previous_category_number = skills.CATEGORIES.index(previous_skill["category"])
        category_number = skills.CATEGORIES.index(skill["category"])

        assert previous_category_number <= category_number, skill["id"] + " is in the wrong category group"

        if previous_category_number == category_number:
            previous_level_number = skills.VALID_LEVELS.index(previous_skill["level"])
            level_number = skills.VALID_LEVELS.index(skill["level"])

            assert previous_level_number <= level_number, skill["id"] + " comes before an easier skill"


def test_make_skill_label_shows_category_name_and_level():
    label = skills.make_skill_label(skills.get_skill("much_many"))

    assert label == "Nouns and quantifiers · " + skills.get_skill("much_many")["name"] + " (A2)"


def test_skills_as_prompt_text_has_one_line_per_skill_with_tag_when():
    skill_without_tag_when = skills.get_skill("to_be")
    skill_with_tag_when = skills.get_skill("spelling")

    prompt_text = skills.skills_as_prompt_text([skill_without_tag_when, skill_with_tag_when])
    prompt_lines = prompt_text.split("\n")

    assert len(prompt_lines) == 2
    assert prompt_lines[0].startswith("to_be | " + skill_without_tag_when["name"] + " | A2 | typical mistake: ")
    assert "tag when:" not in prompt_lines[0]
    assert prompt_lines[1].endswith(" | tag when: " + skill_with_tag_when["tag_when"])


# ---------- the clue of a fill-the-gap exercise (Step 2, Part 3b) ----------

def test_every_fill_the_gap_skill_has_a_clue_and_no_other_skill_has_one():
    # A new fill-the-gap skill without a clue would crash the batch prompt: this test catches it first.
    assert sorted(skills.GAP_CLUES) == sorted(skills.get_fill_the_gap_skill_ids())


def test_every_clue_is_a_known_clue_type():
    for skill_id, gap_clue in skills.GAP_CLUES.items():
        assert gap_clue in skills.GAP_CLUE_TYPES, skill_id + " has an unknown clue type: " + gap_clue


def test_there_is_no_choice_clue():
    # Two options in brackets are a 50% guess (my rule, 2026-11-19).
    assert "choice" not in skills.GAP_CLUE_TYPES


def test_vocabulary_skills_use_a_portuguese_clue():
    # The Portuguese word is exactly what leads to the typical mistake: perder → lose / miss, fazer → make / do.
    for skill_id in ["word_choice", "false_friends", "make_do", "much_many", "common_collocations"]:
        assert skills.get_gap_clue(skill_id) == "portuguese", skill_id


def test_verb_tense_skills_use_a_base_word_clue():
    for skill_id in ["present_simple", "past_simple", "present_perfect", "conditional_second", "passive_voice"]:
        assert skills.get_gap_clue(skill_id) == "base_word", skill_id


def test_articles_and_prepositions_of_time_and_place_use_the_add_words_clue():
    # Their right answer is often "no word" (last week, life is hard): the clue lets the gap say it.
    for skill_id in ["articles_a_an", "articles_no_article", "prepositions_time", "prepositions_place"]:
        assert skills.get_gap_clue(skill_id) == "add_words", skill_id


# ---------- known Portuguese → English traps ----------

def test_word_traps_are_only_for_fill_the_gap_skills_with_a_portuguese_clue():
    for skill_id in skills.WORD_TRAPS:
        assert skills.get_gap_clue(skill_id) == "portuguese", skill_id


def test_every_word_trap_has_four_filled_fields_and_maybe_also_right():
    for skill_id, word_traps in skills.WORD_TRAPS.items():
        for word_trap in word_traps:
            field_names = sorted(word_trap)

            if "also_right" in field_names:
                field_names.remove("also_right")
                assert len(word_trap["also_right"]) > 0, word_trap["portuguese"]
                assert word_trap["trap"] not in word_trap["also_right"], word_trap["portuguese"]

            assert field_names == ["answer", "portuguese", "trap", "used_for"], skill_id

            for field_name in ["answer", "portuguese", "trap", "used_for"]:
                assert word_trap[field_name].strip() != "", skill_id + ": " + str(word_trap)


def test_a_word_trap_is_never_its_own_answer():
    for skill_id, word_traps in skills.WORD_TRAPS.items():
        for word_trap in word_traps:
            assert word_trap["trap"].lower() != word_trap["answer"].lower(), word_trap["portuguese"]


def test_no_word_trap_pair_is_in_the_list_twice():
    for skill_id, word_traps in skills.WORD_TRAPS.items():
        seen_pairs = []

        for word_trap in word_traps:
            pair = (word_trap["portuguese"], word_trap["answer"])
            assert pair not in seen_pairs, skill_id + ": " + str(pair)
            seen_pairs.append(pair)


def test_every_skill_with_word_traps_has_enough_for_one_batch():
    # A batch of 5 gets 5 DIFFERENT pairs (exercises.BATCH_SIZE; skills.py cannot import exercises.py).
    for skill_id, word_traps in skills.WORD_TRAPS.items():
        assert len(word_traps) >= 5, skill_id


def test_get_word_traps_is_empty_for_a_skill_with_no_list():
    assert skills.get_word_traps("present_simple") == []
    assert skills.get_word_traps("word_choice") == skills.WORD_TRAPS["word_choice"]


def test_get_gap_clue_refuses_a_skill_that_is_not_fill_the_gap():
    for skill_id in ["capitalization", "writing_general"]:
        with pytest.raises(ValueError, match="has no gap clue"):
            skills.get_gap_clue(skill_id)
