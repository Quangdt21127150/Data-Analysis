# -*- coding: utf-8 -*-
"""Mẫu SEM / CFA bằng semopy cho dữ liệu thang đo đa mục hỏi.

Cách dùng:
    python sem_template.py --data du_lieu.csv --model mo_hinh.txt --out thu_muc_ket_qua

Tệp mô hình dùng cú pháp kiểu lavaan mà semopy hỗ trợ, ví dụ:
    # mô hình đo lường
    TamLy =~ q1 + q2 + q3
    HocTap =~ q4 + q5 + q6
    KetQua =~ q7 + q8 + q9
    # mô hình cấu trúc
    KetQua ~ TamLy + HocTap

Đầu ra: chỉ số phù hợp (RMSEA, CFI, TLI), hệ số tải chuẩn hóa, hệ số đường dẫn, Cronbach's Alpha, CR và AVE, kèm cột
"Đánh giá" so với các ngưỡng học thuật: Alpha > 0,7; tải > 0,5; AVE > 0,5; CR > 0,7; RMSEA < 0,08; CFI và TLI > 0,9.
Yêu cầu thư viện semopy (chưa có thì dừng với thông báo rõ ràng, không tự cài đặt).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NGUONG = {"alpha": 0.7, "tai": 0.5, "ave": 0.5, "cr": 0.7, "rmsea": 0.08, "cfi": 0.9, "tli": 0.9}


def cronbach_alpha(df: pd.DataFrame) -> float:
    """Cronbach's Alpha cho các mục hỏi trong df (đã loại dòng thiếu)."""
    x = df.dropna()
    k = x.shape[1]
    if k < 2:
        return float("nan")
    return float(k / (k - 1) * (1 - x.var(ddof=1).sum() / x.sum(axis=1).var(ddof=1)))


def parse_latent(model_text: str) -> dict[str, list[str]]:
    """Trích các biến tiềm ẩn và mục hỏi từ các dòng 'F =~ a + b + c'."""
    out = {}
    for line in model_text.splitlines():
        line = line.split("#")[0].strip()
        m = re.match(r"^(\w+)\s*=~\s*(.+)$", line)
        if m:
            out[m.group(1)] = [t.strip() for t in m.group(2).split("+") if t.strip()]
    return out


def danh_gia(v: float, nguong: float, lon_hon: bool = True) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "Không tính được"
    return "Đạt" if ((v > nguong) if lon_hon else (v < nguong)) else "Không đạt"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="ket_qua_sem")
    ap.add_argument("--sheet", default=None)
    a = ap.parse_args()
    try:
        import semopy
    except ImportError:
        sys.exit("Chưa có thư viện semopy trong môi trường này. Hãy cài đặt (pip install semopy) trên máy có mạng rồi chạy lại.")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(a.data, sheet_name=a.sheet or 0) if a.data.lower().endswith((".xlsx", ".xls")) else pd.read_csv(a.data)
    text = Path(a.model).read_text(encoding="utf-8")
    latent = parse_latent(text)
    mdl = semopy.Model(text)
    mdl.fit(df)  # ước lượng hợp lý cực đại; nếu dữ liệu lệch nặng, cân nhắc biến đổi log và nêu lập luận trong báo cáo
    stats = semopy.calc_stats(mdl).T
    stats.to_csv(out / "sem_chi_so_phu_hop.csv", encoding="utf-8-sig")
    ins = mdl.inspect(std_est=True)
    ins.to_csv(out / "sem_tham_so.csv", index=False, encoding="utf-8-sig")
    est_col = "Est. Std" if "Est. Std" in ins.columns else "Estimate"

    # hệ số đường dẫn (quan hệ cấu trúc): toán tử '~'
    paths = ins[ins["op"] == "~"].copy()
    paths.to_csv(out / "sem_he_so_duong_dan.csv", index=False, encoding="utf-8-sig")
    print("Hệ số đường dẫn:\n", paths[["lval", "op", "rval", est_col, "p-value"]].to_string(index=False))

    # độ tin cậy và giá trị hội tụ theo từng biến tiềm ẩn
    rows = []
    load = ins[ins["op"] == "~"]  # semopy ghi tải nhân tố dưới dạng 'item ~ F'
    for f, items in latent.items():
        sub = load[(load["rval"] == f) & (load["lval"].isin(items))]
        lam = sub[est_col].astype(float).to_numpy()
        ave = float(np.mean(lam ** 2)) if len(lam) else float("nan")
        cr = float(lam.sum() ** 2 / (lam.sum() ** 2 + np.sum(1 - lam ** 2))) if len(lam) else float("nan")
        al = cronbach_alpha(df[items].apply(pd.to_numeric, errors="coerce"))
        rows.append({"Biến tiềm ẩn": f, "Số mục": len(items), "Tải nhỏ nhất": float(lam.min()) if len(lam) else float("nan"),
                     "Alpha": al, "CR": cr, "AVE": ave,
                     "Đánh giá Alpha": danh_gia(al, NGUONG["alpha"]), "Đánh giá tải": danh_gia(float(lam.min()) if len(lam) else None, NGUONG["tai"]),
                     "Đánh giá CR": danh_gia(cr, NGUONG["cr"]), "Đánh giá AVE": danh_gia(ave, NGUONG["ave"])})
    rel = pd.DataFrame(rows)
    rel.to_csv(out / "sem_do_tin_cay.csv", index=False, encoding="utf-8-sig")
    print("\nĐộ tin cậy và giá trị hội tụ:\n", rel.round(3).to_string(index=False))

    fit = {k: float(stats.loc[k].iloc[0]) for k in ("RMSEA", "CFI", "TLI") if k in stats.index}
    print("\nChỉ số phù hợp (ngưỡng: RMSEA < 0,08; CFI và TLI > 0,9):")
    for k, v in fit.items():
        print(f"  {k} = {v:.3f} -> {danh_gia(v, NGUONG[k.lower()], lon_hon=(k != 'RMSEA'))}")
    print(f"\nĐã ghi kết quả vào {out}/")


if __name__ == "__main__":
    main()
