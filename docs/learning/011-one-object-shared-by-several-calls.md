# 011 - One object shared by several calls (the request budget)

- **Date:** 2026-11-16
- **Step of the plan:** Step 2 (Part 2)
- **Files where I used it:** `tutor/llm.py` (`RequestBudget`), `tutor/grading.py` (`ask_ai_for_grade()`)

## what it is

In Python, passing an object to a function does not copy it: the function receives the SAME object. If the function changes it (`budget.requests_left = budget.requests_left - 1`), the caller sees the change, and so does the next function that receives it.

So one object can carry a counter across several calls.

## why I needed it

Grading one answer can need two `ask()` calls: the grade, then one retry when the AI quoted wrong words. Each `ask()` had its own limit (4 requests, 20 s), so together they could reach 8 requests and 40 s. My rule: about 4 requests and 20 seconds for the WHOLE answer.

## how I used it here

`grading.py` creates ONE budget and gives it to both calls:

```python
shared_budget = llm.make_normal_budget()   # 4 requests, 20 s

grade, model_returned = llm.ask(prompt_text, prompt_version, grade_schema, "grade", shared_budget)
...
grade, model_returned = llm.ask(retry_prompt_text, prompt_version, grade_schema, "grade", shared_budget)
```

Inside `ask()`, before each request:

```python
if budget.is_used_up():
    raise AIUnavailableError("The AI did not give a usable answer in time. Try again in a minute.")

budget.requests_left = budget.requests_left - 1
```

If the first call used 3 requests (busy, busy, ok), the retry starts with only 1 left. The clock starts at the first request and keeps running for the second call.

Without a budget, `ask()` creates a new one, so old callers behave exactly as before. `make_fail_fast_budget()` is the same object with `busy_retries` False: the exercise stock uses it so a busy AI does not make me wait.

A test proves the two calls share the same object (`is` = the very same object, not an equal copy):

```python
assert fake_ask.budgets_received[0] is fake_ask.budgets_received[1]
```

## mistakes I made and how I fixed them

- Adding `budget` as the 5th argument of `ask()` moved `settings` to 6th place: 4 tests that passed `settings` in 5th place had to get `None` for the budget.
- The same sharing can be a trap: a default argument like `def ask(..., budget=make_normal_budget())` would create ONE budget when Python reads the file and share it between ALL calls forever. That is why the default is `None` and the budget is created inside the function.

## links

- Note 007 (retries with a time budget): the limits this object now carries.
- Python FAQ, why default values are shared between objects: https://docs.python.org/3/faq/programming.html#why-are-default-values-shared-between-objects
