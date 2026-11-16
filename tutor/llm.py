"""The only file that talks to the AI. It sends a prompt and returns a validated Pydantic object.

Main function: ask(prompt_text, prompt_version, schema) -> (validated object, model returned)

Rules (PLAN.md, Step 1, and the experiments in JOURNAL.md):
- The openai client never retries by itself (max_retries=0): every request sent is ours, logged and counted.
- One line in logs/ai_log.jsonl per request sent, also for failed ones (failed requests use quota too).
- A bad answer is retried once. A 429 or 503 is retried at most 2 times, inside a budget of about 20 seconds.
- Timeouts, wrong settings and refused requests are never retried.
- The API key is never written to the log.
"""

import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import openai
from dotenv import load_dotenv
from pydantic import ValidationError

PROJECT_FOLDER = Path(__file__).resolve().parent.parent
LOG_PATH = PROJECT_FOLDER / "logs" / "ai_log.jsonl"

# Gemini resets the requests-per-day quota at midnight Pacific time.
QUOTA_TIME_ZONE = ZoneInfo("America/Los_Angeles")

MAX_INVALID_ANSWER_RETRIES = 1
MAX_BUSY_RETRIES = 2
BUSY_RETRY_WAITS_SECONDS = [2, 4]
LONGEST_WAIT_SECONDS = 10
RETRY_BUDGET_SECONDS = 20

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_DAILY_LIMIT_MARGIN = 20

# Words that show a 429 is about the DAILY quota (from Google's docs; the real body is not known yet).
DAILY_QUOTA_WORDS = ["perday", "per day", "quota_exceeded", "daily"]


# ---------- errors that pages can show ----------

class AIError(Exception):
    """Every AI error has a friendly message that a page can show."""


class AIConfigurationError(AIError):
    """Wrong or missing key, model or settings in .env."""


class AIDailyLimitError(AIError):
    """No more requests today (our counter, or Google's daily quota)."""


