"""Creating exercises: the code chooses skill, topic and sub-topic, the AI writes the sentence, the database saves it.

This file sits between the screens (pages/) and the AI (llm.py), so the pages stay thin (CLAUDE.md, rule 7).
"""

import json
import random

from tutor import db, llm, prompts, skills
from tutor.schemas import (
    Exercise,
    GapExercise,
    contains_whole_words,
    make_gap_exercise_batch_schema,
    make_gap_exercise_draft_schema,
    split_gap_exercise_items,
)

# The topics of the topic selector (PLAN.md, Step 2). Each sub-topic is one small situation, for variety.
TOPICS = {
    "daily life": ["shopping at the supermarket", "cooking dinner at home", "a visit to the dentist",
                   "plans for the weekend", "doing sport at the gym", "talking with a neighbour"],
    "data science and work": ["cleaning a messy dataset", "a model that gives strange results",
                              "writing a SQL query", "a deadline next Friday", "explaining a chart to a colleague",
                              "a new tool at work"],
    "travel": ["a delayed flight", "checking in at a hotel", "asking for directions in a city",
               "buying a train ticket", "a lost suitcase", "visiting a museum"],
    "meetings": ["a daily stand-up", "a project that is late", "asking a manager for feedback",
                 "presenting results to a client", "planning the next sprint", "a meeting that starts late"],
}

# How many saved sentences go in the prompt. The duplicate check uses ALL saved sentences of the skill.
SENTENCES_TO_AVOID_IN_PROMPT = 5

# Exercises per AI request (CLAUDE.md, rule 5). Each topic needs at least this many sub-topics.
BATCH_SIZE = 5

# Exercises the code dropped from a batch, with the reason. Not in ai_log.jsonl: there, one line = one request,
# and the request counter depends on that.
DROPPED_EXERCISES_LOG_PATH = db.PROJECT_FOLDER / "logs" / "dropped_exercises.jsonl"


# ---------- choices made by the code ----------

def choose_random_skill(level):
    # One fill-the-gap skill at this level or below (for B1: an A2 or a B1 skill).
    return random.choice(skills.get_fill_the_gap_skills_up_to_level(level))


def choose_random_topic():
    return random.choice(list(TOPICS))


def choose_random_sub_topic(topic):
    return random.choice(TOPICS[topic])


def choose_word_traps(skill_id):
    # One known trap pair per exercise of the batch, all different (word_choice, false_friends).
    # An empty list for a skill with no known traps: the AI then finds the trap itself.
    word_traps = skills.get_word_traps(skill_id)

    if len(word_traps) == 0:
        return []

    return random.sample(word_traps, BATCH_SIZE)


def find_word_trap_problem(draft, word_trap):
    # The AI must use the Portuguese word the code chose for this position. Returns a reason, or "" if it is fine.
    if not contains_whole_words(draft.sentence, word_trap["portuguese"]):
        return "the Portuguese word of the situation is not in the brackets: " + word_trap["portuguese"]

    return ""


# ---------- create and save one exercise ----------

def check_gap_skill_and_level(skill_id, level):
    # Guard clauses, BEFORE any request is spent. Returns the skill dict.
    if skill_id not in skills.get_fill_the_gap_skill_ids():
        raise ValueError("this skill cannot be used in fill the gap: " + skill_id)

    skill = skills.get_skill(skill_id)

    if skills.VALID_LEVELS.index(skill["level"]) > skills.VALID_LEVELS.index(level):
        raise ValueError("the skill " + skill_id + " is " + skill["level"] + ", above the level " + level)

    return skill


