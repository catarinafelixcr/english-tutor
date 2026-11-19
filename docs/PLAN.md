# AI English Tutor - Build Plan

Nov 13, 2026 · @Catarina Cruz

## The app in one page

The app is one website with a menu on the left, and each menu item is one way to study. Every section saves your answers in the same database, so the tutor knows your weak points in all of them.

| Section | What you do | What the AI does | Built in |
| --- | --- | --- | --- |
| Home | See today's plan: reviews due, your weak topic, your daily goal | Chooses today's exercises for you | Step 4 |
| Learn | Read a short lesson on one grammar topic, then answer 5 sentences about it | Writes the lesson and starts with your weakest topics | Step 4 |
| Practice | Fill the gap, fix the error, put words in order | Creates the sentences, checks your answer, explains the rule | Step 2 |
| Writing | Write a sentence, an email or a chat message | Lists each mistake with the fix and the reason | Step 3 |
| Listening | Hear a sentence and type what you heard | Compares word by word and shows what you missed | Step 5 |
| Translate | Read a sentence in your language and write it in English | Judges the meaning, not the exact words | Step 6 |
| Review | Repeat sentences you got wrong, on a schedule | Chooses what is due today | Step 7 |
| Progress | See charts of your accuracy by topic and over time | Writes a weekly report | Step 8 |
| Speaking | Read a sentence aloud or role-play a conversation | Turns your voice into text and corrects it | Step 9 |

I assumed your first language is Portuguese. If it is another language, only the Translate section and the explanation language change.

## What makes it good for really learning

The app teaches well only if it follows these seven rules, so every step below is built around them.

1. **One fixed list of skills.** About 40 grammar and vocabulary skills, each with a level (A2 to C1). Examples: verb to be, present perfect, articles, prepositions of time, phrasal verbs. The AI must choose a tag from this list and never invent new ones. Without this rule the app cannot count your mistakes by topic.
2. **Every answer is saved.** Each attempt stores the skill, the section, your answer, the verdict, the type of error and the date. This table is the heart of the app.
3. **Mastery score per skill.** Accuracy over your last 10 attempts on that skill. Below 60% with at least 5 attempts means weak. Above 85% means strong.
4. **"You must study X."** When a skill is weak, Home shows it first, Learn opens a lesson about it, and Practice gives you more sentences on it.
5. **You type first.** Typing the answer from memory teaches more than choosing from options, so typing is the main way to answer. Options (multiple choice) and word tiles appear only as help steps, after I tried, and an answer found with them counts less for mastery (changed 2026-11-19, help ladder in Step 2 Part 3c).
6. **Mistakes come back.** A wrong sentence returns after 1, 3, 7, 14 and 30 days. A second mistake sends it back to day 1.
7. **The AI grader is tested.** An AI can grade wrongly. You keep a file of 50 answers that you graded by hand and measure how often the AI agrees. Aim for 90% or more before you trust it.

A good daily session is 15 minutes: reviews due first, then 5 sentences on your weakest skill, then something new.

## Free tech stack

Everything below costs nothing, and the main version runs on your own computer with no limits. I chose Python and Streamlit because you are a data scientist; the plan also works with another framework.

