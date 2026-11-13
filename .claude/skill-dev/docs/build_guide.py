"""Sinh file hướng dẫn bộ skill của nhóm N02 (N02_HuongDan_Skill.docx và .md).

Khuôn: docs/_template_guide.docx (bản hướng dẫn trước, đúng mẫu báo cáo của nhóm: Times New Roman, cỡ chữ ≥ 13).
Script giữ trang bìa, trang 2 (chỉ bảng thành viên và bảng phân công) và trang mục lục, rồi viết lại phần thân
bằng cách nhân bản các đoạn/bảng mẫu có sẵn trong khuôn để giữ nguyên định dạng. Mục lục được Word tự cập nhật
khi mở file (cờ updateFields).

Số liệu đọc trực tiếp từ:
  testing/results/test_summary.md, testing/results/<bộ>/output/results.json   (student-risk-screening)
  testing/capstone/test_summary.json, testing/capstone/<bộ>/outputs/*           (analytics-capstone-pipeline)
  evaluation/iteration-1/benchmark.json                                         (đánh giá có/không có skill)
  packaging/dist/checksums.txt

Chạy:  python .claude/skill-dev/docs/build_guide.py
"""
import copy
import json
import re
import zipfile
from pathlib import Path

import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
DEV = HERE.parent
TEMPLATE = HERE / "_template_guide.docx"
OUT_DOCX = HERE / "N02_HuongDan_Skill.docx"
OUT_MD = HERE / "N02_HuongDan_Skill.md"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8").replace("NaN", "null"))


def vn(x, d=1):
    return f"{x * 100:.{d}f}%".replace(".", ",")


# ------------------------------------------------------------------ dữ liệu
CAP = jload(DEV / "testing/capstone/test_summary.json")
CAP_R = {k: jload(DEV / f"testing/capstone/{k}/outputs/results.json") for k in CAP}
OLD = {k: jload(DEV / f"testing/results/{k}/output/results.json") for k in ("sape", "uci_student_por", "uci_dropout")}
OLD_SUM = (DEV / "testing/results/test_summary.md").read_text(encoding="utf-8")
N_PASS = re.search(r"\*\*(\d+)/(\d+) kiểm tra đạt", OLD_SUM).groups()
BENCH = jload(DEV / "evaluation/iteration-1/benchmark.json")
RS = BENCH["run_summary"]
SUMS = (DEV / "packaging/dist/checksums.txt").read_text(encoding="utf-8").split()
NAMES = {"sape": "SAPE", "uci_student_por": "UCI Student Performance", "uci_dropout": "UCI Dropout"}
TIMES = {"sape": 74, "uci_student_por": 61, "uci_dropout": 190}
DELIV = DEV / "testing/capstone/sape/outputs/deliverables"


def old_row(k):
    s = re.search(rf"^\| {k} \| .*$", OLD_SUM, re.M).group(0).split("|")[1:-1]
    return [x.strip() for x in s]


# ------------------------------------------------------------------ khuôn
doc = docx.Document(str(TEMPLATE))
body = doc.element.body
kids = list(body)


def text(el):
    return "".join(el.itertext())


h1_p = next(k for k in kids if k.tag == W + "p" and k.find(f".//{W}pStyle") is not None and k.find(f".//{W}pStyle").get(qn("w:val")) == "Heading1")
h2_p = next(k for k in kids if k.tag == W + "p" and k.find(f".//{W}pStyle") is not None and k.find(f".//{W}pStyle").get(qn("w:val")) == "Heading2")
body_p = kids[kids.index(h1_p) + 1]
cap_p = next(k for k in kids if k.tag == W + "p" and text(k).startswith("Bảng 1."))
bul_p = next(k for k in kids if k.tag == W + "p" and k.find(f".//{W}numPr") is not None and k.find(f".//{W}pStyle") is None)
tbl_p = next(k for k in kids[kids.index(h1_p):] if k.tag == W + "tbl")
code_p = next(k for k in kids if k.tag == W + "tbl" and text(k).lstrip().startswith("# giải nén"))
P = {n: copy.deepcopy(e) for n, e in [("h1", h1_p), ("h2", h2_p), ("p", body_p), ("cap", cap_p), ("bul", bul_p), ("tbl", tbl_p), ("code", code_p)]}

