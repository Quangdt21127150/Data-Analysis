# Data profile: students_dropout.csv

- Kích thước: 4424 dòng × 37 cột; SHA-256 `3ef126de5cefff26…`
- Dòng trùng hoàn toàn: 0; ô khuyết: 0

## Biến mục tiêu
```
{
 "type": "categorical",
 "value_counts": {
  "Graduate": 2209,
  "Dropout": 1421,
  "Enrolled": 794
 }
}
```

## Cờ chất lượng và vai trò gợi ý

| Cột | Kiểu | Unique | Khuyết | Cờ |
|---|---|---|---|---|
| Marital status | int64 | 6 | 0 | dồn đống: giá trị 1 chiếm 3919/4424 (gấp 10.3 lần giá trị kế tiếp) - kiểm tra điền khuyết; thuộc tính nhạy cảm (marital) |
| Application mode | int64 | 18 | 0 | - |
| Application order | int64 | 8 | 0 | dồn đống: giá trị 1 chiếm 3026/4424 (gấp 5.5 lần giá trị kế tiếp) - kiểm tra điền khuyết |
| Course | int64 | 17 | 0 | - |
| Daytime/evening attendance | int64 | 2 | 0 | 483 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0 |
| Previous qualification | int64 | 17 | 0 | dồn đống: giá trị 1 chiếm 3717/4424 (gấp 17.0 lần giá trị kế tiếp) - kiểm tra điền khuyết |
| Previous qualification (grade) | float64 | 101 | 0 | tên gợi ý biến kết quả/hệ quả (grade) - kiểm tra thời điểm phát sinh |
| Nacionality | int64 | 21 | 0 | dồn đống: giá trị 1 chiếm 4314/4424 (gấp 113.5 lần giá trị kế tiếp) - kiểm tra điền khuyết; thuộc tính nhạy cảm (nacional) |
| Mother's qualification | int64 | 29 | 0 | thuộc tính nhạy cảm (mother) |
| Father's qualification | int64 | 34 | 0 | thuộc tính nhạy cảm (father) |
| Mother's occupation | int64 | 32 | 0 | thuộc tính nhạy cảm (mother) |
| Father's occupation | int64 | 46 | 0 | thuộc tính nhạy cảm (father) |
| Admission grade | float64 | 620 | 0 | tên gợi ý biến kết quả/hệ quả (grade) - kiểm tra thời điểm phát sinh |
| Displaced | int64 | 2 | 0 | thuộc tính nhạy cảm (displaced) |
| Educational special needs | int64 | 2 | 0 | thuộc tính nhạy cảm (special need) |
| Debtor | int64 | 2 | 0 | thuộc tính nhạy cảm (debtor) |
| Tuition fees up to date | int64 | 2 | 0 | thuộc tính nhạy cảm (tuition) |
| Gender | int64 | 2 | 0 | thuộc tính nhạy cảm (gender) |
| Scholarship holder | int64 | 2 | 0 | 3325 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (scholarship) - kiểm tra thời điểm phát sinh |
| Age at enrollment | int64 | 46 | 0 | thuộc tính nhạy cảm (age) |
| International | int64 | 2 | 0 | thuộc tính nhạy cảm (nation, international) |
| Curricular units 1st sem (credited) | int64 | 21 | 0 | dồn đống: giá trị 0 chiếm 3847/4424 (gấp 40.9 lần giá trị kế tiếp) - kiểm tra điền khuyết; 3847 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (credited) - kiểm tra thời điểm phát sinh |
| Curricular units 1st sem (enrolled) | int64 | 23 | 0 | - |
| Curricular units 1st sem (evaluations) | int64 | 35 | 0 | 349 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (evaluations) - kiểm tra thời điểm phát sinh |
| Curricular units 1st sem (approved) | int64 | 23 | 0 | 718 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (approved) - kiểm tra thời điểm phát sinh |
| Curricular units 1st sem (grade) | float64 | 805 | 0 | dồn đống: giá trị 0.0 chiếm 718/4424 (gấp 3.5 lần giá trị kế tiếp) - kiểm tra điền khuyết; 718 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (grade) - kiểm tra thời điểm phát sinh |
| Curricular units 1st sem (without evaluations) | int64 | 11 | 0 | dồn đống: giá trị 0 chiếm 4130/4424 (gấp 27.0 lần giá trị kế tiếp) - kiểm tra điền khuyết; 4130 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (evaluations) - kiểm tra thời điểm phát sinh |
| Curricular units 2nd sem (credited) | int64 | 19 | 0 | dồn đống: giá trị 0 chiếm 3894/4424 (gấp 36.4 lần giá trị kế tiếp) - kiểm tra điền khuyết; 3894 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (2nd sem, credited) - kiểm tra thời điểm phát sinh |
| Curricular units 2nd sem (enrolled) | int64 | 22 | 0 | 180 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (2nd sem) - kiểm tra thời điểm phát sinh |
| Curricular units 2nd sem (evaluations) | int64 | 30 | 0 | 401 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (evaluations, 2nd sem) - kiểm tra thời điểm phát sinh |
| Curricular units 2nd sem (approved) | int64 | 20 | 0 | 870 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (approved, 2nd sem) - kiểm tra thời điểm phát sinh |
| Curricular units 2nd sem (grade) | float64 | 786 | 0 | dồn đống: giá trị 0.0 chiếm 870/4424 (gấp 5.1 lần giá trị kế tiếp) - kiểm tra điền khuyết; 870 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (grade, 2nd sem) - kiểm tra thời điểm phát sinh |
| Curricular units 2nd sem (without evaluations) | int64 | 10 | 0 | dồn đống: giá trị 0 chiếm 4142/4424 (gấp 29.6 lần giá trị kế tiếp) - kiểm tra điền khuyết; 4142 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; tên gợi ý biến kết quả/hệ quả (evaluations, 2nd sem) - kiểm tra thời điểm phát sinh |
| Unemployment rate | float64 | 10 | 0 | - |
| Inflation rate | float64 | 9 | 0 | - |
| GDP | float64 | 10 | 0 | - |
| Target | str | 3 | 0 | - |

