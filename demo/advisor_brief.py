"""Prototype hỗ trợ quyết định cho cố vấn học tập (Đề cương GĐ7 + kịch bản demo GĐ10).

Luồng: câu hỏi của cố vấn -> đầu vào (danh sách sinh viên của "học kỳ mới", đã giả danh) -> xử lý (kiểm tra schema,
chặn biến cấm, chấm điểm bằng mô hình M4, reason code) -> đầu ra (hàng đợi đề xuất + bằng chứng) -> CON NGƯỜI PHÊ DUYỆT
-> hành động (chỉ xuất danh sách liên hệ cho trường hợp đã duyệt) -> nhật ký kiểm toán.

Bước 1 - tạo hàng đợi đề xuất:
    python demo/advisor_brief.py propose
Bước 2 - cố vấn mở demo/output/advisor_queue.csv, điền cột co_van_duyet = Co/Khong (có thể kèm ghi_chu), lưu lại.
    (để demo nhanh: python demo/advisor_brief.py simulate-review  -> giả lập cố vấn duyệt, CÓ GHI RÕ là giả lập)
Bước 3 - xuất danh sách liên hệ, chỉ gồm trường hợp được duyệt:
    python demo/advisor_brief.py act

Giới hạn (theo M4/M5): điểm chỉ dùng để XẾP HẠNG, không phải xác suất; mô hình chỉ được kiểm chứng trên dữ liệu SAPE
(sàng lọc đồng thời, sinh viên đã có CGPA); không tự gửi thông điệp; giảng viên không nhận điểm cá nhân.
Thành phần LLM (tùy chọn): xem demo/output/llm_prompt.md - chỉ diễn đạt lại reason code đã có, không thêm nhận định.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import config as C                                    # noqa: E402
from model_experiment import FEATS, make_models       # noqa: E402

OUT = ROOT / "demo" / "output"
VIEW = C.PROCESSED / f"view_predictive_{C.PREPARED_VERSION}.csv"
FAIR = C.PROCESSED / f"view_fairness_audit_{C.PREPARED_VERSION}.csv"
CAPACITY = 0.30
MIN_CONTRIB = 0.15   # đóng góp log-odds tối thiểu để một tín hiệu được nêu làm lý do
MODEL_ID = f"LR-E2 (prepared {C.PREPARED_VERSION}, seed {C.SEED})"

# Câu chữ hỗ trợ cho từng tín hiệu (mô tả hành vi/nhu cầu, không đánh giá năng lực hay hoàn cảnh)
PHRASES = {
    "attendance_pct": ("Chuyên cần tự báo cáo {v:.0f}%, thấp hơn mức chung của khóa ({ref:.0f}%)",
                       "Hỏi thăm lịch học, việc đi lại và khó khăn khi đến lớp"),
    "english_ord_1": ("Tự đánh giá tiếng Anh ở mức cơ bản", "Giới thiệu lớp/nhóm hỗ trợ tiếng Anh học thuật"),
    "english_ord_3": ("Thuộc nhóm tự đánh giá tiếng Anh nâng cao, nhóm có tỷ lệ cần hỗ trợ cao hơn mức chung trong dữ liệu",
                      "Hỏi về phương pháp học và mức độ phù hợp của môn học"),
    "co_curricular": ("Tham gia hoạt động ngoại khóa", "Trao đổi về cân bằng thời gian giữa ngoại khóa và học tập"),
    "current_semester": ("Đang ở học kỳ {v:.0f}, muộn hơn phần lớn khóa", "Rà soát tiến độ tín chỉ và kế hoạch tốt nghiệp"),
    "uni_transport": ("Không sử dụng xe của trường", "Hỏi về thời gian di chuyển đến trường"),
    "personal_computer": ("Chưa có máy tính cá nhân", "Giới thiệu phòng máy/chương trình mượn thiết bị"),
    "social_media_hours": ("Thời gian mạng xã hội {v:.0f} giờ/ngày, cao hơn mức chung ({ref:.0f})", "Trao đổi về kế hoạch học tập hằng ngày"),
    "study_hours": ("Giờ tự học {v:.0f} giờ/ngày, thấp hơn mức chung ({ref:.0f})", "Trao đổi về kế hoạch tự học"),
}
SHORT = {"Chuyên cần": "Chuyên cần thấp hơn mức chung", "Đang ở": "Học kỳ muộn hơn phần lớn khóa",
         "Thời gian": "Thời gian mạng xã hội cao", "Giờ tự": "Giờ tự học thấp"}
OPENING ="Em ơi, thầy/cô là cố vấn học tập của khóa; thầy/cô muốn hỏi thăm việc học kỳ này của em, có gì cần hỗ trợ em cứ chia sẻ nhé."


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fit_model(tr):
    model = make_models(FEATS)["LR"]
    X, y = tr[FEATS], tr.needs_support.astype(int).values
    oof = np.zeros(len(y))
    for a, b in StratifiedKFold(5, shuffle=True, random_state=C.SEED).split(X, y):
        oof[b] = clone(model).fit(X.iloc[a], y[a]).predict_proba(X.iloc[b])[:, 1]
    cutoff = float(np.quantile(oof, 1 - CAPACITY))            # điểm cắt học từ train (như M4)
    return clone(model).fit(X, y), cutoff


def reasons(model, X, ref):
    prep, coef = model.named_steps["prep"], model.named_steps["clf"].coef_[0]
    names = [n.split("__", 1)[1] for n in prep.get_feature_names_out()]
    contrib = prep.transform(X) * coef
    out = []
    for i in range(len(X)):
        items = []
        for j in np.argsort(-contrib[i]):
            if contrib[i, j] < MIN_CONTRIB or len(items) == 2:     # chỉ nêu lý do có đóng góp đáng kể
                break
            key = names[j]
            if key not in PHRASES:
                continue
            raw = key if key.startswith("english") else key
            v = X.iloc[i][raw] if raw in X.columns else None
            text, action = PHRASES[key]
            items.append((text.format(v=v if v is not None and not pd.isna(v) else 0, ref=ref.get(raw, 0)), action))
        out.append(items)
    return out


def propose():
    OUT.mkdir(parents=True, exist_ok=True)
    pv = pd.read_csv(VIEW)
    missing = sorted(set(FEATS) - set(pv.columns)); banned = sorted(set(pv.columns) & set(C.BANNED_FROM_MODEL))
    assert not missing, f"Thiếu cột đầu vào: {missing}"
    assert not banned, f"Đầu vào chứa biến bị cấm: {banned}"
    tr = pv[pv.split == "train"].reset_index(drop=True)
    cohort = pv[pv.split == "test"].reset_index(drop=True)      # đóng vai "học kỳ mới" (chưa dùng để huấn luyện)
    model, cutoff = fit_model(tr)
    score = model.predict_proba(cohort[FEATS])[:, 1]
    ref = {"attendance_pct": tr.attendance_pct.median(), "social_media_hours": tr.social_media_hours.median(),
           "study_hours": tr.study_hours.median()}
    rs = reasons(model, cohort[FEATS], ref)
    q = pd.DataFrame({"resp_id": cohort.resp_id, "_score": score})
    q["thu_tu_uu_tien"] = q["_score"].rank(ascending=False, method="first").astype(int)
    q["duoc_de_xuat"] = np.where(score >= cutoff, "Co", "Khong")
    q["ly_do_1"] = [r[0][0] if len(r) > 0 else "" for r in rs]
    q["ly_do_2"] = [r[1][0] if len(r) > 1 else "" for r in rs]
    q["goi_y_trao_doi"] = ["; ".join(a for _, a in r) for r in rs]
    q["cau_mo_loi"] = OPENING
    q["co_van_duyet"] = ""
    q["ghi_chu"] = ""
    queue = q[q.duoc_de_xuat == "Co"].sort_values("thu_tu_uu_tien").drop(columns=["_score", "duoc_de_xuat"])
    queue.to_csv(OUT / "advisor_queue.csv", index=False, encoding="utf-8-sig")

    # Bằng chứng kèm theo: hiệu năng đã kiểm chứng (M4) + kiểm tra tỷ lệ đề xuất theo nhóm của chính danh sách này
    exp = json.loads((C.REPORTS / "milestone4" / "experiment_results.json").read_text(encoding="utf-8"))
    fair = pd.read_csv(FAIR).set_index("resp_id").loc[cohort.resp_id]
    flagged = (score >= cutoff)
    by = {g: {str(k): round(float(flagged[(fair[g] == k).values].mean()), 3) for k in fair[g].dropna().unique()} for g in C.FAIRNESS_AUDIT}
    agg = {"so_sinh_vien": int(len(cohort)), "so_de_xuat": int(flagged.sum()), "ty_le_de_xuat": round(float(flagged.mean()), 3),
           "ly_do_pho_bien": pd.Series([SHORT.get(x.split(" ")[0] + " " + x.split(" ")[1], x.split(" (")[0])
                                        for r, f in zip(rs, flagged) if f for x, _ in r]).value_counts().head(5).to_dict()}
    brief = [
        "# Bản tóm tắt cho cố vấn học tập (demo - dữ liệu SAPE đã giả danh)", "",
        f"- Danh sách đề xuất: **{agg['so_de_xuat']} / {agg['so_sinh_vien']} sinh viên** ({agg['ty_le_de_xuat']:.0%}), theo năng lực tư vấn {CAPACITY:.0%}.",
        "- Thứ tự chỉ là gợi ý. **Cố vấn quyết định** có liên hệ hay không (cột `co_van_duyet`); hệ thống không tự gửi thông điệp.",
        f"- Mức tin cậy đã kiểm chứng (M4, tập kiểm tra độc lập): bắt được khoảng {exp['test_holdout']['LR']['at_train_cutoff_30']['recall']:.0%} sinh viên cần hỗ trợ; "
        f"khoảng {exp['test_holdout']['LR']['at_train_cutoff_30']['precision']:.0%} số được đề xuất thực sự thuộc nhóm cần hỗ trợ. "
        "Nhiều sinh viên cần hỗ trợ sẽ không có trong danh sách: vẫn giữ kênh sinh viên tự tìm đến và giảng viên giới thiệu.",
        f"- Tỷ lệ được đề xuất theo nhóm (giám sát công bằng, không dùng để ra quyết định): {json.dumps(by, ensure_ascii=False)}.",
        f"- Lý do xuất hiện nhiều nhất: {json.dumps(agg['ly_do_pho_bien'], ensure_ascii=False)}.", "",
        "Thông tin cho giảng viên/quản lý chương trình chỉ ở mức tổng hợp như trên; không chia sẻ danh sách cá nhân hay điểm số.",
    ]
    (OUT / "advisor_brief.md").write_text("\n".join(brief), encoding="utf-8")
    (OUT / "llm_prompt.md").write_text(
        "# Prompt cho thành phần LLM (tùy chọn)\n\nBạn hỗ trợ cố vấn học tập soạn câu mở lời. Chỉ dùng các lý do được cung cấp; "
        "không suy đoán hoàn cảnh, sức khỏe, tài chính hay năng lực; không dùng từ mang tính gán nhãn (yếu, kém, có vấn đề, nguy cơ); "
        "không nhắc tới điểm số hay mô hình. Viết 2-3 câu thân thiện, đề nghị gặp trao đổi. Bản nháp sẽ được cố vấn sửa và duyệt trước khi gửi.\n\n"
        "Lý do: {ly_do_1}; {ly_do_2}\nGợi ý trao đổi: {goi_y_trao_doi}\n", encoding="utf-8")
    audit = {"thoi_diem_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "buoc": "propose", "mo_hinh": MODEL_ID,
             "du_lieu": str(VIEW.name), "sha256_du_lieu": sha(VIEW), "diem_cat_hoc_tu_train": round(cutoff, 4), "nang_luc": CAPACITY,
             "so_de_xuat": agg["so_de_xuat"], "bien_cam_trong_dau_vao": banned, "tu_dong_lien_he": False}
    with open(OUT / "audit_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(audit, ensure_ascii=False) + "\n")
    print(json.dumps({"advisor_queue": str(OUT / "advisor_queue.csv"), **agg, "fairness_flag_rate": by}, ensure_ascii=False, indent=1))
    print(queue.head(5)[["thu_tu_uu_tien", "resp_id", "ly_do_1", "ly_do_2"]].to_string(index=False))


def log(entry):
    """Ghi nối một sự kiện vào nhật ký kiểm toán (không sửa, không xóa dòng cũ)."""
    entry = {"thoi_diem_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
    with open(OUT / "audit_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def simulate_review():
    """Chỉ để demo: giả lập cố vấn duyệt (duyệt 2/3 đầu danh sách, từ chối phần còn lại với ghi chú)."""
    q = pd.read_csv(OUT / "advisor_queue.csv", encoding="utf-8-sig", dtype=str).fillna("")
    k = int(round(len(q) * 2 / 3))
    q.loc[:k - 1, "co_van_duyet"] = "Co"
    q.loc[k:, "co_van_duyet"] = "Khong"
    q.loc[k:, "ghi_chu"] = "GIẢ LẬP DEMO: đã gặp trong tháng / sinh viên đã chủ động liên hệ"
    q.to_csv(OUT / "advisor_queue.csv", index=False, encoding="utf-8-sig")
    log({"buoc": "simulate-review", "duyet": k, "tu_choi": int(len(q) - k), "gia_lap": True,
         "ghi_chu": "Chỉ để demo: giả lập quyết định của cố vấn; trong thực tế cố vấn tự điền cột co_van_duyet."})
    print(f"GIẢ LẬP: duyệt {k}/{len(q)} trường hợp (trong thực tế cố vấn tự điền cột co_van_duyet).")


def act():
    q = pd.read_csv(OUT / "advisor_queue.csv", encoding="utf-8-sig", dtype=str).fillna("")
    pending = q[~q.co_van_duyet.isin(["Co", "Khong"])]
    if len(pending):
        log({"buoc": "act", "ket_qua": "tu_choi", "chua_duyet": int(len(pending)), "tu_dong_lien_he": False,
             "ghi_chu": "Cổng phê duyệt con người: còn dòng chưa duyệt nên không xuất danh sách liên hệ."})
        sys.exit(f"Còn {len(pending)} trường hợp chưa được cố vấn duyệt - không xuất danh sách liên hệ (cổng phê duyệt con người).")
    ok = q[q.co_van_duyet == "Co"][["thu_tu_uu_tien", "resp_id", "goi_y_trao_doi", "cau_mo_loi", "ghi_chu"]]
    ok.to_csv(OUT / "contact_list_approved.csv", index=False, encoding="utf-8-sig")
    audit = {"thoi_diem_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "buoc": "act", "duyet": int(len(ok)),
             "tu_choi": int((q.co_van_duyet == "Khong").sum()), "tu_dong_lien_he": False,
             "ghi_chu": "Danh sách chỉ gồm trường hợp cố vấn đã duyệt; việc liên hệ do cố vấn thực hiện."}
    with open(OUT / "audit_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(audit, ensure_ascii=False) + "\n")
    print(json.dumps(audit, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "propose"
    {"propose": propose, "simulate-review": simulate_review, "act": act}[cmd]()
