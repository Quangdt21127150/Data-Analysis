# n02-skills - marketplace của nhóm N02

Chứa plugin `edu-analytics` với skill `student-risk-screening`: sàng lọc người học cần hỗ trợ từ dữ liệu điểm/LMS/khảo sát
theo quy trình có trách nhiệm (profiling → kiểm soát rò rỉ → chẩn đoán → mô hình so với baseline → công bằng → đánh đổi ngưỡng → báo cáo).

## Cài vào Claude Code
```bash
# giải nén n02-skills-marketplace.zip, rồi trong Claude Code:
/plugin marketplace add ./n02-skills-marketplace
/plugin install edu-analytics@n02-skills
# hoặc từ terminal:
claude plugin marketplace add ./n02-skills-marketplace
claude plugin install edu-analytics@n02-skills --scope user
```
Skill được gọi tự động khi bạn yêu cầu phân tích dữ liệu sinh viên, hoặc gọi trực tiếp bằng `/edu-analytics:student-risk-screening`.

## Phụ thuộc
Python 3.9+, pandas, numpy, scikit-learn, scipy, statsmodels, matplotlib (openpyxl nếu đọc .xlsx).

Giấy phép: MIT. Dữ liệu test thuộc các tác giả gốc (CC BY 4.0).