# trang 2: bỏ bảng "Thông tin nhóm" (chỉ giữ bảng thành viên và bảng phân công) và một đoạn trống đi kèm
info = next(k for k in kids if k.tag == W + "tbl" and text(k).startswith("Thông tin nhóm"))
prev = info.getprevious()
body.remove(info)
if prev is not None and prev.tag == W + "p" and not text(prev).strip():
    body.remove(prev)
assign = next(k for k in body if k.tag == W + "tbl" and text(k).startswith("Phân công"))

# xóa toàn bộ phần thân cũ (từ tiêu đề cấp 1 đầu tiên đến trước sectPr)
kids = list(body)
start = kids.index(h1_p)
sect = kids[-1]
for k in kids[start:-1]:
    body.remove(k)


def set_par_text(p, s, bold_prefix=None):
    """Giữ pPr và định dạng run đầu, thay nội dung bằng s (tùy chọn: phần đầu in đậm)."""
    ppr = p.find(W + "pPr")
    runs = p.findall(f".//{W}r")
    rpr = runs[0].find(W + "rPr") if runs else None
    for ch in list(p):
        if ch is not ppr:
            p.remove(ch)

    def run(t, bold=False):
        r = parse_xml(f'<w:r xmlns:w="{W[1:-1]}"/>')
        if rpr is not None:
            rp = copy.deepcopy(rpr)
            for b in rp.findall(W + "b") + rp.findall(W + "bCs"):
                rp.remove(b)
            if bold:
                rp.insert(0, parse_xml(f'<w:b xmlns:w="{W[1:-1]}"/>'))
            r.append(rp)
        te = parse_xml(f'<w:t xmlns:w="{W[1:-1]}" xml:space="preserve"/>')
        te.text = t
        r.append(te)
        p.append(r)

    if bold_prefix:
        run(bold_prefix, True)
    run(s)
    return p


def add(el):
    sect.addprevious(el)
    return el


MD = []
TN = [0]


def h1(s):
    add(set_par_text(copy.deepcopy(P["h1"]), s)); MD.extend(["", f"## {s}", ""])


def h2(s):
    add(set_par_text(copy.deepcopy(P["h2"]), s)); MD.extend(["", f"### {s}", ""])


def para(s, bold_prefix=None):
    add(set_par_text(copy.deepcopy(P["p"]), s, bold_prefix)); MD.extend([(f"**{bold_prefix}**" if bold_prefix else "") + s, ""])


def bullets(items):
    for it in items:
        if isinstance(it, tuple):
            add(set_par_text(copy.deepcopy(P["bul"]), it[1], it[0])); MD.append(f"- **{it[0]}**{it[1]}")
        else:
            add(set_par_text(copy.deepcopy(P["bul"]), it)); MD.append(f"- {it}")
    MD.append("")


def code(lines):
    t = copy.deepcopy(P["code"])
    tc = t.find(f".//{W}tc")
    paras = tc.findall(W + "p")
    proto = paras[0]
    for p in paras:
        tc.remove(p)
    for ln in lines:
        tc.append(set_par_text(copy.deepcopy(proto), ln if ln else " "))
    add(t)
    add(parse_xml(f'<w:p xmlns:w="{W[1:-1]}"/>'))
    MD.extend(["```"] + lines + ["```", ""])


