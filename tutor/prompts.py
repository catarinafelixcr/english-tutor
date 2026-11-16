"""All the prompt texts sent to the AI, in one place.

Each prompt is a TEMPLATE with {places} for the values (level, topic, skill list).
Its version is made from the template text only, BEFORE the values are inserted:
the same template always has the same version, and changing one word gives a new version.
"""

import hashlib

from tutor import skills

# ---------- prompt versions ----------

def make_prompt_version(prompt_name, template):
    # "gap_exercise@3f2a1c": the prompt name + the first 6 characters of a SHA-256 hash of the template.
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    prompt_version = prompt_name + "@" + template_hash[:6]

    return prompt_version


# ---------- fill the gap: create one exercise ----------

GAP_EXERCISE_PROMPT_NAME = "gap_exercise"

GAP_EXERCISE_TEMPLATE = """You are an English teacher. The learner is a Portuguese speaker from Portugal.

Write ONE fill-the-gap exercise in English.

Level (CEFR): {level}
Topic of the sentence: {topic}

Rules:
- The sentence has exactly one gap, written as ___ (three underscores). Do not use underscores anywhere else.
- The gap tests ONE skill from the list below. Choose skill_id only from this list. Never invent a skill.
- Use the "typical mistake" and "tag when" columns to choose the right skill.
- Only one idea must fit the gap, so the learner can find it. When the skill is about a verb form,
  write the base verb in brackets after the gap, for example: She ___ (work) in a bank.
- expected_answer: the word or words that fill the gap.
- accepted_answers: other answers a native speaker would also accept. Use an empty list if there are none.
- hint: a short clue that helps but does not give the answer.
- level: {level}

Skills (id | name | level | typical mistake | tag when):
{skill_list}
"""


def build_gap_exercise_prompt(level, topic, skill_list):
    # Returns the final prompt text and its version.
    skill_list_text = skills.skills_as_prompt_text(skill_list)
    prompt_text = GAP_EXERCISE_TEMPLATE.format(level=level, topic=topic, skill_list=skill_list_text)
    prompt_version = make_prompt_version(GAP_EXERCISE_PROMPT_NAME, GAP_EXERCISE_TEMPLATE)

    return prompt_text, prompt_version
