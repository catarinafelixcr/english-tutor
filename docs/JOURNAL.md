# Project journal

The diary of this project: what I did, why, and what I decided.
Newest entry at the top. One entry per work session.

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
