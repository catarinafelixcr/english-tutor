# Project journal

The diary of this project: what I did, why, and what I decided.
Newest entry at the top. One entry per work session.

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
- Learning notes 004 (pytest) and 005 (SQLite).

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

**Problems and how I solved them**

- I changed `skills.py` without noticing (one extra space). `git status` showed it, `git diff` showed what it was, `git restore` undid it.
- The missing final newline (ruff W292) comes from Claude's file-writing tool, not from my editor.
- My first counts were wrong twice (51 → 49 fill-the-gap skills; 47 → 46 tests). Tests and checking by hand caught them.

**Open questions**

- The real 429 body format.

**Next**

- Part 4: write `tutor/llm.py` with the fake-AI tests. Then Part 5: the demo script.

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
