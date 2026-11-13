# -*- coding: utf-8 -*-
"""Dựng sản phẩm đầu ra từ kết quả của dspipe.py cho BẤT KỲ bộ dữ liệu nào.

Đầu ra (trong <thư mục cấu hình>/<out_dir>/deliverables/):
  1. BaoCao_TongHop.docx            báo cáo học thuật tiếng Việt, KHÔNG chứa mã thực thi, có mục lục kèm số trang,
                                   trích dẫn đánh số [x], danh mục tài liệu tham khảo
  2. GiaiThich_MaNguon_va_HoTro.docx  tài liệu riêng giải thích mã nguồn và cách trợ lý hỗ trợ (đúng yêu cầu tách khỏi báo cáo chính)
  3. deck_outline.json             dàn ý 12 slide kèm kịch bản đọc, để dựng bằng loại Slides (hoặc PowerPoint)
  4. KichBan_ThuyetTrinh.docx      kịch bản đọc từng slide (bản dự phòng)

Mọi con số, nhận định và kết luận đều được sinh từ tệp kết quả (không nhập tay), nên không bao giờ lệch với bảng.
Cách dùng:  python make_report.py --config config.json [--only report|code|deck]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import docx_kit as K  # noqa: E402
from docx_kit import Report, build_with_toc, vi, pct  # noqa: E402
import dspipe as D  # noqa: E402

# Windows: console mặc định cp1252 không in được tiếng Việt
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


REFS = json.loads((HERE.parent / "references" / "refs.json").read_text(encoding="utf-8"))
W = K.PORTRAIT_W
CRIT_NAMES = {
    "S1": "Năng lực sàng lọc tuyệt đối",
    "S2": "Giá trị tăng thêm so với baseline",
    "S3": "Rút gọn đặc trưng mà không mất năng lực",
    "S4": "Hiệu chuẩn xác suất",
    "S5": "Công bằng giữa các nhóm",
}


# ---------------------------------------------------------------------------------------------
# Nạp kết quả
# ---------------------------------------------------------------------------------------------
class Res:
    def __init__(self, cfg_path: str):
        self.cfg_path = Path(cfg_path).resolve()
        self.cfg = D.load_cfg(self.cfg_path)
        self.dirs = D.out_dirs(self.cfg)
        self.out = Path(self.dirs["root"])
        j = lambda n: json.loads((self.out / n).read_text(encoding="utf-8"))  # noqa: E731
        self.audit, self.prep, self.prereg = j("audit.json"), j("prepared_info.json"), j("evaluation_plan_prereg.json")
        self.diag, self.res, self.ver = j("diagnose.json"), j("results.json"), j("verify.json")
        xp = self.out / "xai_status.json"
        self.xai = json.loads(xp.read_text(encoding="utf-8")) if xp.exists() else {}
        self.tab = {}
        for p in (self.out / "tables").glob("*.csv"):
            try:
                self.tab[p.stem] = pd.read_csv(p)
            except pd.errors.EmptyDataError:   # bảng rỗng (ví dụ chưa khai báo nhóm công bằng hoặc nhóm đặc trưng)
                pass
        self.fig = {p.stem.split("_")[0]: str(p) for p in (self.out / "figures").glob("*.png")}
        self.deliver = self.out / "deliverables"
        self.deliver.mkdir(parents=True, exist_ok=True)

    # tiện ích truy xuất
    def model(self, key: str) -> dict:
        return next(m for m in self.res["main"] if m["model"] == key)

    @property
    def best(self) -> dict:
        return self.model(self.res["recommended_model"])

    @property
    def label(self) -> str:
        return self.cfg["target"]["column"]

    @property
    def pos_name(self) -> str:
        return self.cfg["target"].get("positive_name") or "nhóm cần chú ý"

    def target_rule(self) -> str:
        t = self.cfg["target"]
        if t["type"] == "threshold":
            return f"{t['column']} {t['positive_if']} {vi(t['threshold'], 2)}"
        return f"{t['column']} thuộc {t['positive_values']}"


def th(n) -> str:
    """Dấu chấm ngăn cách hàng nghìn theo quy ước tiếng Việt."""
    return f"{int(n):,}".replace(",", ".")


def short(s: str, n: int = 46) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def widths(props: list[float]) -> list[int]:
    tot = sum(props)
    w = [int(W * p / tot) for p in props]
    w[-1] += W - sum(w)
    return w


def RK(R) -> str:
    """Khóa cột recall tại tỷ lệ gắn cờ chính của tiêu chí S1."""
    return f"recall_{R.cfg['criteria']['recall_rate']}"


def ci_txt(v, lo, hi, nd=3):
    return f"{vi(v, nd)} [{vi(lo, nd)}; {vi(hi, nd)}]"


# ---------------------------------------------------------------------------------------------
# Sinh nhận định theo luật (không phụ thuộc bộ dữ liệu)
# ---------------------------------------------------------------------------------------------
def verdict_text(R: Res) -> dict:
    c, m, res = R.res["criteria"], R.best, R.res
    base = R.model("B1")
    pr = R.prereg["tieu_chi"]
    b = {}
    b["S1"] = (f"AUC của {m['label']} là {ci_txt(m['auc'], m['auc_lo'], m['auc_hi'])}; recall tại tỷ lệ gắn cờ "
               f"{pct(R.cfg['criteria']['recall_rate'], 0)} là {pct(m.get(RK(R), float('nan')))}. "
               f"Tiêu chí đã đăng ký: {pr['S1']}.")
    pd_ = next(x for x in res["paired"] if "baseline" in x["comparison"])
    b["S2"] = (f"Chênh lệch AUC so với baseline ({short(res['baseline_feature'], 40)}) là "
               f"{ci_txt(pd_['delta_auc'], pd_['lo'], pd_['hi'])}. Tiêu chí: {pr['S2']}.")
    keep = res.get("items_mean")
    b["S3"] = (f"Mô hình L1 giữ trung bình {vi(keep, 1)} trên {res['n_features']} đặc trưng gốc. Tiêu chí: {pr['S3']}.")
    cal = res["calibration"]
    b["S4"] = (f"Độ dốc hiệu chuẩn {vi(cal['slope'], 2)}, Brier {vi(cal['brier'], 3)} so với {vi(cal['brier_base'], 3)} của "
               f"mô hình chỉ dùng tỷ lệ nền. Tiêu chí: {pr['S4']}.")
    fair = R.tab.get("model_fairness")
    if fair is not None and "conclusive" in fair:
        sub = fair[fair["reference"] == False]  # noqa: E712
        nconc = int(sub["conclusive"].sum()) if len(sub) else 0
        b["S5"] = (f"Có {len(sub)} so sánh nhóm với nhóm tham chiếu, trong đó {nconc} so sánh đủ chắc chắn để kết luận. "
                   f"Tiêu chí: {pr['S5']}.")
    else:
        b["S5"] = "Chưa khai báo thuộc tính nhóm (fairness_cols) nên chưa đánh giá công bằng."
    return b


def implications(R: Res) -> list[str]:
    c = R.res["criteria"]
    out = []
    if str(c["S1"]).startswith("Đạt"):
        out.append("Năng lực sàng lọc đạt ngưỡng đã đăng ký, nên mô hình có thể được thử nghiệm làm công cụ hỗ trợ ưu tiên "
                   "nguồn lực, luôn kèm đánh giá của con người và theo dõi hiệu quả thực tế.")
    else:
        out.append("Năng lực sàng lọc chưa đạt ngưỡng đã đăng ký, vì vậy kết quả không đủ để dùng làm công cụ quyết định độc lập; "
                   "chỉ nên dùng để minh họa tín hiệu và để định hướng thu thập thêm dữ liệu.")
    if not str(c["S2"]).startswith("Đạt"):
        out.append("Mô hình nhiều biến chưa chứng minh được giá trị tăng thêm so với baseline đơn giản; về thực hành, một quy tắc "
                   "đơn giản dựa trên đặc trưng baseline cho hiệu quả tương đương với chi phí triển khai thấp hơn.")
    else:
        out.append("Mô hình nhiều biến có giá trị tăng thêm so với baseline với khoảng tin cậy loại trừ 0, biện minh cho chi phí "
                   "thu thập thêm đặc trưng.")
    if str(c["S3"]).startswith("Đạt"):
        out.append("Bộ đặc trưng có thể rút gọn mà không mất năng lực đáng kể, giúp giảm gánh nặng thu thập dữ liệu.")
    if str(c["S4"]).startswith("Đạt"):
        out.append("Xác suất dự báo được hiệu chuẩn chấp nhận được, cho phép diễn giải điểm nguy cơ như xác suất ở mức thận trọng.")
    else:
        out.append("Xác suất dự báo chưa hiệu chuẩn tốt, nên chỉ dùng thứ hạng nguy cơ, không diễn giải điểm như xác suất tuyệt đối.")
    if str(c["S5"]).startswith("Chưa kết luận"):
        out.append("Chưa đủ bằng chứng để kết luận về công bằng giữa các nhóm do khoảng tin cậy rộng; cần thêm dữ liệu trước khi "
                   "đưa vào vận hành và không dùng thuộc tính nhóm làm đặc trưng đầu vào.")
    elif str(c["S5"]).startswith("Không đạt"):
        out.append("Phát hiện chênh lệch năng lực giữa các nhóm vượt ngưỡng; cần xử lý hoặc hiệu chỉnh ngưỡng theo nhóm trước khi triển khai.")
    return out


def limits(R: Res) -> list[str]:
    cx, a = R.cfg.get("context", {}) or {}, R.audit
    L = []
    if cx.get("self_reported") is not False:
        L.append(f"Đặc trưng và có thể cả nhãn là dữ liệu tự khai nên chịu sai lệch báo cáo và sai lệch phương pháp chung {K_C('podsakoff')}.")
    if cx.get("cross_sectional") is not False:
        L.append("Dữ liệu cắt ngang chỉ cho phép kết luận về liên hệ, không cho phép kết luận nhân quả; để ước lượng tác động của can thiệp "
                 "cần thiết kế thực nghiệm hoặc dữ liệu dọc có kiểm soát nhiễu " + K_C("hernan", "shmueli") + ".")
    if cx.get("single_site") is not False:
        L.append("Mẫu đến từ một nguồn duy nhất nên chưa có kiểm định ngoài (external validation); khả năng khái quát sang cơ sở khác chưa được kiểm chứng.")
    L.append(f"Nhãn được định nghĩa bằng ngưỡng ({R.target_rule()}); ngưỡng này cần được chuyên gia nghiệp vụ xác nhận và kết quả có thể thay đổi khi đổi ngưỡng.")
    L.append(f"Số ca dương là {a['n_positive']} với {a['n_features']} đặc trưng (EPV ≈ {vi(a['events_per_feature'], 1)}), "
             f"nên các ước lượng có độ bất định đáng kể; khoảng tin cậy được báo cáo thay cho ước lượng điểm {K_C('peduzzi', 'riley20')}.")
    if R.res.get("auto_excluded_leakage"):
        L.append("Đặc trưng nghi rò rỉ đã bị loại khỏi mô hình: " + "; ".join(short(x, 60) for x in R.res["auto_excluded_leakage"]) +
                 ". Nếu sau này xác nhận chúng hợp lệ về mặt thời điểm thu thập, cần chạy lại toàn bộ.")
    if R.res.get("fast_mode"):
        L.append("LƯU Ý: kết quả này được chạy ở chế độ nhanh (ít lần lặp, ít lần bootstrap), chỉ dùng để thử nghiệm; cần chạy đầy đủ trước khi nộp.")
    for n in cx.get("notes", []) or []:
        L.append(str(n))
    return L


_CUR = {"r": None}


def K_C(*keys):
    return _CUR["r"].C(*keys)


# ---------------------------------------------------------------------------------------------
# Báo cáo chính
# ---------------------------------------------------------------------------------------------
def cover(r: Report, R: Res):
    t = R.cfg["team"]
    for _ in range(3):
        r.spacer(24)
    r.p("BÁO CÁO PHÂN TÍCH DỮ LIỆU", align="c", size=24, bold=True, color=K.BLUE_DARK, after=6)
    r.p(R.cfg["project_name"].upper(), align="c", size=17, bold=True, color=K.BLUE_MID, after=6)
    r.p(f"Sàng lọc {R.pos_name} và đánh giá có đăng ký trước", align="c", size=13, italic=True, after=40)
    rows = []
    if t.get("course"):
        rows.append(("Học phần", t["course"]))
    if t.get("name"):
        rows.append(("Nhóm thực hiện", t["name"]))
    if t.get("members"):
        rows.append(("Thành viên", "; ".join(t["members"])))
    if t.get("advisor"):
        rows.append(("Giảng viên", t["advisor"]))
    rows.append(("Dữ liệu", f"{Path(R.cfg['data_path']).name} (SHA-256: {R.audit['raw_sha256'][:16]}...)"))
    rows.append(("Mã băm kế hoạch đăng ký trước", R.res["prereg_sha256"][:16] + "..."))
    r.kv_table(rows, widths([3, 7]), ("Hạng mục", "Nội dung"))


def toc_page(r: Report):
    r.pagebreak()
    r.p("MỤC LỤC", align="c", size=17, bold=True, color=K.BLUE_DARK, after=10)
    r.toc_placeholder()


def abstract(r: Report, R: Res):
    a, m, c = R.audit, R.best, R.res["criteria"]
    r.h1("Tóm tắt điều hành", key="abs", numbered=False)
    n_ok = sum(str(v).startswith("Đạt") for v in c.values())
    r.p(f"Báo cáo trình bày quy trình phân tích hoàn chỉnh trên bộ dữ liệu gồm {th(a['n_raw'])} dòng thô, trong đó {th(a['n_valid_label'])} dòng có nhãn hợp lệ "
        f"và {th(R.prep['n_primary'])} dòng thuộc mẫu chính ({R.prep['n_pos_primary']} ca thuộc {R.pos_name}, tỷ lệ {pct(R.res['prevalence'])}). "
        f"Nhãn được định nghĩa là: {R.target_rule()}.")
    r.p(f"Năm tiêu chí thành công được đăng ký và băm SHA-256 trước khi huấn luyện mô hình. Kết quả: {n_ok}/5 tiêu chí đạt. "
        f"Mô hình được giữ lại là {m['label']} với AUC {ci_txt(m['auc'], m['auc_lo'], m['auc_hi'])} trong kiểm định chéo phân tầng lặp "
        f"{R.cfg['cv']['splits']}×{R.cfg['cv']['repeats']} và {th(R.cfg['cv']['n_boot'])} lần bootstrap {r.C('kohavi', 'efron')}.")
    r.callout("Thông điệp chính", implications(R)[:3])


def sec_context(r: Report, R: Res):
    r.h1("Bối cảnh, câu hỏi phân tích và giả định", key="ctx")
    st = R.cfg.get("stakeholders") or []
    aq = R.cfg.get("analysis_questions") or []
    if st:
        src = R.cfg.get("stakeholders_source", "assumed")
        note = ("Các nhu cầu dưới đây được nhóm giả định từ bối cảnh, chưa qua phỏng vấn người dùng thật; cần được xác nhận trước khi triển khai."
                if src == "assumed" else "Các nhu cầu dưới đây được thu thập từ phỏng vấn người dùng thực.")
        r.p("Các bên liên quan và quyết định cần hỗ trợ. " + note)
        r.table(["Vai trò", "Nỗi đau", "Quyết định cần hỗ trợ"], [[s.get("role", ""), s.get("pain", ""), s.get("decision", "")] for s in st],
                widths([2, 4, 4]), "stake", "Các bên liên quan và quyết định cần hỗ trợ", fs=10.5)
    else:
        r.p("Cấu hình chưa khai báo bên liên quan; báo cáo vì vậy tập trung vào câu hỏi chung: các đặc trưng sẵn có phân biệt được "
            f"{R.pos_name} với phần còn lại đến mức nào, và có đủ cơ sở để dùng làm công cụ sàng lọc hay không.")
    if aq:
        r.table(["Mã", "Mức", "Câu hỏi"], [[q.get("id", ""), q.get("level", ""), q.get("question", "")] for q in aq],
                widths([1, 2, 7]), "aq", "Các câu hỏi phân tích", fs=10.5)
    r.h2("Khung phương pháp")
    r.p("Quy trình đi theo chu trình khoa học dữ liệu: hiểu nghiệp vụ, kiểm toán dữ liệu, chuẩn bị có nhật ký, đăng ký trước tiêu chí, chẩn đoán, "
        f"mô hình hóa, kiểm chứng và truyền đạt {r.C('rollins')}. Cách làm có đăng ký trước giúp tách bạch giả thuyết khỏi kết quả, "
        f"hạn chế việc điều chỉnh tiêu chí sau khi đã thấy số liệu {r.C('cawley')}.")


def sec_data(r: Report, R: Res):
    a = R.audit
    r.h1("Dữ liệu và kiểm toán chất lượng", key="data")
    r.p(f"Tệp dữ liệu gốc có {th(a['n_raw'])} dòng; mã băm SHA-256 được ghi để bảo đảm khả năng tái lập. "
        f"Sau xử lý, mẫu chính còn {th(R.prep['n_primary'])} dòng. Bảng {len(r.new_reg['tab']) + 1} liệt kê các vấn đề chất lượng phát hiện tự động cùng hành động xử lý.")
    iss = R.tab["audit_issues"]
    rows = [[x["id"], x["severity"], x["description"], str(int(x["n_rows"])), x["proposed_action"]] for _, x in iss.iterrows()]
    r.table(["Mã", "Mức", "Mô tả", "Số dòng", "Hành động"], rows, widths([1, 1.2, 4.6, 1.2, 3]), "issues",
            "Các vấn đề chất lượng dữ liệu và hành động xử lý", align=["l", "c", "l", "c", "l"], fs=9.5, status_cols=[1])
    r.h2("Nhật ký biến đổi")
    log = R.prep["log"]
    r.table(["Bước", "Trước", "Sau", "Mô tả"], [[x["step"], str(x["n_before"]), str(x["n_after"]), x["detail"]] for x in log],
            widths([3, 1.1, 1.1, 5.8]), "log", "Nhật ký biến đổi dữ liệu (số dòng trước và sau mỗi bước)", align=["l", "c", "c", "l"], fs=9.5)
    if R.res.get("auto_excluded_leakage"):
        r.p("Về rò rỉ dữ liệu: đặc trưng " + ", ".join(f"“{short(x, 60)}”" for x in R.res["auto_excluded_leakage"]) +
            f" có sức dự báo đơn lẻ rất cao và tên gợi ý hệ quả của nhãn, nên bị loại khỏi mô hình để tránh dự báo vòng tròn {r.C('kaufman')}.")
    if R.fig.get("f01"):
        r.figure(R.fig["f01"], "f01", "Phân bố biến nhãn và ngưỡng xác định nhóm", width_in=5.6)


def sec_design(r: Report, R: Res):
    r.h1("Thiết kế đánh giá và đăng ký trước", key="design")
    p = R.prereg
    r.p(f"Kế hoạch đánh giá được băm (SHA-256 {R.res['prereg_sha256'][:16]}...) trước khi chạy mô hình. Kiểm định chéo: {p['kiem_dinh']['chien_luoc']}. "
        f"{p['kiem_dinh']['chong_ro_ri']} Tỷ lệ gắn cờ được xét: " + ", ".join(pct(x, 0) for x in p["ty_le_gan_co"]) + f". Quy tắc chọn mô hình: {p['quy_tac_chon_mo_hinh']}")
    rows = [[k, CRIT_NAMES.get(k, ""), v] for k, v in p["tieu_chi"].items()]
    r.table(["Mã", "Tiêu chí", "Điều kiện đạt"], rows, widths([1, 3.2, 5.8]), "crit", "Năm tiêu chí thành công đăng ký trước", fs=10.5)
    r.table(["Mã", "Mô hình"], [[k, v] for k, v in p["mo_hinh"].items()], widths([1.5, 8.5]), "models",
            "Các phương án mô hình và baseline", fs=10.5)
    r.p(f"Các mô hình tuyến tính và cây được chọn vì tính phổ biến và khả năng diễn giải {r.C('tibshirani', 'breiman', 'friedman')}. "
        f"AUC được diễn giải theo xác suất vượt trội {r.C('hanley')}; do mất cân bằng lớp, độ chính xác theo ngưỡng (precision) và độ phủ (recall) "
        f"tại tỷ lệ gắn cờ cố định được báo cáo kèm theo {r.C('saito')}.")


def sec_diag(r: Report, R: Res):
    r.h1("Kết quả chẩn đoán: nhóm cần chú ý khác phần còn lại ở đâu", key="diag")
    u = R.tab["diagnose_univariate"].sort_values("p_holm")
    r.p(f"Với mỗi đặc trưng, nhóm tính xác suất vượt trội (đặc trưng số, kiểm định Mann-Whitney {r.C('mw')}) hoặc kiểm định độc lập (đặc trưng phân loại), "
        f"điều chỉnh đa so sánh bằng phương pháp Holm {r.C('holm')}. Tỷ lệ theo nhóm dùng khoảng tin cậy Wilson {r.C('wilson')}.")
    rows = []
    for _, x in u.head(12).iterrows():
        eff = vi(x["effect"], 3) if pd.notna(x["effect"]) else ""
        ci = f"[{vi(x['effect_lo'], 3)}; {vi(x['effect_hi'], 3)}]" if pd.notna(x["effect_lo"]) else ""
        rows.append([short(x["feature"], 48), x["type"], eff, ci, f"{x['p_holm']:.4f}".replace(".", ",")])
    r.table(["Đặc trưng", "Loại", "Hiệu ứng", "KTC 95%", "p Holm"], rows, widths([4.4, 1.3, 1.3, 2.2, 1.2]), "uni",
            "Kiểm định đơn biến (hiệu ứng là xác suất vượt trội với biến số; thống kê Cramér V hoặc tương đương với biến phân loại), sắp theo p Holm",
            align=["l", "c", "c", "c", "c"], fs=9.5)
    sig = u[u["p_holm"] < 0.05]
    r.p(f"Có {len(sig)} trên {len(u)} đặc trưng phân biệt được hai nhóm sau hiệu chỉnh Holm" +
        (": " + "; ".join(short(x, 50) for x in sig["feature"]) if len(sig) else "") + ". Đây là liên hệ thống kê, không phải quan hệ nhân quả.")
    adj = R.tab["diagnose_adjusted"]
    rows = [[short(x["term"], 56), ci_txt(x["or"], x["or_lo"], x["or_hi"], 2), f"{x['p_holm']:.3f}".replace(".", ",")] for _, x in adj.iterrows()]
    r.table(["Hạng tử", "Tỷ số chênh hiệu chỉnh [KTC 95%]", "p Holm"], rows, widths([5, 3.4, 1.6]), "adj",
            "Hồi quy logistic hiệu chỉnh đồng thời (kiểm định Wald)", align=["l", "c", "c"], fs=9.5)
    for k, cap in (("f03", "Xác suất vượt trội của từng đặc trưng số"), ("f04", "Tỷ lệ nhóm cần chú ý theo mức của đặc trưng phân loại"),
                   ("f05", "Tỷ lệ nhóm cần chú ý theo phân vị của đặc trưng số")):
        if R.fig.get(k):
            r.figure(R.fig[k], k, cap, width_in=5.9)


def sec_model(r: Report, R: Res):
    r.h1("Kết quả mô hình dự báo", key="model")
    r.p("Mọi bước tiền xử lý và chọn siêu tham số nằm trong Pipeline và chỉ fit trên phần huấn luyện của từng fold nên không rò rỉ thông tin từ fold kiểm tra.")
    rates = R.cfg["flag_rates"]
    rows = []
    for x in R.res["main"]:
        rows.append([x["model"], short(x["label"], 40), ci_txt(x["auc"], x["auc_lo"], x["auc_hi"])] +
                    [pct(x.get(f"recall_{t}", float("nan"))) for t in rates] + [vi(x.get("prauc", float("nan")), 3)])
    ncol = len(rates)
    r.table(["Mã", "Mô hình", "AUC [KTC 95%]"] + [f"Recall {pct(t, 0)}" for t in rates] + ["PR-AUC"], rows,
            widths([0.9, 3.4, 2.8] + [1.1] * ncol + [1.0]), "rank", "So sánh các mô hình (kiểm định chéo lặp, bootstrap)",
            align=["c", "l", "c"] + ["c"] * ncol + ["c"], fs=9.5)
    pr = R.tab["model_paired_delta"]
    r.table(["So sánh", "Chênh lệch AUC", "KTC 95%"], [[x["comparison"], vi(x["delta_auc"], 3), f"[{vi(x['lo'], 3)}; {vi(x['hi'], 3)}]"] for _, x in pr.iterrows()],
            widths([5, 2, 3]), "pair", "Chênh lệch AUC ghép cặp (bootstrap trên cùng mẫu lấy lại)", align=["l", "c", "c"], fs=10)
    r.p(f"Quy tắc chuyển mô hình đã đăng ký: {R.res['switch_note']}")
    if R.fig.get("f06"):
        r.figure(R.fig["f06"], "f06", "AUC và khoảng tin cậy của các phương án", width_in=5.6)
    r.h2("Năng lực gắn cờ theo ngân sách hỗ trợ")
    cap = R.tab["model_capacity_curve"]
    r.p("Cố vấn thường bị giới hạn bởi số ca có thể hỗ trợ, nên năng lực được đo theo tỷ lệ gắn cờ: tỷ lệ gắn cờ càng cao thì độ phủ càng lớn nhưng chi phí càng nhiều. "
        f"Để đạt độ phủ mục tiêu cần gắn cờ khoảng {pct(R.res['flag_rate_for_target_recall'], 0)} số sinh viên.")
    rows = [[pct(x["rate"], 0), pct(x["recall_M1"]) + f" [{pct(x['recall_M1_lo'])}; {pct(x['recall_M1_hi'])}]", pct(x["precision_M1"]), pct(x["recall_B1"]), pct(x["recall_random"])]
            for _, x in cap.iterrows()]
    r.table(["Tỷ lệ gắn cờ", "Recall mô hình [KTC]", "Precision", "Recall baseline", "Ngẫu nhiên"], rows, widths([1.6, 3.6, 1.4, 1.8, 1.6]), "cap",
            "Độ phủ theo tỷ lệ gắn cờ", align=["c"] * 5, fs=9.5)
    if R.fig.get("f07"):
        r.figure(R.fig["f07"], "f07", "Đường năng lực gắn cờ", width_in=5.6)
    r.h2("Hiệu chuẩn, ablation và rút gọn đặc trưng")
    cal = R.res["calibration"]
    r.p(f"Độ dốc hiệu chuẩn bằng {vi(cal['slope'], 2)} (lý tưởng là 1), Brier {vi(cal['brier'], 3)} so với {vi(cal['brier_base'], 3)} của dự báo theo tỷ lệ nền {r.C('steyerberg', 'vancalster')}.")
    ab = R.tab.get("model_ablation")
    if ab is None or len(ab) < 2:
        r.p("Cấu hình chưa khai báo nhóm đặc trưng (groups) nên chưa thực hiện ablation theo nhóm.")
        ab = None
    if ab is not None:
        rows = [[x["setting"], vi(x["auc"], 3), f"{vi(x['delta_auc'], 3)} [{vi(x['lo'], 3)}; {vi(x['hi'], 3)}]", pct(x[RK(R)])] for _, x in ab.iterrows()]
        r.table(["Cấu hình", "AUC", "Δ AUC [KTC 95%]", f"Recall {pct(R.cfg['criteria']['recall_rate'], 0)}"], rows, widths([4, 1.4, 3.4, 1.4]), "abl", "Ablation theo nhóm đặc trưng", align=["l", "c", "c", "c"], fs=9.5)
    if ab is not None and R.fig.get("f08"):
        r.figure(R.fig["f08"], "f08", "Mức giảm AUC khi bỏ từng nhóm đặc trưng", width_in=5.6)
    l1 = R.tab["model_l1_selection"].sort_values("selection_freq", ascending=False)
    r.p(f"Hồi quy L1 chọn trung bình {vi(R.res['items_mean'], 1)} đặc trưng; tần suất được chọn qua các fold ở bảng dưới.")
    r.table(["Đặc trưng", "Tần suất chọn"], [[short(x["feature"], 70), pct(x["selection_freq"], 0)] for _, x in l1.head(12).iterrows()], widths([7.5, 2.5]), "l1",
            "Tần suất được chọn của đặc trưng trong mô hình L1", align=["l", "c"], fs=9.5)


def sec_fair(r: Report, R: Res):
    r.h1("Công bằng thuật toán", key="fair")
    f = R.tab.get("model_fairness")
    if f is None or not len(f):
        r.p("Cấu hình chưa khai báo thuộc tính nhóm nên chưa đánh giá công bằng. Đề nghị bổ sung trước khi đưa mô hình vào vận hành.")
        return
    r.p(f"Công bằng được đánh giá theo cơ hội bình đẳng, tức so sánh recall giữa các nhóm tại cùng tỷ lệ gắn cờ {r.C('hardt', 'barocas')}. "
        f"Kết luận chỉ được đưa ra khi khoảng tin cậy của chênh lệch hẹp hơn {pct(R.cfg['criteria']['fair_ci_width'], 0)} điểm; nếu rộng hơn, kết quả được ghi là chưa kết luận {r.C('bakerhawn')}.")
    rows = []
    for _, x in f.iterrows():
        gap = "tham chiếu" if bool(x["reference"]) else f"{vi(x['gap_vs_ref'] * 100, 1)} [{vi(x['gap_lo'] * 100, 1)}; {vi(x['gap_hi'] * 100, 1)}]"
        st = "" if bool(x["reference"]) else ("Đạt" if (x["within_gap"] and x["conclusive"]) else ("Không đạt" if x["conclusive"] else "Còn mở"))
        rows.append([short(x["attribute"], 26), short(x["group"], 26), str(int(x["n"])), pct(x["recall"]), gap, st])
    r.table(["Thuộc tính", "Nhóm", "n", "Recall", "Chênh lệch điểm % [KTC]", "Kết luận"], rows, widths([2.4, 2.4, 0.8, 1.1, 2.6, 1.2]), "fair",
            "Recall theo nhóm và chênh lệch so với nhóm tham chiếu", align=["l", "l", "c", "c", "c", "c"], fs=9, status_cols=[5])
    if R.fig.get("f09"):
        r.figure(R.fig["f09"], "f09", "Recall theo nhóm với khoảng tin cậy", width_in=5.6)


def sec_verdict(r: Report, R: Res):
    r.h1("Kết luận theo tiêu chí đã đăng ký và hàm ý", key="verdict")
    vt = verdict_text(R)
    rows = [[k, CRIT_NAMES[k], R.res["criteria"][k], vt[k]] for k in ("S1", "S2", "S3", "S4", "S5")]
    r.table(["Mã", "Tiêu chí", "Kết quả", "Bằng chứng"], rows, widths([0.9, 2.6, 1.3, 5.2]), "score", "Bảng điểm theo tiêu chí đã đăng ký trước",
            align=["c", "l", "c", "l"], fs=9.5, status_cols=[2])
    r.h2("Hàm ý chính sách và thực hành")
    r.bullets(implications(R))
    r.h2("Hạn chế và mối đe dọa đến giá trị kết luận")
    r.bullets(limits(R))
    sb = R.res.get("sensitivity_B")
    if sb:
        r.h2("Đối chiếu độ nhạy với mẫu B")
        r.p(f"Khi giữ lại các dòng bị nghi giá trị thay thế (mẫu B, n = {th(sb['n'])}, {sb['positives']} ca dương), AUC của mô hình chính là {vi(sb['auc'], 3)} "
            f"so với {vi(R.model('M1')['auc'], 3)} ở mẫu chính. Mức khác biệt cho thấy mức độ nhạy của kết luận với quyết định xử lý các dòng đáng ngờ.")
    r.h2("Báo cáo theo chuẩn TRIPOD+AI")
    r.p(f"Các mục chính của TRIPOD+AI {r.C('tripodai')} đã được đáp ứng: định nghĩa nhãn và đặc trưng, xử lý dữ liệu thiếu, cỡ mẫu và EPV {r.C('riley19')}, kiểm định nội bộ, "
        "khoảng tin cậy, hiệu chuẩn và công bằng. Chưa có kiểm định ngoài nên tiêu chí này được ghi là hạn chế.")


def sec_verify(r: Report, R: Res):
    r.h1("Kiểm chứng nhất quán và khả năng tái lập", key="verify")
    rows = [[x["check"], "Đạt" if x["passed"] else "Không đạt", x.get("detail", "")] for x in R.ver["checks"]]
    r.table(["Phép kiểm tra", "Kết quả", "Ghi chú"], rows, widths([5.5, 1.3, 3.2]), "ver", "Các phép kiểm tra nhất quán tự động", align=["l", "c", "l"], fs=9.5, status_cols=[1])
    r.p(f"Toàn bộ kết quả có thể tái lập bằng cùng tệp cấu hình, hạt giống {R.cfg['cv']['seed']} và mã băm dữ liệu ở trang bìa. "
        "Phần giải thích mã nguồn và cách trợ lý hỗ trợ được trình bày ở tài liệu riêng theo yêu cầu tách mã khỏi báo cáo chính.")
    if R.xai.get("shap", "").startswith("chưa"):
        r.p("Phân tích diễn giải SHAP chưa được chạy trong môi trường này (thư viện chưa sẵn có); cần chạy trên môi trường có thư viện shap nếu cần đối chiếu tương tác phi tuyến.")


def sec_refs(r: Report, R: Res):
    r.h1("Tài liệu tham khảo", key="refs", numbered=False)
    for i, k in enumerate(r.new_reg["ref"], 1):
        r.p(f"[{i}] {REFS[k]}", align="l", size=11.5, after=4)


def build_report(R: Res):
    def build(reg, pages, path):
        r = Report(registry=reg, pages=pages)
        _CUR["r"] = r
        cover(r, R)
        toc_page(r)
        abstract(r, R)
        sec_context(r, R)
        sec_data(r, R)
        sec_design(r, R)
        sec_diag(r, R)
        sec_model(r, R)
        sec_fair(r, R)
        sec_verdict(r, R)
        sec_verify(r, R)
        sec_refs(r, R)
        r.insert_toc()
        r.save(str(path))
        return r

    K.FOOTER_TEXT = f"{R.cfg['project_name']}"
    out = R.deliver / "BaoCao_TongHop.docx"
    r, n = build_with_toc(build, str(out), workdir=str(R.deliver / "_work"))
    missing = [k for k in r.new_reg["ref"] if k not in REFS]
    print(f"[báo cáo] {out.name}: {n} trang | bảng {len(r.new_reg['tab'])} | hình {len(r.new_reg['fig'])} | tài liệu {len(r.new_reg['ref'])} | thiếu ref {missing}")
    return out


# ---------------------------------------------------------------------------------------------
# Tài liệu giải thích mã nguồn và cách trợ lý hỗ trợ (tách riêng khỏi báo cáo chính)
# ---------------------------------------------------------------------------------------------
STAGES = [
    ("init", "Khởi tạo cấu hình", "Đọc dữ liệu, gợi ý nhãn, cột nghi rò rỉ, cụm giá trị lặp; sinh tệp cấu hình nháp để người dùng xác nhận.", "config.draft.json"),
    ("profile", "Kiểm toán dữ liệu", "Phát hiện mã thiếu, cụm giá trị lặp bất thường, rò rỉ (AUC đơn biến theo fold và gợi ý tên cột), cộng tuyến, cỡ mẫu và EPV.", "audit.json, tables/audit_*.csv"),
    ("prepare", "Chuẩn bị dữ liệu", "Tạo mẫu chính và mẫu độ nhạy, ghi nhật ký biến đổi cùng SHA-256 của dữ liệu.", "data/prepared_*.csv, logs/transformation_log.csv"),
    ("prereg", "Đăng ký trước tiêu chí", "Cố định năm tiêu chí S1 đến S5, thiết kế kiểm định chéo và quy tắc chọn mô hình; băm SHA-256 trước khi mô hình hóa.", "evaluation_plan_prereg.json"),
    ("diagnose", "Chẩn đoán", "Xác suất vượt trội, Mann-Whitney, hiệu chỉnh Holm, khoảng tin cậy Wilson, hồi quy logistic Wald hiệu chỉnh.", "diagnose.json, tables/diagnose_*.csv"),
    ("model", "Mô hình hóa", "Kiểm định chéo phân tầng lặp trong Pipeline, bootstrap, ΔAUC ghép cặp, hiệu chuẩn, đường năng lực, ablation, L1, công bằng.", "results.json, tables/model_*.csv, figures/"),
    ("verify", "Kiểm chứng", "Đối chiếu mã băm, số dòng, số ca dương, AUC giữa tệp và bảng; bảo đảm không có biến rò rỉ trong đặc trưng.", "verify.json"),
]


def build_code_doc(R: Res):
    def build(reg, pages, path):
        r = Report(registry=reg, pages=pages)
        _CUR["r"] = r
        K.FOOTER_TEXT = "GIẢI THÍCH MÃ NGUỒN VÀ CÁCH TRỢ LÝ HỖ TRỢ"
        r.spacer(40)
        r.p("TÀI LIỆU GIẢI THÍCH MÃ NGUỒN", align="c", size=22, bold=True, color=K.BLUE_DARK, after=6)
        r.p("VÀ CÁCH TRỢ LÝ HỖ TRỢ TRONG DỰ ÁN", align="c", size=16, bold=True, color=K.BLUE_MID, after=6)
        r.p(R.cfg["project_name"], align="c", size=13, italic=True, after=24)
        toc_page(r)
        r.h1("Mục đích và phạm vi", key="m")
        r.p("Tài liệu này tách riêng khỏi báo cáo chính để báo cáo không chứa mã thực thi. Nội dung gồm: kiến trúc mã, giải thích từng giai đoạn, "
            "các quyết định thống kê quan trọng và minh bạch về vai trò của trợ lý trí tuệ nhân tạo trong dự án.")
        r.h1("Kiến trúc mã nguồn", key="k")
        r.p("Mã được tổ chức thành một thư viện duy nhất (dspipe.py) với một giao diện dòng lệnh và một tệp cấu hình JSON mô tả toàn bộ lựa chọn của dự án. "
            "Mỗi giai đoạn đọc kết quả của giai đoạn trước từ thư mục đầu ra, nhờ vậy có thể chạy lại riêng lẻ và kiểm tra trung gian.")
        r.table(["Giai đoạn", "Việc thực hiện", "Tệp đầu ra"], [[f"{a}: {b}", c, d] for a, b, c, d in STAGES], widths([2.4, 5, 2.6]), "stages",
                "Các giai đoạn của quy trình và tệp đầu ra", fs=9.5)
        r.h1("Giải thích các quyết định thống kê", key="q")
        for t, body in [
            ("Kiểm định chéo phân tầng lặp trong Pipeline", "Mọi bước điền khuyết, chuẩn hóa, mã hóa và chọn siêu tham số được đặt trong Pipeline và chỉ fit trên phần huấn luyện, nên không có rò rỉ dữ liệu từ bước xử lý đặc trưng sang kiểm tra " + r.C("kohavi", "cawley") + "."),
            ("Khoảng tin cậy bootstrap và ΔAUC ghép cặp", "Khoảng tin cậy lấy mẫu lại quan sát trên điểm dự báo ngoài mẫu; chênh lệch giữa hai mô hình được tính trên cùng mẫu lấy lại để tận dụng tương quan " + r.C("efron") + "."),
            ("Đăng ký trước và mã băm", "Tiêu chí được cố định và băm trước khi mô hình hóa; giai đoạn kiểm chứng đối chiếu lại mã băm để phát hiện chỉnh sửa sau khi thấy kết quả."),
            ("Phát hiện rò rỉ", "Đặc trưng bị loại tự động chỉ khi vừa có AUC đơn biến rất cao vừa có tên gợi ý hệ quả của nhãn; các đặc trưng mạnh khác chỉ bị cảnh báo để người dùng xác nhận, tránh loại nhầm tín hiệu hợp lệ " + r.C("kaufman") + "."),
            ("Công bằng", "So sánh recall giữa các nhóm tại cùng tỷ lệ gắn cờ; nếu khoảng tin cậy của chênh lệch rộng quá ngưỡng thì ghi chưa kết luận thay vì kết luận quá mức " + r.C("hardt") + ".")]:
            r.h3(t)
            r.p(body)
        r.h1("Cách trợ lý hỗ trợ và phân định trách nhiệm", key="a")
        r.p("Trợ lý đã hỗ trợ viết mã, kiểm tra nhất quán số liệu, soạn thảo văn bản học thuật và dựng sản phẩm đầu ra. Các việc sau thuộc trách nhiệm của nhóm và không được giao cho trợ lý:")
        r.bullets(["Xác nhận định nghĩa nhãn, ngưỡng và các cột nghi rò rỉ với chuyên gia nghiệp vụ.",
                   "Thu thập nhu cầu người dùng thật nếu muốn thay các giả định bằng bằng chứng phỏng vấn.",
                   "Đọc lại và chịu trách nhiệm về mọi nhận định trong báo cáo trước khi nộp.",
                   "Trích dẫn nguồn đúng chuẩn và kiểm tra các nguồn tham khảo bổ sung ngoài danh mục có sẵn."])
        r.h1("Hướng dẫn chạy lại", key="run")
        r.p("Cấu hình được lưu trong config.json. Thứ tự lệnh khuyến nghị: init, xác nhận cấu hình, all, make_report. Chế độ --fast chỉ để thử nghiệm; kết quả nộp phải chạy đầy đủ.")
        r.h1("Tài liệu tham khảo", key="refs", numbered=False)
        for i, k in enumerate(r.new_reg["ref"], 1):
            r.p(f"[{i}] {REFS[k]}", align="l", size=11.5, after=4)
        r.insert_toc()
        r.save(str(path))
        return r

    out = R.deliver / "GiaiThich_MaNguon_va_HoTro.docx"
    r, n = build_with_toc(build, str(out), workdir=str(R.deliver / "_work2"))
    print(f"[giải thích mã] {out.name}: {n} trang")
    return out


# ---------------------------------------------------------------------------------------------
# Dàn ý slide và kịch bản đọc
# ---------------------------------------------------------------------------------------------
def deck_outline(R: Res) -> list[dict]:
    a, m, c, res = R.audit, R.best, R.res["criteria"], R.res
    b1 = R.model("B1")
    n_ok = sum(str(v).startswith("Đạt") for v in c.values())
    u = R.tab["diagnose_univariate"].sort_values("p_holm")
    sig = u[u["p_holm"] < 0.05]["feature"].tolist()
    pdl = next(x for x in res["paired"] if "baseline" in x["comparison"])
    f = R.tab.get("model_fairness")
    nconc = int(f[f["reference"] == False]["conclusive"].sum()) if f is not None and len(f) else 0  # noqa: E712
    S = []

    def add(title, kicker, points, script, figure=None):
        S.append({"n": len(S) + 1, "kicker": kicker, "title": title, "points": points, "figure": figure, "script": script})

    add(f"Sàng lọc {R.pos_name}: kết quả {n_ok}/5 tiêu chí", "Mở đầu",
        [R.cfg["project_name"], f"{th(a['n_raw'])} dòng thô, mẫu chính {th(R.prep['n_primary'])}", f"Nhãn: {R.target_rule()}"],
        f"Kính chào quý thầy cô. Nhóm xin trình bày kết quả phân tích dữ liệu của dự án {R.cfg['project_name']}. Mục tiêu là xem các đặc trưng sẵn có "
        f"phân biệt được {R.pos_name} đến mức nào. Nhãn được định nghĩa là {R.target_rule()}. Kết luận ngắn gọn: trong năm tiêu chí đã đăng ký trước, có {n_ok} tiêu chí đạt.")
    add("Bối cảnh và câu hỏi", "Bối cảnh",
        [s.get("role", "") + ": " + s.get("decision", "") for s in (R.cfg.get("stakeholders") or [])[:4]] or ["Câu hỏi chung: đặc trưng nào phân biệt nhóm cần chú ý, và có đủ để sàng lọc không"],
        "Phần này nêu những ai cần kết quả và họ cần ra quyết định gì. " + ("Các nhu cầu này là giả định của nhóm, chưa qua phỏng vấn người dùng thật." if R.cfg.get("stakeholders_source", "assumed") == "assumed" else "Các nhu cầu này đến từ phỏng vấn thực tế."))
    top = R.tab["audit_issues"].head(4)
    add("Chất lượng dữ liệu quyết định kết quả", "Dữ liệu", [f"{x['id']}: {short(x['description'], 90)}" for _, x in top.iterrows()],
        f"Trước khi mô hình hóa, nhóm kiểm toán dữ liệu và phát hiện {len(R.tab['audit_issues'])} vấn đề. Quan trọng nhất là các vấn đề mức cao được xử lý và ghi nhật ký, "
        f"đồng thời giữ mẫu độ nhạy B để kiểm tra mức nhạy của kết luận.", R.fig.get("f01"))
    add("Đăng ký trước: tiêu chí cố định từ đầu", "Phương pháp",
        [f"{k}: {CRIT_NAMES[k]}" for k in CRIT_NAMES] + [f"SHA-256 kế hoạch: {res['prereg_sha256'][:12]}..."],
        "Nhóm cố định năm tiêu chí và băm kế hoạch trước khi huấn luyện. Điều này giúp tránh chỉnh tiêu chí sau khi đã thấy kết quả, và giai đoạn kiểm chứng đối chiếu lại mã băm.")
    add("Những đặc trưng thật sự phân biệt hai nhóm", "Chẩn đoán",
        [f"{len(sig)} trên {len(u)} đặc trưng có p Holm dưới 0,05"] + [short(x, 60) for x in sig[:4]],
        f"Sau hiệu chỉnh Holm, có {len(sig)} trên {len(u)} đặc trưng phân biệt được hai nhóm. Đây là liên hệ thống kê, không phải nhân quả.", R.fig.get("f05") or R.fig.get("f03"))
    add("Mô hình phức tạp có hơn baseline đơn giản không", "Mô hình",
        [f"{m['label']}: AUC {vi(m['auc'], 3)} [{vi(m['auc_lo'], 3)}; {vi(m['auc_hi'], 3)}]", f"Baseline: AUC {vi(b1['auc'], 3)}", f"Δ AUC {vi(pdl['delta_auc'], 3)} [{vi(pdl['lo'], 3)}; {vi(pdl['hi'], 3)}]"],
        f"Mô hình được giữ là {m['label']} với AUC {vi(m['auc'], 3)}. Baseline một đặc trưng đạt {vi(b1['auc'], 3)}. Chênh lệch ghép cặp là {vi(pdl['delta_auc'], 3)} với khoảng tin cậy từ {vi(pdl['lo'], 3)} đến {vi(pdl['hi'], 3)}.", R.fig.get("f06"))
    add("Năng lực gắn cờ theo ngân sách hỗ trợ", "Mô hình",
        [f"Recall tại {pct(R.cfg['criteria']['recall_rate'], 0)}: {pct(m.get(RK(R), float('nan')))}", f"Muốn đạt độ phủ mục tiêu cần gắn cờ khoảng {pct(res['flag_rate_for_target_recall'], 0)}"],
        "Cố vấn bị giới hạn bởi số ca có thể hỗ trợ, nên nhóm đo độ phủ theo tỷ lệ gắn cờ thay vì chỉ nhìn AUC.", R.fig.get("f07"))
    cal = res["calibration"]
    add("Hiệu chuẩn và nhóm đặc trưng quan trọng", "Mô hình", [f"Độ dốc hiệu chuẩn {vi(cal['slope'], 2)}", f"Brier {vi(cal['brier'], 3)} so với {vi(cal['brier_base'], 3)}"],
        "Độ dốc hiệu chuẩn gần 1 cho thấy xác suất dự báo không bị thổi phồng. Ablation cho biết nhóm đặc trưng nào đóng góp nhiều nhất.", R.fig.get("f08"))
    add("Công bằng giữa các nhóm", "Công bằng", [f"{nconc} so sánh đủ chắc chắn để kết luận", f"Kết quả S5: {c['S5']}"],
        "Nhóm so sánh recall giữa các nhóm. Khi khoảng tin cậy quá rộng, nhóm ghi chưa kết luận thay vì kết luận quá mức.", R.fig.get("f09"))
    add("Bảng điểm năm tiêu chí", "Kết luận", [f"{k}: {c[k]}" for k in c],
        "Đây là bảng điểm theo đúng tiêu chí đã đăng ký trước. " + " ".join(f"{k} {c[k].lower()}." for k in c))
    add("Hàm ý và hạn chế", "Kết luận", implications(R)[:2] + [re.sub(r"\s*\[[\d, ]+\]", "", limits(R)[-1])[:120]],
        "Hàm ý thực hành: " + " ".join(implications(R)[:2]) + " Về hạn chế, dữ liệu cắt ngang nên không kết luận nhân quả.")
    add("Bước tiếp theo", "Kết thúc", ["Xác nhận ngưỡng nhãn với chuyên gia nghiệp vụ", "Thu thập dữ liệu dọc và kiểm định ngoài", "Thử nghiệm thí điểm có nhóm đối chứng"],
        "Bước tiếp theo là xác nhận ngưỡng nhãn, bổ sung dữ liệu dọc và kiểm định ngoài, rồi thí điểm có đối chứng. Xin cảm ơn quý thầy cô đã lắng nghe.")
    for s in S:
        s["script"] = s["script"].replace("—", ",").replace("–", "-")
    return S


def build_deck_files(R: Res):
    _CUR["r"] = Report()
    S = deck_outline(R)
    (R.deliver / "deck_outline.json").write_text(json.dumps(S, ensure_ascii=False, indent=2), encoding="utf-8")

    def build(reg, pages, path):
        r = Report(registry=reg, pages=pages)
        _CUR["r"] = r
        K.FOOTER_TEXT = "KỊCH BẢN THUYẾT TRÌNH"
        r.spacer(40)
        r.p("KỊCH BẢN THUYẾT TRÌNH", align="c", size=22, bold=True, color=K.BLUE_DARK, after=6)
        r.p(R.cfg["project_name"], align="c", size=14, italic=True, after=24)
        toc_page(r)
        r.h1("Kịch bản đọc từng slide", key="ks")
        for s in S:
            r.h2(f"Slide {s['n']}. {s['title']}")
            r.p(s["script"])
        r.insert_toc()
        r.save(str(path))
        return r

    out = R.deliver / "KichBan_ThuyetTrinh.docx"
    r, n = build_with_toc(build, str(out), workdir=str(R.deliver / "_work3"))
    print(f"[kịch bản] {out.name}: {n} trang | {len(S)} slide | dàn ý: deck_outline.json")
    return out


def scan_long_dashes(paths):
    from docx import Document
    bad = []
    for p in paths:
        d = Document(str(p))
        txt = "\n".join(x.text for x in d.paragraphs) + "\n".join(c.text for t in d.tables for row in t.rows for c in row.cells)
        if "—" in txt or "–" in txt:
            bad.append(str(p))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--only", choices=["report", "code", "deck"], default=None)
    a = ap.parse_args(argv)
    R = Res(a.config)
    outs = []
    if a.only in (None, "report"):
        outs.append(build_report(R))
    if a.only in (None, "code"):
        outs.append(build_code_doc(R))
    if a.only in (None, "deck"):
        outs.append(build_deck_files(R))
    bad = scan_long_dashes(outs)
    print("Dấu gạch ngang dài còn sót:", bad or "không")
    for p in R.deliver.glob("_work*"):
        import shutil
        shutil.rmtree(p, ignore_errors=True)


if __name__ == "__main__":
    main()
