"""The fixed list of grammar and vocabulary skills. The AI may only use ids from this list.

Rules (see CLAUDE.md, rule 10):
- A skill id is never renamed or deleted, because old attempts point to it.
- To retire a skill, set "active": False.

Fields of each skill:
- typical_mistake: one or more examples "wrong → right", separated by " ; ".
- tag_when (optional): when to choose this skill and not a similar one. Only for skills that overlap.
"""


VALID_LEVELS = ["A2", "B1", "B2", "C1"]

CATEGORIES = [
    "verbs", "modals", "articles", "nouns_and_quantifiers", "prepositions", "pronouns", "comparatives",
    "conditionals", "passive_voice", "word_order", "phrasal_verbs", "collocations", "vocabulary", "spelling", "general",
]


# Each typical mistake is one that Portuguese speakers often make. Some are my own real mistakes.
SKILLS = [
    # ---------- verbs ----------
    {"id": "to_be", "name": "Verb to be", "level": "A2", "category": "verbs", "active": True,
     "typical_mistake": "I have 25 years. → I am 25 years old."},
    {"id": "there_is_are", "name": "There is / there are", "level": "A2", "category": "verbs", "active": True,
     "typical_mistake": "Have many people in the office. → There are many people in the office."},
    {"id": "present_simple", "name": "Present simple (he/she/it + s)", "level": "A2", "category": "verbs",
     "active": True, "typical_mistake": "She work in a bank. → She works in a bank."},
    {"id": "present_continuous", "name": "Present continuous", "level": "A2", "category": "verbs", "active": True,
     "typical_mistake": "I work on the report now. → I am working on the report now."},
    {"id": "past_simple", "name": "Past simple", "level": "A2", "category": "verbs", "active": True,
     "typical_mistake": "Yesterday I go to the office. → Yesterday I went to the office.",
     "tag_when": "The tense is wrong (present used for a finished past action). If the tense is right but the "
                 "irregular form is wrong (writed), use irregular_verbs."},
    {"id": "irregular_verbs", "name": "Irregular verb forms", "level": "A2", "category": "verbs", "active": True,
     "typical_mistake": "I writed the email. → I wrote the email. ; I have went there. → I have gone there.",
     "tag_when": "The past or participle form of an irregular verb is wrong, in any tense. Not a spelling mistake."},
    {"id": "past_continuous", "name": "Past continuous", "level": "B1", "category": "verbs", "active": True,
     "typical_mistake": "I watched TV when she called. → I was watching TV when she called."},
    {"id": "present_perfect", "name": "Present perfect vs past simple", "level": "B1", "category": "verbs",
     "active": True, "typical_mistake": "I have seen him yesterday. → I saw him yesterday.",
     "tag_when": "Present perfect and past simple are mixed up (have + a finished time like yesterday). "
                 "For an action that continues with for / since, use present_perfect_for_since."},
    {"id": "present_perfect_for_since", "name": "Present perfect with for / since", "level": "B1", "category": "verbs",
     "active": True, "typical_mistake": "I live here since 2020. → I have lived here since 2020.",
     "tag_when": "A present tense is used with for / since for something that started in the past and continues."},
    {"id": "future_forms", "name": "Future: will / going to / present continuous", "level": "B1", "category": "verbs",
     "active": True,
     "typical_mistake": "Tomorrow I go to the dentist at 10. → Tomorrow I am going to the dentist at 10."},
    {"id": "used_to", "name": "Used to / be used to", "level": "B1", "category": "verbs", "active": True,
     "typical_mistake": "I am used to wake up early. → I am used to waking up early."},
    {"id": "gerund_infinitive", "name": "Gerund or infinitive", "level": "B1", "category": "verbs", "active": True,
     "typical_mistake": "I enjoy to read. → I enjoy reading. ; "
                        "Is it possible create an app? → Is it possible to create an app?"},
    {"id": "past_perfect", "name": "Past perfect", "level": "B2", "category": "verbs", "active": True,
     "typical_mistake": "When I arrived, the meeting already finished. → "
                        "When I arrived, the meeting had already finished."},
    {"id": "reported_speech", "name": "Reported speech (say / tell)", "level": "B2", "category": "verbs",
     "active": True, "typical_mistake": "She said me that she was busy. → She told me that she was busy."},

    # ---------- modals ----------
    {"id": "modals_base_verb", "name": "Modal + base verb (can, could, should, must)", "level": "A2",
     "category": "modals", "active": True,
     "typical_mistake": "I can to speak English. → I can speak English. ; You should to rest. → You should rest."},
    {"id": "modals_obligation", "name": "Must / have to / don't have to", "level": "B1", "category": "modals",
     "active": True, "typical_mistake": "You mustn't come, it is optional. → You don't have to come, it is optional."},
    {"id": "modals_deduction", "name": "Must / might / can't have (deduction)", "level": "B2", "category": "modals",
     "active": True, "typical_mistake": "He must forget the meeting. → He must have forgotten the meeting."},

    # ---------- articles ----------
    {"id": "articles_a_an", "name": "A / an (jobs and single things)", "level": "A2", "category": "articles",
     "active": True, "typical_mistake": "She is engineer. → She is an engineer."},
    {"id": "articles_no_article", "name": "No article: general ideas, possessives, names", "level": "B1",
     "category": "articles", "active": True,
     "typical_mistake": "The life is hard. → Life is hard. ; I spoke with the my brother. → I spoke with my brother. ; "
                        "I love the Portugal. → I love Portugal. ; I have the Claude Pro. → I have Claude Pro."},

    # ---------- nouns and quantifiers ----------
    {"id": "uncountable_nouns", "name": "Uncountable nouns", "level": "A2", "category": "nouns_and_quantifiers",
     "active": True, "typical_mistake": "I need some informations. → I need some information."},
    {"id": "much_many", "name": "Much / many / a lot of", "level": "A2", "category": "nouns_and_quantifiers",
     "active": True, "typical_mistake": "How much people came? → How many people came?"},

    # ---------- prepositions ----------
    {"id": "prepositions_time", "name": "Prepositions of time (in / on / at / none)", "level": "A2",
     "category": "prepositions", "active": True,
     "typical_mistake": "The meeting is in Monday. → The meeting is on Monday. ; "
                        "I have Claude Pro in this month. → I have Claude Pro this month."},
    {"id": "prepositions_place", "name": "Prepositions of place (in / on / at)", "level": "A2",
     "category": "prepositions", "active": True, "typical_mistake": "I am in the bus stop. → I am at the bus stop."},
    {"id": "dependent_prepositions", "name": "Verb or adjective + preposition", "level": "B1",
     "category": "prepositions", "active": True, "typical_mistake": "It depends of you. → It depends on you."},

    # ---------- pronouns ----------
    {"id": "subject_pronouns", "name": "Subject pronouns (no missing subject)", "level": "A2", "category": "pronouns",
     "active": True,
     "typical_mistake": "Is raining. → It is raining. ; "
                        "I don't know if is right or not. → I don't know if it is right or not."},
    {"id": "possessive_pronouns", "name": "Possessives (his / her / their)", "level": "A2", "category": "pronouns",
     "active": True, "typical_mistake": "My brother and her wife. → My brother and his wife."},
    {"id": "relative_pronouns", "name": "Relative pronouns (who / which / that / whose)", "level": "B1",
     "category": "pronouns", "active": True, "typical_mistake": "The man which called you. → The man who called you."},

    # ---------- comparatives ----------
    {"id": "comparatives_superlatives", "name": "Comparatives and superlatives", "level": "A2",
     "category": "comparatives", "active": True,
     "typical_mistake": "This task is more easy than that. → This task is easier than that. ; "
                        "The more beautiful city of the world. → The most beautiful city in the world."},
    {"id": "too_enough", "name": "Too / enough / as ... as", "level": "B1", "category": "comparatives", "active": True,
     "typical_mistake": "I am enough old to decide. → I am old enough to decide."},

    # ---------- conditionals ----------
    {"id": "conditional_first", "name": "Zero and first conditional", "level": "B1", "category": "conditionals",
     "active": True, "typical_mistake": "If it will rain, I stay home. → If it rains, I will stay home."},
    {"id": "conditional_second", "name": "Second conditional", "level": "B1", "category": "conditionals",
     "active": True, "typical_mistake": "If I would have money, I would travel. → If I had money, I would travel."},
    {"id": "conditional_third", "name": "Third conditional", "level": "B2", "category": "conditionals", "active": True,
     "typical_mistake": "If I had known, I would come. → If I had known, I would have come."},
    {"id": "wish", "name": "Wish / if only", "level": "B2", "category": "conditionals", "active": True,
     "typical_mistake": "I wish I can speak better. → I wish I could speak better."},
    {"id": "mixed_conditionals", "name": "Mixed conditionals", "level": "C1", "category": "conditionals",
     "active": True,
     "typical_mistake": "If I took that job, I would be rich now. → If I had taken that job, I would be rich now."},

    # ---------- passive voice ----------
    {"id": "passive_voice", "name": "Passive voice (present and past)", "level": "B1", "category": "passive_voice",
     "active": True,
     "typical_mistake": "The report wrote by Ana yesterday. → The report was written by Ana yesterday."},
    {"id": "have_something_done", "name": "Have something done", "level": "B2", "category": "passive_voice",
     "active": True, "typical_mistake": "I cut my hair yesterday (at the hairdresser). → I had my hair cut yesterday."},
    {"id": "passive_reporting", "name": "Reporting passive (it is said that)", "level": "C1",
     "category": "passive_voice", "active": True,
     "typical_mistake": "Says that the company will close. → It is said that the company will close."},

    # ---------- word order ----------
    {"id": "questions_negatives", "name": "Questions and negatives (word order, do / does / did)", "level": "A2",
     "category": "word_order", "active": True,
     "typical_mistake": "I no like coffee. → I don't like coffee. ; Where you work? → Where do you work? ; "
                        "What he is asking? → What is he asking?"},
    {"id": "adjective_position", "name": "Adjective before the noun", "level": "A2", "category": "word_order",
     "active": True, "typical_mistake": "I have a car red. → I have a red car."},
    {"id": "adverb_position", "name": "Position of adverbs (always, often, never)", "level": "A2",
     "category": "word_order", "active": True, "typical_mistake": "I go always to the gym. → I always go to the gym."},
    {"id": "indirect_questions", "name": "Indirect questions", "level": "B2", "category": "word_order", "active": True,
     "typical_mistake": "Can you tell me where is the station? → Can you tell me where the station is?"},
    {"id": "inversion", "name": "Inversion after negative adverbs", "level": "C1", "category": "word_order",
     "active": True, "typical_mistake": "Never I have seen this. → Never have I seen this."},

    # ---------- phrasal verbs ----------
    {"id": "phrasal_verbs_common", "name": "Common phrasal verbs", "level": "B1", "category": "phrasal_verbs",
     "active": True, "typical_mistake": "Please fill this form. → Please fill in this form."},
    {"id": "phrasal_verbs_separable", "name": "Phrasal verbs with pronouns (turn it off)", "level": "B2",
     "category": "phrasal_verbs", "active": True, "typical_mistake": "Turn off it. → Turn it off."},

    # ---------- collocations ----------
    {"id": "make_do", "name": "Make vs do", "level": "B1", "category": "collocations", "active": True,
     "typical_mistake": "I did a mistake. → I made a mistake.",
     "tag_when": "Only when make and do are mixed up."},
    {"id": "common_collocations", "name": "Common collocations", "level": "B2", "category": "collocations",
     "active": True, "typical_mistake": "Can I make a question? → Can I ask a question?",
     "tag_when": "Two words that usually go together are wrong (make a question). Not make vs do."},

    # ---------- vocabulary ----------
    {"id": "word_choice", "name": "Word choice", "level": "B1", "category": "vocabulary", "active": True,
     "typical_mistake": "I lost the bus. → I missed the bus.",
     "tag_when": "One word is used instead of another with a different meaning. Not a collocation, "
                 "not make vs do, not a false friend."},
    {"id": "false_friends", "name": "False friends (Portuguese / English)", "level": "B1", "category": "vocabulary",
     "active": True, "typical_mistake": "Actually I live in Lisbon (= atualmente). → Currently I live in Lisbon.",
     "tag_when": "The English word looks like a Portuguese word but means something else (actually, pretend, assist)."},

    # ---------- spelling ----------
    {"id": "spelling", "name": "Spelling", "level": "A2", "category": "spelling", "active": True,
     "typical_mistake": "I have finised the report. → I have finished the report.",
     "tag_when": "Wrong letters in a word. Not capital letters (capitalization), "
                 "not irregular forms (irregular_verbs)."},
    {"id": "capitalization", "name": "Capital letters", "level": "A2", "category": "spelling", "active": True,
     "typical_mistake": "on monday i speak english. → On Monday I speak English.",
     "tag_when": "Only capital letters: start of a sentence, I, days, months, languages, nationalities, names."},

    # ---------- general (never recommended as grammar skills) ----------
    {"id": "writing_general", "name": "Writing (no mistakes found)", "level": "A2", "category": "general",
     "active": True, "typical_mistake": "Used only for a free text with no mistakes."},
    {"id": "listening", "name": "Listening (dictation)", "level": "A2", "category": "general", "active": True,
     "typical_mistake": "Used for dictation answers."},
    {"id": "speaking", "name": "Speaking (read aloud)", "level": "A2", "category": "general", "active": True,
     "typical_mistake": "Used for read-aloud answers."},
]


