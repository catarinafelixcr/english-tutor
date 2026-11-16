# 001 - CLAUDE.md and project memory

- **Date:** 2026-11-13
- **Step of the plan:** Step 0
- **Files where I used it:** `CLAUDE.md`

## what it is

`CLAUDE.md` is a Markdown file in the root folder of the project. Claude Code
reads it at the start of every session. It is the permanent memory of the
project: what the project is, the commands, the structure and the rules.

## why I needed it

Claude Code does not remember earlier sessions by itself. Without this file I
would explain the project again every time, and it could break my rules
(for example, write an API key in the code).

## how I used it here

My `CLAUDE.md` has: who I am, where the plan is, the tech stack, the commands,
the folder structure, the rules, and how I want Claude Code to work with me.

A line that starts with `@` points to another file, so the main file stays short:

```text
- The full build plan is in @docs/PLAN.md (Steps 0 to 10).
```

Useful commands inside Claude Code:

```text
/init     create or improve a CLAUDE.md
/memory   see and edit the memory files
/clear    start a new conversation but keep the project memory
```

## mistakes I made and how I fixed them

- (none yet)

## links

- https://code.claude.com/docs/en/memory
