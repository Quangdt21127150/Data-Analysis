# Cấu hình `config.json`

Đường dẫn tương đối được tính từ thư mục chứa file cấu hình.

| Khóa | Bắt buộc | Ý nghĩa |
|---|---|---|
| `project` | không | Tên hiển thị trong báo cáo |
| `data_path` | có | File `.csv` (tự nhận dấu phân cách) hoặc `.xlsx` |
| `sheet` | không | Tên sheet Excel |
| `out_dir` | không | Thư mục kết quả (mặc định `./output`) |
| `id_column` | không | Cột khóa; nếu trống, tạo `_rid` giả danh theo thứ tự dòng |
| `target.column` | có | Cột kết quả |
| `target.type` | có | `threshold_below` (dương nếu < ngưỡng), `threshold_above`, hoặc `classes` |
| `target.threshold` | với threshold | Ngưỡng theo quy chế/nghiệp vụ |
| `target.zero_is_missing` | không | `true` nếu giá trị 0 nghĩa là chưa có kết quả (bị loại khỏi tập nhãn) |
| `target.positive_classes` | với classes | Danh sách nhãn dương, ví dụ `["Dropout"]` |
| `target.sensitivity_thresholds` | không | Các ngưỡng phụ để chạy độ nhạy |
| `features.numeric` / `features.categorical` | có | Đặc trưng hợp lệ tại mốc dự báo. Mã số dạng danh mục (ví dụ mã ngành) để ở `categorical` |
| `exclude.leakage` / `exclude.sensitive` / `exclude.other` | nên có | Biến bị loại kèm lý do trong báo cáo; công cụ dừng nếu một biến vừa là đặc trưng vừa bị loại |
| `fairness_audit` | nên có | 1-3 biến nhạy cảm để kiểm định công bằng (biến số nhiều giá trị được chia theo trung vị) |
| `range_to_mid` | không | Cột có giá trị dạng khoảng "a-b" → lấy trung điểm |
| `missing_codes` | không | `{cột: [mã]}` → NaN (ví dụ chuyên cần 0% không hợp lệ) |
| `valid_ranges` | không | `{cột: [min, max]}` → ngoài khoảng thành NaN |
| `suspect_label_rules` | không | Danh sách luật `{cột: giá trị, ...}` (điều kiện AND, so trên dữ liệu gốc); bản ghi khớp bị loại khỏi nhãn chính |
| `capacity` / `alt_capacity` | không | Tỷ lệ gắn cờ vận hành chính và kịch bản phụ (mặc định 0.30 / 0.15) |
| `seed`, `test_size`, `cv_folds`, `cv_repeats` | không | Mặc định 2026, 0.2, 5, 5 |
| `success` | không | `{auc, recall, max_recall_gap, reduction}` - tiêu chí thành công đặt trước (mặc định 0.70, 0.60, 0.10, 1/3) |

## Ví dụ ngắn

```json
{
  "data_path": "students.csv",
  "target": {"column": "final_score", "type": "threshold_below", "threshold": 5.0, "zero_is_missing": true},
  "features": {"numeric": ["attendance_pct", "quiz_week1_4"], "categorical": ["program"]},
  "exclude": {"leakage": ["midterm", "final_exam"], "sensitive": ["gender", "income"], "other": ["student_name"]},
  "fairness_audit": ["gender"],
  "capacity": 0.2
}
```
