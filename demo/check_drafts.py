"""Kiểm tra bản nháp câu mở lời (do LLM hoặc người soạn) TRƯỚC khi đưa cố vấn duyệt - Đề cương GĐ7/GĐ8.

Mỗi bản nháp phải:
  G1  không chứa từ gán nhãn tiêu cực (yếu, kém, có vấn đề, nguy cơ, rủi ro, cảnh báo, ...);
  G2  không nhắc tới điểm số, CGPA, xác suất, mô hình, thuật toán, danh sách gắn cờ;
  G3  không suy đoán chủ đề nhạy cảm không có trong lý do (sức khỏe, tài chính, gia đình, tâm lý, ...);
  G4  chỉ nhắc tới chủ đề có trong reason code của chính sinh viên đó (grounded);
  G5  có lời mời trao đổi và độ dài 1-4 câu.
Bản nháp trượt bất kỳ kiểm tra nào bị trả về cho cố vấn tự viết; script KHÔNG sửa hay gửi gì.

    python demo/check_drafts.py                                  # chạy trên bộ ca kiểm thử demo/draft_test_cases.csv
    python demo/check_drafts.py duong_dan_ban_nhap.csv           # cột: resp_id, ban_nhap (đối chiếu advisor_queue.csv)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "output"

LABEL_WORDS = ["yếu", "kém", "có vấn đề", "nguy cơ", "rủi ro", "cảnh báo", "báo động", "lười", "tụt hậu", "cá biệt", "thất bại", "trượt"]
SCORE_WORDS = [r"(?<!thời )(?<!địa )điểm", "cgpa", "gpa", "xác suất", "mô hình", "thuật toán", "hệ thống chấm", "gắn cờ", "dự đoán", "phần trăm khả năng"]
SENSITIVE = ["sức khỏe", "bệnh", "tài chính", "tiền", "nợ", "gia đình", "bố mẹ", "tâm lý", "trầm cảm", "giới tính", "nơi ở", "ở trọ", "tôn giáo"]
# chủ đề -> từ khóa trong bản nháp; chủ đề hợp lệ khi reason code của sinh viên chứa "key"
TOPICS = {
    "chuyên cần": (["chuyên cần", "đến lớp", "đi học", "lịch học"], "Chuyên cần"),
    "tiếng Anh": (["tiếng anh"], "tiếng Anh"),
    "ngoại khóa": (["ngoại khóa"], "ngoại khóa"),
    "máy tính": (["máy tính", "thiết bị", "phòng máy"], "máy tính"),
    "đi lại": (["xe", "di chuyển", "đi lại"], "xe của trường|lịch học"),
    "tiến độ": (["tín chỉ", "tiến độ", "tốt nghiệp"], "học kỳ"),
    "mạng xã hội": (["mạng xã hội"], "mạng xã hội"),
    "tự học": (["tự học"], "tự học"),
}
INVITE = ["gặp", "trao đổi", "chia sẻ", "nói chuyện", "ghé", "hẹn"]


def has(text: str, w: str) -> bool:
    """Khớp nguyên từ (tránh 'xe' khớp 'xem'); w có thể là regex."""
    return re.search(rf"(?<!\w){w}(?!\w)", text) is not None


def check(draft: str, reasons: str) -> dict:
    d = draft.lower()
    fails = []
    hit = [w for w in LABEL_WORDS if has(d, re.escape(w))]
    if hit: fails.append(f"G1 gán nhãn: {hit}")
    hit = [w.split(")")[-1] for w in SCORE_WORDS if has(d, w)]
    if hit: fails.append(f"G2 nhắc điểm/mô hình: {hit}")
    hit = [w for w in SENSITIVE if has(d, re.escape(w)) and w not in reasons.lower()]
    if hit: fails.append(f"G3 suy đoán nhạy cảm: {hit}")
    ungrounded = [t for t, (kws, key) in TOPICS.items() if any(has(d, re.escape(k)) for k in kws) and not re.search(key, reasons, re.I)]
    if ungrounded: fails.append(f"G4 chủ đề không có trong lý do: {ungrounded}")
    n_sent = len([s for s in re.split(r"[.!?]+", draft) if s.strip()])
    if not any(has(d, w) for w in INVITE) or not 1 <= n_sent <= 4: fails.append(f"G5 thiếu lời mời hoặc độ dài {n_sent} câu")
    return {"dat": not fails, "loi": fails}


def main():
    queue = pd.read_csv(OUT / "advisor_queue.csv", encoding="utf-8-sig", dtype=str).fillna("")
    reasons = {r.resp_id: f"{r.ly_do_1}; {r.ly_do_2}; {r.goi_y_trao_doi}" for r in queue.itertuples()}
    test_mode = len(sys.argv) < 2
    src = ROOT / "demo" / "draft_test_cases.csv" if test_mode else Path(sys.argv[1])
    df = pd.read_csv(src, encoding="utf-8-sig", dtype=str).fillna("")
    rows = []
    for r in df.itertuples():
        res = check(r.ban_nhap, reasons.get(r.resp_id, ""))
        rows.append({"resp_id": r.resp_id, "dat": res["dat"], "loi": " | ".join(res["loi"]),
                     **({"ky_vong": r.ky_vong} if test_mode else {})})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "draft_check_results.csv", index=False, encoding="utf-8-sig")
    summary = {"thoi_diem_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "buoc": "check-drafts",
               "nguon": src.name, "so_ban_nhap": len(out), "dat": int(out.dat.sum()), "tra_ve_co_van": int((~out.dat).sum())}
    if test_mode:
        exp = out.ky_vong.str.lower().eq("dat")
        summary.update({"ca_dung_bi_chan_nham": int((exp & ~out.dat).sum()), "ca_sai_lot_qua": int((~exp & out.dat).sum()),
                        "do_chinh_xac_bo_kiem_tra": round(float((exp == out.dat).mean()), 3)})
    with open(OUT / "audit_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    print(out.to_string(index=False))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
