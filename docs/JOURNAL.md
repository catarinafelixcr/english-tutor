# Project journal

The diary of this project: what I did, why, and what I decided.
Newest entry at the top. One entry per work session.

---

## 2026-11-16 - Step 2 Part 3: the Practice page

**What I did**

- The Practice page (`pages/practice.py`): skill, level and topic selectors; one sentence from the stock; answer box (Enter sends); hint; green / yellow / red result with the 3 parts, the corrected sentence and the memory tip; "Next sentence"; a session counter ("This session: 7 answers · 5 correct").
- Three additions of mine: "Report a problem" on the result, "Skip: this sentence is bad" before answering, and a guard so one answer is never saved twice.
- `init_db()` now runs once when the app starts (`@st.cache_resource` in `app.py`).
- 4 commits (`b21fdf1`, `dd78da2`, `064684a`, `e1870c8`). Tests: 356 (327 before), ruff clean. Not pushed yet.
- Learning note 012: how Streamlit reruns a page and remembers things (`session_state`).

**Decisions and why**

| Decision | Why |
| --- | --- |
| Default level A2 | I change it myself when the A2 skills are strong |
| With "Any skill", the skill name stays hidden until I answer | The name says the rule; the hint must be about meaning, never the grammar |
| The skill selector comes first, then the level; the level can go up, never below the skill's level | A B1 skill in an A2 exercise makes no sense (PLAN.md) |
| One selectbox, labels like "Verbs · Present perfect (B1)" | Streamlit's selectbox has no groups; the category at the start does the grouping |
| A filter change = a new exercise; the old one stays in the stock | Nothing is lost, no request is wasted |
| Reports in a new table `problem_reports`, not a log file | "A bad sentence leaves the stock" is a SQL rule (`NOT EXISTS`), and Part 4 / Step 7 will query the reports |
| No migration for the new table | A migration changes tables that exist (a new column). `CREATE TABLE IF NOT EXISTS` adds a new table to an old database; database version stays 2, no backup needed |
| `UNIQUE (submission_id, kind)` on reports | A double click on "Send report" saves one row |
| Double save: the page reserves a `submission_id` per exercise; `grade_gap_answer()` stops before the AI call if it is saved; `save_attempts()` checks again under `BEGIN IMMEDIATE` | A rerun while the AI grades can let the first run finish AND start a second one. Only a lock inside the database makes "check, then insert" one step |
| Skip button saves a `bad_sentence` report with an empty answer and no attempt | A bad sentence is often impossible to answer; I should not have to type something to report it |
| Mastery (Step 4): attempts on `bad_sentence` exercises and answers reported as `wrong_grade` do not count, whatever the verdict; the rows stay | A bad sentence or a wrong grade is noise, not my level. Written in PLAN.md Step 4 with its tests |
| Speed charts (Step 8) leave out answers over about 3 minutes; the database keeps the real seconds | I probably left the page; the raw data stays honest |
| After an AI error while grading, the answer stays in the box and the seconds keep counting | Nothing is saved, so "Check" again is safe, and the time stays honest |
| Every text from the AI or the database goes through `escape_markdown()` | Markdown turns `___` into a line and `$` into a formula |
| The page passes `db.DEFAULT_DATABASE_PATH` in every call | Default arguments are fixed when Python reads the function; this lets the page test use a temporary database |

**Problems and how I solved them**

- The first test run passed with no change (355, then 356 with the Skip test).
- A starting value that is a list would be shared between resets: `forget_current_exercise()` creates a new list each time.
- I did not make the correct word bold inside the corrected sentence (my plan said so): a correct answer has no `correction` field to find it, so it would work only sometimes.
- `docs/PROGRESS.md` had my own change (long dashes → short hyphens in the titles); kept as it is.

**Next**

- Done the same day: tested the page in the browser, it works. Part 3 ticked.
- Part 4: gold file (50 rows), `run_eval.py`, hand review of 20 exercises. The `wrong_grade` reports can give real rows for the gold file.

---

## 2026-11-16 - Step 2 Part 2: checking answers, the grader prompt, the exercise stock

**What I did**

