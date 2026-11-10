"""Sang loc sinh vien co nguy co bo hoc ngay sau ket qua HK1 nam nhat.

Chay: python analysis.py  (ghi ket qua vao thu muc chua script)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

OUT = Path(__file__).resolve().parent
DATA = Path(r"D:/Python/data-analysis/skill_source/N02-skills-marketplace/plugins/edu-analytics/"
            r"skills/education-data-analytics/evals/dropout-first-semester-screening/files/students_dropout.csv")
CAP = 0.30  # co van gap toi da ~30% sinh vien
RNG = np.random.default_rng(42)

# ---------------------------------------------------------------- load
df = pd.read_csv(DATA, sep=";")
df.columns = [c.strip() for c in df.columns]
df = df.rename(columns={"Nacionality": "Nationality"})
df["y"] = (df["Target"] == "Dropout").astype(int)

# Khoa tuyen sinh: 3 bien vi mo (that nghiep, lam phat, GDP) chi nhan 10 to hop gia tri
# -> dung lam ma "khoa" (cohort) de kiem dinh leave-one-cohort-out.
macro = ["Unemployment rate", "Inflation rate", "GDP"]
df["cohort"] = df.groupby(macro).ngroup()

# Bien phai sinh tu ket qua HK1
s1 = "Curricular units 1st sem "
enr = df[s1 + "(enrolled)"]
df["s1_zero_enrolled"] = (enr == 0).astype(int)
df["s1_approved_ratio"] = np.where(enr > 0, df[s1 + "(approved)"] / enr.replace(0, np.nan), np.nan)
df["s1_eval_ratio"] = np.where(enr > 0, df[s1 + "(evaluations)"] / enr.replace(0, np.nan), np.nan)
df["s1_no_approved"] = ((df[s1 + "(approved)"] == 0) & (enr > 0)).astype(int)
df["age_group"] = pd.cut(df["Age at enrollment"], [0, 20, 25, 100], labels=["<=20", "21-25", ">25"])

# ---------------------------------------------------------------- feature sets
CAT = ["Application mode", "Course", "Previous qualification", "Mother's qualification",
       "Father's qualification", "Mother's occupation", "Father's occupation", "Marital status"]
NUM_ADMIN = ["Application order", "Daytime/evening attendance", "Previous qualification (grade)",
             "Admission grade", "Displaced", "Educational special needs", "Scholarship holder",
             "Age at enrollment"]
NUM_S1 = [c for c in df.columns if c.startswith(s1)] + [
    "s1_zero_enrolled", "s1_approved_ratio", "s1_eval_ratio", "s1_no_approved"]
FEES = ["Debtor", "Tuition fees up to date"]
S2 = [c for c in df.columns if c.startswith("Curricular units 2nd sem")]
SENSITIVE = ["Gender", "International", "Nationality"]

FEATURE_SETS = {
    "A_admission_only": (CAT, NUM_ADMIN),
    "B_main_admission+HK1": (CAT, NUM_ADMIN + NUM_S1),
    "C_B+hoc_phi_no": (CAT, NUM_ADMIN + NUM_S1 + FEES),
    "D_B+gioi_tinh_quoc_tich": (CAT + ["Nationality"], NUM_ADMIN + NUM_S1 + ["Gender", "International"]),
    "E_LEAKAGE_B+HK2": (CAT, NUM_ADMIN + NUM_S1 + S2),
}


def make_model(kind, cat, num):
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=30, sparse_output=False), cat),
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=False)),
                          ("sc", StandardScaler())]), num),
    ])
    if kind == "logit":
        clf = LogisticRegression(C=0.3, max_iter=3000)
    else:
        clf = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300,
                                             l2_regularization=1.0, random_state=0)
    return Pipeline([("pre", pre), ("clf", clf)])


def flag_top(scores, groups, cap=CAP):
    """Gan co cho top `cap` diem rui ro TRONG MOI KHOA (mo phong cach dung thuc te)."""
    flag = np.zeros(len(scores), dtype=bool)
    for g in np.unique(groups):
        idx = np.where(groups == g)[0]
        k = int(np.floor(cap * len(idx)))
        top = idx[np.argsort(-scores[idx], kind="stable")[:k]]
        flag[top] = True
    return flag


def loco_predict(kind, cat, num, data):
    """Leave-one-cohort-out: train tren 9 khoa, du doan khoa con lai."""
    p = np.zeros(len(data))
    for g in data["cohort"].unique():
        tr, te = data["cohort"] != g, data["cohort"] == g
        m = make_model(kind, cat, num).fit(data.loc[tr, cat + num], data.loc[tr, "y"])
        p[te.values] = m.predict_proba(data.loc[te, cat + num])[:, 1]
    return p


def metrics(y, p, flag):
    tp = (flag & (y == 1)).sum()
    return dict(AUC=roc_auc_score(y, p), PR_AUC=average_precision_score(y, p),
                Brier=brier_score_loss(y, p) if p.max() <= 1 else np.nan, flagged_pct=flag.mean(),
                recall_at_30=tp / (y == 1).sum(), precision_at_30=tp / flag.sum(),
                lift=(tp / flag.sum()) / y.mean())


def boot_ci(y, p, flag, cohorts, B=1000):
    """Bootstrap theo cum (khoa) + trong khoa, cho recall@30 va AUC."""
    rec, auc = [], []
    n = len(y)
    for _ in range(B):
        idx = RNG.integers(0, n, n)
        yy, ff, pp = y[idx], flag[idx], p[idx]
        rec.append((ff & (yy == 1)).sum() / max((yy == 1).sum(), 1))
        auc.append(roc_auc_score(yy, pp))
    return np.percentile(rec, [2.5, 97.5]), np.percentile(auc, [2.5, 97.5])


y = df["y"].values
coh = df["cohort"].values
results, preds = [], {}

# Baseline quy tac don gian: xep hang theo ty le mon dat HK1 (thap -> rui ro cao),
# hoa giai bang diem TB HK1 thap.
rule_score = (1 - df["s1_approved_ratio"].fillna(0)) * 100 + (20 - df[s1 + "(grade)"]) / 20
rule_flag = flag_top(rule_score.values, coh)
results.append(dict(model="Quy tac: ty le mon dat HK1", **metrics(y, rule_score.values, rule_flag)))
preds["rule"] = rule_score.values

for name, (cat, num) in FEATURE_SETS.items():
    for kind in ["logit", "hgb"]:
        p = loco_predict(kind, cat, num, df)
        f = flag_top(p, coh)
        preds[f"{name}|{kind}"] = p
        results.append(dict(model=f"{name} | {kind}", **metrics(y, p, f)))
        print(results[-1]["model"], round(results[-1]["AUC"], 3), round(results[-1]["recall_at_30"], 3))

res = pd.DataFrame(results)
res.to_csv(OUT / "model_comparison.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- chosen model
MAIN = "B_main_admission+HK1|logit"
p_main = preds[MAIN]
f_main = flag_top(p_main, coh)
df["risk_score"] = p_main
df["flagged"] = f_main
rec_ci, auc_ci = boot_ci(y, p_main, f_main, coh)

# Recall theo tung khoa (do on dinh)
per_cohort = (df.groupby("cohort").apply(lambda d: pd.Series({
    "n": len(d), "dropout_rate": d.y.mean(),
    "recall_at_30": (d.flagged & (d.y == 1)).sum() / d.y.sum(),
    "precision_at_30": (d.flagged & (d.y == 1)).sum() / d.flagged.sum(),
    "AUC": roc_auc_score(d.y, d.risk_score)}), include_groups=False))
per_cohort.to_csv(OUT / "per_cohort_main.csv", float_format="%.4f")

# Recall o cac nguong nang luc khac nhau
cap_rows = []
for cap in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
    for key, lab in [(MAIN, "Mo hinh chinh (B, logit)"), ("rule", "Quy tac ty le mon dat"),
                     ("A_admission_only|logit", "Chi du lieu tuyen sinh")]:
        ff = flag_top(preds[key], coh, cap)
        cap_rows.append(dict(cap=cap, model=lab, recall=(ff & (y == 1)).sum() / y.sum(),
                             precision=(ff & (y == 1)).sum() / ff.sum()))
caps = pd.DataFrame(cap_rows)
caps.to_csv(OUT / "recall_by_capacity.csv", index=False, float_format="%.4f")

# Sensitivity: bo nhom "Enrolled" (ket cuc chua ro)
mask = df["Target"] != "Enrolled"
sens = dict(AUC_excl_enrolled=roc_auc_score(y[mask], p_main[mask]))
# Nhom Enrolled bi gan co bao nhieu?
flag_by_target = df.groupby("Target")["flagged"].mean()

# ---------------------------------------------------------------- fairness
def group_table(col):
    rows = []
    for g, d in df.groupby(col, observed=True):
        npos = d.y.sum()
        tp = (d.flagged & (d.y == 1)).sum()
        fp = (d.flagged & (d.y == 0)).sum()
        rows.append(dict(attribute=col, group=str(g), n=len(d), dropout_rate=d.y.mean(),
                         flag_rate=d.flagged.mean(),
                         recall=tp / npos if npos else np.nan,
                         precision=tp / d.flagged.sum() if d.flagged.sum() else np.nan,
                         false_positive_rate=fp / (len(d) - npos),
                         mean_pred=d.risk_score.mean(),
                         AUC=roc_auc_score(d.y, d.risk_score) if 0 < npos < len(d) else np.nan))
    return rows

fair_rows = []
for col in ["Gender", "age_group", "Scholarship holder", "Displaced", "International",
            "Daytime/evening attendance", "Debtor"]:
    fair_rows += group_table(col)
fair = pd.DataFrame(fair_rows)
fair.to_csv(OUT / "fairness_main.csv", index=False, float_format="%.4f")

# Bootstrap CI cho chenh lech recall theo gioi tinh
male, fem = df.Gender.values == 1, df.Gender.values == 0
diffs = []
for _ in range(1000):
    idx = RNG.integers(0, len(df), len(df))
    yy, ff, mm = y[idx], f_main[idx], male[idx]
    r_m = (ff & mm & (yy == 1)).sum() / (mm & (yy == 1)).sum()
    r_f = (ff & ~mm & (yy == 1)).sum() / (~mm & (yy == 1)).sum()
    diffs.append(r_m - r_f)
gender_recall_diff_ci = np.percentile(diffs, [2.5, 97.5]).tolist()

# ---------------------------------------------------------------- coefficients (fit on all data)
cat, num = FEATURE_SETS["B_main_admission+HK1"]
full = make_model("logit", cat, num).fit(df[cat + num], y)
names = full.named_steps["pre"].get_feature_names_out()
coef = pd.DataFrame({"feature": names, "coef_std": full.named_steps["clf"].coef_[0]})
coef["odds_ratio_per_SD_or_level"] = np.exp(coef.coef_std)
coef = coef.reindex(coef.coef_std.abs().sort_values(ascending=False).index)
coef.to_csv(OUT / "logit_coefficients.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- figures
fig, ax = plt.subplots(figsize=(7, 4.5))
for lab, d in caps.groupby("model"):
    ax.plot(d.cap * 100, d.recall * 100, marker="o", label=lab)
ax.plot([0, 40], [0, 40], ls=":", c="grey", label="Chon ngau nhien")
ax.axvline(30, c="k", lw=0.8, ls="--")
ax.set_xlabel("% sinh vien duoc co van gap (top rui ro trong khoa)")
ax.set_ylabel("% sinh vien bo hoc duoc phat hien (recall)")
ax.set_title("Ty le bat duoc SV bo hoc theo nang luc co van\n(kiem dinh leave-one-cohort-out)")
ax.legend(fontsize=8); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(OUT / "fig_recall_vs_capacity.png", dpi=130); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 4.5))
dd = pd.DataFrame({"p": p_main, "y": y})
dd["bin"] = pd.qcut(dd.p, 10, duplicates="drop")
cal = dd.groupby("bin", observed=True).agg(pred=("p", "mean"), obs=("y", "mean"))
ax.plot(cal.pred, cal.obs, marker="o"); ax.plot([0, 1], [0, 1], ls=":", c="grey")
ax.set_xlabel("Xac suat du doan (TB thap phan vi)"); ax.set_ylabel("Ty le bo hoc thuc te")
ax.set_title("Hieu chuan mo hinh chinh"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(OUT / "fig_calibration.png", dpi=130); plt.close(fig)

fg = fair[fair.attribute.isin(["Gender", "age_group", "Scholarship holder", "Displaced"])].copy()
fg["label"] = fg.attribute + "=" + fg.group
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(fg)); w = 0.27
ax.bar(x - w, fg.dropout_rate * 100, w, label="Ty le bo hoc thuc te")
ax.bar(x, fg.flag_rate * 100, w, label="Ty le bi gan co")
ax.bar(x + w, fg.recall * 100, w, label="Recall (trong nhom)")
ax.set_xticks(x); ax.set_xticklabels(fg.label, rotation=30, ha="right", fontsize=8)
ax.set_ylabel("%"); ax.legend(fontsize=8); ax.set_title("Kiem tra cong bang - mo hinh chinh")
fig.tight_layout(); fig.savefig(OUT / "fig_fairness.png", dpi=130); plt.close(fig)

# ---------------------------------------------------------------- summary json
summary = dict(
    n=len(df), dropout_rate=float(y.mean()), n_cohorts=int(df.cohort.nunique()),
    main_model=MAIN, main=metrics(y, p_main, f_main),
    recall_ci95=rec_ci.tolist(), auc_ci95=auc_ci.tolist(),
    recall_by_cohort_min=float(per_cohort.recall_at_30.min()),
    recall_by_cohort_max=float(per_cohort.recall_at_30.max()),
    flag_rate_by_target=flag_by_target.to_dict(), sensitivity=sens,
    gender_recall_diff_male_minus_female_ci95=gender_recall_diff_ci,
)
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
print(json.dumps(summary, indent=2, default=float))
print(res.to_string())
print(per_cohort.to_string())
print(caps.to_string())
print(fair.to_string())
print(coef.head(20).to_string())
