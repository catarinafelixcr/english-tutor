"""Pydantic models: the exact shape of every AI answer, and of every database record (Exercise, Attempt).

Pydantic fields need type annotations: this is the one exception to the "no type hints" rule in CLAUDE.md.
Creating a model needs field names (Attempt(verdict="wrong", ...)): Pydantic does not accept positional values.
"""

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