def table(header, rows, widths, caption):
    """Dựng bảng bằng cách nhân bản ô tiêu đề và ô thân của bảng mẫu (giữ viền, nền, font)."""
    t = copy.deepcopy(P["tbl"])
    trs = t.findall(W + "tr")
    tr_h, tr_b = trs[0], trs[1]
    tc_h, tc_b = tr_h.findall(W + "tc")[0], tr_b.findall(W + "tc")[-1]
    for tr in trs:
        t.remove(tr)
    total = sum(int(g.get(qn("w:w"))) for g in t.find(W + "tblGrid").findall(W + "gridCol"))
    ws = [int(w * total / sum(widths)) for w in widths]
    grid = t.find(W + "tblGrid")
    for g in list(grid):
        grid.remove(g)
    for w in ws:
        grid.append(parse_xml(f'<w:gridCol xmlns:w="{W[1:-1]}" w:w="{w}"/>'))

    def mkrow(proto_tr, proto_tc, vals):
        tr = copy.deepcopy(proto_tr)
        for tc in tr.findall(W + "tc"):
            tr.remove(tc)
        for v, w in zip(vals, ws):
            tc = copy.deepcopy(proto_tc)
            tcw = tc.find(f"{W}tcPr/{W}tcW")
            if tcw is not None:
                tcw.set(qn("w:w"), str(w)); tcw.set(qn("w:type"), "dxa")
            ps = tc.findall(W + "p")
            for p in ps[1:]:
                tc.remove(p)
            set_par_text(ps[0], str(v))
            tr.append(tc)
        return tr

    t.append(mkrow(tr_h, tc_h, header))
    for r in rows:
        t.append(mkrow(tr_b, tc_b, r))
    add(t)
    TN[0] += 1
    add(set_par_text(copy.deepcopy(P["cap"]), f"Bảng {TN[0]}. {caption}"))
    MD.extend(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows] +
              ["", f"*Bảng {TN[0]}. {caption}*", ""])


# ------------------------------------------------------------------ trang bìa: nêu cả hai skill
n_cover = 0
for t in body.iter(W + "t"):
    if t.text and "STUDENT-RISK-SCREENING (PLUGIN EDU-ANALYTICS)" in t.text:
        t.text = t.text.replace("STUDENT-RISK-SCREENING (PLUGIN EDU-ANALYTICS)", "STUDENT-RISK-SCREENING VÀ ANALYTICS-CAPSTONE-PIPELINE (PLUGIN EDU-ANALYTICS)")
        n_cover += 1
assert n_cover, "không tìm thấy dòng phụ đề trên trang bìa"

# ------------------------------------------------------------------ bảng phân công: bổ sung phần việc mới
last = assign.findall(W + "tr")[-1]
new = copy.deepcopy(last)
cells = new.findall(W + "tc")
set_par_text(cells[0].find(W + "p"), "Tích hợp skill analytics-capstone-pipeline vào plugin, chạy test trên 3 bộ dữ liệu, cập nhật hướng dẫn")
set_par_text(cells[-1].find(W + "p"), "Cả nhóm")
assign.append(new)

# ------------------------------------------------------------------ nội dung
MD.extend(["# Hướng dẫn bộ skill của nhóm N02", "",
           "Plugin `edu-analytics` phiên bản 1.2.0 (marketplace `n02-skills`), gồm 2 skill. Nền tảng: Claude Code và claude.ai."])
h1("GIỚI THIỆU BỘ SKILL")
para("Bộ skill đóng gói quy trình phân tích của đồ án thành công cụ dùng lại được trên Claude. Plugin edu-analytics (phiên bản 1.2.0, "
     "marketplace n02-skills) gồm hai skill bổ sung cho nhau: một skill chuyên về sàng lọc người học cần hỗ trợ có trách nhiệm, một skill "
     "chạy trọn quy trình đồ án từ dữ liệu đến báo cáo Word và dàn ý slide.")
table(["Skill", "Mục đích", "Đầu ra chính", "Nên dùng khi"], [
    ["student-risk-screening", "Sàng lọc người học cần hỗ trợ từ dữ liệu điểm, LMS, khảo sát; kiểm soát rò rỉ, baseline, công bằng, đánh đổi ngưỡng",
     "Báo cáo Markdown có số liệu, 4 biểu đồ, cấu hình đã rà soát", "Cần một phân tích sàng lọc chặt chẽ, có tập kiểm tra độc lập"],
    ["analytics-capstone-pipeline", "Chạy trọn quy trình đồ án khoa học dữ liệu trên bảng dữ liệu bất kỳ có biến mục tiêu, có đăng ký trước tiêu chí",
     "Báo cáo Word có mục lục và trích dẫn, tài liệu giải thích mã, kịch bản thuyết trình, dàn ý slide, 9 hình", "Cần sản phẩm đồ án trọn gói theo milestone 1-5"],
], [2200, 3200, 2500, 2100], "Hai skill trong plugin edu-analytics")

