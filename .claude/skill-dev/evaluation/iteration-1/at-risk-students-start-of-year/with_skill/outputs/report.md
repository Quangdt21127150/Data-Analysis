# Start-of-year screening for Portuguese: who might need tutoring support?

**Question.** Using only information available at the start of the school year, can we rank students so that the ~30% that tutors can take include most of those who end the year with a final Portuguese grade G3 < 10?

**Short answer: partly yes.** A simple logistic-regression screen built on start-of-year information finds about **2 in 3 of the students who failed** while flagging 30% of students, which is clearly better than using past failures alone. But roughly 1 in 3 students who fail would still be missed, about 2 in 3 flagged students would have passed anyway, and the result depends heavily on *which school* a student attends. Treat it as a way to prioritise tutor conversations, not as a prediction about individual students.

## 1. Data and set-up

- Last year's file `student-por.csv`: 649 students, 33 columns, no missing values, no duplicate rows. Two schools: GP (423) and MS (226).
- Outcome: **G3 < 10** (the pass mark). 100 students (15.4%) fell below it. This includes 15 students with G3 = 0 who had first-period grades but no final grade, most likely because they dropped out or did not sit the final assessment. I counted them as "did not pass", since they need support just as much. Excluding them gives the same conclusions (see section 6).
- **Removed because they are not known at the start of the year:** G1 and G2 (period grades; on their own they would give AUC around 0.94-0.96, which is exactly why they can't be used), `absences` (this year's count), and `schoolsup` (school support is often given *in response to* early grades, and it is also the intervention itself).
- **Not used as model inputs (sensitive/personal):** sex, age, address, family size, parents' cohabitation, parents' education and jobs, guardian, romantic relationship, alcohol use, health. Sex, address and age were kept aside **only to check fairness**.
- **Used (14 inputs):** past class failures, wants higher education, weekly study time, school, reason for choosing the school, travel time, paid extra classes, family support, extracurricular activities, nursery, internet at home, family relationship quality, free time, going out.
- Method: an 80/20 stratified split. All model choices were made with 5-fold cross-validation repeated 10 times on the 80% part. The 20% test set (130 students, only 20 of them failing) was scored once at the end.

## 2. How well does it work? (flagging 30% of students)

| Approach | AUC (CV) | Share of failing students caught at 30% flagged (CV) | Test AUC [95% CI] | Caught on test |
|---|---|---|---|---|
| Random choice | 0.50 | ~30% | - | - |
| **Past failures only** (best single signal) | 0.67 | 53% | 0.75 [0.63-0.86] | 55% |
| **Logistic regression (chosen)** | **0.80** | **69%** | 0.83 [0.74-0.91] | 60% (12 of 20) |
| Random forest (comparison) | 0.82 | 69% | 0.86 [0.76-0.94] | 65% |

- With 30% flagged, about **35% of flagged students actually failed**, compared with 15% overall (about 2.3 times better than picking at random).
- Catching 60% of failing students takes a flag rate of about **25%**. Flagging only 15% catches about 43%. Full trade-off table: `results/report.md` section 6 and `results/figures/recall_vs_flag.png`.
- The random forest was not chosen because the rule set in advance required a gain of at least 0.02 AUC, and it gained only 0.017. Logistic regression is also easier to explain to tutors.
- The scores are good for **ranking** but are not true probabilities: they overstate risk (average score 0.38 against a real rate of 0.15). Use the order and don't quote "x% chance of failing".
- The test set is small (20 failing students), so the test numbers carry wide uncertainty. The cross-validation figures are the main evidence.

## 3. Which factors matter (associations, not causes)

Adjusted for each other, these start-of-year factors went with a higher chance of failing:

| Factor | Direction | Adjusted odds ratio (95% CI) |
|---|---|---|
| Attending school **MS** (vs GP) | higher risk | 4.7 (2.5-8.8) |
| Does **not** want higher education | higher risk | 2.8 (1.3-5.7) |
| **Past class failures** (per SD) | higher risk | 1.8 (1.4-2.2) |
| Paid extra Portuguese classes | higher risk* | 3.1 (1.2-8.1) |
| More weekly study time (per SD) | lower risk | 0.71 (0.51-0.99) |

