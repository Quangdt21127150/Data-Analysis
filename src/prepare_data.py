"""Milestone 3 - Reproducible Data Preparation Pipeline (raw -> interim -> processed).

Chạy:  python src/prepare_data.py
- Không chỉnh sửa data/raw (raw is immutable; kiểm SHA-256 trước khi chạy).
- Không fit bất kỳ phép biến đổi phụ thuộc dữ liệu nào (impute/scale/encode one-hot) ở đây:
  các phép đó được fit trên training partition bên trong pipeline mô hình ở Milestone 4.
- Ghi: data/interim/sape_typed.csv, data/processed/*.csv, data/metadata/{data_dictionary_v1.csv,
  transformation_log_v1.0.json, validation_summary_v1.0.json} (lineage nằm trong data dictionary và transformation log).
"""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config as C

LOG: list[dict] = []


def log(step: str, rule: str, n_affected: int, detail: str = "") -> None:
    LOG.append({"step": step, "rule": rule, "rows_affected": int(n_affected), "detail": detail})


# ------------------------------------------------------------------ 1. load + validate raw
def load_raw() -> pd.DataFrame:
    digest = hashlib.sha256(C.RAW_FILE.read_bytes()).hexdigest()
    assert digest == C.RAW_SHA256, f"SHA-256 mismatch: {digest}"
    df = pd.read_excel(C.RAW_FILE, engine="openpyxl")
    assert df.shape == (1194, 31), df.shape
    assert list(df.columns) == list(C.RENAME), "Schema khác tài liệu M2"
    log("1-load", "Đọc raw, kiểm SHA-256 và schema 31 cột", len(df), digest)
    return df


