"""English Tutor: the main file. It sets the browser tab and builds the menu on the left."""

import streamlit as st

st.set_page_config("English Tutor", ":material/school:")


# one st.Page per section. "title" and "icon" must be written by name: st.Page does not accept them by position
home_page = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)

learn_page = st.Page("pages/learn.py", title="Learn", icon=":material/menu_book:")
practice_page = st.Page("pages/practice.py", title="Practice", icon=":material/edit_note:")
writing_page = st.Page("pages/writing.py", title="Writing", icon=":material/draw:")
listening_page = st.Page("pages/listening.py", title="Listening", icon=":material/headphones:")
translate_page = st.Page("pages/translate.py", title="Translate", icon=":material/translate:")
speaking_page = st.Page("pages/speaking.py", title="Speaking", icon=":material/mic:")

review_page = st.Page("pages/review.py", title="Review", icon=":material/replay:")
progress_page = st.Page("pages/progress.py", title="Progress", icon=":material/monitoring:")


# the menu is split into three groups!! each key of the dictionary is a group title
menu_sections = {
    "Today": [home_page],
    "Study": [learn_page, practice_page, writing_page, listening_page, translate_page, speaking_page],
    "Track": [review_page, progress_page],
}

selected_page = st.navigation(menu_sections)
selected_page.run()