class AIUnavailableError(AIError):
    """The AI did not answer now. Trying again later can work."""

    def __init__(self, message, retry_after_seconds=None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AIRequestRejectedError(AIError):
    """Google refused the request itself. Trying again will not fix it: the code must change."""


class AIInvalidAnswerError(AIError):
    """The AI answered twice, but both answers broke the schema rules."""


class AnswerNotParsedError(Exception):
    """Internal: the response came back, but without a parsed object (for example a refusal)."""


# ---------- settings ----------

def read_ai_settings():
    # Reads .env. Never prints or logs the key.
    load_dotenv()

    settings = {
        "provider": os.getenv("AI_PROVIDER", "").strip(),
        "model": os.getenv("AI_MODEL", "").strip(),
        "base_url": os.getenv("AI_BASE_URL", "").strip(),
        "api_key": os.getenv("AI_API_KEY", "").strip(),
        "reasoning_effort": os.getenv("AI_REASONING_EFFORT", "").strip(),
    }

    missing_setting_names = []

    for setting_name in ["model", "base_url", "api_key"]:
        if settings[setting_name] == "":
            missing_setting_names.append("AI_" + setting_name.upper())

    if missing_setting_names:
        raise AIConfigurationError("These settings are empty: " + ", ".join(missing_setting_names)
                                   + ". Check your key and model in .env.")

    settings["daily_limit"] = read_number_setting("AI_DAILY_LIMIT", None)
    settings["daily_limit_margin"] = read_number_setting("AI_DAILY_LIMIT_MARGIN", DEFAULT_DAILY_LIMIT_MARGIN)
    settings["timeout_seconds"] = read_number_setting("AI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)

    return settings


def read_number_setting(setting_name, default_value):
    setting_text = os.getenv(setting_name, "").strip()

    if setting_text == "" and default_value is not None:
        return default_value

    if not setting_text.isdigit():
        raise AIConfigurationError(setting_name + " in .env must be a whole number, for example 500.")

    return int(setting_text)


# ---------- the network call (the only place that uses the internet) ----------

def build_request_options(settings, prompt_text, schema):
    request_options = {"model": settings["model"], "messages": [{"role": "user", "content": prompt_text}],
                       "response_format": schema}

    if settings["reasoning_effort"] != "":
        request_options["reasoning_effort"] = settings["reasoning_effort"]

    return request_options


def call_ai(settings, prompt_text, schema):
    # Tests replace this function with a fake AI, so they never use the internet or the quota.
    # max_retries=0: the openai client must never retry by itself. OpenAI() only accepts these arguments by name.
    client = openai.OpenAI(base_url=settings["base_url"], api_key=settings["api_key"], max_retries=0,
                           timeout=settings["timeout_seconds"])

    return client.chat.completions.parse(**build_request_options(settings, prompt_text, schema))


def read_parsed_answer(response):
    message = response.choices[0].message

    if message.parsed is None:
        raise AnswerNotParsedError("no parsed answer (refusal: " + str(message.refusal) + ")")

    return message.parsed


# ---------- clock (tests replace these two, so they never really wait) ----------

def monotonic_seconds():
    return time.monotonic()


def wait_seconds(seconds):
    time.sleep(seconds)


# ---------- reading error bodies (must never crash) ----------

def find_error_object(body):
    # Gemini sends [{"error": {...}}] (seen in the experiments). Others send {"error": {...}} or a plain dict.
    if isinstance(body, list):
        if len(body) == 0:
            return None

        body = body[0]

    if not isinstance(body, dict):
        return None

    if isinstance(body.get("error"), dict):
        return body["error"]

    return body


def read_retry_delay_seconds(error_object, message):
    # 1) Google's RetryInfo detail: {"@type": "...RetryInfo", "retryDelay": "37s"}
    for detail in error_object.get("details") or []:
        if isinstance(detail, dict) and "retryDelay" in detail:
            delay_match = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(detail["retryDelay"]).strip())

            if delay_match:
                return float(delay_match.group(1))

    # 2) The same information inside the message: "Please retry in 12.5s."
    message_match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", message, re.IGNORECASE)

    if message_match:
        return float(message_match.group(1))

    return None


def read_error_details(body):
    # Returns code, status, message and retry_delay_seconds. Never raises: an unreadable body gives empty details.
    error_details = {"code": None, "status": None, "message": "", "retry_delay_seconds": None}

    try:
        error_object = find_error_object(body)

        if error_object is None:
            return error_details

        error_details["code"] = error_object.get("code")
        error_details["status"] = error_object.get("status")
        error_details["message"] = str(error_object.get("message") or "")
        error_details["retry_delay_seconds"] = read_retry_delay_seconds(error_object, error_details["message"])
    except Exception:
        return {"code": None, "status": None, "message": "", "retry_delay_seconds": None}

    return error_details


def is_daily_quota_error(body):
    body_text = str(body).lower()

    for daily_quota_word in DAILY_QUOTA_WORDS:
        if daily_quota_word in body_text:
            return True

    return False


def classify_error(error):
    # Returns one of: invalid_answer, timeout, connection, configuration, rejected, daily_quota, busy, unknown.
    if isinstance(error, (ValidationError, AnswerNotParsedError, json.JSONDecodeError, openai.LengthFinishReasonError,
                          openai.ContentFilterFinishReasonError)):
        return "invalid_answer"

    # APITimeoutError is a kind of APIConnectionError, so it must be checked first.
    if isinstance(error, openai.APITimeoutError):
        return "timeout"

    if isinstance(error, openai.APIConnectionError):
        return "connection"

    status_code = getattr(error, "status_code", None)
    error_body = getattr(error, "body", None)

    if status_code in [401, 403, 404]:
        return "configuration"

    if status_code == 400:
        error_message = read_error_details(error_body)["message"].lower()

        if "api key" in error_message:
            return "configuration"

        return "rejected"

    if status_code == 429:
        if is_daily_quota_error(error_body):
            return "daily_quota"

        return "busy"

    if status_code == 503:
        return "busy"

    return "unknown"


# ---------- log ----------

def remove_models_prefix(model_name):
    if model_name is None:
        return None

    return model_name.removeprefix("models/")


def make_log_line(settings, request_info, outcome, seconds_taken, response, error):
    # Builds the log values by hand from safe fields only: the settings dict (with the key) is never dumped.
    model_returned = getattr(response, "model", None)
    usage = getattr(response, "usage", None)
    answer_text = None

    if response is not None:
        answer_text = response.choices[0].message.content

    error_body = None

    if error is not None:
        error_body = getattr(error, "body", None) or str(error)

    log_line = {
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": settings["provider"],
        "model_asked": settings["model"],
        "model_returned": model_returned,
        "model_mismatch": model_returned is not None
                          and remove_models_prefix(model_returned) != remove_models_prefix(settings["model"]),
        "prompt_version": request_info["prompt_version"],
        "schema_name": request_info["schema_name"],
        "attempt_number": request_info["attempt_number"],
        "outcome": outcome,
        "seconds": round(seconds_taken, 2),
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "answer_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "prompt": request_info["prompt_text"],
        "answer_text": answer_text,
        "error_type": type(error).__name__ if error is not None else None,
        "error_status": getattr(error, "status_code", None),
        "error_body": error_body,
    }

    return log_line


def write_log_line(log_line):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(log_line, ensure_ascii=False, default=str) + "\n")


# ---------- request counter ----------

def start_of_quota_day_in_utc(now):
    # Midnight in Los Angeles for the day of "now", written in UTC.
    local_now = now.astimezone(QUOTA_TIME_ZONE)
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    return local_midnight.astimezone(timezone.utc)


