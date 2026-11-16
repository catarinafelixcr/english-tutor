# 008 - a schema factory with a ClassVar (Pydantic)

- **Date:** 2026-11-16
- **Step of the plan:** Step 1 (Part 5), and Step 2 (Part 1) for the last section
- **Files where I used it:** `tutor/schemas.py`, `tutor/exercises.py`, `tests/test_schemas.py`

## what it is

A **schema factory** is a function that builds and returns a new Pydantic class each time it is called.
A **`ClassVar`** is a value that belongs to the class itself, not a field: Pydantic does not validate it, does not expect it in the data, and does not put it in the JSON schema. Together, they give a schema that "knows" some extra information (here, the sentences already saved) without the AI ever seeing it.

## why I needed it

Rule: if the AI writes a sentence I already have for this skill, the answer is invalid and must be retried once.
`llm.ask()` already retries once when Pydantic refuses an answer. So the easiest way was to make **Pydantic itself** refuse a repeated sentence. But a normal schema does not know which sentences are in my database, and the list changes for every skill and every call.

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

The JSON schema sent to Gemini is exactly the same as before (a test checks that the fields are only sentence, expected_answer, accepted_answers, hint). If Gemini repeats a sentence, `parse()` raises a `ValidationError`, and `llm.ask()` retries once, logs it as `invalid_answer` and counts it, with no new code.

`ClassVar[tuple]` is a type annotation, which my style rules normally avoid. Here Pydantic needs it: without `ClassVar`, Pydantic would think `used_sentences` is a field and send it to the AI.

## validating each item of a list alone (Step 2)

**The problem.** In Step 2 one request returns 5 exercises. With `exercises: list[GapExerciseDraft]`, Pydantic validates the whole list at once: if exercise 4 has a bad hint, the WHOLE answer is a `ValidationError`, and I lose the 4 good exercises (and `llm.ask()` spends one more request).

**The solution: two layers.**

1. The list uses a "loose" item model, with the same fields but no checks. The AI sees exactly the same JSON schema, and a bad item cannot break the list.
2. The code then checks each item alone with the strict model, in a `try / except ValidationError`, and keeps the position of each item.

```python
class GapExerciseItem(BaseModel):          # same fields, no validators
    sentence: str
    signal: str
    ...

def split_gap_exercise_items(items, draft_schema):
    for position, item in enumerate(items):
        try:
            draft = draft_schema(**item.model_dump())          # the strict checks run here
        except ValidationError as error:
            rejected_items.append({"position": position, "reason": describe_validation_error(error), ...})
            continue
        ...
        valid_items.append((position, draft))
```

**Zero good items is still an invalid answer.** The batch model has a validator that calls the same split function and raises only when NO item is valid. So `llm.ask()` keeps its rule "bad answer → retry once", with no new retry code. The schema factory from the first part is reused: `make_gap_exercise_batch_schema()` puts the strict draft schema (which knows the saved sentences) in a `ClassVar` of the batch.

**Why keep the position.** Each exercise was written for its own situation ("1. a delayed flight, 2. ..."). If item 2 is dropped, item 3 must still get situation 3, not situation 2. A test checks exactly this.

**Where the dropped items go.** To `logs/dropped_exercises.jsonl` with the reason, NOT to `logs/ai_log.jsonl`: there, one line = one request, and the daily request counter depends on that.

Note: since Step 2 the draft also has a `signal` field, and `llm.ask()` needs a task (`"create"`), so the code in the first part of this note is the Step 1 version.

## mistakes I made and how I fixed them

- First version: `def make_gap_exercise_draft_schema(used_sentences)` and inside the class
  `used_sentences: ClassVar[tuple] = tuple(used_sentences)`. 9 tests failed with
  `NameError: name 'used_sentences' is not defined`.
  Why: inside a class body, a name that is assigned in the class is looked up in the class and in the module,
  **never in the function around the class**. So the right side could not see the argument.
  Fix: give the argument another name (`sentences_already_saved`).
- A test checks that the plain `GapExerciseDraft` still has an empty list after the factory runs, so one call can never change the base class for the next call.

## links

- Pydantic ClassVar: https://docs.pydantic.dev/latest/concepts/models/#class-vars
- Python class body scope (execution model): https://docs.python.org/3/reference/executionmodel.html#resolution-of-names
