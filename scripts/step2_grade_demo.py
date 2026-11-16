"""Step 2 demo: the REAL AI grades 6 fill-the-gap answers, to see the verdicts, the explanations and the tone.

Run it from the project folder:
    python -m scripts.step2_grade_demo

It uses a TEMPORARY database (deleted at the end): my real data/tutor.db does not change.
About 6 real AI requests (more if a quote is retried or Gemini is busy). The key is never printed.
Grading problems, if any, are written to logs/grading_problems.jsonl (the real log, on purpose).
"""

import tempfile
from pathlib import Path

from scripts.step1_demo import print_ai_usage_today
from tutor import db, grading, llm
from tutor.schemas import Exercise

WRITE_SENTENCE = "She has ___ (write) the report already."
LIVE_SENTENCE = "I ___ (live) in Lisbon since 2020."

# (sentence, expected answer, my answer, what I expect)
DEMO_ANSWERS = [
    (WRITE_SENTENCE, "written", "writen", "correct + a detected spelling slip (green + reminder)"),
    (WRITE_SENTENCE, "written", "writed", "correct + irregular_verbs detected (yellow Almost)"),
    (WRITE_SENTENCE, "written", "write", "partial: has, but no past participle (yellow Partly right)"),
    (LIVE_SENTENCE, "have lived", "have been living", "correct, also right, with a note (green)"),
    (LIVE_SENTENCE, "have lived", "live", "wrong: another tense, the Portuguese 'vivo aqui desde' (red)"),
    (WRITE_SENTENCE, "written", "asdf", "wrong: nonsense (red)"),
]


def print_result(result):
    print("  State          :", result.state)
    print("  Corrected      :", result.corrected_sentence)

    if result.mistake_text != "":
        print("  You wrote      :", result.mistake_text, "→", result.correction)
        print("  Why            :", result.why_wrong)
        print("  Rule           :", result.rule)

    if result.note != "":
        print("  Note           :", result.note)

    if result.detected_skill_id != "":
        print("  Detected       :", result.detected_skill_id + ":", result.detected_mistake_text, "→",
              result.detected_correction)

    if result.reminder != "":
        print("  Reminder       :", result.reminder)

    if result.memory_tip != "":
        print("  Memory tip     :", result.memory_tip)

    if len(result.other_good_answers) > 0:
        print("  Other answers  :", ", ".join(result.other_good_answers))


def grade_one_answer(database_path, sentence, expected_answer, your_answer, what_i_expect):
    exercise = Exercise(section="practice", exercise_type="gap", skill_id="present_perfect", level="B1",
                        topic="work", prompt_text=sentence, expected_answer=expected_answer)
    exercise_id = db.save_exercise(exercise, database_path)

    print()
    print(sentence, " | my answer:", your_answer)
    print("  Expected       :", what_i_expect)

    try:
        result = grading.grade_gap_answer(exercise_id, exercise, your_answer, False, 10.0, "English", database_path)
    except llm.AIError as error:
        print("  AI error (" + type(error).__name__ + "):", error)
        return

    print_result(result)


def main():
    with tempfile.TemporaryDirectory() as temporary_folder:
        database_path = Path(temporary_folder) / "demo_tutor.db"
        db.init_db(database_path)

        for sentence, expected_answer, your_answer, what_i_expect in DEMO_ANSWERS:
            grade_one_answer(database_path, sentence, expected_answer, your_answer, what_i_expect)

        saved_attempts = db.get_attempts(database_path=database_path)

        print()
        print("  Rows saved in the temporary database:", len(saved_attempts))

    print_ai_usage_today()


if __name__ == "__main__":
    main()
