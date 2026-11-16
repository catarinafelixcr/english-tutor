"""Part 4 experiments: real calls to the Gemini API, to learn how it behaves BEFORE writing tutor/llm.py.

Run ONE experiment at a time, from the project folder:
    python -m scripts.part4_experiments E1

E1  parse() with GapExercise                        Lite, 1 request
E2  skill_id as an enum of the 49 fill-the-gap ids  Lite, 1 request
E3  the model name Gemini returns                   shown by E1, E2 and E4 (no extra request)
E4  reasoning_effort="low" vs default, 3 + 3        Lite, 6 requests
E5  429: 6 requests at the same time                gemini-3.8-flash, 6 of its 20 daily requests (none of Lite's)
E6  a wrong key                                     no quota used
E7  a wrong model name                              no quota used

The key is read from .env and never printed.

A record of Step 1, not meant to run again: since Step 2, GapExercise needs a "signal" field that this
frozen prompt does not ask for, so E1, E2 and E4 would now get invalid answers.
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import create_model

from tutor import prompts, skills
from tutor.schemas import GapExercise

TIMEOUT_SECONDS = 60
FLASH_MODEL_FOR_THE_429_EXPERIMENT = "gemini-3.8-flash"
NUMBER_OF_REQUESTS_FOR_THE_429_EXPERIMENT = 6

# A frozen copy of the Step 1 prompt, as it was when E1-E4 ran (the AI chose the skill from a list).
# tutor/prompts.py has a new prompt with ONE skill (Part 5); this copy keeps the experiments a true record.
OLD_GAP_EXERCISE_TEMPLATE = """You are an English teacher. The learner is a Portuguese speaker from Portugal.

Write ONE fill-the-gap exercise in English.

Level (CEFR): {level}
Topic of the sentence: {topic}

Rules:
- The sentence has exactly one gap, written as ___ (three underscores). Do not use underscores anywhere else.
- The gap tests ONE skill from the list below. Choose skill_id only from this list. Never invent a skill.
- Use the "typical mistake" and "tag when" columns to choose the right skill.
- Only one idea must fit the gap, so the learner can find it. When the skill is about a verb form,
  write the base verb in brackets after the gap, for example: She ___ (work) in a bank.
- expected_answer: the word or words that fill the gap.
- accepted_answers: other answers a native speaker would also accept. Use an empty list if there are none.
- hint: a short clue that helps but does not give the answer.
- level: {level}

