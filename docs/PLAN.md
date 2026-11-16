# AI English Tutor – Build Plan

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
5. **You type, you do not click.** Typing the answer from memory teaches more than choosing from options, so there is no multiple choice.
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
- [ ] Ask for structured JSON output with the Pydantic schema, then validate the answer. On a validation error, retry once.
- [ ] On a rate-limit error (HTTP 429), wait and retry up to 3 times, then show a friendly message.
- [ ] Save every prompt and answer to a log file, so you can debug bad AI answers later.

**Skill list (`tutor/skills.py`)**

- [ ] Write the fixed list of about 40 skills. Each one has an id, a name, a level and a category: `to_be | Verb to be | A2 | verbs`.
- [ ] Cover these categories: verb tenses, modals, articles, prepositions, pronouns, comparatives, conditionals, passive voice, word order, phrasal verbs, collocations, spelling.
- [ ] Add one short example of a typical mistake for each skill. The AI uses it to choose the right tag.

**Database (`tutor/db.py`, SQLite)**

- [ ] Table `skills`: id, name, level, category.
- [ ] Table `exercises`: id, section, skill\_id, level, topic, prompt text, expected answer, created date.
- [ ] Table `attempts`: id, exercise\_id, section, skill\_id, your answer, verdict (correct, partial, wrong), error type (grammar, vocabulary, spelling, word order), explanation, hint used, seconds taken, date.
- [ ] Table `reviews`: exercise\_id, box number, due date.
- [ ] Table `lessons`: skill\_id, lesson text, date.
- [ ] Write the helper functions `save_attempt()`, `get_attempts()` and `init_db()`.
- [ ] Write pytest tests that create a temporary database, save one attempt and read it back.

**Done when:** a small script asks the AI for one fill-the-gap sentence, gets a valid object with a skill id from your list, and saves it in the database.

## Step 2 – Practice (fill the gap)

This is the first version you can really study with, and it copies the page I built for you in this chat.

**Create sentences**

- [ ] Write the Pydantic schema `GapExercise`: sentence with `___`, expected answer, other accepted answers, skill id, hint, level.
- [ ] Write the prompt in `prompts.py`. It receives the level, the topic and the full skill list, and returns 5 exercises.
- [ ] Check each exercise in code: exactly one `___`, a skill id that exists, an answer that is not empty. Drop the bad ones.
- [ ] Save the good ones in `exercises` and avoid sentences you already saw.
- [ ] Add selectors for level and topic (daily life, data science and work, travel, meetings).

**Check answers**

- [ ] First check in code: if your answer equals the expected answer or an accepted one (ignore capital letters and spaces), it is correct. No AI call needed.
- [ ] Otherwise ask the AI. Schema `GapGrade`: verdict, error type, explanation, corrected sentence, other good answers, memory tip.
- [ ] Tell the AI to accept any answer a native speaker would use, and to explain why your answer does not work.
- [ ] Show the result in green, yellow or red, with the rule and the corrected sentence.
- [ ] Add a hint button. Save if you used it.
- [ ] Save every attempt with `save_attempt()`, including the seconds you took.

**Two more exercise types (same page, same grading code)**

- [ ] Fix the error: the AI writes a sentence with one mistake, and you rewrite it correctly.
- [ ] Word order: the AI gives shuffled words, and you type the sentence.

**Test the grader**

- [ ] Create `eval/gold_gap.csv` with 50 rows: sentence, expected answer, a learner answer, and the verdict you decide by hand. Include tricky cases: synonyms, spelling mistakes, a correct answer that is different from the expected one.
- [ ] Write `eval/run_eval.py`. It grades all rows with the AI and prints the agreement and a confusion matrix.
- [ ] Improve the prompt, or change the model, until agreement is 90% or more.

**Done when:** you can do 20 sentences without an error, every attempt is in the database with a skill tag, and the grader agrees with you on 45 of the 50 gold rows.

## Step 3 – Writing (check my sentence)

Here you write freely and the AI finds every mistake, so one text can create several rows in the database.

- [ ] Add a text box and a "Check" button. Limit the text to about 150 words to keep answers fast.
- [ ] Write the schema `WritingCheck`: verdict, corrected text, more natural version, praise, and a list of mistakes. Each mistake has the wrong part, the fix, the reason, the skill id and the error type.
- [ ] Write the prompt. The AI must keep your meaning, correct only real errors, and choose skill ids from your list.
- [ ] Show your text with the wrong parts in red and the fixes in green.
- [ ] Show the corrected text and the more natural version below.
- [ ] Save one attempt per mistake, verdict wrong, with its skill id. For a text with no mistakes, save one correct attempt with the skill `writing_general`.
- [ ] Add a "Give me a writing prompt" button that uses your level and topic.
- [ ] Add a "Try again" button: you rewrite the text without looking at the fix, and the AI checks it again.
- [ ] Add 15 rows to the gold file for writing. Include 5 correct texts, to check that the AI does not invent mistakes.

