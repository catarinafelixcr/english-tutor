"""Creating exercises: the code chooses skill, topic and sub-topic, the AI writes the sentence, the database saves it.

This file sits between the screens (pages/) and the AI (llm.py), so the pages stay thin (CLAUDE.md, rule 7).
"""

import random

from tutor import db, llm, prompts, skills
from tutor.schemas import Exercise, GapExercise, make_gap_exercise_draft_schema

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


# ---------- choices made by the code ----------

def choose_random_skill(level):
    # One fill-the-gap skill at this level or below (for B1: an A2 or a B1 skill).
    return random.choice(skills.get_fill_the_gap_skills_up_to_level(level))


def choose_random_topic():
    return random.choice(list(TOPICS))


def choose_random_sub_topic(topic):
    return random.choice(TOPICS[topic])


# ---------- create and save one exercise ----------

def create_gap_exercise(skill_id, level, topic, database_path=db.DEFAULT_DATABASE_PATH):
    # Asks the AI for one sentence on THIS skill and saves it. Returns (Exercise, new exercise id).
    # Raises an llm.AIError if the AI fails (the page or script shows its message).
    if skill_id not in skills.get_fill_the_gap_skill_ids():
        raise ValueError("this skill cannot be used in fill the gap: " + skill_id)

    skill = skills.get_skill(skill_id)

    if skills.VALID_LEVELS.index(skill["level"]) > skills.VALID_LEVELS.index(level):
        raise ValueError("the skill " + skill_id + " is " + skill["level"] + ", above the level " + level)

    sub_topic = choose_random_sub_topic(topic)
    used_sentences = db.get_exercise_sentences(skill_id, database_path)
    recent_sentences = used_sentences[:SENTENCES_TO_AVOID_IN_PROMPT]

    prompt_text, prompt_version = prompts.build_gap_exercise_prompt(level, topic, sub_topic, skill, recent_sentences)

    # The schema refuses a sentence already saved for this skill: llm.ask() then retries once, like any bad answer.
    draft_schema = make_gap_exercise_draft_schema(used_sentences)
    draft, model_returned = llm.ask(prompt_text, prompt_version, draft_schema)

    # The code adds the skill and the level it chose. Pydantic needs field names here.
    gap_exercise = GapExercise(**draft.model_dump(), skill_id=skill_id, level=level)

    exercise = Exercise(section="practice", skill_id=skill_id, level=level, topic=topic, sub_topic=sub_topic,
                        prompt_text=gap_exercise.sentence, expected_answer=gap_exercise.expected_answer,
                        accepted_answers=gap_exercise.accepted_answers, hint=gap_exercise.hint, model=model_returned,
                        prompt_version=prompt_version)
    exercise_id = db.save_exercise(exercise, database_path)

    return exercise, exercise_id