- Ran the batch demo first (open since last session): **0 weak sentences of 5**, first try, no 503 (`gap_exercise_batch@a64005`, signal + default effort).
- Part 2 in 8 small commits:
  - `GapGrade` + `DetectedMistake` schemas (`344bd07`): the main error type can be `spelling` only when the exercise tests spelling.
  - `save_attempts()` (`ccd464d`): all rows of one answer in ONE transaction, all or none.
  - Code checks on the AI grade (`eecdd80`): quotes must be whole words of my full sentence (bracket clue removed); `corrected_sentence` must equal my sentence with the corrections (only logged).
  - The grader prompt `gap_grade` (`8075f02`): verdict rules, slips of other skills, 3 parts, the `tag_when` lines of the other skills.
  - `RequestBudget` in `llm.py` (`9be457f`): several `ask()` calls share 4 requests and 20 seconds; a fail-fast version for refills.
  - `grade_gap_answer()` (`efc22d0`): code first, then the AI, one retry for bad quotes, fallback to my answer, `GapResult` for the page.
  - Grade demo (`c36e80e`) and the fixes it showed (`6a5493e`).
  - The exercise stock (`bc6b5d5`): `get_next_gap_exercise()`.
- Tests: 327 in total (199 at the end of Part 1, so 128 new, with the code check of `afecebd`), ruff clean. Pushed to GitHub.
- Learning notes 010 (database transactions: all or nothing) and 011 (one object shared by several calls: the request budget).

**The batch demo (present simple, A2, daily life)**

| Prompt version | Weak sentences |
| --- | --- |
| `gap_exercise_batch@782cdb` | 5 of 5 |
| `gap_exercise_batch@ef2ee2` | 2 of 5 |
| `gap_exercise_batch@a64005` (signal + default effort) | **0 of 5** |

- Every sentence had a clear signal ("Every morning", "On Saturdays", "Each Tuesday", "Every Sunday", "During every check-up").
- To watch in the hand review (Part 4): all 5 tested only the `-s` of he/she/it. No do/does, no negative, no question. Good sentences, but not the whole skill.

**The grade demo (real Gemini, 6 answers, temporary database)**

| Answer | Expected | Gemini |
| --- | --- | --- |
| writen | correct + spelling | ✅ |
| writed | correct + irregular_verbs (Almost) | ❌ wrong + irregular_verbs on the SAME word |
| write | partial | ✅ |
| have been living | correct + note | ✅, but the note said "present continuous" (it is present PERFECT continuous) |
| live | wrong | ✅ with the Portuguese reason ("vivo aqui desde") |
| asdf | wrong | ✅ |

- No bad quotes, every corrected sentence matched. Tone: kind, and it quotes my words.
- **4 of 10 requests were 503 with `low` effort** (on the grader). So the 503 errors are not only a default-effort problem. All recovered inside the budget (1–2 retries).
- Gemini wrote a `note` on wrong and partial answers too, although the prompt says to leave it empty.

**Decisions and why**

| Decision | Why |
| --- | --- |
| Quote checks in `grading.py`, not in the schema | A schema error twice loses the whole grade; my rule is "never block me", so the code needs the grade to fall back |
| One retry fixes all problems at once (bad quotes + same words twice), one note per problem | Fewer requests; the free tier has a daily limit |
| One budget per graded answer: about 4 requests and 20 s, counting the retry | My ceiling. Without it, two `ask()` calls could reach 8 requests and 40 s |
| One slip counts against ONE skill: the detected mistake cannot quote the same words as the main one; retry, then keep the verdict and drop the detected row | The demo counted "writed" twice; that would lower two skills for one slip |
| `note` only for a correct answer with no slip | Gemini ignores the prompt here. The reminder is enough for a slip; wrong/partial have the 3 parts |
| The note stays required on "also right" answers but not with a detected slip | Two lines saying the same thing on screen |
| `corrected_sentence` check: only logged | A different sentence is a quality signal, not a reason to spend a request |
| The bracket clue is removed before checking quotes | A quote "finish" must not be found in "(finish)" |
| The topic is a filter on the stock; "any topic" is the default | Asking for travel and getting a meetings sentence would feel like a bug |
| Stock: refill below 3; fail fast while exercises remain; normal retries only when the stock is empty | I keep practising when Gemini is busy, and only wait when there is nothing else |
| "Any skill" picks a random exercise from the stock, not the oldest | Not 5 sentences on the same skill in a row |
| Part 4 additions: review ~20 explanations for wrong rules or terms; compare the gold agreement with `low` vs default grader effort | The demo showed a wrong grammar term with a right verdict: the gold verdicts alone would not see it |