**Done when:** a text with 3 mistakes creates 3 attempts with correct skill tags, and a perfect text gets no invented mistakes.

## Step 4 – Tutor brain, Learn and Home

This step adds the part you asked for: the app tells you what to study and teaches it.

**Mastery (`tutor/mastery.py`, plain pandas, no AI)**

- [ ] Write `skill_stats()`: for each skill, the number of attempts, accuracy over the last 10 attempts, and the date of the last attempt. Count a partial answer as half.
- [ ] Give each skill a status: new (under 5 attempts), weak (under 60%), learning (60 to 85%), strong (over 85%).
- [ ] Write `recommend()`: return the 3 weakest skills. Start with the ones at or below your level, because basics like verb to be matter most.
- [ ] Write tests with fake attempts to check the statuses.

**"You must study X" message**

- [ ] After each answer in Practice and Writing, check the skill. If it just became weak, show a box: "You missed verb to be in 6 of your last 10 answers. Study it now?" with a button to the lesson.
- [ ] Show the message once per skill per day, so it does not annoy you.

**Learn section**

- [ ] Show all skills grouped by category, each with its status color. Weak ones first.
- [ ] Write the lesson prompt. It receives the skill and your last 5 wrong answers on it, and returns: the rule in simple words, 3 examples, the typical mistake of Portuguese speakers, and a memory tip.
- [ ] Save the lesson in `lessons`, so the app does not create it again every time.
- [ ] Under the lesson, give 5 fill-the-gap sentences only on that skill. Use the code from Step 2.
- [ ] At the end, show the score and the new status of the skill.
- [ ] Add a selector for the explanation language (Portuguese or English).

**Home page**

- [ ] Show today's plan: reviews due (ready for Step 7), your weakest skill with a "Study now" button, and the daily goal (for example 15 answers).
- [ ] Show the streak: days in a row with the goal reached.
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
- [ ] When an answer is wrong or partial in any section, add the exercise to `reviews` in box 1, due tomorrow.
- [ ] In Review, show the exercises due today, oldest first. Use the same screen and grading as the original section.
- [ ] Correct answer: move up one box and set the new due date. Wrong answer: back to box 1.
- [ ] After a correct answer in box 5, mark the exercise as learned and remove it from the reviews.
- [ ] For Writing and Translate mistakes, do not repeat your old text. Ask the AI for a new fill-the-gap sentence on the same skill and the same kind of mistake.
- [ ] Add the vocabulary you missed in Listening as flashcards: the word, and you type a sentence with it.
- [ ] Limit reviews to 20 a day, so a bad week does not create a mountain.
- [ ] Show the number of reviews due on Home and next to the menu item.
- [ ] Write tests for the box moves and the due dates.

**Done when:** a sentence you get wrong today appears in Review tomorrow, and moves to 3 days after you get it right.

## Step 8 – Progress (dashboard)

By now you have weeks of real answers, so the charts show something true.

- [ ] Top row with four numbers: answers this week, accuracy this week, current streak, skills that are strong.
- [ ] Bar chart: accuracy per skill, sorted from weakest to strongest, colored by status.
- [ ] Line chart: accuracy per week, one line per section (Practice, Writing, Listening, Translate).
- [ ] Calendar heatmap: answers per day, to see your habit.
- [ ] Table of your 10 most repeated mistakes: skill, example of your answer, the correct form.
- [ ] Chart of error types: grammar, vocabulary, spelling, word order.
- [ ] Filters: period, section, level.
- [ ] Level estimate: show the highest level where at least 70% of the skills are strong. Call it an estimate, because it is not an official test.
- [ ] Weekly report button: send this week's numbers to the AI and ask for 5 lines. What improved, what is still weak, and one plan for next week.
- [ ] Export button: download all attempts as CSV, to analyze in a notebook.

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

## Sources

Read on 13 November 2026.

- [Groq rate limits](https://console.groq.com/docs/rate-limits)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Streamlit Community Cloud: manage your app](https://docs.streamlit.io/streamlit-community-cloud/get-started/manage-your-app)
