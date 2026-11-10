"""Milestone 3 - Data Understanding & Data Quality profiling (evidence tables + figures).

Chạy sau prepare_data.py:  python src/profile_data.py
Nguyên tắc: thống kê đơn biến/chất lượng dùng toàn bộ dữ liệu; mọi phân tích hai biến với
biến mục tiêu CHỈ dùng training partition (test set được khóa cho Milestone 4).
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as C

OUT = C.REPORTS / "milestone3"
FIG = OUT / "figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
S1, S2 = "#2a78d6", "#eb6834"          # slot 1: nhóm còn lại, slot 2: nhóm cần hỗ trợ (CGPA < 2.75)
plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 13, "axes.titlesize": 14, "axes.labelsize": 13,
    "xtick.labelsize": 12, "ytick.labelsize": 12, "legend.fontsize": 12,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "figure.dpi": 150, "savefig.bbox": "tight",
})
LABEL = {0: "CGPA ≥ 2.75", 1: "CGPA < 2.75 (cần hỗ trợ)"}


def save(fig, name):
    fig.savefig(FIG / name, facecolor="white")
    plt.close(fig)


def main() -> dict:
    FIG.mkdir(parents=True, exist_ok=True)
    raw = pd.read_excel(C.RAW_FILE).rename(columns=C.RENAME)
    df = pd.read_csv(C.INTERIM / "sape_typed.csv")
    lab_all = df[df["cgpa"].notna()].copy()                      # 1.155 có CGPA (gồm 140 nghi điền khuyết)
    lab = df[df["needs_support"].notna()].copy()                  # 1.015 nhãn chính
    lab["needs_support"] = lab["needs_support"].astype(int)
    tr = lab[lab["split"] == "train"].copy()
    res: dict = {}

    # ---------- profiling đơn biến (toàn bộ dữ liệu)
    num = ["study_hours", "study_sessions", "attendance_pct", "social_media_hours", "skill_dev_hours",
           "current_semester", "credits_completed", "cgpa", "prev_sgpa", "age"]
    prof = []
    for c in num:
        s = df[c]
        q1, q3 = s.quantile([.25, .75])
        iqr = q3 - q1
        prof.append({"var": c, "n": int(s.notna().sum()), "missing": int(s.isna().sum()),
                     "mean": round(s.mean(), 2), "median": round(s.median(), 2), "std": round(s.std(), 2),
                     "min": s.min(), "max": s.max(), "skew": round(s.skew(), 2),
                     "zeros": int((s == 0).sum()),
                     "iqr_outliers": int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())})
    res["numeric_profile"] = prof
    res["missing_raw_cells"] = int(raw.isna().sum().sum())
    res["missing_after_typing"] = {c: int(n) for c, n in df[list(C.RENAME.values())].isna().sum().items() if n > 0}
    res["cgpa_missing_by_semester"] = df.loc[df.cgpa_missing_flag == 1, "current_semester"].value_counts().sort_index().to_dict()
    res["cgpa_missing_by_admission"] = df.loc[df.cgpa_missing_flag == 1, "admission_year"].value_counts().to_dict()
    res["sem1_total"] = int((df.current_semester == 1).sum())
    res["rare_categories"] = {"smartphone_no": int((df.smartphone == 0).sum()),
                              "personal_computer_no": int((df.personal_computer == 0).sum()),
                              "suspension_yes": int((df.suspension_ever == 1).sum()),
                              "disability_yes": int((df.physical_disability == 1).sum())}
    res["representativeness"] = {
        "gender": df.gender.value_counts().to_dict(), "living_with": df.living_with.value_counts().to_dict(),
        "admission_year": df.admission_year.value_counts().sort_index().to_dict(),
        "learning_mode_online": int(df.learning_mode.sum()), "program": raw.program.unique().tolist()}
    res["target_by_threshold_all_cgpa"] = {f"<{t}": {"pos": int((lab_all.cgpa < t).sum()), "rate": round(float((lab_all.cgpa < t).mean()), 4)}
                                           for t in (2.5, 2.75, 3.0)}
    res["target_by_threshold_primary"] = {f"<{t}": {"pos": int((lab.cgpa < t).sum()), "rate": round(float((lab.cgpa < t).mean()), 4)}
                                          for t in (2.5, 2.75, 3.0)}
    res["label_status"] = df.label_status.value_counts().to_dict()
    res["cgpa_top_values"] = {str(k): int(v) for k, v in lab_all.cgpa.round(2).value_counts().head(5).items()}
    res["suspect_pair_n"] = int(df.target_imputed_suspect.sum())
    # số đoạn dòng liên tiếp theo thứ tự file gốc (resp_id tăng dần = thứ tự dòng raw)
    def _runs(mask):
        m = np.asarray(mask, dtype=bool)
        return int(m[0]) + int((m[1:] & ~m[:-1]).sum())
    order = df.sort_values("resp_id")
    res["suspect_pair_runs"] = _runs(order.target_imputed_suspect == 1)
    res["cgpa_315_rows"] = int((order.cgpa.round(2) == 3.15).sum())
    res["cgpa_315_runs"] = _runs(order.cgpa.round(2) == 3.15)
    sus = df[df.target_imputed_suspect == 1]
    res["suspect_by_admission"] = sus.admission_year.value_counts().sort_index().to_dict()
    res["raw_sgpa_mean"] = round(float(raw.prev_sgpa.mean()), 4)
    res["sem_credit_spearman"] = round(df.current_semester.corr(df.credits_completed, method="spearman"), 3)
    res["cgpa_sgpa_spearman"] = round(lab.cgpa.corr(lab.prev_sgpa, method="spearman"), 3)  # trên nhãn chính
    res["dup_feature_rows"] = int(df[C.HABIT_FEATURES + ["learning_mode", "personal_computer", "uni_transport",
                                                        "english_ord", "co_curricular", "current_semester"]].duplicated().sum())

    # ---------- hai biến với mục tiêu (CHỈ train)
    grp = tr.groupby("needs_support")
    res["train_habits_median_by_group"] = {c: {LABEL[k]: float(v) for k, v in grp[c].median().items()} for c in C.HABIT_FEATURES}
    cat_rates = {}
    for c in ["learning_mode", "personal_computer", "uni_transport", "english_ord", "co_curricular", "smartphone", "teacher_consultancy"]:
        t = tr.groupby(c)["needs_support"].agg(["count", "sum", "mean"]).round(3)
        cat_rates[c] = {str(k): {"n": int(r["count"]), "pos": int(r["sum"]), "rate": float(r["mean"])} for k, r in t.iterrows()}
    res["train_rate_by_category"] = cat_rates
    res["train_rate_by_fairness_group"] = {g: {str(k): {"n": int(r["count"]), "pos": int(r["sum"]), "rate": round(float(r["mean"]), 3)}
                                               for k, r in tr.groupby(g)["needs_support"].agg(["count", "sum", "mean"]).iterrows()}
                                           for g in ["gender", "living_with"]}
    res["train_leakage_check"] = {c: {str(k): round(float(v), 3) for k, v in tr.groupby(c)["needs_support"].mean().items()}
                                  for c in ["probation_ever", "merit_scholarship", "suspension_ever"]}
    res["train_spearman_with_cgpa"] = {c: round(tr[c].corr(tr.cgpa, method="spearman"), 3)
                                       for c in C.HABIT_FEATURES + ["current_semester", "credits_completed", "english_ord", "prev_sgpa"]}

    # ---------- Figures ------------------------------------------------------------------
    # F1 CGPA distribution + thresholds (all labeled)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.hist(lab_all.cgpa, bins=np.arange(0.0, 4.05, 0.1), color=S1, edgecolor="white", linewidth=1.2)
    top = ax.get_ylim()[1]
    for (t, ls), yf in zip([(2.5, ":"), (2.75, "-"), (3.0, "--")], (0.95, 0.83, 0.71)):
        ax.axvline(t, color=INK, ls=ls, lw=1.6)
        ax.text(t - 0.04, top * yf, f"< {t:.2f}: {int((lab_all.cgpa < t).sum())} SV", color=INK, fontsize=12, ha="right",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.set_xlim(0, 4.1)
    ax.annotate("3.15: 158 SV\n(140 cặp nghi điền khuyết)", xy=(3.15, 195), xytext=(1.0, 150), color=INK, fontsize=12,
                arrowprops={"arrowstyle": "->", "color": INK2})
    ax.set_xlabel("CGPA hiện tại (thang 4)"); ax.set_ylabel("Số sinh viên")
    ax.set_title("Phân bố CGPA và ba ngưỡng ứng viên (n = 1.155 có CGPA)", loc="left", color=INK)
    save(fig, "F01_cgpa_distribution.png")

    # F2 Missing / invalid evidence
    items = [("Cặp CGPA 3.15 / SGPA 2.68 (nghi điền khuyết)", int(df.target_imputed_suspect.sum())), ("CGPA = 0 (chưa có CGPA)", 39), ("SGPA = 0", int((raw.prev_sgpa == 0).sum())),
             ("Học kỳ > 12 (giữ, gắn cờ)", 36), ("Tổng giờ/ngày > 18 (gắn cờ)", int(df.daily_hours_gt18_flag.sum())),
             ("Skills để trống", 1), ("Chuyên cần dạng khoảng '94-98'", 1), ("Chuyên cần = 0%", 1),
             ("Giờ MXH = 20 giờ/ngày", 1), ("Năm HSC > năm nhập học", 1)]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = np.arange(len(items))[::-1]
    ax.barh(y, [v for _, v in items], color=S1, height=0.6)
    for yi, (_, v) in zip(y, items):
        ax.text(v + 0.6, yi, str(v), va="center", color=INK, fontsize=12)
    ax.set_yticks(y, [k for k, _ in items]); ax.set_xlabel("Số bản ghi"); ax.grid(axis="y", visible=False)
    ax.set_title("Bằng chứng các vấn đề chất lượng dữ liệu (n = 1.194)", loc="left", color=INK)
    save(fig, "F02_quality_issues.png")

    # F3 Habits by group (train) - box plots, small multiples
    fig, axes = plt.subplots(1, 5, figsize=(12, 4.2))
    names = {"study_hours": "Giờ học/ngày", "study_sessions": "Số lần ngồi học/ngày", "attendance_pct": "Chuyên cần (%)",
             "social_media_hours": "Giờ MXH/ngày", "skill_dev_hours": "Giờ phát triển kỹ năng/ngày"}
    for ax, c in zip(axes, C.HABIT_FEATURES):
        data = [tr.loc[tr.needs_support == k, c].dropna() for k in (0, 1)]
        bp = ax.boxplot(data, widths=0.55, patch_artist=True, showfliers=True,
                        medianprops={"color": INK, "lw": 1.6}, flierprops={"marker": "o", "ms": 3, "alpha": .4})
        for patch, col in zip(bp["boxes"], (S1, S2)):
            patch.set_facecolor(col); patch.set_alpha(.85); patch.set_edgecolor("white")
        ax.set_xticks([1, 2], ["≥ 2.75", "< 2.75"]); ax.set_title(names[c], fontsize=12, color=INK)
    fig.suptitle(f"Thói quen học tập tự báo cáo theo nhóm CGPA (training partition, n = {len(tr)})", x=0.01, ha="left", color=INK, fontsize=14)
    fig.tight_layout()
    save(fig, "F03_habits_by_group_train.png")

    # F4 attendance distribution (ceiling / skew)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df.attendance_pct.dropna(), bins=np.arange(0, 102.5, 2.5), color=S1, edgecolor="white", linewidth=1.2)
    ax.set_xlabel("Chuyên cần tự báo cáo (%)"); ax.set_ylabel("Số sinh viên")
    ax.set_title(f"Chuyên cần lệch trái, dồn ở 100% (skew = {df.attendance_pct.skew():.2f}; n = 1.193)", loc="left", color=INK)
    save(fig, "F04_attendance_distribution.png")

    # F5 positive rate by categorical condition (train)
    rows = []
    lbl = {"learning_mode": ("Offline", "Online"), "personal_computer": ("Không có PC", "Có PC"),
           "uni_transport": ("Không đi xe trường", "Đi xe trường"), "co_curricular": ("Không ngoại khóa", "Có ngoại khóa")}
    for c, (a, b) in lbl.items():
        for k, name in ((0, a), (1, b)):
            d = tr[tr[c] == k]; rows.append((name, d.needs_support.mean(), len(d)))
    for k, name in ((1, "Tiếng Anh Basic"), (2, "Tiếng Anh Intermediate"), (3, "Tiếng Anh Advanced")):
        d = tr[tr.english_ord == k]; rows.append((name, d.needs_support.mean(), len(d)))
    fig, ax = plt.subplots(figsize=(8, 5.4))
    y = np.arange(len(rows))[::-1]
    ax.barh(y, [r[1] * 100 for r in rows], color=S2, height=0.6)
    ax.axvline(tr.needs_support.mean() * 100, color=INK, ls="--", lw=1.4, zorder=1)
    for yi, (nm, r, n) in zip(y, rows):
        ax.text(r * 100 + 0.4, yi, f"{r*100:.1f}% (n={n})", va="center", color=INK, fontsize=11, zorder=3,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.set_yticks(y, [r[0] for r in rows]); ax.set_xlabel("Tỷ lệ CGPA < 2.75 (%)"); ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(r[1] for r in rows) * 100 + 9)
    ax.set_title(f"Tỷ lệ cần hỗ trợ theo điều kiện học tập (train; đường đứt = {tr.needs_support.mean()*100:.1f}%)", loc="left", color=INK)
    save(fig, "F05_rate_by_condition_train.png")

    # F6 semester vs credits (collinearity, sem > 12)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    m = df.semester_gt12_flag == 1
    ax.scatter(df.loc[~m, "current_semester"], df.loc[~m, "credits_completed"], s=16, color=S1, alpha=.45, label="Học kỳ ≤ 12")
    ax.scatter(df.loc[m, "current_semester"], df.loc[m, "credits_completed"], s=26, color=S2, alpha=.9, label="Học kỳ > 12 (36 SV)")
    ax.set_xlabel("Current Semester"); ax.set_ylabel("Số tín chỉ đã hoàn thành"); ax.legend(frameon=False, loc="lower right")
    ax.set_title(f"Học kỳ và tín chỉ đồng biến mạnh (Spearman ρ = {res['sem_credit_spearman']})", loc="left", color=INK)
    save(fig, "F06_semester_vs_credits.png")

    # F7 representativeness: admission year
    fig, ax = plt.subplots(figsize=(8, 4))
    ay = df.admission_year.value_counts().sort_index()
    ax.bar(ay.index.astype(str), ay.values, color=S1, width=0.7)
    for x, v in zip(ay.index.astype(str), ay.values):
        ax.text(x, v + 4, str(v), ha="center", color=INK, fontsize=11)
    ax.set_xlabel("Năm nhập học"); ax.set_ylabel("Số phiếu"); ax.grid(axis="x", visible=False)
    ax.set_title("Mẫu tập trung ở các khóa 2019–2022 (1.114/1.194 phiếu)", loc="left", color=INK)
    save(fig, "F07_admission_year.png")

    # F8 fairness group composition (train)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    groups = [("Nữ", tr[tr.gender == "Female"]), ("Nam", tr[tr.gender == "Male"]),
              ("Sống cùng gia đình", tr[tr.living_with == "Family"]), ("Ở trọ (Bachelor)", tr[tr.living_with == "Bachelor"])]
    y = np.arange(len(groups))[::-1]
    ax.barh(y, [g.needs_support.mean() * 100 for _, g in groups], color=S2, height=0.55)
    for yi, (nm, g) in zip(y, groups):
        ax.text(g.needs_support.mean() * 100 + 0.4, yi, f"{g.needs_support.mean()*100:.1f}% ({int(g.needs_support.sum())}/{len(g)})",
                va="center", color=INK, fontsize=12)
    ax.set_yticks(y, [g[0] for g in groups]); ax.set_xlabel("Tỷ lệ CGPA < 2.75 (%)"); ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 28)
    ax.set_title("Tỷ lệ nền và số ca dương theo phân nhóm kiểm định công bằng (train)", loc="left", color=INK)
    save(fig, "F08_fairness_groups_train.png")

    # F9 Spearman correlation matrix (train) - diverging blue/red, neutral midpoint
    cols = C.HABIT_FEATURES + ["current_semester", "credits_completed", "english_ord", "cgpa"]
    short = ["Giờ học", "Số lần học", "Chuyên cần", "Giờ MXH", "Giờ kỹ năng", "Học kỳ", "Tín chỉ", "Tiếng Anh", "CGPA"]
    cm = tr[cols].corr(method="spearman").values
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f1f0ed", "#e34948"])
    fig, ax = plt.subplots(figsize=(7.6, 6.4))
    im = ax.imshow(cm, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)), short, rotation=45, ha="right"); ax.set_yticks(range(len(cols)), short)
    ax.grid(False)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{cm[i, j]:.2f}", ha="center", va="center", fontsize=10, color=INK)
    fig.colorbar(im, ax=ax, shrink=.8, label="Spearman ρ")
    ax.set_title(f"Tương quan hạng giữa các biến số (train, n = {len(tr)})", loc="left", color=INK)
    save(fig, "F09_spearman_train.png")

    (OUT / "profile_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