def create_gap_exercise(skill_id, level, topic, database_path=db.DEFAULT_DATABASE_PATH):
    # Asks the AI for ONE sentence on THIS skill and saves it. Returns (Exercise, new exercise id).
    # Used by scripts/step1_demo.py. The Practice page uses create_gap_exercises() (5 per request).
    # Raises an llm.AIError if the AI fails (the page or script shows its message).
    skill = check_gap_skill_and_level(skill_id, level)

    sub_topic = choose_random_sub_topic(topic)
    used_sentences = db.get_exercise_sentences(skill_id, database_path)
    recent_sentences = used_sentences[:SENTENCES_TO_AVOID_IN_PROMPT]

    prompt_text, prompt_version = prompts.build_gap_exercise_prompt(level, topic, sub_topic, skill, recent_sentences)

    # The schema refuses a sentence already saved for this skill: llm.ask() then retries once, like any bad answer.
    draft_schema = make_gap_exercise_draft_schema(used_sentences)
    draft, model_returned = llm.ask(prompt_text, prompt_version, draft_schema, "create")

    # The code adds the skill and the level it chose. Pydantic needs field names here.
    gap_exercise = GapExercise(**draft.model_dump(), skill_id=skill_id, level=level)

    exercise = Exercise(section="practice", exercise_type="gap", skill_id=skill_id, level=level, topic=topic,
                        sub_topic=sub_topic, prompt_text=gap_exercise.sentence,
                        expected_answer=gap_exercise.expected_answer, accepted_answers=gap_exercise.accepted_answers,
                        hint=gap_exercise.hint, trap=gap_exercise.trap, trap_why=gap_exercise.trap_why,
                        model=model_returned, prompt_version=prompt_version)
    exercise_id = db.save_exercise(exercise, database_path)

    return exercise, exercise_id


# ---------- create and save a batch of exercises (Step 2) ----------

def log_dropped_exercises(rejected_items, skill_id, prompt_version, model_returned):
    # One JSON line per dropped exercise, so I can see later WHY the AI's exercises were refused.
    if len(rejected_items) == 0:
        return

    DROPPED_EXERCISES_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(DROPPED_EXERCISES_LOG_PATH, "a", encoding="utf-8") as log_file:
        for rejected_item in rejected_items:
            log_line = {"time_utc": db.to_iso_text(db.utc_now()), "skill_id": skill_id,
                        "prompt_version": prompt_version, "model_returned": model_returned,
                        "position": rejected_item["position"], "reason": rejected_item["reason"],
                        "item": rejected_item["item"]}
            log_file.write(json.dumps(log_line, ensure_ascii=False) + "\n")


def create_gap_exercises(skill_id, level, topic, database_path=db.DEFAULT_DATABASE_PATH, budget=None):
    # ONE request for BATCH_SIZE sentences on THIS skill, each about a different sub-topic of the topic.
    # Saves the valid ones and drops (and logs) the bad ones. Returns a list of (Exercise, new exercise id).
    # Raises an llm.AIError if the AI fails, or if no exercise of the batch is valid twice in a row.
    # budget: an llm.RequestBudget (for example a fail-fast one for a refill), or None for a normal one.
    skill = check_gap_skill_and_level(skill_id, level)

    # random.sample: BATCH_SIZE DIFFERENT sub-topics, in random order.
    sub_topics = random.sample(TOPICS[topic], BATCH_SIZE)
    used_sentences = db.get_exercise_sentences(skill_id, database_path)
    recent_sentences = used_sentences[:SENTENCES_TO_AVOID_IN_PROMPT]
    word_traps = choose_word_traps(skill_id)

    prompt_text, prompt_version = prompts.build_gap_exercise_batch_prompt(level, topic, sub_topics, skill,
                                                                          recent_sentences, word_traps)
    batch_schema = make_gap_exercise_batch_schema(used_sentences, skills.get_gap_clue(skill_id))
    batch, model_returned = llm.ask(prompt_text, prompt_version, batch_schema, "create", budget)

    # The batch schema already checked that at least one item is valid. Now we split the good from the bad.
    items_asked_for = batch.exercises[:BATCH_SIZE]
    valid_items, rejected_items = split_gap_exercise_items(items_asked_for, batch_schema.strict_draft_schema)

    if len(word_traps) > 0:
        valid_items = drop_items_without_their_word_trap(valid_items, word_traps, rejected_items)

    for extra_position in range(BATCH_SIZE, len(batch.exercises)):
        rejected_items.append({"position": extra_position, "reason": "more exercises than asked for",
                               "item": batch.exercises[extra_position].model_dump()})

    log_dropped_exercises(rejected_items, skill_id, prompt_version, model_returned)

    saved_exercises = []

    for position, draft in valid_items:
        # The code adds the skill and the level it chose, and the sub-topic of this position.
        gap_exercise = GapExercise(**draft.model_dump(), skill_id=skill_id, level=level)

        exercise = Exercise(section="practice", exercise_type="gap", skill_id=skill_id, level=level, topic=topic,
                            sub_topic=sub_topics[position], prompt_text=gap_exercise.sentence,
                            expected_answer=gap_exercise.expected_answer,
                            accepted_answers=gap_exercise.accepted_answers, hint=gap_exercise.hint,
                            trap=gap_exercise.trap, trap_why=gap_exercise.trap_why, model=model_returned,
                            prompt_version=prompt_version)
        exercise_id = db.save_exercise(exercise, database_path)
        saved_exercises.append((exercise, exercise_id))

    return saved_exercises