h1("BỘ SKILL CÓ THỂ LÀM ĐƯỢC GÌ?")
h2("Skill student-risk-screening")
table(["Thành phần", "Chức năng"], [
    ["profile", "Đọc CSV/XLSX, tính SHA-256, mô tả schema; gắn cờ cột số lẫn chuỗi, giá trị dồn đống nghi điền khuyết, số 0 ở cột điểm; sàng lọc biến rò rỉ và thuộc tính nhạy cảm; sinh cấu hình gợi ý"],
    ["prepare", "Làm sạch theo cấu hình, tạo nhãn, loại nhãn không quan sát được, khóa giả danh, chia train/test phân tầng; ghi validation và transformation log"],
    ["analyze", "Chẩn đoán trên train (kiểm định có hiệu chỉnh Holm, logit điều chỉnh); baseline; LR và RF trong Pipeline với quy tắc chọn đặt trước; CV lặp; test một lần kèm bootstrap CI; rút gọn tín hiệu; công bằng; đánh đổi ngưỡng; độ nhạy"],
    ["report", "Báo cáo Markdown có số liệu và phần giới hạn, governance"],
    ["run", "Chạy liền prepare, analyze, report với một cấu hình đã rà soát"],
    ["SKILL.md", "Quy trình 6 bước cho Claude: làm rõ quyết định và mốc dự báo, profile, chốt vai trò biến bằng lập luận domain, chạy, diễn giải có trách nhiệm, bàn giao theo milestone"],
], [1800, 8200], "Chức năng của student-risk-screening")
h2("Skill analytics-capstone-pipeline")
table(["Bước", "Nội dung", "Lệnh / tệp"], [
    ["1. Khởi tạo cấu hình", "Đọc dữ liệu, đếm dòng hợp lệ và tỷ lệ ca dương, gợi ý cột rò rỉ và vấn đề chất lượng", "dspipe.py init"],
    ["2. Xác nhận cấu hình", "Con người chốt đặc trưng, nhóm đặc trưng, cột công bằng, baseline, cột rò rỉ, tiêu chí thành công", "config.json"],
    ["3. Chạy thử nhanh", "Phát hiện lỗi cấu hình trong vài chục giây; số liệu không dùng để báo cáo", "dspipe.py all --fast"],
    ["4. Chạy đầy đủ", "Kiểm toán, chuẩn bị, đăng ký trước tiêu chí S1-S5 (băm SHA-256), chẩn đoán, mô hình (LR L2, LR L1, Random Forest, Gradient Boosting) kiểm định chéo 5×10, bootstrap 2.000 lần, hiệu chuẩn, rút gọn, ablation, công bằng, mẫu độ nhạy, 13 phép kiểm chứng", "dspipe.py all"],
    ["5. Đọc kết quả", "results.json, audit.json, bảng trong tables/, 9 hình trong figures/", "references/methodology.md"],
    ["6. Dựng sản phẩm", "Báo cáo Word (không chứa mã, có mục lục, trích dẫn đánh số), tài liệu giải thích mã, kịch bản thuyết trình, dàn ý slide", "make_report.py"],
    ["7. Kiểm tra sản phẩm", "Số trang mục lục, không có mã trong báo cáo, không có dấu gạch ngang dài, số liệu khớp bảng, trích dẫn khớp danh mục", "make_report.py tự quét"],
    ["8. Giao kết quả", "Nêu số tiêu chí đạt, mô hình giữ lại, giả định và hạn chế", "SKILL.md"],
    ["Mở rộng", "SEM/CFA (semopy), SHAP và LIME cho mô hình cây, so sánh công cụ trực quan hóa, sổ tay Colab tự chứa", "scripts/extensions/, build_notebook.py"],
], [2000, 5600, 2400], "Quy trình tám bước của analytics-capstone-pipeline")

