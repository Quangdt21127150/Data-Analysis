---
name: analytics-capstone-pipeline
description: Chạy trọn quy trình phân tích dữ liệu bảng bất kỳ (CSV/Excel) có biến mục tiêu: kiểm toán, chống rò rỉ, mô hình kiểm định chéo, công bằng, rồi dựng báo cáo Word và dàn ý slide.
---

# Quy trình phân tích dữ liệu hoàn chỉnh (Analytics Capstone Pipeline)

Skill này đúc kết năm milestone của một đồ án thực tế (sàng lọc sinh viên cần hỗ trợ học tập) thành một quy trình tái sử dụng được. Người dùng chỉ cần đưa dữ liệu và nêu biến mục tiêu; skill dựng toàn bộ chuỗi sản phẩm với các con số được sinh trực tiếp từ kết quả, nên báo cáo không bao giờ lệch với bảng.

Ngôn ngữ làm việc: tiếng Việt học thuật, trang trọng, đúng thuật ngữ. Mọi chú thích mã, báo cáo và tin nhắn gửi người dùng đều bằng tiếng Việt.

## Khi nào dùng

Dùng skill này mỗi khi giảng viên hoặc sinh viên nói "phân tích bộ dữ liệu này", "làm đồ án khoa học dữ liệu", "sàng lọc / dự báo nhóm nguy cơ", "xây pipeline phân tích và báo cáo từ file dữ liệu", "chấm hoặc dựng lại milestone 1 đến 5", hoặc đưa một tệp dữ liệu kèm một biến mục tiêu, kể cả khi họ không nhắc đến tên skill. Skill bao trùm từ kiểm toán chất lượng, chống rò rỉ, đăng ký trước tiêu chí, chẩn đoán, mô hình dự báo kiểm định chéo, hiệu chuẩn, công bằng, đến báo cáo Word có mục lục và trích dẫn, tài liệu giải thích mã, dàn ý slide và kịch bản thuyết trình.

## Điều cần có từ người dùng

1. Tệp dữ liệu (CSV hoặc Excel). 
2. Biến mục tiêu. Hai dạng: biến liên tục kèm ngưỡng ("CGPA < 2,75") hoặc nhãn nhị phân có sẵn.
3. Tùy chọn: bên liên quan và quyết định cần hỗ trợ, cột nhạy cảm cho công bằng, thông tin nhóm, tiêu chí thành công riêng.

Nếu thiếu mục (2), không đoán: đọc dữ liệu rồi hỏi một câu ngắn bằng AskUserQuestion (nếu không có công cụ thì hỏi bằng văn bản), kèm tối đa bốn cột ứng viên. Với các mục còn lại, nêu giả định đang dùng ở đầu phản hồi rồi đi tiếp.

## Quy trình tám bước

Đường dẫn dưới đây tính từ thư mục của skill này. Làm việc trong một thư mục riêng cho dự án, không chạy bên trong thư mục skill.

1. **Khởi tạo cấu hình.** 
   `python scripts/dspipe.py init --data <tệp> --target "<cột>" [--threshold T --positive-if "<" --missing-codes 0 | --positive-values 0] [--id-col <cột> --sheet <tên>] --out config.json`
   (`--threshold` cho biến liên tục; `--positive-values` cho nhãn nhị phân, liệt kê giá trị tính là ca dương.)
   Lệnh in ra số dòng hợp lệ, tỷ lệ ca dương, các cột nghi rò rỉ và vấn đề chất lượng, đồng thời ghi `config.json` kèm khối `_goi_y`.