def count_requests_today(model, now=None):
    # An ESTIMATE: it only sees requests sent by this file. Broken log lines are skipped, never a crash.
    if now is None:
        now = datetime.now(timezone.utc)

    if not LOG_PATH.exists():
        return 0

    quota_day_start = start_of_quota_day_in_utc(now)
    request_count = 0

    with open(LOG_PATH, encoding="utf-8") as log_file:
        for log_text in log_file:
            try:
                log_line = json.loads(log_text)
                request_time = datetime.fromisoformat(log_line["time_utc"])
            except (ValueError, KeyError, TypeError):
                continue

            if log_line.get("model_asked") == model and request_time >= quota_day_start:
                request_count = request_count + 1

    return request_count


def stop_if_daily_limit_reached(settings):
    requests_today = count_requests_today(settings["model"])
    usable_limit = settings["daily_limit"] - settings["daily_limit_margin"]

    if requests_today >= usable_limit:
        raise AIDailyLimitError("No more AI requests today (" + str(requests_today) + " used, the app stops at "
                                  + str(usable_limit) + "). The quota resets at midnight Pacific time.")


# ---------- deciding what to do after an error ----------

def choose_busy_wait_seconds(error, busy_retry_number):
    retry_delay_seconds = read_error_details(getattr(error, "body", None))["retry_delay_seconds"]

    if retry_delay_seconds is not None:
        return retry_delay_seconds

    return BUSY_RETRY_WAITS_SECONDS[busy_retry_number - 1]


def raise_final_error(error_kind, settings, error):
    # Errors that are never retried.
    if error_kind == "configuration":
        raise AIConfigurationError("Check your key and model in .env.") from error

    if error_kind == "rejected":
        raise AIRequestRejectedError("The app sent a request Google refused. See the log (logs/ai_log.jsonl).") \
            from error

    if error_kind == "daily_quota":
        raise AIDailyLimitError("Google says the daily quota is used up. It resets at midnight Pacific time.") \
            from error

    if error_kind == "timeout":
        raise AIUnavailableError("The AI did not answer in " + str(settings["timeout_seconds"])
                            + " seconds. Try again in a moment.") from error

    if error_kind == "connection":
        raise AIUnavailableError("No connection to the AI. Check your internet.") from error

    raise AIUnavailableError("Unexpected AI error. See the log (logs/ai_log.jsonl).") from error


# ---------- the main function ----------

def ask(prompt_text, prompt_version, schema, settings=None):
    # Returns (validated object, model returned). Raises one of the AIError types above.
    if settings is None:
        settings = read_ai_settings()

    first_request_time = monotonic_seconds()
    attempt_number = 0
    invalid_answer_count = 0
    busy_retry_count = 0

    while True:
        stop_if_daily_limit_reached(settings)

        attempt_number = attempt_number + 1
        request_info = {"prompt_text": prompt_text, "prompt_version": prompt_version,
                        "schema_name": schema.__name__, "attempt_number": attempt_number}
        request_start_time = monotonic_seconds()
        response = None

        try:
            response = call_ai(settings, prompt_text, schema)
            parsed_answer = read_parsed_answer(response)
        except Exception as error:
            seconds_taken = monotonic_seconds() - request_start_time
            error_kind = classify_error(error)
            write_log_line(make_log_line(settings, request_info, error_kind, seconds_taken, response, error))

            if error_kind == "invalid_answer":
                invalid_answer_count = invalid_answer_count + 1

                if invalid_answer_count > MAX_INVALID_ANSWER_RETRIES:
                    raise AIInvalidAnswerError("The AI gave 2 invalid answers. Try again.") from error

                continue

            if error_kind != "busy":
                raise_final_error(error_kind, settings, error)

            busy_retry_count = busy_retry_count + 1

            if busy_retry_count > MAX_BUSY_RETRIES:
                raise AIUnavailableError("The AI is busy. Try again in a minute.") from error

            wait_time = choose_busy_wait_seconds(error, busy_retry_count)

            if wait_time > LONGEST_WAIT_SECONDS:
                rounded_wait = math.ceil(wait_time)
                raise AIUnavailableError("The AI is busy. Wait " + str(rounded_wait) + " seconds and try again.",
                                    rounded_wait) from error

            if monotonic_seconds() - first_request_time + wait_time > RETRY_BUDGET_SECONDS:
                raise AIUnavailableError("The AI is busy. Try again in a minute.") from error

            wait_seconds(wait_time)
            continue

        seconds_taken = monotonic_seconds() - request_start_time
        write_log_line(make_log_line(settings, request_info, "ok", seconds_taken, response, None))

        return parsed_answer, response.model
