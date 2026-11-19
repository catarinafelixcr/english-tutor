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
- trap: the wrong answer a Portuguese speaker would most likely write in this gap.
- trap_why: one or two short sentences: why the trap is wrong here, then the rule with the correct form.
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
- The gap must test the skill above and nothing else. Do not turn it into a question about another skill.
{clue_rules}
- The sentence must contain a clear signal that makes the answer of the tested skill the ONLY natural answer:
  other words of the sentence, or the meaning of the situation. It must contain no signal that calls for
  another answer. The typical mistake above shows the kind of difference this skill is about.
- Use vocabulary at the {level} level or easier, and grammar at the {level} level or easier.
  The difficulty must be the skill, not the words.
- signal: the exact words of your sentence that are this clear signal. Copy them from the sentence.
  Not the gap, not the words in brackets. If you cannot point to a signal, the sentence is ambiguous: rewrite it.
- expected_answer: the word or words that fill the gap.
- accepted_answers: only other answers that are also natural in this sentence AND test the same thing as the
  expected answer (for example a short form). Use an empty list if there are none.
- trap: the wrong answer a Portuguese speaker would most likely write in this gap: the typical mistake above,
  in this sentence. It must be clearly WRONG for the tested skill: not half right, not a spelling slip, and not
  a mistake of another skill. Build the sentence so the trap is wrong and only the expected answer fits.
- trap_why: for a learner who wrote the trap. One or two short sentences in simple English: why the trap is
  wrong in this sentence, then the rule with the correct form. Do not repeat the whole sentence.
- hint: a short clue about the MEANING or the situation of the sentence, not about grammar. Do not name the
  rule, the tense or the grammar word. Never write the expected answer or an accepted answer in the hint.

Before you answer, read each sentence again with the gap filled. If a different answer would also be natural,
the sentence is ambiguous: rewrite it so only the tested answer fits. Then read it with the trap: the trap
must be clearly wrong.
"""

# The clue after the gap depends on the skill (skills.GAP_CLUES). Only the block of the skill's clue type goes
# into the prompt. No example sentences here: an example of one skill would push every skill toward it.
GAP_CLUE_RULES = {
    "base_word": """- Clue: right after the gap, write ONE base word in round brackets: the base form of the verb, noun
  or adjective the learner must change. The learner writes the right form, and adds any other words the
  skill needs. For a negative answer, write not first, joined with a slash.
- Write the word in brackets in its base form, never in the form of the answer.""",
    "words": """- Clue: right after the gap, write in round brackets the words the learner must use, in their base
  form, separated by a slash ( / ). The learner puts them in the right order and form.
- When the order of the words is what the skill tests, do not write them already in the correct order.""",
    "portuguese": """- Clue: right after the gap, write in round brackets the Portuguese word or short expression
  (European Portuguese, from Portugal) that the learner must say in English. The gap tests which English word
  is right for it.
- Choose a Portuguese word whose FIRST English translation, the one a Portuguese speaker thinks of first, is
  wrong in this sentence. That wrong translation is the trap. A Portuguese word with one obvious translation
  does not test this skill.
- When a situation below gives a Portuguese word, an answer and a trap, use exactly them: that Portuguese word
  in the brackets, that answer (in the form the sentence needs), and that trap.
- Never write the English answer, or a part of it, in the brackets.""",
    "add_words": """- Clue: right after the gap, write in round brackets the noun or the time words the learner must
  use, exactly as they appear at the end of the answer. The learner writes them with the word they need before them,
  or with nothing before them when no word is needed.
- The expected answer and every accepted answer end with the words in brackets.
- Mix the exercises: some need a word before the brackets and, when the skill allows it, some need no word.""",
    "none": """- Clue: no brackets. The other words of the sentence and the situation are the only clue.
