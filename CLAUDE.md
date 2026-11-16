# English Tutor

A personal web app to learn English with an AI tutor. It creates exercises, checks answers, explains mistakes, tracks weak grammar skills and tells the user what to study next.

## About the developer

- Data scientist: strong in Python, pandas and SQL; new to web apps.
- First project with Claude Code. Explain what you do and why, in simple English (the developer is also learning English).
- Wants to understand the code, not only receive it.

## The plan

- The full build plan is in @docs/PLAN.md (Steps 0 to 10).
- Progress is tracked in @docs/PROGRESS.md.
- Work on ONE step at a time. Never start the next step without being asked.
- Each step has a "Done when" line. A step is finished only when it is true.
- When a task is finished, tick it in docs/PROGRESS.md.
- I love excelence and creative.

## Documentation I keep (very important to me)

I want to remember, months from now, what I did and why. Keep these updated:

- `docs/JOURNAL.md` — the diary of the project. At the end of every work session, add a dated entry: what we did, why we did it this way, decisions,
  problems and how we solved them. Newest entry at the top.
- `docs/learning/` — one Markdown file per thing I learned (a tool, a concept, a command, a pattern). When a task uses something new to me, ask:
  "Do you want a learning note about X?" If yes, copy
  `docs/learning/_template.md` to a new numbered file
  (example: `004-pydantic-schemas.md`), fill it in simple English with a real
  example from THIS project, and add one line to `docs/learning/README.md`.
  Leave the section "In my own words" empty: I write that part myself.
- `docs/PROGRESS.md` — tick tasks when they are finished.

Never finish a session without updating JOURNAL.md.

## Tech stack (all free)

- Python 3.11+, Streamlit (UI), SQLite (data), pandas, Plotly (charts)
- Pydantic for every AI answer (structured JSON output)
- AI: Gemini API free tier through the `openai` Python client with a custom `base_url`. Provider, model and key come from `.env`, so we can switch to Groq or Ollama by changing settings only.
- pytest for tests, ruff for style

## Commands

- Run the app: `streamlit run app.py`
- Run tests: `pytest`
- Check style: `ruff check .`
- Test the AI grader: `python eval/run_eval.py`

## Project structure

```
app.py            menu and page routing
pages/            one file per section (home, learn, practice, writing, ...)
tutor/llm.py      the ONLY file that talks to the AI
tutor/prompts.py  all prompt texts
tutor/schemas.py  Pydantic models for AI answers
tutor/db.py       SQLite tables and queries
tutor/skills.py   the fixed skill list
tutor/mastery.py  weak/strong logic and recommendations
tutor/srs.py      spaced repetition
tutor/audio.py    listen and speak helpers
data/             tutor.db (never in git)
tests/            pytest tests
eval/             gold answers to test the AI grader
docs/             plan, progress, journal and learning notes
```

## Rules

1. Secrets: API keys live only in `.env`. Never write a key in code, in docs or in a commit. `.env` and `data/` must stay in `.gitignore`.
2. Skills: the AI must choose skill ids from `tutor/skills.py`. Validate every
   id in code. Never let the AI invent a new skill.
3. Every answer is saved: all sections call `save_attempt()` with a skill id.
4. AI calls only through `tutor/llm.py`. Pages never call the API directly.
5. Check in code first (exact match), and call the AI only when needed. The free tier has a daily limit: batch 5 exercises per call and cache lessons.
6. Logic with no screen (db, mastery, srs, answer comparison) needs pytest tests. Run `pytest` before saying a task is done.
7. Keep pages thin: screens in `pages/`, logic in `tutor/`.
8. Small commits, one task each, with a clear message. Ask before `git push`.
   No "Co-Authored-By: Claude" line (or any Claude attribution) in commit messages or pull requests.
9. Do not add a new library without asking first.
10. Skill ids are never renamed or deleted (old attempts point to them). To retire a skill, set `"active": False` in `tutor/skills.py`. `init_db()` must be safe to run many times: no duplicates, nothing deleted.

## Code style (my preferences)

- Blank lines between logical blocks, functions and classes. Let the code breathe.
- Compact definitions: lists, dicts and function arguments stay on one line when they fit. No line break after every comma.
- Clear, step-by-step logic. No compressed one-liners or complex list comprehensions.
- Long, descriptive names. No abbreviations, no single-letter variables.
- Positional arguments when calling my own functions: `create_user(user_name, user_age)`, not `create_user(name=user_name, age=user_age)`.
  Exception: use keyword names only when a library forces them (for example `client.chat.completions.create(model=..., messages=...)`).
- No type hints in function signatures or on variables.
  Exception: Pydantic models need type annotations on their fields, because that is how Pydantic knows the schema.
- Early returns: guard clauses at the top of a function, so the main logic stays flat.
- ruff checks the code (`ruff check .`). We do not use `ruff format`, because it puts one item per line in long lists.

## How to work with me

- Before writing code for a step, show a short plan and wait for my OK.
- After writing code, explain it in a few lines and tell me how to test it.
- Before running any terminal command (PowerShell, git, pip...), explain in plain words what each part does, ask me "Can I run it?", and STOP. Run it only after I answer yes in the chat.
  Exception: git commands need no explanation, only the question.
- If something in the plan is unclear or looks wrong, ask me. Do not guess.