Two factors, **past failures and school**, already give 95% of the full model's performance. Failure rate goes from 9% with no past failures to 46-64% with one or more. 48% of students who didn't want higher education failed, compared with 12% of those who did.

\*Paid classes probably go with risk because struggling students are the ones who get extra classes (reverse direction), not because the classes hurt. More generally, none of these results show what *causes* failure or what would prevent it.

## 4. Important caveat: the school effect

The two schools differ a lot: 7.6% of GP students failed against 30% at MS. Much of the model's strength comes from telling the schools apart. If you apply it **within a single school**, it is weaker (supplementary check, school removed from the model, `within_school_check.json`):

| School | Students (failing) | AUC | Caught at 30% flagged | Past failures alone |
|---|---|---|---|---|
| GP | 423 (32) | 0.76 | 72% | 58% |
| MS | 226 (68) | 0.66 | 49% | 54% |

At GP the screen still adds value. At MS, where almost a third fail, it does **no better than simply looking at past failures**, and with a 30% capacity many failing students would be missed anyway. **If your school is like MS, a simple rule ("prior failures, or not planning higher education") is about as good as the model and easier to justify.** If you pool both schools into one list, MS students and rural students get far more of the tutor places (rural students: 47% flagged vs 23% urban).

## 5. Fairness check (flag 30%)

Share of failing students who were caught, by group (cross-validation on the training set):

- **Sex:** girls 73%, boys 64% (gap 9 points). Flag rates were equal (30%).
- **Address:** urban 66%, rural 72%. Rural students were flagged twice as often (47% vs 23%), mainly through school and travel time.
- **Age:** 17 or younger: 61%; older than 17: 83% (gap 22 points; on the test set it was even larger). Older students are flagged more because they are more likely to have repeated a year. The upshot is that **younger students who fail are missed more often.**

The success criterion set in advance (recall gap of 10 points or less) is **not met**, mainly because of the age gap. Tutors should know that a younger student without a failure history can still struggle.

## 6. Robustness

- **Without the 15 G3 = 0 students:** AUC (CV) 0.80, 72% caught at 30%. The same conclusions hold.
- **Other cut-offs:** G3 < 8 gives AUC 0.77 (only 20 cases, unstable). G3 < 12 gives AUC 0.79 and catches 54% at 30%, because many more students fall below 12.

## 7. Limitations

- This uses one year from two schools. Performance can change from year to year or at another school, so re-check it at the end of each year before relying on it.
- The questionnaire items (study time, going out, family relationships, and so on) are self-reported and assumed to be collectable at enrolment. If they are actually filled in later in the year, timing matters.
- The data contains no information about tutoring itself, so this analysis cannot say whether tutoring helps or who benefits most.
- Prior-year grades and prior-year attendance were not available. They would likely improve a start-of-year screen considerably and are worth collecting.
- One cheap, strong option: add an **early check after the first grading period**. G1 alone is extremely informative (AUC around 0.94), so a second-round list in term 1 would catch most of the students this start-of-year list misses.

## 8. Recommendations

1. **Use the ranked list as a starting point for tutors and coordinators, not as an automatic decision.** A person reviews every flagged student, and outreach is framed as an offer of support. Never tell a student they are "predicted to fail".
2. Give tutors neutral reasons for each student (e.g. "has repeated a course before", "reports little weekly study time") rather than a risk score.
3. Pair the start-of-year list with a **term-1 re-check** using G1, and keep some tutor capacity free for it.
4. Each year, check how many failing students were caught, overall and by sex, age and address, and adjust.

## Files

- `config.json`: the analysis configuration actually used (primary). `config_sens_G3zero_excluded.json` is the sensitivity variant.
- `results/`: full tool output (`results.json`, the detailed auto-report `report.md` in Vietnamese, `prepared.csv`, logs, and `figures/roc_pr.png`, `recall_vs_flag.png`, `reduction.png`, `calibration.png`).
- `results_sens_G3zero_excluded/`: sensitivity run. `within_school_check.py` / `.json`: per-school check.
- `work/profile.md`: data-quality profile. `notes.md`: key decisions.
