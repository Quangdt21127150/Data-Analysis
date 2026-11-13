# Các bẫy thường gặp và cách xử lý

Rút từ năm milestone thực tế. Mỗi mục gồm dấu hiệu, vì sao nguy hiểm, và cách xử lý trong quy trình.

## Mục lục
1. Mã thiếu giả dạng giá trị thật
2. Cụm giá trị lặp bất thường
3. Rò rỉ dữ liệu
4. Cỡ mẫu nhỏ và mất cân bằng lớp
5. Dữ liệu tự khai và cắt ngang
6. Baseline lạc quan
7. Điều chỉnh tiêu chí sau khi thấy kết quả
8. Môi trường thiếu thư viện hoặc không có mạng
9. Lỗi trình bày hay gặp

## 1. Mã thiếu giả dạng giá trị thật
Dấu hiệu: giá trị 0 hoặc -1, 99, 999 ở cột điểm hay tuổi. Nguy hiểm vì kéo trung bình và tạo nhãn dương sai (điểm 0 dưới mọi ngưỡng). Xử lý: khai `target.missing_codes`; quy trình chuyển thành thiếu và loại khỏi mẫu có nhãn, ghi số dòng trong nhật ký. Trong đồ án gốc: 39 dòng CGPA bằng 0.

## 2. Cụm giá trị lặp bất thường
Dấu hiệu: một giá trị nhãn xuất hiện hàng trăm lần trong khi trung vị tần suất chỉ vài lần, và các dòng đó cùng một giá trị ở cột liên quan. Gợi ý giá trị thay thế khi nhập liệu. Xử lý: mẫu chính loại cụm (`exclude_repeat_clusters`), mẫu B giữ lại, báo cáo cả hai và nhận định mức nhạy. Trong đồ án gốc: 140 dòng nhãn 3,15 cùng điểm kỳ trước 2,68.

## 3. Rò rỉ dữ liệu
Dấu hiệu: đặc trưng gần như đoán đúng nhãn (AUC đơn biến cao) hoặc tên cột là hệ quả của nhãn. Trong đồ án gốc: điểm kỳ trước có AUC 0,88 vì điểm tích lũy được tính từ chính điểm kỳ. Loại ngay không đủ: phải hỏi người dùng về thời điểm thu thập. Nếu loại, mô hình tụt AUC rõ rệt; đó là kết quả trung thực, không phải lỗi.

## 4. Cỡ mẫu nhỏ và mất cân bằng lớp
Dấu hiệu: EPV dưới 10, dưới 100 ca dương. Xử lý: báo khoảng tin cậy, giảm số fold, tránh mô hình quá linh hoạt; không dùng SMOTE để "tăng" mẫu trong sản phẩm vì làm đẹp số liệu. Với lớp mất cân bằng, đọc recall và precision tại tỷ lệ gắn cờ thay vì chỉ AUC.

## 5. Dữ liệu tự khai và cắt ngang
Nhãn và đặc trưng cùng do người trả lời khai thì tương quan có thể do sai lệch phương pháp chung. Cắt ngang không cho thứ tự thời gian. Xử lý: viết đúng như vậy ở phần hạn chế, không viết hàm ý nhân quả, đề xuất thiết kế dữ liệu dọc.

## 6. Baseline lạc quan
Chọn đặc trưng đơn tốt nhất sau khi nhìn dữ liệu làm baseline thành đối thủ khó vượt và làm S2 đẹp giả tạo theo chiều ngược lại. Xử lý: khai `baseline_feature` theo trực giác nghiệp vụ trước khi chạy. Nếu bỏ trống, quy trình chọn tự động và ghi cảnh báo.

## 7. Điều chỉnh tiêu chí sau khi thấy kết quả
Là lỗi nghiêm trọng nhất về phương pháp. Mã băm kế hoạch bị kiểm tra ở giai đoạn verify. Nếu phải đổi, ghi Change Log, chạy lại từ prereg, nêu rõ trong báo cáo.

## 8. Môi trường thiếu thư viện hoặc không có mạng
Lõi chỉ cần pandas, numpy, scipy, scikit-learn, matplotlib. Thiếu statsmodels: hồi quy logistic Wald được tính bằng cài đặt nội bộ. Thiếu shap, semopy: bỏ qua phần mở rộng, ghi `xai_status.json`, nói rõ với người dùng. Không dùng `pip install` khi mạng tắt. Với bộ dữ liệu lớn, chạy nền và theo dõi nhật ký thay vì chờ đồng bộ.

## 9. Lỗi trình bày hay gặp
- Dấu phẩy thập phân bị đổi thành dấu chấm khi thay thế chuỗi hàng loạt; dùng hàm định dạng số thay vì `replace`.
- Câu bị cắt sai ở dấu hai chấm hoặc chấm phẩy khi tách câu cho kịch bản; chỉ tách ở dấu chấm theo sau là chữ hoa.
- Hình tràn lề hoặc bảng sai tổng độ rộng cột; dùng hàm `widths()` của `make_report.py`.
- Tiêu đề slide nghe gượng; đọc to và viết lại.
