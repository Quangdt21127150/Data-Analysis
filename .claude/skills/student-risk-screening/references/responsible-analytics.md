# Phân tích có trách nhiệm với dữ liệu người học

## Chín nguyên tắc (áp dụng từ đầu, không chờ cuối dự án)
| Nguyên tắc | Cách thể hiện trong phân tích |
|---|---|
| Purpose limitation | Chỉ dùng dữ liệu cho quyết định hỗ trợ học tập đã nêu |
| Data minimization | Loại biến không cần; đề xuất bộ tín hiệu rút gọn |
| Privacy | Dữ liệu ẩn danh/giả danh; chỉ báo cáo tổng hợp; không đưa dữ liệu dòng lên công cụ AI công cộng |
| Fairness | Không dùng biến nhạy cảm làm đặc trưng; kiểm định recall/tỷ lệ gắn cờ theo nhóm kèm CI |
| Transparency | Công bố nguồn, version, Change Log, cả kết quả phủ định |
| Explainability | Mô hình giải thích được; reason code trung tính |
| Accountability | Ghi ai quyết định gì; nhật ký dùng AI |
| Human oversight | Con người phê duyệt mọi hành động hướng tới người học |
| Auditability | Pipeline tái lập từ raw (SHA-256), seed cố định, log biến đổi |

## Ngôn ngữ báo cáo
- Dùng "liên hệ với", "khác biệt giữa", "gắn với"; tránh "gây ra", "dẫn đến", "tác động" khi dữ liệu là quan sát.
- Dùng "sinh viên cần hỗ trợ thêm về ..." thay vì "sinh viên yếu", "sinh viên có vấn đề".
- Reason code mô tả hành vi/nhu cầu: "chuyên cần thấp hơn mức chung của khóa", không mô tả năng lực hay hoàn cảnh.
- Phân biệt "không thấy bằng chứng" với "không có dữ liệu để kiểm tra".

## Diễn giải mô hình sàng lọc
- Recall tại năng lực can thiệp quan trọng hơn accuracy; luôn kèm precision và tỷ lệ gắn cờ.
- Lift = recall / tỷ lệ gắn cờ: cho biết danh sách tốt hơn chọn ngẫu nhiên bao nhiêu lần.
- Nếu mô hình không vượt baseline một biến, khuyến nghị dùng luật đơn giản (dễ giải thích) hoặc thu thập dữ liệu tốt hơn.
- Điểm từ mô hình class_weight cân bằng thường bị thổi phồng; nếu cần xác suất thật phải hiệu chỉnh lại.
- Chênh lệch công bằng ở biến không có trong mô hình cho thấy biến đại diện gián tiếp (ví dụ tuổi qua học kỳ, nơi ở qua chuyên cần).

## Cổng phê duyệt đề xuất cho triển khai
1. Danh sách gắn cờ chỉ hiển thị cho cố vấn có thẩm quyền; giảng viên chỉ nhận thông tin tổng hợp.
2. Cố vấn xem reason code và quyết định có liên hệ hay không; không gửi thông điệp tự động.
3. Theo dõi mỗi kỳ: recall, tỷ lệ gắn cờ và chênh lệch theo nhóm; kiểm định lại khi đổi chương trình/cơ sở.
