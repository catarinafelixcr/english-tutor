"""Step 2 demo: ask the AI for a BATCH of 5 fill-the-gap exercises in ONE request, and save the valid ones.

Run it from the project folder:
    python -m scripts.step2_batch_demo                    a random A2 skill
    python -m scripts.step2_batch_demo present_simple     this skill (at its own level)

What to look at:
- 5 exercises, each about a different situation of the topic.
- Hints about the MEANING of the sentence, not the grammar rule.
- Dropped exercises (if any) are listed with their reason in logs/dropped_exercises.jsonl.

The first run on an old database also runs the migration to version 2 (a backup goes to data/backups/).
It uses 1 real AI request (2 if no exercise of the first answer is valid). The key is never printed.
"""

import sys

from scripts.step1_demo import choose_skill, print_ai_usage_today, print_exercise
from tutor import db, exercises, llm


def main():
    command_arguments = sys.argv[1:]

    if len(command_arguments) > 1:
        print("Use: python -m scripts.step2_batch_demo [skill_id]")
        sys.exit(1)

    skill = choose_skill(command_arguments)
    topic = exercises.choose_random_topic()

    db.init_db()

    print("Asking the AI for", exercises.BATCH_SIZE, "exercises on", skill["id"], "(" + skill["level"] + "), topic:",
          topic)

    try:
        saved_exercises = exercises.create_gap_exercises(skill["id"], skill["level"], topic)
    except llm.AIError as error:
        print("AI error (" + type(error).__name__ + "):", error)
        sys.exit(1)

    for exercise, exercise_id in saved_exercises:
        print_exercise(exercise, exercise_id)

    print()
    print("  Saved", len(saved_exercises), "of", exercises.BATCH_SIZE, "exercises.")
    print_ai_usage_today()


if __name__ == "__main__":
    main()
