# English Tutor

A personal web app to learn English with an AI tutor.

It creates exercises, checks answers, explains mistakes, finds weak grammar skills and then tells you what to study next.

**Status:** work in progress (Step 0 – Setup). See [docs/PLAN.md](docs/PLAN.md) for the full plan and [docs/PROGRESS.md](docs/PROGRESS.md) for progress.


## Tech stack

Python, Streamlit, SQLite, pandas, Plotly, Pydantic. The AI is the Gemini API free tier, called through the `openai` Python client, so the provider can be changed in `.env`.


## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # on Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # then write your own API key in .env
streamlit run app.py
```


## License

MIT