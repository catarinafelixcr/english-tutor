"""Pydantic models: the exact shape of every AI answer, and of every database record (Exercise, Attempt).

Pydantic fields need type annotations: this is the one exception to the "no type hints" rule in CLAUDE.md.
Creating a model needs field names (Attempt(verdict="wrong", ...)): Pydantic does not accept positional values.
"""

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tutor import skills

# ---------- shared checks ----------

def check_skill_id_exists(skill_id):
    if not skills.is_valid_skill_id(skill_id):
        raise ValueError("unknown skill id: " + skill_id)

    return skill_id


def convert_to_utc(moment):
    # Every date is stored in UTC. A date without a time zone is refused, because we cannot know its real time.
    if moment is None:
        return None

    if moment.tzinfo is None:
        raise ValueError("a date needs a time zone, for example datetime.now(timezone.utc)")

    return moment.astimezone(timezone.utc)


def normalize_answer(answer_text):
    # For comparing answers: small letters, no spaces at the ends, one space between words.
    small_letters_text = answer_text.strip().lower()
    normalized_text = " ".join(small_letters_text.split())

    return normalized_text


def contains_whole_words(text, words):
    # True if "words" appears in "text" as whole words, ignoring capital letters.
    # "am" is found in "I am here" but not in "the same verb".
    pattern = r"\b" + re.escape(normalize_answer(words)) + r"\b"

    return re.search(pattern, normalize_answer(text)) is not None


# ---------- database records ----------

class Exercise(BaseModel):
    """One row of the "exercises" table."""

    # Unknown fields are refused, so a typo in a field name cannot pass silently.
    # validate_assignment: a field changed later (exercise.level = "B1") is checked too.
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    section: Literal["practice", "learn", "writing", "listening", "translate", "review", "speaking"]
    skill_id: str
    level: Literal["A2", "B1", "B2", "C1"]
    topic: str | None = None
    prompt_text: str = Field(min_length=1)
    expected_answer: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    created_at: datetime | None = None

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_exist(cls, skill_id):
        return check_skill_id_exists(skill_id)

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_utc(cls, created_at):
        return convert_to_utc(created_at)


class Attempt(BaseModel):
    """One row of the "attempts" table: one answer (or one part of an answer) about one skill."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    submission_id: str = Field(min_length=1)
    exercise_id: int
    section: Literal["practice", "learn", "writing", "listening", "translate", "review", "speaking"]
    skill_id: str
    source: Literal["targeted", "detected"]
    your_answer: str
    verdict: Literal["correct", "partial", "wrong"]
    error_type: Literal["grammar", "vocabulary", "spelling", "word_order", "naturalness"] | None = None
    explanation: str = ""
    mistake_text: str | None = None
    correction: str | None = None
    hint_used: bool = False
    seconds_taken: float | None = Field(default=None, ge=0)
    graded_by: Literal["code", "ai"]
    model: str | None = None
    prompt_version: str | None = None
    created_at: datetime | None = None

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_exist(cls, skill_id):
        return check_skill_id_exists(skill_id)

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_utc(cls, created_at):
        return convert_to_utc(created_at)

    @model_validator(mode="after")
    def error_type_must_match_verdict(self):
        if self.verdict == "correct" and self.error_type not in [None, "naturalness"]:
            raise ValueError("a correct answer can only have the error type naturalness, or none")

        if self.verdict != "correct" and self.error_type is None:
            raise ValueError("a wrong or partial answer needs an error type")

        if self.verdict != "correct" and self.error_type == "naturalness":
            raise ValueError("naturalness is only for correct sentences")

        if self.error_type == "naturalness" and self.source != "detected":
            raise ValueError("a naturalness row is always detected, never targeted")

        return self

    @model_validator(mode="after")
    def model_must_match_grader(self):
        if self.graded_by == "code" and (self.model is not None or self.prompt_version is not None):
            raise ValueError("graded by code: model and prompt_version must stay empty")

        if self.graded_by == "ai" and (self.model is None or self.prompt_version is None):
            raise ValueError("graded by ai: model and prompt_version are required")

        return self


# ---------- AI answers ----------

class GapExercise(BaseModel):
    """One fill-the-gap exercise, exactly as the AI must return it."""

    # Unknown fields are refused: if the AI adds or misspells a field, the answer is invalid and llm.py retries.
    model_config = ConfigDict(extra="forbid")

    sentence: str
    expected_answer: str
    accepted_answers: list[str] = Field(default_factory=list)
    skill_id: str
    hint: str
    level: Literal["A2", "B1", "B2", "C1"]

    @field_validator("sentence")
    @classmethod
    def sentence_must_have_exactly_one_gap(cls, sentence):
        # Exactly three underscores in the whole sentence, together: "___". So "____" or "a_b ___" are refused.
        if sentence.count("_") != 3 or "___" not in sentence:
            raise ValueError("the sentence needs exactly one gap written as ___ : " + sentence)

        return sentence

    @field_validator("expected_answer")
    @classmethod
    def expected_answer_must_not_be_empty(cls, expected_answer):
        if expected_answer.strip() == "":
            raise ValueError("the expected answer is empty")

        return expected_answer.strip()

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_be_a_fill_the_gap_skill(cls, skill_id):
        # Only active learning skills, never general skills, never capitalization (PLAN.md, Step 2).
        if skill_id not in skills.get_fill_the_gap_skill_ids():
            raise ValueError("this skill id cannot be used in fill the gap: " + skill_id)

        return skill_id

    @field_validator("hint")
    @classmethod
    def hint_must_not_be_empty(cls, hint):
        if hint.strip() == "":
            raise ValueError("the hint is empty")

        return hint.strip()

    @model_validator(mode="after")
    def accepted_answers_must_be_clean(self):
        seen_answers = [normalize_answer(self.expected_answer)]

        for accepted_answer in self.accepted_answers:
            normalized_accepted_answer = normalize_answer(accepted_answer)

            if normalized_accepted_answer == "":
                raise ValueError("accepted_answers has an empty item")

            if normalized_accepted_answer == normalize_answer(self.expected_answer):
                raise ValueError("accepted_answers repeats the expected answer: " + accepted_answer)

            if normalized_accepted_answer in seen_answers:
                raise ValueError("accepted_answers has a duplicate: " + accepted_answer)

            seen_answers.append(normalized_accepted_answer)

        return self

    @model_validator(mode="after")
    def hint_must_not_give_the_answer(self):
        if contains_whole_words(self.hint, self.expected_answer):
            raise ValueError("the hint gives the expected answer: " + self.hint)

        for accepted_answer in self.accepted_answers:
            if contains_whole_words(self.hint, accepted_answer):
                raise ValueError("the hint gives an accepted answer: " + self.hint)

        return self
