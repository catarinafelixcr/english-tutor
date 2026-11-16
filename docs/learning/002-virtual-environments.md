# 002 - Virtual environments (venv)

- **Date:** 2026-11-16
- **Step of the plan:** Step 0
- **Files where I used it:** `.venv/` (the folder), `requirements.txt`, `.gitignore`

## What it is

A virtual environment is a private folder with its own copy of Python and its own libraries, just for one project.
Libraries installed there do not mix with other projects on the computer. It is similar to a conda environment, but it comes with Python (`venv`), so nothing extra to install.

## why I needed it

Each project needs its own libraries, sometimes in different versions. Without a venv, everything goes into the one global Python, and one project can break another when I update a library.
With a venv, this project has exactly what is in `requirements.txt`, and I can delete `.venv` and create it again at any time.

## how I used it here

Create the environment (one time only). This makes the folder `.venv` in the project:

```text
python -m venv .venv
```

Install the libraries listed in `requirements.txt` into it:

```text
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Activate it in my own terminal (every time I open a new terminal). After this, `python`, `pip`, `streamlit`, `pytest` and `ruff` all use the project's private copy. The prompt starts with `(.venv)`:

```text
.venv\Scripts\activate        # Windows (PowerShell)
source .venv/bin/activate     # Mac / Linux
deactivate                    # leave the environment
```

Check which Python is in use (it should point inside `.venv`):

```text
python -c "import sys; print(sys.executable)"
```

Two important things:

- `.venv/` is in `.gitignore`. It is big and specific to my computer, so it never goes to GitHub.
  Other people recreate it from `requirements.txt` with the two commands above.
- `requirements.txt` is the "recipe", and `.venv` is the "cooked dish". Git saves the recipe, not the dish.

## mistakes I made and how I fixed them

- If PowerShell says "running scripts is disabled on this system" when I activate, run this once:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. (Not needed yet, write here if it happens.)


## links

- https://docs.python.org/3/library/venv.html
- https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/