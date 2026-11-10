"""Sinh file hướng dẫn bộ skill: N02_HuongDan_Skill.docx (format như báo cáo nhóm) và N02_HuongDan_Skill.md."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEV = HERE.parent                      # .claude/skill-dev
ROOT = HERE.parents[2]                 # gốc dự án
sys.path.insert(0, str(ROOT / "reports" / "build"))
from docbuilder import Report  # noqa: E402

T = json.loads((DEV / "testing/results/test_summary.json").read_text(encoding="utf-8"))
B = json.loads((DEV / "evaluation/iteration-1/benchmark.json").read_text(encoding="utf-8"))
S = T["summary"]
MEMBERS = "Ngô Triệu Gia Gia - 25C11037\nTrần Duy Khương - 25C12004\nNguyễn Hoàng Nhật Quang - 25C12033"


def pc(x, d=1):
    return f"{x * 100:.{d}f}%".replace(".", ",")


def n3(x):
    return f"{x:.3f}"


DATASETS = [
    ["SAPE - Students_Academic_Performance_Evaluation_Dataset", "Mendeley Data, DOI 10.17632/dc3797vf3t.1, CC BY 4.0",
     "1.194 sinh viên CSE (Bangladesh), 31 biến khảo sát", "CGPA < 2.75 (sàng lọc đồng thời)", "Bộ dữ liệu của đồ án; kiểm tra tái lập Milestone 3-4"],
    ["UCI Student Performance (môn tiếng Bồ Đào Nha)", "UCI ML Repository, DOI 10.24432/C5TG7T, CC BY 4.0",
     "649 học sinh THPT, 33 biến", "G3 < 10 (trượt môn), mốc đầu năm học", "Bộ khác hoàn toàn: bậc học, thang điểm, biến rò rỉ G1/G2"],
    ["UCI Predict Students' Dropout and Academic Success", "UCI ML Repository, DOI 10.24432/C5MC89, CC BY 4.0",
     "4.424 sinh viên đại học (Bồ Đào Nha), 37 biến", "Target = Dropout, mốc cuối học kỳ 1", "Nhãn nhiều lớp, cỡ mẫu lớn, rò rỉ theo thời gian (học kỳ 2)"],
]

CAPABILITIES = [
    ["profile", "Đọc CSV/XLSX, tính SHA-256, mô tả schema; gắn cờ cột số lẫn chuỗi ('94-98'), giá trị dồn đống nghi điền khuyết, số 0 ở cột điểm, hằng số, "
                "văn bản tự do; sàng lọc biến rò rỉ (theo tên và AUC đơn biến ≥ 0.80), thuộc tính nhạy cảm; gợi ý luật nhãn nghi vấn và lớp dương; sinh suggested_config.json"],
    ["prepare", "Làm sạch theo cấu hình (trung điểm khoảng, mã khuyết, khoảng hợp lệ), tạo nhãn (ngưỡng hoặc lớp), loại nhãn không quan sát/nghi vấn, khóa giả danh, "
                "split phân tầng; chặn cấu hình nếu biến vừa là đặc trưng vừa bị loại; ghi validation và transformation log"],
    ["analyze", "Chẩn đoán trên train (Mann-Whitney/Chi-square/Fisher + Holm, hiệu ứng, logit điều chỉnh); baseline tỷ lệ nền và tín hiệu đơn tốt nhất (chọn trên train); "
                "LR và RF trong Pipeline (fit trên train), quy tắc chọn đặt trước; CV phân tầng lặp; test một lần kèm bootstrap CI; rút gọn bộ tín hiệu; "
                "permutation importance; công bằng theo nhóm kèm CI; hiệu chỉnh; bảng đánh đổi ngưỡng; độ nhạy; đối chiếu tiêu chí thành công; 4 biểu đồ"],
    ["report", "Báo cáo Markdown có số liệu: dữ liệu, nhật ký biến đổi, chẩn đoán, hiệu năng vs baseline, rút gọn, công bằng, ngưỡng, độ nhạy, tiêu chí, giới hạn/governance"],
    ["run", "Chạy liền prepare → analyze → report với một config đã được rà soát"],
    ["SKILL.md", "Quy trình 6 bước cho Claude: làm rõ quyết định và mốc dự báo, profile, chốt vai trò biến bằng lập luận domain, chạy, diễn giải có trách nhiệm, bàn giao theo milestone"],
]

GOOD = [
    "Tổng quát: chạy được trên 3 bộ dữ liệu khác nhau về bậc học, kích thước (649-4.424 dòng), định dạng (xlsx/csv dấu ';'), kiểu nhãn (ngưỡng điểm, nhiều lớp) chỉ bằng file cấu hình.",
    "Tái lập đúng đồ án: trên SAPE cho AUC CV 0.620 so với 0.619 của Milestone 4, cùng recall 48,5% trên test và cùng kết luận phủ định. Các chênh lệch nhỏ (ví dụ AUC test 0.614 so với 0.611) là do skill chạy pipeline tổng quát của chính nó (mã hóa, impute, làm tròn mặc định), không dùng lại mã của đồ án.",
    "Tự phát hiện các vấn đề mà nhóm mất nhiều công tìm thủ công: 140 nhãn nghi điền khuyết (3.15/2.68), 5 biến rò rỉ, 7 biến nhạy cảm, ô '94-98', G1/G2 ở bộ UCI.",
    "Kỷ luật đánh giá: baseline bắt buộc, split trước khi fit, test một lần, CI bootstrap, quy tắc chọn mô hình đặt trước, tiêu chí thành công đặt trước; trung thực với kết quả phủ định.",
    "Governance tích hợp: biến nhạy cảm bị loại khỏi mô hình nhưng giữ lại để kiểm định; phát hiện chênh lệch công bằng do biến đại diện gián tiếp (tuổi ở bộ Dropout: 21,9 điểm).",
    f"Đánh giá có/không có skill: pass rate {pc(B['run_summary']['with_skill']['pass_rate']['mean'], 0)} so với {pc(B['run_summary']['without_skill']['pass_rate']['mean'], 0)}; khác biệt nằm ở việc không dùng thuộc tính nhạy cảm làm đặc trưng.",
    "Đóng gói chuẩn: qua validator chính thức của skill-creator, mô tả 190 ký tự (dưới giới hạn 200 của claude.ai), plugin + marketplace cho Claude Code; 28/28 kiểm tra tự động đạt.",
]
NOT_GOOD = [
    "Không làm mô hình mạnh hơn: hiệu năng tương đương khi Claude tự làm không có skill; giá trị nằm ở quy trình, không ở độ chính xác.",
    "Gợi ý vai trò biến dựa trên từ khóa và thống kê, cần người rà soát: bộ Dropout bị gắn cờ cả biến học kỳ 1 (hợp lệ ở mốc cuối học kỳ 1); trước khi sửa, lớp dương được đoán sai là 'Enrolled'.",
    "Chỉ hỗ trợ dữ liệu một bảng, mỗi dòng một người học; chưa có split theo thời gian/nhóm (khóa, trường) - với dữ liệu nhiều khóa nên kiểm định theo khóa như lượt chạy không skill đã làm.",
    "Báo cáo tự sinh bằng tiếng Việt; báo cáo cho người dùng ngôn ngữ khác do Claude viết lại.",
    "Chưa hiệu chỉnh xác suất (điểm LR class_weight cân bằng bị thổi phồng) và chưa có giải thích cấp cá nhân (reason code) tự động.",
    "Tốn token hơn (TB ~87k so với ~64k) và chậm hơn ~98 giây mỗi lần do đọc hướng dẫn và chạy thêm phân tích độ nhạy.",
    "Cấu hình test Dropout giữ 3 biến vĩ mô cấp khóa (thất nghiệp, lạm phát, GDP); cả hai lượt đánh giá đều loại chúng vì hằng số trong một khóa - nên loại khi triển khai thật.",
]


def build_docx(out):
    r = Report(out, cover_title="HƯỚNG DẪN BỘ SKILL", cover_subtitle="STUDENT-RISK-SCREENING (PLUGIN EDU-ANALYTICS)")
    r.front_tables(
        [["Tên nhóm", "Nhóm N02"], ["Thành viên", MEMBERS], ["Tên skill", "student-risk-screening (plugin edu-analytics, marketplace n02-skills), phiên bản 1.1.0 - đổi tên từ education-data-analytics để phản ánh đúng tác vụ sàng lọc người học cần hỗ trợ"],
         ["Nền tảng", "Claude Code (plugin) và claude.ai (custom skill)"], ["Ngày", "10/11/2026"]],
        [["Lõi phân tích (analyze), thiết kế đánh giá, vòng đánh giá có/không có skill", "Nguyễn Hoàng Nhật Quang"],
         ["Profile, chuẩn bị dữ liệu, cấu hình và dữ liệu test", "Ngô Triệu Gia Gia"],
         ["SKILL.md, tài liệu tham chiếu, báo cáo tự sinh, file hướng dẫn", "Trần Duy Khương"],
         ["Bộ test tự động, đóng gói và rà soát", "Cả nhóm"]],
        "Phân công xây dựng skill")
    r.h1("BỘ SKILL CÓ THỂ LÀM ĐƯỢC GÌ?")
    r.p("student-risk-screening giúp Claude thực hiện trọn vẹn một phân tích sàng lọc người học cần hỗ trợ từ dữ liệu điểm, LMS, khảo sát hoặc hồ sơ tuyển sinh, "
        "theo đúng phương pháp đồ án N02 đã áp dụng ở Milestone 1-5: câu hỏi quyết định dữ liệu, kiểm soát rò rỉ, so sánh với baseline, kiểm định công bằng và "
        "trình bày trung thực cả kết quả phủ định. Skill gồm hướng dẫn quy trình cho Claude (SKILL.md) và một công cụ Python có 5 lệnh (profile, prepare, analyze, report, run); bảng dưới liệt kê từng lệnh và vai trò của SKILL.md:")
    r.table(["Thành phần", "Chức năng"], CAPABILITIES, widths=[1600, 7760], caption="Chức năng của bộ skill", label_col=True)
    r.p("Đầu ra của một lần chạy: prepared.csv, validation.json, transformation_log.json, results.json, report.md và 4 biểu đồ (ROC/PR, recall theo tỷ lệ gắn cờ, "
        "đường rút gọn, hiệu chỉnh). Ví dụ yêu cầu kích hoạt skill: 'Tôi có file điểm và log LMS của khóa trước, muốn biết sau tuần 5 có lọc được sinh viên có "
        "cần hỗ trợ để cố vấn gặp trước không, cố vấn chỉ gặp được 20% sinh viên.'")
    r.h1("MỨC ĐỘ")
    r.table(["Khía cạnh", "Mức"], [
        ["Theo Đề cương học phần", "Mức 3 - Predictive / Explanatory: có mô hình sàng lọc, target, mốc dự báo, baseline, metric, phân tích FN/FP, giải thích (hệ số, permutation importance), governance. Bao gồm cả Mức 1-2 (mô tả, chẩn đoán)."],
        ["Mức tự động hóa", "Bán tự động có kiểm soát: công cụ tự profile và gợi ý, nhưng vai trò biến, ngưỡng nhãn và mốc dự báo phải được Claude/người phân tích chốt bằng lập luận domain trước khi chạy."],
        ["Không thuộc phạm vi", "Mức 4-5 (Knowledge Graph, RAG, Agent tự hành động); không suy luận nhân quả, không đánh giá hiệu quả can thiệp, không tự liên hệ người học."],
        ["Yêu cầu kỹ thuật", "Python 3.9+ (đã kiểm thử trên 3.12), pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib, openpyxl; dữ liệu vài nghìn dòng chạy 1-2 phút."],
    ], widths=[2400, 6960], caption="Mức độ của bộ skill", label_col=True)
    r.h1("CÀI ĐẶT VÀ SỬ DỤNG")
    r.h2("Claude Code (plugin)")
    r.h2("Claude Code - chép thư mục (nhanh nhất)")
    r.p("Chép thư mục .claude/skills/student-risk-screening/ vào .claude/skills/ của dự án (chỉ dùng trong dự án đó) hoặc vào "
        "~/.claude/skills/ (dùng cho mọi dự án). Claude Code tự nạp skill khi khởi động, không cần lệnh cài.")
    r.h2("Claude Code - plugin")
    r.code(["# giải nén .claude/skill-dev/packaging/dist/n02-skills-marketplace.zip, rồi trong Claude Code:", "/plugin marketplace add ./n02-skills-marketplace",
            "/plugin install edu-analytics@n02-skills", "# gọi trực tiếp (hoặc để Claude tự kích hoạt khi bạn yêu cầu phân tích dữ liệu sinh viên):",
            "/edu-analytics:student-risk-screening"])
    r.h2("claude.ai")
    r.p("Bật Code execution trong Settings > Capabilities; vào Customize > Skills, tải lên student-risk-screening.zip (thư mục skill nằm ở cấp cao nhất của ZIP) và bật skill.")
    r.h2("Dùng trực tiếp công cụ (không qua Claude)")
    r.code(["python scripts/risk_screening.py profile students.csv --target \"final_result\" --out work/",
            "# rà soát work/suggested_config.json -> work/config.json (xem references/config-schema.md)",
            "python scripts/risk_screening.py run --config work/config.json"])
    r.h1("ĐÃ CHẠY TEST TRÊN BỘ DỮ LIỆU NÀO?")
    r.table(["Bộ dữ liệu", "Nguồn / giấy phép", "Quy mô", "Bài toán", "Mục đích test"], DATASETS, widths=[2000, 2100, 1700, 1700, 1860],
            caption="Ba bộ dữ liệu dùng để test")
    r.p("Mỗi bộ được chạy đủ chuỗi profile → rà soát cấu hình theo domain → run (cấu hình trong .claude/skill-dev/testing/configs). Ngoài ra skill được đánh giá theo "
        "quy trình skill-creator: Claude (tác tử con) làm 2 nhiệm vụ thực tế trên hai bộ UCI, mỗi nhiệm vụ một lần có skill và một lần không có skill, chấm theo 6 tiêu chí khách quan.")
    r.h1("KẾT QUẢ")
    r.h2("Kết quả phân tích trên ba bộ dữ liệu")
    rows = []
    names = {"sape": "SAPE", "uci_student_por": "UCI Student Performance", "uci_dropout": "UCI Dropout"}
    for k, s in S.items():
        rows.append([names[k], f"{s['labeled']} / {s['positives']} ({pc(s['positives'] / s['labeled'])})", f"{n3(s['cv_auc_primary']['mean'])} ({n3(s['cv_auc_baseline']['mean'])})",
                     f"{n3(s['test_auc_primary'])} [{n3(s['test_auc_ci95'][0])}; {n3(s['test_auc_ci95'][1])}]", f"{pc(s['test_recall_at_capacity'])} / {pc(s['test_precision_at_capacity'])}",
                     f"{sum(s['success'].values())}/{len(s['success'])}"])
    r.table(["Bộ dữ liệu", "Nhãn / ca dương", "AUC CV LR (baseline)", "AUC test [CI 95%]", "Recall / precision test @30%", "Tiêu chí đạt"], rows,
            widths=[1900, 1700, 1500, 1800, 1500, 960], caption="Hiệu năng mô hình sàng lọc (LR là primary ở cả ba bộ)", center_cols=(5,))
    r.p("Tiêu chí 'vượt baseline ≥ 0.02 AUC' là mặc định cố định trong mã của skill trước mọi lần chạy; riêng với SAPE, ngưỡng này được đặt sau khi đồ án đã có kết quả, nên khi so với báo cáo đồ án chỉ coi là so sánh bổ sung.", indent=False)
    r.p("Cột 'Tiêu chí đạt' là số tiêu chí thành công mà công cụ tự đối chiếu. Với SAPE, công cụ chấm tiêu chí công bằng trên dự đoán OOF của train (đạt), "
        "trong khi báo cáo Milestone 4 thận trọng ghi 'chưa kết luận được' vì chênh lệch trên tập kiểm tra lớn nhưng số ca dương mỗi nhóm rất nhỏ.", indent=False)
    r.bullets([
        "**SAPE:** phiếu khảo sát tự báo cáo chỉ cho tín hiệu yếu, mô hình không vượt baseline chuyên cần (0.620 so với 0.615), không đạt AUC và recall - tái lập đúng kết luận phủ định của đồ án.",
        "**UCI Student Performance:** đạt cả 6 tiêu chí; tín hiệu chính là số lần trượt trước đây, trường học và nguyện vọng học tiếp; mô hình hơn baseline 0.13 AUC.",
        "**UCI Dropout:** hiệu năng cao nhất (AUC 0.876, bắt 67,6% sinh viên bỏ học khi gắn cờ 30%, precision 75%), nhưng trượt tiêu chí công bằng: sinh viên ≤ 20 tuổi chỉ được bắt 55% so với 77% (chênh lệch theo giới tính cũng 10,2 điểm; chênh lệch theo tuổi 21,9 điểm) dù tuổi không phải đầu vào.",
    ])
    r.h2("Bộ test tự động")
    r.p(f".claude/skill-dev/testing/run_tests.py chạy lại toàn bộ pipeline trên ba bộ dữ liệu và kiểm tra {T['total']} tính chất (không biến cấm trong đặc trưng, split phân tầng, đủ kết quả, "
        f"baseline chọn trên train, có báo cáo và hình, tái lập Milestone 4, phát hiện nhãn nghi vấn, rò rỉ, lớp dương đúng...). Kết quả: **{T['passed']}/{T['total']} đạt**.")
    r.h2("Đánh giá có và không có skill (skill-creator)")
    r.p("Vòng đánh giá này chạy trên phiên bản 1.0.0 (tên cũ education-data-analytics). Bản 1.1.0 đổi tên skill và thu hẹp phần mô tả, mục khi nào dùng; "
        "quy trình và công cụ phân tích không đổi, nên nhóm chưa chạy lại vòng đánh giá.", indent=False)
    rs = B["run_summary"]
    r.table(["Chỉ số", "Có skill", "Không có skill", "Chênh lệch"], [
        ["Pass rate (12 tiêu chí)", pc(rs["with_skill"]["pass_rate"]["mean"], 0), pc(rs["without_skill"]["pass_rate"]["mean"], 0), "+17 điểm"],
        ["Thời gian TB", f"{rs['with_skill']['time_seconds']['mean']:.0f} giây", f"{rs['without_skill']['time_seconds']['mean']:.0f} giây", f"+{rs['with_skill']['time_seconds']['mean'] - rs['without_skill']['time_seconds']['mean']:.0f} giây"],
        ["Token TB", f"{rs['with_skill']['tokens']['mean']:,.0f}".replace(",", "."), f"{rs['without_skill']['tokens']['mean']:,.0f}".replace(",", "."), f"+{rs['with_skill']['tokens']['mean'] - rs['without_skill']['tokens']['mean']:,.0f}".replace(",", ".")],
    ], widths=[3000, 2100, 2100, 2160], caption="Benchmark 2 nhiệm vụ × 2 cấu hình", center_cols=(1, 2, 3))
    r.p("Cả hai cấu hình đều loại đúng biến rò rỉ, so sánh với baseline, báo recall ở mức 30%, kiểm định công bằng và diễn đạt ở mức liên hệ. Khác biệt duy nhất: khi không có "
        "skill, Claude vẫn đưa thuộc tính nhạy cảm (tuổi, nghề nghiệp/học vấn cha mẹ, nơi ở, học bổng...) vào mô hình ở cả hai nhiệm vụ; khi có skill, các biến này chỉ được dùng để "
        "kiểm định công bằng. Trình xem chi tiết: .claude/skill-dev/evaluation/eval_review.html.")
    r.h2("Lỗi phát hiện trong quá trình đánh giá và đã sửa")
    r.bullets([
        "Cấu hình gợi ý chọn lớp hiếm nhất ('Enrolled') làm lớp dương ở bộ Dropout; nay ưu tiên lớp mang nghĩa kết quả bất lợi (dropout, fail, withdrawn...) và ghi chú cần xác nhận.",
        "Cấu hình test UCI ban đầu giữ 'absences' (số buổi vắng của chính năm học) và 'schoolsup': tác tử con có skill phát hiện; đã loại và bổ sung cảnh báo về biến tích lũy trong kỳ vào SKILL.md.",
        "Báo cáo tự sinh để trống mục độ nhạy khi không cấu hình; nay ghi rõ.",
    ])
    r.h1("NHẬN XÉT CHUNG")
    r.h2("Mặt được")
    r.bullets(GOOD)
    r.h2("Chưa được")
    r.bullets(NOT_GOOD)
    r.h2("Hướng phát triển")
    r.bullets(["Kiểm định theo nhóm/thời gian (GroupKFold theo khóa, temporal split) khi dữ liệu có cột khóa hoặc mốc thời gian.",
               "Hiệu chỉnh xác suất (Platt/isotonic trên OOF) và reason code cấp cá nhân theo ngôn ngữ hỗ trợ.",
               "Báo cáo song ngữ Việt/Anh; xuất .docx theo mẫu milestone.",
               "Hỗ trợ dữ liệu nhiều bảng (LMS event log) với tổng hợp theo cửa sổ thời gian trước mốc dự báo."])
    r.h1("CẤU TRÚC GÓI VÀ MÃ NGUỒN", numbered=True)
    r.table(["Đường dẫn", "Nội dung"], [
        [".claude/skill-dev/packaging/dist/student-risk-screening.zip", "Gói tải lên claude.ai (6 file: SKILL.md, scripts, references, assets)"],
        [".claude/skill-dev/packaging/dist/n02-skills-marketplace.zip", "Marketplace + plugin cho Claude Code (kèm evals)"],
        [".claude/skills/student-risk-screening/", "Skill gốc - nguồn duy nhất: SKILL.md, scripts/risk_screening.py, references/, assets/, evals/"],
        [".claude/skill-dev/packaging/", "Manifest plugin + marketplace, build_package.py (kiểm tra và đóng gói), dist/"],
        [".claude/skill-dev/testing/", "run_tests.py, datasets/ (3 bộ), configs/, results/ (test_summary.md)"],
        [".claude/skill-dev/evaluation/", "Vòng đánh giá có/không có skill: đầu ra, chấm điểm, benchmark, eval_review.html"],
        [".claude/skill-dev/docs/", "build_guide.py và file hướng dẫn này"],
    ], widths=[3800, 5560], caption="Cấu trúc gói nộp liên quan đến skill")
    r.save()


def build_md(out):
    L = ["# Hướng dẫn bộ skill student-risk-screening (nhóm N02)", "",
         "Plugin `edu-analytics` (marketplace `n02-skills`), phiên bản 1.1.0. Nền tảng: Claude Code và claude.ai.", "",
         "## 1. Bộ skill có thể làm được gì?", ""]
    L += [f"- **{a}**: {b}" for a, b in CAPABILITIES]
    L += ["", "## 2. Mức độ", "", "- Mức 3 (Predictive / Explanatory) theo Đề cương, bao gồm Mức 1-2.",
          "- Bán tự động có kiểm soát: vai trò biến, ngưỡng nhãn, mốc dự báo do Claude/người phân tích chốt bằng lập luận domain.",
          "- Không thuộc phạm vi: KG/RAG/Agent, suy luận nhân quả, tự liên hệ người học.", "",
          "## 3. Cài đặt", "", "Giải nén n02-skills-marketplace.zip trước, rồi trong Claude Code:", "", "```", "/plugin marketplace add ./n02-skills-marketplace", "/plugin install edu-analytics@n02-skills", "```",
          "Hoặc chép `.claude/skills/student-risk-screening/` vào `.claude/skills/` của dự án hoặc `~/.claude/skills/`.",
          "claude.ai: Customize > Skills > tải `student-risk-screening.zip` (cần bật Code execution).", "",
          "## 4. Dữ liệu test", "", "| Bộ dữ liệu | Nguồn | Quy mô | Bài toán |", "|---|---|---|---|"]
    L += [f"| {d[0]} | {d[1]} | {d[2]} | {d[3]} |" for d in DATASETS]
    L += ["", "## 5. Kết quả", "", "| Bộ dữ liệu | AUC CV (baseline) | AUC test [CI] | Recall @30% test | Tiêu chí |", "|---|---|---|---|---|"]
    for k, s in S.items():
        L.append(f"| {k} | {n3(s['cv_auc_primary']['mean'])} ({n3(s['cv_auc_baseline']['mean'])}) | {n3(s['test_auc_primary'])} {s['test_auc_ci95']} | "
                 f"{pc(s['test_recall_at_capacity'])} | {sum(s['success'].values())}/{len(s['success'])} |")
    rs = B["run_summary"]
    L += ["", f"- Bộ test tự động: **{T['passed']}/{T['total']} đạt**.",
          f"- Đánh giá skill-creator: pass rate có skill {pc(rs['with_skill']['pass_rate']['mean'], 0)}, không có skill {pc(rs['without_skill']['pass_rate']['mean'], 0)}.", "",
          "## 6. Nhận xét chung", "", "### Mặt được", ""] + [f"- {x}" for x in GOOD] + ["", "### Chưa được", ""] + [f"- {x}" for x in NOT_GOOD]
    Path(out).write_text("\n".join(L).replace("**", "**"), encoding="utf-8")


if __name__ == "__main__":
    build_docx(HERE / "N02_HuongDan_Skill.docx")
    build_md(HERE / "N02_HuongDan_Skill.md")
    print("saved")
