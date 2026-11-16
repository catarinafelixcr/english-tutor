"""Tests for tutor/llm.py. A fake AI and a fake clock: no internet, no quota, no real waiting."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import openai
import pytest
from pydantic import BaseModel, ValidationError

from tutor import llm

FAKE_API_KEY = "FAKE-SECRET-123"


class TinyAnswer(BaseModel):
    text: str


# ---------- fake objects ----------

class FakeStatusError(Exception):
    """Looks like an openai APIStatusError: it has status_code and body."""

    def __init__(self, status_code, body):
        super().__init__("fake error " + str(status_code))
        self.status_code = status_code
        self.body = body


def make_gemini_error(status_code, message, details=None):
    # The real Gemini format seen in the experiments: a list with one item.
    error_object = {"code": status_code, "message": message, "status": "SOME_STATUS"}

    if details is not None:
        error_object["details"] = details

    return FakeStatusError(status_code, [{"error": error_object}])


def make_timeout_error():
    # The real openai timeout error, created without its complicated __init__ (it needs a network request object).
    return openai.APITimeoutError.__new__(openai.APITimeoutError)


def make_validation_error():
    try:
        TinyAnswer(text=None)
    except ValidationError as validation_error:
        return validation_error


def make_fake_response(answer_text, model_returned):
    message = SimpleNamespace(parsed=TinyAnswer(text=answer_text), content='{"text": "' + answer_text + '"}',
                              refusal=None)
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120)

    return SimpleNamespace(model=model_returned, usage=usage, choices=[SimpleNamespace(message=message)])


def make_fake_settings():
    return {"provider": "gemini", "model": "fake-test-model", "base_url": "https://fake.example",
            "api_key": FAKE_API_KEY, "reasoning_effort": "", "daily_limit": 500, "daily_limit_margin": 20,
            "timeout_seconds": 30}


class FakeWorld:
    """A fake AI with planned results, and a fake clock. Each request takes request_seconds on the fake clock."""

    def __init__(self, planned_results, request_seconds):
        self.planned_results = list(planned_results)
        self.request_seconds = request_seconds
        self.clock_seconds = 1000.0
        self.call_count = 0
        self.waits = []

    def call_ai(self, settings, prompt_text, schema):
        self.call_count = self.call_count + 1
        self.clock_seconds = self.clock_seconds + self.request_seconds
        planned_result = self.planned_results.pop(0)

        if isinstance(planned_result, Exception):
            raise planned_result

        return planned_result

    def monotonic_seconds(self):
        return self.clock_seconds

    def wait_seconds(self, seconds):
        self.waits.append(seconds)
        self.clock_seconds = self.clock_seconds + seconds


@pytest.fixture
def log_path(tmp_path, monkeypatch):
    temporary_log_path = tmp_path / "ai_log.jsonl"
    monkeypatch.setattr(llm, "LOG_PATH", temporary_log_path)

    return temporary_log_path


def install_fake_world(monkeypatch, planned_results, request_seconds):
    fake_world = FakeWorld(planned_results, request_seconds)
    monkeypatch.setattr(llm, "call_ai", fake_world.call_ai)
    monkeypatch.setattr(llm, "monotonic_seconds", fake_world.monotonic_seconds)
    monkeypatch.setattr(llm, "wait_seconds", fake_world.wait_seconds)

    return fake_world


def read_log_lines(log_path):
    log_lines = []

    for log_text in log_path.read_text(encoding="utf-8").splitlines():
        log_lines.append(json.loads(log_text))

    return log_lines


def ask_tiny_question():
    return llm.ask("Say hi", "tiny@000000", TinyAnswer, make_fake_settings())


# ---------- ask(): success and bad answers ----------

def test_a_good_answer_is_returned_and_logged(log_path, monkeypatch):
    fake_world = install_fake_world(monkeypatch, [make_fake_response("hi", "fake-test-model")], 1)

    parsed_answer, model_returned = ask_tiny_question()

    assert parsed_answer.text == "hi"
    assert model_returned == "fake-test-model"
    assert fake_world.call_count == 1

    log_lines = read_log_lines(log_path)

    assert len(log_lines) == 1
    assert log_lines[0]["outcome"] == "ok"
    assert log_lines[0]["prompt_version"] == "tiny@000000"
    assert log_lines[0]["schema_name"] == "TinyAnswer"
    assert log_lines[0]["prompt_tokens"] == 100
    assert log_lines[0]["answer_tokens"] == 20
    assert log_lines[0]["total_tokens"] == 120


def test_a_bad_answer_is_retried_once(log_path, monkeypatch):
    planned_results = [make_validation_error(), make_fake_response("hi", "fake-test-model")]
    fake_world = install_fake_world(monkeypatch, planned_results, 1)

    parsed_answer, model_returned = ask_tiny_question()

    assert parsed_answer.text == "hi"
    assert fake_world.call_count == 2
    assert fake_world.waits == []


def test_two_bad_answers_raise_ai_invalid_answer(log_path, monkeypatch):
    fake_world = install_fake_world(monkeypatch, [make_validation_error(), make_validation_error()], 1)

    with pytest.raises(llm.AIInvalidAnswerError):
        ask_tiny_question()

    assert fake_world.call_count == 2
    assert len(read_log_lines(log_path)) == 2


def test_an_answer_without_a_parsed_object_counts_as_a_bad_answer(log_path, monkeypatch):
    refused_response = make_fake_response("hi", "fake-test-model")
    refused_response.choices[0].message.parsed = None
    fake_world = install_fake_world(monkeypatch, [refused_response, make_fake_response("hi", "fake-test-model")], 1)

    ask_tiny_question()

    assert fake_world.call_count == 2
    assert read_log_lines(log_path)[0]["outcome"] == "invalid_answer"


# ---------- ask(): busy (429 / 503) ----------

def test_busy_twice_then_ok_waits_2_then_4_seconds(log_path, monkeypatch):
    planned_results = [make_gemini_error(429, "Too many requests"), make_gemini_error(429, "Too many requests"),
                       make_fake_response("hi", "fake-test-model")]
    fake_world = install_fake_world(monkeypatch, planned_results, 1)

    parsed_answer, model_returned = ask_tiny_question()

    assert parsed_answer.text == "hi"
    assert fake_world.waits == [2, 4]
    assert len(read_log_lines(log_path)) == 3


def test_busy_three_times_raises_ai_unavailable_after_2_retries(log_path, monkeypatch):
    planned_results = [make_gemini_error(429, "Too many requests")] * 3
    fake_world = install_fake_world(monkeypatch, planned_results, 1)

    with pytest.raises(llm.AIUnavailableError):
        ask_tiny_question()

    assert fake_world.call_count == 3
    assert fake_world.waits == [2, 4]


def test_a_503_high_demand_is_retried_like_a_429(log_path, monkeypatch):
    planned_results = [make_gemini_error(503, "This model is currently experiencing high demand."),
                       make_fake_response("hi", "fake-test-model")]
    fake_world = install_fake_world(monkeypatch, planned_results, 1)

    ask_tiny_question()

    assert fake_world.call_count == 2
    assert fake_world.waits == [2]


def test_a_daily_quota_429_stops_at_once(log_path, monkeypatch):
    daily_quota_error = make_gemini_error(429, "Quota exceeded for GenerateRequestsPerDayPerProjectPerModel")
    fake_world = install_fake_world(monkeypatch, [daily_quota_error], 1)

    with pytest.raises(llm.AIDailyLimitError):
        ask_tiny_question()

    assert fake_world.call_count == 1
    assert fake_world.waits == []


def test_a_short_retry_delay_from_the_body_is_used(log_path, monkeypatch):
    retry_info = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "5s"}]
    planned_results = [make_gemini_error(429, "Too many requests", retry_info), make_fake_response("hi", "m")]
    fake_world = install_fake_world(monkeypatch, planned_results, 1)

    ask_tiny_question()

    assert fake_world.waits == [5.0]


def test_a_long_retry_delay_stops_and_says_how_long_to_wait(log_path, monkeypatch):
    retry_info = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "14.2s"}]
    fake_world = install_fake_world(monkeypatch, [make_gemini_error(429, "Too many requests", retry_info)], 1)

    with pytest.raises(llm.AIUnavailableError) as error_information:
        ask_tiny_question()

    assert error_information.value.retry_after_seconds == 15
    assert "15 seconds" in str(error_information.value)
    assert fake_world.waits == []


def test_the_20_second_budget_stops_the_retries(log_path, monkeypatch):
    # The first request takes 19 s on the fake clock: 19 + a 2 s wait is more than 20 s, so no wait and no retry.
    fake_world = install_fake_world(monkeypatch, [make_gemini_error(503, "high demand")], 19)

    with pytest.raises(llm.AIUnavailableError):
        ask_tiny_question()

    assert fake_world.call_count == 1
    assert fake_world.waits == []


# ---------- ask(): errors that are never retried ----------

def test_a_timeout_is_not_retried(log_path, monkeypatch):
    fake_world = install_fake_world(monkeypatch, [make_timeout_error()], 30)

    with pytest.raises(llm.AIUnavailableError, match="did not answer in 30 seconds"):
        ask_tiny_question()

    assert fake_world.call_count == 1
    assert read_log_lines(log_path)[0]["outcome"] == "timeout"


def test_a_wrong_key_400_raises_ai_configuration_error(log_path, monkeypatch):
    fake_world = install_fake_world(monkeypatch, [make_gemini_error(400, "Please pass a valid API key")], 1)

    with pytest.raises(llm.AIConfigurationError, match="Check your key and model in .env"):
        ask_tiny_question()

    assert fake_world.call_count == 1


def test_another_400_raises_ai_request_rejected(log_path, monkeypatch):
    fake_world = install_fake_world(monkeypatch, [make_gemini_error(400, "Invalid JSON schema")], 1)

    with pytest.raises(llm.AIRequestRejectedError, match="Google refused"):
        ask_tiny_question()

    assert fake_world.call_count == 1


def test_a_wrong_model_404_raises_ai_configuration_error(log_path, monkeypatch):
    install_fake_world(monkeypatch, [make_gemini_error(404, "models/x is not found")], 1)

    with pytest.raises(llm.AIConfigurationError):
        ask_tiny_question()


def test_an_unreadable_error_becomes_ai_unavailable_with_the_body_in_the_log(log_path, monkeypatch):
    install_fake_world(monkeypatch, [FakeStatusError(500, "<html>strange body</html>")], 1)

    with pytest.raises(llm.AIUnavailableError):
        ask_tiny_question()

    assert "strange body" in read_log_lines(log_path)[0]["error_body"]


# ---------- the key and the log ----------

def test_the_api_key_is_never_written_to_the_log(log_path, monkeypatch):
    planned_results = [make_validation_error(), make_gemini_error(503, "high demand"),
                       make_fake_response("hi", "fake-test-model")]
    install_fake_world(monkeypatch, planned_results, 1)

    ask_tiny_question()

    assert FAKE_API_KEY not in log_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("model_returned, expected_mismatch", [
    ("fake-test-model", False),
    ("models/fake-test-model", False),
    ("another-model", True),
])
def test_the_log_marks_a_model_mismatch(log_path, monkeypatch, model_returned, expected_mismatch):
    install_fake_world(monkeypatch, [make_fake_response("hi", model_returned)], 1)

    ask_tiny_question()

    assert read_log_lines(log_path)[0]["model_mismatch"] is expected_mismatch


# ---------- daily limit and counter ----------

def write_fake_log_line(log_path, model, request_time):
    log_line = {"time_utc": request_time.isoformat(timespec="seconds"), "model_asked": model, "outcome": "ok"}

    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(log_line) + "\n")


def test_ask_stops_before_sending_when_the_limit_minus_the_margin_is_reached(log_path, monkeypatch):
    now = datetime.now(timezone.utc)

    for request_number in range(8):
        write_fake_log_line(log_path, "fake-test-model", now)

    settings = make_fake_settings()
    settings["daily_limit"] = 10
    settings["daily_limit_margin"] = 2
    fake_world = install_fake_world(monkeypatch, [make_fake_response("hi", "fake-test-model")], 1)

    with pytest.raises(llm.AIDailyLimitError):
        llm.ask("Say hi", "tiny@000000", TinyAnswer, settings)

    assert fake_world.call_count == 0


def test_the_counter_day_starts_at_midnight_in_los_angeles_in_winter(log_path):
    # 16 November: Los Angeles is UTC-8, so its midnight is 08:00 UTC.
    write_fake_log_line(log_path, "m", datetime(2026, 11, 16, 7, 59, tzinfo=timezone.utc))
    write_fake_log_line(log_path, "m", datetime(2026, 11, 16, 8, 1, tzinfo=timezone.utc))

    request_count = llm.count_requests_today("m", datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc))

    assert request_count == 1


def test_the_counter_day_starts_at_midnight_in_los_angeles_in_summer(log_path):
    # 1 July: Los Angeles is UTC-7 (summer time), so its midnight is 07:00 UTC.
    write_fake_log_line(log_path, "m", datetime(2026, 7, 1, 6, 59, tzinfo=timezone.utc))
    write_fake_log_line(log_path, "m", datetime(2026, 7, 1, 7, 1, tzinfo=timezone.utc))

    request_count = llm.count_requests_today("m", datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc))

    assert request_count == 1


def test_the_counter_counts_only_one_model_and_skips_broken_lines(log_path):
    now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
    write_fake_log_line(log_path, "lite", now - timedelta(minutes=5))
    write_fake_log_line(log_path, "flash", now - timedelta(minutes=5))

    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("this is not json\n")

    assert llm.count_requests_today("lite", now) == 1


def test_the_counter_counts_failed_requests_too(log_path, monkeypatch):
    planned_results = [make_gemini_error(503, "high demand"), make_fake_response("hi", "fake-test-model")]
    install_fake_world(monkeypatch, planned_results, 1)

    ask_tiny_question()

    assert llm.count_requests_today("fake-test-model") == 2


def test_the_counter_is_zero_without_a_log_file(log_path):
    assert llm.count_requests_today("m") == 0


# ---------- reading error bodies ----------

def test_read_error_details_accepts_the_gemini_list_format():
    body = [{"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}}]

    error_details = llm.read_error_details(body)

    assert error_details["code"] == 503
    assert error_details["status"] == "UNAVAILABLE"
    assert error_details["message"] == "high demand"


def test_read_error_details_accepts_a_plain_dict_format():
    body = {"error": {"code": 429, "message": "Too many requests", "status": "RESOURCE_EXHAUSTED"}}

    error_details = llm.read_error_details(body)

    assert error_details["code"] == 429
    assert error_details["message"] == "Too many requests"


@pytest.mark.parametrize("unreadable_body", [None, 42, "plain text", [], [None], {"error": "only a string"},
                                             [{"error": {"message": None, "details": "not a list"}}]])
def test_read_error_details_never_crashes(unreadable_body):
    error_details = llm.read_error_details(unreadable_body)

    assert error_details["retry_delay_seconds"] is None


def test_read_error_details_finds_the_retry_delay_in_the_message():
    body = [{"error": {"code": 429, "message": "Quota exceeded. Please retry in 12.5s.", "status": "X"}}]

    assert llm.read_error_details(body)["retry_delay_seconds"] == 12.5


# ---------- settings ----------

def set_fake_environment(monkeypatch, environment_values):
    # load_dotenv is replaced, so the real .env (with the real key) is never read in tests.
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)

    for setting_name in ["AI_PROVIDER", "AI_MODEL", "AI_BASE_URL", "AI_API_KEY", "AI_REASONING_EFFORT",
                         "AI_DAILY_LIMIT", "AI_DAILY_LIMIT_MARGIN", "AI_TIMEOUT_SECONDS"]:
        monkeypatch.delenv(setting_name, raising=False)

    for setting_name, setting_value in environment_values.items():
        monkeypatch.setenv(setting_name, setting_value)


def test_read_ai_settings_uses_the_defaults(monkeypatch):
    set_fake_environment(monkeypatch, {"AI_MODEL": "m", "AI_BASE_URL": "https://fake.example",
                                       "AI_API_KEY": FAKE_API_KEY, "AI_DAILY_LIMIT": "500"})

    settings = llm.read_ai_settings()

    assert settings["daily_limit"] == 500
    assert settings["daily_limit_margin"] == 20
    assert settings["timeout_seconds"] == 30
    assert settings["reasoning_effort"] == ""


def test_read_ai_settings_without_a_key_raises_ai_configuration_error(monkeypatch):
    set_fake_environment(monkeypatch, {"AI_MODEL": "m", "AI_BASE_URL": "https://fake.example",
                                       "AI_DAILY_LIMIT": "500"})

    with pytest.raises(llm.AIConfigurationError, match="AI_API_KEY"):
        llm.read_ai_settings()


def test_read_ai_settings_needs_a_daily_limit(monkeypatch):
    set_fake_environment(monkeypatch, {"AI_MODEL": "m", "AI_BASE_URL": "https://fake.example",
                                       "AI_API_KEY": FAKE_API_KEY})

    with pytest.raises(llm.AIConfigurationError, match="AI_DAILY_LIMIT"):
        llm.read_ai_settings()


def test_reasoning_effort_is_sent_only_when_it_is_set():
    settings = make_fake_settings()

    options_without_effort = llm.build_request_options(settings, "Say hi", TinyAnswer)
    settings["reasoning_effort"] = "low"
    options_with_effort = llm.build_request_options(settings, "Say hi", TinyAnswer)

    assert "reasoning_effort" not in options_without_effort
    assert options_with_effort["reasoning_effort"] == "low"