h1("MỨC ĐỘ")
table(["Khía cạnh", "student-risk-screening", "analytics-capstone-pipeline"], [
    ["Theo Đề cương", "Mức 3 - Predictive / Explanatory (bao gồm Mức 1-2)", "Mức 3 - Predictive / Explanatory, thêm sản phẩm trình bày (báo cáo, slide) phục vụ Giai đoạn 9-10"],
    ["Mức tự động hóa", "Bán tự động: vai trò biến, ngưỡng nhãn, mốc dự báo do người phân tích chốt", "Bán tự động: bước 2 (xác nhận cấu hình) bắt buộc có con người; các bước còn lại tự động"],
    ["Thiết kế đánh giá", "Tập kiểm tra độc lập dùng một lần + CV lặp trên train", "Kiểm định chéo lặp 5×10 trên toàn mẫu + đăng ký trước tiêu chí có mã băm"],
    ["Không thuộc phạm vi", "KG/RAG/Agent, suy luận nhân quả, tự liên hệ người học", "Như bên trái; phần mở rộng SEM/SHAP chỉ chạy khi có thư viện và được yêu cầu"],
    ["Yêu cầu kỹ thuật", "Python 3.9+ (đã kiểm thử 3.12), pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib, openpyxl", "Như bên trái + python-docx; LibreOffice để điền số trang mục lục (tùy chọn)"],
], [2000, 4000, 4000], "Mức độ của hai skill")

h1("ĐÃ CHẠY TEST TRÊN BỘ DỮ LIỆU NÀO?")
para("Cả hai skill được chạy trên cùng ba bộ dữ liệu mở, khác nhau về bậc học, quy mô, định dạng và kiểu nhãn, với cùng lựa chọn đặc trưng, "
     "biến loại trừ và cột công bằng để kết quả so sánh được.")
table(["Bộ dữ liệu", "Nguồn / giấy phép", "Quy mô", "Bài toán"], [
    ["SAPE - Students_Academic_Performance_Evaluation_Dataset", "Mendeley Data, DOI 10.17632/dc3797vf3t.1, CC BY 4.0", "1.194 sinh viên CSE (Bangladesh), 31 biến", "CGPA < 2,75 (sàng lọc đồng thời)"],
    ["UCI Student Performance (môn tiếng Bồ Đào Nha)", "UCI ML Repository, DOI 10.24432/C5TG7T, CC BY 4.0", "649 học sinh THPT, 33 biến", "G3 < 10 (trượt môn), mốc đầu năm học"],
    ["UCI Predict Students' Dropout and Academic Success", "UCI ML Repository, DOI 10.24432/C5MC89, CC BY 4.0", "4.424 sinh viên đại học (Bồ Đào Nha), 37 biến", "Target = Dropout, mốc cuối học kỳ 1"],
], [2700, 2700, 2300, 2300], "Ba bộ dữ liệu dùng để test")

h1("KẾT QUẢ")
h2("Kết quả của student-risk-screening")
rows = []
for k in ("sape", "uci_student_por", "uci_dropout"):
    r = old_row(k)
    rows.append([NAMES[k], r[1], r[2], r[4], r[5], r[6]])
table(["Bộ dữ liệu", "Dòng (có nhãn)", "Ca dương", "AUC CV (baseline)", "AUC test [CI]", "Recall test @30%"], rows,
      [1800, 1300, 1300, 2300, 1900, 1400], "Hiệu năng của student-risk-screening (LR là mô hình chính ở cả ba bộ)")
bullets([("Bộ test tự động: ", f"{N_PASS[0]}/{N_PASS[1]} kiểm tra đạt (testing/run_tests.py)."),
         ("Đánh giá có/không có skill (skill-creator): ", f"pass rate {vn(RS['with_skill']['pass_rate']['mean'], 0)} so với {vn(RS['without_skill']['pass_rate']['mean'], 0)}; "
          "chạy trên phiên bản 1.0.0, mỗi cấu hình một lần.")])
