# 008 - a schema factory with a ClassVar (Pydantic)

- **Date:** 2026-11-16
- **Step of the plan:** Step 1 (Part 5)
- **Files where I used it:** `tutor/schemas.py`, `tutor/exercises.py`, `tests/test_schemas.py`

## what it is

A **schema factory** is a function that builds and returns a new Pydantic class each time it is called.
A **`ClassVar`** is a value that belongs to the class itself, not a field: Pydantic does not validate it, does
not expect it in the data, and does not put it in the JSON schema. Together, they give a schema that "knows"
some extra information (here, the sentences already saved) without the AI ever seeing it.

## why I needed it

Rule: if the AI writes a sentence I already have for this skill, the answer is invalid and must be retried once.
`llm.ask()` already retries once when Pydantic refuses an answer. So the easiest way was to make **Pydantic
itself** refuse a repeated sentence. But a normal schema does not know which sentences are in my database, and
the list changes for every skill and every call.

## how I used it here

**1. The base class has an empty ClassVar and a validator that reads it.**

```python
class GapExerciseDraft(BaseModel):
    used_sentences: ClassVar[tuple] = ()      # not a field: the AI never sees it

    sentence: str
    ...

    @model_validator(mode="after")
    def sentence_must_be_new(self):
        for used_sentence in self.used_sentences:
            if normalize_answer(used_sentence) == normalize_answer(self.sentence):
                raise ValueError("this sentence was already used for this skill: " + self.sentence)

        return self
```

**2. The factory builds a copy of the class with the real list.**

```python
def make_gap_exercise_draft_schema(sentences_already_saved):
    class NewGapExerciseDraft(GapExerciseDraft):
        used_sentences: ClassVar[tuple] = tuple(sentences_already_saved)

    return NewGapExerciseDraft
```

**3. `exercises.py` passes this new class to `llm.ask()`.**

```python
used_sentences = db.get_exercise_sentences(skill_id, database_path)
draft_schema = make_gap_exercise_draft_schema(used_sentences)
draft, model_returned = llm.ask(prompt_text, prompt_version, draft_schema)
```

The JSON schema sent to Gemini is exactly the same as before (a test checks that the fields are only
sentence, expected_answer, accepted_answers, hint). If Gemini repeats a sentence, `parse()` raises a
`ValidationError`, and `llm.ask()` retries once, logs it as `invalid_answer` and counts it, with no new code.

`ClassVar[tuple]` is a type annotation, which my style rules normally avoid. Here Pydantic needs it: without
`ClassVar`, Pydantic would think `used_sentences` is a field and send it to the AI.

## mistakes I made and how I fixed them

- First version: `def make_gap_exercise_draft_schema(used_sentences)` and inside the class
  `used_sentences: ClassVar[tuple] = tuple(used_sentences)`. 9 tests failed with
  `NameError: name 'used_sentences' is not defined`.
  Why: inside a class body, a name that is assigned in the class is looked up in the class and in the module,
  **never in the function around the class**. So the right side could not see the argument.
  Fix: give the argument another name (`sentences_already_saved`).
- A test checks that the plain `GapExerciseDraft` still has an empty list after the factory runs, so one call
  can never change the base class for the next call.

## links

- Pydantic ClassVar: https://docs.pydantic.dev/latest/concepts/models/#class-vars
- Python class body scope (execution model): https://docs.python.org/3/reference/executionmodel.html#resolution-of-names
