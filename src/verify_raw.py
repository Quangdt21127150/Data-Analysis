"""Milestone 2 - Initial Structural Verification (read-only).

Đọc file raw, KHÔNG chỉnh sửa, KHÔNG làm sạch. Ghi kết quả kiểm tra cấu trúc vào data/metadata.
Chạy:  python src/verify_raw.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Students_Performance_data_set.xlsx"
META = ROOT / "data" / "metadata"
EXPECTED_SHA256 = "04ebaf9f3a047afe96d9bff22dbe65b2a320e6395f230032735495e7e58277cf"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> dict:
    META.mkdir(parents=True, exist_ok=True)
    digest = sha256(RAW)
    xl = pd.ExcelFile(RAW, engine="openpyxl")
    df = pd.read_excel(xl, sheet_name=xl.sheet_names[0])

    cgpa = "What is your current CGPA?"
    sgpa = "What was your previous SGPA?"
    pos = df[cgpa][df[cgpa] > 0]
    summary = {
        "file": RAW.name,
        "size_bytes": RAW.stat().st_size,
        "sha256": digest,
        "sha256_matches_expected": digest == EXPECTED_SHA256,
        "sheets": xl.sheet_names,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "dtype_counts": {str(k): int(v) for k, v in df.dtypes.astype(str).value_counts().items()},
        "full_duplicate_rows": int(df.duplicated().sum()),
        "missing_cells_total": int(df.isna().sum().sum()),
        "missing_by_column": {c: int(n) for c, n in df.isna().sum().items() if n > 0},
        "cgpa_zero": int((df[cgpa] == 0).sum()),
        "sgpa_zero": int((df[sgpa] == 0).sum()),
        "cgpa_and_sgpa_zero": int(((df[cgpa] == 0) & (df[sgpa] == 0)).sum()),
        "cgpa_positive_n": int(pos.shape[0]),
        "label_feasibility": {
            f"<{t}": {"n_pos": int((pos < t).sum()), "rate": round(float((pos < t).mean()), 4)}
            for t in (2.5, 2.75, 3.0)
        },
    }
    schema = pd.DataFrame(
        {
            "column": df.columns,
            "dtype_initial": df.dtypes.astype(str).values,
            "n_unique": df.nunique(dropna=True).values,
            "n_missing": df.isna().sum().values,
            "example_values": [", ".join(map(str, df[c].dropna().unique()[:5])) for c in df.columns],
        }
    )
    schema.insert(0, "#", range(1, len(schema) + 1))
    schema.to_csv(META / "structural_summary_m2.csv", index=False, encoding="utf-8-sig")
    (META / "structural_summary_m2.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
