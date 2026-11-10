---
name: student-risk-screening
description: Sàng lọc người học cần hỗ trợ từ dữ liệu điểm/LMS/khảo sát - profiling, rò rỉ, chẩn đoán, mô hình vs baseline, công bằng, ngưỡng, báo cáo. Dùng khi cần tìm, xếp ưu tiên người học cần hỗ trợ.
license: MIT
compatibility: Python 3.9+ với pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib (openpyxl nếu đọc .xlsx).
metadata:
  author: "Nhóm N02 - Khoa học Phân tích Dữ liệu, FIT-HCMUS"
  version: "1.1.0"
---

# Student Risk Screening (sàng lọc người học cần hỗ trợ có trách nhiệm)

Skill này biến một bảng dữ liệu người học (điểm, LMS, khảo sát, hồ sơ tuyển sinh) thành một phân tích **có thể bảo vệ được**:
hiểu dữ liệu → phát hiện vấn đề chất lượng và rò rỉ → chuẩn bị dữ liệu tái lập → chẩn đoán → mô hình sàng lọc so với baseline
→ rút gọn tín hiệu → kiểm định công bằng → bảng đánh đổi ngưỡng → báo cáo có số liệu và giới hạn rõ ràng.
Phương pháp lấy từ đồ án N02 (Milestone 1-5): câu hỏi quyết định dữ liệu, không làm ngược lại; kết quả phủ định được chứng minh
cũng là kết quả hợp lệ.

Công cụ chính: `scripts/risk_screening.py` (một file, chỉ cần các thư viện khoa học dữ liệu phổ biến).
Trong Claude Code gọi bằng `python "${CLAUDE_SKILL_DIR}/scripts/risk_screening.py" ...`; trên claude.ai dùng đường dẫn tương đối `scripts/risk_screening.py`.

## Khi nào dùng
- Người dùng có dữ liệu sinh viên/học sinh và muốn tìm, xếp ưu tiên người học cần hỗ trợ (nguy cơ trượt, bỏ học, điểm thấp) hoặc xây
  cảnh báo sớm; các bước profiling, chẩn đoán yếu tố liên quan và báo cáo là một phần của quy trình sàng lọc này.
- Không dùng làm công cụ đánh giá chất lượng dữ liệu hay viết báo cáo nói chung khi không có bài toán sàng lọc người học.
- Không dùng cho: tra cứu quy chế, chấm bài, phân tích văn bản tự do, hoặc khi người dùng chỉ cần một biểu đồ đơn lẻ.

## Quy trình

### Bước 1 - Làm rõ quyết định trước khi chạm vào mô hình
Xác định (hỏi người dùng nếu chưa rõ, mỗi lần một vài câu): ai dùng kết quả và để quyết định gì; đơn vị phân tích (một dòng là gì);
kết quả cần sàng lọc và **ngưỡng theo quy chế/nghiệp vụ** (không chọn theo phân bố dữ liệu); **mốc dự báo** (thông tin nào có trước thời điểm ra quyết định);
năng lực can thiệp (ví dụ chỉ hỗ trợ được 30% hay 15% người học); tiêu chí thành công. Lý do: thiếu mốc dự báo là nguồn rò rỉ phổ biến nhất,
và thiếu năng lực can thiệp thì không chọn được điểm cắt có ý nghĩa.

### Bước 2 - Profile dữ liệu
```bash
python scripts/risk_screening.py profile <data.csv|xlsx> --target "<cột kết quả>" --out work/
```
Đọc `work/profile.md`. Công cụ tự gắn cờ: cột số lẫn chuỗi (ví dụ "94-98"), giá trị dồn đống nghi điền khuyết, số 0 ở cột điểm có thể là khuyết,
hằng số, văn bản tự do, biến có liên hệ quá mạnh với nhãn (nghi rò rỉ), thuộc tính nhạy cảm; và gợi ý luật nhãn nghi vấn
(giá trị dồn đống của mục tiêu đi kèm một giá trị cố định ở cột khác). Báo cáo các phát hiện này cho người dùng bằng lời.

### Bước 3 - Chốt vai trò biến bằng lập luận domain (phần quan trọng nhất)
`work/suggested_config.json` chỉ là gợi ý từ khóa và thống kê. Rà soát từng biến:
- **Rò rỉ**: loại mọi biến ghi nhận *sau* mốc dự báo hoặc được *xác định bởi* kết quả (điểm kỳ sau, cảnh cáo học vụ, học bổng thành tích,
  đã được tư vấn...). Cẩn thận với biến *tích lũy trong chính kỳ được dự báo* (số buổi vắng cả năm, hỗ trợ học tập đã nhận): tên trông vô hại
  nhưng giá trị cuối kỳ chưa có ở mốc dự báo. Biến có tên giống điểm nhưng phát sinh *trước* mốc dự báo (ví dụ điểm học kỳ 1 khi dự báo bỏ học
  cuối năm) được giữ.
- **Nhạy cảm** (giới tính, tuổi, thu nhập, sức khỏe, khuyết tật, hoàn cảnh gia đình, quốc tịch, nợ học phí...): không làm đặc trưng;
  chọn 1-3 biến vào `fairness_audit` để kiểm định công bằng.
