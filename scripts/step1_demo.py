"""Step 1 demo: ask the AI for ONE fill-the-gap exercise, check it and save it in data/tutor.db.

Run it from the project folder:
    python -m scripts.step1_demo                    a random A2 skill
    python -m scripts.step1_demo present_simple     this skill (at its own level)

Run it twice with the same skill: the second sentence must be different (the "sentences to avoid" list).
It uses 1 real AI request (2 if the first answer is invalid). The key is read from .env and never printed.
"""

import sys

from tutor import db, exercises, llm, skills

DEMO_LEVEL = "A2"


def choose_skill(command_arguments):
    # No argument: a random skill at DEMO_LEVEL or below. One argument: that skill, if fill the gap can use it.
    if len(command_arguments) == 0:
        return exercises.choose_random_skill(DEMO_LEVEL)

    skill_id = command_arguments[0]

    if skill_id not in skills.get_fill_the_gap_skill_ids():
        print("This skill id cannot be used in fill the gap:", skill_id)
        print("Choose one of:", ", ".join(skills.get_fill_the_gap_skill_ids()))
        sys.exit(1)

    return skills.get_skill(skill_id)


def print_exercise(exercise, exercise_id):
    print()
    print("  Exercise id     :", exercise_id)
    print("  Skill           :", exercise.skill_id, "(" + exercise.level + ")")
    print("  Topic           :", exercise.topic, "/", exercise.sub_topic)
    print("  Sentence        :", exercise.prompt_text)
    print("  Expected answer :", exercise.expected_answer)
    print("  Accepted answers:", exercise.accepted_answers)
    print("  Trap            :", exercise.trap)
    print("  Why it is wrong :", exercise.trap_why)
    print("  Hint            :", exercise.hint)
    print("  Model returned  :", exercise.model)
    print("  Prompt version  :", exercise.prompt_version)


def print_ai_usage_today():
    settings = llm.read_ai_settings()
    requests_today = llm.count_requests_today(settings["model"])
    usable_limit = settings["daily_limit"] - settings["daily_limit_margin"]

    print()
    print("  AI today:", requests_today, "/", usable_limit, "requests (estimate; tokens are in logs/ai_log.jsonl)")


def main():
    command_arguments = sys.argv[1:]

    if len(command_arguments) > 1:
        print("Use: python -m scripts.step1_demo [skill_id]")
        sys.exit(1)

    skill = choose_skill(command_arguments)
    topic = exercises.choose_random_topic()

    db.init_db()

    print("Asking the AI for one exercise on", skill["id"], "(" + skill["level"] + "), topic:", topic)

    try:
        exercise, exercise_id = exercises.create_gap_exercise(skill["id"], skill["level"], topic)
    except llm.AIError as error:
        print("AI error (" + type(error).__name__ + "):", error)
        sys.exit(1)

    print_exercise(exercise, exercise_id)
    print_ai_usage_today()


if __name__ == "__main__":
    main()
