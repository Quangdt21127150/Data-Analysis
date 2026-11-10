# Các quyết định phân tích chính

## Mục tiêu và đánh giá
- Biến mục tiêu nhị phân: Dropout = 1; Enrolled và Graduate = 0. "Enrolled" có kết cục chưa rõ. Kiểm tra độ nhạy: loại nhóm này thì AUC đạt 0,91 (so với 0,88).
- Ngưỡng gắn cờ: 30% sinh viên có điểm rủi ro cao nhất **trong mỗi khóa**, theo giới hạn năng lực của cố vấn. Đây là sàng lọc theo năng lực, không dùng ngưỡng xác suất cố định.
- Khóa (cohort) được suy ra từ 10 tổ hợp duy nhất của (Unemployment rate, Inflation rate, GDP). Các tổ hợp này có cỡ từ 362 đến 571 SV, khớp với giả định mỗi tổ hợp là một năm tuyển sinh.
- Kiểm định leave-one-cohort-out (10 lần) để mô phỏng việc áp dụng cho khóa mới. Khoảng tin cậy 95% tính bằng bootstrap (1.000 lần lặp).
- Mô hình chính: hồi quy logistic (C=0.3, one-hot cho biến mã hóa, gộp các mức có dưới 30 SV, chuẩn hóa biến số). Chọn mô hình này thay vì HistGradientBoosting vì hai mô hình cho kết quả như nhau mà logistic dễ giải thích hơn.
- Mô hình được so với 2 mốc tham chiếu: chỉ dùng dữ liệu tuyển sinh, và quy tắc đơn giản "tỷ lệ môn đạt HK1".

## Các cột bị loại khỏi mô hình chính và lý do
| Cột | Lý do |
|---|---|
| Curricular units 2nd sem (6 cột) | Rò rỉ thời gian: lúc lập danh sách (ngay sau HK1) chưa có dữ liệu này. Chỉ chạy để tham khảo (mô hình E). |
| Debtor, Tuition fees up to date | Không rõ thời điểm ghi nhận, có thể là nhân quả ngược (SV bỏ học thì ngừng đóng học phí). Chạy riêng ở mô hình C: recall 73%. Có thể đưa vào nếu xác nhận dữ liệu có sẵn vào cuối HK1. |
| Gender, Nationality, International | Thuộc tính nhạy cảm: không dùng để chấm điểm, chỉ dùng để kiểm tra công bằng. Chạy riêng ở mô hình D: chỉ thêm khoảng 0,5 điểm recall. |
| Unemployment rate, Inflation rate, GDP | Hằng số trong mỗi khóa nên không giúp xếp hạng trong khóa, và có thể khiến mô hình khớp theo đặc điểm của khóa cũ. Chỉ dùng để xác định khóa. |
| Target | Biến kết cục. |

## Các cột được giữ (có ghi chú)
- Nghề nghiệp và trình độ của cha mẹ, Marital status, Age, Scholarship holder, Displaced, Educational special needs: đều có sẵn từ lúc nhập học. Các cột này là đại diện cho hoàn cảnh kinh tế - xã hội nên được đưa vào kiểm tra công bằng (tuổi, học bổng, displaced). Hệ số theo mã nghề nghiệp không ổn định và không được diễn giải.
- Biến tự tạo từ kết quả HK1: tỷ lệ môn đạt, tỷ lệ môn có dự thi, cờ "không đăng ký môn nào", cờ "không đạt môn nào". Có 180 SV có 0 môn đăng ký ở HK1; với các SV này, các tỷ lệ được điền bằng trung vị và có cờ riêng.

## Dữ liệu
- Đọc file với `sep=";"`, cắt khoảng trắng / ký tự tab trong tên cột ("Daytime/evening attendance\t"), đổi tên "Nacionality" thành "Nationality". Không có giá trị thiếu, không có dòng trùng. File gốc không bị sửa.
