# Báo cáo phân tích sàng lọc người học: UCI Predict Students' Dropout - sàng lọc nguy cơ bỏ học tại mốc cuối học kỳ 1

> Sinh tự động bởi skill student-risk-screening (10/11/2026). Các con số lấy từ `results.json`; phần diễn giải cần người phân tích rà soát.

## 1. Dữ liệu và nhãn

- Nguồn: `uci_dropout.csv` (SHA-256 `3ef126de5cefff26…`), 4424 dòng.
- Nhãn dương: **Target ∈ ['Dropout']**; tập có nhãn 4424 dòng, 1421 ca dương (tỷ lệ nền 32.1%).
- Trạng thái nhãn: {'observed': 4424}. Train 3539 (1137 dương) / test 885 (284 dương), phân tầng, seed 2026.
- 16 đặc trưng hợp lệ; biến bị loại: leakage: Curricular units 2nd sem (credited), Curricular units 2nd sem (enrolled), Curricular units 2nd sem (evaluations), Curricular units 2nd sem (approved), Curricular units 2nd sem (grade), Curricular units 2nd sem (without evaluations); sensitive: Marital status, Nacionality, Mother's qualification, Father's qualification, Mother's occupation, Father's occupation, Displaced, Educational special needs, Debtor, Tuition fees up to date, Gender, Age at enrollment, International, Scholarship holder; other: -.

### Nhật ký biến đổi

| Bước | Luật | Số dòng |
|---|---|---|
| key | tạo khóa giả danh _rid theo thứ tự dòng |  |
| label | {"column": "Target", "type": "classes", "positive_classes": ["Dropout"]} | 4424 |

## 2. Chẩn đoán (chỉ trên train; hiệu chỉnh Holm)

| Biến | Kiểm định | Hiệu ứng | p (Holm) | Có ý nghĩa |
|---|---|---|---|---|
| Curricular units 1st sem (approved) | Mann-Whitney U | rank-biserial r = -0.624 | 1.46e-202 | Có |
| Curricular units 1st sem (grade) | Mann-Whitney U | rank-biserial r = -0.541 | 7.39e-149 | Có |
| Application mode | Chi-square | Cramér's V = 0.296 | 2.33e-55 | Có |
| Course | Chi-square | Cramér's V = 0.265 | 1.07e-42 | Có |
| Previous qualification | Chi-square | Cramér's V = 0.215 | 8e-26 | Có |
| Curricular units 1st sem (enrolled) | Mann-Whitney U | rank-biserial r = -0.196 | 2.96e-22 | Có |
| Application order | Mann-Whitney U | rank-biserial r = -0.095 | 3.55e-07 | Không |
| Admission grade | Mann-Whitney U | rank-biserial r = -0.108 | 1.64e-06 | Có |
| Previous qualification (grade) | Mann-Whitney U | rank-biserial r = -0.101 | 9.22e-06 | Có |
| Daytime/evening attendance | Chi-square | Cramér's V = 0.072 | 0.000124 | Không |
| Curricular units 1st sem (without evaluations) | Mann-Whitney U | rank-biserial r = 0.029 | 0.00903 | Không |
| Curricular units 1st sem (evaluations) | Mann-Whitney U | rank-biserial r = -0.055 | 0.0384 | Không |
| GDP | Mann-Whitney U | rank-biserial r = -0.05 | 0.061 | Không |
| Unemployment rate | Mann-Whitney U | rank-biserial r = 0.025 | 0.675 | Không |
| Inflation rate | Mann-Whitney U | rank-biserial r = 0.024 | 0.675 | Không |
| Curricular units 1st sem (credited) | Mann-Whitney U | rank-biserial r = 0.001 | 0.942 | Không |

Hồi quy logistic điều chỉnh (pseudo R² = 0.3896; biến số: OR mỗi 1 độ lệch chuẩn; biến phân loại: so với mức phổ biến nhất). Các hạng tử p < 0.05:

- Curricular units 1st sem (approved): OR 0.075 (CI 95% 0.057-0.098)
- Curricular units 1st sem (credited): OR 2.648 (CI 95% 2.038-3.441)
- Course_9853: OR 4.916 (CI 95% 2.917-8.286)
- Curricular units 1st sem (enrolled): OR 2.339 (CI 95% 1.681-3.254)
- Course_9773: OR 2.987 (CI 95% 1.861-4.793)
- Application mode_39: OR 2.204 (CI 95% 1.562-3.11)
- Course_9130: OR 4.176 (CI 95% 2.227-7.831)
- Curricular units 1st sem (without evaluations): OR 0.801 (CI 95% 0.719-0.891)
- Course_9254: OR 2.566 (CI 95% 1.519-4.335)
- Unemployment rate: OR 1.213 (CI 95% 1.088-1.352)
- Previous qualification_2: OR 7.431 (CI 95% 2.092-26.402)
- Application mode_15: OR 0.166 (CI 95% 0.038-0.725)
- Application mode_7: OR 2.877 (CI 95% 1.07-7.741)

> Diễn giải: đây là liên hệ trên dữ liệu quan sát, có thể theo chiều ngược hoặc do yếu tố gây nhiễu; không kết luận nhân quả.

## 3. Hiệu năng sàng lọc

Baseline một tín hiệu được chọn trên train: **Curricular units 1st sem (approved)**. Primary theo quy tắc đặt trước: **LR**.

