"""Milestone 4 - LEVEL 2 Prototype Experiment (tuân thủ Evaluation Plan của Level 1).

Chạy sau prepare_data.py:  python src/model_experiment.py
- Đầu vào: data/processed/view_*_v1.0.csv (prepared dataset v1.0 của Milestone 3).
- Mọi lựa chọn mô hình/ngưỡng/bộ biến thực hiện trên training partition (CV 5-fold phân tầng, lặp 10 lần).
- Test set (n=231) chỉ dùng MỘT lần ở cuối để báo cáo hiệu năng.
- Quy tắc chọn primary approach đặt trước: giữ Logistic Regression trừ khi ứng viên phức tạp hơn
  vượt AUC CV trung bình ít nhất 0.02 VÀ không kém hơn về recall@30%.
"""
from __future__ import annotations

import json
import platform
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
import statsmodels.api as sm
from scipy import stats
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve, precision_recall_curve
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.multitest import multipletests

import config as C

OUT = C.REPORTS / "milestone4"
FIG = OUT / "figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 13, "axes.titlesize": 14, "axes.labelsize": 13,
    "xtick.labelsize": 12, "ytick.labelsize": 12, "legend.fontsize": 12, "axes.edgecolor": INK2,
    "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "figure.dpi": 150, "savefig.bbox": "tight"})
FEATS = [c if c != "english_level" else "english_ord" for c in C.MODEL_FEATURES]
VN = {"study_hours": "Giờ học/ngày", "study_sessions": "Số lần ngồi học/ngày", "attendance_pct": "Chuyên cần (%)",
      "social_media_hours": "Giờ MXH/ngày", "skill_dev_hours": "Giờ phát triển kỹ năng/ngày",
      "learning_mode": "Ưa học Online", "personal_computer": "Có máy tính cá nhân", "uni_transport": "Đi xe của trường",
      "english_ord": "Trình độ tiếng Anh (1-3)", "co_curricular": "Tham gia ngoại khóa", "current_semester": "Học kỳ hiện tại",
      "credits_completed": "Tín chỉ đã hoàn thành", "smartphone": "Dùng smartphone", "teacher_consultancy": "Từng tư vấn giảng viên"}
N_REPEATS, K = 10, 5
FLAG_RATES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]


def save(fig, name):
    fig.savefig(FIG / name, facecolor="white"); plt.close(fig)