h2("Kết quả của analytics-capstone-pipeline")
rows = []
for k, s in CAP.items():
    c = s["crit"]
    m1 = s["m1"]
    rec = next(m for m in CAP_R[k]["main"] if m["model"] == CAP_R[k]["recommended_model"])["label"]
    passed = sum(1 for v in c.values() if v.startswith("Đạt"))
    rows.append([NAMES[k], f"{s['n']:,} / {s['pos']:,} ({vn(s['prev'])})".replace(",", "."), f"{m1[0]:.3f} [{m1[1]:.3f}; {m1[2]:.3f}]".replace(".", ","),
                 f"{s['b1']:.3f}".replace(".", ","), vn(s["rec30"]), f"{passed}/5", rec, f"{s['ver']}"])
table(["Bộ dữ liệu", "Mẫu / ca dương", "AUC LR [KTC 95%]", "AUC baseline", "Recall @30%", "Tiêu chí đạt", "Mô hình giữ", "Kiểm chứng"], rows,
      [1500, 1500, 1700, 1000, 1000, 900, 1400, 1000], "Hiệu năng của analytics-capstone-pipeline (kiểm định chéo 5×10, seed 42)")
crit_rows = [[NAMES[k], s["crit"]["S1"], s["crit"]["S2"], s["crit"]["S3"], s["crit"]["S4"], s["crit"]["S5"]] for k, s in CAP.items()]
table(["Bộ dữ liệu", "S1 hiệu năng", "S2 hơn baseline", "S3 rút gọn", "S4 hiệu chuẩn", "S5 công bằng"], crit_rows,
      [1900, 1700, 1600, 1500, 1600, 1700], "Kết quả từng tiêu chí đăng ký trước")
dl = {p.name: p for p in DELIV.iterdir()} if DELIV.exists() else {}
rep = docx.Document(str(dl["BaoCao_TongHop.docx"])) if "BaoCao_TongHop.docx" in dl else None
bullets([
    ("Thời gian chạy đầy đủ: ", f"{TIMES['sape']} giây (SAPE), {TIMES['uci_student_por']} giây (UCI Student Performance), {TIMES['uci_dropout']} giây (UCI Dropout) trên máy Windows 11."),
    ("Kiểm chứng tự động: ", "cả ba bộ qua đủ 13/13 phép kiểm chứng (mã băm, tính nhất quán, chế độ chạy đầy đủ)."),
    ("Rò rỉ tự phát hiện: ", "trên SAPE, skill tự loại cột điểm SGPA kỳ trước (vừa có tên gợi ý hệ quả của nhãn, vừa có AUC đơn biến rất cao), đúng kết luận của đồ án."),
    ("Dựng sản phẩm (SAPE): ", f"make_report.py sinh đủ 4 tệp trong 5 giây: báo cáo tổng hợp ({len(rep.tables) if rep else '?'} bảng, 8 hình, 25 tài liệu tham khảo, không thiếu trích dẫn), "
     "tài liệu giải thích mã, kịch bản thuyết trình 12 slide, dàn ý slide (JSON); không còn dấu gạch ngang dài."),
    ("Tái lập đồ án: ", f"trên SAPE, AUC LR {CAP['sape']['m1'][0]:.3f} và Random Forest 0,635, gần với notebook Milestone 4 của nhóm (0,621 và 0,638; khác 1 đặc trưng mã hóa); cùng kết luận 2/5 tiêu chí đạt."),
])
h2("So sánh hai skill trên cùng dữ liệu")
cmp_rows = []
for k in ("sape", "uci_student_por", "uci_dropout"):
    r = old_row(k)
    cmp_rows.append([NAMES[k], r[4].split(" (")[0], r[5].split(" [")[0], f"{CAP[k]['m1'][0]:.3f}".replace(".", ","), "Không đạt" if k == "sape" else "Đạt"])
table(["Bộ dữ liệu", "student-risk-screening: AUC CV", "student-risk-screening: AUC test", "analytics-capstone-pipeline: AUC CV", "Kết luận chung về tiêu chí hiệu năng"], cmp_rows,
      [1900, 2000, 2000, 2100, 2000], "Hai skill cho kết luận giống nhau trên cùng dữ liệu")