## Vai trò gợi ý (cần người phân tích xác nhận)
```
{
 "features": {
  "numeric": [
   "Application mode",
   "Application order",
   "Course",
   "Previous qualification",
   "Curricular units 1st sem (enrolled)",
   "Unemployment rate",
   "Inflation rate",
   "GDP"
  ],
  "categorical": [
   "Daytime/evening attendance"
  ]
 },
 "exclude": {
  "leakage_candidates": [
   "Previous qualification (grade)",
   "Admission grade",
   "Scholarship holder",
   "Curricular units 1st sem (credited)",
   "Curricular units 1st sem (evaluations)",
   "Curricular units 1st sem (approved)",
   "Curricular units 1st sem (grade)",
   "Curricular units 1st sem (without evaluations)",
   "Curricular units 2nd sem (credited)",
   "Curricular units 2nd sem (enrolled)",
   "Curricular units 2nd sem (evaluations)",
   "Curricular units 2nd sem (approved)",
   "Curricular units 2nd sem (grade)",
   "Curricular units 2nd sem (without evaluations)"
  ],
  "sensitive": [
   "Marital status",
   "Nacionality",
   "Mother's qualification",
   "Father's qualification",
   "Mother's occupation",
   "Father's occupation",
   "Displaced",
   "Educational special needs",
   "Debtor",
   "Tuition fees up to date",
   "Gender",
   "Age at enrollment",
   "International"
  ],
  "constant_or_id": [],
  "free_text": []
 },
 "fixes": {
  "range_to_mid": [],
  "missing_codes": {}
 },
 "suspect_label_rules": []
}
```