- **Nhiễu/không dùng**: hằng số, ID, văn bản tự do, biến đa cộng tuyến gần hoàn toàn với biến khác.
- **Nhãn nghi vấn**: nếu profile gợi ý luật dồn đống, kiểm tra thứ tự dòng/giá trị rồi đưa vào `suspect_label_rules` (bị loại khỏi tập nhãn chính,
  vẫn được chạy độ nhạy).
Ghi lại mỗi quyết định kèm lý do để đưa vào báo cáo (Change Log). Chi tiết khóa cấu hình: `references/config-schema.md`;
mẫu: `assets/config-template.json`.

### Bước 4 - Chạy toàn bộ phân tích
```bash
python scripts/risk_screening.py run --config work/config.json
```
Kết quả trong `out_dir`: `prepared.csv`, `validation.json`, `transformation_log.json`, `results.json`, `report.md`, `figures/`.
Pipeline: split phân tầng trước mọi phép fit; impute/chuẩn hóa/one-hot nằm trong Pipeline fit trên train; chẩn đoán chỉ trên train;
baseline B0 (tỷ lệ nền) và B1 (tín hiệu đơn tốt nhất, chọn trên train); LR (primary) và RF, quy tắc chọn đặt trước
(RF chỉ thay nếu hơn ≥ 0.02 AUC CV và recall không kém); CV phân tầng lặp; đánh giá test **một lần**; bootstrap CI;
rút gọn bộ tín hiệu; công bằng; hiệu chỉnh; bảng đánh đổi ngưỡng; độ nhạy theo ngưỡng nhãn và nhãn nghi vấn.
Bộ dữ liệu vài nghìn dòng chạy trong 1-3 phút.

### Bước 5 - Diễn giải có trách nhiệm
Đọc `results.json`/`report.md` rồi viết phần nhận định cho người dùng. Những điều cần giữ:
- So sánh với **baseline B1** trước khi khen mô hình: nếu chỉ ngang một biến đơn, nói thẳng như vậy.
- Lấy CV làm căn cứ chính; test nhỏ thì nêu CI. Không chọn mô hình hay ngưỡng dựa trên test.
- Chẩn đoán là **liên hệ**, không phải nguyên nhân; nêu khả năng chiều ngược và yếu tố gây nhiễu.
- Nếu Brier kém hơn dự đoán hằng số (thường do class_weight cân bằng), điểm chỉ dùng để **xếp hạng**, không gọi là xác suất.
- Công bằng: báo chênh lệch recall và tỷ lệ gắn cờ theo nhóm kèm CI; chênh lệch lớn ở biến *không* nằm trong mô hình nghĩa là có biến đại diện gián tiếp.
- Dữ liệu cắt ngang thì gọi là "sàng lọc đồng thời", không gọi là "dự báo sớm".
- Không đạt tiêu chí thành công vẫn là kết quả hữu ích: nói rõ tín hiệu nào thiếu và dữ liệu nào cần thu thập.
- Không bao giờ đề xuất tự động liên hệ hay gán nhãn người học; mọi hành động cần con người phê duyệt, diễn đạt theo hướng hỗ trợ.
Hướng dẫn chi tiết và cách viết: `references/responsible-analytics.md`.

### Bước 6 - Bàn giao
`report.md` do công cụ sinh là phụ lục kỹ thuật (tiếng Việt). Báo cáo cho người dùng do bạn viết, theo ngôn ngữ của họ, dựa trên số liệu trong `results.json`.
Trình bày ngắn: câu trả lời cho câu hỏi quyết định, bảng hiệu năng so với baseline, tiêu chí đạt/không đạt, rủi ro công bằng, giới hạn,
khuyến nghị cho từng stakeholder. Nếu người dùng cần báo cáo theo milestone (proposal, data understanding, modeling, final report) hoặc
traceability matrix, dùng khung trong `references/methodology.md`.

## Lỗi thường gặp cần tránh
- Đưa điểm cuối kỳ/điểm tích lũy hoặc biến hệ quả vào đặc trưng rồi báo AUC rất cao.
- Chuẩn hóa/impute trên toàn bộ dữ liệu trước khi split; xem test nhiều lần để chỉnh mô hình.
- Dùng accuracy với dữ liệu mất cân bằng.
- Chọn ngưỡng nhãn theo phân bố để "đẹp" số ca dương mà không ghi rõ là giả định.
- Bỏ hẳn biến nhạy cảm khỏi dữ liệu (mất khả năng audit công bằng) thay vì chỉ loại khỏi mô hình.
- Trình bày khuyến nghị can thiệp như kết luận khi dữ liệu không có thông tin can thiệp.

## Khắc phục sự cố
- Thiếu thư viện: `pip install pandas numpy scikit-learn scipy statsmodels matplotlib openpyxl`.
- `adjusted_logit` báo lỗi (tách biệt hoàn toàn/đa cộng tuyến): bỏ biến gây lỗi hoặc gộp mức hiếm; phần còn lại vẫn chạy.
- Cột mục tiêu phân loại nhiều lớp: dùng `"type": "classes"` với `positive_classes`.
- Ít hơn khoảng 50 ca dương: báo trước rằng ước lượng không ổn định; cân nhắc chỉ làm mô tả và chẩn đoán.