def drop_items_without_their_word_trap(valid_items, word_traps, rejected_items):
    # Keeps the items that use the Portuguese word of their position; adds the others to rejected_items (logged).
    kept_items = []

    for position, draft in valid_items:
        problem = find_word_trap_problem(draft, word_traps[position])

        if problem != "":
            rejected_items.append({"position": position, "reason": problem, "item": draft.model_dump()})
            continue

        kept_items.append((position, draft))

    return kept_items


# ---------- the exercise stock (Step 2, Part 2) ----------

# Below this many unanswered exercises, a new batch is created (PLAN.md, "Exercise stock").
MINIMUM_STOCK = 3

# Shown on the page when the AI was busy but the stock still had an exercise. A notice, not an error.
BUSY_STOCK_NOTICE = "The AI is busy right now, so you are practising with your saved sentences."


def refill_stock(skill_id, level, topic, stock_is_empty, database_path):
    # One batch. With exercises still in the stock, a busy AI stops at once (no 2 s + 4 s waits):
    # I keep practising instead of waiting. With an EMPTY stock, the normal retries are worth the wait.
    # skill_id or topic None = "any": the code chooses one at random for this batch.
    if skill_id is None:
        skill_id = choose_random_skill(level)["id"]

    if topic is None:
        topic = choose_random_topic()

    if stock_is_empty:
        budget = llm.make_normal_budget()
    else:
        budget = llm.make_fail_fast_budget()

    create_gap_exercises(skill_id, level, topic, database_path, budget)


def choose_from_stock(stock, skill_id):
    # One skill: the oldest first. Any skill: a random one, so I do not get 5 sentences on one skill in a row.
    if skill_id is not None:
        return stock[0]

    return random.choice(stock)


def get_next_gap_exercise(level, skill_id=None, topic=None, database_path=db.DEFAULT_DATABASE_PATH):
    # The next fill-the-gap exercise for the Practice page. Returns (exercise id, Exercise, notice).
    # notice is "" normally, or BUSY_STOCK_NOTICE when the AI was busy and the exercise came from the stock.
    # skill_id and topic are filters (None = any skill, any topic). Practice never depends on a live request
    # while the stock has exercises: only an EMPTY stock + an AI error raises the llm.AIError (the page shows
    # it with a "Try again" button).
    stock = db.get_unanswered_exercises("gap", level, skill_id, topic, database_path)
    notice = ""

    if len(stock) < MINIMUM_STOCK:
        stock_is_empty = len(stock) == 0

        try:
            refill_stock(skill_id, level, topic, stock_is_empty, database_path)
        except llm.AIError:
            if stock_is_empty:
                raise

            notice = BUSY_STOCK_NOTICE

        stock = db.get_unanswered_exercises("gap", level, skill_id, topic, database_path)

    exercise_id, exercise = choose_from_stock(stock, skill_id)

    return exercise_id, exercise, notice