2. **Xác nhận cấu hình với người dùng.** Đây là bước duy nhất bắt buộc có con người, vì nhãn, ngưỡng, cột rò rỉ và tiêu chí thành công quyết định mọi kết luận về sau. Đọc `_goi_y`, rồi điền hoặc sửa: `features`, `groups` (nhóm đặc trưng cho ablation), `fairness_cols`, `baseline_feature`, `exclude.leakage`, `keep_despite_leakage_flag`, `context`, `stakeholders`, `analysis_questions`, `team`, `criteria`. Xem `references/config_guide.md` và mẫu `assets/config_example_sape.json`. Nếu người dùng vắng mặt hoặc đã nói "cứ làm", chọn mặc định hợp lý và ghi từng giả định vào phần Hạn chế của báo cáo.
3. **Chạy thử nhanh.** `python scripts/dspipe.py all --config config.json --fast` để phát hiện lỗi cấu hình trong vài chục giây. Số liệu của lần này không được dùng để báo cáo.
4. **Chạy đầy đủ.** `python scripts/dspipe.py all --config config.json` (kiểm định chéo 5×10, bootstrap 2.000 lần; khoảng vài phút trên 2 CPU; chạy nền nếu công cụ có giới hạn thời gian). Kết thúc bằng giai đoạn kiểm chứng; nếu có phép kiểm tra không đạt, đọc `verify.json`, sửa nguyên nhân rồi chạy lại, không bỏ qua.
5. **Đọc kết quả trước khi viết.** Mở `results.json`, `audit.json`, các bảng trong `tables/` và nhìn các hình trong `figures/`. Quy tắc diễn giải nằm ở `references/methodology.md`; đặc biệt đừng diễn giải quá mức khi khoảng tin cậy rộng hoặc khi tiêu chí không đạt.
6. **Dựng sản phẩm.** `python scripts/make_report.py --config config.json` sinh ra bốn tệp trong `<out_dir>/deliverables/`: báo cáo Word (không chứa mã thực thi, có mục lục kèm số trang, trích dẫn đánh số), tài liệu giải thích mã và cách trợ lý hỗ trợ (tách riêng), `deck_outline.json` và kịch bản thuyết trình. Với slide: nếu phiên làm việc có loại Slides trong công cụ Artifact thì dựng bộ slide từ `deck_outline.json` (đọc `references/report_and_deck_spec.md`); nếu người dùng muốn PowerPoint thì dùng skill pptx.
7. **Kiểm tra sản phẩm.** Mở báo cáo (đổi sang PDF rồi nhìn các trang), kiểm tra: số trang trong mục lục khớp, không có mã thực thi trong báo cáo chính, không có dấu gạch ngang dài (— hoặc –), số liệu trong tóm tắt khớp bảng, danh mục tài liệu tham khảo khớp các trích dẫn [x]. Lệnh `make_report.py` đã tự quét dấu gạch ngang dài.
8. **Giao kết quả.** Gửi tệp bằng SendUserFile, nêu một đến hai câu về kết luận (bao nhiêu trên năm tiêu chí đạt, mô hình giữ lại, điểm cần lưu ý), liệt kê giả định và hạn chế quan trọng nhất, và kết thúc bằng dự báo bước kỹ thuật tiếp theo.

## Những nguyên tắc không được thương lượng

Những nguyên tắc này đến từ các lỗi thực tế đã gặp trong đồ án gốc; chúng tồn tại để kết luận còn đáng tin sau khi bị chất vấn.

- **Không dữ liệu giả.** Không tạo, nội suy hay mô phỏng dữ liệu để lấp chỗ thiếu trong sản phẩm. Thiếu thì ghi rõ là thiếu.
- **Chống rò rỉ.** Mọi tiền xử lý nằm trong Pipeline và chỉ fit trên phần huấn luyện của fold. Cột nghi rò rỉ (tên gợi ý hệ quả của nhãn và sức dự báo đơn lẻ rất cao) bị loại tạm thời và phải được người dùng xác nhận mới đưa lại.
- **Đăng ký trước.** Tiêu chí S1 đến S5 được băm SHA-256 trước khi mô hình hóa. Không sửa tiêu chí sau khi đã thấy kết quả; nếu buộc phải đổi, ghi Change Log và chạy lại từ bước prereg.
- **Trung thực về độ bất định.** Báo cáo khoảng tin cậy chứ không chỉ ước lượng điểm. Công bằng chỉ kết luận khi khoảng tin cậy hẹp; nếu rộng hơn 20 điểm phần trăm thì ghi "chưa kết luận".
- **Không nhân quả.** Dữ liệu quan sát cắt ngang chỉ cho liên hệ. Mô tả đúng như vậy trong báo cáo, kể cả khi kết quả đẹp.
- **Mẫu độ nhạy.** Khi có cụm giá trị lặp bất thường (nghi giá trị thay thế), mẫu chính loại cụm đó và mẫu độ nhạy B giữ lại; luôn báo cáo cả hai.
- **Tiêu chí không đạt vẫn là kết quả.** Đừng chỉnh mô hình đến khi đạt. Báo cáo trung thực rằng bằng chứng chưa đủ và nói rõ cần thêm gì.
- **Quy cách văn bản.** Tiếng Việt học thuật; không dùng dấu gạch ngang dài; mục lục có số trang; trích dẫn đánh số [x] khớp danh mục; báo cáo chính không chứa mã, phần giải thích mã để ở tệp Word riêng.
- **Môi trường.** Nếu mạng bị tắt và thiếu thư viện (ví dụ shap, statsmodels, semopy), không cố cài; dùng phần đã có, nói rõ thư viện nào chưa dùng và để người dùng đổi cài đặt mạng. `dspipe.py` chỉ cần pandas, numpy, scipy, scikit-learn, matplotlib; python-docx cho báo cáo; LibreOffice và pdftotext để điền số trang mục lục.

