# 003 - Git basics

- **Date:** 2026-11-16
- **Step of the plan:** Step 0
- **Files where I used it:** the whole project, `.gitignore`

## what it is

Git saves the history of a project: each "commit" is a photo of the files at one moment, with a message that says what changed.
The history lives in the hidden `.git` folder, on my computer. GitHub is a website that keeps a copy of that history online.

## why I needed it

To go back when something breaks, to remember why I changed something (the commit messages),
and to put the project on GitHub so other people can see it and clone it.

## how I used it here

The 3 places a file can be:

```text
working folder  --git add-->  staging area  --git commit-->  history (.git)  --git push-->  GitHub
(my files)                    (selected for                  (on my computer)              (online)
                               the next commit)
```

Commands I used in Step 0:

```text
git status --short              # what changed? (only reads)
                                #   ?? = new file git does not know yet
                                #   M  = modified    D = deleted
git add app.py pages tutor      # select files for the next commit
git commit -q -m "message"      # save the selected files in the history
                                #   -m = the message, -q = quiet output
git log --oneline               # list the commits, one per line (only reads)
git ls-files                    # list all files that git saves (only reads)
git restore .env.example        # bring back a file from the last commit
git branch -m main              # rename the current branch to "main"
git remote add origin <url>     # connect my local repo to the GitHub repo (one time)
git push -u origin main         # first upload to GitHub; -u remembers where to push
git push                        # next uploads: only this
```

A real example from today: I renamed `.env.example` to `.env` by mistake. `git status` showed `D .env.example` (deleted),
and `git restore .env.example` brought it back from the last commit.

Things git must NEVER save: `.env` (my key), `data/` (my database) and `.venv/`. They are in `.gitignore`.
Before the first push, `git ls-files` confirmed none of them was in the list.

Good habits:

- Small commits, one task each, with a clear message ("Add empty app with menu, pages and tutor modules").
- `commit` is local and safe. `push` is public: check before.

## mistakes I made and how I fixed them

- Renamed `.env.example` instead of copying it → `git restore .env.example`.
- Warnings "LF will be replaced by CRLF": not an error. Windows and Mac/Linux mark line ends differently, and git converts them.

## links

- https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F
- https://docs.github.com/en/get-started/using-git/about-git