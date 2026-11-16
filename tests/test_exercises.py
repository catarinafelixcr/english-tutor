"""Tests for tutor/exercises.py, with a fake ask() instead of the real AI (no internet, no quota)."""

import pytest
from pydantic import ValidationError

from tutor import db, exercises, llm, skills


@pytest.fixture
def database_path(tmp_path):
    temporary_database_path = tmp_path / "test_tutor.db"
    db.init_db(temporary_database_path)

    return temporary_database_path


class FakeAsk:
    """Replaces llm.ask(). It validates the planned answer with the schema it receives, like the real parse()."""

    def __init__(self, planned_answer):
        self.planned_answer = planned_answer
        self.prompts_received = []

    def ask(self, prompt_text, prompt_version, schema):
        self.prompts_received.append(prompt_text)
        validated_answer = schema(**self.planned_answer)

        return validated_answer, "fake-test-model"


def install_fake_ask(monkeypatch, sentence):
    planned_answer = {"sentence": sentence, "expected_answer": "am", "accepted_answers": ["'m"],
                      "hint": "the verb for how you feel"}
    fake_ask = FakeAsk(planned_answer)
    monkeypatch.setattr(llm, "ask", fake_ask.ask)

    return fake_ask


# ---------- choices made by the code ----------

def test_choose_random_skill_at_a2_gives_only_a2_fill_the_gap_skills():
    for repetition in range(50):
        skill = exercises.choose_random_skill("A2")

        assert skill["level"] == "A2"
        assert skill["id"] in skills.get_fill_the_gap_skill_ids()


def test_choose_random_skill_at_b1_gives_a2_or_b1_skills():
    chosen_levels = set()

    for repetition in range(200):
        skill = exercises.choose_random_skill("B1")
        chosen_levels.add(skill["level"])

        assert skill["id"] in skills.get_fill_the_gap_skill_ids()

    assert chosen_levels == {"A2", "B1"}


def test_every_topic_has_sub_topics():
    for topic, sub_topics in exercises.TOPICS.items():
        assert len(sub_topics) >= 3, topic + " needs more sub-topics"


# ---------- create_gap_exercise ----------

def test_create_gap_exercise_saves_one_exercise_with_the_skill_chosen_by_the_code(database_path, monkeypatch):
    install_fake_ask(monkeypatch, "I ___ tired after the flight.")

    exercise, exercise_id = exercises.create_gap_exercise("to_be", "A2", "travel", database_path)

    assert exercise.skill_id == "to_be"
    assert exercise.level == "A2"
    assert exercise.topic == "travel"
    assert exercise.sub_topic in exercises.TOPICS["travel"]
    assert exercise.accepted_answers == ["'m"]
    assert exercise.hint == "the verb for how you feel"
    assert exercise.model == "fake-test-model"
    assert exercise.prompt_version.startswith("gap_exercise@")
    assert db.get_exercise_sentences("to_be", database_path) == ["I ___ tired after the flight."]
    assert exercise_id == 1


def test_create_gap_exercise_sends_the_saved_sentences_to_avoid(database_path, monkeypatch):
    install_fake_ask(monkeypatch, "I ___ tired after the flight.")
    exercises.create_gap_exercise("to_be", "A2", "travel", database_path)

    fake_ask = install_fake_ask(monkeypatch, "We ___ late for the meeting.")
    exercises.create_gap_exercise("to_be", "A2", "meetings", database_path)

    assert "- I ___ tired after the flight." in fake_ask.prompts_received[0]


def test_a_sentence_already_saved_for_the_skill_is_an_invalid_answer(database_path, monkeypatch):
    # In the real app, llm.ask() catches this ValidationError and retries once (tests/test_llm.py).
    install_fake_ask(monkeypatch, "I ___ tired after the flight.")
    exercises.create_gap_exercise("to_be", "A2", "travel", database_path)

    install_fake_ask(monkeypatch, "i ___ TIRED after  the flight.")

    with pytest.raises(ValidationError, match="already used"):
        exercises.create_gap_exercise("to_be", "A2", "travel", database_path)

    assert len(db.get_exercise_sentences("to_be", database_path)) == 1


def test_the_same_sentence_for_another_skill_is_allowed(database_path, monkeypatch):
    install_fake_ask(monkeypatch, "I ___ tired after the flight.")
    exercises.create_gap_exercise("to_be", "A2", "travel", database_path)

    exercise, exercise_id = exercises.create_gap_exercise("present_simple", "A2", "travel", database_path)

    assert exercise.skill_id == "present_simple"


@pytest.mark.parametrize("skill_id", ["capitalization", "listening", "invented_skill"])
def test_create_gap_exercise_refuses_a_skill_that_fill_the_gap_cannot_use(database_path, monkeypatch, skill_id):
    fake_ask = install_fake_ask(monkeypatch, "I ___ tired.")

    with pytest.raises(ValueError, match="cannot be used in fill the gap"):
        exercises.create_gap_exercise(skill_id, "A2", "travel", database_path)

    assert fake_ask.prompts_received == []


def test_create_gap_exercise_refuses_a_skill_above_the_level(database_path, monkeypatch):
    fake_ask = install_fake_ask(monkeypatch, "Never ___ I seen this.")

    with pytest.raises(ValueError, match="above the level"):
        exercises.create_gap_exercise("inversion", "A2", "meetings", database_path)

    assert fake_ask.prompts_received == []
