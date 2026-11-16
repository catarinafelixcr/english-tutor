"""Practice: fill the gap (Step 2, Part 3). Fix the error and word order come in Part 5.

The page only draws (CLAUDE.md, rule 7). The logic lives in tutor/exercises.py (the next exercise, from the stock)
and tutor/grading.py (check the answer, save every row).

Streamlit runs this whole file again after every click. st.session_state is the page's memory between two runs.
The page passes db.DEFAULT_DATABASE_PATH in every call: it is read at call time, so the page test can swap it
for a temporary database.
"""

import time

import streamlit as st

from tutor import db, exercises, grading, llm, prompts, skills
from tutor.schemas import ProblemReport

# Characters that Markdown reads as formatting: "___" would become a line or bold text, "$" a math formula.
# The backslash must be first, so the backslashes we add are not escaped again.
MARKDOWN_SPECIAL_CHARACTERS = ["\\", "`", "*", "_", "$", "#", "|", "~", "[", "]", "<", ">"]

STATE_TITLES = {"correct": "Correct!", "almost": "Almost!", "partial": "Partly right", "wrong": "Not quite"}

REPORT_KIND_LABELS = {"bad_sentence": "The sentence is bad (it will not come back)",
                      "wrong_grade": "The grade is wrong"}

# The AI errors where "Try again" can help. A daily limit, a wrong key or a refused request need something else.
ERRORS_WORTH_RETRYING = (llm.AIUnavailableError, llm.AIInvalidAnswerError)

# The memory of this page, with the starting value of each key.
STARTING_MEMORY = {
    "practice_filters": None,
    "practice_answer_count": 0,
    "practice_correct_count": 0,
    # A short message for the NEXT run (after st.rerun), shown once. Kept outside EXERCISE_MEMORY on purpose:
    # it must survive forget_current_exercise().
    "practice_flash_message": "",
}

# The memory of ONE exercise on screen. forget_current_exercise() puts these values back.
EXERCISE_MEMORY = {
    "practice_exercise_id": None,
    "practice_exercise": None,
    "practice_notice": "",
    # Reserved when the exercise appears: a double click on Check can never save the answer twice.
    "practice_submission_id": None,
    "practice_shown_at": None,
    "practice_hint_used": False,
    "practice_result": None,
    "practice_already_saved": False,
    "practice_load_error": None,
    "practice_grade_error": None,
    "practice_reports_sent": [],
}


# ---------- memory between runs ----------

def start_page_memory():
    # Only the first run of the session finds the keys missing.
    for memory_key, starting_value in STARTING_MEMORY.items():
        if memory_key not in st.session_state:
            st.session_state[memory_key] = starting_value

    if "practice_exercise_id" not in st.session_state:
        forget_current_exercise()


def forget_current_exercise():
    # The exercise stays in the database: if I did not answer it, it is still in the stock.
    for memory_key, starting_value in EXERCISE_MEMORY.items():
        st.session_state[memory_key] = starting_value

    # A new list, so two exercises never share the same list object.
    st.session_state.practice_reports_sent = []


# ---------- small text helpers ----------

def escape_markdown(text):
    escaped_text = text

    for special_character in MARKDOWN_SPECIAL_CHARACTERS:
        escaped_text = escaped_text.replace(special_character, "\\" + special_character)

    return escaped_text


def get_skill_name(skill_id):
    return skills.get_skill(skill_id)["name"]


def make_skill_option_label(skill_id):
    if skill_id is None:
        return "Any skill"

    return skills.make_skill_label(skills.get_skill(skill_id))


def make_topic_option_label(topic):
    if topic is None:
        return "Any topic"

    return topic.capitalize()


def make_session_counter_text():
    answer_count = st.session_state.practice_answer_count
    correct_count = st.session_state.practice_correct_count

    if answer_count == 1:
        return "This session: 1 answer · " + str(correct_count) + " correct"

    return "This session: " + str(answer_count) + " answers · " + str(correct_count) + " correct"