| Mô hình | AUC CV | PR-AUC CV | Recall@30% CV | AUC test [CI 95%] | Recall test @30% |
|---|---|---|---|---|---|
| B0_prior | 0.499 ± 0.000 | 0.321 | 28.9% | - | - |
| B1_best_single | 0.810 ± 0.001 | 0.680 | 65.3% | 0.844 [0.814; 0.869] | 66.2% |
| LR | 0.873 ± 0.001 | 0.802 | 68.5% | 0.876 [0.849; 0.899] | 67.6% |
| RF | 0.859 ± 0.002 | 0.785 | 67.0% | 0.881 [0.855; 0.903] | 71.5% |
| LR_reduced_best | (đường rút gọn) | - | - | 0.878 | 67.2% |

Hiệu chỉnh: xác suất TB 0.4187 so với tỷ lệ nền 0.3213 (Brier 0.1364 vs hằng số 0.2181). Xác suất tương đối hiệu chỉnh.

## 4. Rút gọn bộ tín hiệu

- AUC CV mô hình đầy đủ: 0.8733.
- Quy tắc 95%: 2 biến (Curricular units 1st sem (credited), Curricular units 1st sem (approved)).
- AUC CV cao nhất: 0.874 với 8 biến (Application order, Curricular units 1st sem (credited), Curricular units 1st sem (enrolled), Curricular units 1st sem (approved), Unemployment rate, GDP, Application mode, Course).
- Permutation importance (top 5): Curricular units 1st sem (approved) (0.3502), Curricular units 1st sem (credited) (0.046), Curricular units 1st sem (enrolled) (0.0409), Course (0.0276), Application mode (0.0132).

## 5. Công bằng tại tỷ lệ gắn cờ 30%

- Gender (train_oof): 0: recall 63.5%, gắn cờ 23.2% (n=2298, dương=567); 1: recall 73.7%, gắn cờ 42.5% (n=1241, dương=570) → chênh lệch recall 10.2% (CI [0.048, 0.154])
- Gender (test): 0: recall 62.1%, gắn cờ 22.3% (n=570, dương=153); 1: recall 74.0%, gắn cờ 40.6% (n=315, dương=131) → chênh lệch recall 11.9% (CI [0.018, 0.224])
- Age at enrollment (train_oof): <= 20: recall 55.0%, gắn cờ 18.4% (n=2035, dương=431); > 20: recall 76.9%, gắn cờ 45.7% (n=1504, dương=706) → chênh lệch recall 21.9% (CI [0.17, 0.274])
- Age at enrollment (test): <= 20: recall 53.2%, gắn cờ 18.8% (n=516, dương=111); > 20: recall 76.9%, gắn cờ 42.8% (n=369, dương=173) → chênh lệch recall 23.7% (CI [0.129, 0.332])

## 6. Đánh đổi ngưỡng (primary)

| Gắn cờ | Recall OOF | Precision OOF | Lift | Recall test | Precision test |
|---|---|---|---|---|---|
| 5% | 14.9% | 96.0% | 2.99 | 13.7% | 97.5% |
| 10% | 29.4% | 94.3% | 2.94 | 27.5% | 95.1% |
| 15% | 42.7% | 91.3% | 2.84 | 43.3% | 89.1% |
| 20% | 53.8% | 86.4% | 2.69 | 51.4% | 86.4% |
| 25% | 62.2% | 79.9% | 2.49 | 59.5% | 80.9% |
| 30% | 68.6% | 73.5% | 2.29 | 67.6% | 75.3% |
| 35% | 74.1% | 68.0% | 2.12 | 74.7% | 68.6% |
| 40% | 80.4% | 64.5% | 2.01 | 79.2% | 63.0% |
| 50% | 87.7% | 56.3% | 1.75 | 89.1% | 56.1% |

Tỷ lệ gắn cờ cần để đạt recall mục tiêu 60%: 24%.

## 7. Độ nhạy

- Không cấu hình kịch bản độ nhạy (sensitivity_thresholds / suspect_label_rules).

## 8. Đối chiếu tiêu chí thành công (đặt trước)

| Tiêu chí | Kết quả | Đánh giá |
|---|---|---|
| AUC ≥ 0.7 | CV 0.873; test 0.876 | Đạt |
| Recall ≥ 60% khi gắn cờ 30% | CV 68.5%; test 67.6% | Đạt |
| Vượt baseline ≥ 0.02 AUC | 0.873 vs 0.810 | Đạt |
| Rút gọn ≥ 33% số biến | 87.5% | Đạt |
| Chênh lệch recall ≤ 10% | [0.102, 0.219] | Không đạt |
| Biến bị cấm trong mô hình = 0 | 0 | Đạt |

## 9. Giới hạn và governance (bắt buộc rà soát)

- Kết luận chỉ ở mức liên hệ/sàng lọc trên dữ liệu đã cho; không suy diễn nhân quả hay hiệu quả can thiệp.
- Nếu dữ liệu cắt ngang (không có mốc thời gian), không tuyên bố 'dự báo sớm'.
- Mọi đề xuất hỗ trợ người học phải qua phê duyệt của con người; không gán nhãn tiêu cực; diễn đạt theo hướng hỗ trợ.
- Biến nhạy cảm chỉ dùng để kiểm định công bằng; tập kiểm tra nhỏ khiến CI rộng.
- Kết quả không chuyển giao trực tiếp sang bối cảnh/cơ sở khác khi chưa kiểm định lại.

Hình: `figures/roc_pr.png`, `figures/recall_vs_flag.png`, `figures/reduction.png`, `figures/calibration.png`.