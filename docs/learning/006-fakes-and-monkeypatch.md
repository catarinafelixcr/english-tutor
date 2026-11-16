# 006 - fakes in tests with monkeypatch

- **Date:** 2026-11-16
- **Step of the plan:** Step 1 (Part 4)
- **Files where I used it:** `tests/test_llm.py`, `tutor/llm.py`

## what it is

A **fake** is a small piece of test code that pretends to be something real: here, a fake AI and a fake clock.
`monkeypatch` is a pytest fixture that replaces a function or a value **during one test only**, and puts the
real one back when the test ends. So the test controls exactly what "the AI" answers and what "time" it is.

## why I needed it

`llm.py` talks to Gemini, waits between retries and reads `.env`. Tests with the real thing would be:

- slow (real waits of 2 s and 4 s, real network),
- expensive (every test run would use my daily quota, and failed requests count too),
- impossible to control (I cannot ask Google to send a 503 now, then a 429 with `retryDelay: 14.2s`),
- risky (a test could read my real API key).

## how I used it here

**1. Keep the dangerous parts in tiny functions.** In `llm.py`, only `call_ai()` uses the internet, and only
`monotonic_seconds()` and `wait_seconds()` use the clock. Everything else is plain logic that calls them.
This is the trick that makes faking easy: a test replaces three small functions, not the whole file.

```python
def call_ai(settings, prompt_text, schema):
    client = openai.OpenAI(base_url=settings["base_url"], api_key=settings["api_key"], max_retries=0, ...)
    return client.chat.completions.parse(...)

def wait_seconds(seconds):
    time.sleep(seconds)
```

**2. A fake world with planned answers.** In `tests/test_llm.py`, `FakeWorld` holds a list of planned results.
Each call to the fake AI takes the next one: an answer, or an error to raise. Its clock only moves when a
request "takes time" or when the code "waits", so nothing really waits.

```python
planned_results = [make_gemini_error(503, "high demand"), make_fake_response("hi", "fake-test-model")]
fake_world = install_fake_world(monkeypatch, planned_results, 1)

ask_tiny_question()

assert fake_world.call_count == 2     # one 503, then one retry
assert fake_world.waits == [2]        # the code "waited" 2 s, in 0 real seconds
```

**3. monkeypatch replaces the real functions, only inside this test.**

```python
monkeypatch.setattr(llm, "call_ai", fake_world.call_ai)
monkeypatch.setattr(llm, "wait_seconds", fake_world.wait_seconds)
monkeypatch.setattr(llm, "LOG_PATH", tmp_path / "ai_log.jsonl")   # a temporary log, not logs/
monkeypatch.setattr(llm, "load_dotenv", lambda: None)             # never read my real .env
```

Result: 40 tests for `llm.py` in about 1 second, 0 requests, 0 quota, and my key is never touched.
One test even uses a fake key (`FAKE-SECRET-123`) and checks it is not in the log.

## mistakes I made and how I fixed them

- The real `openai.APITimeoutError` needs a network request object to be created. The test creates it without
  running its `__init__` (`openai.APITimeoutError.__new__(openai.APITimeoutError)`): it is still a real
  `APITimeoutError` for `isinstance()`, which is all `llm.py` checks.
- The other openai errors are not used directly: a small `FakeStatusError` with only `status_code` and `body`
  is enough, because `llm.py` only reads those two values. The real shapes of `body` came from the experiments
  E5–E7 (a list with one item).
- Without faking `load_dotenv`, the settings tests would read my real `.env` and could pass or fail depending
  on my settings. Tests must give the same result on any computer.

## links

- pytest monkeypatch: https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- pytest tmp_path: https://docs.pytest.org/en/stable/how-to/tmp_path.html