para("Hai skill dùng hai thiết kế đánh giá khác nhau (tập kiểm tra độc lập so với kiểm định chéo lặp trên toàn mẫu) nhưng cho AUC gần nhau "
     "và cùng kết luận: phiếu khảo sát SAPE không đạt tiêu chí hiệu năng, hai bộ UCI đạt. Sự nhất quán này là bằng chứng các con số không phụ thuộc vào một cách triển khai.")

h1("NHẬN XÉT CHUNG")
h2("student-risk-screening")
para("", "Mặt được")
bullets([
    "Tổng quát: chạy trên 3 bộ dữ liệu khác nhau về bậc học, kích thước (649-4.424 dòng), định dạng (xlsx, csv dấu ';'), kiểu nhãn chỉ bằng file cấu hình.",
    "Tái lập đúng kết luận phủ định của đồ án trên SAPE; tự phát hiện 140 nhãn nghi điền khuyết, biến rò rỉ, biến nhạy cảm.",
    "Kỷ luật đánh giá: baseline bắt buộc, chia dữ liệu trước khi fit, test một lần, CI bootstrap, quy tắc chọn mô hình và tiêu chí thành công đặt trước.",
    "Governance tích hợp: biến nhạy cảm bị loại khỏi mô hình nhưng giữ lại để kiểm định; phát hiện chênh lệch công bằng theo tuổi ở bộ Dropout.",
    f"Đánh giá có/không có skill: pass rate {vn(RS['with_skill']['pass_rate']['mean'], 0)} so với {vn(RS['without_skill']['pass_rate']['mean'], 0)}.",
])
para("", "Chưa được")
bullets([
    "Không làm mô hình mạnh hơn; giá trị nằm ở quy trình, không ở độ chính xác.",
    "Gợi ý vai trò biến dựa trên từ khóa và thống kê, vẫn cần người rà soát (ví dụ bộ Dropout).",
    "Chỉ hỗ trợ dữ liệu một bảng; chưa có chia theo thời gian hoặc theo nhóm; báo cáo chỉ ở dạng Markdown.",
    "Chưa hiệu chỉnh xác suất và chưa có giải thích cấp cá nhân tự động; tốn token và thời gian hơn khi không dùng skill.",
])
h2("analytics-capstone-pipeline")
para("", "Mặt được")
bullets([
    "Chạy được trên cả 3 bộ dữ liệu chỉ bằng file cấu hình, qua đủ 13/13 phép kiểm chứng ở mỗi bộ.",
    "Đăng ký trước tiêu chí S1-S5 có mã băm SHA-256; so sánh 4 mô hình bằng KTC ghép cặp; chỉ đổi mô hình khi hơn rõ (UCI Student Performance chuyển sang Random Forest đúng quy tắc).",
    "Trung thực với kết quả: SAPE chỉ đạt 2/5 tiêu chí và công bằng được ghi 'chưa kết luận' khi khoảng tin cậy rộng, thay vì kết luận quá mức.",
    "Tự phát hiện cột rò rỉ SGPA trên SAPE; có mẫu độ nhạy giữ cụm giá trị lặp nghi điền khuyết.",
    "Sinh đủ sản phẩm trình bày (báo cáo Word có mục lục và trích dẫn, tài liệu giải thích mã, kịch bản, dàn ý slide) trong vài giây, số liệu lấy trực tiếp từ kết quả.",
])
para("", "Chưa được")
bullets([
    "Trên Windows, bản gốc lỗi bảng mã khi in tiếng Việt (cp1252) ở bước cuối; nhóm đã sửa trong cả 3 script bằng cách buộc đầu ra UTF-8.",
    "Không có LibreOffice thì mục lục của báo cáo sinh ra chưa có số trang (cần mở bằng Word và cập nhật mục lục).",
    "Bảng và chú thích trong báo cáo sinh ra dùng cỡ chữ 9-12,5, thấp hơn mức 13 nhóm áp dụng cho báo cáo milestone.",
    "Mô tả gốc dài 704 ký tự, vượt giới hạn khuyến nghị của claude.ai; nhóm đã rút còn 176 ký tự và chuyển các câu kích hoạt xuống thân SKILL.md.",
    "Chưa có bộ test tự động (evals) và chưa chạy vòng đánh giá có/không có skill; phần mở rộng SHAP, LIME, SEM chưa chạy thử vì máy chưa cài shap, lime, semopy.",
    "Báo cáo sinh ra là khung chung; phần bối cảnh, bên liên quan và câu hỏi phân tích vẫn cần nhóm viết trong file cấu hình.",
])