def get_skill(skill_id):
    for skill in SKILLS:
        if skill["id"] == skill_id:
            return skill

    return None


def is_valid_skill_id(skill_id):
    return get_skill(skill_id) is not None


def get_active_skills():
    active_skills = []

    for skill in SKILLS:
        if skill["active"]:
            active_skills.append(skill)

    return active_skills


def get_learning_skills():
    # Active skills that can be taught and tagged: everything except the "general" category.
    # Prompts that create or tag grammar exercises must use this list, never SKILLS.
    learning_skills = []

    for skill in get_active_skills():
        if skill["category"] != "general":
            learning_skills.append(skill)

    return learning_skills


def get_fill_the_gap_skills():
    # Learning skills that a fill-the-gap exercise can test. Not capitalization: the code check ignores
    # capital letters, so a capitalization gap could never be wrong (PLAN.md, Step 2).
    fill_the_gap_skills = []

    for skill in get_learning_skills():
        if skill["id"] != "capitalization":
            fill_the_gap_skills.append(skill)

    return fill_the_gap_skills


def get_fill_the_gap_skill_ids():
    fill_the_gap_skill_ids = []

    for skill in get_fill_the_gap_skills():
        fill_the_gap_skill_ids.append(skill["id"])

    return fill_the_gap_skill_ids


def skills_as_prompt_text(skill_list):
    # One line per skill, for the AI: "to_be | Verb to be | A2 | typical mistake: ... | tag when: ..."
    prompt_lines = []

    for skill in skill_list:
        prompt_line = skill["id"] + " | " + skill["name"] + " | " + skill["level"]
        prompt_line = prompt_line + " | typical mistake: " + skill["typical_mistake"]

        if "tag_when" in skill:
            prompt_line = prompt_line + " | tag when: " + skill["tag_when"]

        prompt_lines.append(prompt_line)

    return "\n".join(prompt_lines)
