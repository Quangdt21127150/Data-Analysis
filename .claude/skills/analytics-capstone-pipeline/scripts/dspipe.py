# -*- coding: utf-8 -*-
"""dspipe.py: pipeline phân tích dữ liệu sàng lọc (screening) có thể tái lập, dùng cho mọi bộ dữ liệu bảng.

Mô-đun này đúc kết quy trình của đồ án năm milestone (hiểu dữ liệu, chuẩn bị, mô hình hóa, đánh giá, tích hợp):
    init      Phân tích nhanh dữ liệu và đề xuất tệp cấu hình config.draft.json
    profile   Kiểm tra chất lượng dữ liệu, rò rỉ, trùng lặp, mã thiếu (Milestone 2 và 3)
    prepare   Chuẩn bị dữ liệu theo cấu hình, ghi nhật ký biến đổi và mã SHA-256 (Milestone 3)
    prereg    Đăng ký trước tiêu chí thành công, khóa bằng SHA-256 (Milestone 4)
    diagnose  Mô tả và chẩn đoán: so sánh nhóm, tỷ số chênh hiệu chỉnh, hiệu chỉnh Holm (Milestone 3)
    model     Kiểm định chéo phân tầng lặp, bootstrap, hiệu chuẩn, rút gọn, công bằng (Milestone 4)
    verify    Kiểm tra chéo kết quả, mã băm và tính nhất quán (Milestone 5)
    all       Chạy lần lượt toàn bộ các bước trên

Cách chạy:
    python dspipe.py all --config config.json
Chỉ dùng pandas, numpy, scipy, scikit-learn, matplotlib; shap, statsmodels là tùy chọn.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import rankdata

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV  # noqa: E402
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score  # noqa: E402
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

# Windows: console mặc định cp1252 không in được tiếng Việt
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


try:  # joblib đi kèm scikit-learn
    from joblib import Parallel, delayed
except Exception:  # pragma: no cover
    Parallel = None

warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONWARNINGS", "ignore")  # các tiến trình con của joblib cũng im lặng

# --------------------------------------------------------------------------------------------
# Cấu hình
# --------------------------------------------------------------------------------------------
DEFAULT_CFG = {
    "project_name": "Dự án phân tích dữ liệu",
    "language": "vi",
    "team": {"name": "", "members": [], "advisor": "", "course": ""},
    "data_path": "data.csv",
    "sheet": None,
    "id_col": None,
    "features": None,                    # danh sách đặc trưng đầu vào tường minh; None = mọi cột trừ các cột bị loại
    "target": {
        "column": None,
        "type": "threshold",          # "threshold" (biến liên tục + ngưỡng) hoặc "binary" (nhãn nhị phân có sẵn)
        "positive_if": "<",           # <, <=, >, >=   (chỉ dùng cho threshold)
        "threshold": None,
        "positive_values": None,      # danh sách giá trị tính là dương (chỉ dùng cho binary)
        "missing_codes": [],          # giá trị coi là thiếu dữ liệu (ví dụ 0 trong cột điểm chưa có)
        "positive_name": "nhóm cần chú ý",
    },
    "exclude": {"leakage": [], "sensitive_for_model": [], "other": []},
    "auto_exclude_leakage_auc": 0.85,   # đặc trưng có tên gợi ý hệ quả (prev, gpa, status...) và AUC đơn lẻ từ ngưỡng này bị loại tạm thời
    "keep_despite_leakage_flag": [],     # cột đã được người dùng xác nhận là hợp lệ dù bị gắn cờ nghi rò rỉ
    "groups": {},                        # nhóm đặc trưng cho ablation: {"Tên nhóm": [cột, ...]}
    "fairness_cols": [],
    "baseline_feature": None,            # nếu None sẽ chọn đặc trưng đơn lẻ tốt nhất (có cảnh báo lạc quan)
    "flag_rates": [0.15, 0.30],
    "exclude_repeat_clusters": False,    # loại các dòng thuộc cụm giá trị lặp bất thường khỏi mẫu chính
    "criteria": {
        "auc": 0.70, "recall": 0.60, "recall_rate": 0.30, "delta_auc": 0.03,
        "max_items": None, "ablation_tolerance": 0.02,
        "calib_slope": [0.8, 1.2], "fair_gap": 0.10, "fair_ci_width": 0.20,
        "switch_delta": 0.02,
    },
    "cv": {"splits": 5, "repeats": 10, "seed": 42, "n_boot": 2000, "n_jobs": -1},
    "context": {                         # bối cảnh dữ liệu, dùng để viết phần giới hạn trung thực
        "data_source": "", "self_reported": None, "cross_sectional": None, "single_site": None, "notes": [],
    },
    "stakeholders_source": "assumed",    # "assumed" (giả định/AI mô phỏng) hoặc "interviewed" (phỏng vấn thật)
    "stakeholders": [],                  # [{"role":..., "pain":..., "decision":...}]
    "analysis_questions": [],            # [{"id":"AQ1","level":"Descriptive","question":..., "audience":...}]
    "out_dir": "outputs",
}


def deep_merge(base: dict, new: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (new or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_cfg(path: str | Path) -> dict:
    p = Path(path)
    cfg = deep_merge(DEFAULT_CFG, json.loads(p.read_text(encoding="utf-8")))
    cfg["_cfg_dir"] = str(p.resolve().parent)
    return cfg


def out_dirs(cfg: dict) -> dict:
    root = Path(cfg["_cfg_dir"]) / cfg["out_dir"]
    d = {"root": root, "tables": root / "tables", "figures": root / "figures", "data": root / "data", "logs": root / "logs"}
    for v in d.values():
        v.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------------------------
# Tiện ích chung
# --------------------------------------------------------------------------------------------
def vi(x, nd: int = 2) -> str:
    """Định dạng số kiểu Việt Nam: dấu phẩy thập phân, dấu chấm phân tách nghìn."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, nd: int = 1) -> str:
    return vi(100 * x, nd) + "%"


def sha256_of(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def save_json(obj, path: Path) -> None:
    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, Path):
            return str(o)
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=default), encoding="utf-8")


def wilson(k: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def holm(p: list[float]) -> list[float]:
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * p[i])
        adj[i] = min(1.0, run)
    return adj.tolist()


def save_fig(fig, d: dict, name: str) -> str:
    fig.tight_layout()
    path = d["figures"] / f"{name}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


PALETTE = {"main": "#1D4E89", "accent": "#C8551B", "grey": "#6B7280", "light": "#9DB8D9"}


def style_axes(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)


def load_data(cfg: dict) -> pd.DataFrame:
    p = Path(cfg["data_path"])
    if not p.is_absolute():
        p = Path(cfg["_cfg_dir"]) / p
    suf = p.suffix.lower()
    if suf in (".csv", ".txt"):
        df = pd.read_csv(p, sep=None, engine="python")
    elif suf in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(p, sheet_name=cfg["sheet"] or 0)
    elif suf == ".json":
        df = pd.read_json(p)
    elif suf == ".parquet":
        df = pd.read_parquet(p)
    else:
        raise ValueError(f"Định dạng chưa hỗ trợ: {suf}")
    df.columns = [str(c).strip() for c in df.columns]
    coerced = {}
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
            continue
        v = pd.to_numeric(s.astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False).str.strip(), errors="coerce")
        v = v.where(s.notna())
        if s.notna().sum() and v.notna().sum() >= 0.9 * s.notna().sum() and v.nunique() > 6:
            coerced[c] = int(s.notna().sum() - v.notna().sum())
            df[c] = v
    df.attrs["coerced_numeric"] = coerced
    return df


# --------------------------------------------------------------------------------------------
# Nhãn (target)
# --------------------------------------------------------------------------------------------
def build_target(df: pd.DataFrame, cfg: dict) -> tuple[pd.Series, pd.Series, list[dict]]:
    """Trả về (giá trị gốc đã xử lý mã thiếu, nhãn nhị phân 0/1 có NaN, nhật ký)."""
    t = cfg["target"]
    col = t["column"]
    if col is None or col not in df.columns:
        raise ValueError(f"Chưa khai báo hoặc không tìm thấy cột nhãn: {col!r}")
    log = []
    raw = df[col].copy()
    if t["type"] == "threshold":
        val = pd.to_numeric(raw, errors="coerce")
        for code in t.get("missing_codes") or []:
            n = int((val == code).sum())
            if n:
                log.append({"step": "target_missing_code", "n": n,
                            "detail": f"{n} dòng có {col} = {code} được coi là thiếu dữ liệu (chưa có giá trị thật)."})
            val = val.mask(val == code)
        op = t.get("positive_if", "<")
        thr = float(t["threshold"])
        cmp = {"<": val < thr, "<=": val <= thr, ">": val > thr, ">=": val >= thr}[op]
        y = cmp.astype(float).where(val.notna())
        return val, y, log
    # binary
    pv = t.get("positive_values")
    if pv is None:
        uniq = raw.dropna().unique()
        if set(map(str, uniq)) <= {"0", "1", "0.0", "1.0", "True", "False"}:
            pv = [1, 1.0, True, "1"]
        elif len(uniq) == 2:
            vc = raw.value_counts()
            pv = [vc.index[-1]]
            log.append({"step": "target_positive_guess", "n": int(vc.iloc[-1]),
                        "detail": f"Giả định lớp thiểu số {vc.index[-1]!r} là lớp dương; cần người dùng xác nhận."})
        else:
            raise ValueError("Nhãn nhị phân có hơn 2 giá trị; hãy khai báo target.positive_values.")
    y = raw.isin(pv).astype(float).where(raw.notna())
    return raw, y, log


