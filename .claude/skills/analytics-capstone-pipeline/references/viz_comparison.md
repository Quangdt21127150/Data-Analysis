# So sánh công cụ trực quan hóa và mẫu prompt Data Formulator v2

Dùng khi người dùng muốn thực nghiệm biểu đồ đa công cụ cho một chương thực nghiệm. Quy trình chuẩn đã xuất hình bằng mã thuần (matplotlib) trong `figures/`; phần này giúp đối chiếu với Tableau và Microsoft Research Data Formulator v2.

## Khung tiêu chí chọn "Best Visuals/Insights"
| Tiêu chí | Câu hỏi kiểm tra | Thang điểm gợi ý (1 đến 5) |
|---|---|---|
| 1. Độ sâu của insight | Hình có làm lộ quan hệ ẩn hoặc phi tuyến mà bảng số không cho thấy ngay không | |
| 2. Thẩm mỹ và chuẩn mực học thuật | Nhãn trục, đơn vị, khoảng tin cậy, màu phân biệt được, đưa vào luận văn có đạt không | |
| 3. Tương tác và tích hợp | Có lọc, tooltip, nhúng được vào Streamlit hoặc Dash, tái lập được bằng mã không | |

Quy trình: cùng một câu hỏi phân tích, tạo ba phiên bản, chấm điểm theo bảng, chọn hình điểm cao nhất cho từng câu hỏi, rồi viết phần biện luận cho chương thực nghiệm dựa trên hình thắng. Ghi rõ ai chấm và tiêu chí chấm để tránh cảm tính. Với hình có khoảng tin cậy hoặc kiểm định, mã thuần thường thắng tiêu chí 2 và 3; công cụ kéo thả thường nhanh hơn ở khâu khám phá; Data Formulator mạnh khi cần tạo cột dẫn xuất và biến đổi dữ liệu bằng ngôn ngữ tự nhiên.

## Mẫu prompt cho Data Formulator v2
Chuẩn bị: nạp `data/prepared_primary.csv` (hoặc tệp tương đương trong thư mục đầu ra). Mỗi prompt nên nêu rõ trường dữ liệu, nhóm và loại hình.

1. Thiết lập ràng buộc dữ liệu: "Chỉ dùng các dòng trong mẫu chính. Tạo cột `nhom_can_chu_y` bằng 1 nếu `<cột nhãn>` thỏa điều kiện nhãn, ngược lại 0."
2. Biểu đồ đa biến lồng nhau: "Vẽ cột nhóm: trục x là `<đặc trưng phân loại>`, trục y là tỷ lệ `nhom_can_chu_y`, tách theo `<đặc trưng thứ hai>` (facet), thêm đường tỷ lệ nền."
3. Bóc tách động: "Chia `<đặc trưng số>` thành 5 phân vị, tính tỷ lệ `nhom_can_chu_y` mỗi phân vị, vẽ đường kèm số quan sát mỗi phân vị."
4. Kiểm tra tương tác: "Tính tỷ lệ `nhom_can_chu_y` theo cặp (`<đặc trưng A>` tầm trung/thấp/cao, `<đặc trưng B>`) và vẽ bản đồ nhiệt."

Sau khi xuất, ghi lại prompt đã dùng và hình kết quả; nếu cần tích hợp ứng dụng, tái tạo bằng mã thuần (matplotlib hoặc plotly) từ cùng bảng dữ liệu để bảo đảm tái lập.
