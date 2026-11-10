# Key decisions

## Target
- fail = G3 < 10, as the user specified. G3 = 0 (15 students) is kept as a fail but flagged in the report as a likely dropout or absence from the exam.

## Columns excluded (not available at the start of the year, so they would leak information)
- **G1, G2**: period grades from the year being predicted. They appear only in a clearly labelled *reference* model, to show how much waiting for G1 would gain.
- **absences**: the count for the same school year, which builds up while the year is running. Previous-year absences would be a legitimate replacement if the school records them.
- **G3**: the outcome itself.

## Columns kept, with assumptions
- Everything else is treated as known at the start of the year. Questionnaire items (studytime, goout, Dalc, Walc, romantic, health, famrel, freetime) assume a questionnaire is given at enrolment. Because that is not guaranteed, and the items are sensitive, I also tested an **"admin_only"** set: school, age, failures, schoolsup, higher, Medu, Fedu, address, traveltime, guardian, reason, paid, famsup. It performed as well as the full set.
  - schoolsup and paid are assumed to reflect support arranged at enrolment. If they are in fact decided during the year, they leak information. Their importance is small, so the risk is low.
- **sex and age** (sensitive attributes): I tested models with and without them. Accuracy was the same, so they can be dropped.

## Evaluation choices
- The main metric matches the operational constraint: the **share of fails caught** and the **share of flagged students who fail**, when the top 30% by predicted risk are flagged. This is computed within each test fold. ROC-AUC and PR-AUC are reported as secondary metrics.
- Validation: stratified 5-fold cross-validation, repeated 10 times (50 fits per configuration). The results are honest only within this one year. A future year was not available to test on.
- Models: L2-regularised logistic regression with balanced class weights (the main recommendation, for interpretability), random forest, and gradient boosting.
- Factor importance: univariate fail rates (Spearman / Cramér's V, with Benjamini–Hochberg FDR correction), a multivariable logistic model with odds ratios (statsmodels), and permutation importance (drop in AUC on held-out halves, over 10 splits).
- Fairness check: the out-of-fold top-30% flag, broken down by sex, school and address.
- The 382 students who also appear in the Math file are irrelevant here. Only the Portuguese file was used.
