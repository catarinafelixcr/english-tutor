"""All the prompt texts sent to the AI, in one place.

Each prompt is a TEMPLATE with {places} for the values (level, topic, skill...).
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


# ---------- fill the gap: grade one answer (Step 2, Part 2) ----------

GAP_GRADE_PROMPT_NAME = "gap_grade"

# English until Step 4 adds the selector (Portuguese or English).
DEFAULT_EXPLANATION_LANGUAGE = "English"

# The AI is called ONLY when the code found no match, so the answer is never the expected or an accepted one.
# The rules for the verdicts, the slips and the 3-part explanation come from PLAN.md, Step 2, "Check answers".
# The schema gives the AI the allowed skill ids (an enum). The tag_when lines help it choose between skills
# that are often confused (my answer to question 2, 2026-11-16).
GAP_GRADE_TEMPLATE = """You are an English teacher. The learner is a Portuguese speaker from Portugal.

Grade the learner's answer to one fill-the-gap exercise.

Exercise: {sentence}
Expected answer: {expected_answer}
Other accepted answers: {accepted_answers}
The learner's answer: {your_answer}
The learner's full sentence: {sentence_with_answer}

The exercise tests this skill: {skill_name}
Typical mistake of Portuguese speakers with this skill: {typical_mistake}
{tag_when_line}
The learner's answer is NOT the expected answer and NOT an accepted answer. Decide if it still works.
Accept any answer a native speaker would naturally use in this sentence.

Verdict, about the tested skill only:
- correct: the answer is natural in this sentence and uses the tested skill correctly. If the sentence also
  allows another form (for example another tense), and the learner's form is natural, it is correct.
- partial: the learner applied only half of the tested rule and did not try the other half. Example for the
  present perfect: "has finish" (has, but no past participle).
- wrong: the learner did not apply the tested rule, or the answer makes no sense in the sentence.

Slips of ANOTHER skill go in detected_mistake (at most one; leave it empty when there is none):
- A word with wrong letters that is otherwise right ("finised") is a spelling slip: skill_id spelling, error
  type spelling. The verdict is still about the tested skill.
- A wrong form of an irregular verb ("writed", "have went") is a grammar mistake, never spelling. When the
  exercise does not test irregular verbs, the verdict is about the tested skill (for example "have went" in a
  present perfect exercise is correct: the learner used have + a past form) and detected_mistake has skill_id
  irregular_verbs and error type grammar. When the exercise tests irregular verbs, "writed" is simply wrong.
- detected_mistake is never the tested skill: a mistake on the tested skill is the verdict.
- These skills are often confused. Use these lines to choose the skill_id:
{detectable_tag_when_lines}

Fields:
- When the verdict is wrong or partial, fill error_type, mistake_text, correction, why_wrong and rule:
  - mistake_text: the wrong words, copied exactly from the learner's full sentence. Do not change them.
  - correction: the right words that replace mistake_text.
  - why_wrong: why these words do not work in THIS sentence. Name the words of the sentence that show it.
    Talk to the learner ("You wrote ..."). If a Portuguese structure explains the mistake, say it briefly.
  - rule: the rule in one line, with the correct form.
  - error_type: grammar, vocabulary or word_order. Use spelling only when the exercise tests spelling.
- When the verdict is correct, leave error_type, mistake_text, correction, why_wrong and rule empty. If there is
  no detected_mistake, write in note one short line that says the answer is also right, and why.
- detected_mistake.mistake_text: the wrong words, copied exactly from the learner's full sentence.
  detected_mistake.correction: the right words.
- corrected_sentence: the learner's full sentence with ONLY the corrections of mistake_text and detected_mistake.
  Change nothing else. For a correct answer with no slip, copy the learner's full sentence.
- other_good_answers: other answers that fit the gap. An empty list if there are none.
- memory_tip: a short way to remember the rule. It can be empty for a correct answer.

Write why_wrong, rule, note and memory_tip in {explanation_language}. Never translate mistake_text, correction or
corrected_sentence: they stay exactly in English.
Tone: kind and encouraging, but the verdict stays strict. Never call a wrong answer correct to be kind.
"""

# One line per skill with a tag_when, except the tested skill. Part of the version hash too.
DETECTABLE_TAG_WHEN_LINE_TEMPLATE = "- {skill_id}: {tag_when}"


def make_detectable_tag_when_lines(tested_skill_id):
    tag_when_lines = []

    for skill in skills.get_learning_skills():
        if skill["id"] == tested_skill_id:
            continue

        if "tag_when" not in skill:
            continue

        tag_when_lines.append(DETECTABLE_TAG_WHEN_LINE_TEMPLATE.format(skill_id=skill["id"],
                                                                       tag_when=skill["tag_when"]))

    return "\n".join(tag_when_lines)


def make_accepted_answers_text(accepted_answers):
    if len(accepted_answers) == 0:
        return "none"

    return ", ".join(accepted_answers)


def build_gap_grade_prompt(exercise, your_answer, sentence_with_answer, explanation_language):
    # Returns the final prompt text and its version.
    # sentence_with_answer comes from grading.build_sentence_with_answer() (the caller builds it, so this file
    # does not import grading.py, which imports this file).
    skill = skills.get_skill(exercise.skill_id)

    prompt_text = GAP_GRADE_TEMPLATE.format(
        sentence=exercise.prompt_text, expected_answer=exercise.expected_answer,
        accepted_answers=make_accepted_answers_text(exercise.accepted_answers), your_answer=your_answer,
        sentence_with_answer=sentence_with_answer, skill_name=skill["name"], typical_mistake=skill["typical_mistake"],
        tag_when_line=make_tag_when_line(skill), detectable_tag_when_lines=make_detectable_tag_when_lines(skill["id"]),
        explanation_language=explanation_language,
    )

    all_templates = GAP_GRADE_TEMPLATE + TAG_WHEN_LINE_TEMPLATE + DETECTABLE_TAG_WHEN_LINE_TEMPLATE
    prompt_version = make_prompt_version(GAP_GRADE_PROMPT_NAME, all_templates)

    return prompt_text, prompt_version