| Part | Choice | Why | Limit to know |
| --- | --- | --- | --- |
| App and screens | Streamlit (Python) | You write only Python, and charts are easy | None when it runs on your computer |
| AI model, offline backup | Ollama on your computer | Free forever, private, works offline | Needs about 8 GB of free memory for a good model. Pick a current Qwen or Gemma model of 8 to 12 billion parameters from the Ollama library |
| AI model, backup | [Groq](https://console.groq.com/docs/rate-limits) free plan | Fast, and works if your computer is slow | The docs table shows about 30 requests a minute and 1,000 a day for the main chat models. Your account's limits page has the exact numbers |
| AI model, main | [Gemini API](https://ai.google.dev/gemini-api/docs/rate-limits) free tier | Good quality | Google does not publish the free numbers on its docs page. You see them in AI Studio |
| Listening (text to voice) | The browser's built-in voice (Web Speech API) | No install, no key | Voice quality depends on the browser. Piper is a free offline upgrade |
| Speaking (voice to text) | faster-whisper on your computer | Free and offline | Slow on old computers. Groq also offers Whisper: the docs table shows 2,000 requests a day |
| Database | SQLite | One file, no server, perfect with pandas | One user only, which is what you need |
| Charts | Plotly | Interactive charts inside Streamlit | None |
| Code and tests | GitHub and GitHub Actions | Free for public repos | None for this project |
| Online version (optional) | [Streamlit Community Cloud](https://docs.streamlit.io/streamlit-community-cloud/get-started/manage-your-app) | Deploys from your GitHub repo | The app sleeps after 12 hours without visits. Ollama cannot run there, so the online version must use Groq or Gemini. Do not count on the SQLite file surviving a restart |

Free limits change often, so write the AI part so that you can switch provider by changing one setting. Step 1 does this.

## Build order

The dashboard screen comes late (Step 8), but saving the data starts in Step 1. Charts need weeks of answers to show anything, and the "you must study X" tutor uses the same data much earlier.

1. **Step 0 – Setup.** Repo, tools, empty app that opens in the browser.
2. **Step 1 – Foundation.** The AI engine, the database and the skill list.
3. **Step 2 – Practice.** Fill the gap, with every answer saved. This is the first version you can study with.
4. **Step 3 – Writing.** Check my sentence.
5. **Step 4 – Tutor brain.** Weak topics, "you must study X", lessons, Home page.
6. **Step 5 – Listening.** Listen button everywhere, plus dictation.
7. **Step 6 – Translate.**
8. **Step 7 – Review.** Spaced repetition of your mistakes.
9. **Step 8 – Progress.** Dashboard and weekly report.
10. **Step 9 – Speaking.** Voice input and conversation role-play.
11. **Step 10 – Polish.** Tests, README, optional online version.

Use the app every day from Step 2. Each step ends with a "Done when" line: do not start the next step before it is true.

## Step 0 – Setup

You finish this step with an empty app running on your computer and the code on GitHub.

- [ ] Create a public GitHub repo, for example `english-tutor`, with a README, an MIT license and a Python `.gitignore`.
- [ ] Install Python 3.11 or newer and create a virtual environment (`python -m venv .venv`).
- [ ] Create `requirements.txt` with: `streamlit`, `openai`, `pydantic`, `pandas`, `plotly`, `python-dotenv`, `pytest`.
- [ ] Create a free Gemini API key in Google AI Studio, write down your daily limit for the Flash model, and test the key with one English question.
- [ ] Optional backup for days you hit the Gemini limit: install Ollama with one model, or create a free Groq key.
- [ ] Create `.env` for keys and settings, add `.env` and `data/` to `.gitignore`, and commit a `.env.example` without real keys.
- [ ] Create the folders below.
- [ ] Write `app.py` with a title and the left menu (`st.navigation`), one empty page per section.
- [ ] Run `streamlit run app.py` and make the first commit.

```text
english-tutor/
  app.py                 # menu and page routing
  pages/                 # one file per section: home, learn, practice, ...
  tutor/
    llm.py               # talks to the AI model
    prompts.py           # all prompt texts in one place
    schemas.py           # Pydantic models for AI answers
    db.py                # SQLite tables and queries
    skills.py            # the fixed skill list
    mastery.py           # weak/strong logic, recommendations
    srs.py               # spaced repetition
    audio.py             # listen and speak helpers
  data/                  # tutor.db lives here (not in git)
  tests/
  eval/                  # gold answers to test the AI grader
```

**Done when:** the app opens in your browser with all menu items, and the repo is on GitHub.

## Step 1 – Foundation: AI engine, database, skill list

This step has no screen to show, but every later step depends on it.

**AI engine (`tutor/llm.py`)**

- [ ] Write one function `ask(prompt, schema)` that sends a prompt and returns a validated Pydantic object.
- [ ] Use the `openai` Python client with a configurable `base_url`, so the same code talks to Gemini, Groq or Ollama.
- [ ] Read the provider, model name and key from `.env`.
- [ ] Ask for structured output with the Pydantic schema (`parse()` with `response_format`, documented by Gemini as beta). Always validate with Pydantic too. On a validation error, retry once. If Gemini rejects the schema in a real test, switch to JSON mode plus validation.
- [ ] Test if the schema can limit `skill_id` to an enum of the active skill ids. If Gemini accepts it, use it. Keep the code validation in all cases.
- [ ] On a rate-limit error (HTTP 429): if the local counter already reached `AI_DAILY_LIMIT`, or the error says it is the daily quota, stop at once with a clear message. Otherwise retry at most 2 times: after 2 s, then 4 s. If the error body gives a wait time (`retryDelay`), use it. If the wait is longer than about 10 seconds, do not wait: raise an error that says how many seconds to wait.
- [ ] A 503 (UNAVAILABLE, "high demand") is handled like a per-minute 429. Retries have a total time budget: stop when about 20 seconds have passed since the first request (counting the next wait), and raise `AIUnavailableError`. Timeouts are not retried.
- [ ] The code that reads error bodies accepts both formats (a list with one item, and a plain dict), with a test for each. An error it cannot read becomes `AIUnavailableError`, with the full body in the log. It must never crash.
- [ ] Settings in `.env`: `AI_TIMEOUT_SECONDS=30`, `AI_REASONING_EFFORT=low` (empty = Gemini's default).
- [ ] Create the client with `max_retries=0` (the `openai` client retries 429 twice by itself by default, which our log and counter would not see) and the timeout from `AI_TIMEOUT_SECONDS`. A timeout becomes `AIUnavailableError`.
- [ ] A wrong key or a wrong model name raises `AIConfigurationError` with the message "check your key and model in .env" (Google can answer a bad key with 400, not only 401/403).
- [ ] Any other 400 raises `AIRequestRejectedError`: "the app sent a request Google refused, see the log". It is never retried, because retrying later would never fix it.
- [ ] When the error says "wait N seconds", the exception also carries the number as a value (`retry_after_seconds`), so a page can use it.
- [ ] Log the token counts (`usage`) when Gemini returns them.
- [ ] Experiments before writing `llm.py` (`scripts/part4_experiments.py`): E1 `parse()` with `GapExercise`; E2 `skill_id` as an enum; E3 the model name returned; E4 `reasoning_effort="low"` vs default, 3 requests each; E5 the 429 experiment; E6 a wrong key; E7 a wrong model name. Write the results in docs/JOURNAL.md.
- [ ] 429 experiment: send 6 tiny requests in one minute to `gemini-3.8-flash` (5 RPM, its own quota, not Lite's) to see the real error body. Write what we learn in docs/JOURNAL.md.
- [ ] Save every request to `logs/ai_log.jsonl` (one JSON per line): UTC time, model asked (from `.env`), model returned (from Gemini's answer; if different, ignoring a `models/` prefix, mark it as a warning), prompt version, prompt, answer, full error body. Never the API key, and a test proves it. `logs/` is in `.gitignore`.
- [ ] The `model` column in `exercises` and `attempts` saves the model returned, because that model really did the work.
- [ ] Write `count_requests_today(model)`: requests made today for one model, from the log. The day starts at midnight `America/Los_Angeles` (Gemini resets RPD then), using `zoneinfo` + `tzdata`. It is an estimate: it does not see requests made outside this app. It counts every request sent, including failed ones and retries (one log line = one request sent).
- [ ] Read the daily limit from `.env`: `AI_DAILY_LIMIT=500`, the real number from the AI Studio rate limit page for `gemini-3.5-flash-lite`. The app stops a little before it: `AI_DAILY_LIMIT_MARGIN=20`, because the counter does not see requests made outside `llm.py` (scripts, experiments, AI Studio). Failed requests use quota too (seen in AI Studio after E5).

**Skill list (`tutor/skills.py`)**

- [ ] Write the fixed list of about 40 skills. Each one has an id, a name, a level and a category: `to_be | Verb to be | A2 | verbs`.
- [ ] Cover these categories: verb tenses, modals, articles, prepositions, pronouns, comparatives, conditionals, passive voice, word order, phrasal verbs, collocations, spelling.
- [ ] Add one short example of a typical mistake for each skill. The AI uses it to choose the right tag.
- [ ] Each skill has an `active` flag. Skill ids are never renamed or deleted; a retired skill gets `active: False`.
- [ ] Add 4 extra skills: `writing_general`, `listening`, `speaking` (category `general`) and `spelling` (a normal skill).

**Database (`tutor/db.py`, SQLite)**

- [ ] Table `skills`: id, name, level, category, active.
- [ ] Table `exercises`: id, section, skill\_id, level, topic, sub\_topic, prompt text, expected answer (can be empty, for free Writing texts), accepted answers (a JSON list, `[]` when none), hint, model, prompt version, created date. Accepted answers and hint are needed by the code check, the hint button (Step 2) and Review (Step 7).
- [ ] Table `attempts`: id, submission\_id, exercise\_id (required), section, skill\_id, source, your answer, verdict (correct, partial, wrong), error type (grammar, vocabulary, spelling, word order, naturalness), explanation, mistake text, correction, hint used, seconds taken, graded by, model, prompt version, date.
- [ ] `source`: "targeted" = the exercise was made to test this skill; "detected" = a mistake the exercise did not target (for example in free writing). Only targeted attempts count for mastery (Step 4).
- [ ] `submission_id`: all rows from one answer share it (a `uuid`). We count answers by submission, not by row.
- [ ] `mistake_text` and `correction` (both optional): the exact wrong part I wrote, and the right form (or the natural version). For fill the gap: my answer and the expected answer. For Writing: the wrong fragment and its fix. No third "corrected answer" column.
- [ ] `graded_by`: "code" or "ai". When the code grades, model and prompt version stay empty.
- [ ] `prompt_version`: automatic, the prompt name + a short hash of the prompt TEMPLATE (before level, topic and skill list are inserted). A test: the same template with different values gives the same version.
- [ ] An attempt is a Pydantic model `Attempt` with `Literal` values for section, verdict, error type, source and graded by. `save_attempt(attempt)` receives the model.
- [ ] Table `reviews`: exercise\_id, box number, due date.
- [ ] Table `lessons`: skill\_id, lesson text, date.
- [ ] Table `lesson_events`: skill\_id, opened\_at (UTC). One row each time I open a lesson in Learn (Step 4). The Step 8 chart "before and after a lesson" needs it.
- [ ] One `connect()` function opens every connection with `PRAGMA foreign_keys = ON` (SQLite turns it off by default).
- [ ] All dates in UTC, ISO format (`2026-11-16T21:04:05+00:00`). Steps 4 and 7 convert to `Europe/Lisbon` to count days.
- [ ] `init_db()` is safe to run many times: `CREATE TABLE IF NOT EXISTS`, insert-or-update skills, never deletes. It stops with an error if a skill id in the database is missing from `skills.py`. It sets `PRAGMA user_version = 1`; write migrations only when a later step needs a new column.
- [ ] Write the helper functions `save_exercise()`, `save_attempt()`, `get_attempts()` (returns a pandas DataFrame) and `init_db()`.
- [ ] Write pytest tests with a temporary database: save one attempt and read it back; an unknown exercise\_id is refused; an unknown skill\_id is refused; `init_db()` twice gives no duplicates; a skill missing from `skills.py` raises an error.

- [ ] `GapExercise` checks: one `___`, expected answer not empty, a fill-the-gap skill id, hint not empty, the hint does not contain the expected answer or an accepted answer (whole words), accepted answers with no empty items, no duplicates and not the expected answer.
- [ ] The demo script chooses ONE random A2 fill-the-gap skill in code and passes it to the prompt (the AI does not choose the skill). It also accepts a skill id: `python -m scripts.step1_demo present_simple`.
- [ ] The AI returns a `GapExerciseDraft` (sentence, expected answer, accepted answers, hint). The code adds `skill_id` and `level` to build the `GapExercise`.
- [ ] The prompt gets ONE skill: name, typical mistake (only an illustration: do not reuse its sentence or words), `tag_when` (the line is left out when the skill has none), a sub-topic and the last 5 sentences on that skill to avoid.
- [ ] A sentence identical (after normalizing) to one already saved for that skill is an invalid answer: `llm.ask()` retries once.
- [ ] `choose_random_skill(level)` picks a fill-the-gap skill at or below the level.

**Done when:** a small script asks the AI for one fill-the-gap sentence, gets a valid object with a skill id from your list, and saves it in the database.

## Step 2 - Practice (fill the gap)

This is the first version you can really study with, and it copies the page I built for you in this chat.

**Create sentences**

- [x] Write the Pydantic schema `GapExercise`: sentence with `___`, expected answer, other accepted answers, skill id, hint, level. (Done in Step 1, Part 3 and 5.)
- [ ] The CODE chooses the skill, never the AI: my choice in the skill selector, or the tutor's choice (Step 4). The prompt gets ONE skill (with its typical mistake and `tag_when`); the AI only writes the sentences. For variety, the code also sends a random sub-topic and the last few sentences on that skill, to avoid. (Found in the Step 1 experiments: when the AI chose, it always wrote "My brother usually ___ (wake) up".)
- [ ] Write the prompt in `prompts.py`. It receives the level, the topic, the sub-topic, ONE skill and the sentences to avoid, and returns 5 exercises. Fill the gap never uses `capitalization` (the code check ignores capital letters, so it could never be wrong), and the skill selector does not show it for fill the gap. The caller passes only skills at or below the requested level. (The old "check each `exercise.level`" is obsolete since Step 1 Part 5: the AI does not return the level, the code adds it.)
- [ ] Each exercise of a batch gets its own random sub-topic (5 different situations of the topic). The hint is about the MEANING of the sentence, never the grammar rule or the tense (the Step 1 hints named the rule).
- [x] `signal` field (2026-11-16): the AI writes the exact words of the sentence that make the tested form the only natural answer. The code checks it is not empty, appears in the sentence (whole words), and is not the gap or the verb in brackets. No database column: the AI log keeps it.
- [ ] Check each exercise in code: exactly one `___`, a skill id that exists, an answer that is not empty. Drop the bad ones.
- [ ] Validate each exercise of a batch alone: the AI returns a list of raw items (same fields, no checks), then the code validates each item with the strict `GapExerciseDraft`. Drop and log the invalid ones (`logs/dropped_exercises.jsonl`), keep the rest. Two equal sentences in one batch: the second is dropped. 0 valid items = an invalid answer, so `llm.ask()` retries once. (With `list[GapExerciseDraft]`, one bad item would fail the whole batch.)
- [ ] Save the good ones in `exercises` and avoid sentences you already saw.
- [ ] New column `exercise_type` in `exercises`: `gap`, `fix_error` or `word_order` (empty for other sections). It is required for Practice exercises.
- [ ] First migration (database version 1 → 2): adds `exercise_type` and sets the old Practice rows to `gap`. Before ANY migration runs, `init_db()` copies `data/tutor.db` to `data/backups/tutor_before_v2_<UTC time>.db`. No copy for a new database or one already up to date. A test upgrades a real version-1 database.
- [x] Use saved exercises first: exercises that were created but never answered are shown before the app asks the AI for new ones.
- [x] Exercise stock (2026-11-16, to build in Part 2, after a day with 8 × 503 "high demand" out of 12 requests): Practice never depends on a live request to show the next exercise. It keeps a stock of unused exercises in the database (`get_unanswered_exercises()`). When the stock for a skill is below 3, it creates a new batch. If the AI is busy, I keep practising from the stock and see a small notice, not an error. Only an EMPTY stock with a busy AI shows a message (with a "Try again" button). To decide in Part 2: a refill while the stock is not empty should not make me wait for the full retry budget (about 20 s).
- [x] Add selectors for level and topic (daily life, data science and work, travel, meetings).
- [x] Add a skill selector: one skill from the list, grouped by category, or "any skill". Skills of the category `general` are not in it. When I choose a skill, the level selector starts at the skill's level: I can choose a higher level, not a lower one.

**Check answers**

- [x] First check in code: if your answer equals the expected answer or an accepted one (ignore capital letters and spaces), it is correct. No AI call needed.
- [x] Capitalization in code: if my answer equals the expected answer except for capital letters, and the expected answer has a capital where I wrote a small letter (monday vs Monday), save the targeted attempt as correct and add one detected attempt for `capitalization` (same submission\_id), with a short reminder on screen. No AI call.
- [x] Otherwise ask the AI. Schema `GapGrade`: verdict, error type, explanation, corrected sentence, other good answers, memory tip.
- [x] Tell the AI to accept any answer a native speaker would use, and to explain why your answer does not work.
- [x] Grammar right but spelling wrong ("have finised"): save two attempts with the same submission\_id. One targeted, the exercise skill, verdict correct; one detected, skill `spelling`, verdict wrong. A wrong irregular form ("writed", "have went") is a grammar mistake, not spelling. Write this rule clearly in the grader prompt.
- [x] Verdicts in fill the gap (my rule, 2026-11-16):
  - correct = the answer fits. A spelling slip is correct + a detected `spelling` row.
  - partial = I applied half of the tested rule and did not try the other half: "has finish" for present perfect (no past form at all).
  - wrong = I did not apply the tested rule.
  - If the slip belongs to ANOTHER skill of the list, the tested skill is correct and that skill gets a detected wrong row: "writed" in a past simple exercise = `past_simple` correct + `irregular_verbs` wrong; "have went" in a present perfect exercise = `present_perfect` correct (I used have + a past form) + `irregular_verbs` wrong. When the exercise tests `irregular_verbs` itself, "writed" is simply wrong.
- [x] `GapGrade` has one optional `detected_mistake`: skill id (from the list, checked in code), error type, mistake text, correction. Spelling is `skill_id = spelling`.
- [x] On screen: green = correct (a spelling or capitalization slip adds a small reminder); yellow "Almost" = tested skill correct + a detected grammar mistake; yellow "Partly right" = partial; red = wrong.
- [x] Every explanation of a wrong or partial answer has 3 parts, in this order: (a) quote what I wrote, (b) why it is wrong in this sentence, (c) the rule in one line with the correct form. No general grammar text that ignores my answer.
- [x] The 3 parts are 3 fields in `GapGrade`: `mistake_text`, `why_wrong`, `rule`. `mistake_text` is the same value saved in the `mistake_text` column; Writing (Step 3) uses the same field and the same check.
- [x] The 3 fields are required when the verdict is wrong or partial, and empty when it is correct. For a correct answer that differs from the expected one, one short line in the optional field `note` confirms it is also right.
- [ ] Ambiguous sentences (2026-11-16): when my answer is natural in the sentence but different from the expected one (for example another tense that the sentence allows), the verdict is correct, with the "also right" note. The prompt rule ("one clear signal, only the tested form fits") cannot remove every ambiguous sentence, so the grader is the second protection. Write this rule in the grader prompt, and add gold rows for it.
- [x] Code check: `mistake_text` must appear in the full sentence with my answer inserted (not only in my answer). Ignore capital letters, quote marks, apostrophe styles (' and ’) and extra spaces.
- [x] If the check fails: retry once at most. If it fails again, use my answer as `mistake_text`, show the explanation, and log the case. Never block me.
- [x] `why_wrong` and `rule` follow my explanation language setting (English by default until Step 4 adds the selector). `mistake_text` is never translated or changed.
- [x] In the database, the 3 parts are joined into the `explanation` column.
- [x] Tone: kind and encouraging, explain the reason (often the Portuguese structure behind the mistake). The verdict stays strict.
- [x] One slip, one skill (2026-11-16, after the grade demo: "writed" was a wrong verdict AND a detected irregular_verbs row). The detected mistake cannot quote the same words as the main mistake. Checked in code (`grading.py`), with an explicit "She has writed it" example in the prompt. One retry (the same retry as the quotes, one note per problem). If it happens again: keep the main verdict, drop the detected row, log it. Never count one slip against two skills.
- [x] `note` (2026-11-16): the code ignores it unless the verdict is correct (wrong and partial have the 3 parts), and does not show it when there is a detected slip (the reminder is enough).
- [x] A total ceiling per graded answer (2026-11-16): about 4 requests and 20 seconds, counting the quote retry (`RequestBudget` in `llm.py`, shared by the calls).
- [x] `corrected_sentence` check (2026-11-16): my sentence with each quote replaced by its correction must give `corrected_sentence`. If not, it is only logged (`logs/grading_problems.jsonl`), never retried.
- [x] Show the result in green, yellow or red, with the rule and the corrected sentence.
- [x] Add a hint button. Save if you used it.
- [x] "Report a problem" on the result box (2026-11-16): "the sentence is bad" or "the grade is wrong", with an optional comment. Saved in a new table `problem_reports` (exercise id, submission id, kind, my answer, comment, date; one row per answer and kind). A new table needs no migration: `CREATE TABLE IF NOT EXISTS` adds it to an old database. A sentence reported as bad leaves the stock.
- [x] "Skip: this sentence is bad" before answering (2026-11-16): saves a `bad_sentence` report (my answer empty, the submission id reserved for that exercise, no attempt) and takes the sentence out of the stock. A bad sentence is often impossible to answer.
- [x] One answer is never saved twice (2026-11-16): the page reserves one `submission_id` per exercise on screen. `grade_gap_answer()` stops before the AI call if it is already saved, and `save_attempts()` checks again under a write lock (`BEGIN IMMEDIATE`). Tests: the same answer twice, and two gradings at the same moment.
- [x] Save every attempt with `save_attempt()`, including the seconds you took.

**Two more exercise types (same page, same grading code)**

- [ ] Fix the error (find the wrong word and fix it): the AI writes a sentence with one mistake, and you rewrite it correctly.
- [ ] `capitalization` is available in Fix the error (for example "on monday i speak english"). For this skill only, the code check compares capital letters exactly.
- [ ] Word order: the AI writes the correct sentence, the CODE shuffles its words (never in an accepted order), and you type the sentence. Word tiles (build the sentence by clicking the words) only as a help step, like the options (2026-11-19).
- [ ] Word order skills: the `word_order` category plus `too_enough`, `phrasal_verbs_separable` and `have_something_done`, in one helper `get_word_order_skill_ids()` with a test. When a sentence has two correct orders, both are saved (expected answer + accepted answers).

**Test the grader**

- [ ] Create `eval/gold_gap.csv` with 50 rows: sentence, expected answer, a learner answer, and the verdict you decide by hand. Include tricky cases: synonyms, spelling mistakes, a correct answer that is different from the expected one. Include 2–3 typo cases ("finised": grammar correct + spelling) and 2–3 wrong irregular forms ("writed": grammar wrong). Add 5 rows that check the explanation: it must contain my exact wrong words.
- [ ] Gold file rules (2026-11-16): Claude writes the 50 rows with my verdict EMPTY. At least 10 rows use my real mistakes (JOURNAL.md and the `typical_mistake` examples). About 8 partial rows, with "has finish" and "have went" both in. Columns: sentence, expected answer, accepted answers, learner answer, `my_verdict`, `my_detected_skill`, `sure` (yes/no), `must_quote`, notes. I fill `my_verdict`, `my_detected_skill` and `sure`.
- [ ] Claude writes its own verdicts in `eval/gold_gap_claude.csv` (same row ids, one short reason each), at the same time as the gold file. I do not open it until my verdicts are finished.
- [ ] `run_eval.py` compares three graders (me, Claude, Gemini) in pairs, on all rows and on `sure = yes` rows only. It reports agreement with 3 verdicts, with partial counted as wrong, and on the detected skill. "Done when" uses Gemini against MY verdicts; rows with `sure = no` are discussed first.
- [ ] Levels (2026-11-19): the app is for anyone, and my level will go up, so the gold file tests the grader at every level: 15 A2, 15 B1, 12 B2, 8 C1. My real mistakes are in the A2 and B1 rows. `run_eval.py` reports agreement per level, with the number of rows for each.
- [ ] Holdout (2026-11-19): a `split` column, 35 dev rows and 15 holdout rows, drawn once at random AFTER my verdicts are filled, with each of my verdict types in both (fixed seed, never drawn again). Prompt work uses only the dev rows. The holdout rows are graded once, at the end, with the final prompt: that number goes in docs/JOURNAL.md, next to the 50-row number for "Done when".
- [ ] Noise first (2026-11-19): before comparing efforts, run `low` twice on the dev rows and report the difference. An effort difference smaller than it means nothing.
- [ ] Cohen's kappa next to every agreement % (agreement corrected for chance).
- [ ] Write `eval/run_eval.py` (run with `python -m eval.run_eval`). It grades all rows with the AI and prints the agreement and a confusion matrix.
- [ ] `run_eval.py` appends each run to `eval/results.csv`: date (UTC), eval set (gap, writing, translate), model, prompt version, number of rows, agreement. The file goes in git. The Step 8 chart "grader agreement per prompt version" reads it.
- [ ] Improve the prompt, or change the model, until agreement is 90% or more.
- [ ] Explanation review (2026-11-16): besides the gold verdicts, I read the explanations of about 20 graded answers and mark any rule or grammar term that may be wrong (example from the grade demo: "present continuous" for "have been living"). Count them and write the number in docs/JOURNAL.md.
- [ ] Grader effort (2026-11-16): run the gold file with the grader on `low` effort and on the default effort, and compare the agreement. `AI_REASONING_EFFORT_GRADE` changes only in `.env`.
- [x] Reasoning effort per task (2026-11-16): `llm.ask()` receives a task ("create" or "grade"). The values live in `.env` (`AI_REASONING_EFFORT_CREATE`, `AI_REASONING_EFFORT_GRADE`), never in code, so changing provider still needs only settings. Every log line saves the task and the effort used.
- [ ] Effort comparison, blind (can run over two days): 40 exercises made with `low` and 40 with the default, 8 batches each, the SAME skills and topics in both groups. Claude gives me one file with the 80 sentences mixed, without effort or batch. I mark each one good or weak. Claude reveals the groups only after I finish. Only a clear difference counts (small samples, random AI).
- [ ] Review 20 generated exercises by hand and count how many really test the skill that was asked. The AI returns a `GapExerciseDraft` and the code adds `skill_id` and `level`, so this is the only check that the AI wrote about the right skill. Write the number in docs/JOURNAL.md.

**Done when:** you can do 20 sentences without an error, every attempt is in the database with a skill tag, and the grader agrees with you on 45 of the 50 gold rows.

## Step 3 – Writing (check my sentence)

Here you write freely and the AI finds every mistake, so one text can create several rows in the database.

- [ ] Add a text box and a "Check" button. Limit the text to about 150 words to keep answers fast.
- [ ] Write the schema `WritingCheck`: verdict, corrected text, more natural version, praise, and a list of mistakes. Each mistake has the wrong part, the fix, the reason, the skill id and the error type.
- [ ] Write the prompt. The AI must keep your meaning, correct only real errors, and choose skill ids from your list.
- [ ] Show your text with the wrong parts in red and the fixes in green.
- [ ] Show the corrected text and the more natural version below.
- [ ] Naturalness: when a sentence is correct but a native speaker would say it differently, save it with error type `naturalness`, verdict correct, source detected, and the closest skill (if nothing fits, `word_choice`). It never lowers the mastery score. Save my sentence + the natural version, so Review (Step 7) can bring these "expressions to learn" back.
- [ ] Each checked text creates one row in `exercises` (section writing, prompt text = the writing prompt or your text, expected answer empty), so every attempt has an exercise\_id.
- [ ] Save one attempt per mistake, verdict wrong, with its skill id and source "detected". For a text with no mistakes, save one correct attempt with the skill `writing_general`. All rows of one text share the same submission\_id.
- [ ] Add a "Give me a writing prompt" button that uses your level and topic.
- [ ] Add a "Try again" button: you rewrite the text without looking at the fix, and the AI checks it again.
- [ ] Add 15 rows to the gold file for writing. Include 5 correct texts, to check that the AI does not invent mistakes.

**Done when:** a text with 3 mistakes creates 3 attempts with correct skill tags, and a perfect text gets no invented mistakes.

## Step 4 – Tutor brain, Learn and Home

This step adds the part you asked for: the app tells you what to study and teaches it.

**Mastery (`tutor/mastery.py`, plain pandas, no AI)**

- [ ] Write `skill_stats()`: for each skill, the number of attempts, accuracy over the last 10 attempts, and the date of the last attempt. Count a partial answer as half.
- [ ] Give each skill a status: new (under 5 attempts), weak (under 60%), learning (60 to 85%), strong (over 85%).
- [ ] Only targeted attempts count for the mastery score. Detected attempts are a warning signal.
- [ ] Reported attempts do not count (decided 2026-11-16): every attempt on an exercise reported as `bad_sentence` (by exercise id), and every attempt of an answer reported as `wrong_grade` (by submission id), is left out of the mastery score, whatever the verdict. The rows stay in the database; only `mastery.py` leaves them out (`problem_reports`, Step 2 Part 3).
- [ ] Write `recommend()`: return the 3 weakest skills. Start with the ones at or below your level, because basics like verb to be matter most. `writing_general`, `listening` and `speaking` are never recommended as grammar skills. `spelling` is a normal skill.
- [ ] Detected mistakes become visible: if a skill gets 3 detected mistakes in 14 days, Home suggests 5 targeted sentences on it. Naturalness rows do not count for this rule.
- [ ] Test: naturalness rows never change the mastery score and never create a warning.
- [ ] Write tests with fake attempts to check the statuses.
- [ ] Tests for reported attempts: a wrong attempt on a `bad_sentence` exercise does not lower the score; a correct one does not raise it; an answer reported as `wrong_grade` is left out (all its rows), but other answers on the same exercise still count; the reported rows are still in `attempts`.

**"You must study X" message**

- [ ] After each answer in Practice and Writing, check the skill. If it just became weak, show a box: "You missed verb to be in 6 of your last 10 answers. Study it now?" with a button to the lesson.
- [ ] Show the message once per skill per day, so it does not annoy you.

**Learn section**

- [ ] Show all skills grouped by category, each with its status color. Weak ones first.
- [ ] Write the lesson prompt. It receives the skill and your last 5 wrong answers on it, and returns: the rule in simple words, 3 examples, the typical mistake of Portuguese speakers, and a memory tip.
- [ ] Save the lesson in `lessons`, so the app does not create it again every time.
- [ ] Save one row in `lesson_events` each time I open a lesson.
- [ ] Under the lesson, give 5 fill-the-gap sentences only on that skill. Use the code from Step 2.
- [ ] At the end, show the score and the new status of the skill.
- [ ] Match each sentence to its rule (2026-11-19): a few sentences and a few rules; I connect each sentence to the rule it uses.
- [ ] Sort sentences into two columns (2026-11-19), for skills that look alike (present perfect / past simple, make / do, will / going to): each sentence goes in the column of the form it needs.
- [ ] Add a selector for the explanation language (Portuguese or English).

**Home page**

- [ ] Show today's plan: reviews due (ready for Step 7), your weakest skill with a "Study now" button, and the daily goal (for example 15 answers).
- [ ] Show the streak: days in a row with the goal reached.
- [ ] Show the AI usage of today in the menu: "AI today: 37 / 500 requests". Turn it orange near the limit.
- [ ] Make Practice choose skills in a smart way: about 60% weak skills, 30% learning, 10% new or strong.

**Done when:** you answer verb to be wrong 6 times on purpose, the app tells you to study it, the lesson uses your own mistakes, and Practice gives you more sentences about it.

## Step 5 – Listening

You add a Listen button to every English sentence in the app, then a dictation exercise.

**Listen button (`tutor/audio.py`)**

- [ ] Write `listen_button(text)`: a small HTML block (`st.components.v1.html`) with a button that calls the browser's `speechSynthesis` with an English voice.
- [ ] Add a speed option: normal and slow (rate 0.7).
- [ ] Add a voice option: American or British English, from the voices the browser offers.
- [ ] Put the button on corrected sentences in Practice and Writing, and on lesson examples in Learn.
- [ ] Test in Chrome and in one other browser. Some browsers have few voices.

**Dictation**

- [ ] The AI writes a sentence for your level and topic. The app hides the text and shows only Play and Play slow.
- [ ] You type what you hear and press Check.
- [ ] Compare in code with `difflib`, word by word: correct words in green, wrong or missing words in red. Ignore capital letters and punctuation.
- [ ] Score = percentage of correct words. 100% is correct, 80% or more is partial, less is wrong.
- [ ] Count how many times you pressed Play and save it with the attempt.
- [ ] Save the attempt with the skill `listening` and the list of words you missed. These words become vocabulary to review.
- [ ] Add a second mode: listen to a short text of 3 sentences and answer one question about it. The AI grades the answer.

**Done when:** every English sentence in the app has a Listen button, and a dictation shows exactly which words you missed.

Upgrade for later: if the browser voice sounds bad, create the audio in Python with Piper (free, offline) and play it with `st.audio`.

## Step 6 – Translate

You read a sentence in Portuguese and write it in English, and the AI judges the meaning.

- [ ] Write the schema `TranslationExercise`: Portuguese sentence, one good English translation, main skill id, level.
- [ ] Write the prompt. Ask for sentences where Portuguese speakers often make mistakes in English: false friends, "have" for age, missing subject, prepositions.
- [ ] Write the schema `TranslationGrade`: verdict, meaning is correct (yes or no), list of mistakes with skill ids, your sentence corrected, the most natural version.
- [ ] Tell the AI to accept any translation with the same meaning and correct grammar, and to keep your words when they are right.
- [ ] Show the three versions together: yours, corrected, natural. Add the Listen button.
- [ ] Save attempts like in Writing: one per mistake, with its skill id.
- [ ] Add a second direction for vocabulary: one English word or expression in a sentence, and you explain it in Portuguese.
- [ ] Add 15 translation rows to the gold file. Include correct translations that use different words from the expected one.

**Done when:** a correct translation with different words gets "correct", and a translation with the wrong meaning gets "wrong" with a clear reason.

## Step 7 – Review (spaced repetition)

Your mistakes come back on a schedule until you know them, and this is what makes the learning stay.

- [ ] Write `tutor/srs.py` with the box system: box 1 returns after 1 day, box 2 after 3, box 3 after 7, box 4 after 14, box 5 after 30.
- [ ] When an answer is wrong or partial in any section, add the exercise to `reviews` in box 1, due tomorrow. This includes a submission where only a DETECTED row is wrong ("writed": past simple correct, irregular verbs wrong), otherwise that mistake would never come back.
- [ ] In Review, show the exercises due today, oldest first. Use the same screen and grading as the original section.
- [ ] Correct answer: move up one box and set the new due date. Wrong answer: back to box 1.
- [ ] After a correct answer in box 5, mark the exercise as learned and remove it from the reviews.
- [ ] For Writing and Translate mistakes, do not repeat your old text. Ask the AI for a new fill-the-gap sentence on the same skill and the same kind of mistake.
- [ ] Add the vocabulary you missed in Listening as flashcards: the word, and you type a sentence with it.
- [ ] Limit reviews to 20 a day, so a bad week does not create a mountain.
- [ ] Never bring back an exercise I reported as a bad sentence (`problem_reports`, kind `bad_sentence`, Step 2 Part 3).
- [ ] Show the number of reviews due on Home and next to the menu item.
- [ ] Write tests for the box moves and the due dates.

**Done when:** a sentence you get wrong today appears in Review tomorrow, and moves to 3 days after you get it right.

## Step 8 – Progress (dashboard)

By now you have weeks of real answers, so the charts show something true.

- [ ] Top row with four numbers: answers this week, accuracy this week, current streak, skills that are strong.
- [ ] Filters: period, section, level.
- [ ] Level estimate: show the highest level where at least 70% of the skills are strong. Call it an estimate, because it is not an official test.
- [ ] Weekly report button: send this week's numbers to the AI and ask for 5 lines. What improved, what is still weak, and one plan for next week.
- [ ] Export button: download all attempts as CSV, to analyze in a notebook.

**Rules for every chart**

- [ ] All calculations live in `tutor/stats.py` as functions that return DataFrames, with pytest tests on fake data. Pages only draw.
- [ ] One definition of accuracy, the same as mastery: targeted attempts only, partial = 0.5, counted by `submission_id`. Naturalness rows never count.
- [ ] Every chart shows the number of answers behind it. Fewer than 5 answers = grey, with "not enough data yet".
- [ ] Days, weeks and hours use Europe/Lisbon time.
- [ ] Speed charts (seconds per answer) leave out answers that took more than about 3 minutes: I probably left the page. The database keeps the real seconds; only the chart filters them (2026-11-16).
- [ ] Status colors always come with a text label.
- [ ] One line under each chart says what to do next.

**First version: 4 charts**

- [ ] Accuracy by CEFR level (A2, B1, B2, C1): the average of the skill accuracies in each level, so skills I practise more do not weigh more.
- [ ] Skill map: all skills grouped by category, colored by status (new, weak, learning, strong), with a mark on skills that have detected warnings. A click opens the skill in Learn.
- [ ] Accuracy per week: one line for new exercises, one for reviews, with bars for the number of answers. Weeks with fewer than 10 answers are grey.
- [ ] Top 10 mistake patterns in the last 30 days: skill, number of mistakes (targeted wrong + detected), and my 2 latest examples as `mistake_text` → `correction`.
- [ ] "Expressions to learn" is a separate list, not part of the top 10.

**Ideas for later charts (do not build in the first version)**

- [ ] Mistakes by category and by error type (grammar, vocabulary, spelling, word order, naturalness).
- [ ] Bar chart: accuracy per skill, sorted from weakest to strongest, colored by status.
- [ ] Calendar heatmap: answers per day, to see your habit.
- [ ] One skill over time.
- [ ] Skills by status per week (how many weak, learning, strong).
- [ ] Before and after a lesson: accuracy on a skill in the 10 answers before and the 10 after I studied it in Learn.
- [ ] Accuracy by hour of the day.
- [ ] Seconds per answer by skill.
- [ ] Hint use by skill.
- [ ] Reviews by box.
- [ ] Accuracy in Review by days since last seen.
- [ ] Grader agreement per prompt version.
- [ ] AI requests per day against the limit.

**Done when:** you open Progress and can say in 10 seconds which skill to study next and whether this week was better than the last.

## Step 9 – Speaking and conversation

This is the hardest step technically, so it comes after everything else works.

**Voice to text**

- [ ] Record your voice in the page with `st.audio_input`.
- [ ] Add `faster-whisper` to `requirements.txt` and write `transcribe(audio)` in `audio.py` with a small English model.
- [ ] Add a setting to use Groq's Whisper instead, for a slow computer.

**Read aloud**

- [ ] Show a sentence. You read it aloud, and the app transcribes your voice.
- [ ] Compare the transcription with the sentence, word by word. Use the same code as dictation.
- [ ] Show the words the app did not understand. Add the Listen button so you can hear them and try again.
- [ ] Save the attempt with the skill `speaking` and the list of difficult words.
- [ ] Tell yourself the limit in the page: this checks if your speech is understandable, not your accent sound by sound.

**Conversation role-play**

- [ ] Offer scenes: job interview, daily stand-up, explaining a model to a manager, restaurant, airport.
- [ ] Build a chat with `st.chat_message` and `st.chat_input`. You can type or speak your turn.
- [ ] The AI plays the other person, uses your level, and keeps each turn short (2 or 3 sentences).
- [ ] During the chat the AI does not correct you, so the conversation feels real.
- [ ] After 8 to 10 turns, press "Finish". The AI reads all your turns and returns the list of mistakes, like in Writing, plus 3 useful expressions you could have used.
- [ ] Save one attempt per mistake with its skill id. Wrong ones go to Review.
- [ ] Add the Listen button to each AI turn.

**Done when:** you can finish a spoken job-interview scene of 8 turns and get a list of your mistakes at the end.

## Step 10 – Polish, tests, README, online version

The app already works, and this step makes it solid and good to show on your GitHub profile.

**Quality**

- [ ] Add a level test for new users: 20 sentences from A2 to C1, and the app sets the starting level.
- [ ] Add a Settings page: level, topics, explanation language, daily goal, AI provider, voice.
- [ ] Idea: switches in Settings to turn off some detected checks for a while (capitalization, spelling), for example when typing fast on a phone. Default: all on. When a switch is off, those mistakes are not saved as detected attempts.
- [ ] Add a button to back up the database file and one to restore it.
- [ ] Show a clear message when the AI is not available, and let Review work with saved exercises without the AI.
- [ ] Cache AI answers that do not change (lessons, exercises already created) to save requests.
- [ ] Run the gold file again for all sections and write the agreement numbers in the README.

**Code**

- [ ] Finish the tests for `db.py`, `mastery.py`, `srs.py` and the answer comparison code.
- [ ] Add a GitHub Actions workflow that runs `pytest` on every push.
- [ ] Add `ruff` for code style.

**README**

- [ ] Write what the app does, with 3 screenshots or a short GIF.
- [ ] Write how to install and run it in 5 commands.
- [ ] Explain the tutor logic: skill list, mastery score, spaced repetition, grader evaluation. This part shows your data science work.

**Online version (optional)**

- [ ] Deploy to Streamlit Community Cloud from the repo, with Groq or Gemini as the AI.
- [ ] Put the API key in the Streamlit secrets, never in the code.
- [ ] Move the data to a free hosted database, because the SQLite file may not survive a restart there. Check the current free plans of hosted Postgres or SQLite services before you choose.
- [ ] Add a simple password, so other people do not spend your free AI requests.

**Done when:** a friend can clone the repo, follow the README, and study in 10 minutes.

## Risks and later ideas

Four things can make the app teach badly, and each has a fix in the plan.

| Risk | What happens | Fix |
| --- | --- | --- |
| The AI grades wrongly | You learn a wrong rule | The gold file and the 90% target (Steps 2, 3, 6). A small local model may fail this test: then use a bigger model or Groq |
| The AI uses wrong skill tags | The tutor recommends the wrong topic | Fixed skill list, validation in code, and tags checked in the gold file |
| Free limits change | The online AI stops working | Ollama or Groq as a backup, and the provider set in one setting |
| You stop using it | No learning | Short daily goal, streak, and a limit of 20 reviews a day |

**Ideas for later**

- [ ] Paste an article or an email, and the AI creates exercises from it.
- [ ] Reading section: short texts with questions, and click a word to save it as vocabulary.
- [ ] Replace the box system with a model that predicts when you will forget each skill, trained on your own attempts.
- [ ] Pronunciation practice for difficult sounds, with minimal pairs (ship and sheep).
- [ ] Exam mode for IELTS or TOEFL writing tasks.
- [ ] "Is this sentence correct?" (2026-11-19): I say yes or no, and fix it when it is wrong.
- [ ] "Rewrite this sentence in another tense" (2026-11-19): for example, from present simple to past simple.

## Sources

Read on 13 November 2026.

- [Groq rate limits](https://console.groq.com/docs/rate-limits)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Streamlit Community Cloud: manage your app](https://docs.streamlit.io/streamlit-community-cloud/get-started/manage-your-app)