**Problems and how I solved them**

- An exact match with my own capital letter ("Written") built the corrected sentence with "Written" in the middle. A test caught it: the corrected sentence now uses the matched correct answer.
- `\b` fails when a quote ends with an apostrophe or a full stop: used `(?<!\w)…(?!\w)` instead.
- The fallback quote (my answer) plus the correction can give "has has written": logged as a corrected-sentence mismatch, as expected.
- Claude ran a small Python script to tick PLAN.md without asking first (my rule: ask before every terminal command). It only ticked 18 lines; noted so it does not happen again.

**Next**

- Part 3: the Practice page (fill the gap), using `get_next_gap_exercise()` and `grade_gap_answer()`.

---

## 2026-11-16 - Step 2 Part 1: batches of 5, the first migration, a stricter prompt

**What I did**

- Planned Step 2 in 5 parts (batch creation, answer checking, Practice page, gold file, two more exercise types) and wrote many decisions into PLAN.md before any code.
- Part 1 (`02ad729`): one request now creates 5 fill-the-gap exercises. Each item is checked alone, bad items are dropped and logged in `logs/dropped_exercises.jsonl`. New column `exercise_type` (first migration, version 1 → 2, with a backup copy). `get_unanswered_exercises()` so saved exercises are used before asking the AI.
- The `signal` field (`9c36f05`): the AI names the exact words that force the answer; the code checks they are in the sentence and are not the gap or the verb in brackets.
- Reasoning effort per task (`da9decc`): `llm.ask()` receives `"create"` or `"grade"`, and the values live in `.env` (`AI_REASONING_EFFORT_CREATE=` empty = Gemini's default, `AI_REASONING_EFFORT_GRADE=low`).
- Removed 8 ambiguous exercises from `data/tutor.db` (with a backup before each cleanup) and kept them in `eval/weak_sentences.md`.
- Tests: 199 in total (53 new), ruff clean. Pushed to GitHub.
- Learning note 009 (database migrations) and a new section in 008 (validating each item of a list alone).

**The prompt, measured on real sentences (present simple, A2)**

| Prompt version | What changed | Weak sentences |
| --- | --- | --- |
| `gap_exercise_batch@782cdb` | first batch prompt, hints about meaning | 5 of 5 ("this week", "today", "tomorrow", no signal, hard words) |
| `gap_exercise_batch@ef2ee2` | + one clear signal, vocabulary at the level, self-check | 2 of 5 (one still had "today", one had no signal) |
| with `signal` + default effort | + the AI must name its signal | not measured yet (Gemini busy) |

- The new hints are about meaning ("the scheduled call opens after a short delay"), not grammar ("the form for he, she, it").
- Tokens for 5 exercises: 459 prompt + 297 answer, about 1.5× one Step 1 exercise for 5× the exercises.

**Decisions and why**

| Decision | Why |
| --- | --- |
| Verdicts: correct = fits (spelling slip = correct + detected spelling); partial = half of the tested rule ("has finish"); wrong = rule not applied | My rule. A partial must mean something precise to count as half in mastery |
| A slip that belongs to ANOTHER skill = tested skill correct + detected wrong row ("writed" in past simple, "have went" in present perfect → irregular_verbs) | I used the structure, I chose the wrong form of an irregular verb. Shown as yellow "Almost" |
| Review (Step 7) also brings back a submission where only a detected row is wrong | Otherwise "writed" would never come back |
| Word order skills: the word_order category + too_enough, phrasal_verbs_separable, have_something_done | With "to be" or articles, word order does not test the skill |
| Gold file: Claude writes 50 rows with my verdict empty; ≥ 10 of my real mistakes; a `sure` column; Claude's verdicts in a separate file I do not open first | My verdicts must be mine; three graders (me, Claude, Gemini) to compare |
| Migration, not a new database; backup before any migration; one transaction per step | Practice for later steps, and a failed migration must leave nothing half done |
| The batch list uses a loose item model; each item is checked alone | One bad item must not lose the 4 good ones |
| Signal rule written in a GENERAL way, no present simple example in the template | The template is shared by all skills; an example of one tense pushes every skill toward it |
| When my answer is natural but different from the expected one, the verdict is correct + "also right" note | The prompt cannot remove every ambiguous sentence: the grader is the second protection |
| Reasoning effort per TASK, values in `.env`, not in code | `reasoning_effort` is a Gemini option: switching provider must stay a settings change |
| Effort comparison in Part 4: blind, 40 + 40 exercises, same skills and topics | 20 vs 20 is too small with a random AI; blind so I do not judge by the group |
| Exercise stock: Practice never waits for a live request; refill when below 3 | Today 8 of 12 requests were 503. I want to keep practising when Gemini is busy |

**Problems and how I solved them**

- The first batch prompt wrote sentences where another tense was natural ("this week", "today", "tomorrow"). Fixed with the signal rule, the vocabulary rule and the self-check (5/5 → 2/5 weak), then the `signal` field.
- The new `exercise_type` check (a Practice exercise needs a type) broke 2 old tests that created exercises without one: updated them.
- `GapExerciseDraft` is shared with the Step 1 prompt: a required `signal` would break it, so the Step 1 prompt asks for it too. `scripts/part4_experiments.py` now says it is a record that will not run again.
- Gemini was busy: the first demo needed 3 requests (2 × 503, then OK), and the last 2 demo runs failed with 3 × 503 each. The retry code behaved exactly as planned (2 s, 4 s, stop).

**Open questions / next**

- First thing next session: run the batch demo (signal + default effort) and count the weak sentences.
- Then Part 2: answer checking, `GapGrade` with `detected_mistake`, saving attempts, and the exercise stock.

---

## 2026-11-16 - Step 1 done: the first real exercise in the database (Part 5)

**What I did**

- The AI now returns a `GapExerciseDraft` (sentence, expected answer, accepted answers, hint). The code adds
  `skill_id` and `level`, so the AI cannot choose the wrong skill.
- A new prompt with ONE skill: name, typical mistake (marked as "only an illustration, do not reuse its words"),
  `tag_when` (the line is left out when the skill has none), a sub-topic, and the last 5 sentences to avoid.
- New file `tutor/exercises.py`: `TOPICS` (4 topics × 6 sub-topics), `choose_random_skill(level)` (at or below
  the level), and `create_gap_exercise(skill_id, level, topic)` (prompt → `llm.ask()` → save).
- `exercises` table: new columns `sub_topic`, `accepted_answers` (JSON list) and `hint`. Free today, because
  `data/tutor.db` did not exist yet: no migration.
- No repeated sentences: a sentence identical (after normalizing) to one already saved for the skill is an
  invalid answer, so `llm.ask()` retries once.
- `scripts/step1_demo.py`, with an optional skill id. `scripts/part4_experiments.py` keeps a frozen copy of the old prompt.
- Tests: 146 in total (32 new), ruff clean. Learning note 008 (schema factory with a `ClassVar`).

**The real demo (2 requests, no retry)**

| Run | Topic / sub-topic | Sentence | Answer |
| --- | --- | --- | --- |
| 1 | daily life / a visit to the dentist | My dentist always ___ (check) my teeth during a visit. | checks |
| 2 | travel / visiting a museum | The guide ___ (start) the museum tour at ten o'clock. | starts |

- The second prompt listed the first sentence under "sentences already used" (checked in the log); the AI wrote
  a clearly different one.
- Prompt tokens: **about 300** (298 and 308), against 1069 with the old prompt and its list of 49 skills (−72%).
  1.4 s and 1.1 s. Prompt version `gap_exercise@c2deeb`.
- Compared with the experiments ("My brother usually ___ (wake) up" every time): the code choosing skill and
  sub-topic gives real variety.

**Decisions and why**

| Decision | Why |
| --- | --- |
| The AI returns a draft; the code adds skill and level | The code chooses them: the AI cannot get them wrong. A hand review of 20 exercises in Step 2 checks the AI wrote about the right skill |
| The duplicate check lives in the schema, not in a new retry loop | It reuses the "bad answer → retry once" rule of `llm.ask()`: logged, counted, inside the 4-request maximum |
| The prompt shows the last 5 sentences; the check uses ALL saved sentences of the skill | A short prompt, but no repeated sentence ever |
| The `tag_when` line template is in the version hash | Changing its words must give a new prompt version too |
| `accepted_answers`, `hint` and `sub_topic` columns now | Step 2 (code check, hint button) and Step 7 (Review) need them; adding them later needs a migration |
| New file `tutor/exercises.py` | Logic between prompt and database must be tested and reused by the Practice page (pages stay thin) |
| The experiment script keeps the old prompt | So it stays a true record of what E1–E4 sent |

**Problems and how I solved them**

- 9 tests failed with `NameError: name 'used_sentences' is not defined`. Inside a class body,
  `used_sentences = tuple(used_sentences)` cannot read the function argument with the same name: Python looks in
  the class and the module, not in the function around it. Fixed by renaming the argument
  (`sentences_already_saved`). See learning note 008.
- Two lines were 121 characters (limit 120): split.

**Open questions / notes for Step 2**

- The two hints were almost the same ("Think about the correct ... form for he, she, or it"): generic, and they
  name the grammar rule, which makes the exercise easier. In the Step 2 prompt, ask for hints about the meaning
  of the sentence.
- `accepted_answers` was empty both times (correct for "checks" and "starts"). Watch if the AI fills it when
  other answers really exist.

**Next**

- Step 2 - Practice. First a detailed plan, as for Step 1.

---

## 2026-11-16 - Step 1: skill list, database, first prompt, AI experiments

**What I did**

- Planned Step 1 in detail (many of my own rules added to PLAN.md: `source`, `submission_id`, naturalness,
  `mistake_text` / `correction`, prompt versions from the template, UTC dates, foreign keys, safe `init_db()`).
- Part 1: `tutor/skills.py`, 53 skills (50 to learn + 3 general), with my own real mistakes as examples and
  `tag_when` for skills that overlap. 22 tests.
- Part 2: `tutor/db.py` (6 tables, `connect()`, `init_db()`, `save_exercise()`, `save_attempt()`, `get_attempts()`)
  and the Pydantic models `Exercise` and `Attempt`. 25 tests, all on a temporary database.
- Part 3: `GapExercise`, the first prompt, automatic `prompt_version` (name + hash of the template). Tests: 74 in total.
- Part 4, experiments with the real API (`scripts/part4_experiments.py`), before writing `llm.py`.
- Part 4: `tutor/llm.py`, the AI engine. `ask()` sends a prompt and returns a validated Pydantic object, with
  retries, a log (`logs/ai_log.jsonl`) and a daily counter. 40 tests with a fake AI and a fake clock
  (0 real requests). Tests: 114 in total, ruff clean. Part 4 ticked in PROGRESS.md.
- Two commits (`233adc4` Part 3 + experiments, `05a962d` Part 4), pushed to GitHub.
- Learning notes 004 (pytest), 005 (SQLite), 006 (fakes and monkeypatch), 007 (retries with a time budget).

**AI experiments (Part 4) — what we learned**

| # | Question | Result |
| --- | --- | --- |
| E1 | Does `parse()` with a Pydantic model work on Gemini? | Yes. Valid `GapExercise`, our validators ran. 1.8 s, 1069 prompt tokens (mostly the skill list) + 84 answer tokens |
| E2 | Can `skill_id` be an enum of the 49 fill-the-gap ids? | Yes, Gemini accepts the schema (idea A) |
| E3 | Which model name does Gemini return? | Exactly `gemini-3.5-flash-lite`, the same as `.env`, no `models/` prefix |
| E4 | `reasoning_effort="low"` vs default (3 + 3 requests) | low 0.9 s vs default 1.6 s on average, same answer size. Quality to compare on the gold file in Step 2 |
| E5 | Real 429 body (6 requests at once on `gemini-3.8-flash`) | **No 429.** 4 × 503 UNAVAILABLE "high demand" (3.6–42 s) and 2 timeouts at 60 s. Not repeated today |
| E6 | Wrong key | **400** BadRequest, INVALID_ARGUMENT, "Please pass a valid API key" (not 401/403) |
| E7 | Wrong model name | 404 NotFound, NOT_FOUND |

Other findings:

- Gemini error bodies are a **list with one item**, `[{'error': {...}}]`, not a plain dict. Code must read both.
- The 503 body had no wait time and no `retry-after` header. The real 429 format is still unknown: the log will
  keep the full body the first time one happens.
- The `openai` client retries 429 by itself 2 times by default: we use `max_retries=0`, so every request is ours,
  logged and counted.
- E1, E2 and E4 all wrote almost the same sentence ("My brother usually ___ (wake) up..."), because the AI chose
  the skill itself and always picked the easiest one.
- Total cost: 8 Lite requests (of 500) and 6 Flash requests (of 20).
- **Failed requests DO use quota.** AI Studio after E5: Gemini 3.8 Flash showed **6 / 5 RPM in red**, so all 6
  failed requests (4 × 503 and 2 timeouts) were counted. Lite showed 6 / 15 RPM. This confirms the rules
  "count every request sent, including failed ones and retries" and "few retries, with a time budget".
- The experiment script does not use `llm.py`, so its requests are not in the log: the counter cannot see them.
  That is why `AI_DAILY_LIMIT_MARGIN=20`: the app stops 20 requests before the real limit.

**Decisions and why**

| Decision | Why |
| --- | --- |
| The CODE chooses the skill, the AI only writes the sentence | The AI always chose the same easy skill. The tutor must decide what I practise (selector, or weak skills) |
| Variety: a random sub-topic and the last sentences to avoid go in the prompt | Avoid the same sentence again and again |
| 503 is handled like a per-minute 429: at most 2 retries (2 s, then 4 s), total budget about 20 s | Google says 503 is temporary. A retry budget stops the app from waiting too long |
| A wait time in the error body (`retryDelay`) is used if present; more than ~10 s → do not wait, tell me how long | We have not seen a real 429 yet, so we do not guess its format |
| Timeouts are not retried; timeout 30 s, setting `AI_TIMEOUT_SECONDS` | Lite answers in 1–2 s. A 30 s wait is already too long |
| A wrong key or model → `AIConfigurationError` "check your key and model in .env", by status AND message | A wrong key is a 400, and other 400s exist (for example a schema Gemini rejects) |
| `reasoning_effort` becomes a setting `AI_REASONING_EFFORT` | 2× faster in E4; quality to check on the gold file |
| `skill_id` enum: yes, Gemini accepts it | Will be used where the AI tags skills (grader, Writing). Code validation stays |
| `GapExercise`: the hint must not contain the answer (whole words), clean accepted answers | Found while reviewing Part 3 |
| No "In my own words" section in learning notes | My choice |
| Tests use a fake model name (`fake-test-model`) | Tests must not depend on `.env` |
| Any 400 that is not about the key → `AIRequestRejectedError` "the app sent a request Google refused, see the log", never retried | Retrying later would never fix a refused request |
| "Wait N seconds" errors carry the number in `retry_after_seconds` | A page can show it or count down |
| `AI_DAILY_LIMIT_MARGIN=20`: the app stops at 480 of 500 | The counter does not see requests made outside `llm.py`, and failed requests count |
| Every exception name ends in `Error` (`AIUnavailableError`, `AIDailyLimitError`...) | Ruff rule N818, and the same style as `AIConfigurationError`. I chose renaming over turning the rule off |
| The AI returns a `GapExerciseDraft`; the code adds `skill_id` and `level` (Part 5) | The code chooses the skill, so the AI cannot get it wrong. A hand review of 20 exercises (Step 2) checks they really test the skill |
| `.env` needs only `AI_DAILY_LIMIT`; the other new settings have defaults | `.env.example` lists them all, so I can see every setting in one place |

**Problems and how I solved them**

- I changed `skills.py` without noticing (one extra space). `git status` showed it, `git diff` showed what it was, `git restore` undid it.
- The missing final newline (ruff W292) comes from Claude's file-writing tool, not from my editor.
- My first counts were wrong twice (51 → 49 fill-the-gap skills; 47 → 46 tests). Tests and checking by hand caught them.
- The real `openai.APITimeoutError` cannot be created in a test without a network request. The test creates it
  without its `__init__`; `llm.py` only checks its type, so that is enough (learning note 006).
- Ruff found 7 problems after `llm.py`: 1 missing newline (auto-fixed), 1 line too long, 5 × N818 (fixed by the rename).
- `git` shows "LF will be replaced by CRLF" warnings on Windows: harmless, Git changes the invisible line endings.

**Open questions**

- The real 429 body format. The daily-quota check looks for words from Google's docs (`PerDay`, `daily`);
  fix it when the log keeps a real 429 body.

**Next**

- Part 5: `GapExerciseDraft` (the AI does not return `skill_id` and `level`), the prompt with ONE skill, a
  sub-topic and sentences to avoid, then `scripts/step1_demo.py` (one random A2 skill → `ask()` → save in the
  database). That closes Step 1.

---

## 2026-11-16 - Step 0: setup done, app on GitHub

**What I did**

- Renamed the git branch from `master` to `main`.
- Created the project files: `.gitignore`, README, MIT license, `requirements.txt`, `.env.example`, `pyproject.toml` (ruff settings).
- Created the empty app: `app.py` with `st.navigation`, 9 pages in 3 menu groups (Today, Study, Track), and empty `tutor/` modules.
- Created the virtual environment (`.venv`) and installed the libraries.
- Created the Gemini key and tested it with `scripts/check_ai.py`.
- Checked the code with ruff, then pushed everything to https://github.com/catarinafelixcr/english-tutor
- Wrote learning note 002 about virtual environments.

**Decisions and why**

| Decision | Why |
| --- | --- |
| My code style rules are in CLAUDE.md | Blank lines between blocks, compact lists, long names, positional arguments, no type hints, early returns. Claude follows them in every session |
| Two exceptions to the style | Keyword arguments when a library forces them (`OpenAI(base_url=...)`), and type annotations in Pydantic models (they define the schema) |
| ruff added now, not in Step 10 | Clean code from the first line. Only `ruff check`, not `ruff format`, because the formatter puts one item per line in long lists |
| ruff rule RET504 turned off | It wants `return {...}` directly. I prefer a descriptive name before the return: clearer and easier to debug |
| Repo created empty on GitHub | README, license and .gitignore were already local. Creating them on GitHub too would cause a conflict on push |
| No Claude co-author line in commits | My choice: the commits are mine |
| Claude explains every terminal command and waits for my "yes" | I want to understand what runs on my computer. Git commands only need the question |
| Model `gemini-3.5-flash-lite` | `gemini-3.8-flash` has only 20 requests/day; Lite has 500/day and 15/minute, and it is faster. Good enough to find and explain a mistake. A fixed name, not "latest", so the grader does not change by itself |
| Daily AI usage counter (added to PLAN.md) | Count requests in Step 1, show "AI today: 37 / 500" in Step 4, so I know when I am near the limit |
| No backup AI for now | Gemini is enough to start. Groq or Ollama can be added later in `.env` |

**Problems and how I solved them**

- `Error code: 404` with `gemini-2.5-flash`: the model name no longer exists. Fix: `check_ai.py` now lists the Flash models my key can use when this happens.
- I renamed `.env.example` to `.env` instead of copying it. Fix: `git restore .env.example`. The file now says "COPY (do not rename)".
- ruff W292 "no newline at end of file" in all Python files. Fix: `ruff check --fix .`. Later found: the cause is Claude Code's file-writing tool (it happens on every file Claude creates), not my editor. So `ruff check --fix .` after Claude writes a file.
- The AI's first answer was correct but felt too abrupt ("No, it is not correct..."). To solve in Step 2: tone instructions in the prompts (kind, explain the Portuguese reason).

**Next**

- Step 1: the AI engine (`tutor/llm.py`), the skill list and the database.

---

## 2026-11-13 — The idea and the plan

**What I did**

- Had the idea: a free web app to learn English with an AI that says if my
  answer is right or wrong, and why.
- Tested two prototypes in Claude: a simple fill-the-gap game, then an
  "AI English Tutor" page with fill the gap, check my sentence and listening.
- Wrote the full build plan (docs/PLAN.md): 9 sections and Steps 0 to 10.
- Created the project folder with CLAUDE.md and this docs folder.

**Decisions and why**

| Decision | Why |
| --- | --- |
| Python + Streamlit | I am a data scientist: I know Python, and charts are easy |
| Gemini API free tier as the main AI | Free and good quality. Limits are shown in Google AI Studio |
| AI provider set in `.env` | Free limits change. I can switch to Groq or Ollama without changing code |
| SQLite database | One file, no server, works well with pandas |
| Save every answer from Step 1 | The tutor ("you must study X") and the dashboard both need this data |
| Dashboard late (Step 8) | Charts need weeks of answers to show something real |
| One fixed list of skills | Without it the app cannot count my mistakes by topic |
| Test the AI grader with 50 hand-graded answers | An AI that grades wrongly would teach me wrong rules |
| Build with Claude Code | I want to learn it. I have Claude Pro this month |
| Local folder first, GitHub after | I can prepare the files first and push when Step 0 works |

**Problems**

- None yet.

**Next**

- Step 0: install the tools, create the empty app, first commit, push to GitHub.
