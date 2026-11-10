# Data profile: sape_students_performance.xlsx

- Kích thước: 1194 dòng × 31 cột; SHA-256 `04ebaf9f3a047afe…`
- Dòng trùng hoàn toàn: 0; ô khuyết: 1

## Biến mục tiêu
```
{
 "type": "numeric",
 "describe": {
  "count": 1194.0,
  "mean": 3.166,
  "std": 0.75,
  "min": 0.0,
  "25%": 2.9,
  "50%": 3.21,
  "75%": 3.67,
  "max": 4.0
 },
 "zeros": 39,
 "quantiles_of_positive": {
  "q5": 2.51,
  "q10": 2.65,
  "q15": 2.77,
  "q20": 2.87,
  "q25": 2.955
 }
}
```

## Cờ chất lượng và vai trò gợi ý

| Cột | Kiểu | Unique | Khuyết | Cờ |
|---|---|---|---|---|
| University Admission year | int64 | 11 | 0 | - |
| Gender | str | 2 | 0 | thuộc tính nhạy cảm (gender) |
| Age | int64 | 10 | 0 | thuộc tính nhạy cảm (age) |
| H.S.C passing year | int64 | 12 | 0 | - |
| Program | str | 1 | 0 | hằng số |
| Current Semester | int64 | 22 | 0 | - |
| Do you have meritorious scholarship ? | str | 2 | 0 | tên gợi ý biến kết quả/hệ quả (scholarship) - kiểm tra thời điểm phát sinh |
| Do you use University transportation? | str | 2 | 0 | - |
| How many hour do you study daily? | int64 | 12 | 0 | - |
| How many times do you seat for study in a day? | int64 | 8 | 0 | - |
| What is your preferable learning mode? | str | 2 | 0 | - |
| Do you use smart phone? | str | 2 | 0 | - |
| Do you have personal Computer? | str | 2 | 0 | - |
| How many hour do you spent daily in social media? | int64 | 16 | 0 | - |
| Status of your English language proficiency | str | 3 | 0 | - |
| Average attendance on class | object | 66 | 0 | cột số bị lẫn chuỗi: ['94-98']; 1 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0 |
| Did you ever fall in probation? | str | 2 | 0 | tên gợi ý biến kết quả/hệ quả (probation) - kiểm tra thời điểm phát sinh |
| Did you ever got suspension? | str | 2 | 0 | tên gợi ý biến kết quả/hệ quả (suspension) - kiểm tra thời điểm phát sinh |
| Do you attend in teacher consultancy for any kind of academical problems? | str | 2 | 0 | tên gợi ý biến kết quả/hệ quả (consult) - kiểm tra thời điểm phát sinh |
| What are the skills do you have ? | str | 55 | 1 | văn bản tự do / phân loại lực lượng cao (55 mức) - gom nhóm hoặc loại |
| How many hour do you spent daily on your skill development? | int64 | 12 | 0 | - |
| What is you interested area? | str | 25 | 0 | văn bản tự do / phân loại lực lượng cao (25 mức) - gom nhóm hoặc loại |
| What is your relationship status? | str | 5 | 0 | thuộc tính nhạy cảm (relationship) |
| Are you engaged with any co-curriculum activities? | str | 2 | 0 | - |
| With whom you are living with? | str | 2 | 0 | thuộc tính nhạy cảm (living with) |
| Do you have any health issues? | str | 4 | 0 | thuộc tính nhạy cảm (health) |
| What was your previous SGPA? | float64 | 249 | 0 | dồn đống: giá trị 2.68 chiếm 144/1194 (gấp 3.7 lần giá trị kế tiếp) - kiểm tra điền khuyết; liên hệ rất mạnh với nhãn (AUC đơn biến 0.88) - nghi rò rỉ |
| Do you have any physical disabilities? | str | 2 | 0 | thuộc tính nhạy cảm (disab) |
| What is your current CGPA? | float64 | 188 | 0 | dồn đống: giá trị 3.15 chiếm 158/1194 (gấp 4.1 lần giá trị kế tiếp) - kiểm tra điền khuyết |
| How many Credit did you have completed? | int64 | 130 | 0 | dồn đống: giá trị 11 chiếm 161/1194 (gấp 3.4 lần giá trị kế tiếp) - kiểm tra điền khuyết |
| What is your monthly family income? | int64 | 137 | 0 | thuộc tính nhạy cảm (income, family) |

## Vai trò gợi ý (cần người phân tích xác nhận)
```
{
 "features": {
  "numeric": [
   "University Admission year",
   "H.S.C passing year",
   "Current Semester",
   "How many hour do you study daily?",
   "How many times do you seat for study in a day?",
   "How many hour do you spent daily in social media?",
   "Average attendance on class",
   "How many hour do you spent daily on your skill development?",
   "How many Credit did you have completed?"
  ],
  "categorical": [
   "Do you use University transportation?",
   "What is your preferable learning mode?",
   "Do you use smart phone?",
   "Do you have personal Computer?",
   "Status of your English language proficiency",
   "Are you engaged with any co-curriculum activities?"
  ]
 },
 "exclude": {
  "leakage_candidates": [
   "Do you have meritorious scholarship ?",
   "Did you ever fall in probation?",
   "Did you ever got suspension?",
   "Do you attend in teacher consultancy for any kind of academical problems?",
   "What was your previous SGPA?"
  ],
  "sensitive": [
   "Gender",
   "Age",
   "What is your relationship status?",
   "With whom you are living with?",
   "Do you have any health issues?",
   "Do you have any physical disabilities?",
   "What is your monthly family income?"
  ],
  "constant_or_id": [
   "Program"
  ],
  "free_text": [
   "What are the skills do you have ?",
   "What is you interested area?"
  ]
 },
 "fixes": {
  "range_to_mid": [
   "Average attendance on class"
  ],
  "missing_codes": {}
 },
 "suspect_label_rules": [
  {
   "What is your current CGPA?": 3.15,
   "What was your previous SGPA?": 2.68,
   "_evidence": "140/158 dòng có What is your current CGPA? = 3.15 đồng thời What was your previous SGPA? = 2.68"
  }
 ]
}
```