- Do not write brackets anywhere in the sentence.""",
}

# Added to a situation line when the skill has known traps (skills.WORD_TRAPS): one pair per exercise.
WORD_TRAP_LINE_TEMPLATE = (" | Portuguese word: {portuguese} | answer: {answer} | trap: {trap}"
                           " | the answer is right for: {used_for}")

# Added after it when the pair has other right answers (costume → habit, also custom).
ALSO_RIGHT_TEMPLATE = " | also right, put in accepted_answers: {also_right}"


def make_clue_rules_text(skill):
    return GAP_CLUE_RULES[skills.get_gap_clue(skill["id"])]


def make_all_clue_rules_text():
    # For the prompt version: every block, in a fixed order, so changing one word of any block gives a new
    # version, and the version stays the same for every skill.
    clue_rules_texts = []

    for gap_clue_type in skills.GAP_CLUE_TYPES:
        clue_rules_texts.append(GAP_CLUE_RULES[gap_clue_type])

    return "\n".join(clue_rules_texts)


def make_situations_text(sub_topics, word_traps):
    # "1. a delayed flight\n2. checking in at a hotel\n..."
    # word_traps: one trap pair per sub-topic (same order), or an empty list when the skill has none.
    situation_lines = []

    for position, sub_topic in enumerate(sub_topics):
        situation_line = str(position + 1) + ". " + sub_topic

        if len(word_traps) > 0:
            word_trap = word_traps[position]
            situation_line = situation_line + WORD_TRAP_LINE_TEMPLATE.format(
                portuguese=word_trap["portuguese"], answer=word_trap["answer"], trap=word_trap["trap"],
                used_for=word_trap["used_for"])

            if "also_right" in word_trap:
                situation_line = situation_line + ALSO_RIGHT_TEMPLATE.format(
                    also_right=", ".join(word_trap["also_right"]))

        situation_lines.append(situation_line)

    return "\n".join(situation_lines)


def build_gap_exercise_batch_prompt(level, topic, sub_topics, skill, sentences_to_avoid, word_traps):
    # One exercise per sub-topic. Returns the final prompt text and its version.
    # word_traps: one known trap pair per sub-topic (word_choice, false_friends), or an empty list.
    if len(word_traps) > 0 and len(word_traps) != len(sub_topics):
        raise ValueError("word_traps needs one pair per sub-topic")

    prompt_text = GAP_EXERCISE_BATCH_TEMPLATE.format(
        exercise_count=len(sub_topics), level=level, topic=topic, skill_name=skill["name"],
        typical_mistake=skill["typical_mistake"], tag_when_line=make_tag_when_line(skill),
        situations=make_situations_text(sub_topics, word_traps),
        sentences_to_avoid=make_sentences_to_avoid_text(sentences_to_avoid), clue_rules=make_clue_rules_text(skill),
    )

    prompt_version = make_prompt_version(GAP_EXERCISE_BATCH_PROMPT_NAME, GAP_EXERCISE_BATCH_TEMPLATE
                                         + TAG_WHEN_LINE_TEMPLATE + make_all_clue_rules_text()
                                         + WORD_TRAP_LINE_TEMPLATE + ALSO_RIGHT_TEMPLATE)

    return prompt_text, prompt_version


# ---------- fill the gap: grade one answer (Step 2, Part 2) ----------

GAP_GRADE_PROMPT_NAME = "gap_grade"

# English until Step 3 adds the selector (Portuguese or English).
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
- Example: "She has writed the report." in a present perfect exercise: the verdict is correct (has + a past form),
  and detected_mistake is irregular_verbs, "writed" → "written". It is NOT a wrong verdict.
- detected_mistake is never the tested skill: a mistake on the tested skill is the verdict.
- One slip counts against ONE skill only: detected_mistake never quotes the same words as mistake_text.
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

# Added at the end of the prompt for the ONE retry, one note per problem found. Part of the version hash too.
GAP_GRADE_QUOTE_RETRY_NOTE_TEMPLATE = """
Your previous answer quoted words that are not in the learner's full sentence: {bad_quotes}.
Copy mistake_text and detected_mistake.mistake_text exactly from this sentence: {sentence_with_answer}
"""

GAP_GRADE_SAME_WORDS_RETRY_NOTE = """
Your previous answer quoted the same words in mistake_text and in detected_mistake, so one slip counted against
two skills. Decide which skill the slip belongs to. If it is a slip of another skill (for example a wrong
irregular form after a correct have/has), the verdict is about the tested skill and the slip goes only in
detected_mistake. If it is the tested skill's mistake, leave detected_mistake empty.
"""


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

    all_templates = (GAP_GRADE_TEMPLATE + TAG_WHEN_LINE_TEMPLATE + DETECTABLE_TAG_WHEN_LINE_TEMPLATE
                     + GAP_GRADE_QUOTE_RETRY_NOTE_TEMPLATE + GAP_GRADE_SAME_WORDS_RETRY_NOTE)
    prompt_version = make_prompt_version(GAP_GRADE_PROMPT_NAME, all_templates)

    return prompt_text, prompt_version


def add_retry_notes(prompt_text, bad_quotes, same_words_twice, sentence_with_answer):
    # bad_quotes: the wrong quotes themselves, for example ["have finish"] (empty list = no quote problem).
    # same_words_twice: True when the main and the detected mistake quote the same words.
    # One retry fixes both problems. The version does not change.
    retry_prompt_text = prompt_text

    if len(bad_quotes) > 0:
        quoted_texts = []

        for bad_quote in bad_quotes:
            quoted_texts.append("\"" + bad_quote + "\"")

        retry_prompt_text = retry_prompt_text + GAP_GRADE_QUOTE_RETRY_NOTE_TEMPLATE.format(
            bad_quotes=", ".join(quoted_texts), sentence_with_answer=sentence_with_answer)

    if same_words_twice:
        retry_prompt_text = retry_prompt_text + GAP_GRADE_SAME_WORDS_RETRY_NOTE

    return retry_prompt_text