## Mở rộng theo yêu cầu

Chỉ làm khi người dùng yêu cầu hoặc đề bài đòi hỏi, vì mỗi mục cần dữ liệu và giả định riêng.

- **SEM / CFA với semopy** (khi dữ liệu là thang đo đa mục hỏi): dùng `scripts/extensions/sem_template.py`; nhắc người dùng trình bày tường minh Cronbach's Alpha > 0,7, hệ số tải > 0,5, AVE > 0,5, CR > 0,7, RMSEA < 0,08, CFI/TLI > 0,9 và hệ số đường dẫn.
- **SHAP và LIME cho mô hình cây:** `scripts/extensions/xai_shap_lime.py`; sau đó so sánh quan hệ tuyến tính (hệ số logistic hoặc SEM) với tương tác phi tuyến từ SHAP.
- **Trực quan hóa đa công cụ** (Tableau, mã thuần, Microsoft Data Formulator v2): khung tiêu chí chọn hình tốt nhất và mẫu prompt nằm ở `references/viz_comparison.md`.
- **Sổ tay Colab:** `python scripts/build_notebook.py --config config.json --out Quy_trinh.ipynb` sinh sổ tay tự chứa; chỉ cần tải dữ liệu lên.

## Bản đồ tài liệu tham chiếu

| Tệp | Đọc khi |
|---|---|
| `references/config_guide.md` | Điền hoặc sửa `config.json`, hiểu từng trường |
| `references/methodology.md` | Diễn giải kết quả, quy tắc chọn mô hình, ngưỡng, giải thích cho giảng viên |
| `references/report_and_deck_spec.md` | Viết thêm chương, dựng slide, quy cách kịch bản đọc |
| `references/pitfalls.md` | Dữ liệu có dấu hiệu lạ (mã thiếu, giá trị lặp, rò rỉ, cỡ mẫu nhỏ, tự khai) |
| `references/viz_comparison.md` | Khung so sánh Tableau, mã thuần, Data Formulator v2 |
| `references/refs.json` | Danh mục 31 tài liệu tham khảo đã kiểm chứng (khóa dùng trong `r.C(...)`) |

## Cấu trúc đầu ra của `dspipe.py`

Trong `<thư mục cấu hình>/<out_dir>/`: `audit.json`, `prepared_info.json`, `evaluation_plan_prereg.json`, `diagnose.json`, `results.json`, `verify.json`, `xai_status.json`; `tables/*.csv` (audit, diagnose, model); `figures/f01` đến `f09` (PNG); `data/prepared_*.csv`; `logs/transformation_log.csv`; `deliverables/` (sau `make_report.py`).

## Ví dụ

**Ví dụ 1.** Người dùng: "Đây là file khảo sát sinh viên, phân tích giúp tôi, nhóm cần hỗ trợ là CGPA dưới 2,75." 
Hành động: `init` với `--threshold 2.75 --positive-if "<"`, đọc `_goi_y` (sẽ phát hiện cột điểm kỳ trước nghi rò rỉ và cụm giá trị lặp), xác nhận cấu hình, chạy đầy đủ, dựng sản phẩm, giao báo cáo và nêu: bao nhiêu tiêu chí đạt, mô hình giữ lại, hạn chế tự khai.

**Ví dụ 2.** Người dùng: "Dùng skill này cho bộ dữ liệu chẩn đoán ung thư vú, nhãn là cột diagnosis." 
Hành động: nhãn nhị phân (`--target diagnosis --positive-values M`, không cần ngưỡng), đặt `criteria` phù hợp lĩnh vực (ví dụ AUC 0,95 và recall 0,90), chạy và báo cáo. Nhắc rằng trong y khoa cần kiểm định ngoài trước khi dùng thực tế.