# ------------------------------------------------------------------ 2-6. typing, cleaning
def yes_no(s: pd.Series) -> pd.Series:
    m = s.astype(str).str.strip().str.lower().map({"yes": 1, "no": 0, "n": 0})
    return m.astype("Int64")


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=C.RENAME).copy()
    df.insert(0, "resp_id", [f"R{i:04d}" for i in range(1, len(df) + 1)])  # khóa giả danh theo thứ tự dòng
    log("4-key", "Tạo khóa giả danh resp_id theo thứ tự dòng (file không có ID)", len(df))

    # Chuyên cần: chuỗi khoảng "94-98" -> trung điểm 96; 0% với hình thức Offline -> không hợp lệ
    att_raw = df["attendance_pct"].astype(str).str.strip()
    is_range = att_raw.str.contains("-", regex=False)
    df["attendance_range_flag"] = is_range.astype(int)
    rng = att_raw[is_range].str.split("-", expand=True).astype(float).mean(axis=1)
    att = pd.to_numeric(att_raw, errors="coerce")
    att.loc[is_range] = rng
    log("3-type", "attendance_pct: giá trị dạng khoảng -> trung điểm", int(is_range.sum()), "94-98 -> 96")
    zero_att = att.eq(0)
    att.loc[zero_att] = np.nan
    df["attendance_pct"] = att.astype(float)
    log("6-invalid", "attendance_pct = 0 (hình thức Offline, CGPA 3.15) -> NaN", int(zero_att.sum()))

    # Giờ mạng xã hội > 16 giờ/ngày: không khả thi (dòng 20h + 3h học + 1h kỹ năng = 24h)
    bad_sm = df["social_media_hours"].gt(16)
    df["social_media_hours"] = df["social_media_hours"].astype(float).mask(bad_sm)
    log("6-invalid", "social_media_hours > 16 -> NaN", int(bad_sm.sum()))
    tot = df[["study_hours", "social_media_hours", "skill_dev_hours"]].sum(axis=1, min_count=1)
    df["daily_hours_gt18_flag"] = tot.gt(18).astype(int)
    log("6-flag", "Tổng giờ học + MXH + kỹ năng > 18 giờ: gắn cờ, giữ nguyên", int(df["daily_hours_gt18_flag"].sum()))

    # Năm HSC sau năm nhập học -> NaN (biến không vào mô hình, chỉ mô tả)
    bad_hsc = df["hsc_year"].gt(df["admission_year"])
    df["hsc_year"] = df["hsc_year"].astype(float).mask(bad_hsc)
    log("6-invalid", "hsc_year > admission_year -> NaN", int(bad_hsc.sum()))

    # Học kỳ > 12: giữ (tín chỉ 77-143 nhất quán với học kéo dài), chỉ gắn cờ
    df["semester_gt12_flag"] = df["current_semester"].gt(12).astype(int)
    log("6-flag", "current_semester > 12: gắn cờ, giữ nguyên", int(df["semester_gt12_flag"].sum()))

    # Chuẩn hóa nhãn phân loại
    df["health_issue"] = df["health_issue"].astype(str).str.strip().str.lower().map({"yes": "Yes", "no": "No", "n": "No"})
    log("3-label", "health_issue: no/N -> No", int(raw.iloc[:, 25].isin(["no", "N"]).sum()))
    df["relationship_status"] = df["relationship_status"].replace({"In a relationship": "Relationship"})
    log("3-label", "relationship_status: 'In a relationship' -> 'Relationship'", 1)
    df["english_level"] = df["english_level"].replace({"Advance": "Advanced"})
    df["english_ord"] = df["english_level"].map(C.ENGLISH_ORDER).astype("Int64")
    for col in ["merit_scholarship", "uni_transport", "smartphone", "personal_computer", "probation_ever",
                "suspension_ever", "teacher_consultancy", "co_curricular", "physical_disability"]:
        df[col] = yes_no(df[col])
    df["learning_mode"] = df["learning_mode"].map({"Online": 1, "Offline": 0}).astype("Int64")
    df["living_with"] = df["living_with"].map({"Family": "Family", "Bachelor": "Bachelor"})
    log("3-type", "Yes/No -> 1/0; learning_mode Online=1; english_level -> english_ord 1-3", len(df))

    # CGPA = 0: chưa có CGPA (37/39 ở học kỳ 1, 2 ở học kỳ 2, tất cả khóa 2022, tín chỉ trung vị 0)
    z = df["cgpa"].eq(0)
    df["cgpa_missing_flag"] = z.astype(int)
    df["cgpa"] = df["cgpa"].mask(z)
    log("5-missing", "cgpa = 0 -> NaN (khuyết cấu trúc: chưa có điểm tích lũy)", int(z.sum()))

    # CGPA dồn đống: cặp (CGPA 3.15, SGPA 2.68) lặp 140 lần theo từng đoạn dòng liên tiếp; SGPA trung bình
    # toàn file = 2.684 -> nghi là giá trị điền khuyết của nhà cung cấp: nhãn KHÔNG quan sát được.
    sus = df["cgpa"].round(2).eq(3.15) & df["prev_sgpa"].round(2).eq(2.68)
    df["target_imputed_suspect"] = sus.astype(int)
    log("5-missing", "Cặp (cgpa 3.15, prev_sgpa 2.68): gắn cờ nghi điền khuyết, loại khỏi tập nhãn chính", int(sus.sum()))
    df["prev_sgpa"] = df["prev_sgpa"].mask(df["prev_sgpa"].eq(0))
    log("5-missing", "prev_sgpa = 0 -> NaN (biến bị cấm trong mô hình, chỉ mô tả)", int(raw.iloc[:, 26].eq(0).sum()))

    # Biến mục tiêu: nhãn chính chỉ cho bản ghi có CGPA quan sát được và không nghi điền khuyết
    observed = df["cgpa"].notna() & ~sus
    for t, name in [(C.TARGET_THRESHOLD, "needs_support"), (2.50, "needs_support_t250"), (3.00, "needs_support_t300")]:
        df[name] = (df["cgpa"] < t).astype("Int64").mask(~observed)
    df["needs_support_incl_suspect"] = (df["cgpa"] < C.TARGET_THRESHOLD).astype("Int64").mask(df["cgpa"].isna())
    df["label_status"] = np.select([df["cgpa"].isna(), sus], ["no_cgpa", "suspect_imputed"], "observed")
    log("8-derive", f"needs_support = 1 nếu cgpa < {C.TARGET_THRESHOLD}; NaN nếu chưa có CGPA hoặc nghi điền khuyết",
        int(df["needs_support"].notna().sum()))
    return df


