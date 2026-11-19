# Progress

Current step: **Step 2 - Practice** (started 2026-11-16)

Tick a task when it is finished. Write the date when a step is done.

## Step 0 - Setup

- [x] GitHub repo created (README, MIT license, Python .gitignore)
- [x] Virtual environment created
- [x] requirements.txt written and installed
- [x] Gemini API key created and tested (model gemini-3.5-flash-lite: 15 RPM, 500 RPD)
- [x] .env created, .env.example committed, .env and data/ in .gitignore
- [x] Folders created (pages, tutor, data, tests, eval, docs)
- [x] app.py shows the menu with one empty page per section
- [x] First commit pushed

Done when: the app opens in the browser with all menu items, and the repo is on GitHub.

Done on: 2026-11-16

## Step 1 - Foundation

- [x] Part 1: skill list (`tutor/skills.py`, 53 skills) with tests
- [x] Part 2: database (`tutor/db.py`, `Exercise` and `Attempt` models) with tests
- [x] Part 3: `GapExercise` schema and first prompt
- [x] Part 4: AI engine (`tutor/llm.py`), 429 experiment, request counter
- [x] Part 5: demo script (`scripts/step1_demo.py`), one skill per prompt, no repeated sentences

Done when: a small script asks the AI for one fill-the-gap sentence, gets a valid object with a skill id from your list, and saves it in the database.

Done on: 2026-11-16

## Step 2 - Practice

- [x] Part 1: batches of 5 exercises per request, `exercise_type` column (first migration, with backup), stricter batch prompt (one clear signal, level vocabulary, meaning hints)
- [x] First thing next session: run `python -m scripts.step2_batch_demo present_simple` (signal + default effort, never tested for real: 2 tries today, both 503). Done: 0 of 5 weak, first try
- [x] Part 2: check answers (code first, then the AI), `GapGrade`, save attempts, exercise stock (never wait for a live request). Done 2026-11-16: 327 tests, grade demo 6/6 graded with the real AI
- [x] Part 3: the Practice page (fill the gap), with hint, skip, report a problem, no double save. Done 2026-11-16: 356 tests (11 page tests with AppTest), tested in the browser
- [ ] Part 3b: clue type per skill, `add_words`, trap + trap_why (database v3), known Portuguese traps, demo per clue type, level before skill, instruction line
- [ ] Part 3c: rule cards, help ladder (database v4)
- [ ] Part 4: gold file (50 rows), `run_eval.py`, hand review of 20 exercises (4a done 2026-11-19: gold file committed, my verdicts in progress)
- [ ] Part 5: Fix the error and Word order

Done when: you can do 20 sentences without an app error, every attempt is in the database with a skill tag, and the grader agrees with you on 45 of the 50 gold rows.

## Step 3 - Tutor brain, Learn and Home

Not started. (Swapped with Writing on 2026-11-19; older JOURNAL entries call it Step 4.)

## Step 4 - Writing

Not started.

## Step 5 – Listening

Not started.

## Step 6 - Translate

Not started.

## Step 7 - Review

Not started.

## Step 8 - Progress dashboard

Not started.

## Step 9 - Speaking and conversation

Not started.

## Step 10 - Polish

Not started.

## Notes

Write here anything you learned, problems you found, and decisions you made.