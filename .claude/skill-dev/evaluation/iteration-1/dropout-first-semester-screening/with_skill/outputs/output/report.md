# Báo cáo phân tích sàng lọc người học: Sàng lọc nguy cơ bỏ học sau kết quả học kỳ 1 năm nhất

> Sinh tự động bởi skill education-data-analytics (10/11/2026). Các con số lấy từ `results.json`; phần diễn giải cần người phân tích rà soát.

## 1. Dữ liệu và nhãn

- Nguồn: `students_dropout.csv` (SHA-256 `3ef126de5cefff26…`), 4424 dòng.
- Nhãn dương: **Target ∈ ['Dropout']**; tập có nhãn 4424 dòng, 1421 ca dương (tỷ lệ nền 32.1%).
- Trạng thái nhãn: {'observed': 4424}. Train 3539 (1137 dương) / test 885 (284 dương), phân tầng, seed 2026.
- 13 đặc trưng hợp lệ; biến bị loại: leakage: Curricular units 2nd sem (credited), Curricular units 2nd sem (enrolled), Curricular units 2nd sem (evaluations), Curricular units 2nd sem (approved), Curricular units 2nd sem (grade), Curricular units 2nd sem (without evaluations); sensitive: Marital status, Nacionality, Mother's qualification, Father's qualification, Mother's occupation, Father's occupation, Displaced, Educational special needs, Debtor, Tuition fees up to date, Scholarship holder, Gender, Age at enrollment, International; other: Unemployment rate, Inflation rate, GDP.

### Nhật ký biến đổi

| Bước | Luật | Số dòng |
|---|---|---|
| key | tạo khóa giả danh _rid theo thứ tự dòng |  |
| label | {"column": "Target", "type": "classes", "positive_classes": ["Dropout"]} | 4424 |

## 2. Chẩn đoán (chỉ trên train; hiệu chỉnh Holm)

| Biến | Kiểm định | Hiệu ứng | p (Holm) | Có ý nghĩa |
|---|---|---|---|---|
| Curricular units 1st sem (approved) | Mann-Whitney U | rank-biserial r = -0.624 | 1.19e-202 | Có |
| Curricular units 1st sem (grade) | Mann-Whitney U | rank-biserial r = -0.541 | 5.92e-149 | Có |
| Application mode | Chi-square | Cramér's V = 0.296 | 1.83e-55 | Có |
| Course | Chi-square | Cramér's V = 0.265 | 8.19e-43 | Có |
| Previous qualification | Chi-square | Cramér's V = 0.215 | 6e-26 | Có |
| Curricular units 1st sem (enrolled) | Mann-Whitney U | rank-biserial r = -0.196 | 2.15e-22 | Có |
| Application order | Mann-Whitney U | rank-biserial r = -0.095 | 2.49e-07 | Không |
| Admission grade | Mann-Whitney U | rank-biserial r = -0.108 | 1.09e-06 | Có |
| Previous qualification (grade) | Mann-Whitney U | rank-biserial r = -0.101 | 5.76e-06 | Có |
| Daytime/evening attendance | Chi-square | Cramér's V = 0.072 | 7.07e-05 | Không |
| Curricular units 1st sem (without evaluations) | Mann-Whitney U | rank-biserial r = 0.029 | 0.00451 | Không |
| Curricular units 1st sem (evaluations) | Mann-Whitney U | rank-biserial r = -0.055 | 0.0154 | Không |
| Curricular units 1st sem (credited) | Mann-Whitney U | rank-biserial r = 0.001 | 0.942 | Không |

Hồi quy logistic điều chỉnh (pseudo R² = 0.3865; biến số: OR mỗi 1 độ lệch chuẩn; biến phân loại: so với mức phổ biến nhất). Các hạng tử p < 0.05:

- Curricular units 1st sem (approved): OR 0.08 (CI 95% 0.062-0.105)
- Curricular units 1st sem (credited): OR 2.52 (CI 95% 1.949-3.26)
- Course_9853: OR 4.496 (CI 95% 2.681-7.54)
- Curricular units 1st sem (enrolled): OR 2.322 (CI 95% 1.677-3.216)
- Application mode_39: OR 2.282 (CI 95% 1.622-3.212)
- Curricular units 1st sem (without evaluations): OR 0.787 (CI 95% 0.71-0.873)
- Course_9773: OR 2.941 (CI 95% 1.836-4.712)
- Course_9130: OR 4.075 (CI 95% 2.177-7.627)
- Course_9254: OR 2.393 (CI 95% 1.422-4.028)
- Previous qualification_2: OR 6.984 (CI 95% 1.961-24.875)
- Application mode_15: OR 0.178 (CI 95% 0.041-0.775)
- Application mode_7: OR 3.038 (CI 95% 1.129-8.177)
- Application mode_17: OR 1.321 (CI 95% 1.01-1.728)

> Diễn giải: đây là liên hệ trên dữ liệu quan sát, có thể theo chiều ngược hoặc do yếu tố gây nhiễu; không kết luận nhân quả.

## 3. Hiệu năng sàng lọc

Baseline một tín hiệu được chọn trên train: **Curricular units 1st sem (approved)**. Primary theo quy tắc đặt trước: **LR**.

| Mô hình | AUC CV | PR-AUC CV | Recall@30% CV | AUC test [CI 95%] | Recall test @30% |
|---|---|---|---|---|---|
| B0_prior | 0.499 ± 0.000 | 0.321 | 28.9% | - | - |
| B1_best_single | 0.810 ± 0.001 | 0.680 | 65.3% | 0.844 [0.814; 0.869] | 66.2% |
| LR | 0.873 ± 0.001 | 0.802 | 68.6% | 0.877 [0.851; 0.900] | 66.9% |
| RF | 0.858 ± 0.002 | 0.785 | 66.9% | 0.883 [0.857; 0.905] | 70.8% |
| LR_reduced_best | (đường rút gọn) | - | - | 0.877 | 63.7% |