# --------------------------------------------------------------------------------------------
# Loại cột và đặc trưng
# --------------------------------------------------------------------------------------------
def infer_types(X: pd.DataFrame, max_card: int = 25) -> tuple[list[str], list[str], list[str]]:
    num, cat, dropped = [], [], []
    for c in X.columns:
        s = X[c]
        if pd.api.types.is_bool_dtype(s):
            num.append(c)
        elif pd.api.types.is_numeric_dtype(s):
            num.append(c)
        else:
            nun = s.nunique(dropna=True)
            if nun > max_card:
                dropped.append(c)
            elif nun <= 1:
                dropped.append(c)
            else:
                cat.append(c)
    return num, cat, dropped


def feature_columns(df: pd.DataFrame, cfg: dict, auto_leak: list[str] | None = None) -> tuple[list[str], dict]:
    t = cfg["target"]["column"]
    ex = set(cfg["exclude"]["leakage"]) | set(cfg["exclude"]["sensitive_for_model"]) | set(cfg["exclude"]["other"])
    if auto_leak:
        ex |= set(auto_leak)
    ex |= {t}
    if cfg["id_col"]:
        ex.add(cfg["id_col"])
    cols = [c for c in df.columns if c not in ex and not c.startswith("_")]
    if cfg.get("features"):
        cols = [c for c in cfg["features"] if c in df.columns and c not in ex]
    X = df[cols]
    num, cat, dropped = infer_types(X)
    keep = [c for c in cols if c in num or c in cat]
    info = {"numeric": num, "categorical": cat, "dropped_constant_or_highcard": dropped}
    return keep, info


# --------------------------------------------------------------------------------------------
# PROFILE: kiểm tra chất lượng, rò rỉ, trùng lặp
# --------------------------------------------------------------------------------------------
LEAK_NAME_HINTS = re.compile(r"(prev|previous|last|final|total|result|outcome|status|grade|gpa|score|mark|label|class|probation|"
                             r"scholar|dismiss|suspend|warning|churn|default)", re.I)


def univariate_auc(X: pd.DataFrame, y: np.ndarray, num: list[str], cat: list[str], seed: int = 42) -> dict:
    """AUC ngoài fold của từng đặc trưng đứng một mình (phát hiện rò rỉ và chọn baseline)."""
    out = {}
    skf = StratifiedKFold(3, shuffle=True, random_state=seed)
    for c in num + cat:
        pre = ColumnTransformer([("n", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), [c])] if c in num else
                                [("c", Pipeline([("i", SimpleImputer(strategy="most_frequent")),
                                                 ("o", OneHotEncoder(handle_unknown="ignore", drop="if_binary"))]), [c])], sparse_threshold=0)
        pipe = Pipeline([("p", pre), ("m", LogisticRegression(max_iter=500))])
        s = np.zeros(len(y))
        try:
            for tr, te in skf.split(X, y):
                pipe.fit(X.iloc[tr], y[tr])
                s[te] = pipe.predict_proba(X.iloc[te])[:, 1]
            out[c] = float(roc_auc_score(y, s))
        except Exception:
            out[c] = float("nan")
    return out


def find_repeat_clusters(val: pd.Series, other: pd.DataFrame | None = None) -> dict | None:
    """Phát hiện cụm giá trị nhãn lặp bất thường (ví dụ 140 phiếu cùng một cặp điểm)."""
    v = val.dropna()
    if len(v) < 100 or v.nunique() < 20:
        return None
    vc = v.round(4).value_counts()
    med = float(vc.median())
    top = vc[(vc >= max(10, 5 * max(med, 1)))]
    if top.empty:
        return None
    out = {"values": [float(i) for i in top.index], "counts": [int(c) for c in top.values], "n_rows": int(top.sum()),
           "median_count": med, "col": None, "col_value": None}
    if other is not None:  # tinh chỉnh: cụm có thể là một cặp (nhãn, cột khác) lặp cùng nhau
        in_c = v.round(4).isin(top.index)
        best = None
        for c in other.columns:
            o = pd.to_numeric(other.loc[v.index[in_c.values], c], errors="coerce").dropna()
            if len(o) < 10 or pd.to_numeric(other[c], errors="coerce").nunique() < 20:
                continue
            vc2 = o.round(4).value_counts()
            share = vc2.iloc[0] / len(o)
            if share >= 0.6 and vc2.iloc[0] >= 10 and (best is None or vc2.iloc[0] > best[2]):
                best = (c, float(vc2.index[0]), int(vc2.iloc[0]))
        if best:
            out.update({"col": best[0], "col_value": best[1], "n_rows": best[2], "counts": [best[2]]})
    return out


def num_for_cluster(df: pd.DataFrame, cfg: dict) -> list[str]:
    return [c for c in df.columns if c not in (cfg["target"]["column"], cfg["id_col"]) and pd.api.types.is_numeric_dtype(df[c])]


