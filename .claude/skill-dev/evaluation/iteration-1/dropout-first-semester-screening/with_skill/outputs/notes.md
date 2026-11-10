# Ghi chú quyết định phân tích (Change Log)

## Khung quyết định (Bước 1)
- Người dùng: Phòng CTSV / cố vấn học tập. Quyết định: chọn sinh viên để cố vấn gặp sớm (hỗ trợ, không xử lý kỷ luật).
- Đơn vị phân tích: 1 dòng = 1 sinh viên (khóa trước). Không có cột ID → công cụ tạo `_rid` theo thứ tự dòng.
- Mốc dự báo: **ngay sau khi có kết quả học kỳ 1 năm nhất**. Chỉ dùng thông tin có trước hoặc tại mốc này.
- Kết quả: `Target == "Dropout"` là dương. **Giả định**: `Enrolled` (còn đang học khi kết thúc thu thập) và `Graduate` là âm.
  Chạy thêm kịch bản độ nhạy loại `Enrolled` khỏi nhãn chính (`config_sensitivity_no_enrolled.json`).
- Năng lực can thiệp: 30% (capacity = 0.30); kịch bản phụ 15%.
- Tiêu chí thành công đặt trước (mặc định của skill): AUC ≥ 0.70; recall ≥ 60% khi gắn cờ 30%; vượt baseline một biến ≥ 0.02 AUC; chênh lệch recall giữa nhóm ≤ 10 điểm %.

## Biến dùng làm đặc trưng (13)
- Hồ sơ tuyển sinh (có trước khi nhập học): Application mode, Application order, Course, Daytime/evening attendance, Previous qualification, Previous qualification (grade), Admission grade.
  Profile gắn cờ "grade" cho hai biến điểm đầu vào, nhưng chúng phát sinh **trước** mốc dự báo → giữ.
- Kết quả học kỳ 1 (có tại mốc dự báo): Curricular units 1st sem (credited, enrolled, evaluations, approved, grade, without evaluations).
  Profile gắn cờ "nghi rò rỉ", nhưng theo đúng kịch bản sử dụng, dữ liệu HK1 có sẵn khi lập danh sách → giữ.
- Mã số dạng danh mục (Application mode, Course, Previous qualification, Daytime/evening) để ở `categorical`.
- Lưu ý: `Curricular units 1st sem (grade)` = 0 ở 718 dòng tương ứng với 0 học phần đạt (điểm TB không xác định). Giữ nguyên vì thông tin "không đạt học phần nào" đã nằm ở biến `approved`; ghi nhận là giới hạn.
- Tên cột gốc `Daytime/evening attendance\t` có ký tự tab; công cụ tự strip tên cột nên config dùng tên đã strip.

## Biến bị loại và lý do
### Rò rỉ (ghi nhận sau mốc dự báo)
- Toàn bộ 6 biến `Curricular units 2nd sem (...)`: kết quả học kỳ 2 chưa tồn tại khi lập danh sách sau HK1; ngoài ra sinh viên đã bỏ học thì HK2 = 0, gần như mã hóa luôn nhãn.

### Nhạy cảm (không làm đặc trưng, giữ lại để kiểm định công bằng)
- Gender, Age at enrollment, Marital status, Nacionality, International, Displaced, Educational special needs, Mother's/Father's qualification, Mother's/Father's occupation: nhân khẩu học / hoàn cảnh gia đình / sức khỏe.
- Debtor, Tuition fees up to date: tình trạng tài chính (nợ học phí). Ngoài ra **thời điểm ghi nhận không rõ** (có thể là trạng thái cuối kỳ/cuối năm, sau mốc) → vừa nhạy cảm vừa nghi rò rỉ.
- Scholarship holder: tình trạng tài chính; thời điểm ghi nhận không rõ và có thể là học bổng thành tích (hệ quả của kết quả học tập) → loại.
- `fairness_audit`: Gender, Age at enrollment (chia theo trung vị: ≤ 20 / > 20), Debtor.

### Khác
- Unemployment rate, Inflation rate, GDP: chỉ có ~10 giá trị, mỗi giá trị tương ứng một năm/khóa (định danh khóa học). Với một khóa mới, biến là hằng số → không giúp xếp hạng trong khóa, và mô hình có thể học hiệu ứng khóa không lặp lại. Loại.

## Phân tích bổ sung (thư mục `supplementary/`, chỉ trên train OOF)
- So sánh chênh lệch công bằng của baseline 1 biến vs LR theo tuổi/giới.
- Tỷ lệ bỏ học theo số học phần đạt HK1.
- Kịch bản tham khảo "chỉ tiêu 30% riêng cho mỗi nhóm tuổi".
- Phân bố trạng thái thật trong nhóm bị gắn cờ.

## Quy tắc đã tuân thủ
- Split phân tầng 80/20 seed 2026 trước mọi phép fit; tiền xử lý trong Pipeline; chọn mô hình theo CV (5 fold × 5 lần lặp); test xem một lần.
- Không chọn mô hình hay ngưỡng theo test.
