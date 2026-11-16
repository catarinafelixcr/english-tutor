# 012 - How Streamlit reruns a page and remembers things (session_state)

- **Date:** 2026-11-16
- **Step of the plan:** Step 2 (Part 3)
- **Files where I used it:** `pages/practice.py`, `app.py`, `tests/test_practice_page.py`

## what it is

Streamlit runs the WHOLE page file again, from the first line to the last, after every click, every Enter and every change in a selector. This is called a **rerun**. Normal Python variables start again from zero at each rerun.

`st.session_state` is a dictionary that survives reruns. It is the page's memory for one browser tab: what is on screen, what I already did, the counters.

## why I needed it

The Practice page has 3 moments: answering → result → next sentence. After I click "Check", the page runs again from the top. Without a memory, it would not know which sentence I was answering, when it appeared (for the seconds), whether I opened the hint, or that it must now show the result instead of the answer box.

## how I used it here

**1. Memory with starting values.** On the first run, the keys are missing, so they get their starting value. On later runs they are kept:

```python
for memory_key, starting_value in STARTING_MEMORY.items():
    if memory_key not in st.session_state:
        st.session_state[memory_key] = starting_value
```

The memory of ONE exercise (`EXERCISE_MEMORY`) is put back to its starting values by `forget_current_exercise()` when I click "Next", skip a sentence or change a filter.

**2. The page decides what to draw from the memory**, not from the button that was clicked:

```python
if st.session_state.practice_result is not None:
    draw_result()
    draw_report_box()
    draw_next_button()
else:
    draw_answer_form()
    draw_hint_and_skip()
```

**3. `st.rerun()`** stops the current run and starts a new one at once. After grading, the page saves the result in the memory and calls `st.rerun()`, so the answer box disappears and the result box appears.

**4. `st.form`.** Inside a form, typing does not cause a rerun: the values are sent together when I press Enter or "Check". So Enter sends my answer.

**5. Widget keys.** A widget with `key="practice_level"` keeps its value in `st.session_state["practice_level"]`. I can change it BEFORE the widget is drawn (the level jumps to B1 when I choose a B1 skill), never after. The answer box has a key with the submission id in it (`"practice_answer_" + submission_id`), so each new exercise gets a new, empty box.

**6. `@st.cache_resource`** in `app.py`: the function runs once per app start, not once per rerun. `init_db()` is safe to run many times, but there is no reason to run it after every click.

**7. Testing a page with no browser: `AppTest`** (it comes with Streamlit). It runs the page, then I "click" and "type" in Python:

```python
page = AppTest.from_file(PAGE_PATH, default_timeout=15)
page.run()
page.text_input[0].input("am")
page.button(key="practice_check").click()
page.run()
assert page.success[0].value.startswith("**Correct!**")
```

## mistakes I made and how I fixed them

- **A rerun can come while the AI is still grading** (a double click, or Enter twice). Streamlit then starts a second run, and the first one may still finish and save. Fix: one `submission_id` reserved per exercise on screen, a check before the AI call, and a lock in `save_attempts()` (`BEGIN IMMEDIATE`), so one answer is never saved twice. A test with two threads proves it.
- **A list as a starting value is shared.** If the starting value is a list, every reset could give the same list object, and an `append` would change it everywhere. `forget_current_exercise()` creates a new list each time.
- **Markdown reads `___` as formatting** (a line, or bold text). Every sentence goes through `escape_markdown()` before `st.markdown()`, so the gap shows as `___`.
- **Default arguments are fixed when Python reads the function.** To let the page test use a temporary database, the page passes `db.DEFAULT_DATABASE_PATH` in every call (read at call time), and the test changes it with `monkeypatch`.

## links

- Note 006 (fakes and monkeypatch): the fake AI in the page test.
- Note 010 (transactions): the lock that stops a double save.
- Streamlit, session state: https://docs.streamlit.io/develop/concepts/architecture/session-state
- Streamlit, app testing (AppTest): https://docs.streamlit.io/develop/concepts/app-testing