def stage_profile(cfg: dict, df: pd.DataFrame | None = None) -> dict:
    d = out_dirs(cfg)
    df = load_data(cfg) if df is None else df
    val, y, tlog = build_target(df, cfg)
    n_raw = len(df)
    issues: list[dict] = []

    def add(sev, code, desc, n, action):
        issues.append({"id": f"Q{len(issues) + 1:02d}", "severity": sev, "code": code, "description": desc, "n_rows": int(n), "proposed_action": action})

    # Nhãn
    for e in tlog:
        add("Cao", e["step"], e["detail"], e["n"], "Chuyển thành thiếu dữ liệu và loại khỏi mẫu có nhãn.")
    miss_y = int(y.isna().sum())
    if miss_y:
        add("Cao", "target_missing", f"{miss_y} dòng thiếu nhãn.", miss_y, "Loại khỏi mẫu có nhãn; không điền khuyết nhãn.")
    # Trùng lặp
    idc = cfg["id_col"]
    if idc and idc in df.columns:
        dup_id = int(df[idc].duplicated().sum())
        if dup_id:
            add("Cao", "dup_id", f"{dup_id} mã định danh bị lặp.", dup_id, "Kiểm tra nguồn; giữ bản ghi đầu tiên nếu trùng hoàn toàn.")
    exact = int(df.drop(columns=[idc] if idc in df.columns else []).duplicated().sum())
    if exact:
        add("Trung bình", "dup_rows", f"{exact} dòng trùng hoàn toàn các cột còn lại (không tính mã định danh).", exact,
            "Giữ một bản ghi cho mỗi nhóm trùng nếu có căn cứ là nhập lặp; nếu không, giữ và chạy độ nhạy.")
    clusters = find_repeat_clusters(val, df[[c for c in num_for_cluster(df, cfg)]])
    if clusters:
        extra = f", đồng thời cùng giá trị {clusters['col_value']:g} ở cột {clusters['col']}" if clusters.get("col") else ""
        add("Cao", "repeat_cluster", f"Cụm giá trị nhãn lặp bất thường: {clusters['n_rows']} dòng có nhãn = {clusters['values'][0]:g}{extra} "
            f"(trung vị tần suất một giá trị nhãn là {clusters['median_count']:.0f}); nghi giá trị thay thế.",
            clusters["n_rows"], "Tách khỏi mẫu chính, giữ ở mẫu độ nhạy B và so sánh kết quả hai mẫu.")
    # Cột
    feat_all = [c for c in df.columns if c not in {cfg["target"]["column"], idc}]
    num_all, cat_all, dropped = infer_types(df[feat_all])
    rows = []
    for c in df.columns:
        s = df[c]
        rows.append({"column": c, "dtype": str(s.dtype), "n_missing": int(s.isna().sum()), "pct_missing": float(s.isna().mean()),
                     "n_unique": int(s.nunique(dropna=True)), "role": "target" if c == cfg["target"]["column"] else ("id" if c == idc else
                     ("numeric" if c in num_all else ("categorical" if c in cat_all else "dropped")))})
        if s.isna().mean() > 0.3 and c not in {idc}:
            add("Trung bình", "high_missing", f"Cột {c} thiếu {vi(s.isna().mean() * 100, 1)}% giá trị.", int(s.isna().sum()),
                "Cân nhắc loại cột hoặc điền khuyết trong pipeline (không điền trước khi chia fold).")
    for c in dropped:
        add("Thấp", "const_or_highcard", f"Cột {c} hằng số hoặc có quá nhiều mức ({df[c].nunique()}).", 0, "Không đưa vào mô hình.")
    # Rò rỉ: so khớp tên + AUC đơn đặc trưng
    ok = y.notna().values
    Xl, yl = df.loc[ok, feat_all], y[ok].astype(int).values
    uni = {}
    if yl.sum() >= 10 and (len(yl) - yl.sum()) >= 10:
        uni = univariate_auc(Xl, yl, [c for c in num_all], [c for c in cat_all], cfg["cv"]["seed"])
    leak_thr = cfg["auto_exclude_leakage_auc"]
    suspects, strong = [], []
    for c, a in uni.items():
        if a >= leak_thr and c in cfg["keep_despite_leakage_flag"]:
            continue
        if a >= leak_thr and not LEAK_NAME_HINTS.search(c):
            strong.append(c)
            add("Cao", "strong_feature", f"Đặc trưng {c} đứng một mình đạt AUC {vi(a, 3)}: mạnh bất thường nhưng tên không gợi ý hệ quả; cần người dùng xác nhận nó có sẵn tại thời điểm ra quyết định.",
                0, "Giữ trong mô hình nếu xác nhận hợp lệ (khai báo keep_despite_leakage_flag); loại nếu là hệ quả của nhãn.")
        elif a >= leak_thr:
            suspects.append(c)
            add("Cao", "leakage_suspect", f"Đặc trưng {c} đứng một mình đạt AUC {vi(a, 3)} (từ ngưỡng {vi(leak_thr, 2)}): nghi là một phần hoặc hệ quả của nhãn.",
                0, "Loại khỏi mô hình và nói rõ lý do; chỉ giữ nếu xác nhận có sẵn tại thời điểm ra quyết định.")
        elif LEAK_NAME_HINTS.search(c) and a >= 0.70:
            add("Trung bình", "leakage_name_hint", f"Cột {c} có tên gợi ý kết quả/hệ quả và AUC đơn lẻ {vi(a, 3)}.", 0,
                "Người dùng xác nhận thời điểm thu thập; loại nếu thu sau thời điểm quyết định.")
    # Tương quan cao
    if len(num_all) >= 2:
        cm = df[num_all].corr(numeric_only=True).abs()
        for i, a in enumerate(cm.columns):
            for b in cm.columns[i + 1:]:
                if cm.loc[a, b] >= 0.9:
                    add("Trung bình", "collinear", f"{a} và {b} tương quan tuyệt đối {vi(cm.loc[a, b], 2)}.", 0,
                        "Phân tích theo nhóm đặc trưng (ablation theo nhóm) thay vì từng biến.")
    # Mất cân bằng và cỡ mẫu
    nvalid = int(ok.sum())
    npos = int(yl.sum())
    prev = npos / nvalid if nvalid else float("nan")
    n_feat_eff = max(1, len(num_all) + len(cat_all) - len(suspects) - len(cfg["exclude"]["other"]) - len(cfg["exclude"]["sensitive_for_model"]) - len(cfg["exclude"]["leakage"]))
    if cfg.get("features"):
        n_feat_eff = max(1, len(cfg["features"]))
    epv = npos / n_feat_eff
    if prev < 0.2 or prev > 0.8:
        add("Trung bình", "imbalance", f"Tỷ lệ lớp dương {vi(prev * 100, 1)}%; dùng PR-AUC, recall và precision tại tỷ lệ gắn cờ.", 0,
            "Không dùng accuracy; dùng class_weight và đo hiệu chuẩn.")
    if epv < 10:
        add("Cao", "small_sample", f"Chỉ {npos} ca dương cho khoảng {n_feat_eff} đặc trưng (khoảng {vi(epv, 1)} ca mỗi đặc trưng).", npos,
            "Ưu tiên mô hình đơn giản có phạt; nêu rõ khoảng tin cậy rộng; không dùng hold-out nhỏ.")
    prof = {
        "n_raw": n_raw, "n_valid_label": nvalid, "n_positive": npos, "prevalence": prev, "events_per_feature": epv,
        "n_features": len(num_all) + len(cat_all), "numeric": num_all, "categorical": cat_all, "dropped": dropped,
        "univariate_auc": uni, "leakage_suspects": suspects, "strong_features": strong, "repeat_clusters": clusters, "raw_sha256": sha256_of(
            Path(cfg["data_path"]) if Path(cfg["data_path"]).is_absolute() else Path(cfg["_cfg_dir"]) / cfg["data_path"]),
        "issues": issues,
    }
    pd.DataFrame(rows).to_csv(d["tables"] / "audit_columns.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(issues).to_csv(d["tables"] / "audit_issues.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"column": k, "univariate_auc": v} for k, v in sorted(uni.items(), key=lambda kv: -kv[1])]).to_csv(
        d["tables"] / "audit_univariate_auc.csv", index=False, encoding="utf-8-sig")
    save_json(prof, d["root"] / "audit.json")
    # Hình
    lang_vi = cfg["language"] == "vi"
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    v = val.dropna()
    if cfg["target"]["type"] == "threshold" and len(v):
        ax.hist(v, bins=40, color=PALETTE["light"], edgecolor="white")
        ax.axvline(float(cfg["target"]["threshold"]), color=PALETTE["accent"], linestyle="--", linewidth=2)
        ax.set_xlabel(cfg["target"]["column"])
        ax.set_ylabel("Số quan sát" if lang_vi else "Count")
        ax.set_title(f"Phân bố {cfg['target']['column']} (đường nét đứt: ngưỡng {cfg['target']['threshold']})" if lang_vi else "Target distribution", fontsize=11)
    else:
        cnt = y.dropna().value_counts().sort_index()
        ax.bar([str(int(i)) for i in cnt.index], cnt.values, color=[PALETTE["light"], PALETTE["accent"]][:len(cnt)])
        ax.set_title("Phân bố nhãn" if lang_vi else "Label distribution", fontsize=11)
    style_axes(ax)
    save_fig(fig, d, "f01_phan_bo_nhan")
    mm = pd.DataFrame(rows).sort_values("pct_missing", ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.barh(mm["column"][::-1], 100 * mm["pct_missing"][::-1], color=PALETTE["main"])
    ax.set_xlabel("% thiếu dữ liệu" if lang_vi else "% missing")
    style_axes(ax)
    save_fig(fig, d, "f02_thieu_du_lieu")
    return prof


# --------------------------------------------------------------------------------------------
# PREPARE
# --------------------------------------------------------------------------------------------
def stage_prepare(cfg: dict) -> dict:
    d = out_dirs(cfg)
    df = load_data(cfg)
    audit = json.loads((d["root"] / "audit.json").read_text(encoding="utf-8")) if (d["root"] / "audit.json").exists() else stage_profile(cfg, df)
    log: list[dict] = [{"step": "load", "n_before": len(df), "n_after": len(df), "detail": f"Đọc {cfg['data_path']}, SHA-256 {audit['raw_sha256'][:16]}..."}]
    val, y, tlog = build_target(df, cfg)
    for e in tlog:
        log.append({"step": e["step"], "n_before": len(df), "n_after": len(df), "detail": e["detail"]})
    df = df.copy()
    df["_target_value"] = val
    df["_y"] = y
    n0 = len(df)
    df = df[df["_y"].notna()].copy()
    log.append({"step": "drop_missing_label", "n_before": n0, "n_after": len(df), "detail": "Loại dòng thiếu nhãn."})
    df["_y"] = df["_y"].astype(int)
    # Cụm lặp và dòng trùng
    clusters = audit.get("repeat_clusters")
    df["_repeat_cluster"] = False
    if clusters:
        vals = np.array(clusters["values"])
        df["_repeat_cluster"] = df["_target_value"].round(4).isin(np.round(vals, 4))
        if clusters.get("col") and clusters["col"] in df.columns:
            df["_repeat_cluster"] &= pd.to_numeric(df[clusters["col"]], errors="coerce").round(4).eq(round(clusters["col_value"], 4))
    idc = cfg["id_col"]
    cols_nodup = [c for c in df.columns if c not in ([idc] if idc else []) and not c.startswith("_")]
    df["_dup_row"] = df.duplicated(subset=cols_nodup, keep="first")
    master = df.copy()
    master["_in_primary"] = True
    if cfg["exclude_repeat_clusters"] and clusters:
        master["_in_primary"] &= ~master["_repeat_cluster"]
        log.append({"step": "primary_excludes_repeat_cluster", "n_before": len(master), "n_after": int(master["_in_primary"].sum()),
                    "detail": "Mẫu chính loại cụm giá trị nhãn lặp bất thường; mẫu độ nhạy B giữ lại."})
    n_dup = int((master["_dup_row"] & master["_in_primary"]).sum())
    if n_dup:
        master["_in_primary"] &= ~master["_dup_row"]
        log.append({"step": "drop_exact_duplicates", "n_before": len(master), "n_after": int(master["_in_primary"].sum()),
                    "detail": f"Loại {n_dup} dòng trùng hoàn toàn (giữ bản ghi đầu)."})
    primary = master[master["_in_primary"]].copy()
    sens_b = master[~master["_dup_row"]].copy()  # độ nhạy B: giữ cụm lặp
    log.append({"step": "primary_sample", "n_before": len(master), "n_after": len(primary), "detail": f"Mẫu chính {len(primary)} dòng, {int(primary['_y'].sum())} ca dương ({primary['_y'].mean() * 100:.1f}%)."})
    log.append({"step": "sensitivity_B", "n_before": len(master), "n_after": len(sens_b), "detail": f"Mẫu độ nhạy B {len(sens_b)} dòng, {int(sens_b['_y'].sum())} ca dương."})
    master.to_csv(d["data"] / "prepared_master.csv", index=False, encoding="utf-8-sig")
    primary.to_csv(d["data"] / "prepared_primary.csv", index=False, encoding="utf-8-sig")
    sens_b.to_csv(d["data"] / "prepared_sensitivity_B.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(log).to_csv(d["logs"] / "transformation_log.csv", index=False, encoding="utf-8-sig")
    info = {"n_master": len(master), "n_primary": len(primary), "n_pos_primary": int(primary["_y"].sum()), "n_sensitivity_B": len(sens_b),
            "primary_sha256": sha256_of(d["data"] / "prepared_primary.csv"), "raw_sha256": audit["raw_sha256"], "log": log}
    save_json(info, d["root"] / "prepared_info.json")
    return info


# --------------------------------------------------------------------------------------------
# PREREG
# --------------------------------------------------------------------------------------------
def stage_prereg(cfg: dict) -> dict:
    d = out_dirs(cfg)
    prep = json.loads((d["root"] / "prepared_info.json").read_text(encoding="utf-8"))
    cr = cfg["criteria"]
    plan = {
        "version": "prereg-v1.0",
        "ghi_chu": "Kế hoạch đánh giá cố định trước khi huấn luyện mô hình; mọi thay đổi về sau phải ghi trong Change Log.",
        "du_lieu": {"mau_chinh_sha256": prep["primary_sha256"], "n": prep["n_primary"], "n_duong": prep["n_pos_primary"]},
        "nhan": cfg["target"],
        "kiem_dinh": {"chien_luoc": f"RepeatedStratifiedKFold {cfg['cv']['splits']} phần x {cfg['cv']['repeats']} lần lặp, seed {cfg['cv']['seed']}",
                      "chong_ro_ri": "Mọi bước điền khuyết, chuẩn hóa, mã hóa, chọn siêu tham số nằm trong Pipeline và fit trên phần huấn luyện của từng fold.",
                      "khoang_tin_cay": f"Bootstrap {cfg['cv']['n_boot']} lần lấy mẫu lại quan sát; chênh lệch AUC dùng chỉ số bootstrap ghép cặp."},
        "mo_hinh": {"B0": "Ngẫu nhiên theo tỷ lệ nền", "B1": "Baseline một đặc trưng", "M1": "Hồi quy logistic L2 (chính)",
                    "M2": "Random Forest", "M3": "Gradient Boosting (HistGradientBoosting)", "S1": "Logistic L1 để rút gọn đặc trưng"},
        "ty_le_gan_co": cfg["flag_rates"],
        "tieu_chi": {
            "S1": f"AUC >= {cr['auc']} VÀ recall >= {cr['recall']} tại tỷ lệ gắn cờ {cr['recall_rate']}",
            "S2": f"AUC của M1 hơn B1 ít nhất {cr['delta_auc']} và cận dưới khoảng tin cậy 95% của chênh lệch > 0",
            "S3": f"Số đặc trưng gốc được giữ <= {cr['max_items'] or 'ceil(2/3 tổng số)'} và AUC giảm không quá {cr['ablation_tolerance']}",
            "S4": f"Độ dốc hiệu chuẩn trong {cr['calib_slope']} và Brier thấp hơn baseline tỷ lệ nền",
            "S5": f"Chênh lệch recall giữa nhóm <= {cr['fair_gap']} và khoảng tin cậy rộng <= {cr['fair_ci_width']}; nếu rộng hơn thì ghi 'chưa kết luận'",
        },
        "quy_tac_chon_mo_hinh": f"Giữ M1 (logistic) trừ khi mô hình cây hơn M1 ít nhất {cr['switch_delta']} AUC và cận dưới khoảng tin cậy ghép cặp > 0.",
        "cau_hinh_rut_gon": {k: cfg[k] for k in ("exclude", "groups", "fairness_cols", "baseline_feature")},
    }
    text = json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2)
    plan["sha256_of_plan_without_hash"] = sha256_text(text)
    plan["created_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_json(plan, d["root"] / "evaluation_plan_prereg.json")
    return plan


# --------------------------------------------------------------------------------------------
# DIAGNOSE (AQ mô tả và chẩn đoán)
# --------------------------------------------------------------------------------------------
def prob_superiority(x1: np.ndarray, x0: np.ndarray) -> float:
    """P(x lớp dương < x lớp âm) + 0,5 P(bằng nhau): giá trị > 0,5 nghĩa là lớp dương thường thấp hơn."""
    n1, n0 = len(x1), len(x0)
    r = rankdata(np.concatenate([x1, x0]))
    u1 = r[:n1].sum() - n1 * (n1 + 1) / 2
    return 1 - u1 / (n1 * n0)


def logit_wald(X: np.ndarray, y: np.ndarray, names: list[str]) -> pd.DataFrame:
    """Hồi quy logistic không phạt bằng IRLS, trả OR, khoảng tin cậy Wald và p (nếu ma trận khả nghịch)."""
    Xd = np.column_stack([np.ones(len(X)), X])
    beta = np.zeros(Xd.shape[1])
    for _ in range(50):
        eta = np.clip(Xd @ beta, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        w = np.clip(p * (1 - p), 1e-9, None)
        H = Xd.T @ (Xd * w[:, None]) + 1e-8 * np.eye(Xd.shape[1])
        g = Xd.T @ (y - p)
        step = np.linalg.solve(H, g)
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    cov = np.linalg.pinv(H)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    z = beta / np.where(se > 0, se, np.nan)
    pv = 2 * (1 - stats.norm.cdf(np.abs(z)))
    return pd.DataFrame({"term": ["const"] + names, "or": np.exp(beta), "or_lo": np.exp(beta - 1.96 * se), "or_hi": np.exp(beta + 1.96 * se), "p": pv}).iloc[1:]


def stage_diagnose(cfg: dict) -> dict:
    d = out_dirs(cfg)
    prim = pd.read_csv(d["data"] / "prepared_primary.csv")
    audit = json.loads((d["root"] / "audit.json").read_text(encoding="utf-8"))
    feats, info = feature_columns(prim, cfg, audit.get("leakage_suspects") if cfg["auto_exclude_leakage_auc"] else None)
    y = prim["_y"].values
    rng = np.random.default_rng(cfg["cv"]["seed"])
    rows, levels = [], []
    for c in feats:
        s = prim[c]
        if c in info["numeric"]:
            v = pd.to_numeric(s, errors="coerce")
            m = v.notna().values
            x1, x0 = v[m & (y == 1)].values, v[m & (y == 0)].values
            if len(x1) < 5 or len(x0) < 5:
                continue
            ps = prob_superiority(x1, x0)
            bs = []
            for _ in range(500):
                bs.append(prob_superiority(rng.choice(x1, len(x1)), rng.choice(x0, len(x0))))
            lo, hi = np.percentile(bs, [2.5, 97.5])
            p = stats.mannwhitneyu(x1, x0, alternative="two-sided").pvalue
            rows.append({"feature": c, "type": "numeric", "effect": ps, "effect_lo": lo, "effect_hi": hi, "p": p,
                         "median_pos": float(np.median(x1)), "median_neg": float(np.median(x0))})
        else:
            tab = pd.crosstab(s.fillna("(thiếu)"), y)
            if tab.shape[0] < 2 or tab.shape[1] < 2:
                continue
            chi_p = stats.chi2_contingency(tab)[1]
            rate = tab[1] / tab.sum(axis=1)
            for lev, rr in rate.items():
                n = int(tab.loc[lev].sum())
                lo, hi = wilson(float(tab.loc[lev, 1]), n)
                levels.append({"feature": c, "level": str(lev), "n": n, "rate": float(rr), "rate_lo": lo, "rate_hi": hi})
            cv = math.sqrt(stats.chi2_contingency(tab)[0] / (tab.values.sum() * (min(tab.shape) - 1)))
            rows.append({"feature": c, "type": "categorical", "effect": cv, "effect_lo": np.nan, "effect_hi": np.nan, "p": chi_p,
                         "median_pos": np.nan, "median_neg": np.nan})
    uni = pd.DataFrame(rows)
    if not uni.empty:
        uni["p_holm"] = holm(uni["p"].fillna(1).tolist())
        uni = uni.sort_values("p")
    uni.to_csv(d["tables"] / "diagnose_univariate.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(levels).to_csv(d["tables"] / "diagnose_levels.csv", index=False, encoding="utf-8-sig")
    # Tỷ lệ theo phân vị cho biến số nổi bật
    dec = []
    for c in (uni[uni["type"] == "numeric"].head(4)["feature"].tolist() if not uni.empty else []):
        v = pd.to_numeric(prim[c], errors="coerce")
        try:
            b = pd.qcut(v, 5, duplicates="drop")
        except Exception:
            continue
        g = pd.DataFrame({"b": b, "y": y}).dropna().groupby("b", observed=True)["y"].agg(["sum", "count"])
        for lev, r in g.iterrows():
            lo, hi = wilson(float(r["sum"]), int(r["count"]))
            dec.append({"feature": c, "bin": str(lev), "n": int(r["count"]), "rate": float(r["sum"] / r["count"]), "rate_lo": lo, "rate_hi": hi})
    pd.DataFrame(dec).to_csv(d["tables"] / "diagnose_bins.csv", index=False, encoding="utf-8-sig")
    # Hồi quy logistic hiệu chỉnh (tất cả đặc trưng), OR theo 1 độ lệch chuẩn cho biến số
    num, cat = info["numeric"], info["categorical"]
    parts, names = [], []
    for c in num:
        v = pd.to_numeric(prim[c], errors="coerce")
        v = v.fillna(v.median())
        sd = v.std() or 1.0
        parts.append(((v - v.mean()) / sd).values)
        names.append(f"{c} (mỗi 1 độ lệch chuẩn)")
    for c in cat:
        dm = pd.get_dummies(prim[c].fillna("(thiếu)").astype(str), prefix=c, drop_first=True, dtype=float)
        for k in dm.columns:
            parts.append(dm[k].values)
            names.append(str(k))
    adj = pd.DataFrame()
    if parts:
        Xm = np.column_stack(parts)
        adj = logit_wald(Xm, y.astype(float), names)
        adj["p_holm"] = holm(adj["p"].fillna(1).tolist())
    adj.to_csv(d["tables"] / "diagnose_adjusted.csv", index=False, encoding="utf-8-sig")
    # Hình
    lang_vi = cfg["language"] == "vi"
    if not uni.empty:
        top = uni[uni["type"] == "numeric"].head(10)
        if len(top):
            fig, ax = plt.subplots(figsize=(6.4, 0.45 * len(top) + 1.4))
            yy = np.arange(len(top))[::-1]
            ax.errorbar(top["effect"], yy, xerr=[top["effect"] - top["effect_lo"], top["effect_hi"] - top["effect"]], fmt="o", color=PALETTE["main"], capsize=3)
            ax.axvline(0.5, color=PALETTE["accent"], linestyle="--")
            ax.set_yticks(yy)
            ax.set_yticklabels(top["feature"])
            ax.set_xlabel("Xác suất ưu thế (0,5 = không khác biệt; >0,5: nhóm dương thấp hơn)" if lang_vi else "Probability of superiority")
            style_axes(ax)
            save_fig(fig, d, "f03_xac_suat_uu_the")
    if levels:
        lv = pd.DataFrame(levels)
        topc = uni[uni["type"] == "categorical"].head(1)["feature"].tolist()
        if topc:
            sub = lv[lv["feature"] == topc[0]]
            fig, ax = plt.subplots(figsize=(6.4, 3.6))
            ax.bar(sub["level"], 100 * sub["rate"], color=PALETTE["light"], yerr=[100 * (sub["rate"] - sub["rate_lo"]), 100 * (sub["rate_hi"] - sub["rate"])], capsize=4)
            ax.axhline(100 * y.mean(), color=PALETTE["accent"], linestyle="--")
            ax.set_ylabel(f"% {cfg['target']['positive_name']}" if lang_vi else "% positive")
            ax.set_title(f"Tỷ lệ theo {topc[0]} (nét đứt: toàn mẫu)" if lang_vi else topc[0], fontsize=11)
            style_axes(ax)
            save_fig(fig, d, "f04_ty_le_theo_nhom")
    if dec:
        db = pd.DataFrame(dec)
        c0 = db["feature"].iloc[0]
        sub = db[db["feature"] == c0]
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        ax.bar(range(len(sub)), 100 * sub["rate"], color=PALETTE["main"], yerr=[100 * (sub["rate"] - sub["rate_lo"]), 100 * (sub["rate_hi"] - sub["rate"])], capsize=4)
        ax.set_xticks(range(len(sub)))
        ax.set_xticklabels(sub["bin"], rotation=20, ha="right", fontsize=8)
        ax.set_ylabel(f"% {cfg['target']['positive_name']}" if lang_vi else "% positive")
        ax.set_title(f"Tỷ lệ theo năm phân vị của {c0}" if lang_vi else c0, fontsize=11)
        style_axes(ax)
        save_fig(fig, d, "f05_ty_le_theo_phan_vi")
    res = {"n": len(prim), "n_pos": int(y.sum()), "univariate": uni.head(12).to_dict("records"), "adjusted": adj.head(20).to_dict("records") if len(adj) else []}
    save_json(res, d["root"] / "diagnose.json")
    return res


# --------------------------------------------------------------------------------------------
# MODEL
# --------------------------------------------------------------------------------------------
def build_pre(num: list[str], cat: list[str]) -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore", drop="if_binary"))]), cat),
    ], sparse_threshold=0)


def make_model(key: str, num: list[str], cat: list[str], seed: int, C: float | None = None):
    pre = build_pre(num, cat)
    if key == "M1":
        clf = LogisticRegressionCV(Cs=np.logspace(-3, 2, 8), cv=3, scoring="roc_auc", class_weight="balanced", max_iter=3000)
    elif key == "M1u":
        clf = LogisticRegression(C=C or 1.0, max_iter=3000)
    elif key == "M1fix":
        clf = LogisticRegression(C=C or 1.0, class_weight="balanced", max_iter=3000)
    elif key == "L1":
        clf = LogisticRegressionCV(Cs=np.logspace(-2, 1, 6), cv=3, scoring="roc_auc", class_weight="balanced", l1_ratios=(1.0,), solver="liblinear", max_iter=3000)
    elif key == "M2":
        clf = RandomForestClassifier(n_estimators=300, min_samples_leaf=10, class_weight="balanced_subsample", n_jobs=1, random_state=seed)
    elif key == "M3":
        clf = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, class_weight="balanced", random_state=seed)
    elif key == "B1":
        clf = LogisticRegression(max_iter=3000)
    else:
        raise KeyError(key)
    return Pipeline([("pre", pre), ("clf", clf)])


def _fit_fold(key, X, y, tr, te, num, cat, seed, C, want_coef=False):
    m = make_model(key, num, cat, seed, C)
    m.fit(X.iloc[tr], y[tr])
    s = m.predict_proba(X.iloc[te])[:, 1]
    extra = {}
    if key == "M1":
        extra["C"] = float(m.named_steps["clf"].C_[0])
    if key == "L1":
        names = list(m.named_steps["pre"].get_feature_names_out())
        coef = m.named_steps["clf"].coef_.ravel()
        extra["names"] = names
        extra["nz"] = (np.abs(coef) > 1e-8).tolist()
    return te, s, extra


def run_cv(key, X, y, splits, num, cat, seed, C=None, n_jobs=-1, R=10):
    """Trả về ma trận điểm ngoài fold S (R x n) và các thông tin phụ của từng fold."""
    n = len(y)
    S = np.zeros((R, n))
    k = len(splits) // R
    jobs = [(i, tr, te) for i, (tr, te) in enumerate(splits)]
    if Parallel is not None and n_jobs != 1:
        res = Parallel(n_jobs=n_jobs)(delayed(_fit_fold)(key, X, y, tr, te, num, cat, seed, C) for _, tr, te in jobs)
    else:
        res = [_fit_fold(key, X, y, tr, te, num, cat, seed, C) for _, tr, te in jobs]
    extras = []
    for (i, _, _), (te, s, ex) in zip(jobs, res):
        S[i // k, te] = s
        extras.append(ex)
    return S, extras


def auc_fast(y: np.ndarray, s: np.ndarray) -> float:
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(s)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def hits_curve(y: np.ndarray, s: np.ndarray) -> np.ndarray:
    order = np.argsort(-s, kind="mergesort")
    return np.cumsum(y[order])


def metrics_at(y: np.ndarray, S: np.ndarray, rates: list[float]) -> dict:
    """Trung bình theo các lần lặp: AUC, recall và precision tại các tỷ lệ gắn cờ (sắp xếp một lần mỗi lần lặp)."""
    n1 = y.sum()
    n = len(y)
    ks = [max(1, int(round(rt * n))) for rt in rates]
    aucs, hits = [], np.zeros((S.shape[0], len(rates)))
    for r in range(S.shape[0]):
        aucs.append(auc_fast(y, S[r]))
        cum = hits_curve(y, S[r])
        hits[r] = [cum[k - 1] for k in ks]
    out = {"auc": float(np.mean(aucs))}
    for j, (rt, k) in enumerate(zip(rates, ks)):
        out[f"recall_{rt}"] = float(np.mean(hits[:, j] / n1))
        out[f"precision_{rt}"] = float(np.mean(hits[:, j] / k))
    return out


def ci(a: np.ndarray) -> tuple[float, float]:
    a = np.asarray(a, float)
    return (float(np.nanpercentile(a, 2.5)), float(np.nanpercentile(a, 97.5)))


def bootstrap_models(y, Sd: dict, rates: list[float], n_boot: int, seed: int):
    rng = np.random.default_rng(seed)
    n = len(y)
    idx = rng.integers(0, n, size=(n_boot, n))
    res = {m: {} for m in Sd}
    for m in Sd:
        for k in ["auc"] + [f"recall_{r}" for r in rates] + [f"precision_{r}" for r in rates]:
            res[m][k] = np.empty(n_boot)
    for b in range(n_boot):
        ib = idx[b]
        yb = y[ib]
        if yb.sum() == 0:
            for m in Sd:
                for k in res[m]:
                    res[m][k][b] = np.nan
            continue
        for m, S in Sd.items():
            Sb = S[:, ib]
            mm = metrics_at(yb, Sb, rates)
            for k, v in mm.items():
                res[m][k][b] = v
    return res


def calib_slope(y, p):
    z = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(z.reshape(-1, 1), y)
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def fairness_table(y, S_m1, fdf: pd.DataFrame, cols: list[str], rates: list[float], n_boot: int, seed: int, fair_gap: float, fair_w: float):
    rng = np.random.default_rng(seed + 7)
    rows = []
    n = len(y)
    for c in cols:
        if c not in fdf.columns:
            continue
        g = fdf[c]
        if pd.api.types.is_numeric_dtype(g) and g.nunique() > 6:
            med = g.median()
            g = np.where(g <= med, f"{c} <= {med:g}", f"{c} > {med:g}")
        g = pd.Series(g).fillna("(thiếu)").astype(str).values
        levels = [l for l in pd.unique(g) if (g == l).sum() >= 30 and y[g == l].sum() >= 10]
        if len(levels) < 2:
            continue
        ref = max(levels, key=lambda l: (g == l).sum())
        for rt in rates:
            k = max(1, int(round(rt * n)))
            flags = np.zeros_like(S_m1, dtype=bool)
            for r in range(S_m1.shape[0]):
                cut = np.sort(S_m1[r])[::-1][k - 1]
                flags[r] = S_m1[r] >= cut
            stat = {}
            for l in levels:
                ii = np.where(g == l)[0]
                yi = y[ii]
                tp = (flags[:, ii] & (yi == 1)).sum(axis=1)
                fl = flags[:, ii].sum(axis=1)
                bt = []
                for _ in range(n_boot // 4):
                    jb = rng.integers(0, len(ii), len(ii))
                    yb = yi[jb]
                    if yb.sum() == 0:
                        continue
                    bt.append(float(np.mean((flags[:, ii][:, jb] & (yb == 1)).sum(axis=1) / yb.sum())))
                stat[l] = {"n": len(ii), "pos": int(yi.sum()), "recall": float(np.mean(tp / yi.sum())), "precision": float(np.mean(tp / np.maximum(fl, 1))),
                           "flag_rate": float(np.mean(fl / len(ii))), "boot": np.array(bt)}
            for l in levels:
                lo, hi = ci(stat[l]["boot"])
                row = {"attribute": c, "group": l, "n": stat[l]["n"], "positives": stat[l]["pos"], "rate": rt, "recall": stat[l]["recall"], "recall_lo": lo, "recall_hi": hi,
                       "precision": stat[l]["precision"], "flag_rate": stat[l]["flag_rate"], "reference": l == ref}
                if l != ref:
                    m = min(len(stat[l]["boot"]), len(stat[ref]["boot"]))
                    diff = stat[l]["boot"][:m] - stat[ref]["boot"][:m]
                    glo, ghi = ci(diff)
                    row.update({"gap_vs_ref": stat[l]["recall"] - stat[ref]["recall"], "gap_lo": glo, "gap_hi": ghi, "gap_ci_width": ghi - glo,
                                "within_gap": abs(stat[l]["recall"] - stat[ref]["recall"]) <= fair_gap, "conclusive": (ghi - glo) <= fair_w})
                rows.append(row)
    return pd.DataFrame(rows)


def stage_model(cfg: dict, fast: bool = False) -> dict:
    d = out_dirs(cfg)
    pre_path = d["root"] / "evaluation_plan_prereg.json"
    if not pre_path.exists():
        raise RuntimeError("Chưa đăng ký trước tiêu chí: chạy bước prereg trước khi huấn luyện mô hình.")
    plan = json.loads(pre_path.read_text(encoding="utf-8"))
    claimed = plan.pop("sha256_of_plan_without_hash")
    plan.pop("created_utc", None)
    if sha256_text(json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2)) != claimed:
        raise RuntimeError("Mã SHA-256 của kế hoạch đăng ký trước không khớp: tiêu chí đã bị chỉnh sau khi đăng ký.")
    prim_path = d["data"] / "prepared_primary.csv"
    if sha256_of(prim_path) != plan["du_lieu"]["mau_chinh_sha256"]:
        raise RuntimeError("Mẫu chính đã thay đổi sau khi đăng ký trước.")
    cv = dict(cfg["cv"])
    if fast:
        cv.update({"repeats": 3, "n_boot": 300})
    prim = pd.read_csv(prim_path)
    audit = json.loads((d["root"] / "audit.json").read_text(encoding="utf-8"))
    auto_leak = audit.get("leakage_suspects", []) if cfg["auto_exclude_leakage_auc"] else []
    feats, info = feature_columns(prim, cfg, auto_leak)
    num, cat = info["numeric"], info["categorical"]
    y = prim["_y"].values.astype(int)
    X = prim[feats]
    n = len(y)
    rates = sorted(set(cfg["flag_rates"]) | {cfg["criteria"]["recall_rate"]})
    grid = sorted(set(rates) | {round(0.05 * i, 2) for i in range(1, 11)})
    seed, R, K = cv["seed"], cv["repeats"], cv["splits"]
    splits = list(RepeatedStratifiedKFold(n_splits=K, n_repeats=R, random_state=seed).split(X, y))
    uni = audit.get("univariate_auc", {})
    base_feat = cfg["baseline_feature"] or (max((c for c in feats if c in uni), key=lambda c: uni[c]) if any(c in uni for c in feats) else feats[0])
    base_note = "do người dùng chỉ định" if cfg["baseline_feature"] else "chọn tự động theo AUC đơn đặc trưng nên hơi lạc quan"
    nj = cv["n_jobs"]
    # B1, M1, M1u, M2, M3
    Xb = X[[base_feat]]
    nb, cb = ([base_feat], []) if base_feat in num else ([], [base_feat])
    S = {}
    S["B0"] = np.full((R, n), 0.5) + np.random.default_rng(seed).normal(0, 1e-6, (R, n))
    S["B1"], _ = run_cv("B1", Xb, y, splits, nb, cb, seed, n_jobs=nj, R=R)
    S["M1"], ex1 = run_cv("M1", X, y, splits, num, cat, seed, n_jobs=nj, R=R)
    C_med = float(np.median([e["C"] for e in ex1]))
    S["M1u"], _ = run_cv("M1u", X, y, splits, num, cat, seed, C=C_med, n_jobs=nj, R=R)
    S["M2"], _ = run_cv("M2", X, y, splits, num, cat, seed, n_jobs=nj, R=R)
    S["M3"], _ = run_cv("M3", X, y, splits, num, cat, seed, n_jobs=nj, R=R)
    S["M1fix"], _ = run_cv("M1fix", X, y, splits, num, cat, seed, C=C_med, n_jobs=nj, R=R)
    S["L1"], exl = run_cv("L1", X, y, splits, num, cat, seed, n_jobs=nj, R=R)
    # Nhóm đặc trưng và ablation
    groups = {k: [c for c in v if c in feats] for k, v in cfg["groups"].items()}
    groups = {k: v for k, v in groups.items() if v}
    if not groups:
        groups = {c: [c] for c in feats}
    if len(groups) > 25:
        top_groups = sorted(groups, key=lambda g: -max(uni.get(c, 0.5) for c in groups[g]))[:25]
        groups = {g: groups[g] for g in top_groups}
    for gname, cols in groups.items():
        keep = [c for c in feats if c not in cols]
        if not keep:
            continue
        n2 = [c for c in keep if c in num]
        c2 = [c for c in keep if c in cat]
        S[f"abl::{gname}"], _ = run_cv("M1fix", X[keep], y, splits, n2, c2, seed, C=C_med, n_jobs=nj, R=R)
    # Bootstrap
    boot_models = {k: v for k, v in S.items()}
    B = bootstrap_models(y, boot_models, grid, cv["n_boot"], seed)
    pt = {m: metrics_at(y, S[m], grid) for m in S}

    def ci_of(m, k):
        return ci(B[m][k])

    def delta(a, b, k="auc"):
        dd = B[a][k] - B[b][k]
        return float(pt[a][k] - pt[b][k]), ci(dd)

    rows = []
    for m, label in [("B0", "Ngẫu nhiên"), ("B1", f"Baseline: {base_feat}"), ("M1", "Logistic L2 (chính)"), ("M2", "Random Forest"), ("M3", "Gradient Boosting"), ("L1", "Logistic L1")]:
        r = {"model": m, "label": label, "auc": pt[m]["auc"], "auc_lo": ci_of(m, "auc")[0], "auc_hi": ci_of(m, "auc")[1]}
        for rt in rates:
            r[f"recall_{rt}"] = pt[m][f"recall_{rt}"]
            r[f"recall_{rt}_lo"], r[f"recall_{rt}_hi"] = ci_of(m, f"recall_{rt}")
            r[f"precision_{rt}"] = pt[m][f"precision_{rt}"]
        r["prauc"] = float(np.mean([average_precision_score(y, S[m][i]) for i in range(R)]))
        rows.append(r)
    main = pd.DataFrame(rows)
    main.to_csv(d["tables"] / "model_main_ranking.csv", index=False, encoding="utf-8-sig")
    # Chênh lệch ghép cặp
    pair = []
    for a, b, lab in [("M1", "B1", "M1 so với baseline"), ("M2", "M1", "Random Forest so với M1"), ("M3", "M1", "Gradient Boosting so với M1"), ("L1", "M1", "Logistic L1 so với M1")]:
        dl, (lo, hi) = delta(a, b)
        pair.append({"comparison": lab, "delta_auc": dl, "lo": lo, "hi": hi})
    pd.DataFrame(pair).to_csv(d["tables"] / "model_paired_delta.csv", index=False, encoding="utf-8-sig")
    # Hiệu chuẩn
    slopes = [calib_slope(y, S["M1u"][i]) for i in range(R)]
    slope, inter = float(np.mean([s for s, _ in slopes])), float(np.mean([i for _, i in slopes]))
    brier = float(np.mean([brier_score_loss(y, S["M1u"][i]) for i in range(R)]))
    brier_base = float(brier_score_loss(y, np.full(n, y.mean())))
    # Đường cong năng lực
    cap = []
    for rt in grid:
        cap.append({"rate": rt, "recall_M1": pt["M1"][f"recall_{rt}"], "recall_M1_lo": ci_of("M1", f"recall_{rt}")[0], "recall_M1_hi": ci_of("M1", f"recall_{rt}")[1],
                    "precision_M1": pt["M1"][f"precision_{rt}"], "recall_B1": pt["B1"][f"recall_{rt}"], "recall_random": rt})
    capdf = pd.DataFrame(cap)
    capdf.to_csv(d["tables"] / "model_capacity_curve.csv", index=False, encoding="utf-8-sig")
    need = capdf[capdf["recall_M1"] >= cfg["criteria"]["recall"]]
    flag_for_target = float(need["rate"].iloc[0]) if len(need) else None
    # Ablation
    ab = [{"setting": "Đầy đủ (C cố định)", "auc": pt["M1fix"]["auc"], "delta_auc": 0.0, "lo": 0.0, "hi": 0.0, f"recall_{cfg['criteria']['recall_rate']}": pt["M1fix"][f"recall_{cfg['criteria']['recall_rate']}"]}]
    for gname in groups:
        key = f"abl::{gname}"
        if key not in S:
            continue
        dl, (lo, hi) = delta(key, "M1fix")
        ab.append({"setting": f"Bỏ: {gname}", "auc": pt[key]["auc"], "delta_auc": dl, "lo": lo, "hi": hi, f"recall_{cfg['criteria']['recall_rate']}": pt[key][f"recall_{cfg['criteria']['recall_rate']}"]})
    abdf = pd.DataFrame(ab)
    abdf.to_csv(d["tables"] / "model_ablation.csv", index=False, encoding="utf-8-sig")
    # L1: số đặc trưng gốc giữ lại
    sel_count, sel_freq = [], {c: 0 for c in feats}
    for ex in exl:
        names = ex["names"]
        nz = ex["nz"]
        kept = set()
        for nm, flag in zip(names, nz):
            if not flag:
                continue
            base = nm.split("__", 1)[1]
            cands = [c for c in feats if base == c or base.startswith(c + "_")]
            if cands:
                kept.add(max(cands, key=len))
        sel_count.append(len(kept))
        for c in kept:
            sel_freq[c] += 1
    items_mean = float(np.mean(sel_count))
    pd.DataFrame([{"feature": c, "selection_freq": v / len(exl)} for c, v in sorted(sel_freq.items(), key=lambda kv: -kv[1])]).to_csv(
        d["tables"] / "model_l1_selection.csv", index=False, encoding="utf-8-sig")
    # Hệ số logistic chuẩn hóa (fit toàn bộ, mô tả)
    mfull = make_model("M1", num, cat, seed).fit(X, y)
    names_full = list(mfull.named_steps["pre"].get_feature_names_out())
    coef = mfull.named_steps["clf"].coef_.ravel()
    pd.DataFrame({"term": names_full, "coef_std": coef, "odds_ratio": np.exp(coef)}).sort_values("coef_std", key=np.abs, ascending=False).to_csv(
        d["tables"] / "model_coefficients.csv", index=False, encoding="utf-8-sig")
    # Công bằng
    fair_cols = [c for c in cfg["fairness_cols"] if c in prim.columns]
    S_m1 = S["M1"]
    fairdf = fairness_table(y, S_m1, prim, fair_cols, cfg["flag_rates"], cv["n_boot"], seed, cfg["criteria"]["fair_gap"], cfg["criteria"]["fair_ci_width"]) if fair_cols else pd.DataFrame()
    fairdf.to_csv(d["tables"] / "model_fairness.csv", index=False, encoding="utf-8-sig")
    # Tiêu chí
    cr = cfg["criteria"]
    rr = cr["recall_rate"]
    m1 = main[main["model"] == "M1"].iloc[0]
    b1 = main[main["model"] == "B1"].iloc[0]
    auc_ok_pt = m1["auc"] >= cr["auc"]
    rec_ok_pt = m1[f"recall_{rr}"] >= cr["recall"]
    auc_ok_lo = m1["auc_lo"] >= cr["auc"]
    rec_ok_lo = m1[f"recall_{rr}_lo"] >= cr["recall"]
    if auc_ok_pt and rec_ok_pt:
        s1 = "Đạt (độ tin cậy cao)" if (auc_ok_lo and rec_ok_lo) else "Đạt (điểm ước lượng)"
    else:
        s1 = "Không đạt"
    d21, (lo21, hi21) = delta("M1", "B1")
    s2 = "Không đạt" if d21 < cr["delta_auc"] else ("Đạt" if lo21 > 0 else "Chưa kết luận")
    max_items = cr["max_items"] or math.ceil(2 * len(feats) / 3)
    dl_l1, (lo_l1, hi_l1) = delta("L1", "M1")
    s3 = "Đạt" if (items_mean <= max_items and dl_l1 >= -cr["ablation_tolerance"]) else "Không đạt"
    s4 = "Đạt" if (cr["calib_slope"][0] <= slope <= cr["calib_slope"][1] and brier < brier_base) else "Không đạt"
    if len(fairdf) and "gap_vs_ref" in fairdf:
        fg = fairdf.dropna(subset=["gap_vs_ref"])
        if fg.empty:
            s5 = "Chưa kết luận"
        elif (fg["gap_lo"] > cr["fair_gap"]).any() or (fg["gap_hi"] < -cr["fair_gap"]).any():
            s5 = "Không đạt"
        elif fg["within_gap"].all() and fg["conclusive"].all():
            s5 = "Đạt"
        else:
            s5 = "Chưa kết luận"
    else:
        s5 = "Chưa kết luận"
    # Quy tắc chọn mô hình
    recommended = "M1"
    switch_note = "Giữ hồi quy logistic theo quy tắc đã đăng ký."
    for key, lab in [("M2", "Random Forest"), ("M3", "Gradient Boosting")]:
        dl, (lo, hi) = delta(key, "M1")
        if dl >= cr["switch_delta"] and lo > 0:
            recommended = key
            switch_note = f"{lab} hơn M1 {dl:.3f} AUC với cận dưới > 0: chuyển theo quy tắc đã đăng ký."
    res = {
        "n": n, "positives": int(y.sum()), "prevalence": float(y.mean()), "n_features": len(feats), "features": feats, "numeric": num, "categorical": cat,
        "baseline_feature": base_feat, "baseline_note": base_note, "C_median": C_med, "cv": cv, "flag_rates": rates, "grid": grid,
        "main": main.to_dict("records"), "paired": pair, "calibration": {"slope": slope, "intercept": inter, "brier": brier, "brier_base": brier_base},
        "flag_rate_for_target_recall": flag_for_target, "items_mean": items_mean, "max_items": max_items, "l1_delta": dl_l1,
        "criteria": {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5}, "recommended_model": recommended, "switch_note": switch_note,
        "auto_excluded_leakage": auto_leak, "strong_features_unconfirmed": audit.get("strong_features", []), "groups": groups, "prereg_sha256": claimed, "primary_sha256": plan["du_lieu"]["mau_chinh_sha256"],
        "ablation": abdf.to_dict("records"), "fast_mode": fast,
    }
    # Độ nhạy B: chạy lại M1 trên mẫu B và so sánh AUC (nhanh)
    sb = d["data"] / "prepared_sensitivity_B.csv"
    if sb.exists():
        pb = pd.read_csv(sb)
        yb = pb["_y"].values.astype(int)
        if len(pb) != len(prim) and yb.sum() >= 20:
            splb = list(RepeatedStratifiedKFold(n_splits=K, n_repeats=min(R, 5), random_state=seed).split(pb[feats], yb))
            Sb, _ = run_cv("M1", pb[feats], yb, splb, num, cat, seed, n_jobs=nj, R=min(R, 5))
            res["sensitivity_B"] = {"n": len(pb), "positives": int(yb.sum()), "auc": float(np.mean([auc_fast(yb, Sb[i]) for i in range(Sb.shape[0])]))}
    save_json(res, d["root"] / "results.json")
    make_model_figures(cfg, d, main, capdf, abdf, fairdf, slope, y, S, rates)
    maybe_shap(cfg, d, X, y, num, cat, seed)
    return res


def maybe_shap(cfg, d, X, y, num, cat, seed):
    """SHAP là tùy chọn: chỉ chạy khi thư viện có sẵn; nếu không, ghi nhận để báo cáo nói rõ chưa chạy."""
    status = {"shap": "chưa chạy (thư viện shap không có trong môi trường)"}
    try:
        import shap  # type: ignore
        m = make_model("M3", num, cat, seed).fit(X, y)
        Xt = m.named_steps["pre"].transform(X)
        names = list(m.named_steps["pre"].get_feature_names_out())
        idx = np.random.default_rng(seed).choice(len(X), min(400, len(X)), replace=False)
        ex = shap.TreeExplainer(m.named_steps["clf"])
        sv = ex.shap_values(Xt[idx])
        imp = np.abs(sv).mean(axis=0)
        pd.DataFrame({"feature": names, "mean_abs_shap": imp}).sort_values("mean_abs_shap", ascending=False).to_csv(d["tables"] / "xai_shap_importance.csv", index=False, encoding="utf-8-sig")
        shap.summary_plot(sv, Xt[idx], feature_names=names, show=False)
        plt.gcf().savefig(d["figures"] / "f10_shap_summary.png", dpi=200, bbox_inches="tight")
        plt.close("all")
        status = {"shap": "đã chạy trên Gradient Boosting (400 quan sát mẫu)"}
    except Exception as e:  # noqa: BLE001
        status["detail"] = str(e)[:200]
    save_json(status, d["root"] / "xai_status.json")


def make_model_figures(cfg, d, main, capdf, abdf, fairdf, slope, y, S, rates):
    vi_ = cfg["language"] == "vi"
    # AUC với khoảng tin cậy
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    sub = main[main["model"].isin(["B0", "B1", "M1", "M2", "M3"])]
    yy = np.arange(len(sub))[::-1]
    cols = [PALETTE["grey"], PALETTE["grey"], PALETTE["main"], PALETTE["light"], PALETTE["light"]]
    for i, (_, r) in enumerate(sub.iterrows()):
        ax.errorbar(r["auc"], yy[i], xerr=[[r["auc"] - r["auc_lo"]], [r["auc_hi"] - r["auc"]]], fmt="o", color=cols[i], capsize=4, markersize=8)
        ax.text(r["auc_hi"] + 0.006, yy[i], f"{r['auc']:.3f}".replace(".", ",") if vi_ else f"{r['auc']:.3f}", va="center", fontsize=9)
    ax.axvline(cfg["criteria"]["auc"], color=PALETTE["accent"], linestyle="--")
    ax.set_yticks(yy)
    ax.set_yticklabels(sub["label"])
    ax.set_xlabel("AUC (thanh ngang: khoảng tin cậy 95%; nét đứt: mục tiêu)" if vi_ else "AUC (95% CI; dashed = target)")
    if vi_:
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: vi(v, 2)))
    style_axes(ax)
    save_fig(fig, d, "f06_auc_cac_phuong_an")
    # Năng lực: recall theo tỷ lệ gắn cờ
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(100 * capdf["rate"], 100 * capdf["recall_M1"], color=PALETTE["main"], marker="o", label="Mô hình chính" if vi_ else "Main model")
    ax.fill_between(100 * capdf["rate"], 100 * capdf["recall_M1_lo"], 100 * capdf["recall_M1_hi"], color=PALETTE["light"], alpha=0.4)
    ax.plot(100 * capdf["rate"], 100 * capdf["recall_B1"], color=PALETTE["grey"], linestyle="-.", label="Baseline một đặc trưng" if vi_ else "Baseline")
    ax.plot(100 * capdf["rate"], 100 * capdf["recall_random"], color="#9CA3AF", linestyle=":", label="Ngẫu nhiên" if vi_ else "Random")
    ax.axhline(100 * cfg["criteria"]["recall"], color=PALETTE["accent"], linestyle="--")
    ax.set_xlabel("% quan sát được gắn cờ" if vi_ else "% flagged")
    ax.set_ylabel(f"% {cfg['target']['positive_name']} được bắt" if vi_ else "% captured")
    ax.legend(frameon=False, fontsize=9)
    style_axes(ax)
    save_fig(fig, d, "f07_nang_luc_gan_co")
    # Ablation
    if len(abdf) > 1:
        sub = abdf.iloc[1:].sort_values("delta_auc")
        fig, ax = plt.subplots(figsize=(6.4, 0.38 * len(sub) + 1.5))
        yy = np.arange(len(sub))
        ax.barh(yy, sub["delta_auc"], color=[PALETTE["accent"] if v < -0.01 else PALETTE["light"] for v in sub["delta_auc"]])
        ax.errorbar(sub["delta_auc"], yy, xerr=[sub["delta_auc"] - sub["lo"], sub["hi"] - sub["delta_auc"]], fmt="none", color="#374151", capsize=3)
        ax.set_yticks(yy)
        ax.set_yticklabels(sub["setting"].str.replace("Bỏ: ", ""))
        ax.axvline(0, color="#374151", linewidth=1)
        ax.set_xlabel("Thay đổi AUC khi bỏ nhóm đặc trưng" if vi_ else "Change in AUC when removed")
        style_axes(ax)
        save_fig(fig, d, "f08_ablation")
    # Công bằng
    if len(fairdf):
        fr = cfg["flag_rates"][-1]
        sub = fairdf[fairdf["rate"] == fr]
        if len(sub):
            fig, ax = plt.subplots(figsize=(6.4, 0.5 * len(sub) + 1.5))
            yy = np.arange(len(sub))[::-1]
            ax.errorbar(100 * sub["recall"], yy, xerr=[100 * (sub["recall"] - sub["recall_lo"]), 100 * (sub["recall_hi"] - sub["recall"])], fmt="o", color=PALETTE["main"], capsize=3)
            ax.set_yticks(yy)
            ax.set_yticklabels(sub["attribute"] + ": " + sub["group"])
            ax.set_xlabel(f"Recall (%) khi gắn cờ {int(fr * 100)}%" if vi_ else "Recall (%)")
            style_axes(ax)
            save_fig(fig, d, "f09_cong_bang")