# ------------------------------------------------------------------ 7-9. split + views
def make_views(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    lab = df[df["needs_support"].notna()].copy()
    tr_idx, te_idx = train_test_split(lab.index, test_size=C.TEST_SIZE, random_state=C.SEED,
                                      stratify=lab["needs_support"].astype(int))
    df["split"] = "unlabeled"
    df.loc[tr_idx, "split"] = "train"
    df.loc[te_idx, "split"] = "test"
    log("9-split", f"Stratified holdout {int((1 - C.TEST_SIZE) * 100)}/{int(C.TEST_SIZE * 100)} seed={C.SEED} trên tập nhãn chính",
        len(lab), f"train={len(tr_idx)}, test={len(te_idx)}")
    sus = df.index[df["label_status"] == "suspect_imputed"]
    s_tr, s_te = train_test_split(sus, test_size=C.TEST_SIZE, random_state=C.SEED)
    df.loc[s_tr, "split"] = "train_suspect"
    df.loc[s_te, "split"] = "test_suspect"
    log("9-split", "Bản ghi nghi điền khuyết: chia 80/20 riêng, chỉ dùng cho phân tích độ nhạy", len(sus),
        f"train_suspect={len(s_tr)}, test_suspect={len(s_te)}")

    in_scope = df["split"] != "unlabeled"
    desc_cols = ["resp_id", "split", "label_status", "cgpa", "cgpa_missing_flag", "target_imputed_suspect", "needs_support",
                 "needs_support_t250", "needs_support_t300", "current_semester", "admission_year", "gender", "living_with"]
    diag_cols = (["resp_id", "split", "label_status", "cgpa", "needs_support"] + C.HABIT_FEATURES +
                 ["learning_mode", "personal_computer", "uni_transport", "english_ord", "co_curricular",
                  "current_semester", "credits_completed", "smartphone", "teacher_consultancy"])
    pred_cols = ["resp_id", "split", "label_status", "needs_support", "needs_support_t250", "needs_support_t300",
                 "needs_support_incl_suspect"] + [c if c != "english_level" else "english_ord" for c in C.MODEL_FEATURES]
    fair_cols = ["resp_id", "split", "label_status", "needs_support", "needs_support_incl_suspect", "gender", "living_with"]
    views = {
        "view_descriptive": df[desc_cols],
        "view_diagnostic": df.loc[in_scope, diag_cols],
        "view_predictive": df.loc[in_scope, pred_cols],
        "view_fairness_audit": df.loc[in_scope, fair_cols],
    }
    log("9-views", "Tạo 4 analytic-ready views theo mức analytics", len(views))
    return views


# ------------------------------------------------------------------ 10. persist + validate
DICT_ROWS = [
    # name, source field, transformation, dtype, role, sensitivity, purpose
    ("resp_id", "(không có)", "R0001..R1194 theo thứ tự dòng", "string", "key", "Thấp", "Tất cả"),
    ("split", "needs_support", "Stratified 80/20, seed 2026", "string", "split", "Thấp", "AQ4-AQ7"),
    ("cgpa", "What is your current CGPA?", "0 -> NaN", "float", "target source", "Trung bình", "AQ1"),
    ("cgpa_missing_flag", "What is your current CGPA?", "1 nếu CGPA gốc = 0", "int", "flag", "Thấp", "AQ1"),
    ("needs_support", "What is your current CGPA?", "1 nếu cgpa < 2.75; NaN nếu thiếu", "int", "target", "Trung bình", "AQ1, AQ4-AQ7"),
    ("target_imputed_suspect", "CGPA + previous SGPA", "1 nếu cặp (3.15, 2.68) - nghi điền khuyết", "int", "flag", "Thấp", "AQ1, QA"),
    ("label_status", "CGPA + cờ", "observed / no_cgpa / suspect_imputed", "string", "flag", "Thấp", "AQ1"),
    ("needs_support_incl_suspect", "What is your current CGPA?", "như needs_support nhưng giữ 140 dòng nghi điền khuyết", "int", "target (độ nhạy)", "Trung bình", "AQ4"),
    ("needs_support_t250", "What is your current CGPA?", "1 nếu cgpa < 2.50", "int", "target (độ nhạy)", "Trung bình", "AQ1, AQ4"),
    ("needs_support_t300", "What is your current CGPA?", "1 nếu cgpa < 3.00", "int", "target (độ nhạy)", "Trung bình", "AQ1, AQ4"),
    ("study_hours", "How many hour do you study daily?", "giữ nguyên (giờ/ngày)", "int", "feature - thói quen", "Thấp", "AQ2, AQ4"),
    ("study_sessions", "How many times do you seat for study in a day?", "giữ nguyên (lần/ngày)", "int", "feature - thói quen", "Thấp", "AQ2, AQ4"),
    ("attendance_pct", "Average attendance on class", "'94-98' -> 96; 0 -> NaN; ép float", "float", "feature - thói quen", "Thấp", "AQ2, AQ4"),
    ("social_media_hours", "How many hour do you spent daily in social media?", "> 16 -> NaN", "float", "feature - thói quen", "Thấp", "AQ2, AQ4"),
    ("skill_dev_hours", "How many hour do you spent daily on your skill development?", "giữ nguyên", "int", "feature - thói quen", "Thấp", "AQ2, AQ4"),
    ("learning_mode", "What is your preferable learning mode?", "Online=1, Offline=0", "int", "feature - điều kiện", "Thấp", "AQ3, AQ4"),
    ("personal_computer", "Do you have personal Computer?", "Yes=1, No=0", "int", "feature - điều kiện", "Thấp", "AQ3, AQ4"),
    ("uni_transport", "Do you use University transportation?", "Yes=1, No=0", "int", "feature - điều kiện", "Thấp", "AQ3, AQ4"),
    ("english_ord", "Status of your English language proficiency", "Basic=1, Intermediate=2, Advance(d)=3", "int", "feature - điều kiện", "Thấp", "AQ3, AQ4"),
    ("co_curricular", "Are you engaged with any co-curriculum activities?", "Yes=1, No=0", "int", "feature - điều kiện", "Thấp", "AQ3, AQ4"),
    ("current_semester", "Current Semester", "giữ nguyên; cờ > 12", "int", "feature - điều kiện", "Thấp", "AQ3, AQ4"),
    ("credits_completed", "How many Credit did you have completed?", "giữ nguyên", "int", "chẩn đoán (đa cộng tuyến với học kỳ)", "Thấp", "AQ3"),
    ("smartphone", "Do you use smart phone?", "Yes=1, No=0", "int", "chẩn đoán (gần hằng số: 16 'No')", "Thấp", "AQ3"),
    ("teacher_consultancy", "Do you attend in teacher consultancy ...?", "Yes=1, No=0", "int", "chẩn đoán (quan hệ ngược chiều), cấm trong mô hình", "Trung bình", "AQ3"),
    ("gender", "Gender", "giữ nguyên", "string", "kiểm định công bằng", "Cao", "AQ6"),
    ("living_with", "With whom you are living with?", "Family / Bachelor", "string", "kiểm định công bằng", "Cao", "AQ6"),
    ("admission_year", "University Admission year", "giữ nguyên", "int", "mô tả", "Thấp", "AQ1"),
    ("attendance_range_flag", "Average attendance on class", "1 nếu giá trị gốc dạng khoảng", "int", "flag", "Thấp", "QA"),
    ("daily_hours_gt18_flag", "3 biến giờ/ngày", "1 nếu tổng > 18", "int", "flag", "Thấp", "QA"),
    ("semester_gt12_flag", "Current Semester", "1 nếu > 12", "int", "flag", "Thấp", "QA"),
]


def validate(raw: pd.DataFrame, df: pd.DataFrame, views: dict[str, pd.DataFrame]) -> dict:
    pv_all = views["view_predictive"]
    banned_present = sorted(set(pv_all.columns) & set(C.BANNED_FROM_MODEL))
    pv = pv_all[pv_all.split.isin(["train", "test"])]
    tr, te = pv[pv.split == "train"], pv[pv.split == "test"]
    raw_att = pd.to_numeric(raw["Average attendance on class"], errors="coerce")
    sample_check = {
        "attendance_range_row": df.loc[df["attendance_range_flag"] == 1, ["resp_id", "attendance_pct"]].to_dict("records"),
        "attendance_unchanged_elsewhere": bool(np.allclose(
            df.loc[(df["attendance_range_flag"] == 0) & raw_att.ne(0).values, "attendance_pct"].values,
            raw_att[(df["attendance_range_flag"] == 0).values & raw_att.ne(0).values].values)),
        "target_matches_rule": bool(((df["cgpa"] < C.TARGET_THRESHOLD).astype(int)[df["label_status"] == "observed"]
                                     == df.loc[df["label_status"] == "observed", "needs_support"].astype(int)).all()),
        "suspect_rows_all_cgpa_315_sgpa_268": bool(df.loc[df["target_imputed_suspect"] == 1, ["cgpa", "prev_sgpa"]]
                                                   .round(2).eq([3.15, 2.68]).all().all()),
    }
    assert all(v for v in sample_check.values() if isinstance(v, bool)), f"Kiểm tra mẫu thất bại: {sample_check}"
    out = {
        "prepared_version": C.PREPARED_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_sha256": C.RAW_SHA256,
        "code_sha256": {f: hashlib.sha256((Path(__file__).parent / f).read_bytes()).hexdigest() for f in ("prepare_data.py", "config.py")},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "rows_raw": int(len(raw)), "rows_interim": int(len(df)),
        "rows_labeled": int(df["needs_support"].notna().sum()),
        "rows_unlabeled_cgpa_missing": int(df["cgpa_missing_flag"].sum()),
        "rows_target_imputed_suspect": int(df["target_imputed_suspect"].sum()),
        "label_status_counts": df["label_status"].value_counts().to_dict(),
        "split_counts": df["split"].value_counts().to_dict(),
        "target_rate_incl_suspect": round(float(df["needs_support_incl_suspect"].dropna().astype(int).mean()), 4),
        "key_unique": bool(df["resp_id"].is_unique),
        "target_rate_overall": round(float(df["needs_support"].dropna().astype(int).mean()), 4),
        "target_pos_overall": int(df["needs_support"].dropna().astype(int).sum()),
        "train_n": int(len(tr)), "test_n": int(len(te)),
        "train_pos": int(tr["needs_support"].sum()), "test_pos": int(te["needs_support"].sum()),
        "train_rate": round(float(tr["needs_support"].mean()), 4), "test_rate": round(float(te["needs_support"].mean()), 4),
        "sensitivity_pos": {"t250": int(pv["needs_support_t250"].sum()), "t300": int(pv["needs_support_t300"].sum())},
        "missing_in_predictive_view": {c: int(n) for c, n in pv.isna().sum().items() if n > 0},
        "banned_columns_in_predictive_view": banned_present,
        "n_model_features": len(C.MODEL_FEATURES),
        "flags": {f: int(df[f].sum()) for f in ["attendance_range_flag", "daily_hours_gt18_flag", "semester_gt12_flag"]},
        "sample_checks": sample_check,
        "view_shapes": {k: list(v.shape) for k, v in views.items()},
    }
    assert not banned_present, banned_present
    assert out["key_unique"] and sample_check["target_matches_rule"] and sample_check["attendance_unchanged_elsewhere"]
    return out


def main() -> dict:
    for p in (C.INTERIM, C.PROCESSED, C.META):
        p.mkdir(parents=True, exist_ok=True)
    raw = load_raw()
    df = clean(raw)
    views = make_views(df)
    df.to_csv(C.INTERIM / "sape_typed.csv", index=False, encoding="utf-8-sig")
    for name, v in views.items():
        v.to_csv(C.PROCESSED / f"{name}_{C.PREPARED_VERSION}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(DICT_ROWS, columns=["variable", "source_field", "transformation", "dtype", "role",
                                     "sensitivity", "purpose_aq"]).to_csv(
        C.META / f"data_dictionary_{C.PREPARED_VERSION}.csv", index=False, encoding="utf-8-sig")
    (C.META / f"transformation_log_{C.PREPARED_VERSION}.json").write_text(
        json.dumps(LOG, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = validate(raw, df, views)
    (C.META / f"validation_summary_{C.PREPARED_VERSION}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
