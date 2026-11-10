# Data profile: student-por.csv

- Kích thước: 649 dòng × 33 cột; SHA-256 `a7594a11d7771c0e…`
- Dòng trùng hoàn toàn: 0; ô khuyết: 0

## Biến mục tiêu
```
{
 "type": "numeric",
 "describe": {
  "count": 649.0,
  "mean": 11.906,
  "std": 3.231,
  "min": 0.0,
  "25%": 10.0,
  "50%": 12.0,
  "75%": 14.0,
  "max": 19.0
 },
 "zeros": 15,
 "quantiles_of_positive": {
  "q5": 8.0,
  "q10": 9.0,
  "q15": 10.0,
  "q20": 10.0,
  "q25": 10.0
 }
}
```

## Cờ chất lượng và vai trò gợi ý

| Cột | Kiểu | Unique | Khuyết | Cờ |
|---|---|---|---|---|
| school | str | 2 | 0 | - |
| sex | str | 2 | 0 | thuộc tính nhạy cảm (sex) |
| age | int64 | 8 | 0 | thuộc tính nhạy cảm (age) |
| address | str | 2 | 0 | thuộc tính nhạy cảm (address) |
| famsize | str | 2 | 0 | thuộc tính nhạy cảm (famsize) |
| Pstatus | str | 2 | 0 | thuộc tính nhạy cảm (pstatus) |
| Medu | int64 | 5 | 0 | thuộc tính nhạy cảm (medu) |
| Fedu | int64 | 5 | 0 | thuộc tính nhạy cảm (fedu) |
| Mjob | str | 5 | 0 | thuộc tính nhạy cảm (mjob) |
| Fjob | str | 5 | 0 | thuộc tính nhạy cảm (fjob) |
| reason | str | 4 | 0 | - |
| guardian | str | 3 | 0 | thuộc tính nhạy cảm (guardian) |
| traveltime | int64 | 4 | 0 | - |
| studytime | int64 | 4 | 0 | - |
| failures | int64 | 4 | 0 | dồn đống: giá trị 0 chiếm 549/649 (gấp 7.8 lần giá trị kế tiếp) - kiểm tra điền khuyết |
| schoolsup | str | 2 | 0 | - |
| famsup | str | 2 | 0 | - |
| paid | str | 2 | 0 | - |
| activities | str | 2 | 0 | - |
| nursery | str | 2 | 0 | - |
| higher | str | 2 | 0 | - |
| internet | str | 2 | 0 | - |
| romantic | str | 2 | 0 | thuộc tính nhạy cảm (romantic) |
| famrel | int64 | 5 | 0 | - |
| freetime | int64 | 5 | 0 | - |
| goout | int64 | 5 | 0 | - |
| Dalc | int64 | 5 | 0 | dồn đống: giá trị 1 chiếm 451/649 (gấp 3.7 lần giá trị kế tiếp) - kiểm tra điền khuyết; thuộc tính nhạy cảm (dalc) |
| Walc | int64 | 5 | 0 | thuộc tính nhạy cảm (walc) |
| health | int64 | 5 | 0 | thuộc tính nhạy cảm (health) |
| absences | int64 | 24 | 0 | - |
| G1 | int64 | 17 | 0 | 1 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; liên hệ rất mạnh với nhãn (AUC đơn biến 0.94) - nghi rò rỉ |
| G2 | int64 | 16 | 0 | 7 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0; liên hệ rất mạnh với nhãn (AUC đơn biến 0.96) - nghi rò rỉ |
| G3 | int64 | 17 | 0 | 15 giá trị 0 ở cột điểm/chuyên cần - có thể là khuyết được mã hóa 0 |

## Vai trò gợi ý (cần người phân tích xác nhận)
```
{
 "features": {
  "numeric": [
   "traveltime",
   "studytime",
   "failures",
   "famrel",
   "freetime",
   "goout",
   "absences"
  ],
  "categorical": [
   "school",
   "reason",
   "schoolsup",
   "famsup",
   "paid",
   "activities",
   "nursery",
   "higher",
   "internet"
  ]
 },
 "exclude": {
  "leakage_candidates": [
   "G1",
   "G2"
  ],
  "sensitive": [
   "sex",
   "age",
   "address",
   "famsize",
   "Pstatus",
   "Medu",
   "Fedu",
   "Mjob",
   "Fjob",
   "guardian",
   "romantic",
   "Dalc",
   "Walc",
   "health"
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