# --------------------------------------------------------------------------------------------
# VERIFY
# --------------------------------------------------------------------------------------------
def stage_verify(cfg: dict) -> dict:
    d = out_dirs(cfg)
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    audit = json.loads((d["root"] / "audit.json").read_text(encoding="utf-8")) if (d["root"] / "audit.json").exists() else None
    prep = json.loads((d["root"] / "prepared_info.json").read_text(encoding="utf-8")) if (d["root"] / "prepared_info.json").exists() else None
    res = json.loads((d["root"] / "results.json").read_text(encoding="utf-8")) if (d["root"] / "results.json").exists() else None
    plan = json.loads((d["root"] / "evaluation_plan_prereg.json").read_text(encoding="utf-8")) if (d["root"] / "evaluation_plan_prereg.json").exists() else None
    chk("Có đủ các tệp đầu ra chính", all(x is not None for x in (audit, prep, res, plan)))
    if None in (audit, prep, res, plan):
        out = {"checks": checks, "all_passed": False}
        save_json(out, d["root"] / "verify.json")
        return out
    raw = Path(cfg["data_path"]) if Path(cfg["data_path"]).is_absolute() else Path(cfg["_cfg_dir"]) / cfg["data_path"]
    chk("SHA-256 dữ liệu gốc khớp lúc kiểm tra", sha256_of(raw) == audit["raw_sha256"])
    chk("SHA-256 mẫu chính khớp bản đã đăng ký trước", sha256_of(d["data"] / "prepared_primary.csv") == plan["du_lieu"]["mau_chinh_sha256"])
    p2 = dict(plan)
    claimed = p2.pop("sha256_of_plan_without_hash")
    p2.pop("created_utc", None)
    chk("Kế hoạch đăng ký trước không bị chỉnh sửa", sha256_text(json.dumps(p2, ensure_ascii=False, sort_keys=True, indent=2)) == claimed)
    chk("Kế hoạch được lập trước kết quả mô hình", (d["root"] / "evaluation_plan_prereg.json").stat().st_mtime <= (d["root"] / "results.json").stat().st_mtime)
    prim = pd.read_csv(d["data"] / "prepared_primary.csv")
    chk("Số dòng mẫu chính khớp nhật ký", len(prim) == prep["n_primary"] == res["n"], f"{len(prim)} / {prep['n_primary']} / {res['n']}")
    chk("Số ca dương khớp", int(prim["_y"].sum()) == res["positives"] == prep["n_pos_primary"])
    feats = res["features"]
    leaked = [c for c in feats if c == cfg["target"]["column"] or c in cfg["exclude"]["leakage"] or c in res["auto_excluded_leakage"]]
    chk("Không có biến rò rỉ hoặc nhãn trong đặc trưng", not leaked, ", ".join(leaked))
    main = pd.read_csv(d["tables"] / "model_main_ranking.csv")
    chk("AUC mọi mô hình nằm trong [0,1] và khoảng tin cậy chứa ước lượng", bool(((main["auc"] >= 0) & (main["auc"] <= 1) & (main["auc_lo"] <= main["auc"] + 1e-9) & (main["auc_hi"] >= main["auc"] - 1e-9)).all()))
    m1 = main[main["model"] == "M1"].iloc[0]
    chk("AUC trong results.json khớp bảng", abs(m1["auc"] - [r for r in res["main"] if r["model"] == "M1"][0]["auc"]) < 1e-9)
    figs = list(d["figures"].glob("*.png"))
    chk("Có hình xuất ra", len(figs) >= 5, f"{len(figs)} hình")
    chk("Không có giá trị thiếu trong bảng kết quả chính", not main[["auc", "auc_lo", "auc_hi"]].isna().any().any())
    chk("Chế độ chạy đầy đủ (không phải --fast)", not res.get("fast_mode", False), "Chạy nhanh chỉ dùng để thử đường ống; không dùng số liệu cho báo cáo." if res.get("fast_mode") else "")
    out = {"checks": checks, "all_passed": all(c["passed"] for c in checks)}
    save_json(out, d["root"] / "verify.json")
    return out