# ---------- the filters ----------

def draw_filters():
    # Returns (skill id or None, level, topic or None). The skill comes first, so the level list can follow it.
    skill_options = [None]

    for skill in skills.get_fill_the_gap_skills_by_category():
        skill_options.append(skill["id"])

    skill_column, level_column, topic_column = st.columns([3, 1, 2])

    with skill_column:
        skill_id = st.selectbox("Skill", skill_options, format_func=make_skill_option_label, key="practice_skill_id")

    # With one skill: its level or higher, never lower. With any skill: every level (A2 first, the default).
    lowest_level = skills.VALID_LEVELS[0]

    if skill_id is not None:
        lowest_level = skills.get_skill(skill_id)["level"]

    level_options = skills.get_levels_from(lowest_level)

    # The level I had is now too low for the skill: it jumps to the skill's level. This must happen BEFORE the
    # selectbox is drawn (Streamlit refuses a change to a widget's value after the widget is on the page).
    if st.session_state.get("practice_level") not in level_options:
        st.session_state.practice_level = level_options[0]

    with level_column:
        level = st.selectbox("Level", level_options, key="practice_level")

    with topic_column:
        topic_options = [None] + list(exercises.TOPICS)
        topic = st.selectbox("Topic", topic_options, format_func=make_topic_option_label, key="practice_topic")

    return skill_id, level, topic


# ---------- loading the next exercise ----------

def load_next_exercise(level, skill_id, topic):
    forget_current_exercise()

    try:
        with st.spinner("Getting your next sentence..."):
            exercise_id, exercise, notice = exercises.get_next_gap_exercise(level, skill_id, topic,
                                                                            db.DEFAULT_DATABASE_PATH)
    except llm.AIError as error:
        # Only an EMPTY stock + an AI error comes here. It is shown once; "Try again" asks again.
        st.session_state.practice_load_error = error
        return

    st.session_state.practice_exercise_id = exercise_id
    st.session_state.practice_exercise = exercise
    st.session_state.practice_notice = notice
    st.session_state.practice_submission_id = db.new_submission_id()
    st.session_state.practice_shown_at = time.monotonic()


def draw_ai_error(error, extra_text):
    message = str(error)

    if isinstance(error, llm.AIUnavailableError) and error.retry_after_seconds is not None:
        message = message + " Try again in about " + str(round(error.retry_after_seconds)) + " seconds."

    st.error(message + " " + extra_text, icon=":material/cloud_off:")


def draw_load_error():
    error = st.session_state.practice_load_error
    draw_ai_error(error, "There are no saved sentences for these choices, and the AI could not create new ones now.")

    if not isinstance(error, ERRORS_WORTH_RETRYING):
        return

    if st.button("Try again", icon=":material/refresh:", key="practice_try_again_load"):
        forget_current_exercise()
        st.rerun()


# ---------- the exercise and the answer ----------

def make_exercise_caption(exercise, chosen_skill_id):
    # With "any skill", the skill name stays hidden until I answer: it would name the rule (a free hint).
    caption_parts = []
    answer_is_done = st.session_state.practice_result is not None or st.session_state.practice_already_saved

    if chosen_skill_id is not None or answer_is_done:
        caption_parts.append(get_skill_name(exercise.skill_id))

    caption_parts.append(exercise.level)

    if exercise.topic:
        caption_parts.append(exercise.topic.capitalize())

    return " · ".join(caption_parts)


def draw_exercise(chosen_skill_id):
    exercise = st.session_state.practice_exercise

    st.markdown("### " + escape_markdown(exercise.prompt_text))
    st.caption(escape_markdown(make_exercise_caption(exercise, chosen_skill_id)))

    if st.session_state.practice_notice != "":
        st.caption(":material/info: " + st.session_state.practice_notice)

    if st.session_state.practice_flash_message != "":
        st.caption(":material/done: " + st.session_state.practice_flash_message)
        st.session_state.practice_flash_message = ""