Hiệu chỉnh: xác suất TB 0.4191 so với tỷ lệ nền 0.3213 (Brier 0.1365 vs hằng số 0.2181). Xác suất tương đối hiệu chỉnh.

## 4. Rút gọn bộ tín hiệu

- AUC CV mô hình đầy đủ: 0.8725.
- Quy tắc 95%: 2 biến (Curricular units 1st sem (credited), Curricular units 1st sem (approved)).
- AUC CV cao nhất: 0.8731 với 6 biến (Curricular units 1st sem (credited), Curricular units 1st sem (enrolled), Curricular units 1st sem (approved), Curricular units 1st sem (without evaluations), Application mode, Course).
- Permutation importance (top 5): Curricular units 1st sem (approved) (0.3448), Curricular units 1st sem (credited) (0.0443), Curricular units 1st sem (enrolled) (0.0399), Course (0.0269), Application mode (0.0133).

## 5. Công bằng tại tỷ lệ gắn cờ 30%

- Gender (train_oof): 0: recall 62.8%, gắn cờ 23.0% (n=2298, dương=567); 1: recall 74.0%, gắn cờ 43.0% (n=1241, dương=570) → chênh lệch recall 11.2% (CI [0.06, 0.163])
- Gender (test): 0: recall 62.7%, gắn cờ 23.0% (n=570, dương=153); 1: recall 71.8%, gắn cờ 41.0% (n=315, dương=131) → chênh lệch recall 9.1% (CI [0.006, 0.2])
- Age at enrollment (train_oof): <= 20: recall 54.8%, gắn cờ 18.6% (n=2035, dương=431); > 20: recall 76.8%, gắn cờ 45.5% (n=1504, dương=706) → chênh lệch recall 22.0% (CI [0.17, 0.277])
- Age at enrollment (test): <= 20: recall 51.4%, gắn cờ 19.6% (n=516, dương=111); > 20: recall 76.9%, gắn cờ 43.1% (n=369, dương=173) → chênh lệch recall 25.5% (CI [0.144, 0.356])
- Debtor (train_oof): 0: recall 68.8%, gắn cờ 27.6% (n=3142, dương=885); 1: recall 67.1%, gắn cờ 49.1% (n=397, dương=252) → chênh lệch recall 1.7% (CI [0.002, 0.082])
- Debtor (test): 0: recall 67.0%, gắn cờ 26.8% (n=779, dương=224); 1: recall 66.7%, gắn cờ 48.1% (n=106, dương=60) → chênh lệch recall 0.3% (CI [0.002, 0.137])

## 6. Đánh đổi ngưỡng (primary)

| Gắn cờ | Recall OOF | Precision OOF | Lift | Recall test | Precision test |
|---|---|---|---|---|---|
| 5% | 14.9% | 96.0% | 2.99 | 14.4% | 97.6% |
| 10% | 29.3% | 94.1% | 2.93 | 29.6% | 94.4% |
| 15% | 42.7% | 91.5% | 2.85 | 43.7% | 89.2% |
| 20% | 53.8% | 86.4% | 2.69 | 51.8% | 85.0% |
| 25% | 62.9% | 80.8% | 2.52 | 59.5% | 79.3% |
| 30% | 68.4% | 73.3% | 2.28 | 66.9% | 73.1% |
| 35% | 74.6% | 68.4% | 2.13 | 74.3% | 68.1% |
| 40% | 79.8% | 64.0% | 1.99 | 81.7% | 65.2% |
| 50% | 87.7% | 56.3% | 1.75 | 89.8% | 57.4% |

Tỷ lệ gắn cờ cần để đạt recall mục tiêu 60%: 24%.

## 7. Độ nhạy

- Không cấu hình kịch bản độ nhạy (sensitivity_thresholds / suspect_label_rules).

## 8. Đối chiếu tiêu chí thành công (đặt trước)

| Tiêu chí | Kết quả | Đánh giá |
|---|---|---|
| AUC ≥ 0.7 | CV 0.873; test 0.877 | Đạt |
| Recall ≥ 60% khi gắn cờ 30% | CV 68.6%; test 66.9% | Đạt |
| Vượt baseline ≥ 0.02 AUC | 0.873 vs 0.810 | Đạt |
| Rút gọn ≥ 33% số biến | 84.6% | Đạt |
| Chênh lệch recall ≤ 10% | [0.112, 0.22, 0.017] | Không đạt |
| Biến bị cấm trong mô hình = 0 | 0 | Đạt |

## 9. Giới hạn và governance (bắt buộc rà soát)

- Kết luận chỉ ở mức liên hệ/sàng lọc trên dữ liệu đã cho; không suy diễn nhân quả hay hiệu quả can thiệp.
- Nếu dữ liệu cắt ngang (không có mốc thời gian), không tuyên bố 'dự báo sớm'.
- Mọi đề xuất hỗ trợ người học phải qua phê duyệt của con người; không gán nhãn tiêu cực; diễn đạt theo hướng hỗ trợ.
- Biến nhạy cảm chỉ dùng để kiểm định công bằng; tập kiểm tra nhỏ khiến CI rộng.
- Kết quả không chuyển giao trực tiếp sang bối cảnh/cơ sở khác khi chưa kiểm định lại.

Hình: `figures/roc_pr.png`, `figures/recall_vs_flag.png`, `figures/reduction.png`, `figures/calibration.png`.