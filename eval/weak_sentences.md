# Weak sentences

Exercises the AI wrote that do not really test their skill. They were removed from `data/tutor.db`
(never answered). Reuse them when a creation prompt changes: the new prompt must not write sentences like these.

A sentence is **weak** when another form is also natural (ambiguous), when nothing in it signals the tested
form, or when its words are above the level.

## present_simple (A2)

| Removed id | Sentence | Expected | Prompt version | Why it is weak |
| --- | --- | --- | --- | --- |
| 2 | The guide ___ (start) the museum tour at ten o'clock. | starts | gap_exercise@c2deeb | No time signal: "started" and "will start" fit too |
| 3 | Our main project ___ (face) unexpected delays this week. | faces | gap_exercise_batch@782cdb | "this week" calls for "is facing" |
| 4 | The director ___ (share) the quarterly revenue with the client today. | shares | gap_exercise_batch@782cdb | "today" calls for "is sharing" or "will share"; "quarterly revenue" is not A2 |
| 5 | The weekly sync ___ (begin) ten minutes late. | begins | gap_exercise_batch@782cdb | No time signal: "began" fits too |
| 6 | The supervisor ___ (provide) constructive feedback upon request. | provides | gap_exercise_batch@782cdb | "provided" and "will provide" fit too; "supervisor", "upon request" are not A2 |
| 7 | The product owner ___ (schedule) the upcoming sprint tomorrow. | schedules | gap_exercise_batch@782cdb | "tomorrow" calls for "will schedule" or "is scheduling" |
| 8 | My flight ___ (leave) very late today because of the bad weather. | leaves | gap_exercise_batch@ef2ee2 | "today" calls for "is leaving" or "left", although the prompt forbids such signals |
| 11 | The airline ___ (find) missing bags very quickly. | finds | gap_exercise_batch@ef2ee2 | No time signal: "found" fits too |

## word_choice (B1)

Not removed, but reported as `bad_sentence` in `problem_reports` (2026-11-19), so they leave the stock and their
attempts do not count for mastery (Step 3). #28 was found while writing the gold file; then all 5 word_choice
exercises of that batch had the same problem. Counted in the Part 4f hand review of generated exercises.

| Reported id | Sentence | Expected | Prompt version | Why it is weak |
| --- | --- | --- | --- | --- |
| 28 | Yesterday afternoon, she ___ [write] a complex SQL query to extract the user logs. | wrote | gap_exercise_batch@a64005 | Made for word_choice, but it tests the past simple (a verb in brackets, one form) |
| 29 | Right now, the machine learning model ___ [produce] strange results for the sales forecast. | is producing | gap_exercise_batch@a64005 | Tests the present continuous |
| 30 | Last week, the data team ___ [clean] a very messy customer dataset before the meeting. | cleaned | gap_exercise_batch@a64005 | Tests the past simple |
| 31 | Every Monday morning, our department ___ [use] a new data analysis tool for reports. | uses | gap_exercise_batch@a64005 | Tests the present simple |
| 32 | By next Friday, the analyst ___ [finish] the final report before the strict deadline. | will have finished | gap_exercise_batch@a64005 | Tests the future perfect (a B2 form in a B1 exercise) |

## What the prompt versions are

- `gap_exercise@c2deeb`: Step 1, one exercise per request.
- `gap_exercise_batch@782cdb`: first batch prompt (5 per request), no signal rule. 5 of 5 weak.
- `gap_exercise_batch@ef2ee2`: batch prompt with the signal rule, A2 vocabulary and the self-check. 2 of 5 weak.