# --------------------------------------------------------------------------------------------
# INIT: đề xuất cấu hình từ dữ liệu
# --------------------------------------------------------------------------------------------
def stage_init(data: str, target: str, threshold: float | None, out_cfg: str, positive_if: str = "<", id_col: str | None = None,
               sheet=None, missing_codes=None, positive_values=None) -> dict:
    cfgd = copy.deepcopy(DEFAULT_CFG)
    cfgd["data_path"] = data
    cfgd["sheet"] = sheet
    cfgd["id_col"] = id_col
    cfgd["target"]["column"] = target
    if threshold is not None:
        cfgd["target"]["type"] = "threshold"
        cfgd["target"]["threshold"] = threshold
        cfgd["target"]["positive_if"] = positive_if
        cfgd["target"]["missing_codes"] = missing_codes or []
    else:
        cfgd["target"]["type"] = "binary"
        if positive_values:
            cfgd["target"]["positive_values"] = positive_values
    p = Path(out_cfg).resolve()
    cfgd["_cfg_dir"] = str(p.parent)
    cfgd["data_path"] = str(Path(data).resolve()) if not Path(data).is_absolute() else data
    try:
        prof = stage_profile(cfgd)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"Không phân tích được dữ liệu: {e}")
    draft = {k: v for k, v in cfgd.items() if not k.startswith("_")}
    draft["data_path"] = Path(data).name if Path(data).resolve().parent == p.parent else str(Path(data).resolve())
    draft["exclude"]["leakage"] = []
    draft["_goi_y"] = {
        "leakage_suspects_tu_dong": prof["leakage_suspects"],
        "repeat_clusters": prof["repeat_clusters"],
        "bat_buoc_xac_nhan": "Xác nhận nhãn/ngưỡng, các cột rò rỉ, nhóm công bằng (fairness_cols), nhóm đặc trưng (groups) và tiêu chí thành công trước khi chạy.",
    }
    if prof["repeat_clusters"] and prof["repeat_clusters"]["n_rows"] >= 0.05 * prof["n_valid_label"]:
        draft["exclude_repeat_clusters"] = True
    save_json(draft, p)
    return prof


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("init")
    pi.add_argument("--data", required=True)
    pi.add_argument("--target", required=True)
    pi.add_argument("--threshold", type=float, default=None)
    pi.add_argument("--positive-if", default="<")
    pi.add_argument("--id-col", default=None)
    pi.add_argument("--sheet", default=None)
    pi.add_argument("--missing-codes", default="")
    pi.add_argument("--positive-values", default="", help="Với nhãn nhị phân: các giá trị tính là ca dương, cách nhau bằng dấu phẩy (ví dụ 0 hoặc M)")
    pi.add_argument("--out", default="config.draft.json")
    for name in ("profile", "prepare", "prereg", "diagnose", "model", "verify", "all"):
        sp = sub.add_parser(name)
        sp.add_argument("--config", required=True)
        sp.add_argument("--fast", action="store_true", help="Chạy nhanh để thử đường ống (3 lần lặp, 300 bootstrap); không dùng số liệu để báo cáo")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        mc = [float(x) for x in a.missing_codes.split(",") if x.strip()] if a.missing_codes else []
        pv = []
        for x in [t.strip() for t in a.positive_values.split(",") if t.strip()]:
            try:
                pv.append(float(x) if "." in x else int(x))
            except ValueError:
                pv.append(x)
        prof = stage_init(a.data, a.target, a.threshold, a.out, a.positive_if, a.id_col, a.sheet, mc, pv or None)
        print(f"Đã ghi {a.out}. Dòng hợp lệ: {prof['n_valid_label']}, ca dương: {prof['n_positive']} ({prof['prevalence'] * 100:.1f}%), "
              f"nghi rò rỉ: {prof['leakage_suspects']}, vấn đề chất lượng: {len(prof['issues'])}")
        return
    cfg = load_cfg(a.config)
    steps = {"profile": stage_profile, "prepare": stage_prepare, "prereg": stage_prereg, "diagnose": stage_diagnose, "verify": stage_verify}
    if a.cmd == "all":
        stage_profile(cfg)
        stage_prepare(cfg)
        stage_prereg(cfg)
        stage_diagnose(cfg)
        stage_model(cfg, fast=a.fast)
        v = stage_verify(cfg)
        print("Kiểm chứng:", "ĐẠT" if v["all_passed"] else "CÓ MỤC KHÔNG ĐẠT", f"(xem {out_dirs(cfg)['root'] / 'verify.json'})")
    elif a.cmd == "model":
        stage_model(cfg, fast=a.fast)
    else:
        steps[a.cmd](cfg)
    print("Xong:", a.cmd)


if __name__ == "__main__":
    main()
