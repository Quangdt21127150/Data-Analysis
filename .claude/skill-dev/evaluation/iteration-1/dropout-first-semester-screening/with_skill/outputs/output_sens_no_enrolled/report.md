# Báo cáo phân tích sàng lọc người học: Sàng lọc nguy cơ bỏ học sau kết quả học kỳ 1 năm nhất - độ nhạy: loại Enrolled khỏi nhãn chính

> Sinh tự động bởi skill education-data-analytics (10/11/2026). Các con số lấy từ `results.json`; phần diễn giải cần người phân tích rà soát.

## 1. Dữ liệu và nhãn

- Nguồn: `students_dropout.csv` (SHA-256 `3ef126de5cefff26…`), 4424 dòng.
- Nhãn dương: **Target ∈ ['Dropout']**; tập có nhãn 3630 dòng, 1421 ca dương (tỷ lệ nền 39.1%).
- Trạng thái nhãn: {'observed': 3630, 'suspect': 794}. Train 2904 (1137 dương) / test 726 (284 dương), phân tầng, seed 2026.
- 13 đặc trưng hợp lệ; biến bị loại: leakage: Curricular units 2nd sem (credited), Curricular units 2nd sem (enrolled), Curricular units 2nd sem (evaluations), Curricular units 2nd sem (approved), Curricular units 2nd sem (grade), Curricular units 2nd sem (without evaluations); sensitive: Marital status, Nacionality, Mother's qualification, Father's qualification, Mother's occupation, Father's occupation, Displaced, Educational special needs, Debtor, Tuition fees up to date, Scholarship holder, Gender, Age at enrollment, International; other: Unemployment rate, Inflation rate, GDP.

### Nhật ký biến đổi

| Bước | Luật | Số dòng |
|---|---|---|
| key | tạo khóa giả danh _rid theo thứ tự dòng |  |
| label | {"column": "Target", "type": "classes", "positive_classes": ["Dropout"]} | 3630 |

## 2. Chẩn đoán (chỉ trên train; hiệu chỉnh Holm)

| Biến | Kiểm định | Hiệu ứng | p (Holm) | Có ý nghĩa |
|---|---|---|---|---|
| Curricular units 1st sem (approved) | Mann-Whitney U | rank-biserial r = -0.717 | 1.39e-240 | Có |
| Curricular units 1st sem (grade) | Mann-Whitney U | rank-biserial r = -0.618 | 3e-174 | Có |
| Course | Chi-square | Cramér's V = 0.345 | 1.12e-62 | Có |
| Application mode | Chi-square | Cramér's V = 0.316 | 1.55e-50 | Có |
| Curricular units 1st sem (enrolled) | Mann-Whitney U | rank-biserial r = -0.27 | 2.09e-37 | Có |
| Previous qualification | Chi-square | Cramér's V = 0.203 | 1.4e-17 | Có |
| Admission grade | Mann-Whitney U | rank-biserial r = -0.146 | 2.25e-10 | Có |
| Previous qualification (grade) | Mann-Whitney U | rank-biserial r = -0.118 | 4.06e-07 | Có |
| Application order | Mann-Whitney U | rank-biserial r = -0.087 | 7.89e-06 | Không |
| Curricular units 1st sem (without evaluations) | Mann-Whitney U | rank-biserial r = 0.041 | 2.07e-05 | Không |
| Daytime/evening attendance | Chi-square | Cramér's V = 0.084 | 2.07e-05 | Không |
| Curricular units 1st sem (credited) | Mann-Whitney U | rank-biserial r = -0.019 | 0.293 | Không |
| Curricular units 1st sem (evaluations) | Mann-Whitney U | rank-biserial r = -0.027 | 0.293 | Không |

Hồi quy logistic điều chỉnh (pseudo R² = 0.5311; biến số: OR mỗi 1 độ lệch chuẩn; biến phân loại: so với mức phổ biến nhất). Các hạng tử p < 0.05:

- Curricular units 1st sem (approved): OR 0.017 (CI 95% 0.011-0.027)
- Curricular units 1st sem (credited): OR 2.825 (CI 95% 1.973-4.044)
- Course_9853: OR 5.786 (CI 95% 3.075-10.887)
- Curricular units 1st sem (enrolled): OR 4.252 (CI 95% 2.441-7.405)
- Application mode_39: OR 2.954 (CI 95% 1.904-4.583)
- Course_171: OR 0.085 (CI 95% 0.017-0.429)
- Course_9238: OR 0.371 (CI 95% 0.19-0.725)
- Course_9119: OR 4.016 (CI 95% 1.52-10.609)
- Curricular units 1st sem (without evaluations): OR 0.767 (CI 95% 0.632-0.931)
- Course_9773: OR 2.114 (CI 95% 1.205-3.71)
- Application mode_17: OR 1.521 (CI 95% 1.097-2.108)
- Curricular units 1st sem (grade): OR 0.554 (CI 95% 0.346-0.888)
- Previous qualification_2: OR 7.098 (CI 95% 1.359-37.065)
- Curricular units 1st sem (evaluations): OR 1.335 (CI 95% 1.031-1.73)

> Diễn giải: đây là liên hệ trên dữ liệu quan sát, có thể theo chiều ngược hoặc do yếu tố gây nhiễu; không kết luận nhân quả.

## 3. Hiệu năng sàng lọc

Baseline một tín hiệu được chọn trên train: **Curricular units 1st sem (approved)**. Primary theo quy tắc đặt trước: **LR**.

| Mô hình | AUC CV | PR-AUC CV | Recall@30% CV | AUC test [CI 95%] | Recall test @30% |
|---|---|---|---|---|---|
| B0_prior | 0.499 ± 0.000 | 0.391 | 29.1% | - | - |
| B1_best_single | 0.856 ± 0.002 | 0.794 | 66.3% | 0.858 [0.826; 0.887] | 63.0% |
| LR | 0.920 ± 0.001 | 0.905 | 69.7% | 0.920 [0.896; 0.940] | 69.7% |
| RF | 0.908 ± 0.001 | 0.895 | 69.1% | 0.913 [0.889; 0.934] | 65.8% |
| LR_reduced_best | (đường rút gọn) | - | - | 0.920 | 69.0% |

Hiệu chỉnh: xác suất TB 0.4363 so với tỷ lệ nền 0.3915 (Brier 0.1032 vs hằng số 0.2382). Xác suất tương đối hiệu chỉnh.

## 4. Rút gọn bộ tín hiệu

- AUC CV mô hình đầy đủ: 0.9196.
- Quy tắc 95%: 2 biến (Curricular units 1st sem (enrolled), Curricular units 1st sem (approved)).
- AUC CV cao nhất: 0.9216 với 8 biến (Curricular units 1st sem (credited), Curricular units 1st sem (enrolled), Curricular units 1st sem (evaluations), Curricular units 1st sem (approved), Curricular units 1st sem (grade), Application mode, Course, Daytime/evening attendance).
- Permutation importance (top 5): Curricular units 1st sem (approved) (0.3936), Curricular units 1st sem (enrolled) (0.0495), Curricular units 1st sem (credited) (0.032), Course (0.0248), Application mode (0.0089).

## 5. Công bằng tại tỷ lệ gắn cờ 30%

