# Project journal

The diary of this project: what I did, why, and what I decided.
Newest entry at the top. One entry per work session.

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
