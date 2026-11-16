"""All the prompt texts sent to the AI, in one place.

Each prompt is a TEMPLATE with {places} for the values (level, topic, skill...).
Its version is made from the template text only, BEFORE the values are inserted:
the same template always has the same version, and changing one word gives a new version.
"""

import hashlib

# ---------- prompt versions ----------

def make_prompt_version(prompt_name, template):
    # "gap_exercise@3f2a1c": the prompt name + the first 6 characters of a SHA-256 hash of the template.
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    prompt_version = prompt_name + "@" + template_hash[:6]

    return prompt_version


# ---------- fill the gap: create one exercise ----------

GAP_EXERCISE_PROMPT_NAME = "gap_exercise"

# The CODE chooses the skill (PLAN.md, Step 2). The AI only writes the sentence, so it gets ONE skill, not a list.
GAP_EXERCISE_TEMPLATE = """You are an English teacher. The learner is a Portuguese speaker from Portugal.

Write ONE fill-the-gap exercise in English.

Level (CEFR): {level}
Topic: {topic}
Situation for the sentence: {sub_topic}

The gap must test this skill: {skill_name}
Typical mistake of Portuguese speakers with this skill: {typical_mistake}
{tag_when_line}
The typical mistake is only an illustration of the skill. Do not reuse its sentence or its words:
write a new sentence about the situation above.

Sentences already used for this skill. Write a clearly different one (another verb, other words, another idea):
{sentences_to_avoid}

Rules:
- The sentence has exactly one gap, written as ___ (three underscores). Do not use underscores anywhere else.
- Only one idea must fit the gap, so the learner can find it. When the skill is about a verb form,
  write the base verb in brackets after the gap, for example: She ___ (work) in a bank.
- signal: the exact words of your sentence that make the tested form the only natural answer. Copy them from
  the sentence. Not the gap, not the verb in brackets.
- expected_answer: the word or words that fill the gap.
- accepted_answers: other answers a native speaker would also accept. Use an empty list if there are none.
- hint: a short clue that helps but does not give the answer. Never write the expected answer or an
  accepted answer in the hint.
"""

# Only added when the skill has a tag_when. It is part of the version hash too (see below).
TAG_WHEN_LINE_TEMPLATE = "Use this skill exactly when: {tag_when}\n"


def make_tag_when_line(skill):
    if "tag_when" not in skill:
        return ""

    return TAG_WHEN_LINE_TEMPLATE.format(tag_when=skill["tag_when"])


def make_sentences_to_avoid_text(sentences_to_avoid):
    if len(sentences_to_avoid) == 0:
        return "none"

    sentence_lines = []

    for sentence in sentences_to_avoid:
        sentence_lines.append("- " + sentence)

    return "\n".join(sentence_lines)


def build_gap_exercise_prompt(level, topic, sub_topic, skill, sentences_to_avoid):
    # Returns the final prompt text and its version. "skill" is one skill dict from tutor/skills.py.
    prompt_text = GAP_EXERCISE_TEMPLATE.format(
        level=level, topic=topic, sub_topic=sub_topic, skill_name=skill["name"],
        typical_mistake=skill["typical_mistake"], tag_when_line=make_tag_when_line(skill),
        sentences_to_avoid=make_sentences_to_avoid_text(sentences_to_avoid),
    )

    # Both templates are in the hash: changing the tag_when line also gives a new version.
    prompt_version = make_prompt_version(GAP_EXERCISE_PROMPT_NAME, GAP_EXERCISE_TEMPLATE + TAG_WHEN_LINE_TEMPLATE)

    return prompt_text, prompt_version


# ---------- fill the gap: create a batch of exercises (Step 2) ----------

GAP_EXERCISE_BATCH_PROMPT_NAME = "gap_exercise_batch"

# One request, several exercises on ONE skill (CLAUDE.md, rule 5: batch 5 exercises per call).
# Each exercise has its own situation, chosen by the code, for variety.
# The hint rule is new: in Step 1 the hints named the grammar rule, which made the exercise too easy.
GAP_EXERCISE_BATCH_TEMPLATE = """You are an English teacher. The learner is a Portuguese speaker from Portugal.

Write {exercise_count} fill-the-gap exercises in English. All of them test the same skill.

Level (CEFR): {level}
Topic: {topic}

The gap must test this skill: {skill_name}
Typical mistake of Portuguese speakers with this skill: {typical_mistake}
{tag_when_line}
The typical mistake is only an illustration of the skill. Do not reuse its sentence or its words.

Write exactly one exercise for each situation below, in this order:
{situations}

Sentences already used for this skill. Do not repeat them. Make your sentences clearly different from them
and from each other (other verbs, other words, other ideas):
{sentences_to_avoid}

Rules for every exercise:
- The sentence has exactly one gap, written as ___ (three underscores). Do not use underscores anywhere else.
- The sentence must contain a clear signal (a time word, another word in the sentence, or the situation) that
  makes the form of the tested skill the ONLY natural answer. It must contain no signal that calls for another
  form, for example a time word that needs a different tense. The typical mistake above shows the kind of
  difference this skill is about.
- When the skill is about a verb form, write the base verb in brackets after the gap.
- Use vocabulary at the {level} level or easier. The difficulty must be the skill, not the words.
- signal: the exact words of your sentence that are this clear signal. Copy them from the sentence.
  Not the gap, not the verb in brackets. If you cannot point to a signal, the sentence is ambiguous: rewrite it.
- expected_answer: the word or words that fill the gap.
- accepted_answers: only answers that use the SAME grammar as the expected answer (for example a short form
  of the same verb). Use an empty list if there are none.
- hint: a short clue about the MEANING or the situation of the sentence, not about grammar. Do not name the
  rule, the tense or the grammar word. Never write the expected answer or an accepted answer in the hint.

Before you answer, read each sentence again with the gap filled. If a different form would also be natural
(another tense, another word), the sentence is ambiguous: rewrite it so only the tested form fits.
"""


def make_situations_text(sub_topics):
    # "1. a delayed flight\n2. checking in at a hotel\n..."
    situation_lines = []

    for position, sub_topic in enumerate(sub_topics):
        situation_lines.append(str(position + 1) + ". " + sub_topic)

    return "\n".join(situation_lines)


def build_gap_exercise_batch_prompt(level, topic, sub_topics, skill, sentences_to_avoid):
    # One exercise per sub-topic. Returns the final prompt text and its version.
    prompt_text = GAP_EXERCISE_BATCH_TEMPLATE.format(
        exercise_count=len(sub_topics), level=level, topic=topic, skill_name=skill["name"],
        typical_mistake=skill["typical_mistake"], tag_when_line=make_tag_when_line(skill),
        situations=make_situations_text(sub_topics),
        sentences_to_avoid=make_sentences_to_avoid_text(sentences_to_avoid),
    )

    prompt_version = make_prompt_version(GAP_EXERCISE_BATCH_PROMPT_NAME,
                                         GAP_EXERCISE_BATCH_TEMPLATE + TAG_WHEN_LINE_TEMPLATE)

    return prompt_text, prompt_version
