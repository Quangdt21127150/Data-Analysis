"""Supplementary check: does the screen work WITHIN one school (school feature removed)?
Repeated stratified 5-fold CV on all rows of each school (no test peeking; this is descriptive)."""
import json, numpy as np, pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.compose import make_column_transformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score
cfg = json.load(open("config.json"))
d = pd.read_csv(cfg["data_path"], sep=";")
y_all = (d.G3 < 10).astype(int)
num = cfg["features"]["numeric"]; cat = [c for c in cfg["features"]["categorical"] if c != "school"]
def recall_at(y, s, rate=0.3):
    k = int(np.ceil(rate * len(s))); idx = np.argsort(-s)[:k]
    return y.values[idx].sum() / y.sum()
out = {}
# school-level flag share if the pooled list (top 30% overall) were used
for sch in ["GP", "MS"]:
    m = d.school == sch; X = d.loc[m, num + cat]; y = y_all[m]
    aucs, recs, b1a, b1r = [], [], [], []
    for rep in range(10):
        cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=1, random_state=2026 + rep)
        pipe = make_pipeline(make_column_transformer((StandardScaler(), num), (OneHotEncoder(handle_unknown="ignore"), cat)),
                             LogisticRegression(class_weight="balanced", max_iter=2000))
        s = np.zeros(len(y))
        for tr, te in cv.split(X, y):
            pipe.fit(X.iloc[tr], y.iloc[tr]); s[te] = pipe.predict_proba(X.iloc[te])[:, 1]
        aucs.append(roc_auc_score(y, s)); recs.append(recall_at(y, s))
        f = X.failures.values + np.random.RandomState(rep).uniform(0, 1e-3, len(y))  # tie-break randomly
        b1a.append(roc_auc_score(y, X.failures)); b1r.append(recall_at(y, f))
    out[sch] = {"n": int(m.sum()), "positives": int(y.sum()), "base_rate": round(float(y.mean()), 3),
                "LR_cv_auc": round(float(np.mean(aucs)), 3), "LR_cv_auc_sd": round(float(np.std(aucs)), 3),
                "LR_recall_at_30pct": round(float(np.mean(recs)), 3),
                "failures_only_auc": round(float(np.mean(b1a)), 3), "failures_only_recall_at_30pct": round(float(np.mean(b1r)), 3)}
json.dump(out, open("within_school_check.json", "w"), indent=1); print(json.dumps(out, indent=1))