def check_answer(your_answer):
    if grading.clean_answer(your_answer) == "":
        st.warning("Type an answer first.")
        return

    st.session_state.practice_grade_error = None

    # Counted from the moment the exercise appeared. After an AI error, "Check" again keeps counting: honest time.
    seconds_taken = round(time.monotonic() - st.session_state.practice_shown_at, 1)

    try:
        with st.spinner("Checking your answer..."):
            result = grading.grade_gap_answer(st.session_state.practice_exercise_id,
                                              st.session_state.practice_exercise, your_answer,
                                              st.session_state.practice_hint_used, seconds_taken,
                                              prompts.DEFAULT_EXPLANATION_LANGUAGE, db.DEFAULT_DATABASE_PATH,
                                              st.session_state.practice_submission_id)
    except db.AnswerAlreadySavedError:
        # A rerun while the AI was grading: the first run saved it. Nothing new is saved, no request is spent.
        st.session_state.practice_already_saved = True
        st.rerun()
    except llm.AIError as error:
        # Nothing was saved. The answer stays in the box, and "Check" grades it again.
        st.session_state.practice_grade_error = error
        return

    st.session_state.practice_result = result
    st.session_state.practice_answer_count = st.session_state.practice_answer_count + 1

    if result.state == "correct":
        st.session_state.practice_correct_count = st.session_state.practice_correct_count + 1

    # Draws the page again from the top, now with the result instead of the answer box.
    st.rerun()


def draw_answer_form():
    # A form: Enter sends the answer. The key changes with each exercise, so the box starts empty.
    submission_id = st.session_state.practice_submission_id

    with st.form("practice_answer_form", border=False):
        your_answer = st.text_input("Your answer", key="practice_answer_" + submission_id,
                                    placeholder="Type the missing word(s) and press Enter")
        check_clicked = st.form_submit_button("Check", type="primary", key="practice_check")

    if check_clicked:
        check_answer(your_answer)

    grade_error = st.session_state.practice_grade_error

    if grade_error is None:
        return

    if isinstance(grade_error, ERRORS_WORTH_RETRYING):
        draw_ai_error(grade_error, "Your answer was not saved. Press Check to try again.")
    else:
        draw_ai_error(grade_error, "Your answer was not saved.")

    # The exercise stays in the stock. An exact answer still works without the AI.
    if st.button("Skip this sentence", key="practice_skip"):
        forget_current_exercise()
        st.rerun()


def skip_bad_sentence():
    # A bad sentence is often impossible to answer: I report it without typing anything. No attempt is saved
    # (there is no answer); the report uses the submission id reserved for this exercise.
    report = ProblemReport(exercise_id=st.session_state.practice_exercise_id,
                           submission_id=st.session_state.practice_submission_id, kind="bad_sentence")
    db.save_problem_report(report, db.DEFAULT_DATABASE_PATH)

    st.session_state.practice_flash_message = "Thanks. That sentence will not come back."
    forget_current_exercise()
    st.rerun()


def draw_hint_and_skip():
    exercise = st.session_state.practice_exercise
    hint_column, skip_column = st.columns(2)

    with hint_column:
        if exercise.hint and st.button("Show hint", icon=":material/lightbulb:", key="practice_hint"):
            st.session_state.practice_hint_used = True

    with skip_column:
        if st.button("Skip: this sentence is bad", icon=":material/flag:", key="practice_skip_bad_sentence"):
            skip_bad_sentence()

    if st.session_state.practice_hint_used:
        st.info(escape_markdown(exercise.hint), icon=":material/lightbulb:")


# ---------- the result ----------

