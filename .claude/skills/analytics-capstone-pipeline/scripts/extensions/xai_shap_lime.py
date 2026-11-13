# -*- coding: utf-8 -*-
"""Diễn giải mô hình cây bằng SHAP (toàn cục) và LIME (cục bộ), dùng cùng cấu hình với dspipe.py.

Cách dùng:
    python xai_shap_lime.py --config config.json [--n-lime 3]

Để tránh rò rỉ dữ liệu, mô hình chỉ fit trên phần huấn luyện (phân tầng, 75%) và giải thích trên phần kiểm tra.
Đầu ra trong <out_dir>/xai/: shap_tom_tat.png, shap_do_quan_trong.csv, shap_phu_thuoc_<đặc trưng>.png, lime_<k>.csv.
Sau đó đối chiếu hướng tác động của SHAP với hệ số hồi quy logistic (tuyến tính) trong tables/model_coefficients.csv
để phân biệt quan hệ đơn điệu với tương tác phi tuyến. Lưu ý đây vẫn là liên hệ, không phải nhân quả.
Yêu cầu thư viện shap và lime (chưa có thì dừng với thông báo rõ ràng).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dspipe as D  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--n-lime", type=int, default=3)
    a = ap.parse_args()
    try:
        import shap
        from lime.lime_tabular import LimeTabularExplainer
    except ImportError as e:
        sys.exit(f"Thiếu thư viện ({e}). Hãy cài shap và lime trên môi trường có mạng rồi chạy lại.")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split

    cfg = D.load_cfg(a.config)
    dirs = D.out_dirs(cfg)
    res = __import__("json").loads((Path(dirs["root"]) / "results.json").read_text(encoding="utf-8"))
    prim = pd.read_csv(Path(dirs["data"]) / "prepared_primary.csv")
    if "_in_primary" in prim.columns:
        prim = prim[prim["_in_primary"].astype(bool)]
    feats = res["features"]
    num = [c for c in res["numeric"] if c in feats]
    cat = [c for c in res["categorical"] if c in feats]
    y = prim["_y"].to_numpy().astype(int)
    X = prim[feats].copy()
    pre = D.build_pre(num, cat)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=cfg["cv"]["seed"])
    Atr = pre.fit_transform(Xtr)          # tiền xử lý chỉ fit trên huấn luyện
    Ate = pre.transform(Xte)
    names = list(pre.get_feature_names_out())
    Atr = Atr.toarray() if hasattr(Atr, "toarray") else np.asarray(Atr)
    Ate = Ate.toarray() if hasattr(Ate, "toarray") else np.asarray(Ate)
    rf = RandomForestClassifier(n_estimators=500, min_samples_leaf=3, class_weight="balanced", random_state=cfg["cv"]["seed"], n_jobs=-1)
    rf.fit(Atr, ytr)
    out = Path(dirs["root"]) / "xai"
    out.mkdir(exist_ok=True)

    ex = shap.TreeExplainer(rf)
    sv = ex.shap_values(Ate)
    sv1 = sv[1] if isinstance(sv, list) else (sv[:, :, 1] if np.ndim(sv) == 3 else sv)   # lớp dương
    imp = pd.DataFrame({"dac_trung": names, "mean_abs_shap": np.abs(sv1).mean(axis=0)}).sort_values("mean_abs_shap", ascending=False)
    imp.to_csv(out / "shap_do_quan_trong.csv", index=False, encoding="utf-8-sig")
    plt.figure()
    shap.summary_plot(sv1, Ate, feature_names=names, show=False)
    plt.tight_layout()
    plt.savefig(out / "shap_tom_tat.png", dpi=200)
    plt.close()
    for f in imp["dac_trung"].head(3):
        plt.figure()
        shap.dependence_plot(f, sv1, Ate, feature_names=names, show=False)
        plt.tight_layout()
        plt.savefig(out / f"shap_phu_thuoc_{"".join(ch if ch.isalnum() else "_" for ch in f)[:40]}.png", dpi=200)
        plt.close()

    lime_ex = LimeTabularExplainer(Atr, feature_names=names, class_names=["âm", "dương"], mode="classification", random_state=cfg["cv"]["seed"])
    pos_idx = np.where(yte == 1)[0][: a.n_lime]
    for k, i in enumerate(pos_idx, 1):
        e = lime_ex.explain_instance(Ate[i], rf.predict_proba, num_features=8)
        pd.DataFrame(e.as_list(), columns=["dieu_kien", "trong_so"]).to_csv(out / f"lime_{k}.csv", index=False, encoding="utf-8-sig")
    (Path(dirs["root"]) / "xai_status.json").write_text(__import__("json").dumps({"shap": "đã chạy", "lime": "đã chạy", "thu_muc": str(out)}, ensure_ascii=False), encoding="utf-8")
    print("Đã ghi kết quả SHAP và LIME vào", out)


if __name__ == "__main__":
    main()