Skills (id | name | level | typical mistake | tag when):
{skill_list}
"""


def build_old_gap_exercise_prompt(level, topic, skill_list):
    skill_list_text = skills.skills_as_prompt_text(skill_list)
    prompt_text = OLD_GAP_EXERCISE_TEMPLATE.format(level=level, topic=topic, skill_list=skill_list_text)
    prompt_version = prompts.make_prompt_version("gap_exercise", OLD_GAP_EXERCISE_TEMPLATE)

    return prompt_text, prompt_version


# ---------- settings and client ----------

def read_settings():
    load_dotenv()

    settings = {
        "AI_MODEL": os.getenv("AI_MODEL", ""),
        "AI_BASE_URL": os.getenv("AI_BASE_URL", ""),
        "AI_API_KEY": os.getenv("AI_API_KEY", ""),
    }

    return settings


def create_client(settings, api_key):
    # max_retries=0: the openai client must not retry by itself (we want to see every error).
    # OpenAI() only accepts these arguments by name.
    return OpenAI(base_url=settings["AI_BASE_URL"], api_key=api_key, max_retries=0, timeout=TIMEOUT_SECONDS)


def make_gap_exercise_schema_with_skill_enum():
    # Same as GapExercise, but skill_id can only be one of the fill-the-gap ids (an "enum" in the JSON schema).
    # The validators of GapExercise are kept, because this class is built on top of it.
    fill_the_gap_skill_ids = tuple(skills.get_fill_the_gap_skill_ids())

    return create_model("GapExerciseWithSkillEnum", __base__=GapExercise,
                        skill_id=(Literal[fill_the_gap_skill_ids], ...))


# ---------- printing ----------

def print_error(error):
    print("  Error type :", type(error).__name__)
    print("  Status code:", getattr(error, "status_code", None))
    print("  Body       :", getattr(error, "body", None))

    error_response = getattr(error, "response", None)

    if error_response is not None:
        print("  retry-after header:", error_response.headers.get("retry-after"))

    if getattr(error, "body", None) is None:
        print("  Message    :", error)


def print_usage(response):
    if response.usage is None:
        print("  Tokens     : not returned")
        return

    print("  Tokens     : prompt", response.usage.prompt_tokens, "| answer", response.usage.completion_tokens,
          "| total", response.usage.total_tokens)


def print_gap_exercise_result(response, seconds_taken):
    message = response.choices[0].message

    print("  Model returned:", response.model)
    print("  Seconds       :", round(seconds_taken, 1))
    print_usage(response)
    print("  Refusal       :", message.refusal)
    print("  Raw answer    :", message.content)
    print("  Parsed object :", message.parsed)


# ---------- one request ----------

def ask_for_one_gap_exercise(client, model, schema, reasoning_effort):
    prompt_text, prompt_version = build_old_gap_exercise_prompt("A2", "daily life",
                                                                skills.get_fill_the_gap_skills_up_to_level("A2"))
    request_options = {"model": model, "messages": [{"role": "user", "content": prompt_text}],
                       "response_format": schema}

    if reasoning_effort is not None:
        request_options["reasoning_effort"] = reasoning_effort

    start_time = time.perf_counter()
    response = client.chat.completions.parse(**request_options)
    seconds_taken = time.perf_counter() - start_time

    return response, seconds_taken


# ---------- experiments ----------

def run_e1_parse_with_gap_exercise(settings):
    client = create_client(settings, settings["AI_API_KEY"])

    try:
        response, seconds_taken = ask_for_one_gap_exercise(client, settings["AI_MODEL"], GapExercise, None)
    except Exception as error:
        print_error(error)
        return

    print_gap_exercise_result(response, seconds_taken)


def run_e2_skill_id_as_enum(settings):
    schema_with_enum = make_gap_exercise_schema_with_skill_enum()
    skill_id_schema = schema_with_enum.model_json_schema()["properties"]["skill_id"]
    print("  Enum values in the schema:", len(skill_id_schema.get("enum", [])))

    client = create_client(settings, settings["AI_API_KEY"])

    try:
        response, seconds_taken = ask_for_one_gap_exercise(client, settings["AI_MODEL"], schema_with_enum, None)
    except Exception as error:
        print_error(error)
        return

    print_gap_exercise_result(response, seconds_taken)


def run_e4_reasoning_effort(settings):
    client = create_client(settings, settings["AI_API_KEY"])

    # alternate the two settings, so a slow minute does not hurt only one of them
    reasoning_effort_order = [None, "low", None, "low", None, "low"]
    seconds_by_setting = {"default": [], "low": []}

    for request_number, reasoning_effort in enumerate(reasoning_effort_order, start=1):
        setting_name = reasoning_effort or "default"

        try:
            response, seconds_taken = ask_for_one_gap_exercise(client, settings["AI_MODEL"], GapExercise,
                                                               reasoning_effort)
        except Exception as error:
            print("  Request", request_number, "(" + setting_name + ") failed:")
            print_error(error)
            continue

        seconds_by_setting[setting_name].append(seconds_taken)
        answer_tokens = response.usage.completion_tokens if response.usage else None
        print("  Request", request_number, "(" + setting_name + "):", round(seconds_taken, 1), "s,",
              "answer tokens:", answer_tokens, "| model returned:", response.model)

    for setting_name, seconds_list in seconds_by_setting.items():
        if seconds_list:
            average_seconds = sum(seconds_list) / len(seconds_list)
            print("  Average", setting_name + ":", round(average_seconds, 1), "s over", len(seconds_list), "requests")


def send_one_tiny_flash_request(client, request_number):
    start_time = time.perf_counter()

    try:
        client.chat.completions.create(model=FLASH_MODEL_FOR_THE_429_EXPERIMENT,
                                       messages=[{"role": "user", "content": "Answer with one word: OK"}])
    except Exception as error:
        return request_number, time.perf_counter() - start_time, error

    return request_number, time.perf_counter() - start_time, None


def run_e5_rate_limit(settings):
    client = create_client(settings, settings["AI_API_KEY"])
    request_numbers = range(1, NUMBER_OF_REQUESTS_FOR_THE_429_EXPERIMENT + 1)

    # all requests at the same time, so they arrive in the same minute (the limit is 5 per minute)
    with ThreadPoolExecutor(NUMBER_OF_REQUESTS_FOR_THE_429_EXPERIMENT) as executor:
        results = list(executor.map(lambda request_number: send_one_tiny_flash_request(client, request_number),
                                    request_numbers))

    for request_number, seconds_taken, error in results:
        if error is None:
            print("  Request", request_number, ": OK in", round(seconds_taken, 1), "s")
            continue

        print("  Request", request_number, ": FAILED after", round(seconds_taken, 1), "s")
        print_error(error)


def run_e6_wrong_key(settings):
    client = create_client(settings, "this-is-not-a-real-key")

    try:
        client.chat.completions.create(model=settings["AI_MODEL"], messages=[{"role": "user", "content": "Hi"}])
    except Exception as error:
        print_error(error)
        return

    print("  Unexpected: the request worked with a wrong key.")


def run_e7_wrong_model(settings):
    client = create_client(settings, settings["AI_API_KEY"])

    try:
        client.chat.completions.create(model="gemini-model-that-does-not-exist",
                                       messages=[{"role": "user", "content": "Hi"}])
    except Exception as error:
        print_error(error)
        return

    print("  Unexpected: the request worked with a wrong model name.")


EXPERIMENTS = {
    "E1": run_e1_parse_with_gap_exercise,
    "E2": run_e2_skill_id_as_enum,
    "E4": run_e4_reasoning_effort,
    "E5": run_e5_rate_limit,
    "E6": run_e6_wrong_key,
    "E7": run_e7_wrong_model,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1].upper() not in EXPERIMENTS:
        print("Choose one experiment:", ", ".join(EXPERIMENTS), "  (E3 is shown inside E1, E2 and E4)")
        sys.exit(1)

    settings = read_settings()

    for setting_name, setting_value in settings.items():
        if setting_value.strip() == "":
            print("This setting is empty in .env:", setting_name)
            sys.exit(1)

    experiment_name = sys.argv[1].upper()
    model_used = settings["AI_MODEL"]

    if experiment_name == "E5":
        model_used = FLASH_MODEL_FOR_THE_429_EXPERIMENT

    print("Running", experiment_name, "with model", model_used)
    EXPERIMENTS[experiment_name](settings)


if __name__ == "__main__":
    main()