- Gender (train_oof): 0: recall 65.7%, gắn cờ 22.3% (n=1904, dương=580); 1: recall 74.5%, gắn cờ 44.6% (n=1000, dương=557) → chênh lệch recall 8.8% (CI [0.031, 0.142])
- Gender (test): 0: recall 63.6%, gắn cờ 20.8% (n=477, dương=140); 1: recall 75.7%, gắn cờ 45.8% (n=249, dương=144) → chênh lệch recall 12.1% (CI [0.021, 0.235])
- Age at enrollment (train_oof): <= 20: recall 56.5%, gắn cờ 17.0% (n=1626, dương=428); > 20: recall 78.1%, gắn cờ 46.6% (n=1278, dương=709) → chênh lệch recall 21.6% (CI [0.16, 0.268])
- Age at enrollment (test): <= 20: recall 50.0%, gắn cờ 14.3% (n=454, dương=114); > 20: recall 82.9%, gắn cờ 54.4% (n=272, dương=170) → chênh lệch recall 32.9% (CI [0.218, 0.441])
- Debtor (train_oof): 0: recall 70.2%, gắn cờ 27.0% (n=2567, dương=885); 1: recall 69.4%, gắn cờ 52.8% (n=337, dương=252) → chênh lệch recall 0.8% (CI [0.001, 0.072])
- Debtor (test): 0: recall 71.9%, gắn cờ 27.1% (n=650, dương=224); 1: recall 61.7%, gắn cờ 48.7% (n=76, dương=60) → chênh lệch recall 10.2% (CI [0.007, 0.231])

## 6. Đánh đổi ngưỡng (primary)

| Gắn cờ | Recall OOF | Precision OOF | Lift | Recall test | Precision test |
|---|---|---|---|---|---|
| 5% | 12.7% | 98.6% | 2.53 | 17.6% | 100.0% |
| 10% | 25.3% | 99.0% | 2.53 | 26.1% | 100.0% |
| 15% | 38.1% | 99.3% | 2.54 | 37.0% | 100.0% |
| 20% | 50.1% | 98.1% | 2.51 | 49.6% | 98.6% |
| 25% | 61.7% | 96.6% | 2.47 | 58.8% | 97.7% |
| 30% | 70.0% | 91.3% | 2.33 | 69.7% | 93.0% |
| 35% | 76.5% | 85.5% | 2.19 | 72.9% | 88.5% |
| 40% | 83.0% | 81.2% | 2.08 | 78.9% | 83.6% |
| 50% | 90.2% | 70.7% | 1.8 | 89.1% | 74.2% |

Tỷ lệ gắn cờ cần để đạt recall mục tiêu 60%: 25%.

## 7. Độ nhạy

- include_suspect_labels: AUC CV 0.875 ± 0.001; recall@capacity 69.3%; n = 3539

## 8. Đối chiếu tiêu chí thành công (đặt trước)

| Tiêu chí | Kết quả | Đánh giá |
|---|---|---|
| AUC ≥ 0.7 | CV 0.920; test 0.920 | Đạt |
| Recall ≥ 60% khi gắn cờ 30% | CV 69.7%; test 69.7% | Đạt |
| Vượt baseline ≥ 0.02 AUC | 0.920 vs 0.856 | Đạt |
| Rút gọn ≥ 33% số biến | 84.6% | Đạt |
| Chênh lệch recall ≤ 10% | [0.088, 0.216, 0.008] | Không đạt |
| Biến bị cấm trong mô hình = 0 | 0 | Đạt |

## 9. Giới hạn và governance (bắt buộc rà soát)

- Kết luận chỉ ở mức liên hệ/sàng lọc trên dữ liệu đã cho; không suy diễn nhân quả hay hiệu quả can thiệp.
- Nếu dữ liệu cắt ngang (không có mốc thời gian), không tuyên bố 'dự báo sớm'.
- Mọi đề xuất hỗ trợ người học phải qua phê duyệt của con người; không gán nhãn tiêu cực; diễn đạt theo hướng hỗ trợ.
- Biến nhạy cảm chỉ dùng để kiểm định công bằng; tập kiểm tra nhỏ khiến CI rộng.
- Kết quả không chuyển giao trực tiếp sang bối cảnh/cơ sở khác khi chưa kiểm định lại.

Hình: `figures/roc_pr.png`, `figures/recall_vs_flag.png`, `figures/reduction.png`, `figures/calibration.png`.