h1("CÀI ĐẶT VÀ SỬ DỤNG")
h2("Claude Code - theo dự án")
para("Hai thư mục .claude/skills/student-risk-screening/ và .claude/skills/analytics-capstone-pipeline/ được Claude Code tự nạp khi mở dự án. "
     "Muốn dùng ở mọi dự án, chép hai thư mục này vào ~/.claude/skills/.")
h2("Claude Code - plugin")
code(["# giải nén n02-skills-marketplace.zip, rồi gõ trong ô chat của Claude Code:", "/plugin marketplace add ./n02-skills-marketplace",
      "/plugin install edu-analytics@n02-skills"])
h2("claude.ai")
para("Bật Code execution trong Settings > Capabilities; vào Customize > Skills, tải lên student-risk-screening.zip và analytics-capstone-pipeline.zip "
     "(mỗi gói có thư mục skill ở cấp cao nhất).")
h2("Chạy trực tiếp công cụ")
code(["python scripts/risk_screening.py profile students.xlsx --target CGPA --out work      # student-risk-screening",
      "python scripts/risk_screening.py run --config work/config.json",
      "python scripts/dspipe.py init --data data.xlsx --target CGPA --threshold 2.75 --positive-if \"<\" --out config.json   # analytics-capstone-pipeline",
      "python scripts/dspipe.py all --config config.json",
      "python scripts/make_report.py --config config.json"])

h1("CẤU TRÚC MÃ NGUỒN VÀ ĐÓNG GÓI")
table(["Đường dẫn", "Nội dung"], [
    [".claude/skills/student-risk-screening/", "Mã nguồn skill 1: SKILL.md, scripts/risk_screening.py, references/, assets/, evals/"],
    [".claude/skills/analytics-capstone-pipeline/", "Mã nguồn skill 2: SKILL.md, scripts/ (dspipe.py, make_report.py, docx_kit.py, build_notebook.py, extensions/), references/, assets/"],
    [".claude/skill-dev/packaging/build_package.py", "Kiểm tra theo quy tắc chính thức, dựng plugin từ hai skill gốc, nén vào dist/"],
    [".claude/skill-dev/packaging/dist/", f"student-risk-screening.zip, analytics-capstone-pipeline.zip (claude.ai), n02-skills-marketplace.zip (Claude Code), checksums.txt"],
    [".claude/skill-dev/testing/", "run_tests.py, datasets/, configs/ và results/ (skill 1); capstone/ với cấu hình, kết quả và test_summary của skill 2"],
    [".claude/skill-dev/evaluation/", "Vòng đánh giá có/không có skill (skill 1)"],
    [".claude/skill-dev/docs/", "build_guide.py, _template_guide.docx, file hướng dẫn này (.docx, .md)"],
], [3600, 6400], "Cấu trúc mã nguồn và gói phát hành")

# ------------------------------------------------------------------ lưu
s = doc.settings.element
if s.find(W + "updateFields") is None:
    s.append(parse_xml(f'<w:updateFields xmlns:w="{W[1:-1]}" w:val="true"/>'))
doc.save(str(OUT_DOCX))
OUT_MD.write_text("\n".join(MD).strip() + "\n", encoding="utf-8")

# kiểm tra định dạng: chỉ Times New Roman, cỡ chữ ≥ 13
x = zipfile.ZipFile(OUT_DOCX).read("word/document.xml").decode("utf-8")
sizes = {int(v) / 2 for v in re.findall(r'<w:sz w:val="(\d+)"', x)}
fonts = set(re.findall(r'w:ascii="([^"]+)"', x))
print(f"saved {OUT_DOCX.name}: {TN[0]} bảng; cỡ chữ nhỏ nhất {min(sizes)}; font {fonts}")