# ============================================================ helpers
def make_models(feats, english_onehot=True):
    """E2 (đặc tả hiện hành): english_ord one-hot trong LR vì quan hệ không đơn điệu (EDA train).
    E1 (english_onehot=False): english_ord tuyến tính - giữ để ghi experiment log."""
    num = [f for f in feats if not (english_onehot and f == "english_ord")]
    tfs = [("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num)]
    if english_onehot and "english_ord" in feats:
        tfs.append(("eng", OneHotEncoder(categories=[[1, 2, 3]], drop=[2], handle_unknown="ignore"), ["english_ord"]))
    lr = Pipeline([("prep", ColumnTransformer(tfs)),
                   ("clf", LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0))])
    rf = Pipeline([("prep", ColumnTransformer([("num", SimpleImputer(strategy="median"), num)])),
                   ("clf", RandomForestClassifier(n_estimators=500, min_samples_leaf=10, max_features="sqrt",
                                                  class_weight="balanced_subsample", random_state=C.SEED, n_jobs=-1))])
    return {"LR": lr, "RF": rf}


def recall_precision_at_rate(y, s, rate):
    n_flag = int(np.ceil(rate * len(s)))
    order = np.argsort(-s, kind="mergesort")
    flagged = np.zeros(len(s), bool); flagged[order[:n_flag]] = True
    tp = int((flagged & (y == 1)).sum())
    return tp / max(int(y.sum()), 1), tp / max(n_flag, 1), n_flag, flagged


def metrics_at_cutoff(y, s, cut):
    flagged = s >= cut
    tp = int((flagged & (y == 1)).sum()); fp = int((flagged & (y == 0)).sum())
    fn = int((~flagged & (y == 1)).sum()); tn = int((~flagged & (y == 0)).sum())
    return {"flag_rate": round(flagged.mean(), 4), "recall": round(tp / max(tp + fn, 1), 4),
            "precision": round(tp / max(tp + fp, 1), 4), "tp": tp, "fp": fp, "fn": fn, "tn": tn}, flagged


def cv_oof(model, X, y, seed):
    oof = np.zeros(len(y))
    for tr_i, va_i in StratifiedKFold(K, shuffle=True, random_state=seed).split(X, y):
        m = clone(model).fit(X.iloc[tr_i], y[tr_i])
        oof[va_i] = m.predict_proba(X.iloc[va_i])[:, 1]
    return oof


def cv_summary(model, X, y, score_fn=None):
    """Repeated stratified CV; returns per-repeat metrics + OOF of first repeat."""
    rows, oof0 = [], None
    for r in range(N_REPEATS):
        if score_fn is None:
            oof = cv_oof(model, X, y, C.SEED + r)
        else:
            oof = score_fn(X)
        if oof0 is None:
            oof0 = oof
        rec30, prec30, _, _ = recall_precision_at_rate(y, oof, 0.30)
        rec15, prec15, _, _ = recall_precision_at_rate(y, oof, 0.15)
        rows.append({"auc": roc_auc_score(y, oof), "pr_auc": average_precision_score(y, oof),
                     "recall@30": rec30, "precision@30": prec30, "recall@15": rec15, "precision@15": prec15})
        if score_fn is not None:
            break
    df = pd.DataFrame(rows)
    return {k: {"mean": round(df[k].mean(), 4), "sd": round(df[k].std(ddof=1), 4) if len(df) > 1 else 0.0} for k in df}, oof0


def boot_ci(y, s, fn, n=2000, seed=C.SEED):
    rng = np.random.default_rng(seed); vals = []
    idx = np.arange(len(y))
    for _ in range(n):
        b = rng.choice(idx, len(idx), replace=True)
        if y[b].sum() == 0 or y[b].sum() == len(b):
            continue
        vals.append(fn(y[b], s[b]))
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


# ============================================================ main
def main() -> dict:
    FIG.mkdir(parents=True, exist_ok=True)
    pv = pd.read_csv(C.PROCESSED / f"view_predictive_{C.PREPARED_VERSION}.csv")
    dv = pd.read_csv(C.PROCESSED / f"view_diagnostic_{C.PREPARED_VERSION}.csv")
    fv = pd.read_csv(C.PROCESSED / f"view_fairness_audit_{C.PREPARED_VERSION}.csv")
    assert not set(pv.columns) & set(C.BANNED_FROM_MODEL), "Banned column in predictive view"
    tr, te = pv[pv.split == "train"].reset_index(drop=True), pv[pv.split == "test"].reset_index(drop=True)
    Xtr, ytr = tr[FEATS], tr.needs_support.astype(int).values
    Xte, yte = te[FEATS], te.needs_support.astype(int).values
    R: dict = {"environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                               "sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__,
                               "scipy": scipy.__version__, "statsmodels": sm.__version__ if hasattr(sm, "__version__") else "",
                               "seed": C.SEED, "prepared_version": C.PREPARED_VERSION, "cv": f"{K}-fold stratified x {N_REPEATS} repeats"},
               "data": {"train_n": len(tr), "train_pos": int(ytr.sum()), "test_n": len(te), "test_pos": int(yte.sum()),
                        "features": FEATS}}

    # ---------------------------------------------------- A. Diagnostics AQ2/AQ3 (train only)
    dtr = dv[dv.split == "train"].copy(); y = dtr.needs_support.astype(int)
    diag = []
    for c in C.HABIT_FEATURES + ["current_semester", "credits_completed"]:
        a, b = dtr.loc[y == 1, c].dropna(), dtr.loc[y == 0, c].dropna()
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        rrb = 1 - 2 * u / (len(a) * len(b))        # rank-biserial (>0: nhóm cần hỗ trợ có hạng THẤP hơn)
        diag.append({"aq": "AQ2" if c in C.HABIT_FEATURES else "AQ3", "var": c, "test": "Mann-Whitney U",
                     "median_pos": float(a.median()), "median_neg": float(b.median()),
                     "mean_pos": round(a.mean(), 2), "mean_neg": round(b.mean(), 2),
                     "effect": round(-rrb, 3), "effect_name": "rank-biserial r (dương: nhóm cần hỗ trợ cao hơn)", "p": p})
    for c in ["learning_mode", "personal_computer", "uni_transport", "english_ord", "co_curricular", "smartphone", "teacher_consultancy"]:
        tab = pd.crosstab(dtr[c], y)
        chi2, p, dof, exp = stats.chi2_contingency(tab, correction=False)
        test = "Chi-square"
        if tab.shape == (2, 2) and (exp < 5).any():
            p = stats.fisher_exact(tab.values)[1]; test = "Fisher exact"
        v = np.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))
        rates = (tab[1] / tab.sum(axis=1)).round(3).to_dict()
        diag.append({"aq": "AQ3", "var": c, "test": test, "rates_by_level": {str(k): float(r) for k, r in rates.items()},
                     "n_by_level": {str(k): int(n) for k, n in tab.sum(axis=1).items()},
                     "effect": round(v, 3), "effect_name": "Cramér's V", "p": p})
    for aq in ("AQ2", "AQ3"):
        idx = [i for i, d in enumerate(diag) if d["aq"] == aq]
        adj = multipletests([diag[i]["p"] for i in idx], method="holm")[1]
        for i, pa in zip(idx, adj):
            diag[i]["p_holm"] = float(pa); diag[i]["p"] = float(diag[i]["p"])
    R["diagnostic_univariate"] = diag

    # adjusted logistic regression (train), numeric standardized -> OR per 1 SD
    Xd = dtr[FEATS].copy()
    Xd = Xd.fillna(Xd.median())
    num_sd = {}
    for c in C.NUMERIC_FEATURES:
        num_sd[c] = float(Xd[c].std()); Xd[c] = (Xd[c] - Xd[c].mean()) / Xd[c].std()
    Xd["english_basic"] = (Xd["english_ord"] == 1).astype(int)       # tham chiếu: Intermediate
    Xd["english_advanced"] = (Xd["english_ord"] == 3).astype(int)
    Xd = Xd.drop(columns="english_ord")
    VN.update({"english_basic": "Tiếng Anh Basic (vs Intermediate)", "english_advanced": "Tiếng Anh Advanced (vs Intermediate)"})
    logit = sm.Logit(y.values, sm.add_constant(Xd.astype(float))).fit(disp=0)
    ci = logit.conf_int()
    R["diagnostic_adjusted_logit"] = {
        "n": int(len(y)), "pseudo_r2": round(float(logit.prsquared), 4), "llr_p": float(logit.llr_pvalue),
        "terms": [{"var": v, "or": round(float(np.exp(logit.params[v])), 3), "ci_low": round(float(np.exp(ci.loc[v, 0])), 3),
                   "ci_high": round(float(np.exp(ci.loc[v, 1])), 3), "p": float(logit.pvalues[v]),
                   "scale": "per 1 SD" if v in num_sd else ("vs Intermediate" if v.startswith("english") else "Yes vs No"),
                   "sd": round(num_sd.get(v, np.nan), 3)}
                  for v in Xd.columns]}

    # ---------------------------------------------------- B. AQ4 models (train CV)
    models = make_models(FEATS)
    cv, oofs = {}, {}
    cv["B0_majority"], oofs["B0_majority"] = cv_summary(DummyClassifier(strategy="prior"), Xtr, ytr)
    att_score = lambda X: -X["attendance_pct"].fillna(Xtr["attendance_pct"].median()).values  # chuyên cần thấp -> rủi ro cao
    cv["B1_attendance_rule"], oofs["B1_attendance_rule"] = cv_summary(None, Xtr, ytr, score_fn=att_score)
    cv["LR_E1_english_ordinal"], _ = cv_summary(make_models(FEATS, english_onehot=False)["LR"], Xtr, ytr)
    for name, m in models.items():
        cv[name], oofs[name] = cv_summary(m, Xtr, ytr)
    R["cv_train"] = cv
    R["experiment_log"] = [
        {"id": "E1", "change": "LR, 11 biến, english_ord mã hóa tuyến tính (1-3)", "auc_cv": cv["LR_E1_english_ordinal"]["auc"],
         "decision": "Không giữ: AUC CV thấp hơn baseline 1 biến; EDA train cho thấy tỷ lệ cần hỗ trợ theo tiếng Anh hình chữ U"},
        {"id": "E2", "change": "LR, 11 biến, english_ord one-hot (tham chiếu Intermediate)", "auc_cv": cv["LR"]["auc"],
         "decision": "Giữ làm đặc tả LR chính thức; mọi so sánh sau dùng E2"},
        {"id": "E3", "change": "Random Forest (500 cây, min_samples_leaf=10, balanced_subsample)", "auc_cv": cv["RF"]["auc"],
         "decision": "Áp quy tắc chọn primary đặt trước (chênh AUC >= 0.02 và recall@30 không kém)"}]
    lr_auc, rf_auc = cv["LR"]["auc"]["mean"], cv["RF"]["auc"]["mean"]
    primary = "RF" if (rf_auc - lr_auc >= 0.02 and cv["RF"]["recall@30"]["mean"] >= cv["LR"]["recall@30"]["mean"]) else "LR"
    R["primary_rule"] = {"lr_auc": lr_auc, "rf_auc": rf_auc, "primary": primary}

    # sensitivity thresholds (LR, train CV)
    sens = {}
    for col in ["needs_support_t250", "needs_support_t300"]:
        ys = tr[col].astype(int).values
        s_, _ = cv_summary(models["LR"], Xtr, ys)
        sens[col] = {"pos": int(ys.sum()), "auc": s_["auc"], "pr_auc": s_["pr_auc"], "recall@30": s_["recall@30"]}
    R["sensitivity_threshold_train_cv"] = sens
    # sensitivity: giữ 140 bản ghi nghi điền khuyết (nhãn = 0 vì CGPA 3.15)
    trs = pv[pv.split.isin(["train", "train_suspect"])].reset_index(drop=True)
    tes = pv[pv.split.isin(["test", "test_suspect"])].reset_index(drop=True)
    ys_tr, ys_te = trs.needs_support_incl_suspect.astype(int).values, tes.needs_support_incl_suspect.astype(int).values
    s_cv, _ = cv_summary(models["LR"], trs[FEATS], ys_tr)
    m_s = clone(models["LR"]).fit(trs[FEATS], ys_tr); sc_s = m_s.predict_proba(tes[FEATS])[:, 1]
    R["sensitivity_incl_suspect"] = {"train_n": len(trs), "train_pos": int(ys_tr.sum()), "test_n": len(tes), "test_pos": int(ys_te.sum()),
                                     "cv_auc": s_cv["auc"], "cv_recall@30": s_cv["recall@30"],
                                     "test_auc": round(roc_auc_score(ys_te, sc_s), 4),
                                     "test_recall_top30": round(recall_precision_at_rate(ys_te, sc_s, .30)[0], 4)}

    # calibration on OOF (primary)
    o = oofs[primary]
    R["calibration_oof"] = {"brier": round(brier_score_loss(ytr, o), 4), "brier_prior": round(brier_score_loss(ytr, np.full(len(ytr), ytr.mean())), 4),
                            "mean_pred": round(float(o.mean()), 4), "base_rate": round(float(ytr.mean()), 4)}

    # ---------------------------------------------------- C. AQ5 reduction (train CV, LR)
    def cv_auc(feats, repeats=N_REPEATS):
        m = make_models(feats)["LR"]; vals = []
        for r in range(repeats):
            vals.append(roc_auc_score(ytr, cv_oof(m, tr[feats], ytr, C.SEED + r)))
        return float(np.mean(vals))
    full_auc = cv_auc(FEATS)
    path, cur = [{"n": len(FEATS), "removed": None, "auc": round(full_auc, 4), "features": list(FEATS)}], list(FEATS)
    while len(cur) > 1:
        trials = {f: cv_auc([x for x in cur if x != f], repeats=3) for f in cur}
        drop = max(trials, key=trials.get)
        cur = [x for x in cur if x != drop]
        path.append({"n": len(cur), "removed": drop, "auc": round(cv_auc(cur), 4), "features": list(cur)})
    ok = [p for p in path if p["auc"] >= 0.95 * full_auc]
    reduced = min(ok, key=lambda p: p["n"])
    R["reduction"] = {"full_auc_cv": round(full_auc, 4), "criterion_auc": round(0.95 * full_auc, 4), "path": path,
                      "selected": reduced, "reduction_pct": round(1 - reduced["n"] / len(FEATS), 4)}
    # group importance (drop-group)
    R["group_importance_cv"] = {"habits_only": round(cv_auc(C.HABIT_FEATURES), 4),
                                "conditions_only": round(cv_auc([f if f != "english_level" else "english_ord" for f in C.CONDITION_FEATURES]), 4),
                                "all": round(full_auc, 4)}

    # ---------------------------------------------------- D. Final fit + ONE holdout evaluation
    fitted = {n: clone(m).fit(Xtr, ytr) for n, m in models.items()}
    red_feats = reduced["features"]
    best = max(path, key=lambda p: p["auc"])                      # bộ có AUC CV cao nhất trên đường rút gọn (train)
    R["reduction"]["best_on_path"] = best
    sets = {"LR_reduced": red_feats, "LR_best_path": best["features"]}
    for n, fs in sets.items():
        fitted[n] = clone(make_models(fs)["LR"]).fit(tr[fs], ytr)
    feats_of = lambda n: sets.get(n, FEATS)
    test_scores = {n: fitted[n].predict_proba(te[feats_of(n)])[:, 1] for n in fitted}
    test_scores["B1_attendance_rule"] = -Xte["attendance_pct"].fillna(Xtr["attendance_pct"].median()).values
    # operating cutoffs learned on TRAIN OOF score distribution (quantiles)
    oof_for = {"LR": oofs["LR"], "RF": oofs["RF"], "B1_attendance_rule": oofs["B1_attendance_rule"]}
    for n, fs in sets.items():
        oof_for[n] = cv_oof(make_models(fs)["LR"], tr[fs], ytr, C.SEED)
        R["cv_train"][n], _ = cv_summary(make_models(fs)["LR"], tr[fs], ytr)
    test_eval = {}
    for n, s in test_scores.items():
        e = {"auc": round(roc_auc_score(yte, s), 4), "auc_ci95": boot_ci(yte, s, roc_auc_score),
             "pr_auc": round(average_precision_score(yte, s), 4)}
        for rate in (0.15, 0.30):
            cut = np.quantile(oof_for[n], 1 - rate)
            mm, _ = metrics_at_cutoff(yte, s, cut)
            e[f"at_train_cutoff_{int(rate*100)}"] = mm
            rec, prec, nf, _ = recall_precision_at_rate(yte, s, rate)
            e[f"top{int(rate*100)}pct"] = {"recall": round(rec, 4), "precision": round(prec, 4), "n_flagged": nf}
        test_eval[n] = e
    p_s = test_scores[primary]
    test_eval[primary]["recall@30_ci95"] = boot_ci(yte, p_s, lambda yy, ss: recall_precision_at_rate(yy, ss, .30)[0])
    test_eval[primary]["brier"] = round(brier_score_loss(yte, p_s), 4)
    R["test_holdout"] = test_eval

    # coefficients of primary LR (train fit), for reason codes
    lr = fitted["LR"]; coefs = lr.named_steps["clf"].coef_[0]
    tnames = [n.split("__", 1)[1] for n in lr.named_steps["prep"].get_feature_names_out()]
    R["lr_coefficients_std"] = sorted([{"var": f, "coef_std": round(float(c), 3), "or_per_sd": round(float(np.exp(c)), 3)}
                                       for f, c in zip(tnames, coefs)], key=lambda d: -abs(d["coef_std"]))
    # permutation importance of the primary model on train (AUC drop), for explainability
    from sklearn.inspection import permutation_importance
    pi = permutation_importance(fitted[primary], Xtr, ytr, scoring="roc_auc", n_repeats=20, random_state=C.SEED)
    R["permutation_importance_train"] = sorted([{"var": f, "auc_drop": round(float(m), 4), "sd": round(float(s), 4)}
                                                for f, m, s in zip(FEATS, pi.importances_mean, pi.importances_std)],
                                               key=lambda d: -d["auc_drop"])

    # ---------------------------------------------------- E. AQ7 trade-off table (train OOF + test)
    o = oofs[primary]; trade = []
    for rate in FLAG_RATES:
        rec, prec, nf, _ = recall_precision_at_rate(ytr, o, rate)
        cut = np.quantile(o, 1 - rate); mt, _ = metrics_at_cutoff(yte, p_s, cut)
        trade.append({"flag_rate": rate, "train_oof_recall": round(rec, 4), "train_oof_precision": round(prec, 4),
                      "per_100_students_flagged": int(round(rate * 100)), "per_100_true_pos_caught": round(rec * ytr.mean() * 100, 1),
                      "test_flag_rate": mt["flag_rate"], "test_recall": mt["recall"], "test_precision": mt["precision"]})
    R["aq7_tradeoff"] = trade
    feasible = [t for t in trade if t["train_oof_recall"] >= 0.60 and t["flag_rate"] <= 0.30]
    R["aq7_feasible_point"] = feasible[0] if feasible else None
    rr = np.linspace(0.01, 0.99, 99)
    need = next((r for r in rr if recall_precision_at_rate(ytr, o, r)[0] >= 0.60), None)
    R["aq7_flag_rate_needed_for_recall60_train"] = round(float(need), 2) if need is not None else None

    # ---------------------------------------------------- F. AQ6 fairness (train OOF and test) at 30%
    fair = {}
    ftr = fv[fv.split == "train"].reset_index(drop=True); fte = fv[fv.split == "test"].reset_index(drop=True)
    assert (ftr.resp_id.values == tr.resp_id.values).all() and (fte.resp_id.values == te.resp_id.values).all()
    _, flag_tr = metrics_at_cutoff(ytr, o, np.quantile(o, 0.70))
    _, flag_te = metrics_at_cutoff(yte, p_s, np.quantile(o, 0.70))
    for part, ff, yy, fl in (("train_oof", ftr, ytr, flag_tr), ("test", fte, yte, flag_te)):
        fair[part] = {}
        for g in C.FAIRNESS_AUDIT:
            res = {}
            for lvl in sorted(ff[g].unique()):
                m = (ff[g] == lvl).values
                tp = int((fl & m & (yy == 1)).sum()); pos = int((m & (yy == 1)).sum()); nfl = int((fl & m).sum())
                res[lvl] = {"n": int(m.sum()), "pos": pos, "flag_rate": round(nfl / m.sum(), 3),
                            "recall": round(tp / max(pos, 1), 3), "precision": round(tp / max(nfl, 1), 3)}
            gaps = {k: round(abs(np.diff([res[l][k] for l in res]))[0], 3) for k in ("recall", "precision", "flag_rate")}
            # bootstrap CI for recall gap
            rng = np.random.default_rng(C.SEED); gl = []
            lv = list(res)
            for _ in range(1000):
                b = rng.choice(len(yy), len(yy), replace=True)
                r_ = []
                for l in lv:
                    mm_ = (ff[g].values[b] == l); pp = (mm_ & (yy[b] == 1)).sum()
                    r_.append(((fl[b] & mm_ & (yy[b] == 1)).sum() / pp) if pp else np.nan)
                gl.append(abs(r_[0] - r_[1]))
            res["gaps"] = gaps; res["recall_gap_ci95"] = [round(float(np.nanpercentile(gl, 2.5)), 3), round(float(np.nanpercentile(gl, 97.5)), 3)]
            fair[part][g] = res
    R["aq6_fairness_at30"] = fair

    # ---------------------------------------------------- G. Error analysis (test, primary, 30% train cutoff)
    _, fl = metrics_at_cutoff(yte, p_s, np.quantile(o, 0.70))
    grp = np.where(fl & (yte == 1), "TP", np.where(fl & (yte == 0), "FP", np.where(~fl & (yte == 1), "FN", "TN")))
    ea = te.assign(group=grp)
    R["error_analysis_test"] = {g: {"n": int((grp == g).sum()), **{f: round(float(ea.loc[grp == g, f].median()), 2) for f in
                                                                   ["attendance_pct", "english_ord", "social_media_hours", "study_hours", "current_semester"]}}
                                for g in ("TP", "FN", "FP", "TN")}

    # reason codes: top-2 contributions (coef * standardized value) for 3 flagged pseudonymous test cases
    sc = lr.named_steps["prep"].transform(Xte)
    contrib = sc * coefs
    flagged_idx = np.where(fl)[0][:3]
    rc = []
    for i in flagged_idx:
        top = np.argsort(-contrib[i])[:2]
        rc.append({"resp_id": te.resp_id[i], "risk_score_primary": round(float(p_s[i]), 3),
                   "risk_score_lr": round(float(test_scores["LR"][i]), 3),
                   "top_contributors_lr": [{"term": tnames[j], "value": None if tnames[j].startswith("english") else
                                            (None if pd.isna(Xte.loc[i, tnames[j]]) else float(Xte.loc[i, tnames[j]])),
                                            "english_ord": int(Xte.loc[i, "english_ord"]),
                                            "contribution": round(float(contrib[i, j]), 3)} for j in top]})
    R["reason_code_examples"] = rc
    allc = pd.read_csv(C.INTERIM / "sape_typed.csv")["cgpa"].dropna()
    R["cgpa_heaping"] = {"top_values": {str(k): int(v) for k, v in allc.round(2).value_counts().head(5).items()},
                         "n_in_3.10_3.20": int(allc.between(3.10, 3.199).sum())}

    # ---------------------------------------------------- Figures
    # M4-F1 ROC + PR (train OOF)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for name, col, lbl in (("LR", S1, "Logistic Regression"), ("RF", S3, "Random Forest"), ("B1_attendance_rule", S2, "Baseline: chuyên cần")):
        fpr, tpr, _ = roc_curve(ytr, oofs[name]); axes[0].plot(fpr, tpr, color=col, lw=2, label=f"{lbl} (AUC {roc_auc_score(ytr, oofs[name]):.3f})")
        pr, rc_, _ = precision_recall_curve(ytr, oofs[name]); axes[1].plot(rc_, pr, color=col, lw=2, label=lbl)
    axes[0].plot([0, 1], [0, 1], color=INK2, ls=":", lw=1.2); axes[0].set_xlabel("Tỷ lệ dương giả (FPR)"); axes[0].set_ylabel("Recall (TPR)")
    axes[0].set_title("ROC (OOF, train)", loc="left", color=INK); axes[0].legend(frameon=False, loc="lower right", fontsize=11)
    axes[1].axhline(ytr.mean(), color=INK2, ls=":", lw=1.2); axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
    axes[1].set_title(f"Precision-Recall (tỷ lệ nền {ytr.mean():.3f})", loc="left", color=INK)
    fig.tight_layout(); save(fig, "M4F1_roc_pr_oof.png")

    # M4-F2 recall vs flag rate (AQ7)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    rates = np.linspace(0.02, 0.6, 59)
    for name, col, lbl in (("LR", S1, "Logistic Regression"), ("B1_attendance_rule", S2, "Baseline: chuyên cần")):
        ax.plot(rates * 100, [recall_precision_at_rate(ytr, oofs[name], r)[0] * 100 for r in rates], color=col, lw=2, label=lbl)
    ax.plot(rates * 100, rates * 100, color=INK2, ls=":", lw=1.2, label="Chọn ngẫu nhiên")
    ax.axhline(60, color=INK, ls="--", lw=1.2); ax.axvline(30, color=INK, ls="--", lw=1.2); ax.axvline(15, color=INK2, ls="-.", lw=1.0)
    ax.text(31, 4, "trần 30%", color=INK, fontsize=11); ax.text(16, 4, "kịch bản 15%", color=INK2, fontsize=11); ax.text(1, 62, "mục tiêu recall 60%", color=INK, fontsize=11)
    ax.set_xlabel("Tỷ lệ sinh viên được gắn cờ (%)"); ax.set_ylabel("Recall (%)"); ax.legend(frameon=False, loc="lower right")
    ax.set_title("Đánh đổi recall - tải tư vấn (OOF trên train)", loc="left", color=INK)
    save(fig, "M4F2_recall_vs_flagrate.png")

    # M4-F3 adjusted OR forest
    terms = R["diagnostic_adjusted_logit"]["terms"]
    fig, ax = plt.subplots(figsize=(8, 5.2))
    yy_ = np.arange(len(terms))[::-1]
    for yi, t in zip(yy_, terms):
        col = S2 if t["p"] < 0.05 else S1
        ax.plot([t["ci_low"], t["ci_high"]], [yi, yi], color=col, lw=2); ax.plot(t["or"], yi, "o", color=col, ms=8)
    ax.axvline(1, color=INK2, ls=":", lw=1.2); ax.set_xscale("log")
    ax.set_yticks(yy_, [VN[t["var"]] + (" (1 SD)" if t["scale"] == "per 1 SD" else "") for t in terms])
    ax.set_xlabel("Odds ratio (thang log), CI 95%"); ax.grid(axis="y", visible=False)
    ax.set_title("Hồi quy logistic điều chỉnh: liên hệ với CGPA < 2.75 (train)", loc="left", color=INK)
    save(fig, "M4F3_adjusted_or.png")

    # M4-F4 reduction path
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot([p["n"] for p in path], [p["auc"] for p in path], "o-", color=S1, lw=2, ms=7)
    ax.axhline(0.95 * full_auc, color=INK, ls="--", lw=1.2); ax.text(len(FEATS) - 0.2, 0.95 * full_auc + 0.004, "95% AUC đầy đủ", ha="right", color=INK, fontsize=11)
    ax.axvline(reduced["n"], color=S2, ls="-.", lw=1.2)
    ax.plot(best["n"], best["auc"], "o", ms=12, mfc="none", mec=S2, mew=2)
    ax.annotate(f"AUC cao nhất: {best['n']} biến", xy=(best["n"], best["auc"]), xytext=(best["n"] + 3.5, best["auc"] + 0.004),
                color=INK, fontsize=11, arrowprops={"arrowstyle": "->", "color": INK2})
    ax.set_xlabel("Số biến giữ lại"); ax.set_ylabel("AUC (CV trên train)"); ax.invert_xaxis()
    ax.set_title(f"Rút gọn bộ tín hiệu: quy tắc 95% chọn {reduced['n']} biến; đề xuất {best['n']} biến", loc="left", color=INK)
    save(fig, "M4F4_reduction_path.png")

    # M4-F5 calibration (OOF)
    fig, ax = plt.subplots(figsize=(6.4, 5))
    pt, pp = calibration_curve(ytr, oofs["LR"], n_bins=8, strategy="quantile")
    ax.plot(pp, pt, "o-", color=S1, lw=2, ms=7, label="LR (class_weight=balanced)")
    ax.plot([0, 1], [0, 1], color=INK2, ls=":", lw=1.2, label="Hiệu chỉnh hoàn hảo")
    ax.set_xlabel("Xác suất dự đoán trung bình"); ax.set_ylabel("Tỷ lệ dương quan sát"); ax.legend(frameon=False, loc="upper left")
    ax.set_title("Hiệu chỉnh xác suất (OOF, train)", loc="left", color=INK)
    save(fig, "M4F5_calibration.png")

    # M4-F6 fairness recall by group (train OOF)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    labels, vals, ns = [], [], []
    for g, names in (("gender", {"Female": "Nữ", "Male": "Nam"}), ("living_with", {"Family": "Sống cùng gia đình", "Bachelor": "Ở trọ"})):
        for lvl, nm in names.items():
            d = fair["train_oof"][g][lvl]; labels.append(nm); vals.append(d["recall"] * 100); ns.append(f"{int(round(d['recall']*d['pos']))}/{d['pos']}")
    yv = np.arange(len(labels))[::-1]
    ax.barh(yv, vals, color=S1, height=0.55)
    for yi, v, n in zip(yv, vals, ns):
        ax.text(v + 0.8, yi, f"{v:.1f}% ({n})", va="center", color=INK, fontsize=12)
    ax.set_yticks(yv, labels); ax.set_xlim(0, 100); ax.set_xlabel("Recall tại tỷ lệ gắn cờ 30% (%)"); ax.grid(axis="y", visible=False)
    ax.set_title("Recall theo phân nhóm kiểm định công bằng (OOF, train)", loc="left", color=INK)
    save(fig, "M4F6_fairness_recall.png")

    (OUT / "experiment_results.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    return R


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ["cv_train", "primary_rule", "test_holdout", "reduction", "aq7_feasible_point",
                                        "aq7_flag_rate_needed_for_recall60_train", "calibration_oof", "group_importance_cv",
                                        "sensitivity_threshold_train_cv"]}, ensure_ascii=False, indent=1, default=float))
