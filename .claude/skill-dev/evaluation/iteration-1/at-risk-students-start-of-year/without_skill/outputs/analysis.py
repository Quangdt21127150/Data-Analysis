"""At-risk (G3 < 10) early-warning feasibility analysis, Portuguese course.
Usage: python analysis.py <path to student-por.csv>
Writes result files and figures next to this script."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.inspection import permutation_importance

OUT = Path(__file__).resolve().parent
df = pd.read_csv(Path(sys.argv[1]), sep=";")
for c in ["G1", "G2", "G3"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
res = {}
res["n_rows"] = len(df)
res["n_missing_any"] = int(df.isna().sum().sum())
res["n_exact_duplicates"] = int(df.duplicated().sum())
df["fail"] = (df["G3"] < 10).astype(int)
res["fail_rate"] = df["fail"].mean()
res["n_fail"] = int(df["fail"].sum())
res["n_G3_zero"] = int((df["G3"] == 0).sum())
res["fail_rate_by_school"] = df.groupby("school")["fail"].agg(["mean", "size"]).round(3).to_dict()

# ---- Feature sets ----
LEAK = ["G1", "G2", "G3", "absences"]           # not known at start of year
SENSITIVE = ["sex", "age"]                      # tested with/without
ADMIN = ["school", "age", "failures", "schoolsup", "higher", "Medu", "Fedu", "address",
         "traveltime", "guardian", "reason", "paid", "famsup"]  # plausibly on enrolment form
ALL_START = [c for c in df.columns if c not in LEAK + ["fail"]]
num_like = ["age", "Medu", "Fedu", "traveltime", "studytime", "failures", "famrel",
            "freetime", "goout", "Dalc", "Walc", "health", "absences", "G1", "G2"]


def make_pre(cols):
    num = [c for c in cols if c in num_like]
    cat = [c for c in cols if c not in num_like]
    return ColumnTransformer([("num", StandardScaler(), num),
                              ("cat", OneHotEncoder(drop="if_binary", handle_unknown="ignore"), cat)])


models = {
    "logistic": lambda: LogisticRegression(C=0.3, max_iter=2000, class_weight="balanced"),
    "random_forest": lambda: RandomForestClassifier(n_estimators=400, min_samples_leaf=5,
                                                    class_weight="balanced_subsample", random_state=0, n_jobs=-1),
    "grad_boost": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05,
                                                         max_iter=200, random_state=0),
}
FLAG = 0.30
y = df["fail"].values


def top_k_metrics(y_true, score, frac=FLAG):
    k = int(round(frac * len(y_true)))
    idx = np.argsort(-score, kind="stable")[:k]
    tp = y_true[idx].sum()
    return tp / y_true.sum(), tp / k  # recall (share of failers caught), precision


def cv_eval(cols, model_key, n_rep=10):
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=n_rep, random_state=42)
    aucs, aps, recs, precs = [], [], [], []
    oof_first = np.zeros(len(df))
    for i, (tr, te) in enumerate(rskf.split(df, y)):
        pipe = Pipeline([("pre", make_pre(cols)), ("m", models[model_key]())])
        pipe.fit(df.iloc[tr][cols], y[tr])
        p = pipe.predict_proba(df.iloc[te][cols])[:, 1]
        if i < 5:
            oof_first[te] = p
        aucs.append(roc_auc_score(y[te], p))
        aps.append(average_precision_score(y[te], p))
        r, pr = top_k_metrics(y[te], p)
        recs.append(r); precs.append(pr)
    f = lambda a: (float(np.mean(a)), float(np.std(a)))
    return dict(auc=f(aucs), pr_auc=f(aps), recall_at_30=f(recs), precision_at_30=f(precs)), oof_first


feature_sets = {
    "all_start_of_year": ALL_START,
    "all_start_no_sex_age": [c for c in ALL_START if c not in SENSITIVE],
    "admin_only": ADMIN,
    "failures_only": ["failures"],
    "REFERENCE_with_G1_(not_start_of_year)": ALL_START + ["G1", "absences"],
}
rows, oof_store = [], {}
for fs, cols in feature_sets.items():
    for mk in models:
        if fs == "failures_only" and mk != "logistic":
            continue
        m, oof = cv_eval(cols, mk)
        oof_store[(fs, mk)] = oof
        fmt = lambda t: "%.3f +/- %.3f" % t
        rows.append(dict(feature_set=fs, model=mk, n_features=len(cols),
                         auc=fmt(m["auc"]), pr_auc=fmt(m["pr_auc"]),
                         recall_top30=fmt(m["recall_at_30"]), precision_top30=fmt(m["precision_at_30"])))
        print(fs, mk, rows[-1]["auc"], rows[-1]["recall_top30"], flush=True)
perf = pd.DataFrame(rows)
perf.to_csv(OUT / "model_performance.csv", index=False)

# Simple rule baselines (in-sample, no fitting needed)
for name, mask in {
    "failures>0": df.failures > 0,
    "failures>0 OR higher=no": (df.failures > 0) | (df.higher == "no"),
    "failures>0 OR higher=no OR school=MS": (df.failures > 0) | (df.higher == "no") | (df.school == "MS"),
}.items():
    res["rule: " + name] = dict(share_flagged=float(mask.mean()),
                               recall=float(df.loc[mask, "fail"].sum() / df.fail.sum()),
                               precision=float(df.loc[mask, "fail"].mean()))

# ---- Univariate factors ----
uni = []
for c in ALL_START:
    g = df.groupby(c)["fail"].agg(["mean", "size"])
    detail = "; ".join("%s: %.0f%% (n=%d)" % (k, 100 * r["mean"], r["size"]) for k, r in g.iterrows())
    if c in num_like:
        rho, p = stats.spearmanr(df[c], df["fail"])
        uni.append(dict(feature=c, stat="spearman_rho", value=rho, p=p, fail_rate_by_level=detail))
    else:
        tab = pd.crosstab(df[c], df["fail"])
        chi2, p, dof, _ = stats.chi2_contingency(tab)
        v = np.sqrt(chi2 / (len(df) * (min(tab.shape) - 1)))
        uni.append(dict(feature=c, stat="cramers_v", value=v, p=p, fail_rate_by_level=detail))
uni = pd.DataFrame(uni)
uni["p_fdr"] = multipletests(uni["p"], method="fdr_bh")[1]
uni = uni.reindex(uni["value"].abs().sort_values(ascending=False).index)
uni.to_csv(OUT / "univariate_factors.csv", index=False)

# ---- Multivariable logistic (statsmodels) on start-of-year features ----
X = sm.add_constant(pd.get_dummies(df[ALL_START], drop_first=True, dtype=float))
logit = sm.Logit(y, X).fit(disp=0, maxiter=200)
ci = logit.conf_int()
or_tab = pd.DataFrame({"odds_ratio": np.exp(logit.params), "ci_low": np.exp(ci[0]),
                       "ci_high": np.exp(ci[1]), "p": logit.pvalues}).drop("const").sort_values("p")
or_tab.round(4).to_csv(OUT / "logistic_odds_ratios.csv")
res["logit_pseudo_r2"] = float(logit.prsquared)

# ---- Permutation importance (logistic, all start features, 10 random half splits) ----
pi_all = []
for seed in range(10):
    idx = np.random.RandomState(seed).permutation(len(df)); h = len(df) // 2
    tr, te = idx[:h], idx[h:]
    pipe = Pipeline([("pre", make_pre(ALL_START)), ("m", models["logistic"]())]).fit(df.iloc[tr][ALL_START], y[tr])
    pi = permutation_importance(pipe, df.iloc[te][ALL_START], y[te], scoring="roc_auc", n_repeats=10, random_state=seed)
    pi_all.append(pi.importances_mean)
pi_df = pd.DataFrame({"feature": ALL_START, "auc_drop_mean": np.mean(pi_all, 0),
                      "auc_drop_sd": np.std(pi_all, 0)}).sort_values("auc_drop_mean", ascending=False)
pi_df.to_csv(OUT / "permutation_importance.csv", index=False)

# ---- Subgroup check of top-30% flag (logistic, all start, out-of-fold scores) ----
oof = oof_store[("all_start_of_year", "logistic")]
k = int(round(FLAG * len(df))); flag = np.zeros(len(df), int); flag[np.argsort(-oof)[:k]] = 1
df["flag"] = flag
sub = []
for g in ["sex", "school", "address"]:
    for lvl, d in df.groupby(g):
        sub.append(dict(group=g, level=lvl, n=len(d), fail_rate=d.fail.mean(), flagged_share=d.flag.mean(),
                        recall=d.loc[d.fail == 1, "flag"].mean(), precision=d.loc[d.flag == 1, "fail"].mean()))
sub = pd.DataFrame(sub).round(3)
sub.to_csv(OUT / "subgroup_flag_check.csv", index=False)
res["oof_recall_at_30_logistic_all_start"] = float(df.loc[df.fail == 1, "flag"].mean())
res["oof_precision_at_30_logistic_all_start"] = float(df.loc[df.flag == 1, "fail"].mean())
res["fail_G3zero_caught"] = float(df.loc[df.G3 == 0, "flag"].mean())

# ---- Capacity curve ----
fracs = np.linspace(0.05, 1, 20)
fig, ax = plt.subplots(figsize=(7, 5))
for key, lab in [(("all_start_of_year", "logistic"), "Start-of-year model (logistic)"),
                 (("admin_only", "logistic"), "Enrolment-form data only"),
                 (("failures_only", "logistic"), "Past failures only"),
                 (("REFERENCE_with_G1_(not_start_of_year)", "logistic"),
                  "Reference: + 1st-period grade (NOT available at start)")]:
    s = oof_store[key] + np.random.RandomState(0).rand(len(y)) * 1e-9  # random tie-break
    order = np.argsort(-s)
    c = [y[order[:int(round(f * len(y)))]].sum() / y.sum() for f in fracs]
    ax.plot(fracs * 100, np.array(c) * 100, marker="o", ms=3, label=lab)
ax.plot([0, 100], [0, 100], "k--", lw=1, label="Random selection")
ax.axvline(30, color="grey", ls=":"); ax.text(31, 5, "tutor capacity 30%", color="grey")
ax.set_xlabel("% of students flagged (highest risk first)"); ax.set_ylabel("% of failing students caught")
ax.set_title("How many future fails can tutors reach? (cross-validated)")
ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(OUT / "capacity_curve.png", dpi=150)

fig, ax = plt.subplots(figsize=(7, 5))
top = pi_df.head(12)[::-1]
ax.barh(top.feature, top.auc_drop_mean, xerr=top.auc_drop_sd, color="#4C72B0")
ax.set_xlabel("Drop in AUC when feature is shuffled (higher = more important)")
ax.set_title("Most informative start-of-year factors (logistic model)")
fig.tight_layout(); fig.savefig(OUT / "feature_importance.png", dpi=150)

json.dump(res, open(OUT / "summary_stats.json", "w"), indent=2, default=float)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
print(json.dumps(res, indent=2, default=float))
print(perf.to_string())
print(uni.head(16)[["feature", "stat", "value", "p_fdr", "fail_rate_by_level"]].to_string())
print(or_tab.head(14).round(3).to_string())
print(pi_df.head(12).to_string())
print(sub.to_string())
