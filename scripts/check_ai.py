"""Step 0 check: send one English question to the AI and print the answer.

Run it with:  python scripts/check_ai.py
It reads the settings from .env, and it never prints your key.
"""

import os
import sys

from dotenv import load_dotenv
from openai import NotFoundError, OpenAI


def read_settings():
    load_dotenv()

    settings = {
        "AI_PROVIDER": os.getenv("AI_PROVIDER", ""),
        "AI_MODEL": os.getenv("AI_MODEL", ""),
        "AI_BASE_URL": os.getenv("AI_BASE_URL", ""),
        "AI_API_KEY": os.getenv("AI_API_KEY", ""),
    }

    return settings


def find_missing_settings(settings):
    missing_setting_names = []

    for setting_name, setting_value in settings.items():
        if setting_value.strip() == "":
            missing_setting_names.append(setting_name)

    return missing_setting_names


def create_ai_client(settings):
    # OpenAI() only accepts these arguments by name, so here the names are required.
    return OpenAI(base_url=settings["AI_BASE_URL"], api_key=settings["AI_API_KEY"])


def list_flash_model_names(settings):
    ai_client = create_ai_client(settings)
    flash_model_names = []

    for model in ai_client.models.list():
        model_name = model.id.removeprefix("models/")

        if "flash" in model_name:
            flash_model_names.append(model_name)

    return sorted(flash_model_names)


def ask_one_question(settings, question_text):
    ai_client = create_ai_client(settings)

    response = ai_client.chat.completions.create(
        model=settings["AI_MODEL"], messages=[{"role": "user", "content": question_text}]
    )

    return response.choices[0].message.content


def main():
    settings = read_settings()
    missing_setting_names = find_missing_settings(settings)

    if missing_setting_names:
        print("These settings are empty in .env:", ", ".join(missing_setting_names))
        print("Copy .env.example to .env and fill them in.")
        sys.exit(1)

    question_text = "Is 'I have 25 years' correct English? Answer in two short sentences."

    print("Provider:", settings["AI_PROVIDER"], "| Model:", settings["AI_MODEL"])
    print("Question:", question_text)
    print()

    try:
        answer_text = ask_one_question(settings, question_text)
    except NotFoundError:
        print("The model", settings["AI_MODEL"], "does not exist for this key.")
        print("Flash models your key can use (write one of them in AI_MODEL in .env):")

        for model_name in list_flash_model_names(settings):
            print("  ", model_name)

        sys.exit(1)
    except Exception as error:
        print("The AI call failed:", type(error).__name__)
        print(error)
        sys.exit(1)

    print("Answer:", answer_text)
    print()
    print("The key works.")


if __name__ == "__main__":
    main()
