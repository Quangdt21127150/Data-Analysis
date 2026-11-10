#!/usr/bin/env python3
"""Student Risk Screening toolkit (nhóm N02, học phần Khoa học Phân tích Dữ liệu).

Tổng quát hóa quy trình Milestone 2-5 thành công cụ chạy được trên bất kỳ bảng dữ liệu người học nào:

  profile  : hiểu dữ liệu + đánh giá chất lượng + gợi ý vai trò biến (rò rỉ, nhạy cảm) -> suggested_config.json
  prepare  : làm sạch theo cấu hình, tạo nhãn, loại nhãn nghi vấn, split phân tầng có kiểm soát rò rỉ
  analyze  : chẩn đoán (Mann-Whitney/Chi-square + Holm, logit điều chỉnh), mô hình sàng lọc so với baseline
             (CV lặp + holdout một lần), rút gọn bộ tín hiệu, công bằng, đánh đổi ngưỡng, hiệu chỉnh, phân tích lỗi
  report   : báo cáo Markdown có số liệu + đối chiếu tiêu chí thành công + giới hạn/governance
  run      : prepare -> analyze -> report

Ví dụ:
  python risk_screening.py profile data.csv --target "Target" --out work/
  python risk_screening.py run --config work/config.json
Yêu cầu: pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib (openpyxl nếu đọc .xlsx).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SENSITIVE_KW = ["gender", "sex", "age", "income", "salary", "wealth", "health", "disab", "special need", "marital", "relationship",
                "romantic", "nation", "nacional", "ethnic", "race", "religio", "address", "displaced", "debtor", "tuition",
                "pstatus", "famsize", "medu", "fedu", "mjob", "fjob", "mother", "father", "guardian", "parent", "family",
                "living with", "international", "dalc", "walc", "alcohol", "giới tính", "tuổi", "thu nhập", "sức khỏe", "khuyết tật"]
LEAK_KW = ["gpa", "cgpa", "sgpa", "grade", "score", "mark", "final", "result", "g1", "g2", "g3", "probation", "suspension",
           "scholarship", "consult", "approved", "evaluations", "2nd sem", "credited", "điểm", "cảnh cáo", "học bổng"]
NEG_OUTCOME_RE = r"drop|fail|withdr|at.?risk|unsuccess|dismiss|repeat|bỏ học|trượt|không đạt|rớt"
TEXT_KW = ["skills", "interest", "comment", "note", "email", "student id", "họ tên"]


# ============================================================================ I/O helpers
def read_table(path, sheet=None):
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(p, sheet_name=sheet or 0)
    else:
        df = pd.read_csv(p, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def jdump(obj, path):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o)
    return str(o)


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(path).resolve().parent
    for k in ("data_path", "out_dir"):
        if k in cfg and not Path(cfg[k]).is_absolute():
            cfg[k] = str((base / cfg[k]).resolve())
    cfg.setdefault("out_dir", str(base / "output"))
    cfg.setdefault("seed", 2026)
    cfg.setdefault("test_size", 0.2)
    cfg.setdefault("cv_folds", 5)
    cfg.setdefault("cv_repeats", 5)
    cfg.setdefault("capacity", 0.30)
    cfg.setdefault("alt_capacity", 0.15)
    cfg.setdefault("success", {"auc": 0.70, "recall": 0.60, "max_recall_gap": 0.10, "reduction": 1 / 3})
    cfg.setdefault("features", {"numeric": [], "categorical": []})
    cfg.setdefault("exclude", {})
    cfg.setdefault("fairness_audit", [])
    return cfg


def num_like(s: pd.Series):
    """Tỷ lệ giá trị đọc được thành số (bỏ NaN)."""
    v = s.dropna().astype(str).str.strip()
    if v.empty:
        return 0.0
    return pd.to_numeric(v.str.replace(",", ".", regex=False), errors="coerce").notna().mean()


def kw_hit(name, kws):
    n = name.lower()
    return [k for k in kws if re.search(r"(^|[^a-z])" + re.escape(k) + r"($|[^a-z])", n) or (len(k) > 4 and k in n)]


# ============================================================================ PROFILE
def cmd_profile(args):
    from sklearn.metrics import roc_auc_score
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    df = read_table(args.data, args.sheet)
    prof = {"file": str(Path(args.data).resolve()), "sha256": sha256(args.data), "rows": int(len(df)), "columns": int(df.shape[1]),
            "full_duplicate_rows": int(df.duplicated().sum()), "missing_cells": int(df.isna().sum().sum()), "columns_detail": []}
    tgt = args.target
    y_bin = None
    if tgt:
        if tgt not in df.columns:
            sys.exit(f"Không thấy cột mục tiêu '{tgt}'. Các cột: {list(df.columns)}")
        ts = df[tgt]
        if pd.api.types.is_numeric_dtype(ts):
            pos = ts[ts > 0]
            qs = {f"q{int(q * 100)}": float(pos.quantile(q)) for q in (0.05, 0.10, 0.15, 0.20, 0.25)} if len(pos) else {}
            prof["target"] = {"type": "numeric", "describe": ts.describe().round(3).to_dict(), "zeros": int((ts == 0).sum()),
                              "quantiles_of_positive": qs}
            thr = qs.get("q15")
            if thr is not None:
                y_bin = (ts < thr).astype(float).where(ts > 0)
        else:
            vc = ts.astype(str).value_counts()
            prof["target"] = {"type": "categorical", "value_counts": vc.to_dict()}
            bad = [v for v in vc.index if re.search(NEG_OUTCOME_RE, str(v), re.I)]
            pos_guess = bad[0] if bad else vc.index[-1]
            prof["target"]["positive_class_guess"] = {"class": str(pos_guess), "reason": "tên lớp mang nghĩa kết quả bất lợi" if bad else
                                                      "không nhận ra lớp kết quả bất lợi - tạm lấy lớp hiếm nhất, PHẢI xác nhận"}
            y_bin = (ts.astype(str) == pos_guess).astype(float)   # lớp dương tạm để sàng lọc rò rỉ
    suggested = {"numeric": [], "categorical": []}
    exclude = {"leakage_candidates": [], "sensitive": [], "constant_or_id": [], "free_text": []}
    fixes = {"range_to_mid": [], "missing_codes": {}}
    for c in df.columns:
        s = df[c]
        d = {"column": c, "dtype": str(s.dtype), "n_unique": int(s.nunique(dropna=True)), "missing": int(s.isna().sum()),
             "examples": [str(x) for x in s.dropna().unique()[:5]]}
        flags = []
        numeric = pd.api.types.is_numeric_dtype(s)
        if not numeric and num_like(s) >= 0.95 and s.nunique() > 5:
            bad = s.dropna().astype(str)[pd.to_numeric(s.dropna().astype(str), errors="coerce").isna()]
            flags.append(f"cột số bị lẫn chuỗi: {bad.unique()[:5].tolist()}")
            if bad.str.match(r"^\s*\d+(\.\d+)?\s*-\s*\d+(\.\d+)?\s*$").any():
                fixes["range_to_mid"].append(c)
            numeric = True
        if s.nunique(dropna=True) <= 1:
            flags.append("hằng số"); exclude["constant_or_id"].append(c)
        elif not numeric and (s.nunique() > 15 or kw_hit(c, TEXT_KW)):
            flags.append(f"văn bản tự do / phân loại lực lượng cao ({s.nunique()} mức) - gom nhóm hoặc loại"); exclude["free_text"].append(c)
        elif numeric and s.nunique() == len(s):
            flags.append("có thể là ID"); exclude["constant_or_id"].append(c)
        if numeric:
            v = pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce") if not pd.api.types.is_numeric_dtype(s) else s
            d.update({"min": float(v.min()), "max": float(v.max()), "median": float(v.median()), "skew": round(float(v.skew()), 2),
                      "zeros": int((v == 0).sum())})
            vc = v.round(4).value_counts()
            if len(vc) >= 3 and vc.iloc[0] / len(v.dropna()) >= 0.08 and vc.iloc[0] >= 3 * vc.iloc[1]:
                flags.append(f"dồn đống: giá trị {vc.index[0]} chiếm {vc.iloc[0]}/{len(v.dropna())} (gấp {vc.iloc[0] / vc.iloc[1]:.1f} lần giá trị kế tiếp) - kiểm tra điền khuyết")
            if (v == 0).sum() > 0 and (v > 0).sum() > 0 and v[v > 0].min() >= 1 and kw_hit(c, LEAK_KW + ["attendance", "chuyên cần"]):
                flags.append(f"{int((v == 0).sum())} giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0")
        sens, leak = kw_hit(c, SENSITIVE_KW), kw_hit(c, LEAK_KW)
        if c == tgt:
            d["role"] = "target"
        else:
            if y_bin is not None:
                try:
                    m = y_bin.notna()
                    x = pd.to_numeric(s, errors="coerce") if numeric else s.astype(str).map(
                        s.astype(str)[m].groupby(y_bin[m]).count().to_dict() and s.astype(str)[m].groupby(s.astype(str)[m]).apply(lambda g: y_bin[g.index].mean()))
                    mm = m & x.notna()
                    if mm.sum() > 30 and y_bin[mm].nunique() == 2:
                        auc = roc_auc_score(y_bin[mm], x[mm])
                        d["single_feature_auc_screen"] = round(max(auc, 1 - auc), 3)
                        if max(auc, 1 - auc) >= 0.80:
                            flags.append(f"liên hệ rất mạnh với nhãn (AUC đơn biến {max(auc, 1 - auc):.2f}) - nghi rò rỉ")
                            if c not in exclude["leakage_candidates"]:
                                exclude["leakage_candidates"].append(c)
                except Exception:
                    pass
            if leak and c not in exclude["leakage_candidates"]:
                flags.append(f"tên gợi ý biến kết quả/hệ quả ({', '.join(leak)}) - kiểm tra thời điểm phát sinh")
                exclude["leakage_candidates"].append(c)
            if sens:
                flags.append(f"thuộc tính nhạy cảm ({', '.join(sens)})"); exclude["sensitive"].append(c)
            listed = any(c in v for v in exclude.values())
            if not listed:
                (suggested["numeric"] if numeric and s.nunique() > 2 and not kw_hit(c, ["yes", "no"]) else suggested["categorical"]).append(c)
        d["flags"] = flags
        prof["columns_detail"].append(d)
    # Nhãn nghi điền khuyết: giá trị dồn đống của biến mục tiêu đi kèm một giá trị cố định ở cột số khác
    suspect_rules = []
    if tgt and pd.api.types.is_numeric_dtype(df[tgt]):
        vc = df[tgt].round(4).value_counts()
        if len(vc) >= 3 and vc.iloc[0] >= 3 * vc.iloc[1] and vc.iloc[0] / len(df) >= 0.05 and vc.index[0] != 0:
            hv = vc.index[0]; rows = df[df[tgt].round(4) == hv]
            for c in df.columns:
                if c != tgt and pd.api.types.is_numeric_dtype(df[c]):
                    cv_ = rows[c].round(4).value_counts()
                    if len(cv_) and cv_.iloc[0] / len(rows) >= 0.8 and (df[c].round(4) == cv_.index[0]).sum() <= 1.2 * cv_.iloc[0]:
                        suspect_rules.append({tgt: float(hv), c: float(cv_.index[0]), "_evidence": f"{int(cv_.iloc[0])}/{len(rows)} dòng có {tgt} = {hv} đồng thời {c} = {cv_.index[0]}"})
    prof["suggested_roles"] = {"features": suggested, "exclude": exclude, "fixes": fixes, "suspect_label_rules": suspect_rules}
    jdump(prof, out / "profile.json")
    cfg = {
        "project": Path(args.data).stem, "data_path": str(Path(args.data).resolve()), "sheet": args.sheet, "out_dir": str((out / "output").resolve()),
        "id_column": None,
        "target": ({"column": tgt, "type": "threshold_below", "threshold": prof["target"]["quantiles_of_positive"].get("q15"), "zero_is_missing": True,
                    "sensitivity_thresholds": []} if tgt and prof["target"]["type"] == "numeric"
                   else {"column": tgt, "type": "classes", "positive_classes": [prof["target"]["positive_class_guess"]["class"]] if tgt else [],
                    "_positive_class_note": prof["target"]["positive_class_guess"]["reason"] if tgt else ""}),
        "features": suggested, "exclude": {"leakage": exclude["leakage_candidates"], "sensitive": exclude["sensitive"],
                                          "other": exclude["constant_or_id"] + exclude["free_text"]},
        "fairness_audit": exclude["sensitive"][:2], "range_to_mid": fixes["range_to_mid"], "missing_codes": {}, "valid_ranges": {},
        "suspect_label_rules": [{k: v for k, v in r.items() if not k.startswith("_")} for r in suspect_rules], "capacity": 0.30, "alt_capacity": 0.15, "seed": 2026, "test_size": 0.2,
        "success": {"auc": 0.70, "recall": 0.60, "max_recall_gap": 0.10, "reduction": 0.3333},
        "_note": "Gợi ý tự động: PHẢI rà soát vai trò từng biến theo domain (thời điểm phát sinh, rò rỉ, nhạy cảm) và chốt ngưỡng nhãn bằng căn cứ nghiệp vụ trước khi chạy prepare.",
    }
    jdump(cfg, out / "suggested_config.json")
    lines = [f"# Data profile: {Path(args.data).name}", "", f"- Kích thước: {prof['rows']} dòng × {prof['columns']} cột; SHA-256 `{prof['sha256'][:16]}…`",
             f"- Dòng trùng hoàn toàn: {prof['full_duplicate_rows']}; ô khuyết: {prof['missing_cells']}", ""]
    if tgt:
        lines += ["## Biến mục tiêu", "```", json.dumps(prof["target"], ensure_ascii=False, indent=1, default=_json_default), "```", ""]
    lines += ["## Cờ chất lượng và vai trò gợi ý", "", "| Cột | Kiểu | Unique | Khuyết | Cờ |", "|---|---|---|---|---|"]
    for d in prof["columns_detail"]:
        lines.append(f"| {d['column']} | {d['dtype']} | {d['n_unique']} | {d['missing']} | {'; '.join(d['flags']) or '-'} |")
    lines += ["", "## Vai trò gợi ý (cần người phân tích xác nhận)", "```", json.dumps(prof["suggested_roles"], ensure_ascii=False, indent=1), "```"]
    (out / "profile.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"profile": str(out / "profile.md"), "suggested_config": str(out / "suggested_config.json"),
                      "leakage_candidates": exclude["leakage_candidates"], "sensitive": exclude["sensitive"]}, ensure_ascii=False, indent=1))


# ============================================================================ PREPARE
def build_label(df, t):
    col = df[t["column"]]
    if t["type"] in ("threshold_below", "threshold_above"):
        v = pd.to_numeric(col, errors="coerce")
        if t.get("zero_is_missing", False):
            v = v.mask(v == 0)
        y = (v < t["threshold"]) if t["type"] == "threshold_below" else (v > t["threshold"])
        return y.astype(float).where(v.notna()), v
    pos = set(map(str, t["positive_classes"]))
    y = col.astype(str).isin(pos).astype(float).where(col.notna())
    return y, col


def cmd_prepare(cfg):
    from sklearn.model_selection import train_test_split
    out = Path(cfg["out_dir"]); out.mkdir(parents=True, exist_ok=True)
    log = []
    raw = read_table(cfg["data_path"], cfg.get("sheet"))
    df = raw.copy()
    log.append({"step": "load", "rows": len(df), "sha256": sha256(cfg["data_path"])})
    idc = cfg.get("id_column")
    if not idc:
        df.insert(0, "_rid", [f"R{i:05d}" for i in range(1, len(df) + 1)]); idc = "_rid"
        log.append({"step": "key", "rule": "tạo khóa giả danh _rid theo thứ tự dòng"})
    feats_num, feats_cat = list(cfg["features"].get("numeric", [])), list(cfg["features"].get("categorical", []))
    banned = set(sum([list(v) for v in cfg["exclude"].values()], [])) | {cfg["target"]["column"]}
    clash = sorted(banned & set(feats_num + feats_cat))
    if clash:
        sys.exit(f"Cấu hình mâu thuẫn: biến vừa là đặc trưng vừa bị loại: {clash}")
    for c in cfg.get("range_to_mid", []):
        s = df[c].astype(str).str.strip()
        m = s.str.match(r"^\d+(\.\d+)?\s*-\s*\d+(\.\d+)?$")
        df.loc[m, c] = s[m].str.split("-", expand=True).astype(float).mean(axis=1)
        log.append({"step": "type", "rule": f"{c}: giá trị dạng khoảng -> trung điểm", "rows": int(m.sum())})
    for c in feats_num:
        before = df[c].isna().sum()
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False).replace({"nan": None, "None": None}), errors="coerce") \
            if not pd.api.types.is_numeric_dtype(df[c]) else df[c].astype(float)
        if df[c].isna().sum() > before:
            log.append({"step": "type", "rule": f"{c}: ép kiểu số", "new_missing": int(df[c].isna().sum() - before)})
    for c in feats_cat:
        df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan})
    for c, codes in cfg.get("missing_codes", {}).items():
        m = df[c].isin(codes); df[c] = df[c].mask(m)
        log.append({"step": "missing", "rule": f"{c}: mã {codes} -> NaN", "rows": int(m.sum())})
    for c, (lo, hi) in cfg.get("valid_ranges", {}).items():
        v = pd.to_numeric(df[c], errors="coerce"); m = (v < lo) | (v > hi)
        df[c] = v.mask(m)
        log.append({"step": "invalid", "rule": f"{c}: ngoài [{lo}, {hi}] -> NaN", "rows": int(m.sum())})
    y, tv = build_label(df, cfg["target"])
    status = np.where(y.isna(), "no_target", "observed").astype(object)
    sus = pd.Series(False, index=df.index)
    for rule in cfg.get("suspect_label_rules", []):
        m = pd.Series(True, index=df.index)
        for c, val in rule.items():
            m &= pd.to_numeric(raw[c], errors="coerce").round(4).eq(round(float(val), 4)) if isinstance(val, (int, float)) else raw[c].astype(str).eq(str(val))
        sus |= m
    status = np.where(sus & (status == "observed"), "suspect", status)
    log.append({"step": "label", "rule": json.dumps(cfg["target"], ensure_ascii=False), "observed": int((status == "observed").sum()),
                "no_target": int((status == "no_target").sum()), "suspect": int((status == "suspect").sum())})
    df["_y"] = y; df["_label_status"] = status
    obs = df.index[df["_label_status"] == "observed"]
    tr, te = train_test_split(obs, test_size=cfg["test_size"], random_state=cfg["seed"], stratify=df.loc[obs, "_y"].astype(int))
    df["_split"] = "unlabeled"; df.loc[tr, "_split"] = "train"; df.loc[te, "_split"] = "test"
    sidx = df.index[df["_label_status"] == "suspect"]
    if len(sidx) >= 5:
        s_tr, s_te = train_test_split(sidx, test_size=cfg["test_size"], random_state=cfg["seed"])
        df.loc[s_tr, "_split"] = "train_suspect"; df.loc[s_te, "_split"] = "test_suspect"
    alt = {}
    for thr in cfg["target"].get("sensitivity_thresholds", []):
        t2 = dict(cfg["target"], threshold=thr); yy, _ = build_label(df, t2)
        df[f"_y_t{thr}"] = yy; alt[str(thr)] = f"_y_t{thr}"
    audit = [c for c in cfg.get("fairness_audit", []) if c in df.columns]
    keep = [idc, "_split", "_label_status", "_y"] + list(alt.values()) + feats_num + feats_cat + [c for c in audit if c not in feats_num + feats_cat]
    prep = df[keep].copy()
    prep.to_csv(out / "prepared.csv", index=False, encoding="utf-8-sig")
    lab = prep[prep._split.isin(["train", "test"])]
    val = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "raw_sha256": sha256(cfg["data_path"]),
           "rows_raw": len(raw), "rows_labeled": int(len(lab)), "positives": int(lab._y.sum()), "base_rate": round(float(lab._y.mean()), 4),
           "train": {"n": int((lab._split == "train").sum()), "pos": int(lab[lab._split == "train"]._y.sum())},
           "test": {"n": int((lab._split == "test").sum()), "pos": int(lab[lab._split == "test"]._y.sum())},
           "label_status": prep._label_status.value_counts().to_dict(), "n_features": len(feats_num + feats_cat),
           "banned_in_features": sorted(banned & set(feats_num + feats_cat)), "missing_in_features": {c: int(n) for c, n in lab[feats_num + feats_cat].isna().sum().items() if n},
           "key_unique": bool(prep[idc].is_unique), "sensitivity_targets": alt}
    assert val["key_unique"] and not val["banned_in_features"]
    jdump(val, out / "validation.json"); jdump(log, out / "transformation_log.json")
    print(json.dumps(val, ensure_ascii=False, indent=1, default=_json_default))
    return val


# ============================================================================ ANALYZE
def _models(num, cat, seed):
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    tl = []
    if num:
        tl.append(("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num))
    if cat:
        tl.append(("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                                    ("oh", OneHotEncoder(handle_unknown="ignore", min_frequency=5, sparse_output=False))]), cat))
    tr = []
    if num:
        tr.append(("num", SimpleImputer(strategy="median"), num))
    if cat:
        tr.append(("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                                    ("oh", OneHotEncoder(handle_unknown="ignore", min_frequency=5, sparse_output=False))]), cat))
    lr = Pipeline([("prep", ColumnTransformer(tl)), ("clf", LogisticRegression(class_weight="balanced", max_iter=3000))])
    rf = Pipeline([("prep", ColumnTransformer(tr)), ("clf", RandomForestClassifier(n_estimators=400, min_samples_leaf=10, max_features="sqrt",
                                                                                    class_weight="balanced_subsample", random_state=seed, n_jobs=-1))])
    return {"LR": lr, "RF": rf}


def _oof(model, X, y, k, seed):
    from sklearn.base import clone
    from sklearn.model_selection import StratifiedKFold
    o = np.zeros(len(y))
    for a, b in StratifiedKFold(k, shuffle=True, random_state=seed).split(X, y):
        o[b] = clone(model).fit(X.iloc[a], y[a]).predict_proba(X.iloc[b])[:, 1]
    return o


def _at_rate(y, s, rate):
    n = int(np.ceil(rate * len(s))); idx = np.argsort(-s, kind="mergesort")[:n]
    tp = int(y[idx].sum())
    return tp / max(int(y.sum()), 1), tp / max(n, 1)


def _cut(y, s, cut):
    f = s >= cut; tp = int((f & (y == 1)).sum()); fp = int((f & (y == 0)).sum()); fn = int((~f & (y == 1)).sum())
    return {"flag_rate": round(float(f.mean()), 4), "recall": round(tp / max(tp + fn, 1), 4), "precision": round(tp / max(tp + fp, 1), 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": int((~f & (y == 0)).sum())}, f


def _boot(y, s, fn, n=1000, seed=2026):
    rng = np.random.default_rng(seed); v = []
    for _ in range(n):
        b = rng.integers(0, len(y), len(y))
        if 0 < y[b].sum() < len(b):
            v.append(fn(y[b], s[b]))
    return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]


def _cv(model, X, y, k, reps, seed, cap, alt):
    from sklearn.metrics import average_precision_score, roc_auc_score
    rows, first = [], None
    for r in range(reps):
        o = _oof(model, X, y, k, seed + r)
        first = o if first is None else first
        rc, pc = _at_rate(y, o, cap); ra, pa = _at_rate(y, o, alt)
        rows.append({"auc": roc_auc_score(y, o), "pr_auc": average_precision_score(y, o), "recall@cap": rc, "precision@cap": pc,
                     "recall@alt": ra, "precision@alt": pa})
    d = pd.DataFrame(rows)
    return {k_: {"mean": round(float(d[k_].mean()), 4), "sd": round(float(d[k_].std(ddof=1)), 4) if len(d) > 1 else 0.0} for k_ in d}, first


def cmd_analyze(cfg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import statsmodels.api as sm
    from scipy import stats
    from sklearn.base import clone
    from sklearn.calibration import calibration_curve
    from sklearn.dummy import DummyClassifier
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve, roc_auc_score, roc_curve
    from statsmodels.stats.multitest import multipletests

    out = Path(cfg["out_dir"]); fig = out / "figures"; fig.mkdir(parents=True, exist_ok=True)
    seed, K, REP, CAP, ALT = cfg["seed"], cfg["cv_folds"], cfg["cv_repeats"], cfg["capacity"], cfg["alt_capacity"]
    num, cat = list(cfg["features"].get("numeric", [])), list(cfg["features"].get("categorical", []))
    feats = num + cat
    pv = pd.read_csv(out / "prepared.csv", encoding="utf-8-sig", keep_default_na=True)
    for c in cat:
        pv[c] = pv[c].astype("object").where(pv[c].notna(), np.nan).astype(str).replace({"nan": np.nan})
    tr, te = pv[pv._split == "train"].reset_index(drop=True), pv[pv._split == "test"].reset_index(drop=True)
    Xtr, ytr, Xte, yte = tr[feats], tr._y.astype(int).values, te[feats], te._y.astype(int).values
    R = {"config": {k: cfg[k] for k in ("project", "target", "capacity", "alt_capacity", "seed", "cv_folds", "cv_repeats", "success") if k in cfg},
         "data": {"train_n": len(tr), "train_pos": int(ytr.sum()), "test_n": len(te), "test_pos": int(yte.sum()), "features": feats},
         "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__}}
    import sklearn; R["versions"]["sklearn"] = sklearn.__version__
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e4e3df"})
    S1, S2, S3, INK = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b"

    # ---- diagnostics (train only)
    diag = []
    for c in num:
        a, b = tr.loc[ytr == 1, c].dropna(), tr.loc[ytr == 0, c].dropna()
        if len(a) > 2 and len(b) > 2:
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            diag.append({"var": c, "type": "numeric", "test": "Mann-Whitney U", "median_pos": float(a.median()), "median_neg": float(b.median()),
                         "effect": round(float(2 * u / (len(a) * len(b)) - 1), 3), "effect_name": "rank-biserial r (dương: nhóm dương cao hơn)", "p": float(p)})
    for c in cat:
        tab = pd.crosstab(tr[c].fillna("NA"), ytr)
        if tab.shape[0] < 2 or tab.shape[1] < 2:
            continue
        chi2, p, _, exp = stats.chi2_contingency(tab, correction=False); test = "Chi-square"
        if tab.shape == (2, 2) and (exp < 5).any():
            p = stats.fisher_exact(tab.values)[1]; test = "Fisher exact"
        rates = (tab[1] / tab.sum(axis=1)).round(3)
        diag.append({"var": c, "type": "categorical", "test": test, "effect": round(float(np.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))), 3),
                     "effect_name": "Cramér's V", "p": float(p), "rates_by_level": {str(k): float(v) for k, v in rates.items()},
                     "n_by_level": {str(k): int(v) for k, v in tab.sum(axis=1).items()}})
    if diag:
        adj = multipletests([d["p"] for d in diag], method="holm")[1]
        for d, pa in zip(diag, adj):
            d["p_holm"] = float(pa); d["significant"] = bool(pa < 0.05 and abs(d["effect"]) >= 0.1)
    R["diagnostics"] = sorted(diag, key=lambda d: d.get("p_holm", 1))
    try:
        Xd = tr[num].copy().fillna(tr[num].median()) if num else pd.DataFrame(index=tr.index)
        for c in num:
            sd = Xd[c].std(); Xd[c] = (Xd[c] - Xd[c].mean()) / (sd if sd > 0 else 1)
        if cat:
            dm = pd.get_dummies(tr[cat].fillna("NA"), drop_first=False, dtype=float)
            drop = [f"{c}_{tr[c].fillna('NA').mode()[0]}" for c in cat]
            dm = dm.drop(columns=[d for d in drop if d in dm.columns])
            dm = dm.loc[:, dm.sum() >= 10]
            Xd = pd.concat([Xd, dm], axis=1)
        Xd = Xd.loc[:, Xd.std() > 0]
        lg = sm.Logit(ytr, sm.add_constant(Xd.astype(float))).fit(disp=0, maxiter=200)
        ci = lg.conf_int()
        R["adjusted_logit"] = {"pseudo_r2": round(float(lg.prsquared), 4), "llr_p": float(lg.llr_pvalue),
                               "note": "biến số: OR mỗi 1 độ lệch chuẩn; biến phân loại: so với mức phổ biến nhất",
                               "terms": sorted([{"term": v, "or": round(float(np.exp(lg.params[v])), 3), "ci_low": round(float(np.exp(ci.loc[v, 0])), 3),
                                                 "ci_high": round(float(np.exp(ci.loc[v, 1])), 3), "p": float(lg.pvalues[v])} for v in Xd.columns],
                                               key=lambda t: t["p"])}
    except Exception as e:
        R["adjusted_logit"] = {"error": f"Không ước lượng được (đa cộng tuyến/tách biệt hoàn toàn): {e}"}

    # ---- models
    M = _models(num, cat, seed)
    cv, oofs = {}, {}
    cv["B0_prior"], oofs["B0_prior"] = _cv(DummyClassifier(strategy="prior"), Xtr, ytr, K, REP, seed, CAP, ALT)
    uni = {}
    for f in feats:
        m1 = _models([f] if f in num else [], [f] if f in cat else [], seed)["LR"]
        uni[f] = float(np.mean([roc_auc_score(ytr, _oof(m1, Xtr[[f]], ytr, K, seed + r)) for r in range(2)]))
    best1 = max(uni, key=uni.get)
    R["single_feature_cv_auc"] = dict(sorted(((k, round(v, 4)) for k, v in uni.items()), key=lambda t: -t[1]))
    mB1 = _models([best1] if best1 in num else [], [best1] if best1 in cat else [], seed)["LR"]
    cv["B1_best_single"], oofs["B1_best_single"] = _cv(mB1, Xtr[[best1]], ytr, K, REP, seed, CAP, ALT)
    for n_, m_ in M.items():
        cv[n_], oofs[n_] = _cv(m_, Xtr, ytr, K, REP, seed, CAP, ALT)
    primary = "RF" if (cv["RF"]["auc"]["mean"] - cv["LR"]["auc"]["mean"] >= 0.02 and cv["RF"]["recall@cap"]["mean"] >= cv["LR"]["recall@cap"]["mean"]) else "LR"
    R["baseline_single_feature"] = best1
    R["primary_rule"] = {"rule": "LR trừ khi RF hơn ≥ 0.02 AUC CV và recall@capacity không kém (đặt trước)", "primary": primary}

    # ---- reduction (backward elimination, LR)
    def cvauc(fs, reps):
        mm = _models([f for f in fs if f in num], [f for f in fs if f in cat], seed)["LR"]
        return float(np.mean([roc_auc_score(ytr, _oof(mm, Xtr[fs], ytr, K, seed + r)) for r in range(reps)]))
    full = cvauc(feats, REP); path = [{"n": len(feats), "removed": None, "auc": round(full, 4), "features": list(feats)}]; cur = list(feats)
    while len(cur) > 1:
        trial = {f: cvauc([x for x in cur if x != f], 2) for f in cur}
        drop = max(trial, key=trial.get); cur = [x for x in cur if x != drop]
        path.append({"n": len(cur), "removed": drop, "auc": round(cvauc(cur, 3), 4), "features": list(cur)})
    ok = [p for p in path if p["auc"] >= 0.95 * full]
    sel = min(ok, key=lambda p: p["n"]); best = max(path, key=lambda p: (p["auc"], -p["n"]))
    R["reduction"] = {"full_auc_cv": round(full, 4), "rule_95_selected": sel, "best_on_path": best, "path": path,
                      "reduction_rule_95": round(1 - sel["n"] / len(feats), 4), "reduction_best": round(1 - best["n"] / len(feats), 4)}

    # ---- final fit + single holdout evaluation
    fitted = {n_: clone(m_).fit(Xtr, ytr) for n_, m_ in M.items()}
    fitted["B1_best_single"] = clone(mB1).fit(Xtr[[best1]], ytr)
    bf = best["features"]
    mBest = _models([f for f in bf if f in num], [f for f in bf if f in cat], seed)["LR"]
    fitted["LR_reduced_best"] = clone(mBest).fit(Xtr[bf], ytr)
    oofs["LR_reduced_best"] = _oof(mBest, Xtr[bf], ytr, K, seed)
    cols_of = {"B1_best_single": [best1], "LR_reduced_best": bf}
    scores = {n_: f.predict_proba(Xte[cols_of.get(n_, feats)])[:, 1] for n_, f in fitted.items()}
    test = {}
    for n_, s in scores.items():
        e = {"auc": round(float(roc_auc_score(yte, s)), 4), "auc_ci95": _boot(yte, s, roc_auc_score), "pr_auc": round(float(average_precision_score(yte, s)), 4)}
        for lab_, rate in (("cap", CAP), ("alt", ALT)):
            e[f"at_{lab_}"], _ = _cut(yte, s, np.quantile(oofs[n_], 1 - rate))
        test[n_] = e
    ps = scores[primary]
    test[primary]["recall_at_cap_ci95"] = _boot(yte, ps, lambda a, b: _at_rate(a, b, CAP)[0])
    R["cv_train"], R["test_holdout"] = cv, test
    o = oofs[primary]
    R["calibration_oof"] = {"brier": round(float(brier_score_loss(ytr, o)), 4), "brier_constant": round(float(brier_score_loss(ytr, np.full(len(ytr), ytr.mean()))), 4),
                            "mean_pred": round(float(o.mean()), 4), "base_rate": round(float(ytr.mean()), 4)}
    pi = permutation_importance(fitted[primary], Xtr, ytr, scoring="roc_auc", n_repeats=10, random_state=seed)
    R["permutation_importance"] = sorted([{"var": f, "auc_drop": round(float(m), 4)} for f, m in zip(feats, pi.importances_mean)], key=lambda d: -d["auc_drop"])

    # ---- threshold trade-off
    trade = []
    for rate in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
        rc, pc = _at_rate(ytr, o, rate); mt, _ = _cut(yte, ps, np.quantile(o, 1 - rate))
        trade.append({"flag_rate": rate, "oof_recall": round(rc, 4), "oof_precision": round(pc, 4), "lift": round(rc / rate, 2),
                      "test_flag_rate": mt["flag_rate"], "test_recall": mt["recall"], "test_precision": mt["precision"]})
    R["threshold_tradeoff"] = trade
    need = next((r for r in np.linspace(0.01, 0.99, 99) if _at_rate(ytr, o, r)[0] >= cfg["success"]["recall"]), None)
    R["flag_rate_needed_for_target_recall"] = round(float(need), 2) if need is not None else None

    # ---- fairness
    fair = {}
    _, ftr = _cut(ytr, o, np.quantile(o, 1 - CAP)); _, fte = _cut(yte, ps, np.quantile(o, 1 - CAP))
    for g in [c for c in cfg.get("fairness_audit", []) if c in pv.columns]:
        fair[g] = {}
        for part, d_, yy, fl in (("train_oof", tr, ytr, ftr), ("test", te, yte, fte)):
            gv = d_[g]
            if pd.api.types.is_numeric_dtype(gv) and gv.nunique() > 6:
                med = tr[g].median(); gv = np.where(gv <= med, f"<= {med:g}", f"> {med:g}")
            gv = pd.Series(gv).astype(str).values
            lv = [l for l in pd.Series(gv).value_counts().index if ((gv == l) & (yy == 1)).sum() >= 5][:4]
            res = {}
            for l in lv:
                m = gv == l; pos = int((m & (yy == 1)).sum()); nf = int((fl & m).sum()); tp = int((fl & m & (yy == 1)).sum())
                res[l] = {"n": int(m.sum()), "pos": pos, "flag_rate": round(nf / m.sum(), 3), "recall": round(tp / max(pos, 1), 3), "precision": round(tp / max(nf, 1), 3)}
            if len(res) >= 2:
                rec = [v["recall"] for v in res.values()]
                rng = np.random.default_rng(seed); gaps = []
                for _ in range(500):
                    b = rng.integers(0, len(yy), len(yy)); r_ = []
                    for l in res:
                        mm = gv[b] == l; pp = (mm & (yy[b] == 1)).sum()
                        r_.append((fl[b] & mm & (yy[b] == 1)).sum() / pp if pp else np.nan)
                    gaps.append(np.nanmax(r_) - np.nanmin(r_))
                res["_max_recall_gap"] = round(max(rec) - min(rec), 3)
                res["_gap_ci95"] = [round(float(np.nanpercentile(gaps, 2.5)), 3), round(float(np.nanpercentile(gaps, 97.5)), 3)]
            fair[g][part] = res
    R["fairness_at_capacity"] = fair

    # ---- error analysis (test)
    _, fl = _cut(yte, ps, np.quantile(o, 1 - CAP))
    grp = np.where(fl & (yte == 1), "TP", np.where(fl & (yte == 0), "FP", np.where(~fl & (yte == 1), "FN", "TN")))
    top = [d["var"] for d in R["permutation_importance"][:4] if d["var"] in num]
    R["error_profile_test"] = {g: {"n": int((grp == g).sum()), **{f: (round(float(te.loc[grp == g, f].median()), 3) if (grp == g).any() else None) for f in top}}
                               for g in ("TP", "FN", "FP", "TN")}

    # ---- sensitivity
    sens = {}
    for thr, col in json.loads(Path(out / "validation.json").read_text(encoding="utf-8")).get("sensitivity_targets", {}).items():
        ys = tr[col].astype(int).values
        if 5 <= ys.sum() < len(ys) - 5:
            s_, _ = _cv(M["LR"], Xtr, ys, K, max(2, REP // 2), seed, CAP, ALT)
            sens[f"threshold_{thr}"] = {"pos": int(ys.sum()), "auc": s_["auc"], "recall@cap": s_["recall@cap"]}
    trs = pv[pv._split.isin(["train", "train_suspect"])].reset_index(drop=True)
    if (trs._split == "train_suspect").any():
        ys = trs._y.astype(int).values
        s_, _ = _cv(M["LR"], trs[feats], ys, K, max(2, REP // 2), seed, CAP, ALT)
        sens["include_suspect_labels"] = {"n": len(trs), "auc": s_["auc"], "recall@cap": s_["recall@cap"]}
    R["sensitivity"] = sens

    # ---- verdict vs success criteria
    sc = cfg["success"]; gaps = [v["train_oof"].get("_max_recall_gap") for v in fair.values() if "train_oof" in v and "_max_recall_gap" in v["train_oof"]]
    R["success_check"] = {
        "auc": {"target": sc["auc"], "cv": cv[primary]["auc"]["mean"], "test": test[primary]["auc"], "met": bool(cv[primary]["auc"]["mean"] >= sc["auc"])},
        "recall_at_capacity": {"target": sc["recall"], "capacity": CAP, "cv": cv[primary]["recall@cap"]["mean"], "test": test[primary]["at_cap"]["recall"],
                               "met": bool(cv[primary]["recall@cap"]["mean"] >= sc["recall"])},
        "beats_baseline": {"primary_cv_auc": cv[primary]["auc"]["mean"], "baseline_cv_auc": cv["B1_best_single"]["auc"]["mean"],
                           "met": bool(cv[primary]["auc"]["mean"] - cv["B1_best_single"]["auc"]["mean"] >= 0.02)},
        "reduction": {"target": sc["reduction"], "rule_95": R["reduction"]["reduction_rule_95"], "met": bool(R["reduction"]["reduction_rule_95"] >= sc["reduction"])},
        "fairness_recall_gap": {"target": sc["max_recall_gap"], "train_oof_gaps": gaps, "met": bool(gaps and max(gaps) <= sc["max_recall_gap"]) if gaps else None},
        "banned_features": {"count": 0, "met": True},
    }

    # ---- figures
    f_, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    for n_, col, lab_ in ((primary, S1, f"{primary} (primary)"), ("B1_best_single", S2, f"Baseline: {best1}"), ("RF" if primary == "LR" else "LR", S3, "RF" if primary == "LR" else "LR")):
        fp_, tp_, _ = roc_curve(ytr, oofs[n_]); ax[0].plot(fp_, tp_, color=col, lw=2, label=f"{lab_} (AUC {roc_auc_score(ytr, oofs[n_]):.3f})")
        pr_, rc_, _ = precision_recall_curve(ytr, oofs[n_]); ax[1].plot(rc_, pr_, color=col, lw=2, label=lab_)
    ax[0].plot([0, 1], [0, 1], ":", color="#52514e"); ax[0].set_xlabel("FPR"); ax[0].set_ylabel("Recall"); ax[0].legend(frameon=False, fontsize=9, loc="lower right")
    ax[0].set_title("ROC (OOF, train)", loc="left"); ax[1].axhline(ytr.mean(), ls=":", color="#52514e"); ax[1].set_xlabel("Recall"); ax[1].set_ylabel("Precision")
    ax[1].set_title("Precision-Recall (OOF, train)", loc="left"); f_.tight_layout(); f_.savefig(fig / "roc_pr.png", dpi=150); plt.close(f_)
    f_, ax = plt.subplots(figsize=(7.5, 4.2)); rr = np.linspace(0.02, 0.6, 59)
    ax.plot(rr * 100, [_at_rate(ytr, o, r)[0] * 100 for r in rr], color=S1, lw=2, label=primary)
    ax.plot(rr * 100, [_at_rate(ytr, oofs["B1_best_single"], r)[0] * 100 for r in rr], color=S2, lw=2, label=f"Baseline: {best1}")
    ax.plot(rr * 100, rr * 100, ":", color="#52514e", label="Ngẫu nhiên"); ax.axhline(sc["recall"] * 100, ls="--", color=INK, lw=1); ax.axvline(CAP * 100, ls="--", color=INK, lw=1)
    ax.set_xlabel("Tỷ lệ gắn cờ (%)"); ax.set_ylabel("Recall (%)"); ax.legend(frameon=False); ax.set_title("Đánh đổi recall - tải can thiệp (OOF)", loc="left")
    f_.savefig(fig / "recall_vs_flag.png", dpi=150, bbox_inches="tight"); plt.close(f_)
    f_, ax = plt.subplots(figsize=(7.5, 4)); ax.plot([p["n"] for p in path], [p["auc"] for p in path], "o-", color=S1)
    ax.axhline(0.95 * full, ls="--", color=INK, lw=1); ax.invert_xaxis(); ax.set_xlabel("Số biến"); ax.set_ylabel("AUC CV")
    ax.set_title(f"Rút gọn: quy tắc 95% → {sel['n']} biến; AUC cao nhất ở {best['n']} biến", loc="left"); f_.savefig(fig / "reduction.png", dpi=150, bbox_inches="tight"); plt.close(f_)
    pt, pp = calibration_curve(ytr, o, n_bins=8, strategy="quantile")
    f_, ax = plt.subplots(figsize=(5.5, 4.5)); ax.plot(pp, pt, "o-", color=S1); ax.plot([0, 1], [0, 1], ":", color="#52514e")
    ax.set_xlabel("Xác suất dự đoán"); ax.set_ylabel("Tỷ lệ dương quan sát"); ax.set_title("Hiệu chỉnh (OOF)", loc="left"); f_.savefig(fig / "calibration.png", dpi=150, bbox_inches="tight"); plt.close(f_)
    jdump(R, out / "results.json")
    print(json.dumps({"primary": primary, "cv_auc": cv[primary]["auc"], "test_auc": test[primary]["auc"], "baseline": best1,
                      "baseline_cv_auc": cv["B1_best_single"]["auc"], "recall@cap_test": test[primary]["at_cap"]["recall"],
                      "reduction_best": best["features"], "success_check": {k: v["met"] for k, v in R["success_check"].items()}}, ensure_ascii=False, indent=1))
    return R


# ============================================================================ REPORT
def _p(x, d=1):
    return "-" if x is None else f"{x * 100:.{d}f}%"


def cmd_report(cfg):
    out = Path(cfg["out_dir"])
    V = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    R = json.loads((out / "results.json").read_text(encoding="utf-8"))
    L = json.loads((out / "transformation_log.json").read_text(encoding="utf-8"))
    pr = R["primary_rule"]["primary"]; cv, te, sc = R["cv_train"], R["test_holdout"], R["success_check"]
    t = cfg["target"]
    tdesc = (f"{t['column']} < {t['threshold']}" if t["type"] == "threshold_below" else f"{t['column']} > {t['threshold']}" if t["type"] == "threshold_above"
             else f"{t['column']} ∈ {t['positive_classes']}")
    yes = lambda b: "Đạt" if b else ("Chưa kết luận" if b is None else "Không đạt")
    L_ = [f"# Báo cáo phân tích sàng lọc người học: {cfg.get('project', '')}", "",
          f"> Sinh tự động bởi skill student-risk-screening ({datetime.now().strftime('%d/%m/%Y')}). Các con số lấy từ `results.json`; phần diễn giải cần người phân tích rà soát.", "",
          "## 1. Dữ liệu và nhãn", "",
          f"- Nguồn: `{Path(cfg['data_path']).name}` (SHA-256 `{V['raw_sha256'][:16]}…`), {V['rows_raw']} dòng.",
          f"- Nhãn dương: **{tdesc}**; tập có nhãn {V['rows_labeled']} dòng, {V['positives']} ca dương (tỷ lệ nền {_p(V['base_rate'])}).",
          f"- Trạng thái nhãn: {V['label_status']}. Train {V['train']['n']} ({V['train']['pos']} dương) / test {V['test']['n']} ({V['test']['pos']} dương), phân tầng, seed {cfg['seed']}.",
          f"- {V['n_features']} đặc trưng hợp lệ; biến bị loại: " + "; ".join(f"{k}: {', '.join(v) or '-'}" for k, v in cfg["exclude"].items()) + ".", "",
          "### Nhật ký biến đổi", "", "| Bước | Luật | Số dòng |", "|---|---|---|"]
    for x in L[1:]:
        L_.append(f"| {x['step']} | {x.get('rule', '')} | {x.get('rows', x.get('observed', ''))} |")
    L_ += ["", "## 2. Chẩn đoán (chỉ trên train; hiệu chỉnh Holm)", "", "| Biến | Kiểm định | Hiệu ứng | p (Holm) | Có ý nghĩa |", "|---|---|---|---|---|"]
    for d in R["diagnostics"]:
        L_.append(f"| {d['var']} | {d['test']} | {d['effect_name'].split(' (')[0]} = {d['effect']} | {d['p_holm']:.3g} | {'Có' if d['significant'] else 'Không'} |")
    lg = R.get("adjusted_logit", {})
    if "terms" in lg:
        L_ += ["", f"Hồi quy logistic điều chỉnh (pseudo R² = {lg['pseudo_r2']}; {lg['note']}). Các hạng tử p < 0.05:", ""]
        L_ += [f"- {x['term']}: OR {x['or']} (CI 95% {x['ci_low']}-{x['ci_high']})" for x in lg["terms"] if x["p"] < 0.05] or ["- Không có hạng tử nào p < 0.05."]
    L_ += ["", "> Diễn giải: đây là liên hệ trên dữ liệu quan sát, có thể theo chiều ngược hoặc do yếu tố gây nhiễu; không kết luận nhân quả.", "",
           "## 3. Hiệu năng sàng lọc", "", f"Baseline một tín hiệu được chọn trên train: **{R['baseline_single_feature']}**. Primary theo quy tắc đặt trước: **{pr}**.", "",
           f"| Mô hình | AUC CV | PR-AUC CV | Recall@{_p(cfg['capacity'], 0)} CV | AUC test [CI 95%] | Recall test @{_p(cfg['capacity'], 0)} |", "|---|---|---|---|---|---|"]
    for n_ in ("B0_prior", "B1_best_single", "LR", "RF", "LR_reduced_best"):
        c_ = cv.get(n_); t_ = te.get(n_)
        L_.append(f"| {n_} | {c_['auc']['mean']:.3f} ± {c_['auc']['sd']:.3f} | {c_['pr_auc']['mean']:.3f} | {_p(c_['recall@cap']['mean'])} | "
                  f"{t_['auc']:.3f} [{t_['auc_ci95'][0]:.3f}; {t_['auc_ci95'][1]:.3f}] | {_p(t_['at_cap']['recall'])} |" if c_ and t_ else
                  f"| {n_} | {c_['auc']['mean']:.3f} ± {c_['auc']['sd']:.3f} | {c_['pr_auc']['mean']:.3f} | {_p(c_['recall@cap']['mean'])} | - | - |" if c_ else
                  f"| {n_} | (đường rút gọn) | - | - | {t_['auc']:.3f} | {_p(t_['at_cap']['recall'])} |")
    cal = R["calibration_oof"]
    L_ += ["", f"Hiệu chỉnh: xác suất TB {cal['mean_pred']} so với tỷ lệ nền {cal['base_rate']} (Brier {cal['brier']} vs hằng số {cal['brier_constant']}). "
           + ("Điểm chỉ nên dùng để xếp hạng." if cal["brier"] > cal["brier_constant"] else "Xác suất tương đối hiệu chỉnh."), "",
           "## 4. Rút gọn bộ tín hiệu", "", f"- AUC CV mô hình đầy đủ: {R['reduction']['full_auc_cv']}.",
           f"- Quy tắc 95%: {R['reduction']['rule_95_selected']['n']} biến ({', '.join(R['reduction']['rule_95_selected']['features'])}).",
           f"- AUC CV cao nhất: {R['reduction']['best_on_path']['auc']} với {R['reduction']['best_on_path']['n']} biến ({', '.join(R['reduction']['best_on_path']['features'])}).",
           "- Permutation importance (top 5): " + ", ".join(f"{d['var']} ({d['auc_drop']})" for d in R["permutation_importance"][:5]) + ".", "",
           f"## 5. Công bằng tại tỷ lệ gắn cờ {_p(cfg['capacity'], 0)}", ""]
    for g, parts in R["fairness_at_capacity"].items():
        for part, res in parts.items():
            lv = {k: v for k, v in res.items() if not k.startswith("_")}
            L_.append(f"- {g} ({part}): " + "; ".join(f"{k}: recall {_p(v['recall'])}, gắn cờ {_p(v['flag_rate'])} (n={v['n']}, dương={v['pos']})" for k, v in lv.items())
                      + (f" → chênh lệch recall {_p(res.get('_max_recall_gap'))} (CI {res.get('_gap_ci95')})" if "_max_recall_gap" in res else ""))
    L_ += ["", "## 6. Đánh đổi ngưỡng (primary)", "", "| Gắn cờ | Recall OOF | Precision OOF | Lift | Recall test | Precision test |", "|---|---|---|---|---|---|"]
    L_ += [f"| {_p(x['flag_rate'], 0)} | {_p(x['oof_recall'])} | {_p(x['oof_precision'])} | {x['lift']} | {_p(x['test_recall'])} | {_p(x['test_precision'])} |" for x in R["threshold_tradeoff"]]
    L_ += ["", f"Tỷ lệ gắn cờ cần để đạt recall mục tiêu {_p(cfg['success']['recall'], 0)}: {_p(R['flag_rate_needed_for_target_recall'], 0)}.", "",
           "## 7. Độ nhạy", ""] + ([f"- {k}: AUC CV {v['auc']['mean']:.3f} ± {v['auc']['sd']:.3f}; recall@capacity {_p(v['recall@cap']['mean'])}"
                                     + (f"; ca dương {v['pos']}" if "pos" in v else f"; n = {v.get('n')}") for k, v in R["sensitivity"].items()]
                                    or ["- Không cấu hình kịch bản độ nhạy (sensitivity_thresholds / suspect_label_rules)."]) + ["",
           "## 8. Đối chiếu tiêu chí thành công (đặt trước)", "", "| Tiêu chí | Kết quả | Đánh giá |", "|---|---|---|",
           f"| AUC ≥ {sc['auc']['target']} | CV {sc['auc']['cv']:.3f}; test {sc['auc']['test']:.3f} | {yes(sc['auc']['met'])} |",
           f"| Recall ≥ {_p(sc['recall_at_capacity']['target'], 0)} khi gắn cờ {_p(sc['recall_at_capacity']['capacity'], 0)} | CV {_p(sc['recall_at_capacity']['cv'])}; test {_p(sc['recall_at_capacity']['test'])} | {yes(sc['recall_at_capacity']['met'])} |",
           f"| Vượt baseline ≥ 0.02 AUC | {sc['beats_baseline']['primary_cv_auc']:.3f} vs {sc['beats_baseline']['baseline_cv_auc']:.3f} | {yes(sc['beats_baseline']['met'])} |",
           f"| Rút gọn ≥ {_p(sc['reduction']['target'], 0)} số biến | {_p(sc['reduction']['rule_95'])} | {yes(sc['reduction']['met'])} |",
           f"| Chênh lệch recall ≤ {_p(sc['fairness_recall_gap']['target'], 0)} | {sc['fairness_recall_gap']['train_oof_gaps']} | {yes(sc['fairness_recall_gap']['met'])} |",
           "| Biến bị cấm trong mô hình = 0 | 0 | Đạt |", "",
           "## 9. Giới hạn và governance (bắt buộc rà soát)", "",
           "- Kết luận chỉ ở mức liên hệ/sàng lọc trên dữ liệu đã cho; không suy diễn nhân quả hay hiệu quả can thiệp.",
           "- Nếu dữ liệu cắt ngang (không có mốc thời gian), không tuyên bố 'dự báo sớm'.",
           "- Mọi đề xuất hỗ trợ người học phải qua phê duyệt của con người; không gán nhãn tiêu cực; diễn đạt theo hướng hỗ trợ.",
           "- Biến nhạy cảm chỉ dùng để kiểm định công bằng; tập kiểm tra nhỏ khiến CI rộng.",
           "- Kết quả không chuyển giao trực tiếp sang bối cảnh/cơ sở khác khi chưa kiểm định lại.", "",
           "Hình: `figures/roc_pr.png`, `figures/recall_vs_flag.png`, `figures/reduction.png`, `figures/calibration.png`."]
    (out / "report.md").write_text("\n".join(L_), encoding="utf-8")
    print(str(out / "report.md"))


# ============================================================================ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("profile"); p.add_argument("data"); p.add_argument("--target"); p.add_argument("--sheet"); p.add_argument("--out", default="work")
    for c in ("prepare", "analyze", "report", "run"):
        q = sub.add_parser(c); q.add_argument("--config", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "profile":
        return cmd_profile(a)
    cfg = load_config(a.config)
    if a.cmd in ("prepare", "run"):
        cmd_prepare(cfg)
    if a.cmd in ("analyze", "run"):
        cmd_analyze(cfg)
    if a.cmd in ("report", "run"):
        cmd_report(cfg)


if __name__ == "__main__":
    main()
