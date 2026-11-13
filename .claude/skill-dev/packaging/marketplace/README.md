# n02-skills - marketplace của nhóm N02

Chứa plugin `edu-analytics` (1.2.0) với hai skill:
- `student-risk-screening`: sàng lọc người học cần hỗ trợ từ dữ liệu điểm/LMS/khảo sát theo quy trình có trách nhiệm.
- `analytics-capstone-pipeline`: quy trình đồ án trọn gói trên bảng dữ liệu bất kỳ, dựng báo cáo Word, kịch bản và dàn ý slide.

## Cài vào Claude Code
```bash
# giải nén n02-skills-marketplace.zip, rồi trong Claude Code:
/plugin marketplace add ./n02-skills-marketplace
/plugin install edu-analytics@n02-skills
# hoặc từ terminal:
claude plugin marketplace add ./n02-skills-marketplace
claude plugin install edu-analytics@n02-skills --scope user
```
Skill được gọi tự động theo yêu cầu, hoặc gọi trực tiếp bằng `/edu-analytics:student-risk-screening` và `/edu-analytics:analytics-capstone-pipeline`.

## Phụ thuộc
Python 3.9+, pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib (openpyxl nếu đọc .xlsx); python-docx cho báo cáo Word.

Giấy phép: MIT. Dữ liệu test thuộc các tác giả gốc (CC BY 4.0).
