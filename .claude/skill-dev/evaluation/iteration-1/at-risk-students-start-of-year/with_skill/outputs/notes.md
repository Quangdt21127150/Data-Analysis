# Key decisions (analysis log)

Tool: education-data-analytics skill, `scripts/edu_analytics.py` (profile -> run). No human available; assumptions documented here.

## Decision framing
- Users: tutor coordinators; decision = whom to offer early tutoring. Unit = one student-year (row). Prediction point = START of school year.
- Outcome: G3 < 10 (official pass mark, given by the user, not chosen from the data). Capacity 30% (alt 15%).
- Success criteria fixed before running (skill defaults): CV AUC >= 0.70, recall >= 60% at 30% flagged, >= 0.02 AUC over best single signal, recall gap across groups <= 10 points.

## Columns excluded
| Column(s) | Category | Reason |
|---|---|---|
| G1, G2 | Leakage (timing) | Period grades recorded during the year, after the prediction point; univariate AUC 0.94/0.96. |
| absences | Leakage (timing) | Absence count for the current school year, so not known at the start. Prior-year absences would be fine to collect. |
| schoolsup | Leakage (consequence) / intervention | Extra school support is plausibly assigned in response to early poor grades, and it is the intervention itself. |
| sex, age, address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob, guardian | Sensitive (demographic / family background) | Not used to make decisions about individual students; kept in the data for auditing. |
| romantic, Dalc, Walc, health | Sensitive (private life / health) | Privacy; inappropriate as a basis for outreach. |

Fairness audit variables: sex, address, age (age is also a proxy for grade repetition).

## Kept but flagged
- `school`: the strongest predictor (GP 7.6% vs MS 30% failure). Kept because it is a legitimate, known-at-start attribute, but it dominates the pooled model. A supplementary within-school check (`within_school_check.py`) shows the model adds little over prior failures inside MS.
- `paid` (paid extra classes): kept as a start-of-year attribute (assumed enrolled at the start); its positive association with failing is interpreted as reverse direction / selection.
- `traveltime`: kept; correlates with rural address (indirect proxy), which shows up in the rural flag rate.
- `internet`: kept as a practical study-resource variable, though it is a mild socio-economic proxy.
- Questionnaire items (studytime, goout, freetime, famrel, higher, activities, famsup, nursery, reason) are assumed collectable through an enrolment questionnaire.

## Label decisions
- 15 students with G3 = 0 (all had G1 > 0 and 0 absences; 14 of 15 at MS) are interpreted as dropout / no final assessment. Primary: counted as fail (`zero_is_missing: false`), because from the school's view they did not pass and needed support. Sensitivity run excludes them (`config_sens_G3zero_excluded.json`): conclusions unchanged (CV AUC 0.80).
- Profile flagged pile-ups at failures = 0 and Dalc = 1. These are plausible real distributions (most students have no failures), not imputation, so no fix was applied.
- Sensitivity thresholds G3 < 8 and G3 < 12 were run for robustness only.

## Modelling choices (tool defaults, pre-specified)
- Stratified 80/20 split, seed 2026; preprocessing fitted inside pipelines on train only; 5-fold x 10 repeats CV; test evaluated once.
- Primary = logistic regression; RF would replace it only if >= 0.02 CV AUC better with no worse recall (it was +0.017, so LR kept).
- Scores are not calibrated (class_weight balanced) and are reported for ranking only.
- Supplementary within-school check uses repeated CV on all rows of each school (descriptive; not used for model selection).
