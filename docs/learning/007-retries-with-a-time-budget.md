# 007 - retries with a time budget

- **Date:** 2026-11-16
- **Step of the plan:** Step 1 (Part 4)
- **Files where I used it:** `tutor/llm.py`, `scripts/part4_experiments.py`

## what it is

A **retry** means sending the same request again after it failed. The hard part is not retrying, it is
deciding **which** errors deserve a retry, **how long** to wait, and **when to stop**. A **time budget** is a
limit on the total time of all tries together, so the app never makes me wait for a long time.

## why I needed it

The free Gemini API fails sometimes, and every request, even a failed one, uses quota (AI Studio showed
6 / 5 RPM in red after my 6 failed requests in E5). So:

- no retries = the app breaks at the first busy minute;
- too many retries = I lose quota and wait in front of a frozen page.

## how I used it here

**1. Sort errors into "retry" and "stop".** The question is: can trying again soon fix it?

| Error | Retry? | Why |
| --- | --- | --- |
| 429 per minute, 503 "high demand" | yes, at most 2 times | the server is busy now, it can work in a few seconds |
| bad answer (Pydantic refuses it) | yes, once | the AI can write a good answer the next time |
| 429 daily quota | no → `AIDailyLimitError` | it resets at midnight Pacific time |
| timeout (30 s) | no → `AIUnavailableError` | I already waited 30 s; waiting 30 s more is worse |
| wrong key (400 "API key") or model (404) | no → `AIConfigurationError` | only fixing `.env` helps |
| other 400 | no → `AIRequestRejectedError` | the request itself is wrong: the code must change |

**2. Wait a little longer each time (backoff):** 2 s, then 4 s. If the error body says how long to wait
(`retryDelay: "5s"`), use that. If it says more than 10 s, do not wait: stop and say "wait 15 seconds",
with the number in `error.retry_after_seconds`, so a page can show a countdown.

**3. The budget check, BEFORE each wait.**

```python
if monotonic_seconds() - first_request_time + wait_time > RETRY_BUDGET_SECONDS:   # 20 s
    raise AIUnavailableError("The AI is busy. Try again in a minute.") from error
```

"Time already used + the next wait" is checked first, so the app never waits only to give up after.
`time.monotonic()` is used instead of the normal clock because it never jumps back (for example when Windows
changes the time).

**4. Only my code retries.** The `openai` client retries 429 two times by itself by default. Those hidden
retries would use quota without a line in my log or a count in my counter, so the client gets `max_retries=0`.

**5. Worst case for one `ask()`:** 1 request + 1 bad-answer retry + 2 busy retries = 4 requests, in about
20 seconds at most (plus the time of the requests themselves).

## mistakes I made and how I fixed them

- I expected the E5 experiment (6 requests at once) to give a 429. It gave **503** "high demand" and timeouts
  instead. So 503 is now handled like a per-minute 429. Lesson: test the real API before writing the rules.
- I thought failed requests were free. AI Studio showed they are counted. So the counter counts every request
  sent, and the app stops 20 requests before the limit (`AI_DAILY_LIMIT_MARGIN`), because it cannot see
  requests made outside `llm.py`.
- A wrong key is a 400, not a 401/403 (E6), so the message decides ("API key" → configuration error). In the
  first plan, any other 400 became `AIUnavailableError` ("try again later"). But retrying a refused request
  never fixes it, so it got its own error: `AIRequestRejectedError`.
- Ruff rule N818 asked that exception names end in `Error`. I renamed them all (`AIUnavailable` →
  `AIUnavailableError`), like `AIConfigurationError` already was.

## links

- Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini API troubleshooting (error codes): https://ai.google.dev/gemini-api/docs/troubleshooting
- Python `time.monotonic`: https://docs.python.org/3/library/time.html#time.monotonic