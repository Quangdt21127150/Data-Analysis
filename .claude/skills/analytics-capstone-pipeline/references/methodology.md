# Phương pháp luận và quy tắc diễn giải

Tài liệu này giải thích vì sao quy trình làm như vậy, để người dùng bảo vệ được từng lựa chọn khi bị chất vấn, và để trợ lý diễn giải kết quả đúng mức.

## Mục lục
1. Chu trình tám giai đoạn
2. Kiểm toán và rò rỉ dữ liệu
3. Chẩn đoán
4. Mô hình hóa và đánh giá
5. Năm tiêu chí S1 đến S5 và cách diễn giải
6. Công bằng
7. Ngưỡng thống kê cho SEM và thang đo
8. Cách viết kết luận

## 1. Chu trình tám giai đoạn
init, profile, prepare, prereg, diagnose, model, verify, make_report. Thứ tự này quan trọng: prereg đứng trước model để tiêu chí không bị điều chỉnh theo kết quả; verify đứng sau để đối chiếu mã băm. Khung chung theo chu trình khoa học dữ liệu (Rollins, 2015).

## 2. Kiểm toán và rò rỉ dữ liệu
- **Mã thiếu** (ví dụ điểm bằng 0 nghĩa là chưa có): chuyển thành thiếu rồi loại khỏi mẫu có nhãn. Không điền khuyết nhãn.
- **Cụm giá trị lặp bất thường:** một giá trị nhãn lặp nhiều gấp bội so với trung vị tần suất và trùng giá trị ở một cột liên quan gợi ý giá trị thay thế (mặc định hệ thống). Mẫu chính loại cụm, mẫu B giữ lại; báo cáo cả hai.
- **Rò rỉ:** AUC đơn biến tính ngoài mẫu theo fold kèm gợi ý tên cột (Kaufman và cộng sự, 2012). Một đặc trưng mạnh không đồng nghĩa với rò rỉ; chỉ loại tự động khi cả hai dấu hiệu cùng có.
- **Cỡ mẫu:** EPV (số ca dương trên số đặc trưng) dưới 10 là cảnh báo mạnh (Peduzzi và cộng sự, 1996; Riley và cộng sự, 2019, 2020). Nêu rõ trong hạn chế và dựa vào khoảng tin cậy thay vì ước lượng điểm.

## 3. Chẩn đoán
- Đặc trưng số: xác suất vượt trội (tương đương AUC đơn biến, giải thích trực quan là xác suất một ca dương có giá trị cao hơn một ca âm ngẫu nhiên), kiểm định Mann-Whitney, hiệu chỉnh Holm.
- Đặc trưng phân loại: kiểm định độc lập và tỷ lệ ca dương theo mức với khoảng tin cậy Wilson.
- Hồi quy logistic hiệu chỉnh đồng thời (Wald) cho tỷ số chênh. Giải thích: tỷ số chênh hiệu chỉnh là liên hệ sau khi giữ các đặc trưng còn lại không đổi, không phải tác động nhân quả.
- Khi kết quả đơn biến có ý nghĩa mà hiệu chỉnh không còn ý nghĩa, nói rõ khả năng cộng tuyến hoặc nhiễu.

## 4. Mô hình hóa và đánh giá
- Kiểm định chéo phân tầng lặp 5×10 với Pipeline (điền khuyết, chuẩn hóa, mã hóa, chọn C nằm trong fold) để không rò rỉ từ bước xử lý đặc trưng (Kohavi, 1995; Cawley và Talbot, 2010).
- Mô hình: B0 ngẫu nhiên, B1 baseline một đặc trưng, M1 logistic L2 (mô hình chính, dễ diễn giải), M2 Random Forest, M3 Gradient Boosting, L1 logistic Lasso để rút gọn.
- Khoảng tin cậy bootstrap lấy lại quan sát trên điểm dự báo ngoài mẫu; chênh lệch AUC dùng cùng mẫu lấy lại (ghép cặp) để tận dụng tương quan giữa hai mô hình.
- Báo cáo thêm PR-AUC và precision, recall tại tỷ lệ gắn cờ cố định vì lớp mất cân bằng (Saito và Rehmsmeier, 2015). Đường năng lực gắn cờ trả lời câu hỏi thực tế "cần gắn cờ bao nhiêu phần trăm để bắt được bao nhiêu ca".
- Hiệu chuẩn: độ dốc và Brier (Steyerberg và cộng sự, 2010; Van Calster và cộng sự, 2019).

