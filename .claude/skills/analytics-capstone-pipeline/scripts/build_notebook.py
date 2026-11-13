# -*- coding: utf-8 -*-
"""Sinh sổ tay Jupyter/Colab chạy toàn bộ quy trình cho một cấu hình cụ thể.

Sổ tay nhúng sẵn dspipe.py, make_report.py, docx_kit.py (qua %%writefile) nên có thể chạy độc lập trên Colab:
chỉ cần tải lên tệp dữ liệu. Không cần nbformat; tệp .ipynb được ghi trực tiếp dưới dạng JSON.
Cách dùng:  python build_notebook.py --config config.json --out Quy_trinh.ipynb
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Windows: console mặc định cp1252 không in được tiếng Việt
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


HERE = Path(__file__).resolve().parent


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(True)}


def code(t):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t.strip("\n").splitlines(True)}


def build(cfg_path: str, out: str) -> None:
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    cfg["data_path"] = Path(cfg["data_path"]).name
    cfg.pop("_goi_y", None)
    cells = [
        md("# Quy trình phân tích dữ liệu có đăng ký trước\nSổ tay này chạy lần lượt: kiểm toán, chuẩn bị, đăng ký trước, chẩn đoán, mô hình hóa, kiểm chứng và dựng báo cáo. "
           "Hãy tải lên tệp dữ liệu có tên trùng `data_path` trong cấu hình ở ô thứ hai."),
        code("# Ô 1. Ghi các mô-đun của quy trình ra đĩa\nimport os, json\nos.makedirs('references', exist_ok=True)\nos.makedirs('scripts', exist_ok=True)"),
    ]
    for name in ("dspipe.py", "docx_kit.py", "make_report.py"):
        src = (HERE / name).read_text(encoding="utf-8")
        cells.append(code(f"%%writefile scripts/{name}\n{src}"))
    cells.append(code("%%writefile references/refs.json\n" + (HERE.parent / "references" / "refs.json").read_text(encoding="utf-8")))
    cells.append(code("%%writefile config.json\n" + json.dumps(cfg, ensure_ascii=False, indent=2)))
    cells.append(code(f"# Ô 2. Tải dữ liệu lên (Colab) hoặc đặt tệp cùng thư mục\ntry:\n    from google.colab import files\n    files.upload()\nexcept ImportError:\n    print('Không phải Colab: hãy đặt {cfg['data_path']} cùng thư mục với sổ tay.')"))
    for title, stage in (("Kiểm toán dữ liệu", "profile"), ("Chuẩn bị dữ liệu và nhật ký biến đổi", "prepare"), ("Đăng ký trước tiêu chí", "prereg"),
                         ("Chẩn đoán", "diagnose"), ("Mô hình hóa (thêm --fast để chạy thử)", "model"), ("Kiểm chứng nhất quán", "verify")):
        cells.append(md(f"## {title}"))
        cells.append(code(f"!python scripts/dspipe.py {stage} --config config.json"))
    cells.append(md("## Dựng sản phẩm đầu ra"))
    cells.append(code("!python scripts/make_report.py --config config.json"))
    cells.append(code(f"import pandas as pd, glob\nfor f in sorted(glob.glob('{cfg['out_dir']}/tables/model_main_ranking.csv')):\n    display(pd.read_csv(f))"))
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    Path(out).write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Đã ghi", out, "-", len(cells), "ô")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    build(a.config, a.out)