def make_result_message(result):
    # The text inside the coloured box. Every text from the AI is escaped: it is shown as written.
    message_lines = ["**" + STATE_TITLES[result.state] + "**"]

    if result.state == "almost":
        message_lines.append("The tested grammar is right, but: **" + escape_markdown(result.detected_mistake_text)
                             + "** → **" + escape_markdown(result.detected_correction) + "** ("
                             + get_skill_name(result.detected_skill_id) + ").")

    if result.state in ["partial", "wrong"]:
        message_lines.append("You wrote: **" + escape_markdown(result.mistake_text) + "**")
        message_lines.append("Why: " + escape_markdown(result.why_wrong))
        message_lines.append("Rule: " + escape_markdown(result.rule))

    if result.note != "":
        message_lines.append(escape_markdown(result.note))

    if result.reminder != "":
        message_lines.append(escape_markdown(result.reminder))

    return "\n\n".join(message_lines)


def draw_result():
    result = st.session_state.practice_result
    result_message = make_result_message(result)

    st.caption("Your answer: " + escape_markdown(result.your_answer))

    if result.state == "correct":
        st.success(result_message, icon=":material/check_circle:")
    elif result.state == "wrong":
        st.error(result_message, icon=":material/cancel:")
    else:
        st.warning(result_message, icon=":material/error:")

    st.markdown("**Correct sentence:** " + escape_markdown(result.corrected_sentence))

    if len(result.other_good_answers) > 0:
        st.markdown("**Also good:** " + escape_markdown(", ".join(result.other_good_answers)))

    if result.memory_tip != "":
        st.markdown("**Memory tip:** " + escape_markdown(result.memory_tip))


def send_report(report_kind, comment):
    # Pydantic needs field names (the exception in CLAUDE.md).
    report = ProblemReport(exercise_id=st.session_state.practice_exercise_id,
                           submission_id=st.session_state.practice_submission_id, kind=report_kind,
                           your_answer=st.session_state.practice_result.your_answer, comment=comment.strip())

    # A second click saves nothing new: the table has UNIQUE (submission_id, kind).
    db.save_problem_report(report, db.DEFAULT_DATABASE_PATH)

    if report_kind not in st.session_state.practice_reports_sent:
        st.session_state.practice_reports_sent.append(report_kind)


def draw_report_box():
    submission_id = st.session_state.practice_submission_id

    with st.expander("Report a problem", icon=":material/flag:"):
        report_kind = st.radio("What is wrong?", list(REPORT_KIND_LABELS), format_func=REPORT_KIND_LABELS.get,
                               key="practice_report_kind_" + submission_id)
        comment = st.text_input("Comment (optional)", key="practice_report_comment_" + submission_id)

        if st.button("Send report", key="practice_send_report"):
            send_report(report_kind, comment)

        for sent_kind in st.session_state.practice_reports_sent:
            st.caption(":material/done: Saved: " + REPORT_KIND_LABELS[sent_kind])


def draw_next_button():
    if st.button("Next sentence", type="primary", icon=":material/arrow_forward:", key="practice_next"):
        forget_current_exercise()
        st.rerun()


# ---------- the page ----------

start_page_memory()

st.title("Practice")
st.caption(make_session_counter_text())

chosen_skill_id, chosen_level, chosen_topic = draw_filters()
chosen_filters = (chosen_skill_id, chosen_level, chosen_topic)

# A new filter = a new exercise. The old one, if unanswered, stays in the stock: nothing is lost.
if st.session_state.practice_filters != chosen_filters:
    st.session_state.practice_filters = chosen_filters
    forget_current_exercise()

if st.session_state.practice_exercise is None and st.session_state.practice_load_error is None:
    load_next_exercise(chosen_level, chosen_skill_id, chosen_topic)

if st.session_state.practice_load_error is not None:
    draw_load_error()
    st.stop()

st.divider()
draw_exercise(chosen_skill_id)

if st.session_state.practice_result is not None:
    draw_result()
    draw_report_box()
    draw_next_button()
elif st.session_state.practice_already_saved:
    st.info("This answer was already saved.", icon=":material/info:")
    draw_next_button()
else:
    draw_answer_form()
    draw_hint_and_skip()
