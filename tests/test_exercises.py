"""Tests for tutor/exercises.py, with a fake ask() instead of the real AI (no internet, no quota)."""

import json

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


def test_every_topic_has_enough_sub_topics_for_one_batch():
    # A batch gives each exercise a DIFFERENT sub-topic, so a topic needs at least BATCH_SIZE of them.
    for topic, sub_topics in exercises.TOPICS.items():
        assert len(sub_topics) >= exercises.BATCH_SIZE, topic + " needs more sub-topics"


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


def test_create_gap_exercise_saves_the_exercise_type_gap(database_path, monkeypatch):
    install_fake_ask(monkeypatch, "I ___ tired after the flight.")

    exercise, exercise_id = exercises.create_gap_exercise("to_be", "A2", "travel", database_path)

    assert exercise.exercise_type == "gap"


# ---------- create_gap_exercises (a batch of 5 in one request) ----------

@pytest.fixture
def dropped_log_path(tmp_path, monkeypatch):
    # Tests never write to the real logs/ folder.
    temporary_log_path = tmp_path / "dropped_exercises.jsonl"
    monkeypatch.setattr(exercises, "DROPPED_EXERCISES_LOG_PATH", temporary_log_path)

    return temporary_log_path


def make_batch_item(sentence):
    return {"sentence": sentence, "expected_answer": "am", "accepted_answers": ["'m"], "hint": "how you feel"}


FIVE_GOOD_SENTENCES = ["I ___ tired after the flight.", "I ___ at the hotel now.", "I ___ ready to check in.",
                       "I ___ happy with the room.", "I ___ late for the train."]


def install_fake_batch_ask(monkeypatch, sentences):
    items = []

    for sentence in sentences:
        items.append(make_batch_item(sentence))

    fake_ask = FakeAsk({"exercises": items})
    monkeypatch.setattr(llm, "ask", fake_ask.ask)

    return fake_ask


def read_log_lines(log_path):
    log_lines = []

    for line_text in log_path.read_text(encoding="utf-8").splitlines():
        log_lines.append(json.loads(line_text))

    return log_lines


def test_create_gap_exercises_saves_five_exercises_from_one_request(database_path, monkeypatch, dropped_log_path):
    fake_ask = install_fake_batch_ask(monkeypatch, FIVE_GOOD_SENTENCES)

    saved_exercises = exercises.create_gap_exercises("to_be", "A2", "travel", database_path)

    assert len(fake_ask.prompts_received) == 1
    assert len(saved_exercises) == 5

    sub_topics = set()

    for exercise, exercise_id in saved_exercises:
        assert exercise.skill_id == "to_be"
        assert exercise.level == "A2"
        assert exercise.exercise_type == "gap"
        assert exercise.prompt_version.startswith("gap_exercise_batch@")
        assert exercise.sub_topic in exercises.TOPICS["travel"]
        sub_topics.add(exercise.sub_topic)

    assert len(sub_topics) == 5
    assert len(db.get_exercise_sentences("to_be", database_path)) == 5
    assert not dropped_log_path.exists()


def test_each_exercise_keeps_the_sub_topic_of_its_position(database_path, monkeypatch, dropped_log_path):
    # The 2nd item is bad. The 3rd exercise must still get the 3rd situation of the prompt, not the 2nd.
    sentences = list(FIVE_GOOD_SENTENCES)
    sentences[1] = "No gap in this sentence."
    fake_ask = install_fake_batch_ask(monkeypatch, sentences)

    saved_exercises = exercises.create_gap_exercises("to_be", "A2", "travel", database_path)
    third_exercise = saved_exercises[1][0]

    assert third_exercise.prompt_text == "I ___ ready to check in."
    assert "3. " + third_exercise.sub_topic in fake_ask.prompts_received[0]


def test_a_bad_item_is_dropped_and_logged_and_the_others_are_saved(database_path, monkeypatch, dropped_log_path):
    sentences = list(FIVE_GOOD_SENTENCES)
    sentences[3] = "No gap in this sentence."
    install_fake_batch_ask(monkeypatch, sentences)

    saved_exercises = exercises.create_gap_exercises("to_be", "A2", "travel", database_path)
    log_lines = read_log_lines(dropped_log_path)

    assert len(saved_exercises) == 4
    assert len(log_lines) == 1
    assert log_lines[0]["position"] == 3
    assert log_lines[0]["skill_id"] == "to_be"
    assert "exactly one gap" in log_lines[0]["reason"]
    assert log_lines[0]["item"]["sentence"] == "No gap in this sentence."


def test_a_sentence_already_saved_is_dropped_from_the_batch(database_path, monkeypatch, dropped_log_path):
    install_fake_ask(monkeypatch, "I ___ tired after the flight.")
    exercises.create_gap_exercise("to_be", "A2", "travel", database_path)

    fake_ask = install_fake_batch_ask(monkeypatch, FIVE_GOOD_SENTENCES)
    saved_exercises = exercises.create_gap_exercises("to_be", "A2", "travel", database_path)

    assert len(saved_exercises) == 4
    assert "- I ___ tired after the flight." in fake_ask.prompts_received[0]
    assert "already used" in read_log_lines(dropped_log_path)[0]["reason"]


def test_extra_items_beyond_the_batch_size_are_dropped(database_path, monkeypatch, dropped_log_path):
    install_fake_batch_ask(monkeypatch, FIVE_GOOD_SENTENCES + ["I ___ hungry after the trip."])

    saved_exercises = exercises.create_gap_exercises("to_be", "A2", "travel", database_path)
    log_lines = read_log_lines(dropped_log_path)

    assert len(saved_exercises) == 5
    assert log_lines[0]["reason"] == "more exercises than asked for"


def test_a_batch_with_no_valid_item_saves_nothing(database_path, monkeypatch, dropped_log_path):
    # In the real app, llm.ask() catches this ValidationError and retries once (tests/test_llm.py).
    install_fake_batch_ask(monkeypatch, ["No gap here.", "No gap there either."])

    with pytest.raises(ValidationError, match="no valid exercise"):
        exercises.create_gap_exercises("to_be", "A2", "travel", database_path)

    assert db.get_exercise_sentences("to_be", database_path) == []


@pytest.mark.parametrize("skill_id, level, error_text", [("capitalization", "A2", "cannot be used in fill the gap"),
                                                         ("inversion", "A2", "above the level")])
def test_create_gap_exercises_checks_skill_and_level_before_asking(database_path, monkeypatch, skill_id, level,
                                                                    error_text):
    fake_ask = install_fake_batch_ask(monkeypatch, FIVE_GOOD_SENTENCES)

    with pytest.raises(ValueError, match=error_text):
        exercises.create_gap_exercises(skill_id, level, "travel", database_path)

    assert fake_ask.prompts_received == []