## 5. Năm tiêu chí và cách diễn giải
| Mã | Điều kiện | Nếu không đạt thì nói |
|---|---|---|
| S1 | AUC và recall đạt ngưỡng tại tỷ lệ gắn cờ đã định | Không đủ để làm công cụ quyết định độc lập |
| S2 | Hơn baseline ít nhất `delta_auc` và cận dưới KTC ghép cặp > 0 | Nhiều biến chưa chứng minh giá trị tăng thêm; quy tắc đơn giản đủ dùng |
| S3 | Giữ không quá 2/3 đặc trưng và AUC giảm không quá dung sai | Khó rút gọn khảo sát |
| S4 | Độ dốc trong [0,8; 1,2] và Brier thấp hơn tỷ lệ nền | Chỉ dùng thứ hạng, không diễn giải điểm như xác suất |
| S5 | Chênh lệch recall giữa nhóm trong ngưỡng và KTC đủ hẹp | Chưa kết luận thay vì kết luận quá mức |

Nhãn S1 có hai dạng: "Đạt (độ tin cậy cao)" khi cận dưới KTC cũng qua ngưỡng, "Đạt (điểm ước lượng)" khi chỉ ước lượng điểm qua. Hai dạng này không nên được gộp trong lời diễn giải. S2 có thể là "Chưa kết luận" khi chênh lệch đủ lớn nhưng khoảng tin cậy chứa 0.

Quy tắc chọn mô hình: giữ M1 trừ khi mô hình cây hơn M1 ít nhất `switch_delta` AUC và cận dưới KTC ghép cặp > 0. Lý do: mô hình đơn giản dễ diễn giải và dễ triển khai; mô hình phức tạp phải chứng minh được lợi ích (Shmueli, 2010).

## 6. Công bằng
Dùng cơ hội bình đẳng: so sánh recall giữa các nhóm tại cùng tỷ lệ gắn cờ (Hardt và cộng sự, 2016; Barocas và cộng sự, 2023). Kết luận chỉ khi KTC chênh lệch hẹp hơn `fair_ci_width`. Nhóm nhỏ thường cho KTC rộng, đó là kết quả trung thực chứ không phải thất bại. Không dùng thuộc tính nhóm làm đặc trưng đầu vào. Bối cảnh giáo dục: Baker và Hawn (2022).

## 7. Ngưỡng thống kê khi có thang đo hoặc SEM
Cronbach's Alpha > 0,7; hệ số tải nhân tố > 0,5; AVE > 0,5; CR > 0,7; RMSEA < 0,08; CFI và TLI > 0,9. Khi dữ liệu lệch, dùng ước lượng hợp lý cực đại vững (robust ML) hoặc biến đổi log kèm lập luận. Luôn trình bày tường minh các chỉ số này và hệ số đường dẫn.

## 8. Cách viết kết luận
- Nêu số tiêu chí đạt trên năm, rồi nêu từng tiêu chí với bằng chứng và khoảng tin cậy.
- Phân biệt "chưa đạt" (có bằng chứng không đạt) với "chưa kết luận" (bằng chứng chưa đủ).
- Hàm ý thực hành phải tương xứng với bằng chứng; kết quả liên hệ không được viết thành khuyến nghị can thiệp nhân quả (Hernán và Robins, 2020).
- Dữ liệu tự khai: nêu sai lệch báo cáo và sai lệch phương pháp chung (Podsakoff và cộng sự, 2003).
- Kết thúc bằng bước kỹ thuật tiếp theo cụ thể (xác nhận ngưỡng, thu thập dữ liệu dọc, kiểm định ngoài, thí điểm có đối chứng).
